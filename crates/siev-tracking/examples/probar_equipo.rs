//! Prueba del equipo por linea de comandos (lo mismo que hace la app al arrancar).
//!
//!   cargo run --release -p siev-tracking --example probar_equipo -- <clip.mjpeg> [modelo.bin]

use siev_tracking::vng::equipo::{self, NIVELES};
use siev_tracking::vng::mejoras::OpcionesDetector;

fn main() {
    let a: Vec<String> = std::env::args().skip(1).collect();
    let clip = a.first().expect("uso: probar_equipo <clip.mjpeg> [modelo.bin]");
    let r = equipo::medir(clip.as_ref(), a.get(1).map(|s| s.as_str()), |nv| {
        nv.set_nose_width(0.25);
        nv.set_eye_height(0.25);
        nv.set_manual_roi_right(0.19, 0.67, 0.91, 0.16);
        nv.set_manual_roi_left(0.17, 0.68, 0.14, 0.86);
        nv.set_thresholds(0, 0);
        nv.set_detector_options(OpcionesDetector { quitar_reflejos: true, umbral_valle: false, umbral_semilla: true });
    })
    .expect("prueba fallida");
    println!("{}: sin IA {:.3} ms, con IA {:.3} ms por cuadro", r.cpu, r.ms_sin_ia, r.ms_con_ia);
    for (w, h) in [(640, 360), (1280, 720), (1920, 1080)] {
        let niveles: Vec<String> =
            NIVELES.iter().map(|(f, _)| format!("{f}:{}", if r.alcanza(w, h, *f, true) { "si" } else { "no" })).collect();
        println!("  {w}x{h}: ~{:.0} fps -> {}", r.fps_max(w, h, true), niveles.join(" "));
    }
}
