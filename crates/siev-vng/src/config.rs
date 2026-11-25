//! Configuracion persistente en `~/.config/siev-vng/config.json`.
//!
//! Los valores por defecto son los que la app anterior (rama rust-rust) tenia
//! guardados para esta misma mascara en `siev.db` (`settings.app_config.vng`).
//! Mismo equipo, mismos valores de partida.

use std::collections::BTreeMap;
use std::path::PathBuf;

use serde::{Deserialize, Serialize};
use crate::calibracion::Estacion;
use siev_tracking::vng::camara_hw;
use siev_tracking::vng::mejoras::OpcionesDetector;
use siev_tracking::vng::native_video::NativeVideoManager;

#[derive(Clone, Default, Serialize, Deserialize)]
#[serde(default)]
pub struct Config {
    pub camara: Camara,
    pub ojos: Ojos,
    pub detector: Detector,
    pub analisis: Analisis,
    pub ia: Ia,
    pub estacion: Estacion,
}

#[derive(Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct Camara {
    /// Nombre de la camara preferida; vacio = primera USB.
    pub nombre: String,
    pub ancho: u32,
    pub alto: u32,
    pub fps: u32,
    pub brillo: i32,
    /// Escala de la UI 0-100; 33.3 = sin cambio.
    pub contraste: f32,
    pub mostrar_mascaras: bool,
    /// Controles del sensor (V4L2) que el usuario cambio: id -> valor.
    /// Los que no estan quedan como los tenga la camara.
    pub sensor: BTreeMap<u32, i64>,
}

#[derive(Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct Ojos {
    /// Umbral automatico por cuadro (ignora `umbral_*`).
    pub auto_od: bool,
    pub auto_oi: bool,
    pub umbral_od: u8,
    pub umbral_oi: u8,
    pub roi_od: Roi,
    pub roi_oi: Roi,
    pub franja_nasal: f32,
    pub alto_ojo: f32,
}

#[derive(Clone, Copy, Serialize, Deserialize)]
pub struct Roi {
    pub top: f32,
    pub bottom: f32,
    pub nasal: f32,
    pub temporal: f32,
}

#[derive(Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct Detector {
    pub suavizado: f32,
    pub min_circularidad: f32,
    pub min_area: u32,
    pub max_area_ratio: f32,
    pub parpadeo: bool,
    pub parpadeo_blanco: f32,
    pub tolerancia_perdida: u32,
    pub margen_velocidad: f32,
    pub aspecto_min: f32,
    pub aspecto_max: f32,
    pub quitar_reflejos: bool,
    pub metodo_auto: MetodoAuto,
}

/// Como se calcula el umbral automatico (ver `vng::mejoras`).
#[derive(Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum MetodoAuto {
    /// Crecer desde el punto mas oscuro mientras la region siga redonda.
    Region,
    /// Valle del histograma entre pupila e iris; si no hay, region.
    Valle,
    /// Percentil 15 % de la ventana (metodo original).
    Percentil,
}

impl MetodoAuto {
    pub const TODOS: [MetodoAuto; 3] = [MetodoAuto::Region, MetodoAuto::Valle, MetodoAuto::Percentil];
    pub fn nombre(self) -> &'static str {
        match self {
            MetodoAuto::Region => "Region oscura (recomendado)",
            MetodoAuto::Valle => "Valle del histograma",
            MetodoAuto::Percentil => "Percentil 15 % (original)",
        }
    }
}

#[derive(Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct Analisis {
    pub amplitud_min: f64,
    pub ventana_s: f64,
    pub espejar_h: bool,
}

#[derive(Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct Ia {
    pub modelo: String,
    pub usar: bool,
    /// Margen alrededor del iris detectado, en fraccion de su diametro.
    pub margen: f32,
    /// Si la IA no ve el iris, el ojo se da por cerrado.
    pub juez: bool,
}

impl Default for Ia {
    fn default() -> Self {
        Self { modelo: String::new(), usar: false, margen: 0.15, juez: true }
    }
}

impl Default for Camara {
    fn default() -> Self {
        // siev.db: camera_id 2, 640x360 @ 210, brightness 4, contrast 34
        Self {
            nombre: String::new(),
            ancho: 640,
            alto: 360,
            fps: 210,
            brillo: 4,
            contraste: 34.0,
            mostrar_mascaras: false,
            sensor: BTreeMap::new(),
        }
    }
}

impl Default for Ojos {
    fn default() -> Self {
        // siev.db: threshold_right 61, threshold_left 16, ROI ajustado por ojo.
        // Ojo derecho: temporal < nasal (ver [H-01]); el izquierdo al reves.
        Self {
            auto_od: true,
            auto_oi: true,
            umbral_od: 61,
            umbral_oi: 16,
            roi_od: Roi { top: 0.19, bottom: 0.67, nasal: 0.91, temporal: 0.16 },
            roi_oi: Roi { top: 0.17, bottom: 0.68, nasal: 0.14, temporal: 0.86 },
            franja_nasal: 0.25,
            alto_ojo: 0.25,
        }
    }
}

impl Default for Detector {
    fn default() -> Self {
        Self {
            suavizado: 2.5,
            min_circularidad: 0.55,
            min_area: 30,
            max_area_ratio: 0.6,
            parpadeo: true,
            parpadeo_blanco: 0.60,
            tolerancia_perdida: 5,
            margen_velocidad: 2.0,
            aspecto_min: 0.4,
            aspecto_max: 2.5,
            quitar_reflejos: true,
            metodo_auto: MetodoAuto::Region,
        }
    }
}

