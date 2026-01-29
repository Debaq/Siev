use std::sync::{Arc, Mutex, atomic::{AtomicBool, Ordering}};
use std::thread;
use std::io::Cursor;
use nokhwa::pixel_format::LumaFormat;
use nokhwa::utils::{CameraIndex, RequestedFormat, RequestedFormatType, CameraFormat, FrameFormat, Resolution, ApiBackend};
use nokhwa::query;
use nokhwa::Camera;
use image::{GrayImage, ImageBuffer, Rgb, Luma, codecs::jpeg::JpegEncoder, DynamicImage};
use imageproc::point::Point;
use imageproc::filter::gaussian_blur_f32;
use imageproc::morphology::{erode_mut, close_mut};
use imageproc::distance_transform::Norm;
use imageproc::contours::find_contours;
use zune_jpeg::JpegDecoder;
use zune_core::options::DecoderOptions;
use zune_core::colorspace::ColorSpace;
use ort::session::Session;
use ndarray::Array4;
use serde::{Serialize, Deserialize};
use crate::websocket::{WebSocketServer, WsMessage};
use crate::math::processor::{RawEyeData, EyeProcessor};
use crate::storage::recorder::SessionRecorder;
use crate::storage::video_recorder::VideoRecorder;

// V4L2 directo como fallback cuando nokhwa falla (framerates fraccionarios, etc.)
use v4l::video::Capture as V4lCapture;
use v4l::io::traits::CaptureStream as V4lCaptureStream;

/// Información de una cámara detectada
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct CameraInfo {
    pub index: u32,
    pub name: String,
    pub description: String,
}

/// Formato de cámara soportado
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct CameraFormatInfo {
    pub width: u32,
    pub height: u32,
    pub fps: u32,
    pub format: String,  // "MJPEG", "YUYV", etc.
}

/// Lista las cámaras disponibles en el sistema
/// Nota: No intentamos abrir las cámaras aquí porque pueden estar en uso
pub fn list_cameras() -> Result<Vec<CameraInfo>, String> {
    let cameras = query(ApiBackend::Auto)
        .map_err(|e| format!("Error listando cámaras: {:?}", e))?;

    // Filtrar cámaras por índice par (en V4L2, los índices impares suelen ser metadata)
    // /dev/video0 = video, /dev/video1 = metadata de video0
    // /dev/video2 = video, /dev/video3 = metadata de video2, etc.
    let valid_cameras: Vec<CameraInfo> = cameras
        .into_iter()
        .filter_map(|c| {
            let idx = match c.index() {
                CameraIndex::Index(i) => *i,
                CameraIndex::String(s) => s.parse().unwrap_or(0),
            };

            // Solo incluir índices pares (nodos de video reales)
            if idx % 2 == 0 {
                Some(CameraInfo {
                    index: idx,
                    name: c.human_name().to_string(),
                    description: c.description().to_string(),
                })
            } else {
                None
            }
        })
        .collect();

    Ok(valid_cameras)
}

/// Lista los formatos soportados por una cámara específica
pub fn list_camera_formats(camera_id: u32) -> Result<Vec<CameraFormatInfo>, String> {
    // Intentar con nokhwa primero
    match list_camera_formats_nokhwa(camera_id) {
        Ok(formats) => Ok(formats),
        Err(nokhwa_err) => {
            // Fallback a v4l directo (maneja framerates fraccionarios)
            println!("[SIEV] nokhwa falló para cámara {}, usando v4l directo: {}", camera_id, nokhwa_err);
            list_camera_formats_v4l(camera_id)
        }
    }
}

fn list_camera_formats_nokhwa(camera_id: u32) -> Result<Vec<CameraFormatInfo>, String> {
    let index = CameraIndex::Index(camera_id);

    let format = RequestedFormat::new::<LumaFormat>(RequestedFormatType::None);
    let mut camera = Camera::new(index, format)
        .map_err(|e| format!("Error abriendo cámara {}: {:?}", camera_id, e))?;

    let formats = camera.compatible_camera_formats()
        .map_err(|e| format!("Error obteniendo formatos: {:?}", e))?;

    let mut result: Vec<CameraFormatInfo> = formats
        .into_iter()
        .filter(|f| f.format() == FrameFormat::MJPEG)
        .map(|f| CameraFormatInfo {
            width: f.resolution().width(),
            height: f.resolution().height(),
            fps: f.frame_rate(),
            format: format!("{:?}", f.format()),
        })
        .collect();

    result.sort_by(|a, b| {
        let res_a = a.width * a.height;
        let res_b = b.width * b.height;
        res_b.cmp(&res_a).then(b.fps.cmp(&a.fps))
    });
    result.dedup_by(|a, b| a.width == b.width && a.height == b.height && a.fps == b.fps);

    Ok(result)
}

/// Fallback: lista formatos usando v4l directo (soporta framerates fraccionarios)
fn list_camera_formats_v4l(camera_id: u32) -> Result<Vec<CameraFormatInfo>, String> {
    let dev = v4l::Device::new(camera_id as usize)
        .map_err(|e| format!("Error abriendo dispositivo V4L2 {}: {:?}", camera_id, e))?;

    let formats = V4lCapture::enum_formats(&dev)
        .map_err(|e| format!("Error listando formatos v4l: {:?}", e))?;

    let mut result = Vec::new();
    let mjpg = v4l::FourCC::new(b"MJPG");

    for fmt_desc in &formats {
        let is_mjpeg = fmt_desc.fourcc == mjpg;
        let format_name = if is_mjpeg { "MJPEG".to_string() } else { format!("{}", fmt_desc.fourcc) };

        let framesizes = V4lCapture::enum_framesizes(&dev, fmt_desc.fourcc).unwrap_or_default();

        for size in &framesizes {
            match &size.size {
                v4l::framesize::FrameSizeEnum::Discrete(d) => {
                    let intervals = V4lCapture::enum_frameintervals(&dev, fmt_desc.fourcc, d.width, d.height)
                        .unwrap_or_default();

                    for interval in &intervals {
                        match &interval.interval {
                            v4l::frameinterval::FrameIntervalEnum::Discrete(frac) => {
                                if frac.numerator > 0 {
                                    let fps = (frac.denominator as f64 / frac.numerator as f64).round() as u32;
                                    if fps > 0 {
                                        result.push(CameraFormatInfo {
                                            width: d.width,
                                            height: d.height,
                                            fps,
                                            format: format_name.clone(),
                                        });
                                    }
                                }
                            }
                            _ => {}
                        }
                    }

                    // Si no hay intervalos reportados, agregar con fps=30 por defecto
                    if V4lCapture::enum_frameintervals(&dev, fmt_desc.fourcc, d.width, d.height)
                        .unwrap_or_default().is_empty()
                    {
                        result.push(CameraFormatInfo {
                            width: d.width,
                            height: d.height,
                            fps: 30,
                            format: format_name.clone(),
                        });
                    }
                }
                _ => {}
            }
        }
    }

    result.sort_by(|a, b| {
        let res_a = a.width * a.height;
        let res_b = b.width * b.height;
        res_b.cmp(&res_a).then(b.fps.cmp(&a.fps))
    });
    result.dedup_by(|a, b| a.width == b.width && a.height == b.height && a.fps == b.fps);

    Ok(result)
}

