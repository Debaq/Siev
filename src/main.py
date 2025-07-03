#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIEV - Sistema Integrado de Evaluación Vestibular
Main Window - Completo con sistema modular de protocolos
"""

import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, 
                              QVBoxLayout, QHBoxLayout, QFrame, QPushButton,
                              QSizePolicy, QGroupBox)
from PySide6.QtCore import QTimer, Qt, QSize, Signal, QRect, QFile
from PySide6.QtGui import QIcon
from PySide6.QtUiTools import QUiLoader

# Imports de widgets personalizados
from utils.vcl_graph import VCLGraphWidget
from camera.camera_widget import ModularCameraWidget
from utils.siev_detection_modal import SievDetectionModal
from utils.icon_utils import get_icon, IconColors

# Imports de módulos de protocolos
from widgets.protocol_tree_widget import ProtocolTreeWidget
from utils.protocol_executor import ProtocolExecutor
from utils.protocol_manager import ProtocolManager
from utils.dialog_utils import (show_info, show_success, show_warning, show_error, 
                               ask_confirmation, DialogUtils)
from widgets.protocol_config_dialog import show_protocol_config_dialog


class SIEVMainWindow(QMainWindow):
    """
    Ventana principal completa con sistema modular de protocolos.
    Coordinador entre todos los módulos del sistema SIEV.
    """
    
    def __init__(self, ui_file_path="main_window.ui"):
        super().__init__()
        
        # Variables de estado SIEV
        self.siev_setup = None
        self.siev_camera_index = None
        self.siev_serial_port = None
        self.siev_connected = False
        
        # Módulos del sistema
        self.protocol_manager = None
        self.protocol_executor = None
        self.protocol_widget = None
        
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
        
        # Inicializar sistema modular
        self.init_modular_system()
        
        # Configurar widgets personalizados
        self.setup_custom_widgets()
        
        # Configurar conexiones
        self.setup_connections()
        
        # Cargar iconos
        self.load_icons()
        
        # Detectar SIEV al iniciar
        QTimer.singleShot(2000, self.detect_siev_on_startup)
        
        print("✅ SIEV MainWindow completamente inicializado")
    
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
    
    def init_modular_system(self):
        """Inicializar sistema modular de protocolos"""
        try:
            # Inicializar ProtocolManager
            self.protocol_manager = ProtocolManager()
            self.protocol_manager.load_protocols()
            
            # Inicializar ProtocolExecutor
            self.protocol_executor = ProtocolExecutor()
            
            # Conectar señales del manager
            self.protocol_manager.protocols_loaded.connect(self.on_protocols_loaded)
            self.protocol_manager.validation_error.connect(self.on_validation_error)
            
            # Conectar señales del executor
            self.protocol_executor.execution_started.connect(self.on_execution_started)
            self.protocol_executor.execution_finished.connect(self.on_execution_finished)
            self.protocol_executor.execution_progress.connect(self.on_execution_progress)
            self.protocol_executor.event_triggered.connect(self.on_event_triggered)
            self.protocol_executor.hardware_command_sent.connect(self.on_hardware_command)
            self.protocol_executor.execution_error.connect(self.on_execution_error)
            
            print("✅ Sistema modular de protocolos inicializado")
            
        except Exception as e:
            print(f"❌ Error inicializando sistema modular: {e}")
            show_error("Error de Inicialización", 
                      f"No se pudo inicializar el sistema de protocolos: {e}", self)
    
    def setup_custom_widgets(self):
        """Configurar widgets personalizados"""
        
        # Reemplazar widget de cámara
        self.setup_camera_widget()
        
        # Reemplazar widget de gráfico
        self.setup_graph_widget()
        
        # Configurar widget de protocolos
        self.setup_protocol_widget()
        
        # Agregar controles de gráfico
        self.setup_graph_controls()
    
    def setup_camera_widget(self):
        """Configurar widget de cámara modular"""
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
            self.camera_widget = ModularCameraWidget()
            camera_layout.insertWidget(camera_index, self.camera_widget)
            
            # Configurar executor con widget de cámara
            self.protocol_executor.set_camera_widget(self.camera_widget)
            
            print("✅ Widget de cámara integrado")
    
    def setup_graph_widget(self):
        """Configurar widget de gráfico modular"""
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
            
            # Configurar executor con widget de gráfico
            self.protocol_executor.set_graph_widget(self.vcl_graph_widget)
            
            print("✅ VCLGraphWidget integrado")
    
    def setup_protocol_widget(self):
        """Configurar widget de protocolos modular"""
        # Obtener layout izquierdo
        left_layout = self.ui.layout_left_vertical
        
        # Crear widget de protocolos
        self.protocol_widget = ProtocolTreeWidget()
        
        # Insertar al inicio del layout (antes de cualquier otro widget)
        left_layout.insertWidget(0, self.protocol_widget)
        
        # Conectar señales
        self.protocol_widget.protocol_selected.connect(self.on_protocol_selected)
        self.protocol_widget.protocol_execution_requested.connect(self.on_protocol_execution_requested)
        self.protocol_widget.protocol_changed.connect(self.on_protocol_status_changed)
        
        print("✅ Widget de protocolos integrado")
    
    def setup_graph_controls(self):
        """Agregar controles de gráfico en panel derecho"""
        if not hasattr(self.ui, 'layout_right_vertical'):
            return
        
        self.graph_tools_group = QGroupBox("Herramientas de Gráfico")
        if hasattr(self.ui, 'group_controles_analisis'):
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
        
        if hasattr(self.ui, 'group_controles_analisis'):
            for i in range(right_layout.count()):
                item = right_layout.itemAt(i)
                if item.widget() == self.ui.group_controles_analisis:
                    insert_position = i + 1
                    break
        
        right_layout.insertWidget(insert_position, self.graph_tools_group)
        print("✅ Controles de gráfico agregados")
    
    def setup_connections(self):
        """Configurar conexiones básicas"""
        if not hasattr(self.ui, 'btn_conectar_camara'):
            print("⚠️ No se encontraron algunos botones en el UI")
            return
        
        # Configurar botón principal SIEV
        self.ui.btn_conectar_camara.setText("Buscar SIEV")
        self.ui.btn_conectar_camara.clicked.connect(self.handle_main_button)
        
        # Botón de grabación
        if hasattr(self.ui, 'btn_grabar'):
            self.ui.btn_grabar.clicked.connect(self.toggle_recording)
        
        # Controles de cámara
        if hasattr(self.ui, 'check_crosshair'):
            self.ui.check_crosshair.toggled.connect(self.update_camera_options)
        if hasattr(self.ui, 'check_tracking'):
            self.ui.check_tracking.toggled.connect(self.update_camera_options)
        
        # Señales del gráfico
        if hasattr(self, 'vcl_graph_widget'):
            self.vcl_graph_widget.point_added.connect(self.on_point_added)
            self.vcl_graph_widget.point_removed.connect(self.on_point_removed)
            self.vcl_graph_widget.torok_region_changed.connect(self.on_torok_changed)
        
        print("✅ Conexiones básicas configuradas")
    
    def load_icons(self):
        """Cargar iconos básicos"""
        try:
            # Icono del botón principal
            search_icon = get_icon("search", 16, IconColors.BLUE)
            self.ui.btn_conectar_camara.setIcon(search_icon)
            
            # Icono de grabación
            if hasattr(self.ui, 'btn_grabar'):
                record_icon = get_icon("circle", 16, IconColors.RED)
                self.ui.btn_grabar.setIcon(record_icon)
            
            print("✅ Iconos básicos cargados")
        except Exception as e:
            print(f"⚠️ Error cargando iconos: {e}")
    
    # ===== MÉTODOS DE PROTOCOLOS =====
    
    def on_protocols_loaded(self, count: int):
        """Manejar carga de protocolos"""
        self.ui.statusbar.showMessage(f"✅ {count} protocolos cargados correctamente")
    
    def on_validation_error(self, error_msg: str):
        """Manejar error de validación"""
        show_error("Error de Validación", error_msg, self)
    
    def on_protocol_selected(self, protocol_key: str):
        """Manejar selección de protocolo"""
        protocol = self.protocol_manager.get_protocol(protocol_key)
        if protocol:
            self.ui.statusbar.showMessage(f"Protocolo seleccionado: {protocol['name']}")
    
    def on_protocol_execution_requested(self, protocol_data: dict):
        """Manejar solicitud de ejecución de protocolo"""
        # Verificar estado del sistema
        if self.protocol_executor.is_protocol_executing():
            if ask_confirmation(
                "Protocolo en Ejecución",
                "Ya hay un protocolo ejecutándose. ¿Desea detenerlo y ejecutar el nuevo?",
                self
            ):
                self.protocol_executor.stop_execution()
            else:
                return
        
        # Configurar hardware si es necesario
        if protocol_data.get("hardware_control", {}).get("led_control", False):
            if self.siev_connected and self.siev_serial_port:
                self.protocol_executor.set_hardware_port(self.siev_serial_port)
            else:
                # Preguntar si continuar sin hardware
                if not ask_confirmation(
                    "Hardware No Disponible",
                    f"El protocolo '{protocol_data['name']}' requiere control de LED, "
                    f"pero el hardware SIEV no está conectado.\n\n"
                    f"¿Desea continuar sin control de hardware?",
                    self
                ):
                    return
        
        # Ejecutar protocolo
        success = self.protocol_executor.execute_protocol(protocol_data)
        if not success:
            show_error("Error de Ejecución", 
                      "No se pudo iniciar la ejecución del protocolo", self)
    
    def on_protocol_status_changed(self, message: str):
        """Manejar cambio de estado de protocolos"""
        self.ui.statusbar.showMessage(message)
    
    def on_execution_started(self, protocol_name: str):
        """Manejar inicio de ejecución"""
        self.ui.statusbar.showMessage(f"🚀 Ejecutando: {protocol_name}")
        
        # Mostrar progreso si es protocolo con duración
        status = self.protocol_executor.get_execution_status()
        if status.get("duration_max", 0) > 0:
            self.progress_dialog = DialogUtils.show_execution_progress(
                protocol_name, 
                status["duration_max"], 
                self
            )
            self.progress_dialog.stop_button.clicked.connect(self.stop_protocol_execution)
    
    def on_execution_finished(self, protocol_name: str, success: bool):
        """Manejar finalización de ejecución"""
        if success:
            self.ui.statusbar.showMessage(f"✅ {protocol_name} completado exitosamente")
            show_success("Protocolo Completado", 
                        f"El protocolo '{protocol_name}' se ejecutó correctamente")
        else:
            self.ui.statusbar.showMessage(f"❌ {protocol_name} cancelado o falló")
        
        # Cerrar diálogo de progreso si existe
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.on_execution_finished(success)
    
    def on_execution_progress(self, progress_percent: float, status_message: str):
        """Manejar progreso de ejecución"""
        self.ui.statusbar.showMessage(status_message)
        
        # Actualizar diálogo de progreso si existe
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.update_progress(progress_percent, status_message)
    
    def on_event_triggered(self, event_data: dict):
        """Manejar evento temporal disparado"""
        event_desc = event_data.get("description", "Evento")
        self.ui.statusbar.showMessage(f"⚡ {event_desc}")
        print(f"📅 Evento ejecutado: {event_data}")
    
    def on_hardware_command(self, command: str):
        """Manejar comando de hardware enviado"""
        self.ui.statusbar.showMessage(f"📡 Hardware: {command}")
    
    def on_execution_error(self, error_msg: str):
        """Manejar error de ejecución"""
        show_error("Error de Ejecución", error_msg, self)
    
    def stop_protocol_execution(self):
        """Detener ejecución de protocolo"""
        if self.protocol_executor.is_protocol_executing():
            if ask_confirmation(
                "Detener Protocolo",
                "¿Está seguro de que desea detener la ejecución del protocolo?",
                self
            ):
                self.protocol_executor.stop_execution()
    
    def show_protocol_editor(self, protocol_key: str):
        """Mostrar editor de protocolo"""
        protocol = self.protocol_manager.get_protocol(protocol_key)
        if not protocol:
            show_error("Error", f"No se encontró el protocolo: {protocol_key}", self)
            return
        
        validation_schema = self.protocol_manager.get_validation_schema()
        
        updated_protocol = show_protocol_config_dialog(
            protocol_key,
            protocol,
            validation_schema,
            self
        )
        
        if updated_protocol:
            # Actualizar protocolo
            if self.protocol_manager.update_protocol(protocol_key, updated_protocol):
                self.protocol_manager.save_protocols()
                self.protocol_widget.refresh_protocols()
                show_success("Protocolo Actualizado", 
                           f"El protocolo '{updated_protocol['name']}' se guardó correctamente")
            else:
                show_error("Error", "No se pudo actualizar el protocolo", self)
    
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
            
            # Mostrar información del hardware
            DialogUtils.show_hardware_status(self.siev_setup, self)
            
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
        self.ui.btn_conectar_camara.setText("Conectar Cámara")
        camera_icon = get_icon("camera", 16, IconColors.GREEN)
        self.ui.btn_conectar_camara.setIcon(camera_icon)
    
    def switch_to_siev_mode(self):
        """Cambiar botón a modo SIEV"""
        self.ui.btn_conectar_camara.setText("Buscar SIEV")
        search_icon = get_icon("search", 16, IconColors.BLUE)
        self.ui.btn_conectar_camara.setIcon(search_icon)
    
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
    
    # ===== MÉTODOS DE CÁMARA =====
    
    def toggle_camera(self):
        """Toggle cámara"""
        if not hasattr(self, 'camera_widget') or not self.siev_connected:
            return
        
        if not self.camera_widget.is_connected:
            # Conectar usando índice SIEV
            if self.camera_widget.init_camera(self.siev_camera_index):
                self.camera_widget.start_capture()
                self.ui.btn_conectar_camara.setText("🔌 Desconectar Cámara")
                if hasattr(self.ui, 'btn_grabar'):
                    self.ui.btn_grabar.setEnabled(True)
                if hasattr(self.ui, 'lbl_estado_camara'):
                    self.ui.lbl_estado_camara.setText("Estado: Conectado ✅")
                    self.ui.lbl_estado_camara.setStyleSheet("color: green; font-weight: bold;")
            else:
                if hasattr(self.ui, 'lbl_estado_camara'):
                    self.ui.lbl_estado_camara.setText("Estado: Error ❌")
                    self.ui.lbl_estado_camara.setStyleSheet("color: red; font-weight: bold;")
        else:
            # Desconectar
            self.camera_widget.release_camera()
            self.ui.btn_conectar_camara.setText("Conectar Cámara")
            if hasattr(self.ui, 'btn_grabar'):
                self.ui.btn_grabar.setEnabled(False)
                self.ui.btn_grabar.setText("Grabar")
            if hasattr(self.ui, 'lbl_estado_camara'):
                self.ui.lbl_estado_camara.setText("Estado: Desconectado")
                self.ui.lbl_estado_camara.setStyleSheet("color: gray;")
    
    def toggle_recording(self):
        """Toggle grabación"""
        if not hasattr(self, 'camera_widget'):
            return
        
        if not self.camera_widget.is_recording:
            self.camera_widget.start_recording()
            if hasattr(self.ui, 'btn_grabar'):
                self.ui.btn_grabar.setText("⏹️ Detener")
            self.ui.statusbar.showMessage("🔴 GRABANDO - Evaluación en curso")
        else:
            self.camera_widget.stop_recording()
            if hasattr(self.ui, 'btn_grabar'):
                self.ui.btn_grabar.setText("Grabar")
            self.ui.statusbar.showMessage("Grabación detenida")
    
    def update_camera_options(self):
        """Actualizar opciones de cámara"""
        if hasattr(self, 'camera_widget'):
            if hasattr(self.ui, 'check_crosshair'):
                self.camera_widget.set_overlay_options(
                    crosshair=self.ui.check_crosshair.isChecked()
                )
            if hasattr(self.ui, 'check_tracking'):
                self.camera_widget.set_overlay_options(
                    tracking=self.ui.check_tracking.isChecked()
                )
    
    # ===== MÉTODOS DE GRÁFICO =====
    
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
    
    # ===== MÉTODOS DE MENÚ Y ACCIONES ADICIONALES =====
    
    def show_system_info(self):
        """Mostrar información del sistema"""
        info_text = f"""
