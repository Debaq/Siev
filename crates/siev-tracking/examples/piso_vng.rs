//! Piso de hardware del VNG: mide en ESTE PC cuanto cuesta cada cuadro del
//! pipeline real (sin dibujar) y lo clasifica en los niveles clinicos.
//!
//!   cargo run --release -p siev-tracking --example piso_vng -- <carpeta_pgm> [carpeta_jpg]
//!
//! <carpeta_pgm>: secuencia de camara cruda (p. ej. fixtures/mascara_20261125_2min/pgm).
//! [carpeta_jpg]: cuadros MJPEG originales de la camara para medir la
//!   decodificacion (ffmpeg -i crudo.mkv -c:v copy -frames:v 500 dir/%06d.jpg).
//!
//! Variables: SIEV_YOLO=<modelo.bin|onnx> (IA), SIEV_IA_CADA, SIEV_IA_ROI,
//! SIEV_IA_PARALELO, SIEV_OJO_SIN_AVX, SIEV_OJO_UMBRAL (ver video_marcado).
//!
//! Niveles (requisito clinico): 60 fps clinico, 90 vHIT basico, 120 vHIT
//! avanzado, 220 lujo. Un nivel se cumple si decodificar + procesar un cuadro
//! usa como mucho el 70 % de 1000/fps ms (el resto queda para la GUI y el SO).

use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use std::time::Instant;

use siev_tracking::bus::EventBus;
use siev_tracking::math::processor::EyeProcessor;
use siev_tracking::vng::mejoras::OpcionesDetector;
use siev_tracking::vng::native_video::NativeVideoManager;
use siev_tracking::vng::trace::PgmSequence;
use zune_core::colorspace::ColorSpace;
use zune_core::options::DecoderOptions;
use zune_jpeg::JpegDecoder;

const NIVELES: [(u32, &str); 4] = [(60, "clinico"), (90, "vHIT basico"), (120, "vHIT avanzado"), (220, "lujo")];
const USO_MAX: f64 = 0.7;

fn main() {
    let a: Vec<String> = std::env::args().skip(1).collect();
    let Some(dir) = a.first() else {
        eprintln!("uso: piso_vng <carpeta_pgm> [carpeta_jpg]");
        std::process::exit(2);
    };

    // 1) decodificacion MJPEG (lo que hace la app con la camara real)
    let ms_jpeg = a.get(1).map(|d| medir_jpeg(d)).unwrap_or(0.0);

    // 2) pipeline real sobre la secuencia, sin vista previa por cuadro
    let seq = PgmSequence::open(&PathBuf::from(dir), 225.0).expect("secuencia PGM ilegible");
    let n = seq.len();
    let (bus, rx) = EventBus::new_lossless(n * 2 + 16);
    let nv = NativeVideoManager::new(Arc::new(bus), Arc::new(Mutex::new(EyeProcessor::new())), Arc::new(Mutex::new(None)));
    nv.set_nose_width(0.25);
    nv.set_eye_height(0.25);
    nv.set_manual_roi_right(0.19, 0.67, 0.91, 0.16);
    nv.set_manual_roi_left(0.17, 0.68, 0.14, 0.86);
    nv.set_thresholds(0, 0);
    nv.set_detector_options(OpcionesDetector { quitar_reflejos: true, umbral_valle: false, umbral_semilla: true });
    nv.set_ia_closed_eye_judge(true);
    nv.set_preview_every_frame(false);
    if let Some(cada) = std::env::var("SIEV_IA_CADA").ok().and_then(|v| v.parse().ok()) {
        nv.set_yolo_frequency(cada);
    }
    let modelo = std::env::var("SIEV_YOLO").ok();
    nv.set_use_yolo(modelo.is_some());
    let modelo = modelo.unwrap_or_else(|| "/nonexistent/no-yolo.onnx".into());
    let traza = std::env::temp_dir().join("piso_vng.traza.jsonl");
    // vaciar el bus en paralelo para que no se llene
    let vaciador = std::thread::spawn(move || {
        while rx.frames.recv().is_ok() {}
    });
    let t = Instant::now();
    nv.run_pgm_sequence(seq, traza.clone(), modelo).expect("corrida fallida");
    let ms_pipe = t.elapsed().as_secs_f64() * 1000.0 / n as f64;
    drop(nv);
    let _ = vaciador.join();
    let _ = std::fs::remove_file(&traza);

    let total = ms_jpeg + ms_pipe;
    println!();
    println!("=== piso_vng ({n} cuadros) ===");
    println!("decodificar MJPEG : {ms_jpeg:6.3} ms/cuadro{}", if a.get(1).is_none() { " (no medido)" } else { "" });
    println!("pipeline (+lectura): {ms_pipe:6.3} ms/cuadro");
    println!("total             : {total:6.3} ms/cuadro  -> maximo sostenible ~{:.0} fps", 1000.0 * USO_MAX / total);
    for (fps, nombre) in NIVELES {
        let presupuesto = 1000.0 / fps as f64;
        let uso = total / presupuesto;
        println!(
            "  {fps:>3} fps {nombre:<14} presupuesto {presupuesto:5.2} ms  uso {:5.1} %  {}",
            uso * 100.0,
            if uso <= USO_MAX { "OK" } else if uso <= 1.0 { "justo" } else { "NO" }
        );
    }
}

fn medir_jpeg(dir: &str) -> f64 {
    let mut archivos: Vec<_> = std::fs::read_dir(dir)
        .expect("carpeta_jpg ilegible")
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| p.extension().is_some_and(|x| x == "jpg"))
        .collect();
    archivos.sort();
    let datos: Vec<Vec<u8>> = archivos.iter().map(|p| std::fs::read(p).unwrap()).collect();
    let opciones = DecoderOptions::default().jpeg_set_out_colorspace(ColorSpace::Luma);
    let t = Instant::now();
    let mut px = 0usize;
    for d in &datos {
        let mut dec = JpegDecoder::new_with_options(d.as_slice(), opciones);
        px += dec.decode().map(|v| v.len()).unwrap_or(0);
    }
    let ms = t.elapsed().as_secs_f64() * 1000.0 / datos.len().max(1) as f64;
    eprintln!("[jpeg] {} cuadros, {} px/cuadro", datos.len(), px / datos.len().max(1));
    ms
}
