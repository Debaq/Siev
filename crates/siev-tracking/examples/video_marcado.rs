//! Video de depuracion: pasa una secuencia PGM de camara cruda por el pipeline
//! real, con la configuracion de la app, y escribe CADA cuadro con sus marcas
//! y el numero de cuadro, para ubicar errores.
//!
//!   cargo run --release -p siev-tracking --example video_marcado -- \
//!       <carpeta_pgm> <salida.mp4> [fps_salida=60]
//!
//! Variables: SIEV_YOLO=<modelo.onnx> (IA), SIEV_JUEZ=0 (desactiva la IA como
//! juez de ojo cerrado).
//!
//! Marcas: caja verde = zona de la IA, amarilla = zona manual, magenta = la IA
//! da el ojo por cerrado. Cruz roja/azul = pupila OD/OI. Cruz verde fina =
//! centro del iris segun la IA. Arriba: numero de cuadro (= `frame_idx` de la
//! traza; el PGM es ese numero + 1) y tiempo en la grabacion.

use std::io::Write;
use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::sync::{Arc, Mutex};

use siev_tracking::bus::EventBus;
use siev_tracking::math::processor::EyeProcessor;
use siev_tracking::vng::mejoras::OpcionesDetector;
use siev_tracking::vng::native_video::NativeVideoManager;
use siev_tracking::vng::trace::PgmSequence;

const FPS_GRABACION: f64 = 225.0;

fn main() {
    let a: Vec<String> = std::env::args().skip(1).collect();
    let (Some(dir), Some(salida)) = (a.first(), a.get(1)) else {
        eprintln!("uso: video_marcado <carpeta_pgm> <salida.mp4> [fps_salida]");
        std::process::exit(2);
    };
    let fps_salida: u32 = a.get(2).and_then(|v| v.parse().ok()).unwrap_or(60);

    let seq = PgmSequence::open(&PathBuf::from(dir), FPS_GRABACION).expect("secuencia PGM ilegible");
    let n = seq.len();

    let (bus, rx) = EventBus::new_lossless(n * 2 + 16);
    let nv = NativeVideoManager::new(Arc::new(bus), Arc::new(Mutex::new(EyeProcessor::new())), Arc::new(Mutex::new(None)));
    // Configuracion por defecto de la app (siev.db + mejoras activas).
    nv.set_nose_width(0.25);
    nv.set_eye_height(0.25);
    nv.set_manual_roi_right(0.19, 0.67, 0.91, 0.16);
    nv.set_manual_roi_left(0.17, 0.68, 0.14, 0.86);
    nv.set_thresholds(0, 0);
    nv.set_detector_options(OpcionesDetector { quitar_reflejos: true, umbral_valle: false, umbral_semilla: true });
    nv.set_ia_closed_eye_judge(std::env::var("SIEV_JUEZ").map(|v| v != "0").unwrap_or(true));
    nv.set_preview_every_frame(true);
    let modelo = std::env::var("SIEV_YOLO").ok();
    nv.set_use_yolo(modelo.is_some());
    let modelo = modelo.unwrap_or_else(|| "/nonexistent/no-yolo.onnx".into());

    let trace = PathBuf::from(salida).with_extension("traza.jsonl");
    let nv = Arc::new(nv);
    let corrida = {
        let (nv, trace) = (nv.clone(), trace.clone());
        std::thread::spawn(move || nv.run_pgm_sequence(seq, trace, modelo).expect("corrida fallida"))
    };
    // Soltar la referencia local: al terminar la corrida se libera el bus y
    // el canal de cuadros se cierra, lo que termina el bucle de abajo.
    drop(nv);

    // El primer cuadro fija el tamaño para ffmpeg.
    let primero = rx.frames.recv().expect("el pipeline no emitio cuadros");
    let (w, h) = primero.dimensions();
    let texto = format!(
        "drawtext=fontfile=/usr/share/fonts/TTF/DejaVuSansMono.ttf:fontsize=22:fontcolor=white:x=10:y=6:\
         text='cuadro %{{frame_num}}   t=%{{eif\\:n/{FPS_GRABACION}\\:d}}.%{{eif\\:mod(n*1000/{FPS_GRABACION}\\,1000)\\:d\\:3}} s'"
    );
    let filtro = format!("scale={}:{}:flags=lanczos,pad=iw:ih+36:0:36:color=0x2b3440,{texto}", w * 2, h * 2);
    let mut ff = Command::new("ffmpeg")
        .args(["-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24"])
        .args(["-s", &format!("{w}x{h}"), "-r", &fps_salida.to_string(), "-i", "-"])
        .args(["-vf", &filtro, "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p"])
        .arg(salida)
        .stdin(Stdio::piped())
        .spawn()
        .expect("no se pudo lanzar ffmpeg");
    let mut entrada = ff.stdin.take().unwrap();

    let mut escritos = 0usize;
    entrada.write_all(primero.as_raw()).expect("ffmpeg cerro la entrada");
    escritos += 1;
    while let Ok(f) = rx.frames.recv() {
        if f.dimensions() != (w, h) {
            eprintln!("cuadro {escritos} con otro tamaño, omitido");
            continue;
        }
        entrada.write_all(f.as_raw()).expect("ffmpeg cerro la entrada");
        escritos += 1;
        if escritos.is_multiple_of(2000) {
            eprintln!("{escritos}/{n} cuadros");
        }
    }
    drop(entrada);
    corrida.join().unwrap();
    let ok = ff.wait().map(|s| s.success()).unwrap_or(false);
    println!(
        "{} cuadros escritos de {n} -> {salida} ({}), traza en {}",
        escritos,
        if ok { "ok" } else { "ffmpeg fallo" },
        trace.display()
    );
}