#[derive(Clone, Copy, Debug, Serialize)]
pub struct RustPupilResult {
    pub center_x: f32,
    pub center_y: f32,
    pub radius: f32,
    pub confidence: f32,
    pub found: bool,
}

/// ROI manual para un ojo: límites superior, inferior, nasal y temporal
/// Los valores son relativos (0.0 a 1.0) respecto al área de cada ojo en la imagen combinada
#[derive(Clone, Copy, Debug, Serialize, Deserialize)]
pub struct ManualEyeRoi {
    pub top: f32,      // Límite superior (0.0 = arriba)
    pub bottom: f32,   // Límite inferior (1.0 = abajo)
    pub nasal: f32,    // Límite nasal (hacia el centro de la cara)
    pub temporal: f32, // Límite temporal (hacia afuera)
}

impl Default for ManualEyeRoi {
    fn default() -> Self {
        Self {
            top: 0.1,
            bottom: 0.9,
            nasal: 0.1,
            temporal: 0.9,
        }
    }
}

pub struct NativeVideoManager {
    running: Arc<AtomicBool>,
    starting: Arc<AtomicBool>,  // Bloquea nuevas llamadas mientras se está iniciando
    ws_server: Arc<WebSocketServer>,
    eye_processor: Arc<Mutex<EyeProcessor>>,
    threshold: Arc<Mutex<[u8; 2]>>,      // [right, left]
    erode: Arc<Mutex<[u8; 2]>>,          // [right, left]
    nose_width: Arc<Mutex<f32>>,
    eye_height: Arc<Mutex<f32>>,
    use_yolo: Arc<AtomicBool>,
    yolo_frequency: Arc<Mutex<u32>>,
    // ROI manual para cada ojo [derecho, izquierdo]
    manual_roi_right: Arc<Mutex<ManualEyeRoi>>,
    manual_roi_left: Arc<Mutex<ManualEyeRoi>>,
    // Suavizado gaussiano (sigma)
    smooth_sigma: Arc<Mutex<f32>>,
    // Ajustes de imagen
    brightness: Arc<Mutex<i32>>,  // -100 a +100
    contrast: Arc<Mutex<f32>>,    // 0.0 a 3.0 (1.0 = sin cambio)
    // Modo debug: muestra máscaras de umbralización
    show_debug: Arc<AtomicBool>,
    // Session recorder for eye data
    active_recorder: Arc<Mutex<Option<SessionRecorder>>>,
    // Video recorder for raw frames (no UI marks)
    active_video_recorder: Arc<Mutex<Option<VideoRecorder>>>,
    // Capture dimensions (for video recorder initialization)
    capture_width: Arc<Mutex<u32>>,
    capture_height: Arc<Mutex<u32>>,
}

impl NativeVideoManager {
    pub fn new(
        ws_server: Arc<WebSocketServer>,
        eye_processor: Arc<Mutex<EyeProcessor>>,
        active_recorder: Arc<Mutex<Option<SessionRecorder>>>,
    ) -> Self {
        Self {
            running: Arc::new(AtomicBool::new(false)),
            starting: Arc::new(AtomicBool::new(false)),
            ws_server,
            eye_processor,
            threshold: Arc::new(Mutex::new([40, 40])),
            erode: Arc::new(Mutex::new([1, 1])),
            nose_width: Arc::new(Mutex::new(0.25)),
            eye_height: Arc::new(Mutex::new(0.25)),
            use_yolo: Arc::new(AtomicBool::new(false)),
            yolo_frequency: Arc::new(Mutex::new(10)),
            manual_roi_right: Arc::new(Mutex::new(ManualEyeRoi::default())),
            manual_roi_left: Arc::new(Mutex::new(ManualEyeRoi::default())),
            smooth_sigma: Arc::new(Mutex::new(2.5)),
            brightness: Arc::new(Mutex::new(0)),
            contrast: Arc::new(Mutex::new(1.0)),
            show_debug: Arc::new(AtomicBool::new(false)),
            active_recorder,
            active_video_recorder: Arc::new(Mutex::new(None)),
            capture_width: Arc::new(Mutex::new(0)),
            capture_height: Arc::new(Mutex::new(0)),
        }
    }

    pub fn set_brightness(&self, value: i32) {
        if let Ok(mut b) = self.brightness.lock() {
            *b = value.clamp(-100, 100);
            println!("[IMAGE] Brillo: {}", *b);
        }
    }

    pub fn set_contrast(&self, value: f32) {
        if let Ok(mut c) = self.contrast.lock() {
            // Convertir de 0-100 a 0.5-2.0
            *c = 0.5 + (value / 100.0) * 1.5;
            println!("[IMAGE] Contraste: {:.2}", *c);
        }
    }

    pub fn set_threshold(&self, value: u8) {
        if let Ok(mut t) = self.threshold.lock() {
            t[0] = value;
            t[1] = value;
            println!("[THRESHOLD] Configurado ambos ojos a: {}", value);
        }
    }

    /// Configura el threshold para cada ojo por separado
    pub fn set_thresholds(&self, right: u8, left: u8) {
        if let Ok(mut t) = self.threshold.lock() {
            t[0] = right;
            t[1] = left;
            println!("[THRESHOLD] Der={}, Izq={}", right, left);
        }
    }

    pub fn set_nose_width(&self, value: f32) {
        if let Ok(mut n) = self.nose_width.lock() {
            *n = value;
        }
    }

    pub fn set_eye_height(&self, value: f32) {
        if let Ok(mut e) = self.eye_height.lock() {
            *e = value;
        }
    }

    /// Configura la ROI manual del ojo derecho
    pub fn set_manual_roi_right(&self, top: f32, bottom: f32, nasal: f32, temporal: f32) {
        if let Ok(mut roi) = self.manual_roi_right.lock() {
            roi.top = top.clamp(0.0, 1.0);
            roi.bottom = bottom.clamp(0.0, 1.0);
            roi.nasal = nasal.clamp(0.0, 1.0);
            roi.temporal = temporal.clamp(0.0, 1.0);
            println!("[ROI] Ojo derecho configurado: top={:.2}, bottom={:.2}, nasal={:.2}, temporal={:.2}",
                roi.top, roi.bottom, roi.nasal, roi.temporal);
        }
    }

