//! Calibracion px -> grados contra estimulos en el monitor del paciente.
//!
//! Tres niveles, de lo mas fijo a lo mas variable:
//!   - Mascara: la escala de fabrica sale del historial de calibraciones
//!     hechas con esa misma camara (mediana de las ultimas). Nada que medir.
//!   - Estacion (una vez por sala): monitor, cm por px medido con una regla
//!     en pantalla y distancia de los ojos del paciente a la pantalla.
//!   - Paciente: escala opcional (puntos) y cero obligatorio en cada prueba.
//!
//! Convencion de los angulos: + derecha del paciente, + arriba. El paciente
//! mira la pantalla de frente, asi que su derecha es la derecha de la pantalla.

use std::path::PathBuf;
use std::time::{Duration, Instant};

use serde::{Deserialize, Serialize};

use crate::config::dir_config;

/// Largo real de la barra de la regla en pantalla.
pub const LARGO_REGLA_CM: f64 = 20.0;
/// Tiempo para que el paciente lleve la mirada al punto antes de medir.
const FIJAR: Duration = Duration::from_millis(1200);
/// Muestreo minimo y maximo por punto (se alarga si hay parpadeos).
const MUESTREO_MIN: Duration = Duration::from_millis(800);
const MUESTREO_MAX: Duration = Duration::from_millis(3000);
/// Muestras validas pedidas por ojo y punto (~0,2 s a 200 Hz).
const MUESTRAS_MIN: usize = 40;
/// Por debajo de esto el punto no cuenta para ese ojo.
const MUESTRAS_UTILES: usize = 15;
/// Duracion de la toma del cero al iniciar una prueba.
pub const DURACION_CERO: Duration = Duration::from_millis(1500);
/// Calibraciones recientes que forman la escala por defecto.
const N_DEFECTO: usize = 10;
const MAX_HISTORIAL: usize = 200;

// -------------------------------------------------------------------
// Estacion
// -------------------------------------------------------------------

#[derive(Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct Estacion {
    /// Indice del monitor del paciente (orden del sistema, 0 = primero).
    pub monitor: usize,
    /// Tamaño fisico de un px del monitor del paciente; 0 = sin medir.
    pub cm_por_px: f64,
    /// Distancia de los ojos del paciente a la pantalla.
    pub distancia_cm: f64,
    /// Angulo de los puntos laterales y verticales, en grados.
    pub amplitud_h: f64,
    pub amplitud_v: f64,
}

impl Default for Estacion {
    fn default() -> Self {
        Self { monitor: 1, cm_por_px: 0.0, distancia_cm: 100.0, amplitud_h: 10.0, amplitud_v: 8.0 }
    }
}

impl Estacion {
    pub fn medida(&self) -> bool {
        self.cm_por_px > 0.0 && self.distancia_cm > 0.0
    }

    /// Posicion en px (respecto del centro de la pantalla, y hacia abajo) de
    /// un punto visto con el angulo `ang` (grados, + derecha, + arriba).
    pub fn a_px(&self, ang: [f64; 2]) -> [f64; 2] {
        let d = self.distancia_cm;
        [d * ang[0].to_radians().tan() / self.cm_por_px, -d * ang[1].to_radians().tan() / self.cm_por_px]
    }

    /// Mayor angulo que cabe en una pantalla de `tam_px`, dejando margen.
    pub fn angulo_max(&self, tam_px: [f64; 2]) -> [f64; 2] {
        let f = |px: f64| (0.45 * px * self.cm_por_px / self.distancia_cm).atan().to_degrees();
        [f(tam_px[0]), f(tam_px[1])]
    }
}

// -------------------------------------------------------------------
// Puntos y medidas
// -------------------------------------------------------------------

#[derive(Clone, Copy, Debug)]
pub struct Objetivo {
    pub nombre: &'static str,
    /// Grados, + derecha, + arriba.
    pub ang: [f64; 2],
}

