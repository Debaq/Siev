//! SIEV VNG — videonistagmografia en Rust puro (eframe/egui + egui_plot).
//!
//! Pantalla clinica: video de ambos ojos a lo ancho, resultado por ojo a su
//! lado y trazados abajo. Los ajustes tecnicos viven en la ventana de
//! Configuracion (secciones desplegables) y se guardan en disco.

mod config;
mod tema;

use std::collections::VecDeque;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use eframe::egui::{self, Color32, ColorImage, CornerRadius, RichText, Stroke, TextureHandle, TextureOptions};
use egui_plot::{HLine, Legend, Line, Plot, PlotPoints, Points};

use config::{Config, MetodoAuto, Roi};
use siev_tracking::bus::{BusReceiver, EventBus, TrackEvent};
use siev_tracking::math::processor::EyeProcessor;
use siev_tracking::storage::SessionRecorder;
use siev_tracking::vng::camara_hw::{self, ControlHw};
use siev_tracking::vng::live::{Eje, LiveNystagmus, Ojo, Resumen};
use siev_tracking::vng::native_video::{self, CameraFormatInfo, CameraInfo, NativeVideoManager};
use siev_tracking::vng::trace::PgmSequence;
use tema::{ACENTO, AMBAR, LIENZO_VIDEO, OD, OI, ROJO, TEXTO_SUAVE, VERDE};

/// Ventana visible de los trazados, en segundos.
const VENTANA_TRAZO_S: f64 = 10.0;
/// Ventana para el indicador de calidad de seguimiento.
const VENTANA_CALIDAD_S: f64 = 2.0;
/// Espera entre intentos de conexion automatica de la camara.
const REINTENTO_CAMARA: Duration = Duration::from_secs(2);

fn main() -> eframe::Result {
    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_title("SIEV — Videonistagmografia")
            .with_inner_size([1440.0, 920.0])
            .with_min_inner_size([1100.0, 700.0]),
        ..Default::default()
    };
    eframe::run_native("siev-vng", options, Box::new(|cc| Ok(Box::new(VngApp::new(cc)))))
}

#[derive(Clone, Copy)]
struct Muestra {
    t: f64,
    od: Option<[f64; 2]>,
    oi: Option<[f64; 2]>,
}

struct VngApp {
    manager: Arc<NativeVideoManager>,
    procesador: Arc<Mutex<EyeProcessor>>,
    rx: BusReceiver,
    recorder: Arc<Mutex<Option<SessionRecorder>>>,

    cfg: Config,
    cfg_sucia: Option<Instant>,
    ver_config: bool,

    camaras: Vec<CameraInfo>,
    formatos: Vec<CameraFormatInfo>,
    controles_hw: Vec<ControlHw>,
    /// La camara acaba de conectar: aplicar los controles del sensor.
    sensor_pendiente: bool,

    estado_camara: String,
    mensaje: String,

    muestras: VecDeque<Muestra>,
    t0: Option<f64>,
    pausado: bool,
    fps: f64,
    contador_fps: (f64, u32),
    /// Hora de inicio del examen en curso (None = solo vista en vivo).
    inicio_prueba: Option<Instant>,
    ultimo_intento: Option<Instant>,
    /// true mientras se reproduce una secuencia PGM: no reconectar la camara.
    reproduciendo: Arc<AtomicBool>,

    textura: Option<TextureHandle>,

    nistagmo: LiveNystagmus,
    en_grados: bool,
    eje_spv: Eje,

    /// Desarrollo: `SIEV_CAPTURA=ruta.png` guarda una captura de la ventana a
    /// los 5 s y cierra la app. Evita capturar el escritorio completo.
    captura: Option<(std::path::PathBuf, Instant, bool)>,
}

impl VngApp {
    fn new(cc: &eframe::CreationContext<'_>) -> Self {
        tema::aplicar(&cc.egui_ctx);

        let (bus, rx) = EventBus::new();
        let ctx = cc.egui_ctx.clone();
        bus.set_notifier(move || ctx.request_repaint());

        let recorder = Arc::new(Mutex::new(None));
        let procesador = Arc::new(Mutex::new(EyeProcessor::new()));
        let manager = Arc::new(NativeVideoManager::new(Arc::new(bus), procesador.clone(), recorder.clone()));

        let cfg = Config::cargar();
        cfg.aplicar(&manager);
        let mut nistagmo = LiveNystagmus::new(cfg.analisis.amplitud_min);
        nistagmo.ventana_s = cfg.analisis.ventana_s;
        nistagmo.set_espejar_h(cfg.analisis.espejar_h);

        let mut app = Self {
            manager,
            procesador,
            rx,
            recorder,
            cfg,
            cfg_sucia: None,
            ver_config: false,
            camaras: Vec::new(),
            formatos: Vec::new(),
            controles_hw: Vec::new(),
            sensor_pendiente: false,
            estado_camara: "desconectada".into(),
            mensaje: String::new(),
            muestras: VecDeque::new(),
            t0: None,
            pausado: false,
            fps: 0.0,
            contador_fps: (0.0, 0),
            inicio_prueba: None,
            ultimo_intento: None,
            reproduciendo: Arc::new(AtomicBool::new(false)),
            textura: None,
            nistagmo,
            en_grados: false,
            eje_spv: Eje::H,
            captura: std::env::var_os("SIEV_CAPTURA").map(|p| (p.into(), Instant::now(), false)),
        };
        app.refrescar_camaras();
        app
    }

    // ---------------------------------------------------------------
    // Camara y captura
    // ---------------------------------------------------------------

    fn refrescar_camaras(&mut self) {
        match native_video::list_cameras() {
            Ok(c) => self.camaras = c,
            Err(e) => self.mensaje = format!("Error listando camaras: {e}"),
        }
        if self.camara_actual().is_none() {
            // Preferir la camara USB de la mascara sobre la integrada.
            let usb = self.camaras.iter().find(|c| {
                let n = c.name.to_lowercase();
                n.contains("usb") && !n.contains("integrated")
            });
            if let Some(c) = usb.or(self.camaras.first()) {
                self.cfg.camara.nombre = c.name.clone();
            }
        }
        self.refrescar_formatos();
    }