    /// Configura la ROI manual del ojo izquierdo
    pub fn set_manual_roi_left(&self, top: f32, bottom: f32, nasal: f32, temporal: f32) {
        if let Ok(mut roi) = self.manual_roi_left.lock() {
            roi.top = top.clamp(0.0, 1.0);
            roi.bottom = bottom.clamp(0.0, 1.0);
            roi.nasal = nasal.clamp(0.0, 1.0);
            roi.temporal = temporal.clamp(0.0, 1.0);
            println!("[ROI] Ojo izquierdo configurado: top={:.2}, bottom={:.2}, nasal={:.2}, temporal={:.2}",
                roi.top, roi.bottom, roi.nasal, roi.temporal);
        }
    }

    /// Obtiene las ROIs manuales actuales
    pub fn get_manual_rois(&self) -> (ManualEyeRoi, ManualEyeRoi) {
        let right = self.manual_roi_right.lock().map(|r| *r).unwrap_or_default();
        let left = self.manual_roi_left.lock().map(|l| *l).unwrap_or_default();
        (right, left)
    }

    /// Activa o desactiva YOLO
    pub fn set_use_yolo(&self, enabled: bool) {
        self.use_yolo.store(enabled, Ordering::SeqCst);
        println!("[YOLO] {}", if enabled { "Activado" } else { "Desactivado - usando ROI manual" });
    }

    /// Activa o desactiva el modo debug (muestra máscaras de umbralización)
    pub fn set_show_debug(&self, enabled: bool) {
        self.show_debug.store(enabled, Ordering::SeqCst);
        println!("[DEBUG] Modo debug {}", if enabled { "activado - mostrando máscaras" } else { "desactivado" });
    }

    /// Configura el sigma del suavizado gaussiano (mínimo 0.1)
    pub fn set_smooth(&self, sigma: f32) {
        if let Ok(mut s) = self.smooth_sigma.lock() {
            *s = sigma.clamp(0.1, 10.0); // Mínimo 0.1 para evitar panic
            println!("[SMOOTH] Sigma configurado a: {:.1}", *s);
        }
    }

    /// Obtiene el valor actual de smooth
    pub fn get_smooth(&self) -> f32 {
        self.smooth_sigma.lock().map(|s| *s).unwrap_or(2.5)
    }

