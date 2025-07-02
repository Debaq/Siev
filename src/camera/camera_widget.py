import sys
import os
import cv2
import numpy as np
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, 
                              QVBoxLayout, QHBoxLayout, QFrame, QPushButton,
                              QTreeWidget, QTreeWidgetItem, QSizePolicy)
from PySide6.QtCore import QTimer, Qt, QSize, Signal, QRect, QFile
from PySide6.QtGui import QImage, QPixmap, QFont, QPainter, QPen, QColor
from PySide6.QtUiTools import QUiLoader
import pyqtgraph as pg
from collections import deque
import time


class OptimizedCameraWidget(QWidget):
    """
    Widget de cámara optimizado para OpenCV en tiempo real con soporte SIEV
    """
    
    # Señales para comunicar estado a main.py
    frame_ready = Signal(np.ndarray)
    camera_connected = Signal(bool)  # True=conectada, False=desconectada
    camera_disconnected = Signal()   # Señal específica de desconexión
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configuración de cámara
        self.camera = None
        self.is_connected = False
        self.is_recording = False
        self.camera_index = None  # Índice actual de cámara
        
        # Frame data
        self.cv_frame = None
        self.frame_rgb = None
        
        # Configuración de análisis
        self.show_crosshair = True
        self.show_tracking = True
        self.eye_position = (320, 240)
        
        # Control de errores de captura
        self.consecutive_failures = 0
        self.max_failures = 5  # Máximo fallos antes de considerar desconectada
        
        # Configurar widget
        self.setMinimumSize(640, 480)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Timer para captura
        self.capture_timer = QTimer()
        self.capture_timer.timeout.connect(self.capture_frame)
        
    def init_camera(self, camera_index: int) -> bool:
        """
        Inicializar cámara con índice específico (requerido)
        
        Args:
            camera_index: Índice de cámara obtenido del modal SIEV
            
        Returns:
            bool: True si la cámara se inicializó correctamente
        """
        try:
            print(f"🔌 Intentando conectar cámara en índice {camera_index}")
            
            # Liberar cámara anterior si existe
            if self.camera:
                self.camera.release()
                self.camera = None
            
            # Crear nueva captura
            self.camera = cv2.VideoCapture(camera_index)
            
            if not self.camera.isOpened():
                print(f"❌ No se pudo abrir cámara en índice {camera_index}")
                return False
                
            # Configuración optimizada
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 800)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 600)
            self.camera.set(cv2.CAP_PROP_FPS, 120)
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M','J','P','G'))

            
            # Test de captura inicial
            ret, test_frame = self.camera.read()
            if not ret or test_frame is None:
                print(f"❌ Cámara {camera_index} no puede capturar frames")
                self.camera.release()
                self.camera = None
                return False
            
            # Éxito
            self.camera_index = camera_index
            self.is_connected = True
            self.consecutive_failures = 0
            
            print(f"✅ Cámara {camera_index} conectada correctamente")
            self.camera_connected.emit(True)
            return True
            
        except Exception as e:
            print(f"❌ Error inicializando cámara {camera_index}: {e}")
            if self.camera:
                self.camera.release()
                self.camera = None
            return False
    
    def start_capture(self) -> bool:
        """Iniciar captura si hay cámara conectada"""
        if self.is_connected and not self.capture_timer.isActive():
            self.capture_timer.start(33)  # ~30 FPS
            print("▶️ Captura de cámara iniciada")
            return True
        return False
    
    def stop_capture(self):
        """Detener captura"""
        if self.capture_timer.isActive():
            self.capture_timer.stop()
            print("⏸️ Captura de cámara detenida")
        
    def release_camera(self):
        """Liberar cámara completamente"""
        print("🔌 Liberando cámara...")
        
        self.stop_capture()
        
        if self.camera:
            self.camera.release()
            self.camera = None
        
        self.is_connected = False
        self.is_recording = False
        self.camera_index = None
        self.cv_frame = None
        self.frame_rgb = None
        self.consecutive_failures = 0
        
        self.camera_connected.emit(False)
        self.update()
        
        print("✅ Cámara liberada")
    
    def capture_frame(self):
        """Capturar frame con detección de desconexión"""
        if not self.camera or not self.camera.isOpened():
            self._handle_capture_failure("Cámara no disponible")
            return
            
        try:
            ret, frame = self.camera.read()
            
            if not ret or frame is None:
                self._handle_capture_failure("No se pudo capturar frame")
                return
            
            # Frame capturado exitosamente
            self.consecutive_failures = 0
            processed_frame = self.process_medical_frame(frame)
            self.frame_rgb = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
            self.frame_ready.emit(frame)
            self.update()
            
        except Exception as e:
            self._handle_capture_failure(f"Error en captura: {e}")
    
    def _handle_capture_failure(self, error_msg: str):
        """Manejar fallos de captura y detectar desconexión"""
        self.consecutive_failures += 1
        
        if self.consecutive_failures >= self.max_failures:
            print(f"❌ Cámara desconectada: {error_msg} (fallos: {self.consecutive_failures})")
            
            # Marcar como desconectada
            self.is_connected = False
            self.stop_capture()
            
            # Notificar desconexión
            self.camera_connected.emit(False)
            self.camera_disconnected.emit()
            
            # Actualizar display
            self.cv_frame = None
            self.frame_rgb = None
            self.update()
        else:
            print(f"⚠️ Fallo de captura {self.consecutive_failures}/{self.max_failures}: {error_msg}")
    
    def start_recording(self):
        """Iniciar grabación (solo si hay cámara)"""
        if self.is_connected:
            self.is_recording = True
            print("🔴 Grabación iniciada")
    
    def stop_recording(self):
        """Detener grabación"""
        if self.is_recording:
            self.is_recording = False
            print("⏹️ Grabación detenida")
    
    def is_camera_available(self) -> bool:
        """Verificar si la cámara está disponible"""
        return self.is_connected and self.camera is not None
    
    def get_camera_status(self) -> dict:
        """Obtener estado completo de la cámara"""
        return {
            'connected': self.is_connected,
            'recording': self.is_recording,
            'camera_index': self.camera_index,
            'consecutive_failures': self.consecutive_failures
        }
    
    def process_medical_frame(self, frame):
        """Procesar frame con overlays médicos"""
        display_frame = frame.copy()
        h, w = frame.shape[:2]
        center_x, center_y = w // 2, h // 2
        
        # Cruz de referencia
        if self.show_crosshair:
            cv2.line(display_frame, 
                    (center_x - 30, center_y), (center_x + 30, center_y),
                    (0, 255, 0), 2)
            cv2.line(display_frame, 
                    (center_x, center_y - 30), (center_x, center_y + 30),
                    (0, 255, 0), 2)
        
        # Círculos de calibración
        for radius in [50, 100, 150]:
            cv2.circle(display_frame, (center_x, center_y), radius, (100, 100, 255), 1)
        
        # Tracking del ojo
        if self.show_tracking:
            eye_x, eye_y = self.eye_position
            cv2.circle(display_frame, (int(eye_x), int(eye_y)), 20, (255, 0, 0), 2)
            cv2.circle(display_frame, (int(eye_x), int(eye_y)), 8, (0, 0, 255), -1)
        
        # Información
        cv2.putText(display_frame, "SIEV - Análisis Vestibular", 
                   (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Estado de grabación y cámara
        if self.is_recording:
            status = "🔴 GRABANDO"
            color = (0, 0, 255)  # Rojo
        elif self.is_connected:
            status = "⏸️ EN VIVO"  
            color = (0, 255, 0)  # Verde
        else:
            status = "❌ DESCONECTADO"
            color = (128, 128, 128)  # Gris
            
        cv2.putText(display_frame, status, 
                   (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        return display_frame
    
    def paintEvent(self, event):
        """Renderizado optimizado con estados de cámara"""
        painter = QPainter(self)
        
        try:
            if self.frame_rgb is not None and self.is_connected:
                # Mostrar frame de cámara
                h, w, ch = self.frame_rgb.shape
                bytes_per_line = ch * w
                
                qt_image = QImage(self.frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
                
                # Calcular escalado
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
                
            else:
                # Estado sin cámara o desconectada
                if self.is_connected:
                    # Conectada pero sin frame
                    painter.fillRect(self.rect(), QColor(60, 60, 60))
                    painter.setPen(QPen(QColor(255, 255, 0), 2))
                    painter.drawRect(self.rect())
                    
                    painter.setPen(QPen(QColor(255, 255, 0)))
                    painter.drawText(self.rect(), Qt.AlignCenter, 
                                   "⚠️ Cámara conectada\nPero sin señal de video")
                else:
                    # Desconectada
                    painter.fillRect(self.rect(), QColor(40, 40, 40))
                    painter.setPen(QPen(QColor(150, 150, 150), 2))
                    painter.drawRect(self.rect())
                    
                    painter.setPen(QPen(QColor(200, 200, 200)))
                    painter.drawText(self.rect(), Qt.AlignCenter, 
                                   "📹 SIEV Desconectado\n\nUse 'Buscar SIEV' para reconectar\no verifique la conexión del dispositivo")
                
        except Exception as e:
            print(f"Error en paintEvent: {e}")
            painter.fillRect(self.rect(), QColor(60, 20, 20))
            painter.setPen(QPen(QColor(255, 100, 100)))
            painter.drawText(self.rect(), Qt.AlignCenter, f"Error: {str(e)}")
            
        finally:
            painter.end()