/// Centro, derecha, izquierda, arriba, abajo y centro otra vez (para ver si
/// la cabeza o la mascara se movio). Los angulos se recortan a la pantalla.
pub fn secuencia(est: &Estacion, tam_px: [f64; 2]) -> Vec<Objetivo> {
    let max = est.angulo_max(tam_px);
    let (h, v) = (est.amplitud_h.min(max[0]), est.amplitud_v.min(max[1]));
    vec![
        Objetivo { nombre: "Centro", ang: [0.0, 0.0] },
        Objetivo { nombre: "Derecha", ang: [h, 0.0] },
        Objetivo { nombre: "Izquierda", ang: [-h, 0.0] },
        Objetivo { nombre: "Arriba", ang: [0.0, v] },
        Objetivo { nombre: "Abajo", ang: [0.0, -v] },
        Objetivo { nombre: "Centro", ang: [0.0, 0.0] },
    ]
}

#[derive(Clone, Debug)]
pub struct Medida {
    pub objetivo: Objetivo,
    /// Mediana de la posicion cruda (px de imagen); None = sin datos.
    pub od: Option<[f64; 2]>,
    pub oi: Option<[f64; 2]>,
}

pub fn mediana(v: &mut [f64]) -> Option<f64> {
    if v.is_empty() {
        return None;
    }
    v.sort_by(|a, b| a.total_cmp(b));
    let n = v.len();
    Some(if n % 2 == 1 { v[n / 2] } else { 0.5 * (v[n / 2 - 1] + v[n / 2]) })
}

pub fn mediana_2d(m: &[[f64; 2]], minimo: usize) -> Option<[f64; 2]> {
    if m.len() < minimo {
        return None;
    }
    let mut x: Vec<f64> = m.iter().map(|p| p[0]).collect();
    let mut y: Vec<f64> = m.iter().map(|p| p[1]).collect();
    Some([mediana(&mut x)?, mediana(&mut y)?])
}

// -------------------------------------------------------------------
// Ajuste
// -------------------------------------------------------------------

#[derive(Clone, Copy, Debug, Serialize, Deserialize)]
pub struct AjusteOjo {
    /// Grados por px, con signo: `grados = escala * (px - centro)`.
    pub escala: [f64; 2],
    /// Cero en px de imagen.
    pub centro: [f64; 2],
    /// Error cuadratico medio en los puntos, en grados.
    pub error_deg: f64,
    /// Escala del lado derecho / izquierdo (y arriba / abajo). 1 = simetrico.
    pub simetria: [f64; 2],
    /// Distancia entre el primer y el ultimo centro, en grados.
    pub deriva_deg: f64,
}

#[derive(Clone, Debug)]
pub struct Resultado {
    pub od: Option<AjusteOjo>,
    pub oi: Option<AjusteOjo>,
    /// El ojo indicado usa la escala del otro (no se pudo ajustar).
    pub copiado: Option<&'static str>,
    pub avisos: Vec<String>,
}

impl Resultado {
    pub fn usable(&self) -> bool {
        self.od.is_some() && self.oi.is_some()
    }
}

/// Recta `ang = b * px + a` por minimos cuadrados. Devuelve (b, a).
fn recta(pts: &[(f64, f64)]) -> Option<(f64, f64)> {
    let n = pts.len() as f64;
    if pts.len() < 2 {
        return None;
    }
    let mx = pts.iter().map(|p| p.0).sum::<f64>() / n;
    let my = pts.iter().map(|p| p.1).sum::<f64>() / n;
    let sxx: f64 = pts.iter().map(|p| (p.0 - mx).powi(2)).sum();
    let sxy: f64 = pts.iter().map(|p| (p.0 - mx) * (p.1 - my)).sum();
    // Los angulos deben ser distintos y la pupila debe haberse movido.
    let angs_distintos = pts.iter().any(|p| (p.1 - pts[0].1).abs() > 1e-9);
    if !angs_distintos || sxx < 1e-6 {
        return None;
    }
    let b = sxy / sxx;
    Some((b, my - b * mx))
}