    pub fn start_capture(&self, camera_id: u32, width: u32, height: u32, fps: u32, model_path: String) -> Result<(), String> {
        // Usar compare_exchange para evitar múltiples llamadas concurrentes
        if self.starting.compare_exchange(false, true, Ordering::SeqCst, Ordering::SeqCst).is_err() {
            // Ya hay otra llamada en progreso, ignorar esta
            return Ok(());
        }

        // Si ya está corriendo, primero detener y esperar
        if self.running.load(Ordering::SeqCst) {
            self.running.store(false, Ordering::SeqCst);
            // Esperar a que el thread anterior libere la cámara
            std::thread::sleep(std::time::Duration::from_millis(300));
        }

        self.running.store(true, Ordering::SeqCst);
        println!("[SIEV] Iniciando captura: cámara={}, {}x{}@{}", camera_id, width, height, fps);

        // Liberar el flag de starting
        self.starting.store(false, Ordering::SeqCst);
        let running = self.running.clone();
        let ws = self.ws_server.clone();
        let eye_proc = self.eye_processor.clone();
        let threshold_ref = self.threshold.clone();
        let erode_ref = self.erode.clone();
        let nose_ref = self.nose_width.clone();
        let eye_h_ref = self.eye_height.clone();
        let use_yolo_ref = self.use_yolo.clone();
        let yolo_freq_ref = self.yolo_frequency.clone();
        let manual_roi_right_ref = self.manual_roi_right.clone();
        let manual_roi_left_ref = self.manual_roi_left.clone();
        let smooth_ref = self.smooth_sigma.clone();
        let brightness_ref = self.brightness.clone();
        let contrast_ref = self.contrast.clone();
        let show_debug_ref = self.show_debug.clone();
        let recorder_ref = self.active_recorder.clone();
        let video_recorder_ref = self.active_video_recorder.clone();
        let capture_w_ref = self.capture_width.clone();
        let capture_h_ref = self.capture_height.clone();

        thread::spawn(move || {
            // Abrir cámara con fallback de formatos
            let index = CameraIndex::Index(camera_id);

            // Lista de formatos a intentar (el solicitado primero, luego fallbacks)
            let formats_to_try = [
                (width, height, fps),
                (width, height, 240),  // Mismo tamaño, FPS alto
                (width, height, 120),  // Mismo tamaño, FPS medio
                (width, height, 60),   // Mismo tamaño, FPS bajo
                (640, 480, 120),       // Formato común
                (640, 480, 60),
                (640, 400, 240),
                (640, 360, 240),
                (800, 600, 120),
                (1280, 720, 120),
            ];

            let mut nokhwa_camera: Option<Camera> = None;
            let mut v4l_stream: Option<v4l::io::mmap::Stream> = None;
            let mut actual_format = (width, height);

            // Intentar nokhwa primero
            for (w, h, f) in formats_to_try {
                let format = CameraFormat::new(Resolution::new(w, h), FrameFormat::MJPEG, f);
                let requested = RequestedFormat::new::<LumaFormat>(RequestedFormatType::Closest(format));

                match Camera::new(index.clone(), requested) {
                    Ok(mut c) => {
                        if c.open_stream().is_ok() {
                            if w != width || h != height || f != fps {
                                println!("[SIEV] Formato {}x{}@{} no disponible, usando {}x{}@{}", width, height, fps, w, h, f);
                            }
                            actual_format = (w, h);
                            nokhwa_camera = Some(c);
                            break;
                        }
                    }
                    Err(_) => continue,
                }
            }

            // Si nokhwa falló, intentar v4l directo
            if nokhwa_camera.is_none() {
                println!("[SIEV] nokhwa falló para cámara {}, intentando v4l directo...", camera_id);
                if let Ok(dev) = v4l::Device::new(camera_id as usize) {
                    let mjpg = v4l::FourCC::new(b"MJPG");
                    let mut opened = false;

                    for &(w, h, _f) in &formats_to_try {
                        let fmt = v4l::Format::new(w, h, mjpg);
                        match V4lCapture::set_format(&dev, &fmt) {
                            Ok(actual) if actual.fourcc == mjpg => {
                                match v4l::io::mmap::Stream::with_buffers(&dev, v4l::buffer::Type::VideoCapture, 4) {
                                    Ok(stream) => {
                                        actual_format = (actual.width, actual.height);
                                        println!("[SIEV] Cámara {} abierta con v4l directo: {}x{}", camera_id, actual.width, actual.height);
                                        v4l_stream = Some(stream);
                                        opened = true;
                                        break;
                                    }
                                    Err(e) => {
                                        println!("[SIEV] v4l stream falló para {}x{}: {:?}", w, h, e);
                                        continue;
                                    }
                                }
                            }
                            _ => continue,
                        }
                    }

                    if !opened {
                        // Intentar sin especificar formato (usar el default de la cámara)
                        if let Ok(current_fmt) = V4lCapture::format(&dev) {
                            if let Ok(stream) = v4l::io::mmap::Stream::with_buffers(&dev, v4l::buffer::Type::VideoCapture, 4) {
                                actual_format = (current_fmt.width, current_fmt.height);
                                println!("[SIEV] Cámara {} abierta con formato default v4l: {}x{} {:?}",
                                    camera_id, current_fmt.width, current_fmt.height, current_fmt.fourcc);
                                v4l_stream = Some(stream);
                            }
                        }
                    }
                }
            }

            if nokhwa_camera.is_none() && v4l_stream.is_none() {
                eprintln!("[SIEV] Error: No se pudo abrir la cámara {} con ningún método", camera_id);
                running.store(false, Ordering::SeqCst);
                return;
            }

            if v4l_stream.is_some() {
                println!("[SIEV] Usando captura v4l directa");
            }

            let (width, height) = actual_format;

            // Store capture dimensions for external use (e.g., video recorder)
            {
                let mut cw = capture_w_ref.lock().unwrap();
                *cw = width;
                let mut ch = capture_h_ref.lock().unwrap();
                *ch = height;
            }

            // NOTA: No configuramos auto-exposición aquí porque causa panic en algunas webcams
            // La exposición se puede ajustar manualmente desde la UI si es necesario

            // Pre-configuración de Zune-JPEG
            let zune_options = DecoderOptions::default().jpeg_set_out_colorspace(ColorSpace::Luma);

            // Cargar modelo YOLO
            println!("[SIEV] Intentando cargar modelo: {}", model_path);
            let session = match Session::builder()
                .and_then(|b| b.with_intra_threads(1))
                .and_then(|b| b.commit_from_file(&model_path))
            {
                Ok(s) => {
                    println!("[SIEV] ✓ Modelo ONNX cargado exitosamente");
                    Some(s)
                }
                Err(e) => {
                    eprintln!("[SIEV] ✗ Error cargando modelo: {:?}", e);
                    None
                }
            };

            if session.is_none() {
                eprintln!("[SIEV] IA no cargada. Usando modo manual. Ruta: {}", model_path);
            }

            let mut session = session;
            let mut last_ui_time = std::time::Instant::now();
            let mut last_fps_time = std::time::Instant::now();
            let mut frame_count: u64 = 0;
            let mut fps_frame_count: u32 = 0;
            let mut total_proc_time = std::time::Duration::from_secs(0);

            // Buffers reutilizables para zero-allocation
            let mut scratch_gray_right = GrayImage::new(1, 1);
            let mut scratch_thresh_right = GrayImage::new(1, 1);
            let mut scratch_gray_left = GrayImage::new(1, 1);
            let mut scratch_thresh_left = GrayImage::new(1, 1);

            // Cajas de detección YOLO (coordenadas en la imagen combinada)
            // [x1, y1, x2, y2] para cada ojo en la imagen combinada
            let mut yolo_box_right: Option<[u32; 4]> = None;
            let mut yolo_box_left: Option<[u32; 4]> = None;

            // Variables de estado persistente para matemáticas refinadas
            let mut last_threshold_right = 40u8;
            let mut last_threshold_left = 40u8;
            let mut last_pupil_right: Option<RustPupilResult> = None;
            let mut last_pupil_left: Option<RustPupilResult> = None;

            println!("[SIEV] Iniciando bucle de captura...");

            while running.load(Ordering::SeqCst) {
                // Capturar frame desde nokhwa o v4l
                let frame_bytes: Vec<u8> = if let Some(ref mut cam) = nokhwa_camera {
                    match cam.frame() {
                        Ok(f) => f.buffer().to_vec(),
                        Err(e) => {
                            if frame_count == 0 { println!("[CAM] Error capturando: {:?}", e); }
                            continue;
                        }
                    }
                } else if let Some(ref mut stream) = v4l_stream {
                    match V4lCaptureStream::next(stream) {
                        Ok((buf, meta)) => buf[..meta.bytesused as usize].to_vec(),
                        Err(e) => {
                            if frame_count == 0 { println!("[CAM] Error capturando v4l: {:?}", e); }
                            continue;
                        }
                    }
                } else {
                    break;
                };

                let start_proc = std::time::Instant::now();

                // DECODIFICACIÓN TURBO (Zune-JPEG)
                let mut decoder = JpegDecoder::new_with_options(&frame_bytes, zune_options);
                
                let pixels = match decoder.decode() {
                    Ok(p) => p,
                    Err(_) => continue,
                };

                let img = match ImageBuffer::<Luma<u8>, Vec<u8>>::from_vec(width, height, pixels) {
                    Some(i) => i,
                    None => continue,
                };

                if frame_count == 0 {
                    println!("[CAM] Primer frame capturado: {}x{}", img.width(), img.height());
                }

                let (w, h) = (img.width(), img.height());

                // Obtener parámetros
                let nose_w = *nose_ref.lock().unwrap();
                let eye_h = *eye_h_ref.lock().unwrap();
                let thresholds = *threshold_ref.lock().unwrap();
                let erodes = *erode_ref.lock().unwrap();
                let yolo_freq = *yolo_freq_ref.lock().unwrap();
                let smooth_sigma = *smooth_ref.lock().unwrap();
                let brightness_val = *brightness_ref.lock().unwrap();
                let contrast_val = *contrast_ref.lock().unwrap();

                // ===== PASO 1: Extraer ROIs de ambos ojos =====
                let roi_nose = (w as f32 * nose_w) as u32;
                let roi_y = (h as f32 * 0.1) as u32;
                let roi_height = (h as f32 * eye_h * 2.0) as u32;
                let eyes_width = w - roi_nose;
                let roi_eye_width = eyes_width / 2;

                // ROI ojo derecho (izquierda de la imagen)
                let roi_r_x1 = 0;
                let roi_r_x2 = roi_eye_width;
                let roi_r_y1 = roi_y;
                let roi_r_y2 = (roi_y + roi_height).min(h);

                // ROI ojo izquierdo (derecha de la imagen)
                let roi_l_x1 = roi_eye_width + roi_nose;
                let roi_l_x2 = w;
                let roi_l_y1 = roi_y;
                let roi_l_y2 = (roi_y + roi_height).min(h);

                // Extraer sub-imágenes
                let roi_right_w = roi_r_x2 - roi_r_x1;
                let roi_right_h = roi_r_y2 - roi_r_y1;
                let roi_left_w = roi_l_x2 - roi_l_x1;
                let roi_left_h = roi_l_y2 - roi_l_y1;

                if roi_right_w == 0 || roi_right_h == 0 || roi_left_w == 0 || roi_left_h == 0 {
                    continue;
                }

                // ===== PASO 2: Crear imagen combinada =====
                let combined_width = roi_right_w + roi_left_w;
                let combined_height = roi_right_h.max(roi_left_h);
                let mut combined = GrayImage::new(combined_width, combined_height);

                // Optimización: Copia por bloques (memcpy) por cada fila
                let img_stride = w as usize;
                let combined_stride = combined_width as usize;
                let img_raw = img.as_raw();
                let combined_raw = combined.as_flat_samples_mut().samples;

                // Copiar ROI derecho (lado izquierdo de combined)
                for y in 0..roi_right_h {
                    let src_start = ((roi_r_y1 + y) as usize * img_stride) + roi_r_x1 as usize;
                    let src_end = src_start + roi_right_w as usize;
                    let dst_start = y as usize * combined_stride;
                    let dst_end = dst_start + roi_right_w as usize;
                    
                    if src_end <= img_raw.len() && dst_end <= combined_raw.len() {
                        combined_raw[dst_start..dst_end].copy_from_slice(&img_raw[src_start..src_end]);
                    }
                }

                // Copiar ROI izquierdo (lado derecho de combined)
                for y in 0..roi_left_h {
                    let src_start = ((roi_l_y1 + y) as usize * img_stride) + roi_l_x1 as usize;
                    let src_end = src_start + roi_left_w as usize;
                    let dst_start = (y as usize * combined_stride) + roi_right_w as usize;
                    let dst_end = dst_start + roi_left_w as usize;
                    
                    if src_end <= img_raw.len() && dst_end <= combined_raw.len() {
                        combined_raw[dst_start..dst_end].copy_from_slice(&img_raw[src_start..src_end]);
                    }
                }

                // ===== PASO 2.5: Aplicar brillo y contraste optimizado =====
                Self::apply_brightness_contrast_luma(&mut combined, brightness_val, contrast_val);

                // Send clean frame (no UI marks) to video recorder if active
                if let Ok(guard) = video_recorder_ref.lock() {
                    if let Some(ref vrec) = *guard {
                        vrec.send_frame(combined.clone());
                    }
                }

                // ===== PASO 3: Ejecutar YOLO cada N frames =====
                let use_yolo = use_yolo_ref.load(Ordering::SeqCst);
                if use_yolo {
                    if let Some(ref mut sess) = session {
                        if frame_count % yolo_freq as u64 == 0 {
                            match Self::run_yolo_inference(sess, &combined) {
                                Some((box_r, box_l)) => {
                                    yolo_box_right = Some(box_r);
                                    yolo_box_left = Some(box_l);
                                }
                                None => {}
                            }
                        }
                    }
                }

                // ===== PASO 4: Definir regiones de búsqueda de pupila =====
                // Obtener ROIs manuales
                let manual_right = *manual_roi_right_ref.lock().unwrap();
                let manual_left = *manual_roi_left_ref.lock().unwrap();

                // Calcular cajas de búsqueda
                let search_box_right = if let Some(yolo_box) = yolo_box_right {
                    yolo_box
                } else {
                    let x1 = (roi_right_w as f32 * manual_right.temporal) as u32;
                    let x2 = (roi_right_w as f32 * manual_right.nasal) as u32;
                    let y1 = (combined_height as f32 * manual_right.top) as u32;
                    let y2 = (combined_height as f32 * manual_right.bottom) as u32;
                    [x1, y1, x2.max(x1 + 1), y2.max(y1 + 1)]
                };

                let search_box_left = if let Some(yolo_box) = yolo_box_left {
                    yolo_box
                } else {
                    let left_start = roi_right_w;
                    let left_width = roi_left_w;
                    let x1 = left_start + (left_width as f32 * manual_left.nasal) as u32;
                    let x2 = left_start + (left_width as f32 * manual_left.temporal) as u32;
                    let y1 = (combined_height as f32 * manual_left.top) as u32;
                    let y2 = (combined_height as f32 * manual_left.bottom) as u32;
                    [x1, y1, x2.max(x1 + 1), y2.max(y1 + 1)]
                };

                // ===== PASO 5: Detectar pupilas con Matemáticas Refinadas =====
                let pupil_right = Self::detect_pupil_math_refined(
                    &combined,
                    search_box_right,
                    thresholds[0],
                    &mut last_threshold_right,
                    erodes[0],
                    smooth_sigma,
                    last_pupil_right,
                    &mut scratch_gray_right,
                    &mut scratch_thresh_right
                );
                last_pupil_right = pupil_right;

                let pupil_left = Self::detect_pupil_math_refined(
                    &combined,
                    search_box_left,
                    thresholds[1],
                    &mut last_threshold_left,
                    erodes[1],
                    smooth_sigma,
                    last_pupil_left,
                    &mut scratch_gray_left,
                    &mut scratch_thresh_left
                );
                last_pupil_left = pupil_left;

                // Convertir coordenadas
                let mut pupil_pos: [Option<[f64; 2]>; 2] = [None, None];
                if let Some(pr) = pupil_right {
                    if pr.found { pupil_pos[1] = Some([pr.center_x as f64, (pr.center_y as f64) * -1.0]); }
                }
                if let Some(pl) = pupil_left {
                    if pl.found { pupil_pos[0] = Some([pl.center_x as f64, (pl.center_y as f64) * -1.0]); }
                }

                // ===== PASO 6: Enviar datos de ojos =====
                let raw_data = RawEyeData {
                    left_eye: pupil_pos[0],
                    right_eye: pupil_pos[1],
                    processed: None,
                    timestamp: chrono::Utc::now().timestamp_millis() as f64 / 1000.0,
                };

                let processed = {
                    let mut p = eye_proc.lock().unwrap();
                    p.process(raw_data)
                };
                ws.broadcast(&WsMessage::EyeData(processed.clone()));

                // Send to session recorder if active
                if let Ok(guard) = recorder_ref.lock() {
                    if let Some(ref rec) = *guard {
                        rec.record(processed);
                    }
                }

                // ===== PASO 7: Enviar imagen a UI (30 FPS) =====
                let show_debug = show_debug_ref.load(Ordering::SeqCst);
                if last_ui_time.elapsed().as_millis() > 33 {
                    // Convertir a RGB solo para visualización
                    let mut display = DynamicImage::ImageLuma8(combined.clone()).to_rgb8();

                    // Si modo debug está activo, superponer máscaras de umbralización
                    if show_debug {
                        // El overlay dinámico ahora debe ajustarse a la última ROI de búsqueda (Offset relativo)
                        let get_mask_box = |p: Option<RustPupilResult>, base_roi: [u32; 4], mask_w: u32, mask_h: u32| -> [u32; 4] {
                            if let Some(prev) = p {
                                if prev.found {
                                    let margin = (prev.radius * 2.5) as u32;
                                    let px = (prev.center_x - base_roi[0] as f32) as i32;
                                    let py = (prev.center_y - base_roi[1] as f32) as i32;
                                    let sx = (base_roi[0] as i32 + px - margin as i32).max(base_roi[0] as i32) as u32;
                                    let sy = (base_roi[1] as i32 + py - margin as i32).max(base_roi[1] as i32) as u32;
                                    [sx, sy, sx + mask_w, sy + mask_h]
                                } else { base_roi }
                            } else { base_roi }
                        };

                        let box_r = get_mask_box(last_pupil_right, search_box_right, scratch_thresh_right.width(), scratch_thresh_right.height());
                        let box_l = get_mask_box(last_pupil_left, search_box_left, scratch_thresh_left.width(), scratch_thresh_left.height());

                        Self::overlay_mask(&mut display, &scratch_thresh_right, box_r, [255, 0, 0], 0.5);
                        Self::overlay_mask(&mut display, &scratch_thresh_left, box_l, [0, 191, 255], 0.5);
                    }

                    // Dibujar cajas de búsqueda originales
                    let box_color_r = if yolo_box_right.is_some() { [0, 255, 0] } else { [255, 255, 0] };
                    let box_color_l = if yolo_box_left.is_some() { [0, 255, 0] } else { [255, 255, 0] };

                    Self::draw_box(&mut display, search_box_right, box_color_r);
                    Self::draw_box(&mut display, search_box_left, box_color_l);

                    // Etiquetas
                    Self::draw_label(&mut display, search_box_right[0] + 2, search_box_right[1] + 2, "OD", [255, 0, 0]);
                    Self::draw_label(&mut display, search_box_left[0] + 2, search_box_left[1] + 2, "OI", [0, 191, 255]);

                    // Dibujar pupilas detectadas
                    if let Some(pr) = last_pupil_right {
                        if pr.found {
                            Self::draw_crosshair(&mut display, pr.center_x as u32, pr.center_y as u32, pr.radius as u32, [255, 0, 0]);
                        }
                    }
                    if let Some(pl) = last_pupil_left {
                        if pl.found {
                            Self::draw_crosshair(&mut display, pl.center_x as u32, pl.center_y as u32, pl.radius as u32, [0, 191, 255]);
                        }
                    }

                    // Codificar y enviar JPEG
                    let mut jpeg_bytes = Vec::new();
                    let mut cursor = Cursor::new(&mut jpeg_bytes);
                    let encoder = JpegEncoder::new_with_quality(&mut cursor, 70);

                    if display.write_with_encoder(encoder).is_ok() {
                        ws.broadcast_binary(jpeg_bytes);
                    }

                    last_ui_time = std::time::Instant::now();
                }

                // Mide cuánto tardó SOLO el procesamiento (CPU pura)
                let processing_duration = start_proc.elapsed();
                total_proc_time += processing_duration;
                
                frame_count += 1;
                fps_frame_count += 1;

                // Calcular métricas cada 1 segundo exacto (Tiempo de pared)
                let elapsed_since_last_log = last_fps_time.elapsed();
                
                if elapsed_since_last_log.as_secs_f32() >= 1.0 {
                    // 1. FPS Reales (Frames entregados / Tiempo real transcurrido)
                    let wall_fps = fps_frame_count as f32 / elapsed_since_last_log.as_secs_f32();
                    
                    // 2. Latencia Promedio (Cuánto tarda la CPU en "pensar" por frame)
                    let avg_proc_ms = (total_proc_time.as_micros() as f32 / fps_frame_count as f32) / 1000.0;
                    
                    // 3. Carga de CPU del Pipeline (Load)
                    let cpu_load_percent = (total_proc_time.as_secs_f32() / elapsed_since_last_log.as_secs_f32()) * 100.0;

                    println!("[PERF] FPS Reales: {:.1} | Latencia CPU: {:.3}ms | Carga Pipeline: {:.1}%", 
                             wall_fps, avg_proc_ms, cpu_load_percent);

                    // Reiniciar contadores
                    last_fps_time = std::time::Instant::now();
                    total_proc_time = std::time::Duration::from_secs(0);
                    fps_frame_count = 0;
                }
            }

            // Limpiar recursos
            if let Some(ref mut cam) = nokhwa_camera {
                cam.stop_stream().ok();
            }
            // v4l_stream se limpia automáticamente al hacer drop
            drop(v4l_stream);
        });

        Ok(())
    }

