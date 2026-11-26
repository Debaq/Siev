//! Andamiaje de la Fase 1': fuente de cuadros desde disco y tap de traza.
//!
//! ESTO ES TEMPORAL. Se elimina en la Fase 4, cuando `FrameSource` entra en
//! `vng-io` con su forma definitiva, y en la Fase 5, cuando la salida JSONL
//! estructurada reemplaza a `TraceWriter`.
//!
//! Existe por un motivo unico: poder pasar una secuencia determinista por el
//! bucle de captura REAL, sin duplicar ni una linea de la logica del detector,
//! para fijar un patron de referencia de tolerancia cero antes de reorganizar.
//!
//! Reglas que cumple:
//!   - El tap se invoca FUERA de la ventana cronometrada por `start_proc`.
//!   - El estado del tracker arranca limpio: `start_capture` declara sus
//!     variables de estado antes del bucle, de modo que cada corrida parte de
//!     `last_pupil = None`, `velocity = (0,0)`, `lost_count = 0`,
//!     `last_threshold = 40`.
//!   - El timestamp es sintetico y equiespaciado: sin el, `dt` del Kalman
//!     dependeria del reloj de pared y la traza no seria reproducible.

use std::fs;
use std::io::{BufWriter, Write};
use std::path::{Path, PathBuf};
use image::GrayImage;

/// Secuencia de archivos PGM binarios (P5, 8 bits) leidos en orden alfabetico.
///
/// Se usa un lector propio en vez de `image::open` a proposito: garantiza que
/// los bytes del archivo llegan al pipeline sin pasar por ninguna conversion de
/// color. Cualquier coeficiente de luminancia intermedio introduciria una
/// diferencia de ENTRADA que luego se confundiria con diferencia de algoritmo.
pub struct PgmSequence {
    files: Vec<PathBuf>,
    /// Clip MJPEG: cuadros JPEG tal como los entrega la camara (se decodifican
    /// en el pipeline igual que en vivo). Vacio = secuencia PGM.
    jpegs: Vec<Vec<u8>>,
    index: usize,
    dt: f64,
    t0: f64,
    pub width: u32,
    pub height: u32,
}

impl PgmSequence {
    /// `fps` define el paso de tiempo sintetico entre cuadros consecutivos.
    pub fn open(dir: &Path, fps: f64) -> Result<Self, String> {
        let mut files: Vec<PathBuf> = fs::read_dir(dir)
            .map_err(|e| format!("No se pudo leer {}: {}", dir.display(), e))?
            .filter_map(|e| e.ok().map(|e| e.path()))
            .filter(|p| p.extension().and_then(|x| x.to_str()) == Some("pgm"))
            .collect();

        if files.is_empty() {
            return Err(format!("Sin archivos .pgm en {}", dir.display()));
        }
        files.sort();

        let (width, height, _) = read_pgm(&files[0])?;

        Ok(Self {
            files,
            jpegs: Vec::new(),
            index: 0,
            dt: 1.0 / fps,
            t0: 1_700_000_000.0, // epoch fijo: la traza no debe depender del reloj
            width,
            height,
        })
    }

    /// Clip `.mjpeg` (JPEG concatenados, p. ej. `ffmpeg -i crudo.mkv -c:v copy
    /// -f mjpeg clip.mjpeg`). Se usa para medir el equipo con la decodificacion
    /// incluida, como con la camara real.
    pub fn open_mjpeg(path: &Path, fps: f64) -> Result<Self, String> {
        let datos = fs::read(path).map_err(|e| format!("No se pudo leer {}: {}", path.display(), e))?;
        let mut jpegs = Vec::new();
        let mut i = 0;
        while i + 1 < datos.len() {
            if datos[i] == 0xFF && datos[i + 1] == 0xD8 {
                // fin del cuadro: el primer EOI (FF D9); en MJPEG de camara no hay miniaturas
                let fin = datos[i + 2..].windows(2).position(|w| w == [0xFF, 0xD9]).map(|p| i + 2 + p + 2);
                let Some(fin) = fin else { break };
                jpegs.push(datos[i..fin].to_vec());
                i = fin;
            } else {
                i += 1;
            }
        }
        let primero = jpegs.first().ok_or_else(|| format!("Sin cuadros JPEG en {}", path.display()))?;
        let mut dec = zune_jpeg::JpegDecoder::new(primero.as_slice());
        dec.decode_headers().map_err(|e| format!("JPEG ilegible: {e:?}"))?;
        let (w, h) = dec.dimensions().ok_or("JPEG sin dimensiones")?;
        Ok(Self {
            files: Vec::new(),
            jpegs,
            index: 0,
            dt: 1.0 / fps,
            t0: 1_700_000_000.0,
            width: w as u32,
            height: h as u32,
        })
    }

    pub fn len(&self) -> usize {
        self.files.len().max(self.jpegs.len())
    }

    pub fn es_jpeg(&self) -> bool {
        !self.jpegs.is_empty()
    }

    /// Siguiente cuadro JPEG del clip y su timestamp sintetico.
    pub fn next_jpeg(&mut self) -> Option<(Vec<u8>, f64)> {
        let b = self.jpegs.get(self.index)?.clone();
        let t = self.t0 + self.index as f64 * self.dt;
        self.index += 1;
        Some((b, t))
    }

    /// Devuelve el siguiente cuadro y su timestamp sintetico, o `None` al agotarse.
    pub fn next_frame(&mut self) -> Option<(GrayImage, f64)> {
        if self.index >= self.files.len() {
            return None;
        }
        let path = &self.files[self.index];
        let (w, h, data) = match read_pgm(path) {
            Ok(v) => v,
            Err(e) => {
                eprintln!("[TRACE] PGM ilegible {}: {}", path.display(), e);
                return None;
            }
        };
        if w != self.width || h != self.height {
            eprintln!(
                "[TRACE] {} mide {}x{}, se esperaba {}x{}",
                path.display(), w, h, self.width, self.height
            );
            return None;
        }
        let img = GrayImage::from_vec(w, h, data)?;
        let t = self.t0 + self.index as f64 * self.dt;
        self.index += 1;
        Some((img, t))
    }
}

