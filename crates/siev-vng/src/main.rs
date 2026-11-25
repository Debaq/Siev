//! SIEV VNG — videonistagmografia en Rust puro (eframe/egui + egui_plot).
//!
//! La GUI no hace seguimiento: solo configura `NativeVideoManager`, drena el
//! bus de eventos y dibuja. Todo el pipeline vive en `siev-tracking`.

use std::collections::VecDeque;
use std::sync::{Arc, Mutex};

use eframe::egui::{self, Color32, ColorImage, TextureHandle, TextureOptions};
use egui_plot::{Legend, Line, Plot, PlotPoints};

use siev_tracking::bus::{BusReceiver, EventBus, TrackEvent};
use siev_tracking::math::processor::EyeProcessor;
use siev_tracking::storage::SessionRecorder;
use siev_tracking::vng::native_video::{self, CameraFormatInfo, CameraInfo, NativeVideoManager};
use siev_tracking::vng::trace::PgmSequence;

/// Colores clinicos habituales: OD rojo, OI azul.
const COLOR_OD: Color32 = Color32::from_rgb(230, 60, 60);
const COLOR_OI: Color32 = Color32::from_rgb(40, 150, 255);

/// Ventana visible de los graficos, en segundos.
const VENTANA_S: f64 = 10.0;

/// Contraste UI que corresponde al multiplicador 1.0 (ver [H-09]).
const CONTRASTE_NEUTRO: f32 = 100.0 / 3.0;