    fn camara_actual(&self) -> Option<&CameraInfo> {
        self.camaras.iter().find(|c| c.name == self.cfg.camara.nombre)
    }

    fn refrescar_formatos(&mut self) {
        self.formatos.clear();
        self.controles_hw.clear();
        let Some(idx) = self.camara_actual().map(|c| c.index) else { return };
        self.controles_hw = camara_hw::listar(idx).unwrap_or_default();
        if let Ok(mut f) = native_video::list_camera_formats(idx) {
            f.sort_by_key(|f| std::cmp::Reverse((f.format == "MJPEG", f.fps, f.width)));
            self.formatos = f;
        }
        let c = &self.cfg.camara;
        let existe = self.formatos.iter().any(|f| f.width == c.ancho && f.height == c.alto && f.fps == c.fps);
        if !existe {
            if let Some(f) = self.formatos.first() {
                (self.cfg.camara.ancho, self.cfg.camara.alto, self.cfg.camara.fps) = (f.width, f.height, f.fps);
            }
        }
    }

    /// Abre la camara (vista en vivo). Si ya estaba abierta, la reinicia con
    /// el formato configurado.
    fn conectar(&mut self) {
        self.ultimo_intento = Some(Instant::now());
        let Some(cam) = self.camara_actual().map(|c| c.index) else {
            self.mensaje = "No se encuentra la camara de la mascara. Revisar el cable USB.".into();
            return;
        };
        self.cfg.aplicar(&self.manager);
        let c = &self.cfg.camara;
        match self.manager.start_capture(cam, c.ancho, c.alto, c.fps, self.cfg.ia.modelo.clone()) {
            Ok(()) => self.mensaje.clear(),
            Err(e) => self.mensaje = format!("No se pudo abrir la camara: {e}"),
        }
    }

    /// Conexion automatica: al abrir la app y si la camara se cae.
    fn mantener_camara(&mut self) {
        if self.manager.is_running() || self.reproduciendo.load(Ordering::SeqCst) {
            return;
        }
        if self.ultimo_intento.is_some_and(|t| t.elapsed() < REINTENTO_CAMARA) {
            return;
        }
        if self.camara_actual().is_none() {
            self.ultimo_intento = Some(Instant::now());
            self.refrescar_camaras();
            if self.camara_actual().is_none() {
                self.mensaje = "No se encuentra la camara de la mascara. Revisar el cable USB.".into();
                return;
            }
        }
        self.conectar();
    }

    fn iniciar_prueba(&mut self) {
        self.limpiar();
        self.inicio_prueba = Some(Instant::now());
    }

    fn terminar_prueba(&mut self) {
        self.inicio_prueba = None;
        if let Some(rec) = self.recorder.lock().unwrap().take() {
            rec.stop();
            self.mensaje = "Grabacion guardada".into();
        }
    }

    fn reproducir_secuencia(&mut self) {
        let Some(dir) = rfd::FileDialog::new().set_title("Carpeta con cuadros PGM").pick_folder() else { return };
        let seq = match PgmSequence::open(&dir, 200.0) {
            Ok(s) => s,
            Err(e) => {
                self.mensaje = format!("Secuencia ilegible: {e}");
                return;
            }
        };
        self.reproduciendo.store(true, Ordering::SeqCst);
        self.manager.stop_capture();
        self.cfg.aplicar(&self.manager);
        self.limpiar();
        let trace = std::env::temp_dir().join(format!("siev_vng_trace_{}.jsonl", std::process::id()));
        let (m, modelo) = (self.manager.clone(), self.cfg.ia.modelo.clone());
        let flag = self.reproduciendo.clone();
        std::thread::spawn(move || {
            // Dar tiempo al hilo de la camara a soltar el dispositivo.
            std::thread::sleep(Duration::from_millis(400));
            if let Err(e) = m.run_pgm_sequence(seq, trace, modelo) {
                eprintln!("[SIEV] secuencia fallo: {e}");
            }
            flag.store(false, Ordering::SeqCst);
        });
    }

    fn alternar_grabacion(&mut self) {
        let mut guard = self.recorder.lock().unwrap();
        if let Some(rec) = guard.take() {
            rec.stop();
            self.mensaje = "Grabacion guardada".into();
            return;
        }
        let nombre = format!("vng_{}.jsonl", unix_secs());
        if let Some(path) = rfd::FileDialog::new().set_file_name(&nombre).add_filter("JSONL", &["jsonl"]).save_file() {
            self.mensaje = format!("Grabando en {}", path.display());
            *guard = Some(SessionRecorder::start(path));
        }
    }

    fn limpiar(&mut self) {
        self.muestras.clear();
        self.t0 = None;
        self.contador_fps = (0.0, 0);
        self.nistagmo.reiniciar();
    }

    /// Aplica los controles guardados al sensor y relee sus valores.
    fn aplicar_sensor(&mut self) {
        let Some(idx) = self.camara_actual().map(|c| c.index) else { return };
        let errores = self.cfg.aplicar_sensor(idx);
        if let Some(e) = errores.first() {
            self.mensaje = format!("Control de camara: {e}");
        }
        self.controles_hw = camara_hw::listar(idx).unwrap_or_default();
    }

    fn fijar_sensor(&mut self, id: u32, valor: i64) {
        self.cfg.camara.sensor.insert(id, valor);
        if let Some(idx) = self.camara_actual().map(|c| c.index) {
            if let Err(e) = camara_hw::fijar(idx, id, valor) {
                self.mensaje = format!("Control de camara: {e}");
            }
            self.controles_hw = camara_hw::listar(idx).unwrap_or_default();
        }
        self.cfg_sucia = Some(Instant::now());
    }