fn ajustar_ojo(medidas: &[(Objetivo, [f64; 2])]) -> Option<AjusteOjo> {
    let mut esc = [0.0; 2];
    let mut cen = [0.0; 2];
    for k in 0..2 {
        // Eje horizontal: puntos con angulo vertical 0, y viceversa.
        let pts: Vec<(f64, f64)> =
            medidas.iter().filter(|(o, _)| o.ang[1 - k].abs() < 1e-9).map(|(o, p)| (p[k], o.ang[k])).collect();
        let (b, a) = recta(&pts)?;
        esc[k] = b;
        cen[k] = -a / b;
    }
    let grados = |p: [f64; 2]| [esc[0] * (p[0] - cen[0]), esc[1] * (p[1] - cen[1])];

    let n = medidas.len() as f64;
    let error_deg = (medidas
        .iter()
        .map(|(o, p)| {
            let g = grados(*p);
            (g[0] - o.ang[0]).powi(2) + (g[1] - o.ang[1]).powi(2)
        })
        .sum::<f64>()
        / n)
        .sqrt();

    // Simetria: escala de cada lado por separado, respecto del centro.
    let lado = |k: usize, positivo: bool| -> Option<f64> {
        let (o, p) = medidas.iter().find(|(o, _)| o.ang[1 - k].abs() < 1e-9 && (o.ang[k] > 0.0) == positivo && o.ang[k] != 0.0)?;
        let d = p[k] - cen[k];
        (d.abs() > 1e-6).then(|| o.ang[k] / d)
    };
    let mut simetria = [1.0; 2];
    for (k, s) in simetria.iter_mut().enumerate() {
        if let (Some(a), Some(b)) = (lado(k, true), lado(k, false)) {
            *s = (a / b).abs();
        }
    }

    let centros: Vec<[f64; 2]> = medidas.iter().filter(|(o, _)| o.ang == [0.0, 0.0]).map(|(_, p)| grados(*p)).collect();
    let deriva_deg = match (centros.first(), centros.last()) {
        (Some(a), Some(b)) if centros.len() >= 2 => ((a[0] - b[0]).powi(2) + (a[1] - b[1]).powi(2)).sqrt(),
        _ => 0.0,
    };

    Some(AjusteOjo { escala: esc, centro: cen, error_deg, simetria, deriva_deg })
}

pub fn ajustar(medidas: &[Medida]) -> Resultado {
    let por_ojo = |f: fn(&Medida) -> Option<[f64; 2]>| -> Vec<(Objetivo, [f64; 2])> {
        medidas.iter().filter_map(|m| f(m).map(|p| (m.objetivo, p))).collect()
    };
    let mut od = ajustar_ojo(&por_ojo(|m| m.od));
    let mut oi = ajustar_ojo(&por_ojo(|m| m.oi));
    let mut avisos = Vec::new();
    let mut copiado = None;

    // Un ojo sin ajuste (cerrado, protesis, pupila perdida): usa la escala
    // del otro y su propio cero si al menos se vio en el centro.
    let centro_de = |f: fn(&Medida) -> Option<[f64; 2]>| {
        let c: Vec<[f64; 2]> = medidas.iter().filter(|m| m.objetivo.ang == [0.0, 0.0]).filter_map(f).collect();
        mediana_2d(&c, 1)
    };
    match (&od, &oi) {
        (Some(a), None) => {
            oi = centro_de(|m| m.oi).map(|c| AjusteOjo { centro: c, ..*a });
            copiado = Some("OI");
            avisos.push("No se pudo ajustar el OI: usa la escala del OD.".into());
        }
        (None, Some(a)) => {
            od = centro_de(|m| m.od).map(|c| AjusteOjo { centro: c, ..*a });
            copiado = Some("OD");
            avisos.push("No se pudo ajustar el OD: usa la escala del OI.".into());
        }
        (None, None) => avisos.push("Ningun ojo tuvo datos suficientes. Revisar la deteccion de pupila y repetir.".into()),
        _ => {}
    }

    for (nombre, a) in [("OD", &od), ("OI", &oi)] {
        let Some(a) = a else { continue };
        if copiado == Some(nombre) {
            continue;
        }
        if a.error_deg > 1.5 {
            avisos.push(format!("{nombre}: error de {:.1}° en los puntos. ¿El paciente miro cada punto?", a.error_deg));
        }
        for (k, eje) in ["horizontal", "vertical"].iter().enumerate() {
            let s = a.simetria[k];
            if !(0.75..=1.33).contains(&s) {
                avisos.push(format!("{nombre}: respuesta {eje} asimetrica ({:.0} % entre lados).", (s.max(1.0 / s) - 1.0) * 100.0));
            }
        }
        if a.deriva_deg > 1.5 {
            avisos.push(format!("{nombre}: el centro se corrio {:.1}° entre el inicio y el final. ¿Se movio la cabeza o la mascara?", a.deriva_deg));
        }
    }
    if let (Some(a), Some(b)) = (&od, &oi) {
        for (k, eje) in ["horizontal", "vertical"].iter().enumerate() {
            if a.escala[k].signum() != b.escala[k].signum() {
                avisos.push(format!("Los ojos se movieron en sentido contrario en el eje {eje}: calibracion invalida."));
            } else if copiado.is_none() {
                let r = (a.escala[k] / b.escala[k]).abs();
                if !(0.7..=1.43).contains(&r) {
                    avisos.push(format!("Escala {eje} muy distinta entre ojos ({:.0} %).", (r.max(1.0 / r) - 1.0) * 100.0));
                }
            }
        }
    }
    Resultado { od, oi, copiado, avisos }
}

