//! Analisis de nistagmo en vivo: un `NystagmusAnalyzer` por ojo y por eje.
//!
//! Convencion de signos (la misma que deben usar los graficos, para que la
//! traza y las etiquetas coincidan):
//!   - Horizontal: positivo = derecha. `espejar_h` invierte el eje x de la
//!     imagen; depende de como la camara de la mascara ve al paciente.
//!   - Vertical: positivo = arriba. La imagen crece hacia abajo, asi que se
//!     invierte y siempre.
//!
//! El nistagmo se nombra por la fase rapida; la SPV (velocidad de fase lenta)
//! conserva su signo.

use std::collections::VecDeque;

use super::nystagmus::{NystagmusAnalyzer, NystagmusBeat};

/// Hueco temporal que corta la continuidad aunque no haya `None` de por medio
/// (cuadros perdidos por la camara).
const HUECO_MAX_S: f64 = 0.1;

/// Latidos guardados para el grafico de SPV de la sesion.
const MAX_HISTORIAL: usize = 20_000;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Ojo {
    Od,
    Oi,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Eje {
    H,
    V,
}

impl Ojo {
    pub const TODOS: [Ojo; 2] = [Ojo::Od, Ojo::Oi];
    fn idx(self) -> usize {
        self as usize
    }
    pub fn nombre(self) -> &'static str {
        match self {
            Ojo::Od => "OD",
            Ojo::Oi => "OI",
        }
    }
}

impl Eje {
    pub const TODOS: [Eje; 2] = [Eje::H, Eje::V];
    fn idx(self) -> usize {
        self as usize
    }
    pub fn nombre(self) -> &'static str {
        match self {
            Eje::H => "H",
            Eje::V => "V",
        }
    }
    /// Nombre de la direccion para una velocidad con signo, en esta convencion.
    pub fn direccion(self, velocidad: f64) -> &'static str {
        match (self, velocidad > 0.0) {
            (Eje::H, true) => "derecha",
            (Eje::H, false) => "izquierda",
            (Eje::V, true) => "arriba",
            (Eje::V, false) => "abajo",
        }
    }
}

#[derive(Clone, Debug)]
pub struct LatidoVivo {
    pub ojo: Ojo,
    pub eje: Eje,
    /// Direccion de la fase rapida (nombre del nistagmo).
    pub direccion: &'static str,
    pub beat: NystagmusBeat,
}

#[derive(Clone, Debug, Default)]
pub struct Resumen {
    pub latidos_total: usize,
    pub latidos_ventana: usize,
    /// Latidos por segundo en la ventana.
    pub frecuencia_hz: f64,
    /// Media de |SPV| en la ventana.
    pub spv_abs: f64,
    /// Direccion de fase rapida mayoritaria en la ventana (>= 3 latidos y >= 70 %).
    pub direccion: Option<&'static str>,
}

pub struct LiveNystagmus {
    analizadores: [[NystagmusAnalyzer; 2]; 2], // [ojo][eje]
    ultimo_t: [Option<f64>; 2],                // por ojo
    min_amplitud: f64,
    pub ventana_s: f64,
    pub espejar_h: bool,
    /// La entrada ya viene en grados con la convencion de signos aplicada
    /// (calibracion contra estimulos): no espejar ni invertir.
    convencion_fija: bool,
    historial: VecDeque<LatidoVivo>,
    totales: [[usize; 2]; 2],
    t_actual: f64,
}

impl LiveNystagmus {
    pub fn new(min_amplitud: f64) -> Self {
        let nuevo = || NystagmusAnalyzer::new(min_amplitud);
        Self {
            analizadores: [[nuevo(), nuevo()], [nuevo(), nuevo()]],
            ultimo_t: [None, None],
            min_amplitud,
            ventana_s: 10.0,
            espejar_h: false,
            convencion_fija: false,
            historial: VecDeque::new(),
            totales: [[0; 2]; 2],
            t_actual: 0.0,
        }
    }

    pub fn min_amplitud(&self) -> f64 {
        self.min_amplitud
    }

    pub fn set_min_amplitud(&mut self, v: f64) {
        self.min_amplitud = v;
        for fila in &mut self.analizadores {
            for a in fila {
                a.set_min_amplitude(v);
            }
        }
    }

    /// Lleva una posicion del procesador (centrada, x derecha / y abajo) a la
    /// convencion de este modulo.
    pub fn a_convencion(&self, p: [f64; 2]) -> [f64; 2] {
        if self.convencion_fija {
            return p;
        }
        let x = if self.espejar_h { -p[0] } else { p[0] };
        [x, -p[1]]
    }

    /// Cambiar el espejo invalida lo acumulado: las direcciones cambiarian de nombre.
    pub fn set_espejar_h(&mut self, v: bool) {
        if v != self.espejar_h {
            self.espejar_h = v;
            self.reiniciar();
        }
    }

    /// Ver `convencion_fija`. Cambiarla reinicia el analisis.
    pub fn set_convencion_fija(&mut self, v: bool) {
        if v != self.convencion_fija {
            self.convencion_fija = v;
            self.reiniciar();
        }
    }

    pub fn reiniciar(&mut self) {
        for fila in &mut self.analizadores {
            for a in fila {
                a.reset();
            }
        }
        self.ultimo_t = [None, None];
        self.historial.clear();
        self.totales = [[0; 2]; 2];
        self.t_actual = 0.0;
    }