    fn marcar_config_cambiada(&mut self) {
        self.cfg.aplicar(&self.manager);
        self.cfg_sucia = Some(Instant::now());
    }

    // ---------------------------------------------------------------
    // Datos
    // ---------------------------------------------------------------

    fn drenar_bus(&mut self, ctx: &egui::Context) {
        while let Ok(ev) = self.rx.events.try_recv() {
            match ev {
                // Las primeras ~30 muestras el procesador aun no fijo su centro:
                // la posicion salta al fijarlo y eso se veria como un latido.
                TrackEvent::EyeData(d) if !d.is_calibrated => {}
                TrackEvent::EyeData(d) => {
                    let t0 = *self.t0.get_or_insert(d.timestamp);
                    let t = d.timestamp - t0;
                    // El analisis sigue aunque los trazados esten congelados.
                    self.nistagmo.push(t, d.right, d.left);
                    if !self.pausado {
                        let conv = |p: Option<[f64; 2]>| p.map(|p| self.nistagmo.a_convencion(p));
                        let m = Muestra { t, od: conv(d.right), oi: conv(d.left) };
                        self.muestras.push_back(m);
                    }
                    let (inicio, n) = &mut self.contador_fps;
                    *n += 1;
                    if t - *inicio >= 1.0 {
                        self.fps = *n as f64 / (t - *inicio);
                        *inicio = t;
                        *n = 0;
                    }
                }
                TrackEvent::CameraStatus { status } => {
                    if status == "connected" && self.estado_camara != "connected" {
                        self.sensor_pendiente = true;
                    }
                    self.estado_camara = status;
                }
            }
        }
        if let Some(ultimo) = self.muestras.back().map(|m| m.t) {
            while self.muestras.front().is_some_and(|m| ultimo - m.t > VENTANA_TRAZO_S) {
                self.muestras.pop_front();
            }
        }

        let mut ultimo = None;
        while let Ok(img) = self.rx.frames.try_recv() {
            ultimo = Some(img);
        }
        if let Some(img) = ultimo {
            let ci = ColorImage::from_rgb([img.width() as usize, img.height() as usize], img.as_raw());
            match &mut self.textura {
                Some(t) => t.set(ci, TextureOptions::LINEAR),
                None => self.textura = Some(ctx.load_texture("preview", ci, TextureOptions::LINEAR)),
            }
        }
    }

    /// Fraccion de muestras con pupila en los ultimos segundos.
    fn calidad(&self, ojo: Ojo) -> Option<f64> {
        let fin = self.muestras.back()?.t;
        let recientes: Vec<_> = self.muestras.iter().rev().take_while(|m| fin - m.t <= VENTANA_CALIDAD_S).collect();
        if recientes.len() < 10 {
            return None;
        }
        let con = recientes
            .iter()
            .filter(|m| match ojo {
                Ojo::Od => m.od.is_some(),
                Ojo::Oi => m.oi.is_some(),
            })
            .count();
        Some(con as f64 / recientes.len() as f64)
    }

