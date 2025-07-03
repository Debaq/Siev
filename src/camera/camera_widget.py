#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Camera Widget Modular - Coordinador entre camera_capture y eye_detector
"""

import cv2
import numpy as np
from PySide6.QtWidgets import QWidget, QLabel
from PySide6.QtCore import QTimer, Qt, QSize, Signal
from PySide6.QtGui import QImage, QPixmap, QFont, QPainter, QPen, QColor
from typing import Optional, Dict, Any, List, Tuple

# Importar nuestros módulos
from camera.camera_capture import CameraCapture
from camera.eye_detector import EyeDetector


class ModularCameraWidget(QWidget):
    """
    Widget de cámara modular que coordina captura y detección de ojos.
    Integra CameraCapture y EyeDetector para funcionalidad completa.
    """
    
    # Señales para comunicación externa
    frame_processed = Signal(np.ndarray)  # Frame procesado completo
    eyes_found = Signal(list)  # Ojos detectados
    pupils_found = Signal(list)  # Pupilas detectadas
    camera_status_changed = Signal(bool)  # Estado de cámara
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configurar widget
        self.setMinimumSize(640, 480)
        
        # Inicializar módulos
        self.camera_capture = CameraCapture(self)
        self.eye_detector = EyeDetector(parent=self)
        
        # Estado del widget
        self.current_frame = None
        self.processed_frame = None
        self.is_recording = False
        
        # Configuración de overlay médico
        self.show_crosshair = True
        self.show_tracking = True
        self.show_eye_detection = True
        self.show_pupil_detection = True
        
        # Control de procesamiento
        self.processing_enabled = True
        self.processing_interval = 33  # ~30 FPS
        
        # Timer para captura y procesamiento
        self.capture_timer = QTimer()
        self.capture_timer.timeout.connect(self._capture_and_process)
        
        # Conectar señales de los módulos
        self._connect_module_signals()
        
        print("✅ ModularCameraWidget inicializado")
    
    def _connect_module_signals(self):
        """Conectar señales de los módulos internos."""
        
        # Señales del CameraCapture
        self.camera_capture.camera_connected.connect(self._on_camera_connected)
        self.camera_capture.frame_captured.connect(self._on_frame_captured)
        self.camera_capture.capture_failed.connect(self._on_capture_failed)
        
        # Señales del EyeDetector
        self.eye_detector.eyes_detected.connect(self._on_eyes_detected)
        self.eye_detector.pupils_detected.connect(self._on_pupils_detected)
        self.eye_detector.detection_failed.connect(self._on_detection_failed)
        
        print("🔗 Señales de módulos conectadas")
    
    def init_camera(self, camera_index: int, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Inicializar cámara con configuración específica.
        
        Args:
            camera_index: Índice de cámara SIEV
            config: Configuración opcional de cámara
            
        Returns:
            bool: True si se inicializó correctamente
        """
        print(f"🔌 Inicializando cámara modular en índice {camera_index}")
        return self.camera_capture.init_camera(camera_index, config)
    
    def start_capture(self) -> bool:
        """Iniciar captura y procesamiento."""
        if not self.camera_capture.is_camera_available():
            print("❌ No hay cámara disponible para iniciar captura")
            return False
        
        if not self.capture_timer.isActive():
            self.capture_timer.start(self.processing_interval)
            print("▶️ Captura modular iniciada")
            return True
        
        return False
    
    def stop_capture(self):
        """Detener captura y procesamiento."""
        if self.capture_timer.isActive():
            self.capture_timer.stop()
            print("⏸️ Captura modular detenida")
    
    def release_camera(self):
        """Liberar cámara completamente."""
        print("🔌 Liberando cámara modular...")
        
        self.stop_capture()
        self.camera_capture.release_camera()
        
        # Limpiar frames
        self.current_frame = None
        self.processed_frame = None
        self.is_recording = False
        
        self.update()
        print("✅ Cámara modular liberada")
    
    def _capture_and_process(self):
        """Ciclo principal: capturar frame y procesar detecciones."""
        # Capturar frame
        frame = self.camera_capture.capture_frame()
        if frame is None:
            return
        
        # Guardar frame actual
        self.current_frame = frame.copy()
        
        # Procesar si está habilitado
        if self.processing_enabled:
            self._process_frame(frame)
        else:
            # Solo aplicar overlays médicos básicos
            self.processed_frame = self._apply_medical_overlays(frame)
        
        # Actualizar display
        self.update()
    
    def _process_frame(self, frame: np.ndarray):
        """
        Procesar frame con detección de ojos y pupilas.
        
        Args:
            frame: Frame BGR de entrada
        """
        try:
            # Detectar ojos y pupilas
            eye_regions, pupils = self.eye_detector.process_frame(frame)
            
            # Aplicar overlays médicos
            processed = self._apply_medical_overlays(frame)
            
            # Dibujar detecciones si están habilitadas
            if (self.show_eye_detection or self.show_pupil_detection):
                processed = self._draw_detections(processed, eye_regions, pupils)
            
            self.processed_frame = processed
            
            # Emitir señales
            self.frame_processed.emit(processed)
            
        except Exception as e:
            print(f"❌ Error procesando frame: {e}")
            # Fallback: solo overlays médicos
            self.processed_frame = self._apply_medical_overlays(frame)
    
    def _apply_medical_overlays(self, frame: np.ndarray) -> np.ndarray:
        """
        Aplicar overlays médicos básicos (cruz, círculos, información).
        
        Args:
            frame: Frame original
            
        Returns:
            Frame con overlays médicos
        """
        display_frame = frame.copy()
        h, w = frame.shape[:2]
        center_x, center_y = w // 2, h // 2
        
        # Cruz de referencia central
        if self.show_crosshair:
            cv2.line(display_frame, 
                    (center_x - 30, center_y), (center_x + 30, center_y),
                    (0, 255, 0), 2)
            cv2.line(display_frame, 
                    (center_x, center_y - 30), (center_x, center_y + 30),
                    (0, 255, 0), 2)
        
        # Círculos de calibración concéntricos
        if self.show_tracking:
            for radius in [50, 100, 150]:
                cv2.circle(display_frame, (center_x, center_y), radius, (100, 100, 255), 1)
        
        # Información del sistema
        cv2.putText(display_frame, "SIEV - Análisis Vestibular Modular", 
                   (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Estado de grabación
        status_text = self._get_status_text()
        status_color = self._get_status_color()
        cv2.putText(display_frame, status_text, 
                   (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
        
        # Información de detección
        detection_info = self._get_detection_info()
        cv2.putText(display_frame, detection_info,
                   (10, h - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        return display_frame
    
    def _draw_detections(self, frame: np.ndarray, eye_regions: List[Dict[str, Any]], pupils: List[Dict[str, Any]]) -> np.ndarray:
        """
        Dibujar detecciones de ojos y pupilas en el frame.
        
        Args:
            frame: Frame base
            eye_regions: Regiones de ojos detectadas
            pupils: Pupilas detectadas
            
        Returns:
            Frame con detecciones dibujadas
        """
        display_frame = frame.copy()
        
        # Dibujar regiones de ojos si está habilitado
        if self.show_eye_detection:
            for region in eye_regions:
                x1, y1, x2, y2 = region['bbox']
                confidence = region['confidence']
                
                # Rectángulo del ojo con color verde
                cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # Etiqueta con confianza
                label = f"Ojo: {confidence:.2f}"
                cv2.putText(display_frame, label, (x1, y1-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # Dibujar pupilas si está habilitado
        if self.show_pupil_detection:
            for pupil in pupils:
                center = pupil['center']
                radius = pupil['radius']
                
                # Círculo de la pupila con color azul
                cv2.circle(display_frame, center, radius, (255, 0, 0), 2)
                cv2.circle(display_frame, center, 2, (0, 0, 255), -1)  # Centro rojo
                
                # Etiqueta de la pupila
                label = f"Pupila r={radius}"
                cv2.putText(display_frame, label, (center[0]-30, center[1]-radius-15),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)
        
        return display_frame
    
    def _get_status_text(self) -> str:
        """Obtener texto de estado actual."""
        if self.is_recording:
            return "🔴 GRABANDO"
        elif self.camera_capture.is_camera_available():
            return "⏸️ EN VIVO"
        else:
            return "❌ DESCONECTADO"
    
    def _get_status_color(self) -> Tuple[int, int, int]:
        """Obtener color de estado actual."""
        if self.is_recording:
            return (0, 0, 255)  # Rojo
        elif self.camera_capture.is_camera_available():
            return (0, 255, 0)  # Verde
        else:
            return (128, 128, 128)  # Gris
    
    def _get_detection_info(self) -> str:
        """Obtener información de estado de detección."""
        status = self.eye_detector.get_detection_status()
        
        if status['model_loaded']:
            return f"👁️ YOLO8: Activo | Confianza: {status['confidence_threshold']}"
        else:
            return "👁️ YOLO8: No disponible"
    
    def start_recording(self):
        """Iniciar grabación."""
        if self.camera_capture.is_camera_available():
            self.is_recording = True
            print("🔴 Grabación modular iniciada")
    
    def stop_recording(self):
        """Detener grabación."""
        if self.is_recording:
            self.is_recording = False
            print("⏹️ Grabación modular detenida")
    
    def set_overlay_options(self, crosshair: bool = None, tracking: bool = None, 
                           eye_detection: bool = None, pupil_detection: bool = None):
        """
        Configurar opciones de overlay.
        
        Args:
            crosshair: Mostrar cruz central
            tracking: Mostrar círculos de calibración
            eye_detection: Mostrar detección de ojos
            pupil_detection: Mostrar detección de pupilas
        """
        if crosshair is not None:
            self.show_crosshair = crosshair
        if tracking is not None:
            self.show_tracking = tracking
        if eye_detection is not None:
            self.show_eye_detection = eye_detection
        if pupil_detection is not None:
            self.show_pupil_detection = pupil_detection
        
        print(f"🎨 Overlays actualizados: Cruz={self.show_crosshair}, "
              f"Tracking={self.show_tracking}, Ojos={self.show_eye_detection}, "
              f"Pupilas={self.show_pupil_detection}")
    
    def set_processing_enabled(self, enabled: bool):
        """Habilitar/deshabilitar procesamiento de detección."""
        self.processing_enabled = enabled
        self.eye_detector.set_detection_enabled(enabled)
        print(f"🔄 Procesamiento {'habilitado' if enabled else 'deshabilitado'}")
    
    def get_camera_status(self) -> Dict[str, Any]:
        """Obtener estado completo del sistema."""
        camera_info = self.camera_capture.get_camera_info()
        detection_info = self.eye_detector.get_detection_status()
        
        return {
            'camera': camera_info,
            'detection': detection_info,
            'widget': {
                'recording': self.is_recording,
                'processing_enabled': self.processing_enabled,
                'overlays': {
                    'crosshair': self.show_crosshair,
                    'tracking': self.show_tracking,
                    'eye_detection': self.show_eye_detection,
                    'pupil_detection': self.show_pupil_detection
                }
            }
        }
    
    # Manejadores de señales de módulos internos
    def _on_camera_connected(self, connected: bool):
        """Manejar cambio de estado de cámara."""
        self.camera_status_changed.emit(connected)
        print(f"📷 Cámara {'conectada' if connected else 'desconectada'}")
    
    def _on_frame_captured(self, frame: np.ndarray):
        """Manejar frame capturado (opcional, ya se maneja en _capture_and_process)."""
        pass
    
    def _on_capture_failed(self, error_msg: str):
        """Manejar fallo de captura."""
        print(f"❌ Fallo de captura: {error_msg}")
    
    def _on_eyes_detected(self, eye_regions: List[Dict[str, Any]]):
        """Manejar detección de ojos."""
        self.eyes_found.emit(eye_regions)
        if eye_regions:
            print(f"👁️ {len(eye_regions)} ojos detectados")
    
    def _on_pupils_detected(self, pupils: List[Dict[str, Any]]):
        """Manejar detección de pupilas."""
        self.pupils_found.emit(pupils)
        if pupils:
            print(f"🎯 {len(pupils)} pupilas detectadas")
    
    def _on_detection_failed(self, error_msg: str):
        """Manejar fallo de detección."""
        print(f"⚠️ Fallo de detección: {error_msg}")
    
    def paintEvent(self, event):
        """Renderizado del widget con frame procesado."""
        painter = QPainter(self)
        
        try:
            # Usar frame procesado si está disponible
            if self.processed_frame is not None:
                self._draw_frame(painter, self.processed_frame)
            
            elif self.current_frame is not None:
                # Fallback: frame sin procesar con overlays básicos
                basic_frame = self._apply_medical_overlays(self.current_frame)
                self._draw_frame(painter, basic_frame)
            
            else:
                # Estado sin cámara
                self._draw_no_camera_state(painter)
                
        except Exception as e:
            print(f"Error en paintEvent: {e}")
            self._draw_error_state(painter, str(e))
            
        finally:
            painter.end()
    
    def _draw_frame(self, painter: QPainter, frame: np.ndarray):
        """Dibujar frame en el widget."""
        # Convertir BGR a RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        # Calcular escalado manteniendo aspect ratio
        widget_rect = self.rect()
        image_size = qt_image.size()
        widget_size = widget_rect.size()
        
        scale_x = widget_size.width() / image_size.width()
        scale_y = widget_size.height() / image_size.height()
        scale = min(scale_x, scale_y)
        
        new_width = int(image_size.width() * scale)
        new_height = int(image_size.height() * scale)
        
        x = (widget_rect.width() - new_width) // 2
        y = (widget_rect.height() - new_height) // 2
        
        target_rect = QRect(x, y, new_width, new_height)
        painter.drawImage(target_rect, qt_image)
    
    def _draw_no_camera_state(self, painter: QPainter):
        """Dibujar estado sin cámara."""
        painter.fillRect(self.rect(), QColor(40, 40, 40))
        painter.setPen(QPen(QColor(150, 150, 150), 2))
        painter.drawRect(self.rect())
        
        painter.setPen(QPen(QColor(200, 200, 200)))
        painter.drawText(self.rect(), Qt.AlignCenter, 
                        "📹 SIEV Modular Desconectado\n\n"
                        "• Usa 'Buscar SIEV' para conectar\n"
                        "• Verifica conexión del dispositivo\n"
                        "• Sistema modular: Captura + Detección")
    
    def _draw_error_state(self, painter: QPainter, error_msg: str):
        """Dibujar estado de error."""
        painter.fillRect(self.rect(), QColor(60, 20, 20))
        painter.setPen(QPen(QColor(255, 100, 100)))
        painter.drawText(self.rect(), Qt.AlignCenter, 
                        f"❌ Error en sistema modular:\n{error_msg}")
    
    @property
    def is_connected(self) -> bool:
        """Verificar si la cámara está conectada."""
        return self.camera_capture.is_camera_available()
    
    @property
    def is_camera_available(self) -> bool:
        """Alias para compatibilidad."""
        return self.is_connected