/// Lee un PGM binario P5 de 8 bits. Devuelve (ancho, alto, pixeles).
fn read_pgm(path: &Path) -> Result<(u32, u32, Vec<u8>), String> {
    let raw = fs::read(path).map_err(|e| format!("{}: {}", path.display(), e))?;

    if raw.len() < 2 || &raw[0..2] != b"P5" {
        return Err("no es un PGM binario (P5)".to_string());
    }

    // Cabecera: tres enteros (ancho, alto, maxval), con comentarios '#' y
    // espacios en blanco arbitrarios entre ellos.
    let mut pos = 2usize;
    let mut fields = [0u32; 3];

    for field in fields.iter_mut() {
        // saltar espacios y comentarios
        loop {
            while pos < raw.len() && raw[pos].is_ascii_whitespace() {
                pos += 1;
            }
            if pos < raw.len() && raw[pos] == b'#' {
                while pos < raw.len() && raw[pos] != b'\n' {
                    pos += 1;
                }
            } else {
                break;
            }
        }
        let start = pos;
        while pos < raw.len() && raw[pos].is_ascii_digit() {
            pos += 1;
        }
        if start == pos {
            return Err("cabecera PGM incompleta".to_string());
        }
        *field = std::str::from_utf8(&raw[start..pos])
            .map_err(|_| "cabecera PGM no ASCII".to_string())?
            .parse()
            .map_err(|_| "entero invalido en cabecera PGM".to_string())?;
    }

    let (w, h, maxval) = (fields[0], fields[1], fields[2]);
    if maxval != 255 {
        return Err(format!("maxval {} no soportado (se requiere 255)", maxval));
    }

    // Exactamente un byte de separacion tras maxval
    pos += 1;

    let expected = (w as usize) * (h as usize);
    if raw.len() < pos + expected {
        return Err(format!(
            "datos truncados: {} bytes disponibles, {} esperados",
            raw.len().saturating_sub(pos), expected
        ));
    }

    Ok((w, h, raw[pos..pos + expected].to_vec()))
}

/// Una linea de traza por ojo y por cuadro.
///
/// Campos en el orden acordado: salida cruda del detector (pre-Kalman), estado
/// del tracker TRAS la actualizacion, y posicion post-Kalman.
#[derive(Debug, Clone)]
pub struct TraceRecord {
    pub frame_idx: u64,
    pub eye: &'static str,
    /// "detected" | "lost" | "blink" | "none"
    pub status: &'static str,
    // --- crudo, antes del Kalman ---
    pub raw_x: Option<f32>,
    pub raw_y: Option<f32>,
    pub raw_radius: Option<f32>,
    pub raw_confidence: Option<f32>,
    // --- estado del tracker tras la actualizacion ---
    pub trk_x: Option<f32>,
    pub trk_y: Option<f32>,
    pub trk_radius_smoothed: Option<f32>,
    pub velocity_x: f32,
    pub velocity_y: f32,
    pub lost_count: u32,
    pub threshold_used: u8,
    pub search_box: [u32; 4],
    // --- post-Kalman ---
    pub filtered_x: Option<f64>,
    pub filtered_y: Option<f64>,
}

/// Escritor JSONL. Formatea los flotantes con `{:?}`, que en Rust produce la
/// representacion decimal mas corta que round-trippea al mismo bit: dos
/// corridas identicas dan bytes identicos, y la comparacion textual equivale a
/// comparacion bit a bit.
pub struct TraceWriter {
    out: BufWriter<fs::File>,
}

impl TraceWriter {
    pub fn create(path: &Path) -> Result<Self, String> {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent).map_err(|e| format!("{}: {}", parent.display(), e))?;
        }
        let f = fs::File::create(path).map_err(|e| format!("{}: {}", path.display(), e))?;
        Ok(Self { out: BufWriter::new(f) })
    }

    pub fn write(&mut self, r: &TraceRecord) {
        fn of(v: Option<f32>) -> String {
            match v { Some(x) => format!("{:?}", x), None => "null".to_string() }
        }
        fn od(v: Option<f64>) -> String {
            match v { Some(x) => format!("{:?}", x), None => "null".to_string() }
        }

        let line = format!(
            concat!(
                r#"{{"frame_idx":{},"eye":"{}","status":"{}","#,
                r#""raw_x":{},"raw_y":{},"raw_radius":{},"raw_confidence":{},"#,
                r#""trk_x":{},"trk_y":{},"trk_radius_smoothed":{},"#,
                r#""velocity_x":{:?},"velocity_y":{:?},"lost_count":{},"threshold_used":{},"#,
                r#""search_box":[{},{},{},{}],"#,
                r#""filtered_x":{},"filtered_y":{}}}"#
            ),
            r.frame_idx, r.eye, r.status,
            of(r.raw_x), of(r.raw_y), of(r.raw_radius), of(r.raw_confidence),
            of(r.trk_x), of(r.trk_y), of(r.trk_radius_smoothed),
            r.velocity_x, r.velocity_y, r.lost_count, r.threshold_used,
            r.search_box[0], r.search_box[1], r.search_box[2], r.search_box[3],
            od(r.filtered_x), od(r.filtered_y),
        );
        let _ = writeln!(self.out, "{}", line);
    }

    pub fn finish(mut self) {
        let _ = self.out.flush();
    }
}