    fn unidad(&self) -> &'static str {
        if self.en_grados { "°" } else { "px" }
    }

    // ---------------------------------------------------------------
    // Barra superior: estado + controles de la prueba
    // ---------------------------------------------------------------

    fn barra_superior(&mut self, ui: &mut egui::Ui) {
        ui.horizontal_centered(|ui| {
            ui.label(RichText::new("SIEV").size(24.0).strong().color(ACENTO));
            ui.label(RichText::new("Videonistagmografia").size(16.0).color(TEXTO_SUAVE));
            ui.add_space(16.0);

            let corriendo = self.manager.is_running();
            let (txt, color) = match (corriendo, self.estado_camara.as_str()) {
                _ if self.reproduciendo.load(Ordering::SeqCst) => ("Reproduciendo secuencia", AMBAR),
                (true, "connected") => ("Camara conectada", VERDE),
                (true, _) => ("Conectando camara…", AMBAR),
                (false, _) => ("Sin camara", ROJO),
            };
            chip(ui, txt, color);
            if corriendo && self.fps > 0.0 {
                ui.label(RichText::new(format!("{:.0} Hz", self.fps)).color(TEXTO_SUAVE));
            }
            if !self.mensaje.is_empty() {
                ui.add_space(8.0);
                ui.label(RichText::new(&self.mensaje).color(AMBAR));
            }

            ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                if ui.add(egui::Button::new(RichText::new("⚙  Configuracion")).min_size(egui::vec2(0.0, 38.0))).clicked() {
                    self.ver_config = !self.ver_config;
                }
                ui.add_space(6.0);

                let grabando = self.recorder.lock().unwrap().is_some();
                let (txt, fondo, texto) = if grabando {
                    ("⏺  Grabando", ROJO, Color32::WHITE)
                } else {
                    ("⏺  Grabar", Color32::from_rgb(0xFB, 0xE4, 0xE4), ROJO)
                };
                let b = egui::Button::new(RichText::new(txt).color(texto).strong()).fill(fondo).min_size(egui::vec2(120.0, 38.0));
                if ui.add_enabled(corriendo || grabando, b).clicked() {
                    self.alternar_grabacion();
                }

                if self.inicio_prueba.is_some() {
                    let b = egui::Button::new(RichText::new("■  Terminar prueba").strong()).min_size(egui::vec2(170.0, 38.0));
                    if ui.add(b).clicked() {
                        self.terminar_prueba();
                    }
                } else {
                    let b = egui::Button::new(RichText::new("▶  Iniciar prueba").strong().color(Color32::WHITE))
                        .fill(ACENTO)
                        .min_size(egui::vec2(170.0, 38.0));
                    if ui.add_enabled(corriendo, b).on_disabled_hover_text("Esperando la camara").clicked() {
                        self.iniciar_prueba();
                    }
                }

                if let Some(t) = self.inicio_prueba {
                    let s = t.elapsed().as_secs();
                    ui.label(RichText::new(format!("{:02}:{:02}", s / 60, s % 60)).size(26.0).monospace().strong());
                }
            });
        });
    }

    // ---------------------------------------------------------------
    // Fila superior: video a lo ancho + tarjetas por ojo
    // ---------------------------------------------------------------

    fn fila_video(&mut self, ui: &mut egui::Ui, alto: f32) {
        let aspecto = self.textura.as_ref().map(|t| t.size_vec2().x / t.size_vec2().y).unwrap_or(480.0 / 180.0);
        let ancho_total = ui.available_width();
        // El video ocupa lo que su aspecto pida, dejando al menos 340 px a las tarjetas.
        let ancho_video = (alto * aspecto).min(ancho_total - 340.0 - 16.0).max(300.0);

        ui.horizontal_top(|ui| {
            // Video
            let (rect, _) = ui.allocate_exact_size(egui::vec2(ancho_video, alto), egui::Sense::hover());
            ui.painter().rect_filled(rect, CornerRadius::same(14), LIENZO_VIDEO);
            match &self.textura {
                Some(t) => {
                    let s = t.size_vec2();
                    let k = (rect.width() / s.x).min(rect.height() / s.y);
                    let r = egui::Rect::from_center_size(rect.center(), s * k);
                    let uv = egui::Rect::from_min_max(egui::pos2(0.0, 0.0), egui::pos2(1.0, 1.0));
                    ui.painter().image(t.id(), r, uv, Color32::WHITE);
                    // Rotulos sobre el video
                    let pinta = |pos: egui::Pos2, txt: &str, color: Color32| {
                        let g = ui.painter().layout_no_wrap(txt.into(), egui::FontId::proportional(13.0), Color32::WHITE);
                        let caja = egui::Rect::from_min_size(pos, g.size() + egui::vec2(14.0, 6.0));
                        ui.painter().rect_filled(caja, CornerRadius::same(6), color.gamma_multiply(0.9));
                        ui.painter().galley(pos + egui::vec2(7.0, 3.0), g, Color32::WHITE);
                    };
                    pinta(r.left_top() + egui::vec2(10.0, 10.0), "OD", OD);
                    pinta(egui::pos2(r.right() - 46.0, r.top() + 10.0), "OI", OI);
                }
                None => {
                    ui.painter().text(
                        rect.center(),
                        egui::Align2::CENTER_CENTER,
                        "Esperando video de la mascara…",
                        egui::FontId::proportional(16.0),
                        TEXTO_SUAVE,
                    );
                }
            }

            // Tarjetas
            ui.vertical(|ui| {
                ui.set_width(ui.available_width());
                let alto_tarjeta = (alto - 46.0 - 8.0) / 2.0;
                for ojo in Ojo::TODOS {
                    self.tarjeta_ojo(ui, ojo, alto_tarjeta);
                }
                ui.horizontal(|ui| {
                    if !self.en_grados {
                        ui.label(RichText::new("● Sin calibracion: valores en px").small().color(AMBAR));
                    }
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        if ui.small_button("Reiniciar analisis").clicked() {
                            self.nistagmo.reiniciar();
                        }
                        ui.label(RichText::new(format!("ventana {:.0} s", self.nistagmo.ventana_s)).small().color(TEXTO_SUAVE));
                    });
                });
            });
        });
    }

    fn tarjeta_ojo(&self, ui: &mut egui::Ui, ojo: Ojo, alto: f32) {
        let (titulo, color) = match ojo {
            Ojo::Od => ("Ojo derecho", OD),
            Ojo::Oi => ("Ojo izquierdo", OI),
        };
        let u = self.unidad();
        tema::tarjeta().show(ui, |ui| {
            ui.set_width(ui.available_width());
            ui.set_height((alto - 28.0).max(60.0));
            ui.horizontal(|ui| {
                ui.label(RichText::new("●").size(18.0).color(color));
                ui.label(RichText::new(titulo).size(17.0).strong());
                ui.label(RichText::new(if ojo == Ojo::Od { "OD" } else { "OI" }).color(TEXTO_SUAVE));
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| match self.calidad(ojo) {
                    Some(q) => {
                        let c = if q >= 0.9 { VERDE } else if q >= 0.6 { AMBAR } else { ROJO };
                        chip(ui, &format!("seguimiento {:.0}%", q * 100.0), c)
                            .on_hover_text("Cuadros con pupila detectada en los ultimos 2 s");
                    }
                    None => {
                        ui.label(RichText::new("sin señal").small().color(TEXTO_SUAVE));
                    }
                });
            });
            ui.add_space(2.0);
            egui::Grid::new(("hallazgos", titulo)).num_columns(2).spacing([14.0, 6.0]).striped(false).show(ui, |ui| {
                for eje in Eje::TODOS {
                    let r = self.nistagmo.resumen(ojo, eje);
                    let nombre = if eje == Eje::H { "Horizontal" } else { "Vertical" };
                    ui.label(RichText::new(nombre).color(TEXTO_SUAVE));
                    hallazgo(ui, &r, u);
                    ui.end_row();
                }
            });
        });
        ui.add_space(8.0);
    }

    // ---------------------------------------------------------------
    // Trazados
    // ---------------------------------------------------------------

    fn trazados(&mut self, ui: &mut egui::Ui) {
        tema::tarjeta().show(ui, |ui| {
            ui.set_width(ui.available_width());
            ui.set_height(ui.available_height());
            ui.horizontal(|ui| {
                ui.label(RichText::new("Registro").size(17.0).strong());
                ui.add_space(8.0);
                ui.label(RichText::new("━ OD").color(OD).strong());
                ui.label(RichText::new("━ OI").color(OI).strong());
                ui.label(RichText::new("▬ fase lenta").color(TEXTO_SUAVE));
                ui.add_space(8.0);
                ui.label(RichText::new("H: + derecha  ·  V: + arriba").small().color(TEXTO_SUAVE));
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    if ui.button("Limpiar").clicked() {
                        self.limpiar();
                    }
                    ui.toggle_value(&mut self.pausado, "❚❚ Congelar");
                    ui.add_space(12.0);
                    ui.selectable_value(&mut self.eje_spv, Eje::V, "V");
                    ui.selectable_value(&mut self.eje_spv, Eje::H, "H");
                    ui.label(RichText::new("Curva SPV").color(TEXTO_SUAVE));
                });
            });

            let u = self.unidad();
            let alto_plot = ((ui.available_height() - 20.0) / 3.0).max(90.0);
            let grupo = egui::Id::unique("ejes_vng");
            let t_min = self.muestras.front().map(|m| m.t).unwrap_or(0.0);

            for (titulo, eje) in [("Horizontal", Eje::H), ("Vertical", Eje::V)] {
                let k = if eje == Eje::H { 0 } else { 1 };
                // Los huecos (parpadeo, perdida) cortan la linea con NaN.
                let serie = |ojo: fn(&Muestra) -> Option<[f64; 2]>| -> Vec<[f64; 2]> {
                    self.muestras.iter().map(|m| [m.t, ojo(m).map(|v| v[k]).unwrap_or(f64::NAN)]).collect()
                };
                let (od, oi) = (serie(|m| m.od), serie(|m| m.oi));

                // Fases lentas detectadas, resaltadas sobre la traza
                let lentas: Vec<(Ojo, Vec<[f64; 2]>)> = self
                    .nistagmo
                    .historial()
                    .filter(|l| l.eje == eje && l.beat.slow_end_time >= t_min)
                    .map(|l| {
                        let b = &l.beat;
                        let pts = b
                            .deflection_points
                            .iter()
                            .filter(|(t, _)| *t >= b.slow_start_time && *t <= b.slow_end_time)
                            .map(|&(t, p)| [t, p])
                            .collect();
                        (l.ojo, pts)
                    })
                    .collect();

                let corto = if eje == Eje::H { "H" } else { "V" };
                Plot::new(titulo)
                    .height(alto_plot)
                    .link_axis(grupo, [true, false])
                    .y_axis_label(format!("{corto} ({u})"))
                    .y_axis_min_width(56.0)
                    .grid_color(tema::GRILLA)
                    .include_y(-5.0)
                    .include_y(5.0)
                    .default_x_bounds(0.0, VENTANA_TRAZO_S)
                    .show(ui, |pui| {
                        pui.hline(HLine::new("", 0.0).color(tema::BORDE).width(1.0));
                        for (ojo, pts) in lentas {
                            let color = if ojo == Ojo::Od { OD } else { OI };
                            pui.line(Line::new("", PlotPoints::from(pts)).color(color.gamma_multiply(0.30)).width(7.0));
                        }
                        pui.line(Line::new("OD", PlotPoints::from(od)).color(OD).width(1.8));
                        pui.line(Line::new("OI", PlotPoints::from(oi)).color(OI).width(1.8));
                    });
            }

            // SPV por latido a lo largo de la prueba
            let eje = self.eje_spv;
            let spv = |ojo: Ojo| -> Vec<[f64; 2]> {
                self.nistagmo
                    .historial()
                    .filter(|l| l.ojo == ojo && l.eje == eje)
                    .map(|l| [l.beat.slow_end_time, l.beat.slow_velocity])
                    .collect()
            };
            let (spv_od, spv_oi) = (spv(Ojo::Od), spv(Ojo::Oi));
            let nombre_eje = if eje == Eje::H { "H" } else { "V" };
            Plot::new("spv")
                .height(alto_plot)
                .legend(Legend::default())
                .y_axis_label(format!("SPV {nombre_eje} ({u}/s)"))
                .y_axis_min_width(56.0)
                .grid_color(tema::GRILLA)
                .include_y(-5.0)
                .include_y(5.0)
                .default_x_bounds(0.0, 60.0)
                .x_axis_label("tiempo (s)")
                .show(ui, |pui| {
                    pui.hline(HLine::new("", 0.0).color(tema::BORDE).width(1.0));
                    pui.points(Points::new("SPV OD", PlotPoints::from(spv_od)).color(OD).radius(3.5));
                    pui.points(Points::new("SPV OI", PlotPoints::from(spv_oi)).color(OI).radius(3.5));
                });
        });
    }

    // ---------------------------------------------------------------
    // Ventana de configuracion
    // ---------------------------------------------------------------

    fn ventana_config(&mut self, ctx: &egui::Context) {
        let mut abierta = self.ver_config;
        let mut cambio = false;
        let mut refrescar = false;
        let mut reconectar = false;
        let ocupado = self.reproduciendo.load(Ordering::SeqCst);

        egui::Window::new(RichText::new("Configuracion").size(18.0).strong())
            .open(&mut abierta)
            .default_width(400.0)
            .default_pos([ctx.content_rect().right() - 430.0, 70.0])
            .resizable(true)
            .show(ctx, |ui| {
                egui::ScrollArea::vertical().show(ui, |ui| {
                    egui::CollapsingHeader::new(RichText::new("Ojos y umbrales").strong()).default_open(true).show(ui, |ui| {
                        let o = &mut self.cfg.ojos;
                        ui.label(RichText::new("En automatico el umbral se calcula en cada cuadro. En manual: subirlo si la pupila no se detecta, bajarlo si toma pestañas o sombras.").small().color(TEXTO_SUAVE));
                        for (nombre, color, auto, umbral) in [
                            ("Umbral OD", OD, &mut o.auto_od, &mut o.umbral_od),
                            ("Umbral OI", OI, &mut o.auto_oi, &mut o.umbral_oi),
                        ] {
                            ui.horizontal(|ui| {
                                cambio |= ui.toggle_value(auto, "Auto").changed();
                                cambio |= ui
                                    .add_enabled(!*auto, egui::Slider::new(umbral, 1..=255).text(RichText::new(nombre).color(color)))
                                    .changed();
                            });
                        }
                        egui::CollapsingHeader::new("Zona de busqueda OD").show(ui, |ui| cambio |= editor_roi(ui, &mut o.roi_od));
                        egui::CollapsingHeader::new("Zona de busqueda OI").show(ui, |ui| cambio |= editor_roi(ui, &mut o.roi_oi));
                        egui::CollapsingHeader::new("Recorte de la imagen").show(ui, |ui| {
                            cambio |= ui.add(egui::Slider::new(&mut o.franja_nasal, 0.0..=0.6).text("Franja nasal")).changed();
                            cambio |= ui.add(egui::Slider::new(&mut o.alto_ojo, 0.0..=0.5).text("Alto de ojo")).changed();
                        });
                    });

                    egui::CollapsingHeader::new(RichText::new("Imagen").strong()).show(ui, |ui| {
                        cambio |= ui
                            .checkbox(&mut self.cfg.detector.quitar_reflejos, "Quitar reflejos del LED")
                            .on_hover_text("Rellena los puntos blancos del LED infrarrojo antes de buscar la pupila.")
                            .changed();
                        cambio |= ui.checkbox(&mut self.cfg.camara.mostrar_mascaras, "Mostrar lo que el detector ve como pupila").changed();

                        egui::CollapsingHeader::new("Sensor de la camara").default_open(true).show(ui, |ui| {
                            if self.controles_hw.is_empty() {
                                ui.label(RichText::new("La camara no expone controles.").small().color(TEXTO_SUAVE));
                            }
                            ui.label(RichText::new("Se aplican en la camara, antes de comprimir la imagen. Exposicion manual: el brillo no cambia solo durante la prueba.").small().color(TEXTO_SUAVE));
                            let fps = self.cfg.camara.fps;
                            let manual = self
                                .controles_hw
                                .iter()
                                .find(|c| c.id == camara_hw::EXPOSICION_AUTO)
                                .map(|c| c.actual == camara_hw::EXPOSICION_MANUAL);
                            let mut fijar: Option<(u32, i64)> = None;
                            for ctl in &self.controles_hw {
                                match ctl.id {
                                    camara_hw::EXPOSICION_AUTO => {
                                        let mut auto = ctl.actual != camara_hw::EXPOSICION_MANUAL;
                                        if ui.checkbox(&mut auto, "Exposicion automatica").changed() {
                                            let v = if auto { camara_hw::EXPOSICION_APERTURA } else { camara_hw::EXPOSICION_MANUAL };
                                            fijar = Some((ctl.id, v));
                                        }
                                    }
                                    camara_hw::EXPOSICION => {
                                        // Unidades UVC de 100 us. Mas exposicion = mas luz
                                        // pero menos fps: un cuadro no puede durar mas
                                        // que la exposicion.
                                        let mut v = ctl.actual;
                                        let etiqueta = format!(
                                            "Exposicion {:.1} ms (max. {:.1} ms a {fps} fps)",
                                            v as f64 / 10.0,
                                            camara_hw::exposicion_max_para(fps) as f64 / 10.0
                                        );
                                        let r = ui.add_enabled(
                                            manual == Some(true),
                                            egui::Slider::new(&mut v, ctl.min..=ctl.max).logarithmic(true).text(etiqueta),
                                        );
                                        if r.changed() {
                                            fijar = Some((ctl.id, v));
                                        }
                                        let medidos = self.fps;
                                        if manual == Some(true) && medidos > 0.0 && medidos < fps as f64 * 0.9 {
                                            ui.label(
                                                RichText::new(format!("La camara bajo a {medidos:.0} fps (pedidos {fps}): exposicion demasiado alta."))
                                                    .small()
                                                    .color(AMBAR),
                                            );
                                        }
                                    }
                                    _ => {
                                        let mut v = ctl.actual;
                                        if ui.add(egui::Slider::new(&mut v, ctl.min..=ctl.max).text(&ctl.nombre)).changed() {
                                            fijar = Some((ctl.id, v));
                                        }
                                    }
                                }
                            }
                            if let Some((id, v)) = fijar {
                                self.fijar_sensor(id, v);
                            }
                            if !self.controles_hw.is_empty() && ui.button("Valores de fabrica del sensor").clicked() {
                                let defectos: Vec<(u32, i64)> = self.controles_hw.iter().map(|c| (c.id, c.defecto)).collect();
                                for (id, v) in defectos {
                                    self.fijar_sensor(id, v);
                                }
                                self.cfg.camara.sensor.clear();
                            }
                        });

                        egui::CollapsingHeader::new("Ajuste por software").show(ui, |ui| {
                            let c = &mut self.cfg.camara;
                            cambio |= ui.add(egui::Slider::new(&mut c.brillo, -100..=100).text("Brillo")).changed();
                            cambio |= ui.add(egui::Slider::new(&mut c.contraste, 0.0..=100.0).text("Contraste")).changed();
                        });
                    });

                    egui::CollapsingHeader::new(RichText::new("Analisis de nistagmo").strong()).show(ui, |ui| {
                        let a = &mut self.cfg.analisis;
                        let u = if self.en_grados { "°" } else { "px" };
                        if ui
                            .add(egui::Slider::new(&mut a.amplitud_min, 0.1..=20.0).logarithmic(true).text(format!("Amplitud minima ({u})")))
                            .on_hover_text("Latidos mas pequeños se ignoran. Subir si cuenta latidos con la mirada quieta.")
                            .changed()
                        {
                            self.nistagmo.set_min_amplitud(a.amplitud_min);
                            cambio = true;
                        }
                        if ui.add(egui::Slider::new(&mut a.ventana_s, 2.0..=60.0).text("Ventana de resumen (s)")).changed() {
                            self.nistagmo.ventana_s = a.ventana_s;
                            cambio = true;
                        }
                        if ui
                            .checkbox(&mut a.espejar_h, "Invertir derecha/izquierda")
                            .on_hover_text("Si al mirar a la derecha la traza horizontal baja, activar. Reinicia el analisis.")
                            .changed()
                        {
                            self.nistagmo.set_espejar_h(a.espejar_h);
                            self.muestras.clear();
                            cambio = true;
                        }
                    });

                    egui::CollapsingHeader::new(RichText::new("Camara").strong()).show(ui, |ui| {
                        let nombres: Vec<String> = self.camaras.iter().map(|c| c.name.clone()).collect();
                        egui::ComboBox::from_label("Dispositivo")
                            .selected_text(if self.cfg.camara.nombre.is_empty() { "—" } else { &self.cfg.camara.nombre })
                            .show_ui(ui, |ui| {
                                for n in &nombres {
                                    if ui.selectable_value(&mut self.cfg.camara.nombre, n.clone(), n).changed() {
                                        refrescar = true;
                                        reconectar = true;
                                        cambio = true;
                                    }
                                }
                            });
                        let c = &mut self.cfg.camara;
                        let actual = format!("{}x{} @ {} fps", c.ancho, c.alto, c.fps);
                        egui::ComboBox::from_label("Formato").selected_text(actual).show_ui(ui, |ui| {
                            for f in &self.formatos {
                                let sel = f.width == c.ancho && f.height == c.alto && f.fps == c.fps;
                                let txt = format!("{}x{} @ {} fps {}", f.width, f.height, f.fps, f.format);
                                if ui.selectable_label(sel, txt).clicked() {
                                    (c.ancho, c.alto, c.fps) = (f.width, f.height, f.fps);
                                    reconectar = true;
                                    cambio = true;
                                }
                            }
                        });
                        if ui.button("Buscar camaras").clicked() {
                            refrescar = true;
                        }
                    });

                    egui::CollapsingHeader::new(RichText::new("Detector (avanzado)").strong()).show(ui, |ui| {
                        let d = &mut self.cfg.detector;
                        egui::ComboBox::from_label("Umbral automatico").selected_text(d.metodo_auto.nombre()).show_ui(ui, |ui| {
                            for m in MetodoAuto::TODOS {
                                cambio |= ui.selectable_value(&mut d.metodo_auto, m, m.nombre()).changed();
                            }
                        });
                        cambio |= ui.add(egui::Slider::new(&mut d.suavizado, 0.0..=6.0).text("Suavizado σ")).changed();
                        cambio |= ui.add(egui::Slider::new(&mut d.min_circularidad, 0.0..=1.0).text("Circularidad min")).changed();
                        cambio |= ui.add(egui::Slider::new(&mut d.min_area, 1..=2000).text("Area min (px)")).changed();
                        cambio |= ui.add(egui::Slider::new(&mut d.max_area_ratio, 0.05..=1.0).text("Area max (fraccion)")).changed();
                        cambio |= ui.add(egui::Slider::new(&mut d.aspecto_min, 0.1..=1.0).text("Aspecto min")).changed();
                        cambio |= ui.add(egui::Slider::new(&mut d.aspecto_max, 1.0..=5.0).text("Aspecto max")).changed();
                        cambio |= ui.checkbox(&mut d.parpadeo, "Detectar parpadeo").changed();
                        cambio |= ui.add(egui::Slider::new(&mut d.parpadeo_blanco, 0.1..=1.0).text("Fraccion blanca parpadeo")).changed();
                        cambio |= ui.add(egui::Slider::new(&mut d.tolerancia_perdida, 0..=60).text("Tolerancia perdida (cuadros)")).changed();
                        cambio |= ui.add(egui::Slider::new(&mut d.margen_velocidad, 0.5..=6.0).text("Margen por velocidad")).changed();
                    });

                    egui::CollapsingHeader::new(RichText::new("Asistencia IA (YOLO)").strong()).show(ui, |ui| {
                        let ia = &mut self.cfg.ia;
                        ui.label(RichText::new("Acepta YOLO26 (clases ojo/pupila) o un detector de iris YOLOv8 como siev_iris_r01. La IA ubica cada ojo y el detector busca la pupila adentro. Se carga al conectar la camara.").small().color(TEXTO_SUAVE));
                        ui.horizontal(|ui| {
                            cambio |= ui.add(egui::TextEdit::singleline(&mut ia.modelo).hint_text("modelo .onnx").desired_width(240.0)).changed();
                            if ui.button("…").clicked() {
                                if let Some(f) = rfd::FileDialog::new().add_filter("ONNX", &["onnx"]).pick_file() {
                                    ia.modelo = f.display().to_string();
                                    cambio = true;
                                    reconectar = true;
                                }
                            }
                        });
                        if ui.add_enabled(!ia.modelo.is_empty(), egui::Checkbox::new(&mut ia.usar, "Usar IA para ubicar los ojos")).changed() {
                            cambio = true;
                            reconectar = true;
                        }
                        cambio |= ui
                            .add_enabled(ia.usar, egui::Slider::new(&mut ia.margen, 0.0..=0.6).text("Margen alrededor del iris"))
                            .on_hover_text("Tamaño de la zona verde, en fraccion del diametro del iris. La cruz verde marca el centro del iris: el detector prefiere la pupila cerca de ella.")
                            .changed();
                    });

                    egui::CollapsingHeader::new(RichText::new("Herramientas").strong()).show(ui, |ui| {
                        if ui.add_enabled(!ocupado, egui::Button::new("Reproducir secuencia PGM…")).clicked() {
                            self.reproducir_secuencia();
                        }
                        if ui.button("Restaurar valores de la mascara").clicked() {
                            let nombre = std::mem::take(&mut self.cfg.camara.nombre);
                            self.cfg = Config::default();
                            self.cfg.camara.nombre = nombre;
                            self.nistagmo.set_min_amplitud(self.cfg.analisis.amplitud_min);
                            self.nistagmo.ventana_s = self.cfg.analisis.ventana_s;
                            self.nistagmo.set_espejar_h(self.cfg.analisis.espejar_h);
                            cambio = true;
                        }
                    });
                });
            });

        self.ver_config = abierta;
        if refrescar {
            self.refrescar_camaras();
        }
        if reconectar {
            self.conectar();
        }
        if cambio {
            self.marcar_config_cambiada();
        }
    }
}

