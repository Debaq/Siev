#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIEV - Sistema Integrado de Evaluación Vestibular
Main Window usando archivo .ui externo
"""

import sys
import os
import numpy as np
import time
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, 
                              QVBoxLayout, QHBoxLayout, QFrame, QPushButton,
                              QTreeWidget, QTreeWidgetItem, QSizePolicy, QGroupBox)
from PySide6.QtCore import QTimer, Qt, QSize, Signal, QRect, QFile
from PySide6.QtGui import QImage, QPixmap, QFont, QPainter, QPen, QColor
from PySide6.QtUiTools import QUiLoader
from utils.vcl_graph import VCLGraphWidget
from camera.camera_widget import OptimizedCameraWidget

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
        
        # Variables de estado
        self.start_time = time.time()
        self.current_test = "Ninguno"
        
        # Reemplazar placeholders con widgets personalizados
        self.setup_custom_widgets()
        
        # Configurar conexiones
        self.setup_connections()
        
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
        
        # === REEMPLAZAR WIDGET DE GRÁFICO CON VCLGraphWidget ===
        plot_placeholder = self.ui.widget_plot_placeholder
        plot_parent = plot_placeholder.parent()
        plot_layout = plot_parent.layout()
        
        # Encontrar índice del placeholder
        plot_index = -1
        for i in range(plot_layout.count()):
            if plot_layout.itemAt(i).widget() == plot_placeholder:
                plot_index = i
                break
        
        # Remover placeholder y agregar VCLGraphWidget
        if plot_index >= 0:
            plot_placeholder.setParent(None)
            self.vcl_graph_widget = VCLGraphWidget()
            plot_layout.insertWidget(plot_index, self.vcl_graph_widget)
            print("✅ VCLGraphWidget integrado")
        else:
            print("⚠️ No se encontró placeholder de gráfico")
        
        # === AGREGAR CONTROLES DE GRÁFICO AL PANEL DERECHO ===
        self.setup_graph_controls()
    
    def setup_graph_controls(self):
        """Agregar controles de gráfico al panel derecho"""
        if not hasattr(self.ui, 'layout_right_vertical'):
            print("⚠️ No se encontró layout del panel derecho")
            return
        
        # Crear grupo de herramientas de gráfico
        self.graph_tools_group = QGroupBox("Herramientas de Gráfico")
        self.graph_tools_group.setFont(self.ui.group_controles_analisis.font())
        
        # Layout del grupo
        graph_tools_layout = QVBoxLayout(self.graph_tools_group)
        graph_tools_layout.setSpacing(8)
        
        # Botón Toggle Torok
        self.btn_torok = QPushButton("Activar Torok")
        self.btn_torok.setCheckable(True)
        self.btn_torok.clicked.connect(self.toggle_torok)
        graph_tools_layout.addWidget(self.btn_torok)
        
        # Botón Toggle Peak Edit
        self.btn_peak_edit = QPushButton("Activar Edición Picos")
        self.btn_peak_edit.setCheckable(True)
        self.btn_peak_edit.clicked.connect(self.toggle_peak_edit)
        graph_tools_layout.addWidget(self.btn_peak_edit)
        
        # Botón Add Tiempo Fijación
        self.btn_tiempo_fijacion = QPushButton("Agregar Tiempo Fijación")
        self.btn_tiempo_fijacion.clicked.connect(self.add_tiempo_fijacion)
        graph_tools_layout.addWidget(self.btn_tiempo_fijacion)
        
        # Botón Toggle Zoom
        self.btn_zoom = QPushButton("Activar Zoom")
        self.btn_zoom.setCheckable(True)
        self.btn_zoom.clicked.connect(self.toggle_zoom)
        graph_tools_layout.addWidget(self.btn_zoom)
        
        # Botón Toggle Crosshair
        self.btn_crosshair_graph = QPushButton("Activar Cursor Cruz")
        self.btn_crosshair_graph.setCheckable(True)
        self.btn_crosshair_graph.clicked.connect(self.toggle_crosshair_graph)
        graph_tools_layout.addWidget(self.btn_crosshair_graph)
        
        # Botón Peak Detection
        self.btn_peak_detection = QPushButton("Detección Automática")
        self.btn_peak_detection.setCheckable(True)
        self.btn_peak_detection.clicked.connect(self.toggle_peak_detection)
        graph_tools_layout.addWidget(self.btn_peak_detection)
        
        # Insertar el grupo después de los controles de análisis
        right_layout = self.ui.layout_right_vertical
        # Buscar posición después del grupo de controles
        insert_position = 1  # Después del grupo_controles_analisis
        for i in range(right_layout.count()):
            item = right_layout.itemAt(i)
            if item.widget() == self.ui.group_controles_analisis:
                insert_position = i + 1
                break
        
        right_layout.insertWidget(insert_position, self.graph_tools_group)
        print("✅ Controles de gráfico agregados")
    
    def setup_graph_connections(self):
        """Conectar señales del VCLGraphWidget"""
        if hasattr(self, 'vcl_graph_widget'):
            self.vcl_graph_widget.point_added.connect(self.on_point_added)
            self.vcl_graph_widget.point_removed.connect(self.on_point_removed)
            self.vcl_graph_widget.torok_region_changed.connect(self.on_torok_changed)
            print("✅ Señales de VCLGraphWidget conectadas")
    
    def toggle_torok(self):
        """Alternar herramienta Torok"""
        if not hasattr(self, 'vcl_graph_widget'):
            return
        
        if self.btn_torok.isChecked():
            self.vcl_graph_widget.activate_torok_tool()
            self.btn_torok.setText("Desactivar Torok")
            self.ui.statusbar.showMessage("Herramienta Torok activada - ROI amarillo móvil")
        else:
            self.vcl_graph_widget.deactivate_torok_tool()
            self.btn_torok.setText("Activar Torok")
            self.ui.statusbar.showMessage("Herramienta Torok desactivada")
    
    def toggle_peak_edit(self):
        """Alternar edición de picos"""
        if not hasattr(self, 'vcl_graph_widget'):
            return
        
        if self.btn_peak_edit.isChecked():
            self.vcl_graph_widget.activate_peak_editing()
            self.btn_peak_edit.setText("Desactivar Edición")
            self.ui.statusbar.showMessage("Edición de picos activada - Click para crear/eliminar puntos")
        else:
            self.vcl_graph_widget.deactivate_peak_editing()
            self.btn_peak_edit.setText("Activar Edición Picos")
            self.ui.statusbar.showMessage("Edición de picos desactivada")
    
    def add_tiempo_fijacion(self):
        """Agregar tiempo de fijación"""
        if not hasattr(self, 'vcl_graph_widget'):
            return
        
        import random
        inicio = random.uniform(5, 45)
        fin = inicio + random.uniform(3, 10)
        self.vcl_graph_widget.create_tiempo_fijacion(inicio, fin)
        self.ui.statusbar.showMessage(f"Tiempo de fijación creado: {inicio:.1f} - {fin:.1f}s")
    
    def toggle_zoom(self):
        """Alternar zoom"""
        if not hasattr(self, 'vcl_graph_widget'):
            return
        
        if self.btn_zoom.isChecked():
            self.vcl_graph_widget.activate_zoom()
            self.btn_zoom.setText("Desactivar Zoom")
            self.ui.statusbar.showMessage("Zoom activado")
        else:
            self.vcl_graph_widget.deactivate_zoom()
            self.btn_zoom.setText("Activar Zoom")
            self.ui.statusbar.showMessage("Zoom desactivado")
    
    def toggle_crosshair_graph(self):
        """Alternar cursor cruzado en gráfico"""
        if not hasattr(self, 'vcl_graph_widget'):
            return
        
        if self.btn_crosshair_graph.isChecked():
            self.vcl_graph_widget.activate_crosshair()
            self.btn_crosshair_graph.setText("Desactivar Cruz")
            self.ui.statusbar.showMessage("Cursor cruzado activado")
        else:
            self.vcl_graph_widget.deactivate_crosshair()
            self.btn_crosshair_graph.setText("Activar Cursor Cruz")
            self.ui.statusbar.showMessage("Cursor cruzado desactivado")
    
    def toggle_peak_detection(self):
        """Alternar detección automática de picos"""
        if not hasattr(self, 'vcl_graph_widget'):
            return
        
        if self.btn_peak_detection.isChecked():
            self.vcl_graph_widget.activate_peak_detection()
            self.btn_peak_detection.setText("Desactivar Detección")
            self.ui.statusbar.showMessage("Detección automática de picos activada")
        else:
            self.vcl_graph_widget.deactivate_peak_detection()
            self.btn_peak_detection.setText("Detección Automática")
            self.ui.statusbar.showMessage("Detección automática desactivada")
    
    def on_point_added(self, tiempo, amplitud, tipo):
        """Manejar punto agregado"""
        self.ui.statusbar.showMessage(f"Punto agregado: t={tiempo:.2f}s, amp={amplitud:.2f}°, tipo={tipo}")
    
    def on_point_removed(self, tiempo, amplitud, tipo):
        """Manejar punto eliminado"""
        self.ui.statusbar.showMessage(f"Punto eliminado: t={tiempo:.2f}s, amp={amplitud:.2f}°, tipo={tipo}")
    
    def on_torok_changed(self, inicio, fin):
        """Manejar cambio de región Torok"""
        self.ui.statusbar.showMessage(f"Región Torok: {inicio:.1f} - {fin:.1f}s")
        datos_torok = self.vcl_graph_widget.get_torok()
        if datos_torok:
            puntos_count = len(datos_torok.get('tiempo', []))
            print(f"Datos en región Torok: {puntos_count} puntos")

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
        
        # Conectar señales del gráfico
        self.setup_graph_connections()
        
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
            self.start_time = time.time()
            self.ui.statusbar.showMessage("🔴 GRABANDO - Evaluación en curso")
        else:
            self.camera_widget.is_recording = False
            self.ui.btn_grabar.setText("⏺️ Grabar")
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
            
            # Simular movimiento del ojo para demostración
            center_x, center_y = 320, 240
            vel_x = 20 * np.sin(2 * np.pi * 1.5 * current_time)
            vel_y = 15 * np.cos(2 * np.pi * 0.8 * current_time)
            
            self.camera_widget.eye_position = (
                center_x + vel_x * 3,
                center_y + vel_y * 3
            )
    
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