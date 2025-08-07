#!/usr/bin/env python3
"""
Fast Video Processor - Versión Mejorada
Procesador de video optimizado con las mejoras de robustez de video_processes.py
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
    possible_paths = [
        f"models/{model_name}",
        f"src/models/{model_name}", 
        f"src-processor/models/{model_name}", 
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
    def calculate_distances_fast(contour_points, center_x, center_y):
        """Calcular distancias de puntos al centro con Numba"""
        n = len(contour_points)
        distances = np.zeros(n)
        
        for i in range(n):
            dx = contour_points[i][0] - center_x
            dy = contour_points[i][1] - center_y
            distances[i] = np.sqrt(dx*dx + dy*dy)
            
        return distances
else:
    def apply_threshold_fast(gray_region, threshold):
        """Versión estándar sin Numba"""
        return cv2.threshold(gray_region, threshold, 255, cv2.THRESH_BINARY_INV)[1]
    
    def calculate_distances_fast(contour_points, center_x, center_y):
        """Versión estándar sin Numba"""
        dx = contour_points[:, 0] - center_x
        dy = contour_points[:, 1] - center_y
        return np.sqrt(dx*dx + dy*dy)


class FastVideoProcessor:
    """
    Procesador de video optimizado con mejoras de robustez de video_processes.py
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
        
        
        # Cache del último valor válido para parpadeos
        self.last_valid_pupil_x = 0.0
        self.last_valid_pupil_y = 0.0
        self.last_valid_radius = 0.0

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
            
           # Optimizaciones para CPU/GPU (solo la primera vez)
            try:
                if not torch.cuda.is_available():
                    torch.set_num_threads(1)
                    torch.set_num_interop_threads(1)
                    print("Usando CPU para YOLO")
                else:
                    print("Usando GPU para YOLO")
            except RuntimeError as e:
                # Ya está configurado, ignorar
                print(f"PyTorch ya configurado previamente: {e}")
                
            print(f"Modelo YOLO cargado desde: {model_path}")
            
        except Exception as e:
            print(f"Error cargando modelo YOLO: {e}")
            self.model = None
            
    def process_frame(self, frame: np.ndarray) -> Tuple[float, float, bool, np.ndarray]:
        #print(f"🟦 === INICIO process_frame ===")
        #print(f"🟦 Línea 1: frame type = {type(frame)}")
        #print(f"🟦 Línea 2: frame shape = {frame.shape if frame is not None else 'None'}")
        #print(f"🟦 Línea 3: model = {self.model is not None}")
        """
        Procesar frame y retornar posición de pupila del ojo derecho con visualización
        
        Returns:
            Tuple[x, y, detected, visualization_frame]: Posición x, y, si se detectó y frame con visualización
        """
        
        #print(f"🟦 Línea 4: Después del docstring")
        
        if frame is None or self.model is None:
            #print("="*50)
            #print(f"EARLY RETURN DEBUG:")
            #print(f"frame is None: {frame is None}")
            #print(f"model is None: {self.model is None}")
            #print("="*50)
            return 0.0, 0.0, False, frame if frame is not None else np.zeros((480, 640, 3), dtype=np.uint8)
            
        #print(f"🟦 Línea 5: Pasó el if inicial")
                    
        try:
            #print(f"🟦 Línea 6: Entrando al try")

            # Hacer copia para visualización
            vis_frame = frame.copy()
            #print(f"🟦 Línea 7: vis_frame creado")

            h, w = frame.shape[:2]
            #print(f"🟦 Línea 8: Llamando _detect_eyes_yolo")

            # Detectar ojos con YOLO (con cache para optimizar)
            detections = self._detect_eyes_yolo(frame)
            #print(f"🟦 Línea 9: _detect_eyes_yolo retornó: {len(detections) if detections else 0} detections")

            if not detections:
                #print(f"🔴 YOLO falló, last_valid_pupil_x = {self.last_valid_pupil_x} (debería ser 41.0)")
                self._draw_no_detection_info(vis_frame, "No se detectaron ojos con YOLO")
                return_value = self.last_valid_pupil_x, self.last_valid_pupil_y, False, vis_frame
                #print(f"🔴 Retornando: {return_value[0]}, {return_value[1]}")
                return return_value
                
            # Buscar ojo derecho (el de la izquierda en la imagen, menor x)
            right_eye_detection = self._find_right_eye(detections, w)
            
            if right_eye_detection is None:
                #print(f"🔴 No right eye, last_valid_pupil_x = {self.last_valid_pupil_x}")
                self._draw_no_detection_info(vis_frame, "No se identificó ojo derecho válido")
                return_value = self.last_valid_pupil_x, self.last_valid_pupil_y, False, vis_frame
                #print(f"🔴 Retornando: {return_value[0]}, {return_value[1]}")
                return return_value
                
            # Dibujar detección YOLO
            if self.show_yolo_detection:
                self._draw_yolo_detection(vis_frame, right_eye_detection)
                
            # Procesar región del ojo derecho
            pupil_x, pupil_y, radius, masks = self._process_eye_region_improved(frame, right_eye_detection)
            
            # Dibujar máscaras y pupila
            if self.show_masks and masks:
                self._draw_eye_masks(vis_frame, right_eye_detection, masks)
                
            if self.show_pupil_point and pupil_x > 0 and pupil_y > 0:
                self._draw_pupil_detection_improved(vis_frame, right_eye_detection, pupil_x, pupil_y, radius)
            
            # Mostrar parámetros
            if self.show_parameters:
                pass
                #self._draw_parameters_info(vis_frame)
            
            # Actualizar cache solo si se detectó correctamente
            if pupil_x > 0 and pupil_y > 0:
                #print(f"ACTUALIZANDO last_valid: de {self.last_valid_pupil_x} a {pupil_x}")
                if pupil_x > 5.0:
                    old_value = self.last_valid_pupil_x  # Guardar valor anterior
                    self.last_valid_pupil_x = pupil_x
                    #print(f"🟢 CONFIRMADO: last_valid_pupil_x cambió de {old_value} a {self.last_valid_pupil_x}")
    
            return pupil_x, pupil_y, True, vis_frame
            
        except Exception as e:
            #print(f"🔴 EXCEPCIÓN CAPTURADA: {e}")
            #print(f"Error procesando frame: {e}")
            self._draw_error_info(vis_frame, str(e))
            return 0.0, 0.0, False, vis_frame  # ← ¡AQUÍ ESTÁ EL 0.0!
            
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
        # Solo procesar ojos en la mitad IZQUIERDA de la imagen (ojo derecho del sujeto)
        frame_center_x = frame_width / 2
        valid_detections = []

        for det in detections:
            # Si el centro del ojo está en la mitad izquierda, es válido
            if det['cx'] < frame_center_x:
                valid_detections.append(det)

        if not valid_detections:
            return None

        # Si hay múltiples ojos válidos, tomar el de menor x
        return min(valid_detections, key=lambda det: det['cx'])
        
    def _process_eye_region_improved(self, frame: np.ndarray, eye_detection: Dict) -> Tuple[float, float, float, List]:
        """
        Procesar región del ojo con las mejoras de video_processes.py
        """
        masks = []
        
        try:
            # Extraer ROI del ojo
            x1, y1, x2, y2 = eye_detection['x1'], eye_detection['y1'], eye_detection['x2'], eye_detection['y2']
            eye_region = frame[y1:y2, x1:x2]
            
            if eye_region.size == 0:
                return 0.0, 0.0, 0.0, masks
                
            # Convertir a escala de grises
            if len(eye_region.shape) == 3:
                eye_gray = cv2.cvtColor(eye_region, cv2.COLOR_BGR2GRAY)
            else:
                eye_gray = eye_region.copy()
                
            # Dimensiones del ojo
            ew, eh = eye_region.shape[1], eye_region.shape[0]
                
            # 1. PREPROCESAMIENTO OPTIMIZADO (igual que video_processes.py)
            blurred = cv2.GaussianBlur(eye_gray, (5, 5), 0)
            
            # Mejorar contraste con CLAHE
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(blurred)
            
            # 2. UMBRAL MEJORADO (con opción OTSU como en video_processes.py)
            threshold_value = self.thresholds.get('threshold_right', 50)
            
            if threshold_value == 0:
                # Usar OTSU adaptativo cuando threshold es 0
                otsu_thresh, _ = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                adjusted_thresh = max(0, min(255, otsu_thresh + threshold_value))
                _, thresh = cv2.threshold(enhanced, adjusted_thresh, 255, cv2.THRESH_BINARY_INV)
            else:
                # Umbral fijo
                if NUMBA_AVAILABLE:
                    thresh = apply_threshold_fast(enhanced, threshold_value)
                else:
                    _, thresh = cv2.threshold(enhanced, threshold_value, 255, cv2.THRESH_BINARY_INV)
                    
            masks.append((thresh, (255, 255, 0), f"THRESHOLD {threshold_value}"))  # Amarillo
            
            # 3. OPERACIONES MORFOLÓGICAS MEJORADAS (igual que video_processes.py)
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
            
            # 4. ENCONTRAR CONTORNOS Y FILTRAR (MEJORADO)
            contours, _ = cv2.findContours(thresh_processed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return 0.0, 0.0, 0.0, masks
                
            # FILTRADO MEJORADO: área mínima Y MÁXIMA (como en video_processes.py)
            valid_contours = []
            for c in contours:
                area = cv2.contourArea(c)
                # La pupila no debe ser más del 50% del ojo (importante!)
                if area > 20 and area < (ew * eh * 0.5):
                    valid_contours.append(c)
            
            if not valid_contours:
                return 0.0, 0.0, 0.0, masks
                
            # Ordenar por área (mayor primero)
            valid_contours = sorted(valid_contours, key=cv2.contourArea, reverse=True)
            largest_contour = valid_contours[0]
            
            # 5. CÁLCULO ROBUSTO DEL CENTRO (como en video_processes.py)
            M = cv2.moments(largest_contour)
            if M["m00"] != 0:
                center_x = int(M["m10"] / M["m00"])
                center_y = int(M["m01"] / M["m00"])
            else:
                # Fallback si el momento falla
                x, y, w, h = cv2.boundingRect(largest_contour)
                center_x = x + w // 2
                center_y = y + h // 2
            
            # 6. ESTABILIZACIÓN DEL RADIO (CRÍTICO - como en video_processes.py)
            # Calcular distancias de todos los puntos al centro
            contour_points = largest_contour.reshape(-1, 2)
            
            if NUMBA_AVAILABLE:
                distances = calculate_distances_fast(contour_points, center_x, center_y)
            else:
                # Versión vectorizada numpy
                dx = contour_points[:, 0] - center_x
                dy = contour_points[:, 1] - center_y
                distances = np.sqrt(dx*dx + dy*dy)
            
            # Usar MEDIANA para estabilidad (no media!)
            if len(distances) > 0:
                radius = int(np.median(distances))
            else:
                # Fallback
                (cx, cy), radius = cv2.minEnclosingCircle(largest_contour)
                radius = int(radius)
            
            # 7. LIMITAR CAMBIOS BRUSCOS EN EL RADIO (como en video_processes.py)
            min_radius = 5
            max_radius = min(ew, eh) // 3  # El radio no debe ser más de 1/3 del ojo
            
            radius = max(min_radius, min(radius, max_radius))
            
            # Crear máscara del contorno final para visualización
            contour_mask = np.zeros_like(thresh_processed)
            cv2.drawContours(contour_mask, [largest_contour], 0, 255, -1)
            
            # Dibujar información en la máscara
            mask_viz = cv2.cvtColor(contour_mask, cv2.COLOR_GRAY2BGR)
            cv2.circle(mask_viz, (center_x, center_y), radius, (0, 255, 0), 1)
            cv2.circle(mask_viz, (center_x, center_y), 2, (255, 0, 0), -1)
            masks.append((mask_viz, (0, 0, 255), "PUPIL"))  # Rojo
            
            return float(center_x), float(center_y), float(radius), masks
            
        except Exception as e:
            print(f"Error en process_eye_region_improved: {e}")
            return 0.0, 0.0, 0.0, masks
            
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
                # Verificar si es imagen o máscara
                if len(mask.shape) == 3:
                    # Es una imagen BGR, usar directamente
                    mask_colored = mask
                else:
                    # Es una máscara de un canal, convertir
                    mask_resized = cv2.resize(mask, (roi_w, roi_h))
                    mask_colored = np.zeros((roi_h, roi_w, 3), dtype=np.uint8)
                    mask_colored[mask_resized > 128] = color
                
                # Redimensionar si es necesario
                if mask_colored.shape[:2] != (roi_h, roi_w):
                    mask_colored = cv2.resize(mask_colored, (roi_w, roi_h))
                
                # Aplicar overlay en la región del ojo
                eye_roi = vis_frame[y1:y2, x1:x2]
                if eye_roi.shape[:2] == mask_colored.shape[:2]:
                    blended = cv2.addWeighted(eye_roi, 0.7, mask_colored, 0.3, 0)
                    vis_frame[y1:y2, x1:x2] = blended
                
                # Etiqueta de la máscara (fuera del ROI)
                label_y = y2 + 20 + (i * 15)
                cv2.putText(vis_frame, label, (x1, label_y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
                
    def _draw_pupil_detection_improved(self, vis_frame: np.ndarray, detection: Dict, 
                                      pupil_x: float, pupil_y: float, radius: float):
        """Dibujar punto y círculo de pupila detectada"""
        x1, y1 = detection['x1'], detection['y1']
        
        # Convertir coordenadas locales a globales
        global_pupil_x = int(x1 + pupil_x)
        global_pupil_y = int(y1 + pupil_y)
        
        # Dibujar círculo de pupila con el radio calculado
        cv2.circle(vis_frame, (global_pupil_x, global_pupil_y), int(radius), (0, 0, 255), 1)
        
        # Punto central
        cv2.circle(vis_frame, (global_pupil_x, global_pupil_y), 2, (0, 255, 0), -1)
        
        # Cruz para marcar el centro
        longitud_cruz = 5
        cv2.line(vis_frame, (global_pupil_x - longitud_cruz, global_pupil_y), 
                (global_pupil_x + longitud_cruz, global_pupil_y), (0, 255, 0), 1)
        cv2.line(vis_frame, (global_pupil_x, global_pupil_y - longitud_cruz), 
                (global_pupil_x, global_pupil_y + longitud_cruz), (0, 255, 0), 1)
        
        # Coordenadas de pupila
        cv2.putText(vis_frame, f"PUPIL ({pupil_x:.0f},{pupil_y:.0f}) R:{radius:.0f}", 
                   (global_pupil_x + 5, global_pupil_y - 5), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
                   
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
        
        cv2.putText(vis_frame, f"Threshold: {threshold}", (10, 25), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(vis_frame, f"Erode: {erode}", (10, 45), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(vis_frame, f"Nose Width: {nose_width:.2f}", (10, 65), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(vis_frame, f"Eye Height: {eye_height:.2f}", (10, 85), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
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