// -------------------------------------------------------------------
// Asistente (maquina de estados de la toma de puntos)
// -------------------------------------------------------------------

pub enum Fase {
    /// Esperando que el paciente lleve la mirada al punto.
    Fijar,
    Muestreo,
}

pub struct Toma {
    pub objetivos: Vec<Objetivo>,
    pub i: usize,
    pub fase: Fase,
    pub inicio: Instant,
    od: Vec<[f64; 2]>,
    oi: Vec<[f64; 2]>,
    pub medidas: Vec<Medida>,
}

impl Toma {
    pub fn nueva(objetivos: Vec<Objetivo>) -> Self {
        Self { objetivos, i: 0, fase: Fase::Fijar, inicio: Instant::now(), od: Vec::new(), oi: Vec::new(), medidas: Vec::new() }
    }

    pub fn actual(&self) -> Option<Objetivo> {
        self.objetivos.get(self.i).copied()
    }

    /// Fraccion de avance de la fase actual (0..1), para animar el punto.
    pub fn avance_fase(&self) -> f32 {
        let total = match self.fase {
            Fase::Fijar => FIJAR,
            Fase::Muestreo => MUESTREO_MIN,
        };
        (self.inicio.elapsed().as_secs_f32() / total.as_secs_f32()).min(1.0)
    }

    pub fn muestras(&self) -> (usize, usize) {
        (self.od.len(), self.oi.len())
    }

    pub fn push(&mut self, od: Option<[f64; 2]>, oi: Option<[f64; 2]>) {
        if matches!(self.fase, Fase::Muestreo) {
            self.od.extend(od);
            self.oi.extend(oi);
        }
    }

    /// Avanza el reloj. Devuelve true cuando ya se midieron todos los puntos.
    pub fn tick(&mut self) -> bool {
        let Some(obj) = self.actual() else { return true };
        let t = self.inicio.elapsed();
        match self.fase {
            Fase::Fijar if t >= FIJAR => {
                self.fase = Fase::Muestreo;
                self.inicio = Instant::now();
                self.od.clear();
                self.oi.clear();
            }
            Fase::Muestreo => {
                let suficientes = self.od.len() >= MUESTRAS_MIN && self.oi.len() >= MUESTRAS_MIN;
                if (t >= MUESTREO_MIN && suficientes) || t >= MUESTREO_MAX {
                    self.medidas.push(Medida {
                        objetivo: obj,
                        od: mediana_2d(&self.od, MUESTRAS_UTILES),
                        oi: mediana_2d(&self.oi, MUESTRAS_UTILES),
                    });
                    self.i += 1;
                    self.fase = Fase::Fijar;
                    self.inicio = Instant::now();
                }
            }
            _ => {}
        }
        self.i >= self.objetivos.len()
    }
}