<b>SIEV - Sistema Integrado de Evaluación Vestibular</b><br><br>

<b>Estado del Sistema:</b><br>
• Hardware SIEV: {'Conectado' if self.siev_connected else 'No conectado'}<br>
• Protocolos cargados: {len(self.protocol_manager.get_all_protocols()) if self.protocol_manager else 0}<br>
• Cámara: {'Activa' if hasattr(self, 'camera_widget') and self.camera_widget.is_connected else 'Inactiva'}<br>
• Ejecución: {'En curso' if self.protocol_executor.is_protocol_executing() else 'Inactiva'}<br><br>

<b>Módulos del Sistema:</b><br>
• ProtocolTreeWidget: Gestión de protocolos<br>
• ProtocolExecutor: Ejecución con eventos temporales<br>
• ProtocolManager: Validación y persistencia<br>
• ModularCameraWidget: Captura y detección<br>
• VCLGraphWidget: Análisis de señales<br><br>

<b>Características:</b><br>
• ✅ Protocolos vestibulares estándar médicos<br>
• ✅ Control de hardware ESP8266 + LEDs<br>
• ✅ Eventos temporales automáticos<br>
• ✅ Editor avanzado de protocolos<br>
• ✅ Detección automática de ojos y pupilas<br>
• ✅ Análisis de gráficos con herramientas especializadas<br>
"""
        
        DialogUtils.show_info("Información del Sistema", info_text, self)
    
    def export_protocols(self):
        """Exportar protocolos a archivo"""
        if not self.protocol_manager:
            show_error("Error", "Sistema de protocolos no disponible", self)
            return
        
        from PySide6.QtWidgets import QFileDialog
        
        export_path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Protocolos",
            "protocolos_siev_export.json",
            "JSON Files (*.json)"
        )
        
        if export_path:
            if self.protocol_manager.export_protocols(export_path):
                show_success("Exportación Exitosa", 
                           f"Protocolos exportados a:\n{export_path}")
            else:
                show_error("Error de Exportación", 
                          "No se pudieron exportar los protocolos")
    
    def import_protocols(self):
        """Importar protocolos desde archivo"""
        if not self.protocol_manager:
            show_error("Error", "Sistema de protocolos no disponible", self)
            return
        
        from PySide6.QtWidgets import QFileDialog
        
        import_path, _ = QFileDialog.getOpenFileName(
            self,
            "Importar Protocolos",
            "",
            "JSON Files (*.json)"
        )
        
        if import_path:
            success, count = self.protocol_manager.import_protocols(import_path)
            if success:
                self.protocol_manager.save_protocols()
                self.protocol_widget.refresh_protocols()
                show_success("Importación Exitosa", 
                           f"{count} protocolos importados correctamente")
            else:
                show_error("Error de Importación", 
                          "No se pudieron importar los protocolos")
    
    def show_protocol_statistics(self):
        """Mostrar estadísticas de protocolos"""
        if not self.protocol_manager:
            show_error("Error", "Sistema de protocolos no disponible", self)
            return
        
        stats = self.protocol_manager.get_statistics()
        
        categories_text = "<br>".join([
            f"• {cat}: {count}" for cat, count in stats["categories"].items()
        ])
        
        behavior_types_text = "<br>".join([
            f"• {bt}: {count}" for bt, count in stats["behavior_types"].items()
        ])
        
        stats_text = f"""