fn main() -> eframe::Result {
    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_title("SIEV — VNG")
            .with_inner_size([1400.0, 900.0]),
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

/// Parametros del detector expuestos en la UI. Defaults = constructor del manager.
struct Params {
    umbral_od: u8,
    umbral_oi: u8,
    suavizado: f32,
    ancho_nariz: f32,
    alto_ojo: f32,
    brillo: i32,
    contraste: f32, // escala UI 0-100
    min_circularidad: f32,
    min_area: u32,
    max_area_ratio: f32,
    parpadeo: bool,
    parpadeo_blanco: f32,
    tolerancia_perdida: u32,
    margen_velocidad: f32,
    aspecto_min: f32,
    aspecto_max: f32,
    debug: bool,
    yolo: bool,
}

impl Default for Params {
    fn default() -> Self {
        Self {
            umbral_od: 40,
            umbral_oi: 40,
            suavizado: 2.5,
            ancho_nariz: 0.25,
            alto_ojo: 0.25,
            brillo: 0,
            contraste: CONTRASTE_NEUTRO,
            min_circularidad: 0.55,
            min_area: 30,
            max_area_ratio: 0.6,
            parpadeo: true,
            parpadeo_blanco: 0.60,
            tolerancia_perdida: 5,
            margen_velocidad: 2.0,
            aspecto_min: 0.4,
            aspecto_max: 2.5,
            debug: false,
            yolo: false,
        }
    }
}

struct VngApp {
    manager: Arc<NativeVideoManager>,
    rx: BusReceiver,
    recorder: Arc<Mutex<Option<SessionRecorder>>>,

    camaras: Vec<CameraInfo>,
    camara_sel: Option<usize>,
    formatos: Vec<CameraFormatInfo>,
    formato_sel: Option<usize>,
    modelo_yolo: String,

    params: Params,
    estado_camara: String,
    mensaje: String,

    muestras: VecDeque<Muestra>,
    t0: Option<f64>,
    pausado: bool,
    fps_eventos: f64,
    contador_fps: (f64, u32),

    textura: Option<TextureHandle>,
}

impl VngApp {
    fn new(cc: &eframe::CreationContext<'_>) -> Self {
        let (bus, rx) = EventBus::new();
        let ctx = cc.egui_ctx.clone();
        bus.set_notifier(move || ctx.request_repaint());

        let recorder = Arc::new(Mutex::new(None));
        let manager = Arc::new(NativeVideoManager::new(
            Arc::new(bus),
            Arc::new(Mutex::new(EyeProcessor::new())),
            recorder.clone(),
        ));

        let mut app = Self {
            manager,
            rx,
            recorder,
            camaras: Vec::new(),
            camara_sel: None,
            formatos: Vec::new(),
            formato_sel: None,
            modelo_yolo: String::new(),
            params: Params::default(),
            estado_camara: "desconectada".into(),
            mensaje: String::new(),
            muestras: VecDeque::new(),
            t0: None,
            pausado: false,
            fps_eventos: 0.0,
            contador_fps: (0.0, 0),
            textura: None,
        };
        app.refrescar_camaras();
        app
    }

    fn refrescar_camaras(&mut self) {
        match native_video::list_cameras() {
            Ok(c) => {
                self.camaras = c;
                self.camara_sel = if self.camaras.is_empty() { None } else { Some(0) };
                self.refrescar_formatos();
            }
            Err(e) => self.mensaje = format!("Error listando camaras: {e}"),
        }
    }

    fn refrescar_formatos(&mut self) {
        self.formatos.clear();
        self.formato_sel = None;
        let Some(i) = self.camara_sel else { return };
        match native_video::list_camera_formats(self.camaras[i].index) {
            Ok(mut f) => {
                // MJPEG primero y a mayor fps: es lo que usa el equipo.
                f.sort_by(|a, b| {
                    (b.format == "MJPEG", b.fps, b.width).cmp(&(a.format == "MJPEG", a.fps, a.width))
                });
                self.formatos = f;
                self.formato_sel = if self.formatos.is_empty() { None } else { Some(0) };
            }
            Err(e) => self.mensaje = format!("Error listando formatos: {e}"),
        }
    }

    fn iniciar(&mut self) {
        let (Some(ci), Some(fi)) = (self.camara_sel, self.formato_sel) else {
            self.mensaje = "Elegir camara y formato".into();
            return;
        };
        let cam = self.camaras[ci].index;
        let f = self.formatos[fi].clone();
        self.aplicar_todos_los_params();
        self.limpiar_graficos();
        if let Err(e) = self.manager.start_capture(cam, f.width, f.height, f.fps, self.modelo_yolo.clone()) {
            self.mensaje = format!("No se pudo iniciar: {e}");
        }
    }

    fn reproducir_secuencia(&mut self) {
        let Some(dir) = rfd::FileDialog::new().set_title("Carpeta con cuadros PGM").pick_folder() else {
            return;
        };
        let seq = match PgmSequence::open(&dir, 200.0) {
            Ok(s) => s,
            Err(e) => {
                self.mensaje = format!("Secuencia ilegible: {e}");
                return;
            }
        };
        self.aplicar_todos_los_params();
        self.limpiar_graficos();
        let trace = std::env::temp_dir().join(format!("siev_vng_trace_{}.jsonl", std::process::id()));
        self.mensaje = format!("Reproduciendo {} cuadros; traza en {}", seq.len(), trace.display());
        let m = self.manager.clone();
        let modelo = self.modelo_yolo.clone();
        std::thread::spawn(move || {
            if let Err(e) = m.run_pgm_sequence(seq, trace, modelo) {
                eprintln!("[SIEV] secuencia fallo: {e}");
            }
        });
    }

    fn alternar_grabacion(&mut self) {
        let mut guard = self.recorder.lock().unwrap();
        if let Some(rec) = guard.take() {
            rec.stop();
            self.mensaje = "Grabacion detenida".into();
            return;
        }
        let nombre = format!("vng_{}.jsonl", unix_secs());
        if let Some(path) = rfd::FileDialog::new()
            .set_file_name(&nombre)
            .add_filter("JSONL", &["jsonl"])
            .save_file()
        {
            self.mensaje = format!("Grabando en {}", path.display());
            *guard = Some(SessionRecorder::start(path));
        }
    }

    fn limpiar_graficos(&mut self) {
        self.muestras.clear();
        self.t0 = None;
        self.contador_fps = (0.0, 0);
    }

    fn aplicar_todos_los_params(&self) {
        let p = &self.params;
        let m = &self.manager;
        m.set_thresholds(p.umbral_od, p.umbral_oi);
        m.set_smooth(p.suavizado);
        m.set_nose_width(p.ancho_nariz);
        m.set_eye_height(p.alto_ojo);
        m.set_brightness(p.brillo);
        // Solo si se movio: la escala UI no alcanza exacto el multiplicador 1.0.
        if (p.contraste - CONTRASTE_NEUTRO).abs() > 1e-3 {
            m.set_contrast(p.contraste);
        }
        m.set_min_circularity(p.min_circularidad);
        m.set_min_area(p.min_area);
        m.set_max_area_ratio(p.max_area_ratio);
        m.set_blink_detection(p.parpadeo);
        m.set_blink_white_ratio(p.parpadeo_blanco);
        m.set_lost_tolerance(p.tolerancia_perdida);
        m.set_velocity_margin_factor(p.margen_velocidad);
        m.set_aspect_ratio_min(p.aspecto_min);
        m.set_aspect_ratio_max(p.aspecto_max);
        m.set_show_debug(p.debug);
        m.set_use_yolo(p.yolo);
    }

    fn drenar_bus(&mut self, ctx: &egui::Context) {
        while let Ok(ev) = self.rx.events.try_recv() {
            match ev {
                TrackEvent::EyeData(d) => {
                    let t0 = *self.t0.get_or_insert(d.timestamp);
                    let t = d.timestamp - t0;
                    if !self.pausado {
                        self.muestras.push_back(Muestra { t, od: d.right, oi: d.left });
                    }
                    // Frecuencia medida sobre los timestamps del pipeline
                    let (inicio, n) = &mut self.contador_fps;
                    *n += 1;
                    if t - *inicio >= 1.0 {
                        self.fps_eventos = *n as f64 / (t - *inicio);
                        *inicio = t;
                        *n = 0;
                    }
                }
                TrackEvent::CameraStatus { status } => self.estado_camara = status,
            }
        }
        if let Some(ultimo) = self.muestras.back().map(|m| m.t) {
            while self.muestras.front().is_some_and(|m| ultimo - m.t > VENTANA_S) {
                self.muestras.pop_front();
            }
        }

        // Solo interesa el cuadro mas reciente
        let mut ultimo = None;
        while let Ok(img) = self.rx.frames.try_recv() {
            ultimo = Some(img);
        }
        if let Some(img) = ultimo {
            let size = [img.width() as usize, img.height() as usize];
            let ci = ColorImage::from_rgb(size, img.as_raw());
            match &mut self.textura {
                Some(t) => t.set(ci, TextureOptions::LINEAR),
                None => self.textura = Some(ctx.load_texture("preview", ci, TextureOptions::LINEAR)),
            }
        }
    }

    fn panel_superior(&mut self, ui: &mut egui::Ui) {
        ui.horizontal(|ui| {
            let corriendo = self.manager.is_running();

            ui.add_enabled_ui(!corriendo, |ui| {
                let txt = self
                    .camara_sel
                    .map(|i| self.camaras[i].name.clone())
                    .unwrap_or_else(|| "—".into());
                let mut cambio = false;
                egui::ComboBox::from_id_salt("camara").selected_text(txt).width(220.0).show_ui(ui, |ui| {
                    for (i, c) in self.camaras.iter().enumerate() {
                        cambio |= ui.selectable_value(&mut self.camara_sel, Some(i), &c.name).changed();
                    }
                });
                if cambio {
                    self.refrescar_formatos();
                }
                let txt = self
                    .formato_sel
                    .map(|i| fmt_formato(&self.formatos[i]))
                    .unwrap_or_else(|| "—".into());
                egui::ComboBox::from_id_salt("formato").selected_text(txt).width(200.0).show_ui(ui, |ui| {
                    for (i, f) in self.formatos.iter().enumerate() {
                        ui.selectable_value(&mut self.formato_sel, Some(i), fmt_formato(f));
                    }
                });
                if ui.button("⟳").on_hover_text("Refrescar camaras").clicked() {
                    self.refrescar_camaras();
                }
            });

            ui.separator();
            if corriendo {
                if ui.button("⏹ Detener").clicked() {
                    self.manager.stop_capture();
                }
            } else {
                if ui.button("▶ Iniciar").clicked() {
                    self.iniciar();
                }
                if ui.button("Secuencia PGM…").clicked() {
                    self.reproducir_secuencia();
                }
            }

            let grabando = self.recorder.lock().unwrap().is_some();
            let etiqueta = if grabando { "⏺ Detener grabacion" } else { "⏺ Grabar" };
            if ui.add(egui::Button::new(etiqueta).selected(grabando)).clicked() {
                self.alternar_grabacion();
            }

            ui.separator();
            ui.label(format!("Camara: {}", self.estado_camara));
            ui.label(format!("{:.0} Hz", self.fps_eventos));
            if !self.mensaje.is_empty() {
                ui.separator();
                ui.label(&self.mensaje);
            }
        });
    }

    fn panel_parametros(&mut self, ui: &mut egui::Ui) {
        let m = self.manager.clone();
        let p = &mut self.params;
        let modelo = &mut self.modelo_yolo;
        egui::ScrollArea::vertical().show(ui, |ui| {
            ui.heading("Detector");
            let c1 = ui.add(egui::Slider::new(&mut p.umbral_od, 0..=255).text("Umbral OD")).changed();
            let c2 = ui.add(egui::Slider::new(&mut p.umbral_oi, 0..=255).text("Umbral OI")).changed();
            if c1 || c2 {
                m.set_thresholds(p.umbral_od, p.umbral_oi);
            }
            ui.small("0 = umbral adaptativo");
            if ui.add(egui::Slider::new(&mut p.suavizado, 0.0..=6.0).text("Suavizado σ")).changed() {
                m.set_smooth(p.suavizado);
            }
            if ui.add(egui::Slider::new(&mut p.min_circularidad, 0.0..=1.0).text("Circularidad min")).changed() {
                m.set_min_circularity(p.min_circularidad);
            }
            if ui.add(egui::Slider::new(&mut p.min_area, 1..=2000).text("Area min (px)")).changed() {
                m.set_min_area(p.min_area);
            }
            if ui.add(egui::Slider::new(&mut p.max_area_ratio, 0.05..=1.0).text("Area max (fraccion)")).changed() {
                m.set_max_area_ratio(p.max_area_ratio);
            }
            if ui.add(egui::Slider::new(&mut p.aspecto_min, 0.1..=1.0).text("Aspecto min")).changed() {
                m.set_aspect_ratio_min(p.aspecto_min);
            }
            if ui.add(egui::Slider::new(&mut p.aspecto_max, 1.0..=5.0).text("Aspecto max")).changed() {
                m.set_aspect_ratio_max(p.aspecto_max);
            }

            ui.separator();
            ui.heading("Seguimiento");
            if ui.checkbox(&mut p.parpadeo, "Detectar parpadeo").changed() {
                m.set_blink_detection(p.parpadeo);
            }
            if ui
                .add(egui::Slider::new(&mut p.parpadeo_blanco, 0.1..=1.0).text("Fraccion blanca parpadeo"))
                .changed()
            {
                m.set_blink_white_ratio(p.parpadeo_blanco);
            }
            if ui
                .add(egui::Slider::new(&mut p.tolerancia_perdida, 0..=60).text("Tolerancia perdida (cuadros)"))
                .changed()
            {
                m.set_lost_tolerance(p.tolerancia_perdida);
            }
            if ui
                .add(egui::Slider::new(&mut p.margen_velocidad, 0.5..=6.0).text("Margen por velocidad"))
                .changed()
            {
                m.set_velocity_margin_factor(p.margen_velocidad);
            }

            ui.separator();
            ui.heading("Geometria");
            if ui.add(egui::Slider::new(&mut p.ancho_nariz, 0.0..=0.6).text("Franja nasal")).changed() {
                m.set_nose_width(p.ancho_nariz);
            }
            if ui.add(egui::Slider::new(&mut p.alto_ojo, 0.0..=0.5).text("Alto de ojo")).changed() {
                m.set_eye_height(p.alto_ojo);
            }

            ui.separator();
            ui.heading("Imagen");
            if ui.add(egui::Slider::new(&mut p.brillo, -100..=100).text("Brillo")).changed() {
                m.set_brightness(p.brillo);
            }
            if ui.add(egui::Slider::new(&mut p.contraste, 0.0..=100.0).text("Contraste")).changed() {
                m.set_contrast(p.contraste);
            }
            if ui.checkbox(&mut p.debug, "Mostrar mascaras").changed() {
                m.set_show_debug(p.debug);
            }

            ui.separator();
            ui.heading("Anclaje YOLO");
            ui.horizontal(|ui| {
                ui.add(egui::TextEdit::singleline(modelo).hint_text("modelo .onnx").desired_width(160.0));
                if ui.button("…").clicked() {
                    if let Some(f) = rfd::FileDialog::new().add_filter("ONNX", &["onnx"]).pick_file() {
                        *modelo = f.display().to_string();
                    }
                }
            });
            ui.small("El modelo se carga al iniciar la captura.");
            if ui.checkbox(&mut p.yolo, "Usar YOLO").changed() {
                m.set_use_yolo(p.yolo);
            }
        });
    }

    fn panel_central(&mut self, ui: &mut egui::Ui) {
        let alto_preview = (ui.available_height() * 0.42).max(160.0);

        // Preview de camara con marcas de ROI y pupila (dibujadas por el pipeline)
        ui.allocate_ui(egui::vec2(ui.available_width(), alto_preview), |ui| {
            ui.centered_and_justified(|ui| match &self.textura {
                Some(t) => {
                    let s = t.size_vec2();
                    let k = (ui.available_width() / s.x).min(ui.available_height() / s.y);
                    ui.image((t.id(), s * k));
                }
                None => {
                    ui.label("Sin video");
                }
            });
        });

        ui.horizontal(|ui| {
            ui.checkbox(&mut self.pausado, "Pausar graficos");
            if ui.button("Limpiar").clicked() {
                self.limpiar_graficos();
            }
        });

        let alto_plot = ((ui.available_height() - 8.0) / 2.0).max(80.0);
        let grupo = egui::Id::unique("ejes_vng");

        for (titulo, eje) in [("Horizontal", 0usize), ("Vertical", 1usize)] {
            // Los huecos (parpadeo, perdida) cortan la linea con NaN.
            let serie = |ojo: fn(&Muestra) -> Option<[f64; 2]>| -> Vec<[f64; 2]> {
                self.muestras
                    .iter()
                    .map(|m| [m.t, ojo(m).map(|v| v[eje]).unwrap_or(f64::NAN)])
                    .collect()
            };
            let od = serie(|m| m.od);
            let oi = serie(|m| m.oi);
            Plot::new(titulo)
                .height(alto_plot)
                .legend(Legend::default())
                .link_axis(grupo, [true, false])
                .y_axis_label(format!("{titulo} (°)"))
                .x_axis_label("t (s)")
                .show(ui, |pui| {
                    pui.line(Line::new("OD", PlotPoints::from(od)).color(COLOR_OD).width(1.5));
                    pui.line(Line::new("OI", PlotPoints::from(oi)).color(COLOR_OI).width(1.5));
                });
        }
    }
}

impl eframe::App for VngApp {
    fn ui(&mut self, ui: &mut egui::Ui, _frame: &mut eframe::Frame) {
        let ctx = ui.ctx().clone();
        self.drenar_bus(&ctx);
        if self.manager.is_running() {
            // Los cuadros ya piden repintado; esto cubre los datos entre cuadros.
            ctx.request_repaint_after(std::time::Duration::from_millis(16));
        }

        egui::Panel::top("barra").show(ui, |ui| self.panel_superior(ui));
        egui::Panel::left("parametros")
            .resizable(true)
            .default_size(300.0)
            .show(ui, |ui| self.panel_parametros(ui));
        egui::CentralPanel::default().show(ui, |ui| self.panel_central(ui));
    }

    fn on_exit(&mut self) {
        self.manager.stop_capture();
        if let Some(rec) = self.recorder.lock().unwrap().take() {
            rec.stop();
        }
    }
}

fn fmt_formato(f: &CameraFormatInfo) -> String {
    format!("{}x{} @{} {}", f.width, f.height, f.fps, f.format)
}

fn unix_secs() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0)
}