/// Toma del cero al iniciar una prueba: el paciente mira el centro.
pub struct TomaCero {
    pub inicio: Instant,
    od: Vec<[f64; 2]>,
    oi: Vec<[f64; 2]>,
}

impl TomaCero {
    pub fn nueva() -> Self {
        Self { inicio: Instant::now(), od: Vec::new(), oi: Vec::new() }
    }
    pub fn push(&mut self, od: Option<[f64; 2]>, oi: Option<[f64; 2]>) {
        // El primer tercio es tiempo para llevar la mirada al centro.
        if self.inicio.elapsed() > DURACION_CERO / 3 {
            self.od.extend(od);
            self.oi.extend(oi);
        }
    }
    pub fn terminada(&self) -> bool {
        self.inicio.elapsed() >= DURACION_CERO
    }
    /// Cero de cada ojo; None si ese ojo casi no se vio.
    pub fn resultado(&self) -> (Option<[f64; 2]>, Option<[f64; 2]>) {
        (mediana_2d(&self.od, MUESTRAS_UTILES), mediana_2d(&self.oi, MUESTRAS_UTILES))
    }
}

// -------------------------------------------------------------------
// Historial y escala por defecto
// -------------------------------------------------------------------

#[derive(Clone, Serialize, Deserialize)]
pub struct Registro {
    pub fecha_unix: u64,
    /// Perfil de mascara (hoy, el nombre de su camara).
    pub mascara: String,
    pub distancia_cm: f64,
    pub escala_od: [f64; 2],
    pub escala_oi: [f64; 2],
    pub error_od: f64,
    pub error_oi: f64,
    /// Un ojo uso la escala del otro: no entra en la escala por defecto.
    #[serde(default)]
    pub parcial: bool,
}

#[derive(Default, Serialize, Deserialize)]
pub struct Historial {
    pub registros: Vec<Registro>,
}

/// De donde sale la escala que se esta usando.
#[derive(Clone, PartialEq)]
pub enum Fuente {
    /// Sin escala: valores en px.
    Ninguna,
    /// Mediana de las ultimas `n` calibraciones de esta mascara.
    PorDefecto { n: usize },
    /// Calibrada con este paciente.
    Paciente { hora: String, error: f64 },
}

impl Historial {
    fn ruta() -> PathBuf {
        dir_config().join("calibraciones.json")
    }

    pub fn cargar() -> Self {
        std::fs::read_to_string(Self::ruta()).ok().and_then(|s| serde_json::from_str(&s).ok()).unwrap_or_default()
    }

    pub fn guardar(&self) -> Result<(), String> {
        let ruta = Self::ruta();
        if let Some(dir) = ruta.parent() {
            std::fs::create_dir_all(dir).map_err(|e| e.to_string())?;
        }
        std::fs::write(&ruta, serde_json::to_string_pretty(self).map_err(|e| e.to_string())?).map_err(|e| e.to_string())
    }

    pub fn agregar(&mut self, r: Registro) {
        self.registros.push(r);
        let sobra = self.registros.len().saturating_sub(MAX_HISTORIAL);
        self.registros.drain(..sobra);
    }