impl eframe::App for VngApp {
    fn ui(&mut self, ui: &mut egui::Ui, _frame: &mut eframe::Frame) {
        let ctx = ui.ctx().clone();
        self.drenar_bus(&ctx);
        self.en_grados = self.procesador.lock().map(|p| p.has_degree_mapping()).unwrap_or(false);
        self.mantener_camara();
        if self.sensor_pendiente {
            self.sensor_pendiente = false;
            self.aplicar_sensor();
        }
        if self.manager.is_running() {
            ctx.request_repaint_after(Duration::from_millis(16));
        } else {
            // Seguir intentando conectar aunque no haya eventos de entrada.
            ctx.request_repaint_after(REINTENTO_CAMARA);
        }

        // Guardado diferido: no escribir a disco en cada paso de un slider.
        if self.cfg_sucia.is_some_and(|t| t.elapsed() > Duration::from_millis(800)) {
            if let Err(e) = self.cfg.guardar() {
                self.mensaje = format!("No se pudo guardar la configuracion: {e}");
            }
            self.cfg_sucia = None;
        } else if self.cfg_sucia.is_some() {
            ctx.request_repaint_after(Duration::from_millis(200));
        }

        egui::Panel::top("barra")
            .frame(
                egui::Frame::new()
                    .fill(Color32::WHITE)
                    .inner_margin(egui::Margin::symmetric(20, 10))
                    .stroke(Stroke::new(1.0, tema::BORDE)),
            )
            .exact_size(64.0)
            .show(ui, |ui| self.barra_superior(ui));

        egui::CentralPanel::default()
            .frame(egui::Frame::new().fill(tema::FONDO).inner_margin(egui::Margin::same(16)))
            .show(ui, |ui| {
                let alto_video = (ui.available_height() * 0.38).clamp(220.0, 420.0);
                self.fila_video(ui, alto_video);
                ui.add_space(12.0);
                self.trazados(ui);
            });

        self.ventana_config(&ctx);
        self.captura_desarrollo(&ctx);
    }