    /// Ejecuta inferencia YOLO y retorna las cajas de ambos ojos
    fn run_yolo_inference(session: &mut Session, img: &GrayImage) -> Option<([u32; 4], [u32; 4])> {
        let (orig_w, orig_h) = (img.width() as f32, img.height() as f32);

        // Letterboxing: mantener proporción y añadir padding gris (114,114,114)
        let scale = (640.0 / orig_w).min(640.0 / orig_h);
        let new_w = (orig_w * scale) as u32;
        let new_h = (orig_h * scale) as u32;
        let pad_x = (640 - new_w) / 2;
        let pad_y = (640 - new_h) / 2;

        // Redimensionar manteniendo proporción
        let resized = image::imageops::resize(img, new_w, new_h, image::imageops::FilterType::Triangle);

        // Crear imagen 640x640 con padding gris (114,114,114)
        let mut input = Array4::<f32>::zeros((1, 3, 640, 640));
        let gray_val = 114.0 / 255.0;

        // Llenar con gris
        for y in 0..640 {
            for x in 0..640 {
                input[[0, 0, y, x]] = gray_val;
                input[[0, 1, y, x]] = gray_val;
                input[[0, 2, y, x]] = gray_val;
            }
        }

        // Copiar imagen redimensionada al centro, replicando el canal Luma en RGB
        for y in 0..new_h {
            for x in 0..new_w {
                let p = resized.get_pixel(x, y);
                let val = p.0[0] as f32 / 255.0;
                let tx = (pad_x + x) as usize;
                let ty = (pad_y + y) as usize;
                input[[0, 0, ty, tx]] = val; // R
                input[[0, 1, ty, tx]] = val; // G
                input[[0, 2, ty, tx]] = val; // B
            }
        }

        let input_tensor = match ort::value::Value::from_array(input) {
            Ok(t) => t,
            Err(_) => return None
        };

        let outputs = match session.run(ort::inputs![input_tensor]) {
            Ok(o) => o,
            Err(_) => return None
        };

        let output = match outputs.get("output0") {
            Some(o) => match o.try_extract_array::<f32>() {
                Ok(arr) => arr,
                Err(_) => return None
            },
            None => return None
        };

        // Parsear detecciones
        let mut detections = Vec::new();
        let num_boxes = output.shape()[2];

        for i in 0..num_boxes {
            let score = output[[0, 4, i]];
            if score > 0.25 {
                let cx_lb = output[[0, 0, i]];
                let cy_lb = output[[0, 1, i]];
                let bw_lb = output[[0, 2, i]];
                let bh_lb = output[[0, 3, i]];

                let scale = (640.0 / orig_w).min(640.0 / orig_h);
                let pad_x = (640.0 - orig_w * scale) / 2.0;
                let pad_y = (640.0 - orig_h * scale) / 2.0;

                let cx = (cx_lb - pad_x) / scale;
                let cy = (cy_lb - pad_y) / scale;
                let bw = bw_lb / scale;
                let bh = bh_lb / scale;

                detections.push((cx, cy, bw, bh, score));
            }
        }

        detections.sort_by(|a, b| b.4.partial_cmp(&a.4).unwrap());

        if detections.len() >= 2 {
            let mut top2: Vec<_> = detections.into_iter().take(2).collect();
            top2.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap());

            let padding_x = 20.0;
            let padding_y = 40.0;

            let to_box = |d: &(f32, f32, f32, f32, f32)| -> [u32; 4] {
                let x1 = ((d.0 - d.2 / 2.0) - padding_x).max(0.0) as u32;
                let y1 = ((d.1 - d.3 / 2.0) - padding_y).max(0.0) as u32;
                let x2 = ((d.0 + d.2 / 2.0) + padding_x).min(orig_w) as u32;
                let y2 = ((d.1 + d.3 / 2.0) + padding_y).min(orig_h) as u32;
                [x1, y1, x2, y2]
            };

            return Some((to_box(&top2[0]), to_box(&top2[1])));
        }

