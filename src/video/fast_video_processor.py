#!/usr/bin/env python3
"""
Fast Video Processor
Procesador de video optimizado específico para detección de pupila del ojo derecho.
Usa modelo YOLO y sigue la arquitectura del sistema original.
"""

import cv2
import numpy as np
import time
import os
from typing import Dict, List, Optional, Tuple
from PySide6.QtCore import QThread, Signal

try:
    from numba import jit, prange
    NUMBA_AVAILABLE = True
    print("Numba disponible - usando optimizaciones")
except ImportError:
    NUMBA_AVAILABLE = False
    print("Numba no disponible - usando implementación estándar")

try:
    from ultralytics import YOLO
    import torch
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("YOLO no disponible - verificar instalación de ultralytics")


def get_model_file_path(model_name):
    """Obtener ruta del modelo YOLO"""
    # Buscar en diferentes ubicaciones posibles
    possible_paths = [
        f"models/{model_name}",
        f"src/models/{model_name}", 
        f"utils/models/{model_name}",
        f"data/models/{model_name}",
        model_name
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    print(f"Modelo {model_name} no encontrado en rutas: {possible_paths}")
    return None


# Funciones aceleradas con Numba si está disponible
if NUMBA_AVAILABLE:
    @jit(nopython=True, cache=True)
    def apply_threshold_fast(gray_region, threshold):
        """Aplicar umbral rápido con Numba"""
        h, w = gray_region.shape
        result = np.zeros((h, w), dtype=np.uint8)
        
        for i in prange(h):
            for j in prange(w):
                if gray_region[i, j] < threshold:
                    result[i, j] = 255
                else:
                    result[i, j] = 0
                    
        return result
    
    @jit(nopython=True, cache=True)
    def calculate_centroid_fast(contour):
        """Calcular centroide rápido con Numba"""
        cx = 0.0
        cy = 0.0
        n = len(contour)
        
        for i in range(n):
            cx += contour[i][0]
            cy += contour[i][1]
            
        return cx / n, cy / n
else:
    def apply_threshold_fast(gray_region, threshold):
        """Versión estándar sin Numba"""
        return cv2.threshold(gray_region, threshold, 255, cv2.THRESH_BINARY_INV)[1]
    
    def calculate_centroid_fast(contour):
        """Versión estándar sin Numba"""
        M = cv2.moments(contour)
        if M['m00'] == 0:
            return 0, 0
        cx = M['m10'] / M['m00']
        cy = M['m01'] / M['m00']
        return cx, cy


class FastVideoProcessor:
    """
    Procesador de video optimizado específico para detección de pupila del ojo derecho
    Usa modelo YOLO siguiendo la arquitectura del sistema original
    """
    
    def __init__(self, thresholds: Dict):
        self.thresholds = thresholds
        self.model = None
        self.setup_yolo_model()
        
        # Cache para optimización
        self.last_detections = []
        self.detection_counter = 0
        self.detection_frequency = 4  # Detectar cada 4 frames
        
        # Configuración de visualización
        self.show_yolo_detection = True
        self.show_masks = True
        self.show_pupil_point = True
        self.show_parameters = True
        
    def setup_yolo_model(self):
        """Configurar modelo YOLO para detección de ojos"""
        if not YOLO_AVAILABLE:
            print("YOLO no disponible - no se puede cargar modelo")
            return
            
        try:
            model_path = get_model_file_path('siev_vng_r01.pt')
            if model_path is None:
                print("No se encontró el modelo YOLO")
                return
                
            self.model = YOLO(model_path)
            
            # Optimizaciones para CPU/GPU
            if not torch.cuda.is_available():
                torch.set_num_threads(1)
                torch.set_num_interop_threads(1)
                print("Usando CPU para YOLO")
            else:
                print("Usando GPU para YOLO")
                
            print(f"Modelo YOLO cargado desde: {model_path}")
            
        except Exception as e:
            print(f"Error cargando modelo YOLO: {e}")
            self.model = None
            
    def process_frame(self, frame: np.ndarray) -> Tuple[float, float, bool, np.ndarray]:
        """
        Procesar frame y retornar posición de pupila del ojo derecho con visualización
        
        Returns:
            Tuple[x, y, detected, visualization_frame]: Posición x, y, si se detectó y frame con visualización
        """
        if frame is None or self.model is None:
            return 0.0, 0.0, False, frame if frame is not None else np.zeros((480, 640, 3), dtype=np.uint8)
            
        try:
            # Hacer copia para visualización
            vis_frame = frame.copy()
            h, w = frame.shape[:2]
            
            # Detectar ojos con YOLO (con cache para optimizar)
            detections = self._detect_eyes_yolo(frame)
            
            if not detections:
                self._draw_no_detection_info(vis_frame, "No se detectaron ojos con YOLO")
                return 0.0, 0.0, False, vis_frame
                
            # Buscar ojo derecho (el de la izquierda en la imagen, menor x)
            right_eye_detection = self._find_right_eye(detections, w)
            
            if right_eye_detection is None:
                self._draw_no_detection_info(vis_frame, "No se identificó ojo derecho")
                return 0.0, 0.0, False, vis_frame
                
            # Dibujar detección YOLO
            if self.show_yolo_detection:
                self._draw_yolo_detection(vis_frame, right_eye_detection)
                
            # Procesar región del ojo derecho
            pupil_x, pupil_y, masks = self._process_eye_region(frame, right_eye_detection)
            
            # Dibujar máscaras y pupila
            if self.show_masks and masks:
                self._draw_eye_masks(vis_frame, right_eye_detection, masks)
                
            if self.show_pupil_point and pupil_x > 0 and pupil_y > 0:
                self._draw_pupil_detection(vis_frame, right_eye_detection, pupil_x, pupil_y)
            
            # Mostrar parámetros
            if self.show_parameters:
                self._draw_parameters_info(vis_frame)
            
            return pupil_x, pupil_y, True, vis_frame
            
        except Exception as e:
            print(f"Error procesando frame: {e}")
            self._draw_error_info(vis_frame, str(e))
            return 0.0, 0.0, False, vis_frame
            
    def _detect_eyes_yolo(self, frame: np.ndarray) -> List[Dict]:
        """Detectar ojos usando YOLO con cache para optimización"""
        self.detection_counter += 1
        
        # Solo ejecutar YOLO cada N frames para optimizar
        if self.detection_counter % self.detection_frequency == 0 or not self.last_detections:
            try:
                # Escalar frame para YOLO (más rápido con imagen más pequeña)
                scale_factor = 0.5
                scaled_frame = cv2.resize(frame, None, fx=scale_factor, fy=scale_factor)
                
                # Ejecutar detección YOLO
                results = self.model(
                    scaled_frame,
                    conf=0.5,      # Umbral de confianza
                    iou=0.45,      # Umbral IOU para NMS
                    verbose=False, # Sin mensajes de debug
                    max_det=2      # Máximo 2 detecciones (ojos)
                )
                
                detections = []
                if results and len(results) > 0:
                    boxes = results[0].boxes
                    if boxes is not None:
                        for box in boxes:
                            # Convertir coordenadas de vuelta a escala original
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                            x1, y1, x2, y2 = x1/scale_factor, y1/scale_factor, x2/scale_factor, y2/scale_factor
                            
                            conf = box.conf[0].cpu().numpy()
                            
                            detections.append({
                                'x1': int(x1), 'y1': int(y1),
                                'x2': int(x2), 'y2': int(y2),
                                'conf': float(conf),
                                'cx': int((x1 + x2) / 2),
                                'cy': int((y1 + y2) / 2),
                                'w': int(x2 - x1),
                                'h': int(y2 - y1)
                            })
                
                self.last_detections = detections
                
            except Exception as e:
                print(f"Error en detección YOLO: {e}")
                return self.last_detections
                
        return self.last_detections
        
    def _find_right_eye(self, detections: List[Dict], frame_width: int) -> Optional[Dict]:
        """Encontrar ojo derecho de las detecciones (menor x en imagen)"""
        if not detections:
            return None
            
        if len(detections) == 1:
            return detections[0]
            
        # Si hay múltiples detecciones, tomar la de menor x (ojo derecho del sujeto)
        return min(detections, key=lambda det: det['cx'])
        
    def _process_eye_region(self, frame: np.ndarray, eye_detection: Dict) -> Tuple[float, float, List]:
        """
        Procesar región del ojo detectado para encontrar pupila
        Sigue la lógica de process_eye_region del sistema original
        """
        masks = []
        
        try:
            # Extraer ROI del ojo
            x1, y1, x2, y2 = eye_detection['x1'], eye_detection['y1'], eye_detection['x2'], eye_detection['y2']
            eye_region = frame[y1:y2, x1:x2]
            
            if eye_region.size == 0:
                return 0.0, 0.0, masks
                
            # Convertir a escala de grises
            if len(eye_region.shape) == 3:
                eye_gray = cv2.cvtColor(eye_region, cv2.COLOR_BGR2GRAY)
            else:
                eye_gray = eye_region.copy()
                
            # 1. PREPROCESAMIENTO OPTIMIZADO (como en video_processes.py)
            blurred = cv2.GaussianBlur(eye_gray, (5, 5), 0)
            
            # Mejorar contraste
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(blurred)
            
            # 2. UMBRAL MANUAL 
            threshold_value = self.thresholds.get('threshold_right', 50)
            
            if NUMBA_AVAILABLE:
                thresh = apply_threshold_fast(enhanced, threshold_value)
            else:
                _, thresh = cv2.threshold(enhanced, threshold_value, 255, cv2.THRESH_BINARY_INV)
                
            masks.append((thresh, (255, 255, 0), f"THRESHOLD {threshold_value}"))  # Amarillo
            
            # 3. OPERACIONES MORFOLÓGICAS MEJORADAS
            kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            
            # Aplicar erosión si es necesario
            erode_value = self.thresholds.get('erode_right', 2)
            if erode_value > 0:
                thresh_eroded = cv2.erode(thresh, kernel_small, iterations=erode_value)
                masks.append((thresh_eroded, (0, 255, 255), f"ERODE {erode_value}"))  # Cian
            else:
                thresh_eroded = thresh
                
            # Cerrar para eliminar pequeños huecos
            thresh_closed = cv2.morphologyEx(thresh_eroded, cv2.MORPH_CLOSE, kernel_small, iterations=1)
            
            # Dilatar ligeramente para capturar toda la pupila
            thresh_processed = cv2.dilate(thresh_closed, kernel_small, iterations=1)
            
            masks.append((thresh_processed, (255, 0, 255), "PROCESSED"))  # Magenta
            
            # 4. ENCONTRAR CONTORNOS Y ANALIZAR
            contours, _ = cv2.findContours(thresh_processed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return 0.0, 0.0, masks
                
            # Filtrar contornos por área mínima
            valid_contours = [c for c in contours if cv2.contourArea(c) > 20]
            
            if not valid_contours:
                return 0.0, 0.0, masks
                
            # Encontrar contorno más grande
            largest_contour = max(valid_contours, key=cv2.contourArea)
            
            # 5. CALCULAR CENTRO Y RADIO DE LA PUPILA
            if NUMBA_AVAILABLE:
                contour_points = largest_contour.reshape(-1, 2)
                center_x, center_y = calculate_centroid_fast(contour_points)
            else:
                center_x, center_y = calculate_centroid_fast(largest_contour)
                
            # Crear máscara del contorno final
            contour_mask = np.zeros_like(thresh_processed)
            cv2.fillPoly(contour_mask, [largest_contour], 255)
            masks.append((contour_mask, (0, 0, 255), "PUPIL"))  # Rojo
            
            return float(center_x), float(center_y), masks
            
        except Exception as e:
            print(f"Error en process_eye_region: {e}")
            return 0.0, 0.0, masks
            
    def _draw_yolo_detection(self, vis_frame: np.ndarray, detection: Dict):
        """Dibujar detección YOLO del ojo"""
        x1, y1, x2, y2 = detection['x1'], detection['y1'], detection['x2'], detection['y2']
        conf = detection['conf']
        
        # Rectángulo de detección
        cv2.rectangle(vis_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        # Etiqueta con confianza
        label = f"RIGHT EYE {conf:.2f}"
        cv2.putText(vis_frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
    def _draw_eye_masks(self, vis_frame: np.ndarray, detection: Dict, masks: List):
        """Dibujar máscaras de procesamiento dentro del ROI del ojo"""
        x1, y1, x2, y2 = detection['x1'], detection['y1'], detection['x2'], detection['y2']
        roi_w, roi_h = x2 - x1, y2 - y1
        
        for i, (mask, color, label) in enumerate(masks):
            if mask is not None and mask.size > 0:
                # Redimensionar máscara al tamaño del ROI
                mask_resized = cv2.resize(mask, (roi_w, roi_h))
                
                # Crear overlay colorido
                mask_colored = np.zeros((roi_h, roi_w, 3), dtype=np.uint8)
                mask_colored[mask_resized > 128] = color
                
                # Aplicar overlay en la región del ojo
                eye_roi = vis_frame[y1:y2, x1:x2]
                if eye_roi.shape[:2] == mask_colored.shape[:2]:
                    blended = cv2.addWeighted(eye_roi, 0.7, mask_colored, 0.3, 0)
                    vis_frame[y1:y2, x1:x2] = blended
                
                # Etiqueta de la máscara (fuera del ROI)
                label_y = y2 + 20 + (i * 15)
                cv2.putText(vis_frame, label, (x1, label_y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
                
    def _draw_pupil_detection(self, vis_frame: np.ndarray, detection: Dict, pupil_x: float, pupil_y: float):
        """Dibujar punto de pupila detectada"""
        x1, y1 = detection['x1'], detection['y1']
        
        # Convertir coordenadas locales a globales
        global_pupil_x = int(x1 + pupil_x)
        global_pupil_y = int(y1 + pupil_y)
        
        # Círculo de pupila
        cv2.circle(vis_frame, (global_pupil_x, global_pupil_y), 3, (0, 0, 255), -1)
        
        # Coordenadas de pupila
        cv2.putText(vis_frame, f"PUPIL ({pupil_x:.0f},{pupil_y:.0f})", 
                   (global_pupil_x + 5, global_pupil_y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
                   
    def _draw_parameters_info(self, vis_frame: np.ndarray):
        """Mostrar información de parámetros en pantalla"""
        # Fondo semi-transparente para mejor legibilidad
        overlay = vis_frame.copy()
        cv2.rectangle(overlay, (5, 5), (250, 100), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, vis_frame, 0.3, 0, vis_frame)
        
        # Texto de parámetros
        threshold = self.thresholds.get('threshold_right', 50)
        erode = self.thresholds.get('erode_right', 2)
        nose_width = self.thresholds.get('nose_width', 0.25)
        eye_height = self.thresholds.get('eye_height', 0.5)
        
        cv2.putText(vis_frame, f"Threshold: {threshold}", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(vis_frame, f"Erode: {erode}", (10, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(vis_frame, f"Nose Width: {nose_width:.2f}", (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(vis_frame, f"Eye Height: {eye_height:.2f}", (10, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
    def _draw_no_detection_info(self, vis_frame: np.ndarray, message: str):
        """Mostrar información cuando no hay detección"""
        cv2.putText(vis_frame, message, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        
    def _draw_error_info(self, vis_frame: np.ndarray, error_msg: str):
        """Mostrar información de error"""
        cv2.putText(vis_frame, f"ERROR: {error_msg}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
    def update_thresholds(self, new_thresholds: Dict):
        """Actualizar umbrales de procesamiento"""
        self.thresholds.update(new_thresholds)
        
    def set_visualization_options(self, **options):
        """Configurar opciones de visualización"""
        for key, value in options.items():
            if hasattr(self, key):
                setattr(self, key, value)


class SimpleVideoProcessor(QThread):
    """Hilo para procesar video completo usando SimpleVideoPlayer existente"""
    
    progress_updated = Signal(int)  # Progreso en porcentaje
    frame_processed = Signal(object, float, float, float)  # frame, timestamp, pupil_x, pupil_y
    processing_finished = Signal()
    
    def __init__(self, video_player, thresholds: Dict):
        super().__init__()
        self.video_player = video_player  # Usar SimpleVideoPlayer existente
        self.thresholds = thresholds
        self.running = True
        
        # Inicializar procesador rápido
        self.processor = FastVideoProcessor(thresholds)
        
    def stop(self):
        """Detener procesamiento"""
        self.running = False
        
    def run(self):
        """Procesar video completo usando frames del SimpleVideoPlayer"""
        try:
            if not self.video_player:
                print("Error: No hay SimpleVideoPlayer disponible")
                return
                
            total_frames = self.video_player.get_total_frames()
            fps = self.video_player.get_fps()
            
            print(f"Procesando video desde memoria: {total_frames} frames a {fps} FPS")
            
            frame_count = 0
            last_valid_pos = (0.0, 0.0)
            
            # Pausar reproducción durante procesamiento
            was_playing = self.video_player.is_playing
            self.video_player.pause()
            
            # Procesar cada frame del video
            for frame_index in range(total_frames):
                if not self.running:
                    break
                    
                # Buscar frame específico
                self.video_player.seek_to_frame(frame_index)
                
                # Esperar un momento para que se procese el frame
                self.msleep(1)
                
                # El frame se obtiene automáticamente via señal frame_ready
                # pero necesitamos una forma de obtenerlo sincrónicamente
                frame = self._get_current_frame()
                
                if frame is not None:
                    timestamp = frame_index / fps if fps > 0 else 0
                    
                    # Procesar frame con FastVideoProcessor
                    pupil_x, pupil_y, detected, vis_frame = self.processor.process_frame(frame)
                    
                    # Si no se detecta, usar última posición válida
                    if not detected:
                        pupil_x, pupil_y = last_valid_pos
                    else:
                        last_valid_pos = (pupil_x, pupil_y)
                    
                    # Emitir frame procesado
                    self.frame_processed.emit(vis_frame, timestamp, pupil_x, pupil_y)
                
                # Actualizar progreso cada 30 frames
                if frame_count % 30 == 0:
                    progress = int((frame_count / total_frames) * 100)
                    self.progress_updated.emit(progress)
                
                frame_count += 1
            
            # Restaurar estado de reproducción
            if was_playing:
                self.video_player.play()
            
            self.processing_finished.emit()
            print(f"Procesamiento completado: {frame_count} frames procesados")
            
        except Exception as e:
            print(f"Error en procesamiento: {e}")
            
    def _get_current_frame(self):
        """Obtener frame actual del SimpleVideoPlayer de forma sincrónica"""
        # Como SimpleVideoPlayer emite frames via señal, necesitamos
        # una forma de obtener el frame actual sincrónicamente
        # Por ahora, asumir que el frame está disponible inmediatamente
        # En implementación real, se podría usar un mecanismo de callback
        
        # Alternativa: acceder directamente al VideoCapture del SimpleVideoPlayer
        if hasattr(self.video_player, 'cap') and self.video_player.cap:
            ret, frame = self.video_player.cap.read()
            if ret:
                return self.video_player._process_frame(frame)
        
        return None