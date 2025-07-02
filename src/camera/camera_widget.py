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
    Widget de cámara optimizado para OpenCV en tiempo real
    """
    
    frame_ready = Signal(np.ndarray)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configuración de cámara
        self.camera = None
        self.is_connected = False
        self.is_recording = False
        
        # Frame data
        self.cv_frame = None
        self.frame_rgb = None
        
        # Configuración de análisis
        self.show_crosshair = True
        self.show_tracking = True
        self.eye_position = (320, 240)
        
        # Configurar widget
        self.setMinimumSize(640, 480)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Timer para captura
        self.capture_timer = QTimer()
        self.capture_timer.timeout.connect(self.capture_frame)
        
    def init_camera(self, camera_id=2):
        """Inicializar cámara"""
        try:
            self.camera = cv2.VideoCapture(camera_id)
            
            if not self.camera.isOpened():
                return False
                
            # Configuración optimizada
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 800)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 600)
            self.camera.set(cv2.CAP_PROP_FPS, 120)
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            self.is_connected = True
            return True
            
        except Exception as e:
            print(f"Error inicializando cámara: {e}")
            return False
    
    def start_capture(self):
        """Iniciar captura"""
        if self.is_connected and not self.capture_timer.isActive():
            self.capture_timer.start(33)  # ~30 FPS
            return True
        return False
    
    def stop_capture(self):
        """Detener captura"""
        if self.capture_timer.isActive():
            self.capture_timer.stop()
        
    def release_camera(self):
        """Liberar cámara"""
        self.stop_capture()
        if self.camera:
            self.camera.release()
            self.camera = None
        self.is_connected = False
        self.cv_frame = None
        self.frame_rgb = None
        self.update()
    
    def capture_frame(self):
        """Capturar frame"""
        if not self.camera or not self.camera.isOpened():
            return
            
        ret, frame = self.camera.read()
        if ret:
            processed_frame = self.process_medical_frame(frame)
            self.frame_rgb = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
            self.frame_ready.emit(frame)
            self.update()
    
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
        
        status = "🔴 GRABANDO" if self.is_recording else "⏸️ EN VIVO"
        cv2.putText(display_frame, status, 
                   (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        return display_frame
    
    def paintEvent(self, event):
        """Renderizado optimizado"""
        painter = QPainter(self)
        
        try:
            if self.frame_rgb is not None:
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
                # Estado sin cámara
                painter.fillRect(self.rect(), QColor(40, 40, 40))
                painter.setPen(QPen(QColor(150, 150, 150), 2))
                painter.drawRect(self.rect())
                
                painter.setPen(QPen(QColor(200, 200, 200)))
                painter.drawText(self.rect(), Qt.AlignCenter, 
                               "📹 Cámara Desconectada\nPresione 'Conectar' para iniciar")
                
        except Exception as e:
            print(f"Error en paintEvent: {e}")
            painter.fillRect(self.rect(), QColor(60, 20, 20))
            painter.setPen(QPen(QColor(255, 100, 100)))
            painter.drawText(self.rect(), Qt.AlignCenter, f"Error: {str(e)}")
            
        finally:
            painter.end()