impl Default for Analisis {
    fn default() -> Self {
        Self { amplitud_min: 0.5, ventana_s: 10.0, espejar_h: false }
    }
}

/// `~/.config/siev-vng` (o `$XDG_CONFIG_HOME/siev-vng`).
pub fn dir_config() -> PathBuf {
    let base = std::env::var_os("XDG_CONFIG_HOME")
        .map(PathBuf::from)
        .or_else(|| std::env::var_os("HOME").map(|h| PathBuf::from(h).join(".config")))
        .unwrap_or_else(|| PathBuf::from("."));
    base.join("siev-vng")
}

impl Config {
    fn ruta() -> PathBuf {
        dir_config().join("config.json")
    }

    pub fn cargar() -> Self {
        let mut cfg: Self = std::fs::read_to_string(Self::ruta())
            .ok()
            .and_then(|s| serde_json::from_str(&s).ok())
            .unwrap_or_default();
        // Sin modelo configurado: usar el de iris si esta disponible.
        if cfg.ia.modelo.is_empty() {
            if let Some(m) = buscar_modelo() {
                cfg.ia.modelo = m;
                cfg.ia.usar = true;
            }
        }
        cfg
    }

    pub fn guardar(&self) -> Result<(), String> {
        let ruta = Self::ruta();
        if let Some(dir) = ruta.parent() {
            std::fs::create_dir_all(dir).map_err(|e| e.to_string())?;
        }
        let json = serde_json::to_string_pretty(self).map_err(|e| e.to_string())?;
        std::fs::write(&ruta, json).map_err(|e| e.to_string())
    }

    /// Empuja TODA la configuracion al pipeline. Nada queda en el default del
    /// constructor: el de `manual_roi_right` deja una caja de 1 px ([H-01]).
    pub fn aplicar(&self, m: &NativeVideoManager) {
        let (c, o, d) = (&self.camara, &self.ojos, &self.detector);
        m.set_brightness(c.brillo);
        m.set_contrast(c.contraste);
        m.set_show_debug(c.mostrar_mascaras);

        // 0 = umbral automatico en el detector.
        m.set_thresholds(if o.auto_od { 0 } else { o.umbral_od }, if o.auto_oi { 0 } else { o.umbral_oi });
        let r = o.roi_od;
        m.set_manual_roi_right(r.top, r.bottom, r.nasal, r.temporal);
        let r = o.roi_oi;
        m.set_manual_roi_left(r.top, r.bottom, r.nasal, r.temporal);
        m.set_nose_width(o.franja_nasal);
        m.set_eye_height(o.alto_ojo);

        m.set_smooth(d.suavizado);
        m.set_min_circularity(d.min_circularidad);
        m.set_min_area(d.min_area);
        m.set_max_area_ratio(d.max_area_ratio);
        m.set_blink_detection(d.parpadeo);
        m.set_blink_white_ratio(d.parpadeo_blanco);
        m.set_lost_tolerance(d.tolerancia_perdida);
        m.set_velocity_margin_factor(d.margen_velocidad);
        m.set_aspect_ratio_min(d.aspecto_min);
        m.set_aspect_ratio_max(d.aspecto_max);
        m.set_detector_options(OpcionesDetector {
            quitar_reflejos: d.quitar_reflejos,
            umbral_valle: d.metodo_auto == MetodoAuto::Valle,
            umbral_semilla: d.metodo_auto != MetodoAuto::Percentil,
        });

        m.set_use_yolo(self.ia.usar && !self.ia.modelo.is_empty());
        m.set_ia_margin(self.ia.margen);
        m.set_ia_closed_eye_judge(self.ia.juez);
    }
}

impl Config {
    /// Lleva al sensor los controles guardados. Devuelve los errores.
    pub fn aplicar_sensor(&self, indice: u32) -> Vec<String> {
        // La exposicion manual debe fijarse antes que su tiempo.
        let mut orden: Vec<(&u32, &i64)> = self.camara.sensor.iter().collect();
        orden.sort_by_key(|(id, _)| **id != camara_hw::EXPOSICION_AUTO);
        orden
            .into_iter()
            .filter_map(|(id, v)| camara_hw::fijar(indice, *id, *v).err())
            .collect()
    }
}

/// Busca el detector de iris siev_iris_r01.onnx (no se versiona: licencia
/// AGPL de Ultralytics y 12 MB). Orden: `SIEV_MODELO`, `./models/`, y el
/// repositorio hermano `siev_vng_models` junto a este proyecto.
fn buscar_modelo() -> Option<String> {
    const NOMBRE: &str = "siev_iris_r01.onnx";
    let mut candidatos: Vec<PathBuf> = Vec::new();
    if let Some(m) = std::env::var_os("SIEV_MODELO") {
        candidatos.push(m.into());
    }
    candidatos.push(PathBuf::from("models").join(NOMBRE));
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            candidatos.push(dir.join("models").join(NOMBRE));
        }
    }
    // <proyectos>/Siev-vng/crates/siev-vng -> <proyectos>/siev_vng_models
    candidatos.push(PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../../siev_vng_models").join(NOMBRE));
    candidatos
        .into_iter()
        .find(|p| p.is_file())
        .and_then(|p| p.canonicalize().ok())
        .map(|p| p.display().to_string())
}