    /// Escala por defecto de una mascara: mediana, componente a componente,
    /// de sus ultimas calibraciones completas. Devuelve (od, oi, n).
    pub fn defecto(&self, mascara: &str) -> Option<([f64; 2], [f64; 2], usize)> {
        let recientes: Vec<&Registro> =
            self.registros.iter().rev().filter(|r| r.mascara == mascara && !r.parcial).take(N_DEFECTO).collect();
        if recientes.is_empty() {
            return None;
        }
        let med = |f: &dyn Fn(&Registro) -> f64| mediana(&mut recientes.iter().map(|r| f(r)).collect::<Vec<_>>()).unwrap_or(0.0);
        let od = [med(&|r| r.escala_od[0]), med(&|r| r.escala_od[1])];
        let oi = [med(&|r| r.escala_oi[0]), med(&|r| r.escala_oi[1])];
        Some((od, oi, recientes.len()))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Ojo sintetico: px = centro + ang / escala (+ ruido opcional).
    fn medidas(esc: [f64; 2], cen: [f64; 2], ruido: f64) -> Vec<Medida> {
        let est = Estacion { cm_por_px: 0.03, ..Default::default() };
        secuencia(&est, [1920.0, 1080.0])
            .into_iter()
            .enumerate()
            .map(|(i, o)| {
                let r = if i % 2 == 0 { ruido } else { -ruido };
                let p = [cen[0] + o.ang[0] / esc[0] + r, cen[1] + o.ang[1] / esc[1] - r];
                Medida { objetivo: o, od: Some(p), oi: Some([p[0] + 300.0, p[1]]) }
            })
            .collect()
    }

    #[test]
    fn recupera_escala_y_centro() {
        let r = ajustar(&medidas([0.4, -0.5], [160.0, 90.0], 0.0));
        let od = r.od.unwrap();
        assert!((od.escala[0] - 0.4).abs() < 1e-9 && (od.escala[1] + 0.5).abs() < 1e-9);
        assert!((od.centro[0] - 160.0).abs() < 1e-6 && (od.centro[1] - 90.0).abs() < 1e-6);
        assert!(od.error_deg < 1e-9);
        assert!((r.oi.unwrap().centro[0] - 460.0).abs() < 1e-6);
        assert!(r.avisos.is_empty(), "{:?}", r.avisos);
    }

    #[test]
    fn ojo_sin_datos_usa_la_escala_del_otro() {
        let mut m = medidas([0.4, -0.5], [160.0, 90.0], 0.0);
        for x in m.iter_mut().filter(|x| x.objetivo.ang != [0.0, 0.0]) {
            x.oi = None;
        }
        let r = ajustar(&m);
        assert_eq!(r.copiado, Some("OI"));
        let oi = r.oi.unwrap();
        assert_eq!(oi.escala, r.od.unwrap().escala);
        assert!((oi.centro[0] - 460.0).abs() < 1e-6);
    }

    #[test]
    fn avisa_si_los_ojos_van_en_sentido_contrario() {
        let mut m = medidas([0.4, -0.5], [160.0, 90.0], 0.0);
        for x in &mut m {
            let p = x.oi.unwrap();
            x.oi = Some([600.0 - p[0], p[1]]);
        }
        assert!(ajustar(&m).avisos.iter().any(|a| a.contains("sentido contrario")));
    }

    #[test]
    fn angulos_se_recortan_a_la_pantalla() {
        // A 200 cm, con 45 % de margen por lado: 1920 px * 0,03 cm -> ±7,4°
        // (pedidos 10°) y 1080 px -> ±4,2° (pedidos 8°).
        let est = Estacion { cm_por_px: 0.03, distancia_cm: 200.0, ..Default::default() };
        let s = secuencia(&est, [1920.0, 1080.0]);
        assert!((s[1].ang[0] - 7.38).abs() < 0.01, "{}", s[1].ang[0]);
        assert!((s[3].ang[1] - 4.17).abs() < 0.01, "{}", s[3].ang[1]);
        // A 100 cm la horizontal cabe entera.
        let est = Estacion { distancia_cm: 100.0, ..est };
        assert_eq!(secuencia(&est, [1920.0, 1080.0])[1].ang[0], 10.0);
    }

    #[test]
    fn defecto_es_mediana_de_la_misma_mascara() {
        let mut h = Historial::default();
        for (i, e) in [0.40, 0.42, 0.90, 0.41].into_iter().enumerate() {
            h.agregar(Registro {
                fecha_unix: i as u64,
                mascara: if e > 0.8 { "otra".into() } else { "USB GS CAM".into() },
                distancia_cm: 100.0,
                escala_od: [e, -e],
                escala_oi: [e, -e],
                error_od: 0.3,
                error_oi: 0.3,
                parcial: false,
            });
        }
        let (od, _, n) = h.defecto("USB GS CAM").unwrap();
        assert_eq!(n, 3);
        assert!((od[0] - 0.41).abs() < 1e-9);
        assert!(h.defecto("nada").is_none());
    }
}