    fn on_exit(&mut self) {
        self.terminar_prueba();
        self.manager.stop_capture();
        let _ = self.cfg.guardar();
    }
}

impl VngApp {
    fn captura_desarrollo(&mut self, ctx: &egui::Context) {
        let Some((ruta, inicio, pedida)) = &mut self.captura else { return };
        if *pedida || inicio.elapsed() < Duration::from_secs(5) {
            ctx.request_repaint_after(Duration::from_millis(200));
            return;
        }
        *pedida = true;
        let (ruta, ctx2) = (ruta.clone(), ctx.clone());
        ctx.send_viewport_cmd(egui::ViewportCommand::Screenshot(egui::ScreenshotCallback::new(move |img| {
            let [w, h] = img.size;
            let rgba: Vec<u8> = img.pixels.iter().flat_map(|c| c.to_array()).collect();
            match image::RgbaImage::from_raw(w as u32, h as u32, rgba).map(|i| i.save(&ruta)) {
                Some(Ok(())) => println!("[CAPTURA] {}", ruta.display()),
                _ => eprintln!("[CAPTURA] fallo al guardar {}", ruta.display()),
            }
            ctx2.send_viewport_cmd(egui::ViewportCommand::Close);
        })));
    }
}

/// Pastilla de estado: punto de color + texto sobre fondo tenue.
fn chip(ui: &mut egui::Ui, txt: &str, color: Color32) -> egui::Response {
    egui::Frame::new()
        .fill(color.gamma_multiply(0.12))
        .corner_radius(CornerRadius::same(20))
        .inner_margin(egui::Margin::symmetric(10, 4))
        .show(ui, |ui| {
            ui.horizontal(|ui| {
                ui.spacing_mut().item_spacing.x = 6.0;
                ui.label(RichText::new("●").color(color));
                ui.label(RichText::new(txt).color(color).strong());
            });
        })
        .response
}

