#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIEV - Sistema Integrado de Evaluación Vestibular
Main Window - Solo coordinador entre módulos
"""

import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, 
                              QVBoxLayout, QHBoxLayout, QFrame, QPushButton,
                              QTreeWidget, QTreeWidgetItem, QSizePolicy, QGroupBox)
from PySide6.QtCore import QTimer, Qt, QSize, Signal, QRect, QFile
from PySide6.QtGui import QIcon
from PySide6.QtUiTools import QUiLoader
from utils.vcl_graph import VCLGraphWidget
from camera.camera_widget import OptimizedCameraWidget
from utils.siev_detection_modal import SievDetectionModal
from utils.icon_utils import get_icon, set_qt_ready

class SIEVMainWindow(QMainWindow):
    """
    Ventana principal - Solo coordinador de módulos
    """
    
    def __init__(self, ui_file_path="ui/main_window.ui"):
        super().__init__()
        
        # Variables de estado SIEV
        self.siev_setup = None
        self.siev_camera_index = None
        self.siev_serial_port = None
        self.siev_connected = False
        
        # Variables de estado
        self.current_test = "Ninguno"
        
        # Cargar UI
        self.ui = self.load_ui(ui_file_path)
        if not self.ui:
            raise Exception(f"No se pudo cargar el archivo UI: {ui_file_path}")
        
        # Configurar ventana principal
        self.setCentralWidget(self.ui.centralwidget)
        self.setMenuBar(self.ui.menubar)
        self.setStatusBar(self.ui.statusbar)
        self.setWindowTitle(self.ui.windowTitle())
        self.setGeometry(self.ui.geometry())
        
        # Configurar widgets personalizados
        self.setup_custom_widgets()
        
        # Configurar conexiones
        self.setup_connections()
        
        # ACTIVAR iconos después de que Qt esté completamente listo
        QTimer.singleShot(1000, lambda: set_qt_ready(True))
        
        # Detectar SIEV al iniciar (más tarde)
        QTimer.singleShot(2000, self.detect_siev_on_startup)
    
    def load_ui(self, ui_file_path):
        """Cargar archivo .ui"""
        try:
            if not os.path.exists(ui_file_path):
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
                    return None
            
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
        """Configurar widgets personalizados"""
        
        # Reemplazar widget de cámara
        self.setup_camera_widget()
        
        # Reemplazar widget de gráfico
        self.setup_graph_widget()
        
        # Agregar controles de gráfico
        self.setup_graph_controls()
    
    def setup_camera_widget(self):
        """Configurar widget de cámara"""
        camera_placeholder = self.ui.widget_camera_placeholder
        camera_parent = camera_placeholder.parent()
        camera_layout = camera_parent.layout()
        
        camera_index = -1
        for i in range(camera_layout.count()):
            if camera_layout.itemAt(i).widget() == camera_placeholder:
                camera_index = i
                break
        
        if camera_index >= 0:
            camera_placeholder.setParent(None)
            self.camera_widget = OptimizedCameraWidget()
            camera_layout.insertWidget(camera_index, self.camera_widget)
            print("✅ Widget de cámara integrado")
    
    def setup_graph_widget(self):
        """Configurar widget de gráfico"""
        plot_placeholder = self.ui.widget_plot_placeholder
        plot_parent = plot_placeholder.parent()
        plot_layout = plot_parent.layout()
        
        plot_index = -1
        for i in range(plot_layout.count()):
            if plot_layout.itemAt(i).widget() == plot_placeholder:
                plot_index = i
                break
        
        if plot_index >= 0:
            plot_placeholder.setParent(None)
            self.vcl_graph_widget = VCLGraphWidget()
            plot_layout.insertWidget(plot_index, self.vcl_graph_widget)
            print("✅ VCLGraphWidget integrado")
    
    def setup_graph_controls(self):
        """Agregar controles de gráfico"""
        if not hasattr(self.ui, 'layout_right_vertical'):
            return
        
        self.graph_tools_group = QGroupBox("Herramientas de Gráfico")
        self.graph_tools_group.setFont(self.ui.group_controles_analisis.font())
        
        graph_tools_layout = QVBoxLayout(self.graph_tools_group)
        graph_tools_layout.setSpacing(8)
        
        # Botones de herramientas
        self.btn_torok = QPushButton("Activar Torok")
        self.btn_torok.setCheckable(True)
        self.btn_torok.clicked.connect(self.toggle_torok)
        graph_tools_layout.addWidget(self.btn_torok)
        
        self.btn_peak_edit = QPushButton("Activar Edición Picos")
        self.btn_peak_edit.setCheckable(True)
        self.btn_peak_edit.clicked.connect(self.toggle_peak_edit)
        graph_tools_layout.addWidget(self.btn_peak_edit)
        
        self.btn_tiempo_fijacion = QPushButton("Agregar Tiempo Fijación")
        self.btn_tiempo_fijacion.clicked.connect(self.add_tiempo_fijacion)
        graph_tools_layout.addWidget(self.btn_tiempo_fijacion)
        
        self.btn_zoom = QPushButton("Activar Zoom")
        self.btn_zoom.setCheckable(True)
        self.btn_zoom.clicked.connect(self.toggle_zoom)
        graph_tools_layout.addWidget(self.btn_zoom)
        
        self.btn_crosshair_graph = QPushButton("Activar Cursor Cruz")
        self.btn_crosshair_graph.setCheckable(True)
        self.btn_crosshair_graph.clicked.connect(self.toggle_crosshair_graph)
        graph_tools_layout.addWidget(self.btn_crosshair_graph)
        
        self.btn_peak_detection = QPushButton("Detección Automática")
        self.btn_peak_detection.setCheckable(True)
        self.btn_peak_detection.clicked.connect(self.toggle_peak_detection)
        graph_tools_layout.addWidget(self.btn_peak_detection)
        
        # Insertar en panel derecho
        right_layout = self.ui.layout_right_vertical
        insert_position = 1
        for i in range(right_layout.count()):
            item = right_layout.itemAt(i)
            if item.widget() == self.ui.group_controles_analisis:
                insert_position = i + 1
                break
        
        right_layout.insertWidget(insert_position, self.graph_tools_group)
        print("✅ Controles de gráfico agregados")
    
    def setup_connections(self):
        """Configurar conexiones"""
        if not hasattr(self.ui, 'btn_conectar_camara'):
            print("⚠️ No se encontraron algunos botones en el UI")
            return
        
        # Configurar botón principal SIN iconos por ahora
        self.ui.btn_conectar_camara.setText("🔍 Buscar SIEV")
        self.ui.btn_conectar_camara.clicked.connect(self.handle_main_button)
        
        # Otros botones
        self.ui.btn_grabar.clicked.connect(self.toggle_recording)
        self.ui.tree_pruebas.itemClicked.connect(self.on_prueba_selected)
        self.ui.btn_iniciar_prueba.clicked.connect(self.iniciar_prueba_seleccionada)
        
        # Controles de cámara
        if hasattr(self.ui, 'check_crosshair'):
            self.ui.check_crosshair.toggled.connect(self.update_camera_options)
            self.ui.check_tracking.toggled.connect(self.update_camera_options)
        
        # Señales del gráfico
        if hasattr(self, 'vcl_graph_widget'):
            self.vcl_graph_widget.point_added.connect(self.on_point_added)
            self.vcl_graph_widget.point_removed.connect(self.on_point_removed)
            self.vcl_graph_widget.torok_region_changed.connect(self.on_torok_changed)
        
        print("✅ Conexiones configuradas")
        
        # CARGAR ICONOS DESPUÉS de que todo esté configurado
        QTimer.singleShot(500, self.load_icons)
    
    def load_icons(self):
        """Cargar iconos de Lucide después de inicialización completa"""
        try:
            # Cargar icono del botón principal
            search_icon = get_icon("search", 16)
            self.ui.btn_conectar_camara.setIcon(QIcon(search_icon))
            print("✅ Iconos cargados correctamente")
        except Exception as e:
            print(f"⚠️ Error cargando iconos: {e}")
            # Continuar sin iconos si hay problemas
        
        # CARGAR ICONOS DESPUÉS de que todo esté configurado
        QTimer.singleShot(100, self.load_icons)
    
    # ===== MÉTODOS SIEV =====
    
    def detect_siev_on_startup(self):
        """Detectar SIEV al iniciar"""
        self.show_siev_detection_modal()
    
    def show_siev_detection_modal(self):
        """Mostrar modal de detección SIEV"""
        modal = SievDetectionModal(self)
        result = modal.exec()
        
        detection_result = modal.get_detection_result()
        
        if detection_result and detection_result['success']:
            # SIEV detectado
            self.siev_setup = detection_result['setup']
            self.siev_camera_index = self.siev_setup['camera'].get('opencv_index')
            self.siev_serial_port = self.siev_setup['esp8266']['port']
            self.siev_connected = True
            
            self.update_siev_status()
            self.switch_to_camera_mode()
            
        else:
            # SIEV no detectado
            self.siev_connected = False
            self.update_siev_status()
    
    def handle_main_button(self):
        """Manejar click del botón principal"""
        if not self.siev_connected:
            # Buscar SIEV
            self.show_siev_detection_modal()
        else:
            # Toggle cámara
            self.toggle_camera()
    
    def switch_to_camera_mode(self):
        """Cambiar botón a modo cámara"""
        self.ui.btn_conectar_camara.setText("📹 Conectar Cámara")
        try:
            camera_icon = get_icon("camera", 16)
            self.ui.btn_conectar_camara.setIcon(QIcon(camera_icon))
        except:
            pass  # Si falla el icono, continuar sin él
    
    def switch_to_siev_mode(self):
        """Cambiar botón a modo SIEV"""
        self.ui.btn_conectar_camara.setText("🔍 Buscar SIEV")
        try:
            search_icon = get_icon("search", 16)
            self.ui.btn_conectar_camara.setIcon(QIcon(search_icon))
        except:
            pass  # Si falla el icono, continuar sin él
    
    def update_siev_status(self):
        """Actualizar estado SIEV en interfaz"""
        if self.siev_connected and self.siev_setup:
            # Estado conectado
            siev_info = (
                f"🔗 SIEV Conectado\n"
                f"📡 ESP8266: {self.siev_serial_port}\n"
                f"📹 Cámara: OpenCV índice {self.siev_camera_index}\n"
                f"🏥 Estado: Listo para evaluación"
            )
            
            if hasattr(self.ui, 'lbl_patient_info'):
                self.ui.lbl_patient_info.setText(siev_info)
                self.ui.lbl_patient_info.setStyleSheet("""
                    QLabel {
                        background-color: #d5ead4;
                        padding: 10px;
                        border-radius: 5px;
                        color: #2c3e50;
                        border: 1px solid #27ae60;
                    }
                """)
            
            self.ui.statusbar.showMessage("✅ Hardware SIEV conectado y listo")
            
        else:
            # Estado desconectado
            siev_info = (
                f"❌ SIEV No Conectado\n"
                f"📅 Fecha: --/--/----\n"
                f"🏥 Estado: Hardware no disponible\n"
                f"💡 Use 'Buscar SIEV' para conectar"
            )
            
            if hasattr(self.ui, 'lbl_patient_info'):
                self.ui.lbl_patient_info.setText(siev_info)
                self.ui.lbl_patient_info.setStyleSheet("""
                    QLabel {
                        background-color: #fdeaea;
                        padding: 10px;
                        border-radius: 5px;
                        color: #2c3e50;
                        border: 1px solid #e74c3c;
                    }
                """)
            
            self.ui.statusbar.showMessage("⚠️ Hardware SIEV no detectado")
            self.switch_to_siev_mode()
    
    # ===== MÉTODOS DE CÁMARA (delegación) =====
    
    def toggle_camera(self):
        """Toggle cámara (delega al camera_widget)"""
        if not hasattr(self, 'camera_widget') or not self.siev_connected:
            return
        
        if not self.camera_widget.is_connected:
            # Conectar usando índice SIEV
            if self.camera_widget.init_camera(self.siev_camera_index):
                self.camera_widget.start_capture()
                self.ui.btn_conectar_camara.setText("🔌 Desconectar Cámara")
                self.ui.btn_grabar.setEnabled(True)
                self.ui.lbl_estado_camara.setText("Estado: Conectado ✅")
                self.ui.lbl_estado_camara.setStyleSheet("color: green; font-weight: bold;")
            else:
                self.ui.lbl_estado_camara.setText("Estado: Error ❌")
                self.ui.lbl_estado_camara.setStyleSheet("color: red; font-weight: bold;")
        else:
            # Desconectar
            self.camera_widget.release_camera()
            self.ui.btn_conectar_camara.setText("📹 Conectar Cámara")
            self.ui.btn_grabar.setEnabled(False)
            self.ui.btn_grabar.setText("⏺️ Grabar")
            self.ui.lbl_estado_camara.setText("Estado: Desconectado")
            self.ui.lbl_estado_camara.setStyleSheet("color: gray;")
    
    def toggle_recording(self):
        """Toggle grabación (delega al camera_widget)"""
        if not hasattr(self, 'camera_widget'):
            return
        
        if not self.camera_widget.is_recording:
            self.camera_widget.start_recording()
            self.ui.btn_grabar.setText("⏹️ Detener")
            self.ui.statusbar.showMessage("🔴 GRABANDO - Evaluación en curso")
        else:
            self.camera_widget.stop_recording()
            self.ui.btn_grabar.setText("⏺️ Grabar")
            self.ui.statusbar.showMessage("Grabación detenida")
    
    def update_camera_options(self):
        """Actualizar opciones de cámara (delega)"""
        if hasattr(self, 'camera_widget') and hasattr(self.ui, 'check_crosshair'):
            self.camera_widget.show_crosshair = self.ui.check_crosshair.isChecked()
            self.camera_widget.show_tracking = self.ui.check_tracking.isChecked()
    
    # ===== MÉTODOS DE GRÁFICO (delegación) =====
    
    def toggle_torok(self):
        if hasattr(self, 'vcl_graph_widget'):
            if self.btn_torok.isChecked():
                self.vcl_graph_widget.activate_torok_tool()
                self.btn_torok.setText("Desactivar Torok")
            else:
                self.vcl_graph_widget.deactivate_torok_tool()
                self.btn_torok.setText("Activar Torok")
    
    def toggle_peak_edit(self):
        if hasattr(self, 'vcl_graph_widget'):
            if self.btn_peak_edit.isChecked():
                self.vcl_graph_widget.activate_peak_editing()
                self.btn_peak_edit.setText("Desactivar Edición")
            else:
                self.vcl_graph_widget.deactivate_peak_editing()
                self.btn_peak_edit.setText("Activar Edición Picos")
    
    def add_tiempo_fijacion(self):
        if hasattr(self, 'vcl_graph_widget'):
            import random
            inicio = random.uniform(5, 45)
            fin = inicio + random.uniform(3, 10)
            self.vcl_graph_widget.create_tiempo_fijacion(inicio, fin)
    
    def toggle_zoom(self):
        if hasattr(self, 'vcl_graph_widget'):
            if self.btn_zoom.isChecked():
                self.vcl_graph_widget.activate_zoom()
                self.btn_zoom.setText("Desactivar Zoom")
            else:
                self.vcl_graph_widget.deactivate_zoom()
                self.btn_zoom.setText("Activar Zoom")
    
    def toggle_crosshair_graph(self):
        if hasattr(self, 'vcl_graph_widget'):
            if self.btn_crosshair_graph.isChecked():
                self.vcl_graph_widget.activate_crosshair()
                self.btn_crosshair_graph.setText("Desactivar Cruz")
            else:
                self.vcl_graph_widget.deactivate_crosshair()
                self.btn_crosshair_graph.setText("Activar Cursor Cruz")
    
    def toggle_peak_detection(self):
        if hasattr(self, 'vcl_graph_widget'):
            if self.btn_peak_detection.isChecked():
                self.vcl_graph_widget.activate_peak_detection()
                self.btn_peak_detection.setText("Desactivar Detección")
            else:
                self.vcl_graph_widget.deactivate_peak_detection()
                self.btn_peak_detection.setText("Detección Automática")
    
    def on_point_added(self, tiempo, amplitud, tipo):
        self.ui.statusbar.showMessage(f"Punto agregado: t={tiempo:.2f}s, tipo={tipo}")
    
    def on_point_removed(self, tiempo, amplitud, tipo):
        self.ui.statusbar.showMessage(f"Punto eliminado: t={tiempo:.2f}s, tipo={tipo}")
    
    def on_torok_changed(self, inicio, fin):
        self.ui.statusbar.showMessage(f"Región Torok: {inicio:.1f} - {fin:.1f}s")
    
    # ===== MÉTODOS DE PRUEBAS =====
    
    def on_prueba_selected(self, item, column):
        self.current_test = item.text(0)
        self.ui.statusbar.showMessage(f"Prueba seleccionada: {self.current_test}")
    
    def iniciar_prueba_seleccionada(self):
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
    
    try:
        window = SIEVMainWindow("main_window.ui")
        window.show()
        print("✅ SIEV iniciado correctamente")
        
    except Exception as e:
        print(f"❌ Error iniciando SIEV: {e}")
        return 1
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())