    /// Alimenta una muestra (t en segundos, relativo al inicio). Devuelve los
    /// latidos completados en esta muestra.
    pub fn push(&mut self, t: f64, od: Option<[f64; 2]>, oi: Option<[f64; 2]>) -> Vec<LatidoVivo> {
        self.t_actual = t;
        let mut nuevos = Vec::new();
        for (ojo, pos) in [(Ojo::Od, od), (Ojo::Oi, oi)] {
            let o = ojo.idx();
            let Some(p) = pos else {
                // Parpadeo o perdida: un latido no puede atravesar el hueco.
                if self.ultimo_t[o].take().is_some() {
                    for a in &mut self.analizadores[o] {
                        a.break_continuity();
                    }
                }
                continue;
            };
            if self.ultimo_t[o].is_some_and(|t0| t - t0 > HUECO_MAX_S) {
                for a in &mut self.analizadores[o] {
                    a.break_continuity();
                }
            }
            self.ultimo_t[o] = Some(t);

            let c = self.a_convencion(p);
            for eje in Eje::TODOS {
                let e = eje.idx();
                if let Some(beat) = self.analizadores[o][e].push_sample(t, c[e]) {
                    self.totales[o][e] += 1;
                    nuevos.push(LatidoVivo { ojo, eje, direccion: eje.direccion(beat.fast_velocity), beat });
                }
            }
        }
        for l in &nuevos {
            self.historial.push_back(l.clone());
        }
        while self.historial.len() > MAX_HISTORIAL {
            self.historial.pop_front();
        }
        nuevos
    }

    /// Todos los latidos de la sesion (acotado a los ultimos `MAX_HISTORIAL`).
    pub fn historial(&self) -> impl Iterator<Item = &LatidoVivo> {
        self.historial.iter()
    }

    pub fn resumen(&self, ojo: Ojo, eje: Eje) -> Resumen {
        let desde = self.t_actual - self.ventana_s;
        let en_ventana: Vec<&LatidoVivo> = self
            .historial
            .iter()
            .rev()
            .take_while(|l| l.beat.fast_end_time.max(l.beat.slow_end_time) >= desde)
            .filter(|l| l.ojo == ojo && l.eje == eje)
            .collect();

        let n = en_ventana.len();
        let mut r = Resumen {
            latidos_total: self.totales[ojo.idx()][eje.idx()],
            latidos_ventana: n,
            ..Default::default()
        };
        if n == 0 {
            return r;
        }
        r.frecuencia_hz = n as f64 / self.ventana_s;
        r.spv_abs = en_ventana.iter().map(|l| l.beat.slow_velocity.abs()).sum::<f64>() / n as f64;

        let positivos = en_ventana.iter().filter(|l| l.beat.fast_velocity > 0.0).count();
        let mayoria = positivos.max(n - positivos);
        if n >= 3 && mayoria as f64 >= 0.7 * n as f64 {
            r.direccion = Some(eje.direccion(if positivos * 2 >= n { 1.0 } else { -1.0 }));
        }
        r
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Diente de sierra en coordenadas de IMAGEN (x derecha, y abajo).
    fn sierra(n: usize, lenta: f64, rapida: f64) -> Vec<(f64, f64)> {
        let (fs, dt) = (200.0, 1.0 / 200.0);
        let (mut t, mut x, mut v) = (0.0, 0.0, Vec::new());
        for _ in 0..n {
            for _ in 0..(1.0 * fs) as usize {
                v.push((t, x));
                x += lenta * dt;
                t += dt;
            }
            for _ in 0..(0.05 * fs) as usize {
                v.push((t, x));
                x += rapida * dt;
                t += dt;
            }
        }
        v
    }

    #[test]
    fn horizontal_izquierda_y_vertical_invertido() {
        let mut live = LiveNystagmus::new(0.5);
        // Lenta a la derecha, rapida a la izquierda -> nistagmo "izquierda" en H.
        // En y (imagen) la misma forma: lenta hacia abajo, rapida hacia arriba
        // -> nistagmo "arriba" en V.
        for (t, p) in sierra(10, 5.0, -100.0) {
            live.push(t, Some([p, p]), None);
        }
        let h = live.resumen(Ojo::Od, Eje::H);
        let v = live.resumen(Ojo::Od, Eje::V);
        assert!(h.latidos_total >= 8 && h.latidos_total <= 10, "{}", h.latidos_total);
        assert_eq!(h.direccion, Some("izquierda"));
        assert_eq!(v.direccion, Some("arriba"));
        assert!((h.spv_abs - 5.0).abs() < 1.5, "spv {}", h.spv_abs);
        assert_eq!(live.resumen(Ojo::Oi, Eje::H).latidos_total, 0);
    }

    #[test]
    fn espejo_invierte_direccion_horizontal() {
        let mut live = LiveNystagmus::new(0.5);
        live.set_espejar_h(true);
        for (t, p) in sierra(6, 5.0, -100.0) {
            live.push(t, Some([p, 0.0]), None);
        }
        assert_eq!(live.resumen(Ojo::Od, Eje::H).direccion, Some("derecha"));
    }

    #[test]
    fn parpadeo_corta_latidos() {
        let mut live = LiveNystagmus::new(0.5);
        let datos = sierra(6, 5.0, -100.0);
        let mut con_huecos = 0;
        for (i, (t, p)) in datos.iter().enumerate() {
            // Hueco a mitad de cada fase lenta: ningun latido completo sobrevive.
            let hueco = (i % 210) == 100;
            con_huecos += live.push(*t, if hueco { None } else { Some([*p, 0.0]) }, None).len();
        }
        assert!(con_huecos <= 1, "latidos atravesando parpadeos: {con_huecos}");
    }
}