<b>Estadísticas de Protocolos</b><br><br>

<b>Resumen General:</b><br>
• Total de protocolos: {stats['total_protocols']}<br>
• Protocolos estándar: {stats['default_protocols']}<br>
• Protocolos personalizados: {stats['preset_protocols']}<br><br>

<b>Por Categoría:</b><br>
{categories_text}<br><br>

<b>Por Tipo de Comportamiento:</b><br>
{behavior_types_text}<br><br>

<b>Archivo:</b><br>
• Ruta: {stats['file_path']}<br>
• Estado: {'Cargado' if stats['is_loaded'] else 'No cargado'}<br>
"""
        
        DialogUtils.show_info("Estadísticas de Protocolos", stats_text, self)
    
    def validate_all_protocols(self):
        """Validar todos los protocolos"""
        if not self.protocol_manager:
            show_error("Error", "Sistema de protocolos no disponible", self)
            return
        
        all_protocols = self.protocol_manager.get_all_protocols()
        validation_schema = self.protocol_manager.get_validation_schema()
        
        valid_count = 0
        invalid_protocols = []
        
        for key, protocol in all_protocols.items():
            is_valid, errors = self.protocol_manager.validate_protocol(protocol)
            if is_valid:
                valid_count += 1
            else:
                invalid_protocols.append((key, errors))
        
        if invalid_protocols:
            error_text = f"Se encontraron {len(invalid_protocols)} protocolos inválidos:\n\n"
            for key, errors in invalid_protocols[:5]:  # Mostrar solo los primeros 5
                error_text += f"• {key}:\n"
                for error in errors[:3]:  # Mostrar solo los primeros 3 errores
                    error_text += f"  - {error}\n"
                error_text += "\n"
            
            if len(invalid_protocols) > 5:
                error_text += f"... y {len(invalid_protocols) - 5} más"
            
            show_warning("Protocolos Inválidos", error_text, self)
        else:
            show_success("Validación Exitosa", 
                        f"Todos los {valid_count} protocolos son válidos")
    
    def reset_to_defaults(self):
        """Resetear protocolos a valores por defecto"""
        if ask_confirmation(
            "Resetear Protocolos",
            "¿Está seguro de que desea eliminar TODOS los protocolos "
            "personalizados y resetear a los valores por defecto?\n\n"
            "Esta acción no se puede deshacer.",
            self
        ):
            if self.protocol_manager:
                # Limpiar presets
                self.protocol_manager.protocols_data["presets"] = {}
                
                # Guardar cambios
                if self.protocol_manager.save_protocols():
                    self.protocol_widget.refresh_protocols()
                    show_success("Reset Completado", 
                               "Protocolos restablecidos a valores por defecto")
                else:
                    show_error("Error", "No se pudo resetear los protocolos")
    
    def closeEvent(self, event):
        """Cleanup al cerrar aplicación"""
        print("🧹 Cerrando SIEV...")
        
        # Detener ejecución de protocolos
        if self.protocol_executor and self.protocol_executor.is_protocol_executing():
            if ask_confirmation(
                "Protocolo en Ejecución",
                "Hay un protocolo ejecutándose. ¿Desea detenerlo y cerrar la aplicación?",
                self
            ):
                self.protocol_executor.stop_execution()
            else:
                event.ignore()
                return
        
        # Liberar cámara
        if hasattr(self, 'camera_widget') and self.camera_widget.is_connected:
            self.camera_widget.release_camera()
        
        # Cleanup del executor
        if self.protocol_executor:
            self.protocol_executor.cleanup()
        
        # Guardar protocolos
        if self.protocol_manager:
            self.protocol_manager.save_protocols()
        
        print("✅ SIEV cerrado correctamente")
        event.accept()


def main():
    """Función principal"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    print("🚀 Iniciando SIEV con sistema completo de protocolos...")
    
    try:
        # Crear ventana principal
        window = SIEVMainWindow("main_window.ui")
        
        # Configurar ventana
        window.setWindowTitle("SIEV v2.0 - Sistema Integrado de Evaluación Vestibular")
        
        # Crear menú de aplicación (opcional)
        menubar = window.menuBar()
        
        # Menú Sistema
        system_menu = menubar.addMenu("Sistema")
        
        # Acción: Información del sistema
        info_action = system_menu.addAction("Información del Sistema")
        info_action.setIcon(get_icon("info", 16, IconColors.BLUE))
        info_action.triggered.connect(window.show_system_info)
        
        system_menu.addSeparator()
        
        # Acción: Salir
        exit_action = system_menu.addAction("Salir")
        exit_action.setIcon(get_icon("x", 16, IconColors.RED))
        exit_action.triggered.connect(window.close)
        
        # Menú Protocolos
        protocols_menu = menubar.addMenu("Protocolos")
        
        # Acción: Exportar protocolos
        export_action = protocols_menu.addAction("Exportar Protocolos...")
        export_action.setIcon(get_icon("download", 16, IconColors.GREEN))
        export_action.triggered.connect(window.export_protocols)
        
        # Acción: Importar protocolos
        import_action = protocols_menu.addAction("Importar Protocolos...")
        import_action.setIcon(get_icon("upload", 16, IconColors.BLUE))
        import_action.triggered.connect(window.import_protocols)
        
        protocols_menu.addSeparator()
        
        # Acción: Estadísticas
        stats_action = protocols_menu.addAction("Estadísticas")
        stats_action.setIcon(get_icon("bar-chart", 16, IconColors.ORANGE))
        stats_action.triggered.connect(window.show_protocol_statistics)
        
        # Acción: Validar todos
        validate_action = protocols_menu.addAction("Validar Todos")
        validate_action.setIcon(get_icon("check-circle", 16, IconColors.GREEN))
        validate_action.triggered.connect(window.validate_all_protocols)
        
        protocols_menu.addSeparator()
        
        # Acción: Reset a defaults
        reset_action = protocols_menu.addAction("Resetear a Valores por Defecto")
        reset_action.setIcon(get_icon("rotate-ccw", 16, IconColors.RED))
        reset_action.triggered.connect(window.reset_to_defaults)
        
        # Menú Ayuda
        help_menu = menubar.addMenu("Ayuda")
        
        # Acción: Acerca de
        about_action = help_menu.addAction("Acerca de SIEV")
        about_action.setIcon(get_icon("help-circle", 16, IconColors.BLUE))
        about_action.triggered.connect(lambda: DialogUtils.show_info(
            "Acerca de SIEV v2.0",
            "Sistema Integrado de Evaluación Vestibular\n\n"
            "• Protocolos vestibulares estándar médicos\n"
            "• Control de hardware ESP8266 + LEDs\n"
            "• Eventos temporales automáticos\n"
            "• Editor avanzado de protocolos\n"
            "• Detección de ojos y pupilas\n"
            "• Análisis de gráficos especializado\n\n"
            "Desarrollado con arquitectura modular\n"
            "© 2025 Proyecto SIEV",
            window
        ))
        
        # Mostrar ventana
        window.show()
        
        print("✅ SIEV v2.0 iniciado correctamente")
        print("📋 Características disponibles:")
        print("   • Sistema modular de protocolos")
        print("   • Ejecutor con eventos temporales")
        print("   • Editor avanzado de configuración")
        print("   • Control de hardware ESP8266")
        print("   • Detección automática SIEV")
        print("   • Análisis de gráficos VCL")
        
        return app.exec()
        
    except Exception as e:
        print(f"❌ Error iniciando SIEV: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())