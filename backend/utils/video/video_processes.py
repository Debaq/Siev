from ultralytics import YOLO
import cv2
import numpy as np
import torch
import multiprocessing as mp
from multiprocessing import Value, Array
import time
import ctypes
import logging
import sys
from utils.path_utils import get_model_file_path, get_model_file_path_prefer_onnx
from utils.video.simulated_box import SimulatedBox
from utils.video.pupil_detectors import (
    create_pupil_detector, DetectorConfig, PupilResult
)
from utils.v4l2_camera import V4L2Camera

# Use the root logger configured in worker.py
logger = logging.getLogger(__name__)


class VideoProcesses:
    def __init__(self, camera_id=0, cap_width=960,
                 cap_height=540, cap_fps=120,
                 brightness=-21, contrast=50):
        # Configuración de la cámara
        self.camera_id = camera_id
        self.cap_width = cap_width
        self.cap_height = cap_height
        self.cap_fps = cap_fps
        
        # Variables compartidas
        self.running = Value(ctypes.c_bool, True)
        self.frame_queue = mp.Queue(maxsize=2)
        self.detection_queue = mp.Queue(maxsize=2)
        self.result_queue = mp.Queue(maxsize=2)
        
        # Configuración de cámara compartida
        self.nose_width = Value(ctypes.c_float, 0.25)
        self.eye_height = Value(ctypes.c_float, 0.25)

        self.changed_nose = Value(ctypes.c_bool, False)
        self.changed_eye_height = Value(ctypes.c_bool, False)

        self.threslhold = Array('i', [0, 0])
        self.erode = Array('i', [0, 0])
        self.cap_error = Value(ctypes.c_bool, False)
        self.slider_th_pressed = Value(ctypes.c_bool, False)
        
        # Variables compartidas para control de color
        self.brightness = Value(ctypes.c_int, brightness) 
        self.contrast = Value(ctypes.c_int, contrast)    
        self.color_changed = Value(ctypes.c_bool, False)  
        
        # Variables para toggle YOLO/ROI fija
        self.use_yolo = Value(ctypes.c_bool, True)
        self.fixed_roi_updated = Value(ctypes.c_bool, False)

        # Configuración del detector de pupila
        # Modos: 0=legacy, 1=fast, 2=hybrid
        self.pupil_mode = Value(ctypes.c_int, 0)  # Default: legacy

        # Parámetros Fast detector
        self.search_window_multiplier = Value(ctypes.c_float, 3.0)
        self.dark_threshold_percent = Value(ctypes.c_int, 20)
        self.starburst_rays = Value(ctypes.c_int, 16)
        self.starburst_min_gradient = Value(ctypes.c_int, 30)
        self.fallback_threshold = Value(ctypes.c_int, 5)

        # Parámetros Hybrid - Validación y re-adquisición
        self.min_confidence_for_lock = Value(ctypes.c_float, 0.5)  # Confianza mínima para lock
        self.revalidation_interval = Value(ctypes.c_int, 30)  # Frames entre re-validaciones

        # Parámetros Legacy detector - Toggles de etapas
        self.legacy_blur_enabled = Value(ctypes.c_bool, True)
        self.legacy_blur_kernel = Value(ctypes.c_int, 5)
        self.legacy_clahe_enabled = Value(ctypes.c_bool, True)
        self.legacy_clahe_clip_limit = Value(ctypes.c_float, 2.0)
        self.legacy_clahe_grid_size = Value(ctypes.c_int, 8)
        self.legacy_morph_enabled = Value(ctypes.c_bool, True)
        self.legacy_morph_close_iterations = Value(ctypes.c_int, 1)
        self.legacy_morph_dilate_iterations = Value(ctypes.c_int, 1)  
    
        # [x1, y1, x2, y2] para ojo derecho e izquierdo
        roi_right_default = [0, int(cap_height * 0.1), int(cap_width * 0.4), int(cap_height * 0.5)]
        roi_left_default = [int(cap_width * 0.6), int(cap_height * 0.1), 
                            int(cap_width), int(cap_height * 0.5)]
        
        # Usar Arrays compartidos para las ROIs fijas
        self.fixed_roi_right = Array('i', roi_right_default)
        self.fixed_roi_left = Array('i', roi_left_default)

        # Procesos
        self.capture_process = None
        self.detection_process = None
        self.processing_process = None
        
    
    def setup_camera(self):
        """Configura la cámara con los parámetros actuales"""
        print(f"--- INICIANDO CONFIGURACIÓN DE CÁMARA ---", flush=True)
        print(f"Configuración Objetivo: ID={self.camera_id}, Resolución={self.cap_width}x{self.cap_height}, FPS={self.cap_fps}", flush=True)
        print(f"Parámetros Hardware: Brillo={self.brightness.value}, Contraste={self.contrast.value}", flush=True)
        
        # En Linux, CAP_V4L2 es más rápido y estable
        cap = cv2.VideoCapture(self.camera_id)
        
        if not cap.isOpened():
            logger.error(f"ERROR: No se pudo abrir el elemento VideoCapture para el ID {self.camera_id}")
            return cap

        # Obtener nombre del backend
        backend_name = cap.getBackendName()
        print(f"Backend OpenCV: {backend_name}", flush=True)

        # 1. SOLICITAR MJPG
        fourcc_mjpg = cv2.VideoWriter_fourcc('M', 'J', 'P', 'G')
        success_fourcc = cap.set(cv2.CAP_PROP_FOURCC, fourcc_mjpg)
        print(f"Establecer MJPG FourCC: {'ÉXITO' if success_fourcc else 'FALLIDO'}", flush=True)
        
        # 2. CONFIGURAR RESOLUCIÓN
        success_w = cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.cap_width)
        success_h = cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.cap_height)
        print(f"Establecer Resolución {self.cap_width}x{self.cap_height}: Ancho={'OK' if success_w else 'ERR'}, Alto={'OK' if success_h else 'ERR'}", flush=True)
        
        # 3. CONFIGURAR FPS
        success_fps = cap.set(cv2.CAP_PROP_FPS, self.cap_fps)
        print(f"Establecer FPS Objetivo {self.cap_fps}: {'ÉXITO' if success_fps else 'FALLIDO'}", flush=True)
        
        # Otras configuraciones de hardware
        cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        # Configuración robusta vía V4L2 (solo Linux)
        try:
            v4l2_cam = V4L2Camera(f"/dev/video{self.camera_id}")
            v4l2_cam.set_exposure_auto(3)  # 3 = Aperture Priority (Auto Mode)
            v4l2_cam.set_exposure_auto_priority(False)  # Mantener FPS constantes
            print(f"V4L2: Auto-exposición forzada (Aperture Priority) y prioridad de FPS desactivada", flush=True)
        except Exception as e:
            logger.warning(f"No se pudo aplicar configuración V4L2: {e}")
        
        # Verificar configuración real aplicada por el driver
        w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        f = cap.get(cv2.CAP_PROP_FPS)
        fourcc_val = int(cap.get(cv2.CAP_PROP_FOURCC))
        fourcc_str = "".join([chr((fourcc_val >> 8 * i) & 0xFF) for i in range(4)])
        
        print(f"--- ESTADO FINAL DEL ELEMENTO CV ---", flush=True)
        print(f"Resolución Real: {w}x{h}", flush=True)
        print(f"FPS Real: {f}", flush=True)
        print(f"Formato Real (FourCC): {fourcc_str} ({fourcc_val})", flush=True)
        
        # Aplicar brillo/contraste
        success_b = cap.set(cv2.CAP_PROP_BRIGHTNESS, self.brightness.value)
        success_c = cap.set(cv2.CAP_PROP_CONTRAST, self.contrast.value)
        print(f"Establecer Brillo ({self.brightness.value}): {'OK' if success_b else 'ERR'}", flush=True)
        print(f"Establecer Contraste ({self.contrast.value}): {'OK' if success_c else 'ERR'}", flush=True)
        
        print(f"--- CONFIGURACIÓN DE CÁMARA COMPLETADA ---", flush=True)
        return cap
    
    def _try_open_camera(self, max_attempts=5, delay=0.5):
        """Intenta abrir la cámara con reintentos.

        Returns:
            tuple: (cap, success) donde cap es el objeto VideoCapture y success es bool
        """
        for attempt in range(max_attempts):
            if not self.running.value:
                return None, False

            logger.info(f"Attempting to open camera {self.camera_id} to {self.cap_width}x{self.cap_height}@{self.cap_fps} (Attempt {attempt+1}/{max_attempts})")
            cap = self.setup_camera()

            if cap.isOpened():
                # Verificar que podemos leer un frame
                ret, _ = cap.read()
                if ret:
                    return cap, True
                cap.release()
            else:
                cap.release()

            if attempt < max_attempts - 1:
                time.sleep(delay)

        return None, False

    def capture_worker(self):
        """Proceso dedicado exclusivamente a capturar frames"""
        logger.info("Starting capture process")

        # Intentar abrir la cámara con más persistencia
        # Aumentamos intentos y delay para dar tiempo al hardware de liberarse
        cap, success = self._try_open_camera(max_attempts=10, delay=1.0)

        if not success:
            logger.error("Error: Could not open camera after 10 attempts")
            self.cap_error.value = True
            return

        # Obtener primer frame para calcular dimensiones
        ret, init_frame = cap.read()
        if not ret:
            logger.error("Error: Could not read first frame")
            self.cap_error.value = True
            cap.release()
            return

        h, w = init_frame.shape[:2]
        frame_info = {
            'height': h,
            'width': w,
            'roi_y': int(h * 0.1),
            'roi_height': int(h * 0.4),
            'new_height': int(h - (h*0.4))
        }

        # Enviar info del frame al proceso de detección
        self.detection_queue.put(frame_info)

        # FPS de entrada (frames capturados por segundo)
        capture_frame_count = 0
        capture_last_second = time.time()
        fps_avg = 0.0
        consecutive_failures = 0
        max_consecutive_failures = 30  # ~0.5 segundos a 60fps antes de intentar reconectar

        try:
            # Bucle principal de captura optimizado para rendimiento
            while self.running.value:
                if self.color_changed.value:
                    cap.set(cv2.CAP_PROP_BRIGHTNESS, self.brightness.value)
                    cap.set(cv2.CAP_PROP_CONTRAST, self.contrast.value)
                    self.color_changed.value = False

                ret, frame = cap.read()
                if not ret:
                    consecutive_failures += 1

                    if consecutive_failures >= max_consecutive_failures:
                        logger.warning(f"Camera {self.camera_id} lost. Attempting to reconnect...")
                        cap.release()
                        time.sleep(1.0)  # Esperar antes de reconectar

                        # Intentar reconectar
                        cap, success = self._try_open_camera(max_attempts=10, delay=1.0)

                        if not success:
                            logger.error("Error: Could not reconnect camera")
                            self.cap_error.value = True
                            return

                        logger.info(f"Camera {self.camera_id} reconnected successfully")
                        consecutive_failures = 0
                        # Aplicar configuración de brillo/contraste
                        cap.set(cv2.CAP_PROP_BRIGHTNESS, self.brightness.value)
                        cap.set(cv2.CAP_PROP_CONTRAST, self.contrast.value)

                    continue

                # Reset contador de fallos al leer exitosamente
                consecutive_failures = 0
                
                last_time = current_time
                
                # Calcular FPS de entrada (frames capturados por segundo)
                capture_frame_count += 1
                capture_now = time.time()
                capture_elapsed = capture_now - capture_last_second
                if capture_elapsed >= 1.0:
                    fps_avg = capture_frame_count / capture_elapsed
                    capture_frame_count = 0
                    capture_last_second = capture_now
                
                # Poner el frame en la cola solo si no está llena - sin bloqueos
                if not self.frame_queue.full():
                    self.frame_queue.put((frame, fps_avg))
        except Exception as e:
            logger.error(f"Error in capture process: {e}")
        finally:
            # Siempre asegurar la liberación de la cámara
            cap.release()
            logger.info("Capture process finished")
    
    def detection_worker(self):
        """Proceso dedicado a detectar ojos con YOLO"""
        logger.info("Starting detection process")

        # Cargar modelo YOLO - prioriza ONNX si existe
        model_path, model_format = get_model_file_path_prefer_onnx('siev_vng_r01.pt')
        logger.info(f"Loading YOLO model: {model_path} (format: {model_format})")
        model = YOLO(model_path)

        # Optimizaciones para CPU
        if not torch.cuda.is_available():
            torch.set_num_threads(1)
            logger.info(f"Using CPU with {torch.get_num_threads()} threads")
            torch.set_num_interop_threads(1)
        else:
            logger.info("Using GPU for inference")
        # Parámetros para detección
        detect_params = {
            'conf': 0.5,      # Umbral de confianza
            'iou': 0.45,      # Umbral IOU para NMS
            'verbose': False, # Sin mensajes de depuración
            'max_det': 2      # Máximo 2 detecciones (ojos)
        }
        
        # Esperar la información del frame
        frame_info = self.detection_queue.get()
        
        # Variables para controlar frecuencia de detección
        detection_counter = 0
        detection_frequency = 4
        last_boxes = []
        scale_factor = 0.5
        
        while self.running.value:
            if self.frame_queue.empty():
                time.sleep(0.001)
                continue
            
            frame, fps = self.frame_queue.get()
            h, w = frame.shape[:2]
            
            # Actualizar dimensiones ROI si cambió el ancho de nariz
            if self.changed_nose.value:
                self.changed_nose.value = False
                roi_nose = int(w * self.nose_width.value)
            else:
                roi_nose = int(w * self.nose_width.value)


            if self.changed_eye_height.value:
                self.changed_eye_height.value = False
                roi_nose_height = int(h * self.eye_height.value)
            else:
                roi_nose_height = int(h * self.eye_height.value)


            
            # Extraer ROIs
            roi_y = frame_info['roi_y']
            roi_height = frame_info['roi_height']
            eyes_width = w - roi_nose
            roi_eye_width = int(eyes_width / 2)


            
            roi_right_eye = frame[roi_y:roi_y+roi_height, :roi_eye_width]
            roi_left_eye = frame[roi_y:roi_y+roi_height, roi_eye_width+roi_nose:]
            
            #roi_right_eye = frame[0:roi_y+roi_height, :roi_eye_width]
            #roi_left_eye = frame[0:roi_y+roi_height, roi_eye_width+roi_nose:]

            # Verificar ROIs
            if roi_right_eye.size == 0 or roi_left_eye.size == 0:
                continue
            
            # Unir horizontalmente
            combined_roi = np.hstack((roi_right_eye, roi_left_eye))
            
            # Redimensionar para mantener proporción
            current_width = combined_roi.shape[1]
            current_height = combined_roi.shape[0]
            new_width = w
            new_height = int((current_height * new_width) / current_width)
            new_h = frame_info['new_height']
            
            if new_height > new_h:
                new_height = new_h
                new_width = int((current_width * new_height) / current_height)
            
            resized_combined = cv2.resize(combined_roi, (new_width, new_height))
            
            # Crear frame final
            final_frame = np.zeros((new_h, w, 3), dtype=np.uint8)
            y_offset = (new_h - new_height) // 2
            x_offset = (w - new_width) // 2
            final_frame[y_offset:y_offset+new_height, x_offset:x_offset+new_width] = resized_combined


            # Convertir a gris para detección
            gray = cv2.cvtColor(final_frame, cv2.COLOR_BGR2GRAY)
            
            # Solo detectar cada N frames
            if self.use_yolo.value:
                if detection_counter % detection_frequency == 0:
                    roi_frame = final_frame[y_offset:y_offset+new_height, x_offset:x_offset+new_width]
                    small_roi = cv2.resize(roi_frame, None, fx=scale_factor, fy=scale_factor)
                    
                    with torch.no_grad():
                        results = model(small_roi, **detect_params)
                    
                    boxes = []
                    for r in results:
                        boxes = r.boxes.cpu().numpy()
                    
                    if len(boxes) > 0:
                        last_boxes = boxes

                        if len(boxes) >= 2:  # Si se detectaron ambos ojos
                            sorted_boxes = sorted(boxes, key=lambda box: box.xyxy[0][0])
                            
                            # Convertir coordenadas a tamaño original
                            for i, box in enumerate(sorted_boxes[:2]):  # Solo los primeros 2 ojos
                                x1, y1, x2, y2 = map(int, box.xyxy[0])
                                # Escalar a coordenadas de imagen completa
                                x1 = int(x1 / scale_factor) + x_offset
                                y1 = int(y1 / scale_factor) + y_offset
                                x2 = int(x2 / scale_factor) + x_offset
                                y2 = int(y2 / scale_factor) + y_offset
                                
                                # Guardar en ROIs fijas (derecho = 0, izquierdo = 1)
                                if i == 0:  # Ojo derecho (el que aparece más a la izquierda)
                                    self.fixed_roi_right[0] = x1
                                    self.fixed_roi_right[1] = y1
                                    self.fixed_roi_right[2] = x2
                                    self.fixed_roi_right[3] = y2
                                else:  # Ojo izquierdo
                                    self.fixed_roi_left[0] = x1
                                    self.fixed_roi_left[1] = y1
                                    self.fixed_roi_left[2] = x2
                                    self.fixed_roi_left[3] = y2
                else:
                    boxes = last_boxes
            else:
                # MODO ROI FIJA: Crear "boxes" sintéticas desde las ROIs fijas
                boxes = []
                
                # Convertir ROIs fijas a formato compatible con el resto del código
                # Convertir de coordenadas globales a coordenadas de escala
                # Ojo derecho
                x1_r = (self.fixed_roi_right[0] - x_offset) * scale_factor
                y1_r = (self.fixed_roi_right[1] - y_offset) * scale_factor
                x2_r = (self.fixed_roi_right[2] - x_offset) * scale_factor
                y2_r = (self.fixed_roi_right[3] - y_offset) * scale_factor
                
                # Ojo izquierdo
                x1_l = (self.fixed_roi_left[0] - x_offset) * scale_factor
                y1_l = (self.fixed_roi_left[1] - y_offset) * scale_factor
                x2_l = (self.fixed_roi_left[2] - x_offset) * scale_factor
                y2_l = (self.fixed_roi_left[3] - y_offset) * scale_factor
                
                # Crear "boxes" simuladas
                box_right = SimulatedBox(x1_r, y1_r, x2_r, y2_r)
                box_left = SimulatedBox(x1_l, y1_l, x2_l, y2_l)
                
                # Añadir a la lista de boxes (derecho primero, luego izquierdo)
                boxes = [box_right, box_left]
        

            detection_counter += 1
            
            # Pasar datos al proceso de procesamiento
            detection_data = {
                'frame': final_frame,
                'gray': gray,
                'boxes': boxes,
                'y_offset': y_offset,
                'scale_factor': scale_factor,
                'fps': fps,
                'w': w,
                'h': new_h
            }
            
            if not self.result_queue.full():
                self.result_queue.put(detection_data)
        
        logger.info("Detection process finished")
    
    def processing_worker(self):
        """Proceso para procesar resultados y detectar pupilas"""
        logger.info("Starting processing process")

        # Crear detectores para cada ojo
        mode_map = {0: "legacy", 1: "fast", 2: "hybrid"}
        current_mode_value = self.pupil_mode.value
        current_mode = mode_map.get(current_mode_value, "legacy")
        detector_right = create_pupil_detector(current_mode)
        detector_left = create_pupil_detector(current_mode)
        logger.info(f"Pupil detectors initialized in mode: {current_mode}")

        # Variables para tracking de FPS del pipeline (contador por segundo)
        pipeline_frame_count = 0
        pipeline_last_second = time.time()
        pipeline_fps = 0.0

        while self.running.value:
            if self.result_queue.empty():
                time.sleep(0.001)
                continue

            # Verificar si el modo cambió
            if self.pupil_mode.value != current_mode_value:
                current_mode_value = self.pupil_mode.value
                current_mode = mode_map.get(current_mode_value, "legacy")
                detector_right = create_pupil_detector(current_mode)
                detector_left = create_pupil_detector(current_mode)
                logger.info(f"Pupil detectors changed to mode: {current_mode}")

            data = self.result_queue.get()
            final_frame = data['frame']
            gray = data['gray']
            boxes = data['boxes']
            y_offset = data['y_offset']
            scale_factor = data['scale_factor']
            fps = data['fps']
            w = data['w']
            h = data['h']
            # Obtener timestamp para cálculo de velocidad
            timestamp = cv2.getTickCount() / cv2.getTickFrequency()
            
            # Procesar detecciones
            eye_regions = []
            if len(boxes) > 0:
                # Ordenar cajas por coordenada X
                sorted_boxes = sorted(boxes, key=lambda box: box.xyxy[0][0])
                
                for j, box in enumerate(sorted_boxes):
                    # Obtener coordenadas
                    x1_small, y1_small, x2_small, y2_small = box.xyxy[0]
                    
                    # Ajustar coordenadas a la imagen original
                    x1 = int(x1_small / scale_factor)
                    y1 = int(y1_small / scale_factor) + y_offset
                    x2 = int(x2_small / scale_factor)
                    y2 = int(y2_small / scale_factor) + y_offset
                    
                    # Convertir a enteros
                    ex, ey = x1, y1
                    ew, eh = x2 - x1, y2 - y1
                    
                    # Determinar si es ojo derecho
                    image_center_x = w / 2
                    eye_center_x = ex + (ew / 2)
                    is_right_eye = eye_center_x < image_center_x
                    
                    # Verificar límites
                    if ey >= 0 and ey+eh <= h and ex >= 0 and ex+ew <= w and eh > 0 and ew > 0:
                        eye_gray = gray[ey:ey+eh, ex:ex+ew]
                        eye_regions.append((eye_gray, ex, ey, ew, eh, is_right_eye))
            
            # Lista para guardar posiciones de pupilas
            pupil_positions = [None, None]

            # Crear configuración para los detectores
            detector_config = DetectorConfig(
                # Fast detector params
                search_window_multiplier=self.search_window_multiplier.value,
                dark_threshold_percent=self.dark_threshold_percent.value,
                starburst_rays=self.starburst_rays.value,
                starburst_min_gradient=self.starburst_min_gradient.value,
                fallback_threshold=self.fallback_threshold.value,
                # Hybrid params
                min_confidence_for_lock=self.min_confidence_for_lock.value,
                revalidation_interval=self.revalidation_interval.value,
                # Legacy detector params
                legacy_blur_enabled=self.legacy_blur_enabled.value,
                legacy_blur_kernel=self.legacy_blur_kernel.value,
                legacy_clahe_enabled=self.legacy_clahe_enabled.value,
                legacy_clahe_clip_limit=self.legacy_clahe_clip_limit.value,
                legacy_clahe_grid_size=self.legacy_clahe_grid_size.value,
                legacy_morph_enabled=self.legacy_morph_enabled.value,
                legacy_morph_close_iterations=self.legacy_morph_close_iterations.value,
                legacy_morph_dilate_iterations=self.legacy_morph_dilate_iterations.value
            )

            # Procesar cada región
            for data in eye_regions:
                eye_gray, ex, ey, ew, eh, is_right_eye = data

                # Configurar threshold y erode por ojo
                detector_config.threshold_value = self.threslhold[0] if is_right_eye else self.threslhold[1]
                detector_config.erode_value = self.erode[0] if is_right_eye else self.erode[1]

                # Seleccionar detector según ojo
                detector = detector_right if is_right_eye else detector_left

                # Detectar pupila
                result = detector.detect(eye_gray, detector_config)

                if result:
                    mask = result.mask

                    # Determinar color por ojo
                    if is_right_eye:
                        color = (0, 0, 255)  # Rojo para ojo derecho (BGR)
                        label = "OD"
                    else:
                        color = (255, 191, 0)  # Azul claro para ojo izquierdo (BGR)
                        label = "OI"

                    # Siempre mostrar rectángulo ROI
                    cv2.rectangle(final_frame, (ex, ey), (ex+ew, ey+eh), color, 1)

                    # Etiqueta del ojo
                    cv2.putText(final_frame, label, (ex + 2, ey + 12),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA)

                    # Modo debug: mostrar máscara de umbralización
                    # Se muestra incluso si no se encontró pupila, para diagnosticar fallos
                    if self.slider_th_pressed.value:
                        roi = final_frame[ey:ey+eh, ex:ex+ew]
                        # Superponer máscara con transparencia
                        if mask is not None:
                            cv2.addWeighted(roi, 0.7, mask, 0.3, 0, roi)

                        # Mostrar valor de threshold y modo
                        th_val = self.threslhold[0] if is_right_eye else self.threslhold[1]
                        er_val = self.erode[0] if is_right_eye else self.erode[1]
                        mode_label = ["L", "F", "H"][self.pupil_mode.value]
                        th_text = f"TH:{th_val} ER:{er_val} M:{mode_label}"
                        cv2.putText(final_frame, th_text, (ex + 2, ey + eh - 5),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 255, 255), 1, cv2.LINE_AA)

                    # Dibujar círculo y guardar posición SOLO si se encontró
                    if result.found:
                        cx, cy, radius = result.center_x, result.center_y, result.radius

                        # Dibujar círculo de la pupila
                        cv2.circle(final_frame[ey:ey+eh, ex:ex+ew], (cx, cy), radius, color, 1)

                        # Calcular coordenadas absolutas
                        abs_x = ex + cx
                        abs_y = ey + cy

                        # Dibujar cruces en centro de pupila
                        longitud_cruz = 5
                        cv2.line(final_frame, (abs_x - longitud_cruz, abs_y), (abs_x + longitud_cruz, abs_y), color, 1)
                        cv2.line(final_frame, (abs_x, abs_y - longitud_cruz), (abs_x, abs_y + longitud_cruz), color, 1)

                        # Guardar posición
                        abs_y_neg = abs_y * -1
                        if is_right_eye:
                            pupil_positions[0] = [abs_x, abs_y_neg]
                        else:
                            pupil_positions[1] = [abs_x, abs_y_neg]

            # Dibujar indicador de modo debug
            if self.slider_th_pressed.value:
                cv2.putText(final_frame, "DEBUG MODE", (10, 20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)
                # Línea central para visualizar separación de ojos
                center_x = w // 2
                cv2.line(final_frame, (center_x, 0), (center_x, h), (0, 255, 255), 1)
            
            # Calcular FPS del pipeline (frames procesados por segundo)
            pipeline_frame_count += 1
            pipeline_now = time.time()
            elapsed = pipeline_now - pipeline_last_second
            if elapsed >= 1.0:
                pipeline_fps = pipeline_frame_count / elapsed
                pipeline_frame_count = 0
                pipeline_last_second = pipeline_now

            # Convertir a RGB para la UI
            final_frame = cv2.cvtColor(final_frame, cv2.COLOR_BGR2RGB)
            fps_text = f"{fps:.0f}/{pipeline_fps:.0f}"
            lbl_fps_position = (w - 85, 15)
            cv2.putText(final_frame, fps_text, lbl_fps_position,
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (248, 243, 43), 1, cv2.LINE_AA)
            # Publicar resultado final para la UI
            output = {
                'frame': final_frame,
                'pupil_positions': pupil_positions,
                'gray' : gray
            }
            
            self.ui_queue.put(output)
        
        logger.info("Processing process finished")
    
    def process_eye_region(self, data):
        try:
            eye_gray, ex, ey, ew, eh, is_right_eye = data
            
            # 1. PREPROCESAMIENTO OPTIMIZADO
            # Suavizado para reducir ruido pero conservar bordes
            blurred = cv2.GaussianBlur(eye_gray, (5, 5), 0)
            
            # Mejorar contraste - opcional, solo si ayuda
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(blurred)
            #enhanced = blurred  # Usar directamente la imagen suavizada
        
            # 2. UMBRAL MANUAL - como el original, pero con mejor preprocesamiento

            threshold_value = self.threslhold[0] if is_right_eye else self.threslhold[1]
            if threshold_value == 0:
                #implementar para tener diferentes opciones
                otsu_thresh, _ = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                adjusted_thresh = max(0, min(255, otsu_thresh + threshold_value))
                _, thresh = cv2.threshold(enhanced, adjusted_thresh, 255, cv2.THRESH_BINARY_INV)


            else:    
                _, thresh = cv2.threshold(enhanced, threshold_value, 255, cv2.THRESH_BINARY_INV )
            
            # 3. OPERACIONES MORFOLÓGICAS MEJORADAS
            # Usar elementos estructurantes circulares
            kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            kernel_medium = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

            # Aplicar erosión si es necesario (usando parámetro existente)
            erode_value = self.erode[0] if is_right_eye else self.erode[1]
            if erode_value > 0:
                thresh_eroded = cv2.erode(thresh, kernel_small, iterations=erode_value)
            else:
                thresh_eroded = thresh

            # Cerrar para eliminar pequeños huecos (conectar regiones)
            thresh_closed = cv2.morphologyEx(thresh_eroded, cv2.MORPH_CLOSE, kernel_small, iterations=1)
        
            # Dilatar ligeramente para asegurar capturar toda la pupila
            thresh_processed = cv2.dilate(thresh_closed, kernel_small, iterations=1)
        
            # 4. ENCONTRAR Y FILTRAR CONTORNOS
            contours, _ = cv2.findContours(thresh_processed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Crear máscara para visualización
            mask = cv2.cvtColor(thresh_processed, cv2.COLOR_GRAY2BGR)

            #min_area = 10
            #contours = [c for c in contours if cv2.contourArea(c) > min_area]
            #NOTA: no suelo tener contornos pequeños pero si unos muy grandes
        
            if not contours:
                return None
                    
            # Filtrar por área para eliminar ruido
            valid_contours = []
            for c in contours:
                area = cv2.contourArea(c)
                # Ajustar estos umbrales según la resolución
                if area > 20 and area < (ew * eh * 0.5):  # Pupila no debería ser más del 50% del ojo
                    valid_contours.append(c)
            

                #areas = np.array([cv2.contourArea(c) for c in contours])
                #valid_mask = (areas > 20) & (areas < (ew * eh * 0.5))
                #valid_contours = [contours[i] for i in np.where(valid_mask)[0]]

            if not valid_contours:
                return None
        
            # Ordenar por área (mayor primero)
            valid_contours = sorted(valid_contours, key=cv2.contourArea, reverse=True)

            # 5. REGULARIZACIÓN DE CONTORNO
            largest_contour = valid_contours[0]

            # Calcular centro e intentar ajustar mejor al círculo
            M = cv2.moments(largest_contour)
            if M["m00"] != 0:
                center_x = int(M["m10"] / M["m00"])
                center_y = int(M["m01"] / M["m00"])
            else:
                # Si el cálculo del momento falla, usar boundingRect
                x, y, w, h = cv2.boundingRect(largest_contour)
                center_x = x + w // 2
                center_y = y + h // 2
            
            # 6. ESTABILIZACIÓN DE CENTRO
            # Obtener todos los puntos del contorno y calcular la distancia al centro
            distances = []
            
            for point in largest_contour.reshape(-1, 2):
                dx = point[0] - center_x
                dy = point[1] - center_y
                distance = np.sqrt(dx*dx + dy*dy)
                distances.append(distance)

            # ESTO es rápido - operación vectorizada:
            #points = largest_contour.reshape(-1, 2)
            #dx = points[:, 0] - center_x
            #dy = points[:, 1] - center_y
            #distances = np.sqrt(dx*dx + dy*dy)
            
            # Calcular radio como la mediana de las distancias (más estable que la media)
            if distances:
                radius = int(np.median(distances))
            else:
                # Fallback: Usar el método tradicional
                (cx, cy), radius = cv2.minEnclosingCircle(largest_contour)
                radius = int(radius)
            
            # 7. LIMITAR CAMBIOS BRUSCOS EN EL RADIO
            # Usar un rango razonable para el radio (ajustar según resolución)
            min_radius = 5
            max_radius = min(ew, eh) // 3
            
            radius = max(min_radius, min(radius, max_radius))
            
            # 8. DIBUJAR INFORMACIÓN EN LA MÁSCARA
            # Dibujar contorno original
            cv2.drawContours(mask, [largest_contour], 0, (0, 0, 255), 1)
            
            # Dibujar círculo calculado
            cv2.circle(mask, (center_x, center_y), radius, (0, 255, 0), 1)
            
            # Dibujar centro
            cv2.circle(mask, (center_x, center_y), 2, (255, 0, 0), -1)
            
            return (center_x, center_y, radius, ex, ey, ew, eh, mask)
                    
        except Exception as e:
            logger.error(f"Error in process_eye_region: {e}")
            return None

    def start(self):
        """Inicia todos los procesos"""
        # Reset running flag (may be False from previous stop)
        self.running.value = True

        # Create fresh queues
        self.frame_queue = mp.Queue(maxsize=2)
        self.detection_queue = mp.Queue(maxsize=2)
        self.result_queue = mp.Queue(maxsize=2)
        self.ui_queue = mp.Queue(maxsize=2)

        self.capture_process = mp.Process(target=self.capture_worker)
        self.detection_process = mp.Process(target=self.detection_worker)
        self.processing_process = mp.Process(target=self.processing_worker)

        # Set as daemon so they die if parent dies
        self.capture_process.daemon = True
        self.detection_process.daemon = True
        self.processing_process.daemon = True

        self.capture_process.start()
        self.detection_process.start()
        self.processing_process.start()

    def set_pupil_mode(self, mode: str):
        """
        Cambia el modo de detección de pupila.

        Args:
            mode: "legacy", "fast", o "hybrid"
        """
        mode_map = {"legacy": 0, "fast": 1, "hybrid": 2}
        if mode in mode_map:
            self.pupil_mode.value = mode_map[mode]
            logger.info(f"Pupil detection mode changed to: {mode}")
        else:
            logger.warning(f"Unknown mode: {mode}. Using 'legacy' as default.")
            self.pupil_mode.value = 0

    def set_pupil_config(self, **kwargs):
        """
        Configura los parámetros del detector de pupila.

        Args:
            # Fast detector
            search_window_multiplier: Multiplicador de ventana de búsqueda (default 3.0)
            dark_threshold_percent: Porcentaje sobre punto más oscuro (default 20)
            starburst_rays: Número de rayos del starburst (default 16)
            starburst_min_gradient: Gradiente mínimo para detectar borde (default 30)
            fallback_threshold: Frames sin detección para activar fallback (default 5)

            # Legacy detector
            legacy_blur_enabled: Activar GaussianBlur (default True)
            legacy_blur_kernel: Tamaño del kernel de blur (default 5)
            legacy_clahe_enabled: Activar CLAHE (default True)
            legacy_clahe_clip_limit: Límite de clip de CLAHE (default 2.0)
            legacy_clahe_grid_size: Tamaño de grid de CLAHE (default 8)
            legacy_morph_enabled: Activar operaciones morfológicas (default True)
            legacy_morph_close_iterations: Iteraciones de cierre (default 1)
            legacy_morph_dilate_iterations: Iteraciones de dilatación (default 1)
        """
        # Fast detector params
        if 'search_window_multiplier' in kwargs:
            self.search_window_multiplier.value = float(kwargs['search_window_multiplier'])
        if 'dark_threshold_percent' in kwargs:
            self.dark_threshold_percent.value = int(kwargs['dark_threshold_percent'])
        if 'starburst_rays' in kwargs:
            self.starburst_rays.value = int(kwargs['starburst_rays'])
        if 'starburst_min_gradient' in kwargs:
            self.starburst_min_gradient.value = int(kwargs['starburst_min_gradient'])
        if 'fallback_threshold' in kwargs:
            self.fallback_threshold.value = int(kwargs['fallback_threshold'])

        # Hybrid params
        if 'min_confidence_for_lock' in kwargs:
            self.min_confidence_for_lock.value = float(kwargs['min_confidence_for_lock'])
        if 'revalidation_interval' in kwargs:
            self.revalidation_interval.value = int(kwargs['revalidation_interval'])

        # Legacy detector params
        if 'legacy_blur_enabled' in kwargs:
            self.legacy_blur_enabled.value = bool(kwargs['legacy_blur_enabled'])
        if 'legacy_blur_kernel' in kwargs:
            self.legacy_blur_kernel.value = int(kwargs['legacy_blur_kernel'])
        if 'legacy_clahe_enabled' in kwargs:
            self.legacy_clahe_enabled.value = bool(kwargs['legacy_clahe_enabled'])
        if 'legacy_clahe_clip_limit' in kwargs:
            self.legacy_clahe_clip_limit.value = float(kwargs['legacy_clahe_clip_limit'])
        if 'legacy_clahe_grid_size' in kwargs:
            self.legacy_clahe_grid_size.value = int(kwargs['legacy_clahe_grid_size'])
        if 'legacy_morph_enabled' in kwargs:
            self.legacy_morph_enabled.value = bool(kwargs['legacy_morph_enabled'])
        if 'legacy_morph_close_iterations' in kwargs:
            self.legacy_morph_close_iterations.value = int(kwargs['legacy_morph_close_iterations'])
        if 'legacy_morph_dilate_iterations' in kwargs:
            self.legacy_morph_dilate_iterations.value = int(kwargs['legacy_morph_dilate_iterations'])

    def stop(self):
        """Detiene todos los procesos de forma segura"""
        logger.info("Initiating process stop...")

        # Primero señalizar que los procesos deben terminar
        if hasattr(self, 'running'):
            self.running.value = False

        # Dar tiempo para que los procesos terminen normalmente
        time.sleep(0.3)

        # Limpiar colas para evitar bloqueos
        for queue_name in ['frame_queue', 'detection_queue', 'result_queue', 'ui_queue']:
            if hasattr(self, queue_name):
                self._clear_queue(getattr(self, queue_name))

        # Verificar y terminar procesos uno por uno
        for process_name in ['capture_process', 'detection_process', 'processing_process']:
            if hasattr(self, process_name):
                process = getattr(self, process_name)
                if process is not None:
                    if process.is_alive():
                        logger.info(f"Stopping {process_name}")
                        process.join(timeout=0.5)

                        if process.is_alive():
                            logger.warning(f"Forcing termination of {process_name}")
                            process.terminate()
                            process.join(timeout=0.3)

                            if process.is_alive():
                                logger.error(f"Using SIGKILL for {process_name}")
                                try:
                                    import os, signal
                                    os.kill(process.pid, signal.SIGKILL)
                                except Exception as e:
                                    logger.error(f"Error terminating process: {e}")
                    # Reset reference to None
                    setattr(self, process_name, None)
        
        logger.info("All processes stopped")

    def _clear_queue(self, q):
        """Vacía una cola sin bloquear"""
        try:
            while True:
                q.get_nowait()
        except Exception:
            # Queue.Empty o cualquier otro error indica que no hay más elementos
            pass