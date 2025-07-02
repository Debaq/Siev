#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIEV - Sistema Integrado de Evaluación Vestibular
Main Window usando archivo .ui externo
"""

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
from collections import deque
import time
from utils.vcl_graph import VCLGraphWidget

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

class SIEVMainWindow(QMainWindow):
    """
    Ventana principal cargando UI desde archivo .ui
    """
    
    def __init__(self, ui_file_path="ui/main_window.ui"):
        super().__init__()
        
        # Cargar UI desde archivo
        self.ui = self.load_ui(ui_file_path)
        if not self.ui:
            raise Exception(f"No se pudo cargar el archivo UI: {ui_file_path}")
        
        # Configurar como ventana principal
        self.setCentralWidget(self.ui.centralwidget)
        self.setMenuBar(self.ui.menubar)
        self.setStatusBar(self.ui.statusbar)
        
        # Aplicar propiedades de la ventana
        self.setWindowTitle(self.ui.windowTitle())
        self.setGeometry(self.ui.geometry())
        
        # Datos de análisis
        self.time_data = deque(maxlen=1000)
        self.velocity_x_data = deque(maxlen=1000)
        self.velocity_y_data = deque(maxlen=1000)
        self.start_time = time.time()
        self.current_test = "Ninguno"
        
        # Reemplazar placeholders con widgets personalizados
        self.setup_custom_widgets()
        
        # Configurar conexiones
        self.setup_connections()
        
        # Timer para gráficos
        self.plot_timer = QTimer()
        self.plot_timer.timeout.connect(self.update_plots)
        
    def load_ui(self, ui_file_path):
        """Cargar archivo .ui"""
        try:
            # Buscar archivo UI
            if not os.path.exists(ui_file_path):
                # Buscar en directorio actual y directorios padre
                possible_paths = [
                    ui_file_path,
                    os.path.join("ui", ui_file_path),
                    os.path.join("src", "ui", ui_file_path),
                    os.path.join("..", ui_file_path),
                ]
                
                ui_file_path = None
                for path in possible_paths:
                    if os.path.exists(path):
                        ui_file_path = path
                        break
                
                if not ui_file_path:
                    print("❌ No se encontró el archivo main_window.ui")
                    print("📁 Busque en:", possible_paths)
                    return None
            
            # Cargar UI
            ui_file = QFile(ui_file_path)
            if not ui_file.open(QFile.ReadOnly):
                print(f"❌ No se puede abrir el archivo: {ui_file_path}")
                return None
            
            loader = QUiLoader()
            ui = loader.load(ui_file)
            ui_file.close()
            
            print(f"✅ UI cargado desde: {ui_file_path}")
            return ui
            
        except Exception as e:
            print(f"❌ Error cargando UI: {e}")
            return None
    
    def setup_custom_widgets(self):
        """Reemplazar placeholders con widgets personalizados"""
        
        # === REEMPLAZAR WIDGET DE CÁMARA ===
        camera_placeholder = self.ui.widget_camera_placeholder
        camera_parent = camera_placeholder.parent()
        camera_layout = camera_parent.layout()
        
        # Encontrar índice del placeholder en el layout
        camera_index = -1
        for i in range(camera_layout.count()):
            if camera_layout.itemAt(i).widget() == camera_placeholder:
                camera_index = i
                break
        
        # Remover placeholder y agregar widget personalizado
        if camera_index >= 0:
            camera_placeholder.setParent(None)
            self.camera_widget = OptimizedCameraWidget()
            camera_layout.insertWidget(camera_index, self.camera_widget)
            print("✅ Widget de cámara integrado")
        else:
            print("⚠️ No se encontró placeholder de cámara")
        
        # === REEMPLAZAR WIDGET DE GRÁFICO ===
        plot_placeholder = self.ui.widget_plot_placeholder
        plot_parent = plot_placeholder.parent()
        plot_layout = plot_parent.layout()
        
        # Encontrar índice del placeholder
        plot_index = -1
        for i in range(plot_layout.count()):
            if plot_layout.itemAt(i).widget() == plot_placeholder:
                plot_index = i
                break
        
        # Remover placeholder y agregar PyQtGraph
        if plot_index >= 0:
            plot_placeholder.setParent(None)
            self.plot_widget = pg.PlotWidget(title="Análisis Vestibular en Tiempo Real")
            self.plot_widget.setLabel('left', 'Velocidad Angular (deg/s)')
            self.plot_widget.setLabel('bottom', 'Tiempo (s)')
            self.plot_widget.addLegend()
            
            # Curvas de datos
            self.curve_x = self.plot_widget.plot(pen='r', name='Velocidad X')
            self.curve_y = self.plot_widget.plot(pen='b', name='Velocidad Y')
            
            plot_layout.insertWidget(plot_index, self.plot_widget)
            print("✅ Widget de gráfico integrado")
        else:
            print("⚠️ No se encontró placeholder de gráfico")
    
    def setup_connections(self):
        """Configurar conexiones de señales"""
        
        # Verificar que los widgets existen
        if not hasattr(self.ui, 'btn_conectar_camara'):
            print("⚠️ No se encontraron algunos botones en el UI")
            return
        
        # Conectar botones de cámara
        self.ui.btn_conectar_camara.clicked.connect(self.toggle_camera)
        self.ui.btn_grabar.clicked.connect(self.toggle_recording)
        
        # Conectar tree de pruebas
        self.ui.tree_pruebas.itemClicked.connect(self.on_prueba_selected)
        self.ui.btn_iniciar_prueba.clicked.connect(self.iniciar_prueba_seleccionada)
        
        # Conectar controles
        if hasattr(self.ui, 'check_crosshair'):
            self.ui.check_crosshair.toggled.connect(self.update_camera_options)
            self.ui.check_tracking.toggled.connect(self.update_camera_options)
        
        # Conectar señal de cámara
        if hasattr(self, 'camera_widget'):
            self.camera_widget.frame_ready.connect(self.process_frame_data)
        
        print("✅ Conexiones configuradas")
    
    def toggle_camera(self):
        """Alternar cámara"""
        if not hasattr(self, 'camera_widget'):
            print("❌ Widget de cámara no disponible")
            return
            
        if not self.camera_widget.is_connected:
            if self.camera_widget.init_camera():
                self.camera_widget.start_capture()
                self.ui.btn_conectar_camara.setText("🔌 Desconectar")
                self.ui.btn_grabar.setEnabled(True)
                self.ui.lbl_estado_camara.setText("Estado: Conectado ✅")
                self.ui.lbl_estado_camara.setStyleSheet("color: green; font-weight: bold;")
                self.ui.statusbar.showMessage("Cámara conectada - Lista para evaluación")
            else:
                self.ui.lbl_estado_camara.setText("Estado: Error ❌")
                self.ui.lbl_estado_camara.setStyleSheet("color: red; font-weight: bold;")
        else:
            self.camera_widget.release_camera()
            self.ui.btn_conectar_camara.setText("🔗 Conectar Cámara")
            self.ui.btn_grabar.setEnabled(False)
            self.ui.btn_grabar.setText("⏺️ Grabar")
            self.ui.lbl_estado_camara.setText("Estado: Desconectado")
            self.ui.lbl_estado_camara.setStyleSheet("color: gray;")
            self.ui.statusbar.showMessage("Cámara desconectada")
    
    def toggle_recording(self):
        """Alternar grabación"""
        if not hasattr(self, 'camera_widget'):
            return
            
        if not self.camera_widget.is_recording:
            self.camera_widget.is_recording = True
            self.ui.btn_grabar.setText("⏹️ Detener")
            self.plot_timer.start(50)
            self.start_time = time.time()
            self.ui.statusbar.showMessage("🔴 GRABANDO - Evaluación en curso")
        else:
            self.camera_widget.is_recording = False
            self.ui.btn_grabar.setText("⏺️ Grabar")
            self.plot_timer.stop()
            self.ui.statusbar.showMessage("Grabación detenida - Datos guardados")
    
    def update_camera_options(self):
        """Actualizar opciones de cámara"""
        if hasattr(self, 'camera_widget') and hasattr(self.ui, 'check_crosshair'):
            self.camera_widget.show_crosshair = self.ui.check_crosshair.isChecked()
            self.camera_widget.show_tracking = self.ui.check_tracking.isChecked()
    
    def process_frame_data(self, frame):
        """Procesar frame para análisis"""
        if hasattr(self, 'camera_widget') and self.camera_widget.is_recording:
            current_time = time.time() - self.start_time
            
            # Simular datos vestibulares
            vel_x = 20 * np.sin(2 * np.pi * 1.5 * current_time) + 5 * np.random.random()
            vel_y = 15 * np.cos(2 * np.pi * 0.8 * current_time) + 3 * np.random.random()
            
            self.time_data.append(current_time)
            self.velocity_x_data.append(vel_x)
            self.velocity_y_data.append(vel_y)
            
            # Actualizar posición de tracking
            center_x, center_y = 320, 240
            self.camera_widget.eye_position = (
                center_x + vel_x * 3,
                center_y + vel_y * 3
            )
    
    def update_plots(self):
        """Actualizar gráficos"""
        if hasattr(self, 'plot_widget') and len(self.time_data) > 1:
            self.curve_x.setData(list(self.time_data), list(self.velocity_x_data))
            self.curve_y.setData(list(self.time_data), list(self.velocity_y_data))
    
    def on_prueba_selected(self, item, column):
        """Manejar selección de prueba"""
        self.current_test = item.text(0)
        self.ui.statusbar.showMessage(f"Prueba seleccionada: {self.current_test}")
    
    def iniciar_prueba_seleccionada(self):
        """Iniciar prueba"""
        if self.current_test != "Ninguno":
            self.ui.statusbar.showMessage(f"Iniciando: {self.current_test}")
        else:
            self.ui.statusbar.showMessage("Seleccione una prueba primero")
    
    def closeEvent(self, event):
        """Cleanup al cerrar"""
        if hasattr(self, 'camera_widget') and self.camera_widget.is_connected:
            self.camera_widget.release_camera()
        event.accept()

def main():
    """Función principal"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    print("🚀 Iniciando SIEV...")
    print("📂 Buscando archivo main_window.ui...")
    
    try:
        # Crear ventana principal
        window = SIEVMainWindow("main_window.ui")
        window.show()
        
        print("✅ SIEV iniciado correctamente")
        print("📹 Use 'Conectar Cámara' para comenzar")
        
    except Exception as e:
        print(f"❌ Error iniciando SIEV: {e}")
        return 1
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())