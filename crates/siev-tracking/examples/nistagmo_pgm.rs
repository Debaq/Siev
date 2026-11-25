//! Corre una secuencia PGM por el pipeline real y resume el nistagmo detectado.
//!
//!   cargo run --release -p siev-tracking --example nistagmo_pgm -- <carpeta> [umbral_od umbral_oi] [amp_min]
//!
//! Defaults: fixtures/seq_eyes_800, umbrales 47 57 (los de la regresion), amplitud 0.5.
//!
//! Variables opcionales:
//!   SIEV_YOLO=<modelo.onnx>   activa el anclaje por IA
//!   SIEV_FRAME_OUT=<png>      guarda el ultimo cuadro de vista previa (con cajas)
//!   SIEV_MEJORAS=reflejos,valle,semilla  activa las mejoras del detector
//!   SIEV_IA_MARGEN=0.3        margen de la caja de iris (fraccion del diametro)
//!   SIEV_FRAMES_DIR=<dir>     guarda ~12 cuadros de vista previa repartidos
//!   SIEV_GEOM_APP=1           geometria de la app para cuadros crudos de camara

use std::path::PathBuf;
use std::sync::{Arc, Mutex};

use siev_tracking::bus::{EventBus, TrackEvent};
use siev_tracking::math::processor::EyeProcessor;
use siev_tracking::vng::live::{Eje, LiveNystagmus, Ojo};
use siev_tracking::vng::native_video::NativeVideoManager;
use siev_tracking::vng::trace::PgmSequence;

fn main() {
    let a: Vec<String> = std::env::args().skip(1).collect();
    let dir = PathBuf::from(a.first().cloned().unwrap_or_else(|| "fixtures/seq_eyes_800".into()));
    let thr_r: u8 = a.get(1).and_then(|v| v.parse().ok()).unwrap_or(47);
    let thr_l: u8 = a.get(2).and_then(|v| v.parse().ok()).unwrap_or(57);
    let amp: f64 = a.get(3).and_then(|v| v.parse().ok()).unwrap_or(0.5);

    let seq = PgmSequence::open(&dir, 200.0).expect("secuencia PGM ilegible");
    let n = seq.len();
    let (bus, rx) = EventBus::new_with_capacity(n * 2 + 16);
    let nv = NativeVideoManager::new(Arc::new(bus), Arc::new(Mutex::new(EyeProcessor::new())), Arc::new(Mutex::new(None)));
    if std::env::var_os("SIEV_GEOM_APP").is_some() {
        // Cuadros crudos de camara: la geometria por defecto de la app (siev.db).
        nv.set_nose_width(0.25);
        nv.set_eye_height(0.25);
        nv.set_manual_roi_right(0.19, 0.67, 0.91, 0.16);
        nv.set_manual_roi_left(0.17, 0.68, 0.14, 0.86);
    } else {
        // Mismos parametros geometricos que la prueba de regresion (fuente = cuadro combinado).
        nv.set_nose_width(0.0);
        nv.set_eye_height(0.5);
        nv.set_manual_roi_right(0.1, 0.9, 0.9, 0.1);
        nv.set_manual_roi_left(0.1, 0.9, 0.1, 0.9);
    }
    nv.set_thresholds(thr_r, thr_l);

    // SIEV_MEJORAS=reflejos,valle
    let mej = std::env::var("SIEV_MEJORAS").unwrap_or_default();
    nv.set_detector_options(siev_tracking::vng::mejoras::OpcionesDetector {
        quitar_reflejos: mej.contains("reflejos"),
        umbral_valle: mej.contains("valle"),
        umbral_semilla: mej.contains("semilla"),
    });

    if let Some(m) = std::env::var("SIEV_IA_MARGEN").ok().and_then(|v| v.parse().ok()) {
        nv.set_ia_margin(m);
    }

    let modelo = std::env::var("SIEV_YOLO").ok();
    if modelo.is_some() {
        nv.set_use_yolo(true);
    }
    let modelo = modelo.unwrap_or_else(|| "/nonexistent/no-yolo.onnx".into());

    let trace = std::env::temp_dir().join(format!("siev_nistagmo_pgm_{}.jsonl", std::process::id()));
    let nv = Arc::new(nv);
    let corrida = {
        let nv = nv.clone();
        std::thread::spawn(move || nv.run_pgm_sequence(seq, trace, modelo).expect("corrida fallida"))
    };
    // Drenar cuadros de vista previa mientras corre; quedarse con uno de la mitad.
    let mut cuadros = Vec::new();
    while !corrida.is_finished() {
        if let Ok(f) = rx.frames.recv_timeout(std::time::Duration::from_millis(50)) {
            cuadros.push(f);
        }
    }
    corrida.join().unwrap();
    if let Ok(dir) = std::env::var("SIEV_FRAMES_DIR") {
        // Muestra pareja de cuadros de vista previa a lo largo de la secuencia.
        std::fs::create_dir_all(&dir).expect("no se pudo crear el directorio");
        let paso = (cuadros.len() / 12).max(1);
        for (i, f) in cuadros.iter().step_by(paso).enumerate() {
            f.save(format!("{dir}/{i:02}.png")).expect("no se pudo guardar el cuadro");
        }
        println!("{} cuadros de muestra en {dir}", cuadros.len().div_ceil(paso));
    }
    if let (Ok(ruta), Some(f)) = (std::env::var("SIEV_FRAME_OUT"), cuadros.get(cuadros.len() / 2)) {
        f.save(&ruta).expect("no se pudo guardar el cuadro");
        println!("cuadro guardado en {ruta} ({} capturados)", cuadros.len());
    }

    let mut live = LiveNystagmus::new(amp);
    live.ventana_s = n as f64 / 200.0;
    let (mut t0, mut muestras, mut con_od, mut con_oi) = (None, 0, 0, 0);
    while let Ok(ev) = rx.events.try_recv() {
        if let TrackEvent::EyeData(d) = ev {
            if !d.is_calibrated {
                continue;
            }
            let t = d.timestamp - *t0.get_or_insert(d.timestamp);
            muestras += 1;
            con_od += d.right.is_some() as usize;
            con_oi += d.left.is_some() as usize;
            live.push(t, d.right, d.left);
        }
    }
    println!("{n} cuadros, {muestras} muestras analizadas (OD {con_od}, OI {con_oi} con pupila), amp min {amp} px");
    for ojo in Ojo::TODOS {
        for eje in Eje::TODOS {
            let r = live.resumen(ojo, eje);
            println!(
                "{} {}: {:3} latidos  {:.2} Hz  |SPV| {:6.1} px/s  dir {}",
                ojo.nombre(), eje.nombre(), r.latidos_total, r.frecuencia_hz, r.spv_abs, r.direccion.unwrap_or("—")
            );
        }
    }
}
