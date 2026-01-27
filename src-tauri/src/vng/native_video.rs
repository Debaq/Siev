use std::sync::{Arc, Mutex, atomic::{AtomicBool, Ordering}};
use std::thread;
use std::io::Cursor;
use nokhwa::pixel_format::RgbFormat;
use nokhwa::utils::{CameraIndex, RequestedFormat, RequestedFormatType, CameraFormat, FrameFormat, Resolution};
use nokhwa::Camera;
use image::{GrayImage, ImageBuffer, Rgb, Luma, codecs::jpeg::JpegEncoder};
use imageproc::filter::gaussian_blur_f32;
use imageproc::morphology::{erode_mut, dilate_mut, close_mut};
use imageproc::distance_transform::Norm;
use imageproc::contours::find_contours;
use ort::session::Session;
use ndarray::Array4;
use serde::{Serialize, Deserialize};
use crate::websocket::{WebSocketServer, WsMessage};
use crate::math::processor::{RawEyeData, EyeProcessor};

#[derive(Clone, Serialize)]
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
}

impl NativeVideoManager {
    pub fn new(ws_server: Arc<WebSocketServer>, eye_processor: Arc<Mutex<EyeProcessor>>) -> Self {
        Self {
            running: Arc::new(AtomicBool::new(false)),
            ws_server,
            eye_processor,
            threshold: Arc::new(Mutex::new([40, 40])),
            erode: Arc::new(Mutex::new([1, 1])),
            nose_width: Arc::new(Mutex::new(0.25)),
            eye_height: Arc::new(Mutex::new(0.25)),
            use_yolo: Arc::new(AtomicBool::new(false)), // YOLO desactivado por defecto
            yolo_frequency: Arc::new(Mutex::new(10)),
            manual_roi_right: Arc::new(Mutex::new(ManualEyeRoi::default())),
            manual_roi_left: Arc::new(Mutex::new(ManualEyeRoi::default())),
            smooth_sigma: Arc::new(Mutex::new(2.5)), // Suavizado por defecto
            brightness: Arc::new(Mutex::new(0)),
            contrast: Arc::new(Mutex::new(1.0)),
            show_debug: Arc::new(AtomicBool::new(false)),
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
        if self.running.load(Ordering::SeqCst) {
            return Ok(());
        }

        self.running.store(true, Ordering::SeqCst);
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

        thread::spawn(move || {
            // Abrir cámara
            let index = CameraIndex::Index(camera_id);
            let format = CameraFormat::new(Resolution::new(width, height), FrameFormat::MJPEG, fps);
            let requested = RequestedFormat::new::<RgbFormat>(RequestedFormatType::Exact(format));

            let mut camera = match Camera::new(index, requested) {
                Ok(c) => c,
                Err(e) => {
                    eprintln!("[SIEV] Error abriendo cámara: {}", e);
                    return;
                }
            };

            if camera.open_stream().is_err() {
                eprintln!("[SIEV] Error iniciando stream de cámara");
                return;
            }

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
            let mut frame_count: u64 = 0;

            // Cajas de detección YOLO (coordenadas en la imagen combinada)
            // [x1, y1, x2, y2] para cada ojo en la imagen combinada
            let mut yolo_box_right: Option<[u32; 4]> = None;
            let mut yolo_box_left: Option<[u32; 4]> = None;

            println!("[SIEV] Iniciando bucle de captura...");

            while running.load(Ordering::SeqCst) {
                // Capturar frame
                let frame = match camera.frame() {
                    Ok(f) => f,
                    Err(e) => {
                        if frame_count == 0 { println!("[CAM] Error capturando: {:?}", e); }
                        continue;
                    }
                };
                let img = match frame.decode_image::<RgbFormat>() {
                    Ok(i) => i,
                    Err(e) => {
                        if frame_count == 0 { println!("[CAM] Error decodificando: {:?}", e); }
                        continue;
                    }
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
                let mut combined = ImageBuffer::<Rgb<u8>, Vec<u8>>::new(combined_width, combined_height);

                // Copiar ROI derecho (lado izquierdo de combined)
                for y in 0..roi_right_h {
                    for x in 0..roi_right_w {
                        if let Some(p) = img.get_pixel_checked(roi_r_x1 + x, roi_r_y1 + y) {
                            combined.put_pixel(x, y, *p);
                        }
                    }
                }

                // Copiar ROI izquierdo (lado derecho de combined)
                for y in 0..roi_left_h {
                    for x in 0..roi_left_w {
                        if let Some(p) = img.get_pixel_checked(roi_l_x1 + x, roi_l_y1 + y) {
                            combined.put_pixel(roi_right_w + x, y, *p);
                        }
                    }
                }

                // ===== PASO 2.5: Aplicar brillo y contraste =====
                Self::apply_brightness_contrast(&mut combined, brightness_val, contrast_val);

                // ===== PASO 3: Ejecutar YOLO cada N frames =====
                let use_yolo = use_yolo_ref.load(Ordering::SeqCst);
                if use_yolo {
                    if let Some(ref mut sess) = session {
                        if frame_count % yolo_freq as u64 == 0 {
                            println!("[YOLO] Frame {}: ejecutando inferencia...", frame_count);
                            match Self::run_yolo_inference(sess, &combined) {
                                Some((box_r, box_l)) => {
                                    println!("[YOLO] ✓ Detectados! R:{:?} L:{:?}", box_r, box_l);
                                    yolo_box_right = Some(box_r);
                                    yolo_box_left = Some(box_l);
                                }
                                None => {
                                    println!("[YOLO] ✗ No se detectaron 2 ojos");
                                }
                            }
                        }
                    } else {
                        if frame_count == 0 {
                            println!("[YOLO] Session es None - modelo no cargado");
                        }
                    }
                } else {
                    if frame_count == 0 {
                        println!("[YOLO] use_yolo está desactivado");
                    }
                }

                // ===== PASO 4: Definir regiones de búsqueda de pupila =====
                // Obtener ROIs manuales
                let manual_right = *manual_roi_right_ref.lock().unwrap();
                let manual_left = *manual_roi_left_ref.lock().unwrap();

                // Calcular cajas de búsqueda
                let search_box_right = if let Some(yolo_box) = yolo_box_right {
                    // Si YOLO detectó, usar su caja
                    yolo_box
                } else {
                    // Usar ROI manual para ojo derecho (lado izquierdo de la imagen combinada)
                    // Para el ojo derecho: temporal está a la izquierda, nasal a la derecha
                    let x1 = (roi_right_w as f32 * manual_right.temporal) as u32;
                    let x2 = (roi_right_w as f32 * manual_right.nasal) as u32;
                    let y1 = (combined_height as f32 * manual_right.top) as u32;
                    let y2 = (combined_height as f32 * manual_right.bottom) as u32;
                    [x1, y1, x2.max(x1 + 1), y2.max(y1 + 1)]
                };

                let search_box_left = if let Some(yolo_box) = yolo_box_left {
                    // Si YOLO detectó, usar su caja
                    yolo_box
                } else {
                    // Usar ROI manual para ojo izquierdo (lado derecho de la imagen combinada)
                    // Para el ojo izquierdo: nasal está a la izquierda, temporal a la derecha
                    let left_start = roi_right_w;
                    let left_width = roi_left_w;
                    let x1 = left_start + (left_width as f32 * manual_left.nasal) as u32;
                    let x2 = left_start + (left_width as f32 * manual_left.temporal) as u32;
                    let y1 = (combined_height as f32 * manual_left.top) as u32;
                    let y2 = (combined_height as f32 * manual_left.bottom) as u32;
                    [x1, y1, x2.max(x1 + 1), y2.max(y1 + 1)]
                };

                // ===== PASO 5: Detectar pupilas en las cajas =====
                let (pupil_right, mask_right) = Self::detect_pupil_legacy(&combined, search_box_right, thresholds[0], erodes[0], smooth_sigma);
                let (pupil_left, mask_left) = Self::detect_pupil_legacy(&combined, search_box_left, thresholds[1], erodes[1], smooth_sigma);

                // Convertir coordenadas a posiciones de pupila
                let mut pupil_pos: [Option<[f64; 2]>; 2] = [None, None];

                if let Some(ref pr) = pupil_right {
                    if pr.found {
                        // Coordenadas en imagen combinada → coordenadas globales
                        pupil_pos[1] = Some([pr.center_x as f64, (pr.center_y as f64) * -1.0]);
                    }
                }

                if let Some(ref pl) = pupil_left {
                    if pl.found {
                        pupil_pos[0] = Some([pl.center_x as f64, (pl.center_y as f64) * -1.0]);
                    }
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
                ws.broadcast(&WsMessage::EyeData(processed));

                // ===== PASO 7: Enviar imagen a UI (30 FPS) =====
                let show_debug = show_debug_ref.load(Ordering::SeqCst);
                if last_ui_time.elapsed().as_millis() > 33 {
                    let mut display = combined.clone();

                    // Si modo debug está activo, superponer máscaras de umbralización
                    if show_debug {
                        // Superponer máscara del ojo derecho (color rojo semi-transparente)
                        if let Some(ref mask) = mask_right {
                            Self::overlay_mask(&mut display, mask, search_box_right, [255, 0, 0], 0.5);
                        }
                        // Superponer máscara del ojo izquierdo (color cyan semi-transparente)
                        if let Some(ref mask) = mask_left {
                            Self::overlay_mask(&mut display, mask, search_box_left, [0, 191, 255], 0.5);
                        }
                    }

                    // Dibujar cajas de búsqueda
                    let box_color_r = if yolo_box_right.is_some() { [0, 255, 0] } else { [255, 255, 0] };
                    let box_color_l = if yolo_box_left.is_some() { [0, 255, 0] } else { [255, 255, 0] };

                    Self::draw_box(&mut display, search_box_right, box_color_r);
                    Self::draw_box(&mut display, search_box_left, box_color_l);

                    // Etiquetas (RGB: Rojo para OD, Cyan para OI)
                    Self::draw_label(&mut display, search_box_right[0] + 2, search_box_right[1] + 2, "OD", [255, 0, 0]);
                    Self::draw_label(&mut display, search_box_left[0] + 2, search_box_left[1] + 2, "OI", [0, 191, 255]);

                    // Dibujar pupilas detectadas
                    if let Some(ref pr) = pupil_right {
                        if pr.found {
                            Self::draw_crosshair(&mut display, pr.center_x as u32, pr.center_y as u32, pr.radius as u32, [255, 0, 0]);
                        }
                    }
                    if let Some(ref pl) = pupil_left {
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

                frame_count += 1;
            }

            camera.stop_stream().ok();
        });

        Ok(())
    }

    /// Ejecuta inferencia YOLO y retorna las cajas de ambos ojos
    fn run_yolo_inference(session: &mut Session, img: &ImageBuffer<Rgb<u8>, Vec<u8>>) -> Option<([u32; 4], [u32; 4])> {
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

        // Copiar imagen redimensionada al centro
        for y in 0..new_h {
            for x in 0..new_w {
                let p = resized.get_pixel(x, y);
                let tx = (pad_x + x) as usize;
                let ty = (pad_y + y) as usize;
                input[[0, 0, ty, tx]] = p.0[0] as f32 / 255.0; // R
                input[[0, 1, ty, tx]] = p.0[1] as f32 / 255.0; // G
                input[[0, 2, ty, tx]] = p.0[2] as f32 / 255.0; // B
            }
        }

        let input_tensor = match ort::value::Value::from_array(input) {
            Ok(t) => t,
            Err(e) => { println!("[YOLO-ERR] from_array: {:?}", e); return None; }
        };
        println!("[YOLO-DBG] Input tensor creado");

        let outputs = match session.run(ort::inputs![input_tensor]) {
            Ok(o) => o,
            Err(e) => { println!("[YOLO-ERR] session.run: {:?}", e); return None; }
        };
        println!("[YOLO-DBG] Inferencia completada, outputs: {}", outputs.len());

        let output = match outputs.get("output0") {
            Some(o) => match o.try_extract_array::<f32>() {
                Ok(arr) => arr,
                Err(e) => { println!("[YOLO-ERR] extract_array: {:?}", e); return None; }
            },
            None => {
                println!("[YOLO-ERR] No se encontró 'output0'. Keys disponibles: {:?}", outputs.keys().collect::<Vec<_>>());
                return None;
            }
        };
        println!("[YOLO-DBG] Output extraído, shape: {:?}", output.shape());

        // Parsear detecciones
        let mut detections = Vec::new();
        let num_boxes = output.shape()[2];

        // Debug: mostrar forma del output
        println!("[YOLO] Output shape: {:?}, num_boxes: {}", output.shape(), num_boxes);

        // Encontrar el score máximo para debug
        let mut max_score = 0.0f32;
        for i in 0..num_boxes {
            let score = output[[0, 4, i]];
            if score > max_score { max_score = score; }
        }
        println!("[YOLO] Max score encontrado: {:.4}", max_score);

        // Calcular parámetros de letterbox para ajustar coordenadas
        let scale = (640.0 / orig_w).min(640.0 / orig_h);
        let pad_x = (640.0 - orig_w * scale) / 2.0;
        let pad_y = (640.0 - orig_h * scale) / 2.0;

        for i in 0..num_boxes {
            let score = output[[0, 4, i]];
            if score > 0.25 {
                // Coordenadas en espacio 640x640 con letterbox
                let cx_lb = output[[0, 0, i]];
                let cy_lb = output[[0, 1, i]];
                let bw_lb = output[[0, 2, i]];
                let bh_lb = output[[0, 3, i]];

                // Convertir de letterbox a coordenadas originales
                let cx = (cx_lb - pad_x) / scale;
                let cy = (cy_lb - pad_y) / scale;
                let bw = bw_lb / scale;
                let bh = bh_lb / scale;

                detections.push((cx, cy, bw, bh, score));
            }
        }

        // Ordenar por confianza y tomar las 2 mejores
        detections.sort_by(|a, b| b.4.partial_cmp(&a.4).unwrap());

        // Debug: mostrar detecciones
        if !detections.is_empty() {
            println!("[YOLO] {} detecciones encontradas. Mejores scores: {:?}",
                detections.len(),
                detections.iter().take(3).map(|d| d.4).collect::<Vec<_>>());
        }

        if detections.len() >= 2 {
            let mut top2: Vec<_> = detections.into_iter().take(2).collect();
            // Ordenar por X (izquierda a derecha)
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

    /// Detector de pupila estilo "legacy" con threshold + suavizado + contornos
    /// Retorna (resultado_pupila, mascara_umbralizada) - la máscara es útil para modo debug
    fn detect_pupil_legacy(img: &ImageBuffer<Rgb<u8>, Vec<u8>>, roi: [u32; 4], threshold: u8, erode_iter: u8, smooth_sigma: f32) -> (Option<RustPupilResult>, Option<GrayImage>) {
        let (x1, y1, x2, y2) = (roi[0], roi[1], roi[2], roi[3]);

        if x2 <= x1 || y2 <= y1 || x2 > img.width() || y2 > img.height() {
            return (None, None);
        }

        let rw = x2 - x1;
        let rh = y2 - y1;

        // Extraer región en escala de grises (usando canal rojo que suele dar mejor contraste para IR)
        let mut gray = GrayImage::new(rw, rh);
        for y in 0..rh {
            for x in 0..rw {
                if let Some(p) = img.get_pixel_checked(x1 + x, y1 + y) {
                    // Usar canal rojo para mejor contraste con iluminación IR
                    gray.put_pixel(x, y, Luma([p.0[0]]));
                }
            }
        }

        // 1. Blur gaussiano (suavizado configurable)
        let blurred = gaussian_blur_f32(&gray, smooth_sigma);

        // 2. Umbralización
        let mut thresh = GrayImage::new(rw, rh);
        let threshold_val = if threshold == 0 {
            // Auto-threshold: usar percentil bajo
            let mut pixels: Vec<u8> = blurred.pixels().map(|p| p.0[0]).collect();
            pixels.sort();
            let idx = (pixels.len() as f32 * 0.15) as usize;
            pixels.get(idx).copied().unwrap_or(50)
        } else {
            threshold
        };

        for (x, y, p) in blurred.enumerate_pixels() {
            let val = if p.0[0] <= threshold_val { 255 } else { 0 };
            thresh.put_pixel(x, y, Luma([val]));
        }

        // 3. Operaciones morfológicas
        // Erosión para eliminar ruido
        for _ in 0..erode_iter {
            erode_mut(&mut thresh, Norm::LInf, 1);
        }

        // Cierre para conectar regiones
        close_mut(&mut thresh, Norm::LInf, 1);

        // Dilatación ligera
        dilate_mut(&mut thresh, Norm::LInf, 1);

        // 4. Encontrar contornos
        let contours = find_contours::<i32>(&thresh);

        if contours.is_empty() {
            return (Some(RustPupilResult {
                center_x: 0.0,
                center_y: 0.0,
                radius: 0.0,
                confidence: 0.0,
                found: false,
            }), Some(thresh));
        }

        // 5. Filtrar contornos válidos
        let max_area = (rw * rh) as f32 * 0.5;
        let mut valid_contours: Vec<_> = contours
            .iter()
            .filter(|c| {
                let area = c.points.len() as f32;
                area > 20.0 && area < max_area
            })
            .collect();

        if valid_contours.is_empty() {
            return (Some(RustPupilResult {
                center_x: 0.0,
                center_y: 0.0,
                radius: 0.0,
                confidence: 0.0,
                found: false,
            }), Some(thresh));
        }

        // Ordenar por área (mayor primero)
        valid_contours.sort_by(|a, b| b.points.len().cmp(&a.points.len()));

        let largest = &valid_contours[0];
        let area = largest.points.len() as f32;

        // 6. Calcular centro (centroide)
        let mut sum_x = 0.0f32;
        let mut sum_y = 0.0f32;
        for p in &largest.points {
            sum_x += p.x as f32;
            sum_y += p.y as f32;
        }
        let center_x = sum_x / area;
        let center_y = sum_y / area;

        // 7. Calcular radio (mediana de distancias al centro)
        let mut distances: Vec<f32> = largest
            .points
            .iter()
            .map(|p| {
                let dx = p.x as f32 - center_x;
                let dy = p.y as f32 - center_y;
                (dx * dx + dy * dy).sqrt()
            })
            .collect();
        distances.sort_by(|a, b| a.partial_cmp(b).unwrap());

        let radius = if !distances.is_empty() {
            distances[distances.len() / 2]
        } else {
            10.0
        };

        // Limitar radio
        let min_radius = 5.0;
        let max_radius = rw.min(rh) as f32 / 3.0;
        let radius = radius.max(min_radius).min(max_radius);

        // Calcular confianza basada en circularidad aproximada
        let perimeter = largest.points.len() as f32;
        let circularity = if perimeter > 0.0 {
            (4.0 * std::f32::consts::PI * area) / (perimeter * perimeter)
        } else {
            0.0
        };
        let confidence = circularity.min(1.0);

        (Some(RustPupilResult {
            center_x: x1 as f32 + center_x,
            center_y: y1 as f32 + center_y,
            radius,
            confidence,
            found: true,
        }), Some(thresh))
    }

    /// Dibuja un rectángulo
    fn draw_box(img: &mut ImageBuffer<Rgb<u8>, Vec<u8>>, roi: [u32; 4], color: [u8; 3]) {
        let (x1, y1, x2, y2) = (roi[0], roi[1], roi[2].saturating_sub(1), roi[3].saturating_sub(1));
        let (w, h) = (img.width(), img.height());

        // Bordes horizontales
        for x in x1..=x2.min(w - 1) {
            if y1 < h { img.put_pixel(x, y1, Rgb(color)); }
            if y2 < h { img.put_pixel(x, y2, Rgb(color)); }
        }
        // Bordes verticales
        for y in y1..=y2.min(h - 1) {
            if x1 < w { img.put_pixel(x1, y, Rgb(color)); }
            if x2 < w { img.put_pixel(x2, y, Rgb(color)); }
        }
    }

    /// Dibuja una cruz y círculo en la posición de la pupila
    fn draw_crosshair(img: &mut ImageBuffer<Rgb<u8>, Vec<u8>>, cx: u32, cy: u32, radius: u32, color: [u8; 3]) {
        let (w, h) = (img.width() as i32, img.height() as i32);
        let cx = cx as i32;
        let cy = cy as i32;
        let r = radius as i32;

        // Cruz
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

        // Círculo aproximado
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

    /// Dibuja una etiqueta simple (2 caracteres)
    fn draw_label(img: &mut ImageBuffer<Rgb<u8>, Vec<u8>>, x: u32, y: u32, _label: &str, color: [u8; 3]) {
        // Dibujar un pequeño marcador cuadrado como indicador
        let (w, h) = (img.width(), img.height());
        for dy in 0..8 {
            for dx in 0..8 {
                let px = x + dx;
                let py = y + dy;
                if px < w && py < h {
                    // Solo el borde del cuadrado
                    if dx == 0 || dx == 7 || dy == 0 || dy == 7 {
                        img.put_pixel(px, py, Rgb(color));
                    }
                }
            }
        }
    }

    /// Superpone una máscara de umbralización sobre la imagen en la posición del ROI
    /// Los pixeles blancos de la máscara (valor 255) se muestran con el color dado y alpha blending
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
                        // Blend: resultado = original * (1-alpha) + color * alpha
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

    /// Aplica brillo y contraste a una imagen RGB
    fn apply_brightness_contrast(img: &mut ImageBuffer<Rgb<u8>, Vec<u8>>, brightness: i32, contrast: f32) {
        if brightness == 0 && (contrast - 1.0).abs() < 0.01 {
            return; // Sin cambios
        }

        for pixel in img.pixels_mut() {
            for c in 0..3 {
                let val = pixel.0[c] as f32;
                // Aplicar contraste (centrado en 128) y luego brillo
                let adjusted = ((val - 128.0) * contrast + 128.0) + brightness as f32;
                pixel.0[c] = adjusted.clamp(0.0, 255.0) as u8;
            }
        }
    }
}
