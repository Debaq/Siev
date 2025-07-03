#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Eye Detector Module - Detección de ojos con YOLO8 y marcado de pupilas
"""

import cv2
import numpy as np
import os
import glob
from typing import Optional, List, Tuple, Dict, Any
from PySide6.QtCore import QObject, Signal

# Try import YOLO8 with graceful fallback
try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    print("⚠️ ONNXRuntime no disponible - detección YOLO8 deshabilitada")

try:
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False
    print("⚠️ Ultralytics no disponible - carga de modelos deshabilitada")


class EyeDetector(QObject):
    """
    Detector de ojos usando YOLO8 (.onnx) y detección de pupilas.
    Se enfoca en detectar regiones de ojos (sin cejas) y marcar pupilas.
    """
    
    # Señales
    eyes_detected = Signal(list)  # Lista de regiones de ojos detectadas
    pupils_detected = Signal(list)  # Lista de pupilas detectadas
    detection_failed = Signal(str)  # Error en detección
    
    def __init__(self, model_path: str = "assets/model/", parent=None):
        super().__init__(parent)
        
        # Configuración de rutas
        self.model_path = model_path
        self.onnx_session = None
        self.model_loaded = False
        
        # Configuración de detección
        self.confidence_threshold = 0.5
        self.nms_threshold = 0.4
        self.input_size = (640, 640)  # Tamaño estándar YOLO
        
        # Estado de detección
        self.last_eye_regions = []
        self.detection_enabled = True
        
        # Intentar cargar modelo al inicializar
        self._load_model()
    
    def _load_model(self) -> bool:
        """
        Cargar modelo YOLO8 ONNX desde assets/model/
        
        Returns:
            bool: True si el modelo se cargó correctamente
        """
        if not ONNX_AVAILABLE:
            print("❌ ONNXRuntime no disponible")
            return False
        
        try:
            # Buscar archivos .onnx en la carpeta de modelos
            onnx_files = glob.glob(os.path.join(self.model_path, "*.onnx"))
            
            if not onnx_files:
                print(f"❌ No se encontraron modelos .onnx en {self.model_path}")
                return False
            
            # Usar el primer modelo encontrado
            model_file = onnx_files[0]
            print(f"🔍 Cargando modelo YOLO8: {model_file}")
            
            # Crear sesión ONNX
            self.onnx_session = ort.InferenceSession(
                model_file,
                providers=['CPUExecutionProvider']  # Usar CPU por compatibilidad
            )
            
            # Verificar entrada del modelo
            input_details = self.onnx_session.get_inputs()[0]
            input_shape = input_details.shape
            print(f"📐 Forma de entrada del modelo: {input_shape}")
            
            # Actualizar tamaño de entrada si es diferente
            if len(input_shape) >= 3:
                self.input_size = (input_shape[2], input_shape[3])
            
            self.model_loaded = True
            print(f"✅ Modelo YOLO8 cargado correctamente")
            return True
            
        except Exception as e:
            print(f"❌ Error cargando modelo YOLO8: {e}")
            self.onnx_session = None
            self.model_loaded = False
            return False
    
    def _preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Preprocesar frame para YOLO8.
        
        Args:
            frame: Frame original BGR
            
        Returns:
            np.ndarray: Frame preprocesado para inferencia
        """
        # Redimensionar manteniendo aspect ratio
        h, w = frame.shape[:2]
        target_h, target_w = self.input_size
        
        # Calcular escala
        scale = min(target_w / w, target_h / h)
        new_w, new_h = int(w * scale), int(h * scale)
        
        # Redimensionar
        resized = cv2.resize(frame, (new_w, new_h))
        
        # Crear canvas con padding
        canvas = np.zeros((target_h, target_w, 3), dtype=np.uint8)
        y_offset = (target_h - new_h) // 2
        x_offset = (target_w - new_w) // 2
        canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized
        
        # Convertir a RGB y normalizar
        rgb_frame = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
        normalized = rgb_frame.astype(np.float32) / 255.0
        
        # Cambiar a formato NCHW (batch, channels, height, width)
        input_tensor = normalized.transpose(2, 0, 1)[np.newaxis, ...]
        
        return input_tensor
    
    def _postprocess_detections(self, outputs: np.ndarray, frame_shape: Tuple[int, int]) -> List[Dict[str, Any]]:
        """
        Postprocesar salidas de YOLO8 para obtener cajas de ojos.
        
        Args:
            outputs: Salidas del modelo YOLO8
            frame_shape: Forma del frame original (height, width)
            
        Returns:
            List de detecciones de ojos
        """
        detections = []
        
        try:
            # YOLO8 output shape típicamente: [1, N, 6] donde N son detecciones
            # Columnas: [x_center, y_center, width, height, confidence, class_id]
            if len(outputs.shape) == 3:
                outputs = outputs[0]  # Remover dimensión batch
            
            frame_h, frame_w = frame_shape
            input_h, input_w = self.input_size
            
            # Calcular factores de escala para convertir a coordenadas originales
            scale_x = frame_w / input_w
            scale_y = frame_h / input_h
            
            for detection in outputs:
                if len(detection) >= 5:
                    x_center, y_center, width, height, confidence = detection[:5]
                    
                    # Filtrar por confianza
                    if confidence < self.confidence_threshold:
                        continue
                    
                    # Convertir a coordenadas del frame original
                    x_center *= scale_x
                    y_center *= scale_y
                    width *= scale_x
                    height *= scale_y
                    
                    # Convertir a formato xyxy
                    x1 = int(x_center - width / 2)
                    y1 = int(y_center - height / 2)
                    x2 = int(x_center + width / 2)
                    y2 = int(y_center + height / 2)
                    
                    # Asegurar que están dentro del frame
                    x1 = max(0, min(x1, frame_w))
                    y1 = max(0, min(y1, frame_h))
                    x2 = max(0, min(x2, frame_w))
                    y2 = max(0, min(y2, frame_h))
                    
                    detections.append({
                        'bbox': (x1, y1, x2, y2),
                        'confidence': float(confidence),
                        'center': (int(x_center), int(y_center)),
                        'area': (x2 - x1) * (y2 - y1)
                    })
            
            # Aplicar NMS si hay múltiples detecciones
            if len(detections) > 1:
                detections = self._apply_nms(detections)
            
        except Exception as e:
            print(f"Error en postprocesamiento: {e}")
        
        return detections
    
    def _apply_nms(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Aplicar Non-Maximum Suppression para eliminar detecciones duplicadas."""
        if len(detections) <= 1:
            return detections
        
        boxes = np.array([det['bbox'] for det in detections])
        scores = np.array([det['confidence'] for det in detections])
        
        # Aplicar NMS de OpenCV
        indices = cv2.dnn.NMSBoxes(
            boxes.tolist(), scores.tolist(), 
            self.confidence_threshold, self.nms_threshold
        )
        
        if len(indices) > 0:
            indices = indices.flatten()
            return [detections[i] for i in indices]
        
        return detections
    
    def detect_eyes_yolo(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detectar regiones de ojos usando YOLO8.
        
        Args:
            frame: Frame BGR de entrada
            
        Returns:
            Lista de regiones de ojos detectadas
        """
        if not self.model_loaded or not self.onnx_session:
            return []
        
        try:
            # Preprocesar frame
            input_tensor = self._preprocess_frame(frame)
            
            # Inferencia
            input_name = self.onnx_session.get_inputs()[0].name
            outputs = self.onnx_session.run(None, {input_name: input_tensor})
            
            # Postprocesar
            if outputs and len(outputs) > 0:
                detections = self._postprocess_detections(outputs[0], frame.shape[:2])
                self.last_eye_regions = detections
                self.eyes_detected.emit(detections)
                return detections
            
        except Exception as e:
            error_msg = f"Error en detección YOLO: {e}"
            print(f"❌ {error_msg}")
            self.detection_failed.emit(error_msg)
        
        return []
    
    def detect_pupils_in_regions(self, frame: np.ndarray, eye_regions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detectar pupilas dentro de las regiones de ojos detectadas.
        
        Args:
            frame: Frame BGR original
            eye_regions: Lista de regiones de ojos
            
        Returns:
            Lista de pupilas detectadas
        """
        pupils = []
        
        for region in eye_regions:
            try:
                pupil = self._detect_pupil_in_region(frame, region)
                if pupil:
                    pupils.append(pupil)
            except Exception as e:
                print(f"Error detectando pupila en región: {e}")
        
        if pupils:
            self.pupils_detected.emit(pupils)
        
        return pupils
    
    def _detect_pupil_in_region(self, frame: np.ndarray, eye_region: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Detectar pupila en una región específica del ojo.
        
        Args:
            frame: Frame BGR completo
            eye_region: Diccionario con información de la región del ojo
            
        Returns:
            Información de la pupila detectada o None
        """
        try:
            x1, y1, x2, y2 = eye_region['bbox']
            
            # Extraer ROI del ojo
            roi = frame[y1:y2, x1:x2]
            if roi.size == 0:
                return None
            
            # Convertir a escala de grises
            gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            
            # Aplicar blur gaussiano para suavizar
            blurred = cv2.GaussianBlur(gray_roi, (5, 5), 0)
            
            # Encontrar el punto más oscuro (candidato a pupila)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(blurred)
            
            # Convertir coordenadas locales a globales
            pupil_x = x1 + min_loc[0]
            pupil_y = y1 + min_loc[1]
            
            # Estimar radio de la pupila usando círculos de Hough
            pupil_radius = self._estimate_pupil_radius(gray_roi, min_loc)
            
            # Validar que la detección sea razonable
            roi_height, roi_width = gray_roi.shape
            if (0 < min_loc[0] < roi_width and 
                0 < min_loc[1] < roi_height and
                pupil_radius > 3):  # Radio mínimo razonable
                
                return {
                    'center': (pupil_x, pupil_y),
                    'radius': pupil_radius,
                    'intensity': min_val,
                    'eye_region': eye_region,
                    'local_coords': min_loc
                }
        
        except Exception as e:
            print(f"Error en detección de pupila: {e}")
        
        return None
    
    def _estimate_pupil_radius(self, gray_roi: np.ndarray, center: Tuple[int, int]) -> int:
        """
        Estimar radio de pupila usando círculos de Hough.
        
        Args:
            gray_roi: ROI en escala de grises
            center: Centro estimado de la pupila
            
        Returns:
            Radio estimado de la pupila
        """
        try:
            # Aplicar detección de círculos de Hough
            circles = cv2.HoughCircles(
                gray_roi,
                cv2.HOUGH_GRADIENT,
                dp=1,
                minDist=gray_roi.shape[0] // 4,
                param1=50,
                param2=30,
                minRadius=3,
                maxRadius=gray_roi.shape[0] // 3
            )
            
            if circles is not None:
                circles = np.round(circles[0, :]).astype("int")
                
                # Encontrar el círculo más cercano al centro estimado
                min_distance = float('inf')
                best_radius = 8  # Radio por defecto
                
                for (x, y, r) in circles:
                    distance = np.sqrt((x - center[0])**2 + (y - center[1])**2)
                    if distance < min_distance:
                        min_distance = distance
                        best_radius = r
                
                return best_radius
            
        except Exception as e:
            print(f"Error estimando radio: {e}")
        
        # Fallback: estimar basado en tamaño de ROI
        return max(5, min(gray_roi.shape) // 8)
    
    def process_frame(self, frame: np.ndarray) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Procesar frame completo: detectar ojos y pupilas.
        
        Args:
            frame: Frame BGR de entrada
            
        Returns:
            Tuple (eye_regions, pupils)
        """
        if not self.detection_enabled:
            return [], []
        
        # Detectar regiones de ojos
        eye_regions = self.detect_eyes_yolo(frame)
        
        # Detectar pupilas en las regiones encontradas
        pupils = self.detect_pupils_in_regions(frame, eye_regions)
        
        return eye_regions, pupils
    
    def draw_detections(self, frame: np.ndarray, eye_regions: List[Dict[str, Any]], pupils: List[Dict[str, Any]]) -> np.ndarray:
        """
        Dibujar detecciones sobre el frame.
        
        Args:
            frame: Frame original
            eye_regions: Regiones de ojos detectadas
            pupils: Pupilas detectadas
            
        Returns:
            Frame con detecciones dibujadas
        """
        output_frame = frame.copy()
        
        # Dibujar regiones de ojos
        for region in eye_regions:
            x1, y1, x2, y2 = region['bbox']
            confidence = region['confidence']
            
            # Rectángulo del ojo
            cv2.rectangle(output_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Etiqueta de confianza
            label = f"Eye: {confidence:.2f}"
            cv2.putText(output_frame, label, (x1, y1-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # Dibujar pupilas
        for pupil in pupils:
            center = pupil['center']
            radius = pupil['radius']
            
            # Círculo de la pupila
            cv2.circle(output_frame, center, radius, (255, 0, 0), 2)
            cv2.circle(output_frame, center, 2, (0, 0, 255), -1)  # Centro
            
            # Etiqueta
            label = f"Pupil r={radius}"
            cv2.putText(output_frame, label, (center[0]-30, center[1]-radius-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)
        
        return output_frame
    
    def set_detection_enabled(self, enabled: bool) -> None:
        """Habilitar/deshabilitar detección."""
        self.detection_enabled = enabled
        print(f"🔍 Detección {'habilitada' if enabled else 'deshabilitada'}")
    
    def get_detection_status(self) -> Dict[str, Any]:
        """Obtener estado de la detección."""
        return {
            'model_loaded': self.model_loaded,
            'onnx_available': ONNX_AVAILABLE,
            'ultralytics_available': ULTRALYTICS_AVAILABLE,
            'detection_enabled': self.detection_enabled,
            'model_path': self.model_path,
            'confidence_threshold': self.confidence_threshold,
            'input_size': self.input_size
        }