        None
    }

    /// Detector de pupila optimizado con Precisión Sub-píxel, Tracking y Centroide Ponderado
    fn detect_pupil_math_refined(
        img: &GrayImage,
        roi: [u32; 4],
        manual_threshold: u8,
        last_threshold: &mut u8,
        erode_iter: u8,
        smooth_sigma: f32,
        prev_pupil: Option<RustPupilResult>,
        scratch_gray: &mut GrayImage,
        scratch_thresh: &mut GrayImage
    ) -> Option<RustPupilResult> {
        let (x1, y1, x2, y2) = (roi[0], roi[1], roi[2], roi[3]);
        let full_rw = x2 - x1;
        let full_rh = y2 - y1;

        // --- MEJORA 1: ROI DINÁMICO (Tracking) ---
        let (search_x, search_y, search_w, search_h, offset_x, offset_y) = if let Some(prev) = prev_pupil {
            if prev.found {
                let margin = (prev.radius * 2.5) as u32;
                let px = (prev.center_x - x1 as f32) as i32;
                let py = (prev.center_y - y1 as f32) as i32;
                
                let sx = (px - margin as i32).max(0) as u32;
                let sy = (py - margin as i32).max(0) as u32;
                let sw = (margin * 2).min(full_rw - sx);
                let sh = (margin * 2).min(full_rh - sy);
                
                if sw < 10 || sh < 10 {
                    (0, 0, full_rw, full_rh, 0, 0)
                } else {
                    (sx, sy, sw, sh, sx, sy)
                }
            } else {
                (0, 0, full_rw, full_rh, 0, 0)
            }
        } else {
            (0, 0, full_rw, full_rh, 0, 0)
        };

        if scratch_gray.width() != search_w || scratch_gray.height() != search_h {
            *scratch_gray = GrayImage::new(search_w, search_h);
            *scratch_thresh = GrayImage::new(search_w, search_h);
        }

        // Extracción de ROI (más pequeña si hay tracking)
        let src_stride = img.width() as usize;
        let dst_stride = search_w as usize;
        let src_raw = img.as_raw();
        let dst_raw = scratch_gray.as_flat_samples_mut().samples;

        for y in 0..search_h {
            let src_start = ((y1 + search_y + y) as usize * src_stride) + (x1 + search_x) as usize;
            let src_end = src_start + search_w as usize;
            let dst_start = y as usize * dst_stride;
            let dst_end = dst_start + search_w as usize;
            
            if src_end <= src_raw.len() && dst_end <= dst_raw.len() {
                dst_raw[dst_start..dst_end].copy_from_slice(&src_raw[src_start..src_end]);
            }
        }

        let blurred = gaussian_blur_f32(scratch_gray, smooth_sigma);

        // --- MEJORA 2: UMBRAL ESTABILIZADO (Histéresis) ---
        let current_thresh_val = if manual_threshold == 0 {
            let mut hist = [0u32; 256];
            let skip = if search_w > 100 { 2 } else { 1 }; 
            for (i, p) in blurred.pixels().enumerate() {
                if i % skip == 0 { hist[p.0[0] as usize] += 1; }
            }
            
            let target = ((search_w * search_h) / (skip as u32 * skip as u32)) as f32 * 0.15;
            let mut acc = 0u32;
            let mut raw_val = 50u8;
            for (i, &count) in hist.iter().enumerate() {
                acc += count;
                if acc as f32 >= target {
                    raw_val = i as u8;
                    break;
                }
            }

            let smoothed = (*last_threshold as f32 * 0.8) + (raw_val as f32 * 0.2);
            let final_val = smoothed as u8;
            *last_threshold = final_val;
            final_val
        } else {
            manual_threshold
        };

        for (x, y, p) in blurred.enumerate_pixels() {
            let val = if p.0[0] <= current_thresh_val { 255 } else { 0 };
            scratch_thresh.put_pixel(x, y, Luma([val]));
        }

        close_mut(scratch_thresh, Norm::LInf, 2); 
        for _ in 0..erode_iter {
            erode_mut(scratch_thresh, Norm::LInf, 1);
        }

        let contours = find_contours::<i32>(scratch_thresh);
        if contours.is_empty() { return Some(RustPupilResult { center_x: 0.0, center_y: 0.0, radius: 0.0, confidence: 0.0, found: false }); }

        let max_area = (full_rw * full_rh) as f32 * 0.6;
        let min_area = 30.0;
        let mut best_pupil: Option<RustPupilResult> = None;
        let mut max_score = 0.0;

        for contour in contours.iter() {
            let mut min_bcx = search_w as i32; let mut max_bcx = 0;
            let mut min_bcy = search_h as i32; let mut max_bcy = 0;
            for p in &contour.points {
                if p.x < min_bcx { min_bcx = p.x; }
                if p.x > max_bcx { max_bcx = p.x; }
                if p.y < min_bcy { min_bcy = p.y; }
                if p.y > max_bcy { max_bcy = p.y; }
            }

            // --- MEJORA 3: CENTROIDE PONDERADO (Weighted Moments) ---
            let mut m00 = 0.0;
            let mut m10_w = 0.0;
            let mut m01_w = 0.0;
            let mut weight_sum = 0.0;

            for y in min_bcy.max(0)..=max_bcy.min(search_h as i32 - 1) {
                for x in min_bcx.max(0)..=max_bcx.min(search_w as i32 - 1) {
                    if scratch_thresh.get_pixel(x as u32, y as u32).0[0] > 128 {
                        m00 += 1.0;
                        let intensity = blurred.get_pixel(x as u32, y as u32).0[0] as f32;
                        let weight = (255.0 - intensity).powi(2); 
                        m10_w += x as f32 * weight;
                        m01_w += y as f32 * weight;
                        weight_sum += weight;
                    }
                }
            }

            let area = m00;
            if area < min_area || area > max_area { continue; }

            let perimeter_val = perimeter(&contour.points);
            if perimeter_val == 0.0 { continue; }
            let circularity = (4.0 * std::f32::consts::PI * area) / (perimeter_val.powi(2) as f32);
            if circularity < 0.55 { continue; }

            let score = area * circularity; 

            if score > max_score {
                let center_x = if weight_sum > 0.0 { m10_w / weight_sum } else { 0.0 };
                let center_y = if weight_sum > 0.0 { m01_w / weight_sum } else { 0.0 };
                let radius = (area / std::f32::consts::PI).sqrt();

                max_score = score;
                best_pupil = Some(RustPupilResult {
                    center_x: x1 as f32 + offset_x as f32 + center_x,
                    center_y: y1 as f32 + offset_y as f32 + center_y,
                    radius,
                    confidence: circularity.min(1.0),
                    found: true,
                });
            }
        }

        best_pupil.or(Some(RustPupilResult {
            center_x: 0.0, center_y: 0.0, radius: 0.0, confidence: 0.0, found: false
        }))
    }

    /// Dibuja un rectángulo en buffer RGB
    fn draw_box(img: &mut ImageBuffer<Rgb<u8>, Vec<u8>>, roi: [u32; 4], color: [u8; 3]) {
        let (x1, y1, x2, y2) = (roi[0], roi[1], roi[2].saturating_sub(1), roi[3].saturating_sub(1));
        let (w, h) = (img.width(), img.height());

        for x in x1..=x2.min(w - 1) {
            if y1 < h { img.put_pixel(x, y1, Rgb(color)); }
            if y2 < h { img.put_pixel(x, y2, Rgb(color)); }
        }
        for y in y1..=y2.min(h - 1) {
            if x1 < w { img.put_pixel(x1, y, Rgb(color)); }
            if x2 < w { img.put_pixel(x2, y, Rgb(color)); }
        }
    }

    /// Dibuja una cruz y círculo en buffer RGB
    fn draw_crosshair(img: &mut ImageBuffer<Rgb<u8>, Vec<u8>>, cx: u32, cy: u32, radius: u32, color: [u8; 3]) {
        let (w, h) = (img.width() as i32, img.height() as i32);
        let cx = cx as i32;
        let cy = cy as i32;
        let r = radius as i32;

        let line_len = 5i32;
        for dx in -line_len..=line_len {
            let px = cx + dx;
            if px >= 0 && px < w && cy >= 0 && cy < h {
                img.put_pixel(px as u32, cy as u32, Rgb(color));
            }
        }
        for dy in -line_len..=line_len {
            let py = cy + dy;
            if cx >= 0 && cx < w && py >= 0 && py < h {
                img.put_pixel(cx as u32, py as u32, Rgb(color));
            }
        }

        let steps = 32;
        for i in 0..steps {
            let angle = (i as f32 / steps as f32) * 2.0 * std::f32::consts::PI;
            let px = cx + (r as f32 * angle.cos()) as i32;
            let py = cy + (r as f32 * angle.sin()) as i32;
            if px >= 0 && px < w && py >= 0 && py < h {
                img.put_pixel(px as u32, py as u32, Rgb(color));
            }
        }
    }

    /// Dibuja una etiqueta simple en buffer RGB
    fn draw_label(img: &mut ImageBuffer<Rgb<u8>, Vec<u8>>, x: u32, y: u32, _label: &str, color: [u8; 3]) {
        let (w, h) = (img.width(), img.height());
        for dy in 0..8 {
            for dx in 0..8 {
                let px = x + dx;
                let py = y + dy;
                if px < w && py < h {
                    if dx == 0 || dx == 7 || dy == 0 || dy == 7 {
                        img.put_pixel(px, py, Rgb(color));
                    }
                }
            }
        }
    }

    /// Superpone una máscara en buffer RGB
    fn overlay_mask(img: &mut ImageBuffer<Rgb<u8>, Vec<u8>>, mask: &GrayImage, roi: [u32; 4], color: [u8; 3], alpha: f32) {
        let (x1, y1, _x2, _y2) = (roi[0], roi[1], roi[2], roi[3]);
        let (img_w, img_h) = (img.width(), img.height());
        let (mask_w, mask_h) = (mask.width(), mask.height());

        for my in 0..mask_h {
            for mx in 0..mask_w {
                let mask_val = mask.get_pixel(mx, my).0[0];
                if mask_val > 0 {
                    let px = x1 + mx;
                    let py = y1 + my;
                    if px < img_w && py < img_h {
                        let orig = img.get_pixel(px, py);
                        let blend = |o: u8, c: u8| -> u8 {
                            ((o as f32 * (1.0 - alpha)) + (c as f32 * alpha)) as u8
                        };
                        img.put_pixel(px, py, Rgb([
                            blend(orig.0[0], color[0]),
                            blend(orig.0[1], color[1]),
                            blend(orig.0[2], color[2]),
                        ]));
                    }
                }
            }
        }
    }

    pub fn stop_capture(&self) {
        self.running.store(false, Ordering::SeqCst);
    }

    pub fn get_video_recorder_arc(&self) -> Arc<Mutex<Option<VideoRecorder>>> {
        self.active_video_recorder.clone()
    }

    pub fn get_capture_dimensions(&self) -> (u32, u32) {
        let w = *self.capture_width.lock().unwrap();
        let h = *self.capture_height.lock().unwrap();
        (w, h)
    }

    /// Aplica brillo y contraste optimizado para GrayImage usando LUT
    fn apply_brightness_contrast_luma(img: &mut GrayImage, brightness: i32, contrast: f32) {
        if brightness == 0 && (contrast - 1.0).abs() < 0.01 {
            return;
        }

        let mut lut = [0u8; 256];
        for i in 0..256 {
            let val = i as f32;
            let adjusted = ((val - 128.0) * contrast + 128.0) + brightness as f32;
            lut[i] = adjusted.clamp(0.0, 255.0) as u8;
        }

        for pixel in img.pixels_mut() {
            pixel.0[0] = lut[pixel.0[0] as usize];
        }
    }
}

fn perimeter(points: &[Point<i32>]) -> f64 {
    if points.len() < 2 { return 0.0; }
    let mut p = 0.0;
    for i in 0..points.len() {
        let p1 = points[i];
        let p2 = points[(i + 1) % points.len()];
        let dx = (p1.x - p2.x) as f64;
        let dy = (p1.y - p2.y) as f64;
        p += (dx * dx + dy * dy).sqrt();
    }
    p
}
