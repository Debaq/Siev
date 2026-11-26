//! Prueba del equipo: cuanto cuesta cada cuadro en ESTE PC y que niveles
//! clinicos puede sostener (ver `tools/piso/README.md`).
//!
//! Pasa un clip MJPEG real de la mascara por el pipeline completo (decode
//! incluido, sin dibujar) dos veces: sin IA y con IA. Con eso estima los fps
//! sostenibles en cualquier resolucion: el decode y el detector clasico crecen
//! con los pixeles; la IA en recorte de 64x64 no.

use std::path::Path;
use std::sync::{Arc, Mutex};
use std::time::Instant;

use serde::{Deserialize, Serialize};

use super::native_video::NativeVideoManager;
use super::trace::PgmSequence;
use crate::bus::EventBus;
use crate::math::processor::EyeProcessor;

/// Fraccion maxima del presupuesto por cuadro que puede usar el pipeline
/// (el resto queda para la GUI y el sistema).
pub const USO_MAX: f64 = 0.7;

/// Niveles clinicos: (fps, nombre).
pub const NIVELES: [(u32, &str); 4] = [(60, "clinico"), (90, "vHIT basico"), (120, "vHIT avanzado"), (220, "lujo")];

/// fps minimos para que el equipo sea compatible.
pub const FPS_MINIMO: u32 = 60;

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct ResultadoEquipo {
    /// CPU medida (si cambia, hay que volver a medir).
    pub cpu: String,
    /// ms por cuadro sin IA (decode + detector + tracking).
    pub ms_sin_ia: f64,
    /// ms por cuadro con IA.
    pub ms_con_ia: f64,
    /// Pixeles por cuadro del clip medido.
    pub px_ref: u64,
    /// Fecha de la medicion (unix, s).
    pub fecha: i64,
}

impl ResultadoEquipo {
    /// ms estimados por cuadro a `ancho` x `alto`.
    pub fn ms_cuadro(&self, ancho: u32, alto: u32, con_ia: bool) -> f64 {
        let escala = (ancho as f64 * alto as f64) / self.px_ref.max(1) as f64;
        let ia = if con_ia { (self.ms_con_ia - self.ms_sin_ia).max(0.0) } else { 0.0 };
        self.ms_sin_ia * escala + ia
    }

    /// fps sostenibles a esa resolucion.
    pub fn fps_max(&self, ancho: u32, alto: u32, con_ia: bool) -> f64 {
        1000.0 * USO_MAX / self.ms_cuadro(ancho, alto, con_ia).max(1e-3)
    }

    /// El equipo alcanza `fps` a esa resolucion.
    pub fn alcanza(&self, ancho: u32, alto: u32, fps: u32, con_ia: bool) -> bool {
        self.fps_max(ancho, alto, con_ia) >= fps as f64
    }

    /// Nivel clinico mas alto alcanzable a esa resolucion (None = ninguno).
    pub fn nivel(&self, ancho: u32, alto: u32, con_ia: bool) -> Option<(u32, &'static str)> {
        NIVELES.iter().rev().copied().find(|(f, _)| self.alcanza(ancho, alto, *f, con_ia))
    }
}

/// Nombre de la CPU de este equipo.
pub fn cpu_actual() -> String {
    std::fs::read_to_string("/proc/cpuinfo")
        .ok()
        .and_then(|s| s.lines().find(|l| l.starts_with("model name")).map(|l| l.split(':').nth(1).unwrap_or("").trim().to_string()))
        .unwrap_or_else(|| std::env::consts::ARCH.to_string())
}

/// Mide el equipo con el clip MJPEG. `configurar` aplica la configuracion del
/// detector (la de la app) al pipeline de prueba. `modelo`: el de la IA (o None).
pub fn medir(
    clip: &Path,
    modelo: Option<&str>,
    configurar: impl Fn(&NativeVideoManager),
) -> Result<ResultadoEquipo, String> {
    let pasada = |con_ia: bool| -> Result<(f64, u64), String> {
        let seq = PgmSequence::open_mjpeg(clip, 225.0)?;
        let (n, px) = (seq.len(), seq.width as u64 * seq.height as u64);
        let (bus, rx) = EventBus::new_lossless(n * 2 + 16);
        let nv = NativeVideoManager::new(Arc::new(bus), Arc::new(Mutex::new(EyeProcessor::new())), Arc::new(Mutex::new(None)));
        configurar(&nv);
        nv.set_preview_every_frame(false);
        nv.set_yolo_frequency(1);
        let modelo = match (con_ia, modelo) {
            (true, Some(m)) => m.to_string(),
            _ => "/nonexistent/sin-ia".to_string(),
        };
        nv.set_use_yolo(con_ia && modelo != "/nonexistent/sin-ia");
        let vaciador = std::thread::spawn(move || while rx.frames.recv().is_ok() {});
        let traza = std::env::temp_dir().join(format!("siev_equipo_{}.jsonl", std::process::id()));
        let t = Instant::now();
        nv.run_pgm_sequence(seq, traza.clone(), modelo)?;
        let ms = t.elapsed().as_secs_f64() * 1000.0 / n.max(1) as f64;
        drop(nv);
        let _ = vaciador.join();
        let _ = std::fs::remove_file(traza);
        Ok((ms, px))
    };
    // una pasada corta de calentamiento (caches, frecuencia de la CPU)
    let _ = pasada(false)?;
    let (ms_sin_ia, px_ref) = pasada(false)?;
    let ms_con_ia = if modelo.is_some() { pasada(true)?.0 } else { ms_sin_ia };
    Ok(ResultadoEquipo {
        cpu: cpu_actual(),
        ms_sin_ia,
        ms_con_ia,
        px_ref,
        fecha: std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs() as i64).unwrap_or(0),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn r() -> ResultadoEquipo {
        ResultadoEquipo { cpu: "x".into(), ms_sin_ia: 2.0, ms_con_ia: 3.0, px_ref: 640 * 360, fecha: 0 }
    }

    #[test]
    fn escala_con_la_resolucion_salvo_la_ia() {
        let r = r();
        assert!((r.ms_cuadro(640, 360, true) - 3.0).abs() < 1e-9);
        // 4x pixeles: el decode/detector se multiplica, la IA no
        assert!((r.ms_cuadro(1280, 720, true) - 9.0).abs() < 1e-9);
    }

    #[test]
    fn niveles() {
        let r = r(); // 3 ms -> 233 fps al 70 %
        assert_eq!(r.nivel(640, 360, true), Some((220, "lujo")));
        // 1280x720: 9 ms -> 78 fps -> solo clinico
        assert_eq!(r.nivel(1280, 720, true), Some((60, "clinico")));
        assert!(!r.alcanza(1280, 720, 90, true));
    }
}