fn hallazgo(ui: &mut egui::Ui, r: &Resumen, u: &str) {
    match r.direccion {
        Some(dir) => {
            let flecha = match dir {
                "derecha" => "→",
                "izquierda" => "←",
                "arriba" => "↑",
                _ => "↓",
            };
            ui.horizontal(|ui| {
                ui.label(RichText::new(format!("{flecha} batiendo a la {dir}")).size(16.0).strong());
                ui.label(RichText::new(format!("SPV {:.1} {u}/s", r.spv_abs)).size(16.0).strong().color(ACENTO));
                ui.label(RichText::new(format!("{:.1} lat/s", r.frecuencia_hz)).color(TEXTO_SUAVE));
            });
        }
        None if r.latidos_ventana > 0 => {
            ui.label(RichText::new(format!("{} latido(s) aislado(s)", r.latidos_ventana)).color(TEXTO_SUAVE));
        }
        None => {
            ui.label(RichText::new("sin nistagmo").color(TEXTO_SUAVE));
        }
    }
}

fn editor_roi(ui: &mut egui::Ui, r: &mut Roi) -> bool {
    let mut c = false;
    c |= ui.add(egui::Slider::new(&mut r.top, 0.0..=1.0).text("Superior")).changed();
    c |= ui.add(egui::Slider::new(&mut r.bottom, 0.0..=1.0).text("Inferior")).changed();
    c |= ui.add(egui::Slider::new(&mut r.nasal, 0.0..=1.0).text("Nasal")).changed();
    c |= ui.add(egui::Slider::new(&mut r.temporal, 0.0..=1.0).text("Temporal")).changed();
    c
}

fn unix_secs() -> u64 {
    std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0)
}
