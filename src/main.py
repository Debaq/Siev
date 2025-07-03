#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIEV - Sistema Integrado de Evaluación Vestibular v2.0
Main Window con sistema de documentos .siev y flujo de trabajo modular
Hardware: VideoSIEV, AxisSIEV, PosturoSIEV
"""

import sys
import os
from typing import Optional, Dict, Any
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                              QHBoxLayout, QSplitter, QFrame, QFileDialog,
                              QMessageBox)
from PySide6.QtCore import QTimer, Qt, QSize
from PySide6.QtGui import QIcon
from PySide6.QtUiTools import QUiLoader

# Imports de widgets y módulos
from widgets.welcome_widget import WelcomeWidget
from widgets.protocol_tree_widget import ProtocolTreeWidget
from widgets.document_tests_widget import DocumentTestsWidget
from utils.document_manager import DocumentManager, create_document_with_patient_dialog, open_document_dialog
from dialogs.patient_data_dialog import show_patient_data_dialog
from utils.protocol_executor import ProtocolExecutor
from utils.icon_utils import get_icon, IconColors, preload_icons
from utils.dialog_utils import (show_info, show_success, show_warning, show_error, 
                               ask_confirmation, DialogUtils)

# Widgets dinámicos (se importan según necesidad)
from utils.vcl_graph import VCLGraphWidget
from camera.camera_widget import ModularCameraWidget


class SIEVMainWindow(QMainWindow):
    """
    Ventana principal de SIEV con sistema completo de documentos.
    Maneja creación/apertura de documentos .siev y ejecución de protocolos.
    Hardware: VideoSIEV, AxisSIEV, PosturoSIEV
    """
    
    def __init__(self, ui_file_path="ui/main_window.ui"):
        super().__init__()
        
        # Estado del sistema
        self.document_manager = None
        self.protocol_executor = None
        self.current_hardware_type = None  # 'videosiev', 'axissiev', 'posturosiev'
        
        # Widgets dinámicos
        self.welcome_widget = None
        self.protocol_tree_widget = None
        self.document_tests_widget = None
        self.central_widgets = {}  # Cache de widgets centrales
        
        # Referencias a contenedores del UI
        self.ui = None
        self.left_panel = None
        self.central_panel = None
        self.right_panel = None
        
        # Cargar UI
        if not self.load_ui(ui_file_path):
            # Si falla cargar UI, crear layout básico
            self.create_fallback_ui()
        
        # Configurar ventana
        self.setup_window()
        
        # Inicializar sistema
        self.init_system()
        
        # Configurar menús
        self.setup_menus()
        
        # Estado inicial: mostrar bienvenida
        self.show_welcome_state()
        
    def create_fallback_ui(self):
        """Crear UI básico si falla cargar el archivo .ui"""
        print("⚠️ Creando UI de respaldo...")
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal horizontal
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Panel izquierdo
        self.left_panel = QFrame()
        self.left_panel.setMaximumWidth(250)
        self.left_panel.setFrameStyle(QFrame.StyledPanel)
        main_layout.addWidget(self.left_panel)
        
        # Panel central
        self.central_panel = QFrame()
        self.central_panel.setFrameStyle(QFrame.StyledPanel)
        main_layout.addWidget(self.central_panel)
        
        # Panel derecho
        self.right_panel = QFrame()
        self.right_panel.setMaximumWidth(220)
        self.right_panel.setFrameStyle(QFrame.StyledPanel)
        main_layout.addWidget(self.right_panel)
        
        # Crear layouts para cada panel
        QVBoxLayout(self.left_panel)
        QVBoxLayout(self.central_panel) 
        QVBoxLayout(self.right_panel)
        
        # Crear barra de estado
        self.statusBar().showMessage("UI de respaldo cargado")
        
        print("✅ UI de respaldo creado")
    
    
    def load_ui(self, ui_file_path: str) -> bool:
        """Cargar archivo .ui con contenedores vacíos"""
        try:
            # Buscar archivo UI
            possible_paths = [
                ui_file_path,
                os.path.join("src", ui_file_path),
                os.path.join("src", "ui", "main_window.ui"),  # Agregar esta ruta
                os.path.join("ui", "main_window.ui"),
                "main_window.ui"
            ]
            
            ui_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    ui_path = path
                    break
            
            if not ui_path:
                print("❌ No se encontró archivo main_window.ui")
                return False
            
            # Cargar UI
            loader = QUiLoader()
            self.ui = loader.load(ui_path)  # Cambiar esta línea

            
            # Configurar como widget central
            self.setCentralWidget(self.ui.centralwidget)
            self.setMenuBar(self.ui.menubar)
            self.setStatusBar(self.ui.statusbar)
            
            # Obtener referencias a contenedores
            self.left_panel = self.ui.findChild(QWidget, "frame_left_panel")
            self.central_panel = self.ui.findChild(QWidget, "frame_central_panel") 
            self.right_panel = self.ui.findChild(QWidget, "frame_right_panel")
            
            if not all([self.left_panel, self.central_panel, self.right_panel]):
                print("❌ No se encontraron todos los contenedores en el UI")
                return False
            
            print(f"✅ UI cargado desde: {ui_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error cargando UI: {e}")
            return False
    
    def setup_window(self):
        """Configurar propiedades de la ventana"""
        self.setWindowTitle("SIEV v2.0 - Sistema Integrado de Evaluación Vestibular")
        self.setMinimumSize(1200, 800)
        
        # Icono de la aplicación
        try:
            app_icon = get_icon("eye", 32, IconColors.BLUE)
            self.setWindowIcon(app_icon)
        except:
            pass
        
        # Centrar ventana
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(
            (screen.width() - 1200) // 2,
            (screen.height() - 800) // 2,
            1200, 800
        )
    
    def init_system(self):
        """Inicializar sistema modular"""
        try:
            # Pre-cargar iconos
            preload_icons()
            
            # Inicializar ProtocolExecutor
            self.protocol_executor = ProtocolExecutor()
            
            # Conectar señales del executor
            self.protocol_executor.execution_started.connect(self.on_execution_started)
            self.protocol_executor.execution_finished.connect(self.on_execution_finished)
            self.protocol_executor.execution_progress.connect(self.on_execution_progress)
            self.protocol_executor.event_triggered.connect(self.on_event_triggered)
            self.protocol_executor.hardware_command_sent.connect(self.on_hardware_command)
            self.protocol_executor.execution_error.connect(self.on_execution_error)
            
            print("✅ Sistema modular inicializado")
            
        except Exception as e:
            print(f"❌ Error inicializando sistema: {e}")
            show_error("Error de Inicialización", 
                      f"No se pudo inicializar el sistema: {e}", self)
    
    def setup_menus(self):
        """Configurar menús de la aplicación"""
        menubar = self.menuBar()
        
        # === MENÚ ARCHIVO ===
        file_menu = menubar.addMenu("Archivo")
        
        # Nuevo documento
        new_action = file_menu.addAction("Nuevo Documento...")
        new_action.setIcon(get_icon("file-plus", 16, IconColors.GREEN))
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.create_new_document)
        
        # Abrir documento
        open_action = file_menu.addAction("Abrir Documento...")
        open_action.setIcon(get_icon("folder-open", 16, IconColors.BLUE))
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_document)
        
        file_menu.addSeparator()
        
        # Guardar documento
        self.save_action = file_menu.addAction("Guardar")
        self.save_action.setIcon(get_icon("save", 16, IconColors.GREEN))
        self.save_action.setShortcut("Ctrl+S")
        self.save_action.triggered.connect(self.save_document)
        self.save_action.setEnabled(False)
        
        # Guardar como
        self.save_as_action = file_menu.addAction("Guardar Como...")
        self.save_as_action.setIcon(get_icon("save", 16, IconColors.BLUE))
        self.save_as_action.setShortcut("Ctrl+Shift+S")
        self.save_as_action.triggered.connect(self.save_document_as)
        self.save_as_action.setEnabled(False)
        
        file_menu.addSeparator()
        
        # Cerrar documento
        self.close_doc_action = file_menu.addAction("Cerrar Documento")
        self.close_doc_action.setIcon(get_icon("x", 16, IconColors.ORANGE))
        self.close_doc_action.triggered.connect(self.close_document)
        self.close_doc_action.setEnabled(False)
        
        file_menu.addSeparator()
        
        # Salir
        exit_action = file_menu.addAction("Salir")
        exit_action.setIcon(get_icon("x", 16, IconColors.RED))
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        
        # === MENÚ PACIENTE ===
        patient_menu = menubar.addMenu("Paciente")
        
        # Editar datos del paciente
        self.edit_patient_action = patient_menu.addAction("Editar Datos del Paciente...")
        self.edit_patient_action.setIcon(get_icon("user", 16, IconColors.BLUE))
        self.edit_patient_action.triggered.connect(self.edit_patient_data)
        self.edit_patient_action.setEnabled(False)
        
        # === MENÚ HERRAMIENTAS ===
        tools_menu = menubar.addMenu("Herramientas")
        
        # Configuración
        config_action = tools_menu.addAction("Configuración...")
        config_action.setIcon(get_icon("settings", 16, IconColors.GRAY))
        config_action.triggered.connect(self.show_configuration)
        
        # === MENÚ AYUDA ===
        help_menu = menubar.addMenu("Ayuda")
        
        # Acerca de
        about_action = help_menu.addAction("Acerca de SIEV")
        about_action.setIcon(get_icon("circle-question-mark", 16, IconColors.BLUE))
        about_action.triggered.connect(self.show_about)
    
    # === GESTIÓN DE DOCUMENTOS ===
    
    def show_welcome_state(self):
        """Mostrar estado de bienvenida (sin documento)"""
        # Limpiar paneles
        self.clear_all_panels()
        
        # Mostrar widget de bienvenida en el centro
        if not self.welcome_widget:
            self.welcome_widget = WelcomeWidget()
            self.welcome_widget.create_document_requested.connect(self.create_new_document)
            self.welcome_widget.open_document_requested.connect(self.open_document)
        
        self.set_central_widget(self.welcome_widget)
        
        # Configurar panel izquierdo solo con protocolos
        self.setup_left_panel_protocols_only()
        
        # Actualizar estado de menús
        self.update_menus_state(False)
        
        # Actualizar barra de estado
        self.statusBar().showMessage("Sin documento abierto - Use Archivo > Nuevo/Abrir para comenzar")
    
    def show_document_state(self):
        """Mostrar estado con documento abierto"""
        if not self.document_manager:
            return
        
        # Configurar panel izquierdo con ambos trees
        self.setup_left_panel_with_document()
        
        # Por defecto, mostrar widget neutral en el centro
        self.show_neutral_central_state()
        
        # Actualizar estado de menús
        self.update_menus_state(True)
        
        # Actualizar información del paciente
        self.update_patient_info()
    
    def create_new_document(self):
        """Crear nuevo documento"""
        print("📄 Creando nuevo documento...")
        
        # Si hay documento abierto con cambios, preguntar
        if self.document_manager and self.document_manager.is_modified:
            if not self.confirm_close_document():
                return
        
        # Crear documento con diálogo de paciente
        doc_manager, success = create_document_with_patient_dialog(self)
        
        if success and doc_manager:
            # Cerrar documento anterior si existe
            if self.document_manager:
                self.close_document()
            
            # Establecer nuevo documento
            self.document_manager = doc_manager
            self.connect_document_signals()
            
            # Cambiar a estado con documento
            self.show_document_state()
            
            patient_name = doc_manager.get_patient_data().get("name", "Sin nombre")
            show_success("Documento Creado", 
                        f"Documento creado para: {patient_name}")
            
            print(f"✅ Documento creado para: {patient_name}")
    
    def open_document(self):
        """Abrir documento existente"""
        print("📂 Abriendo documento...")
        
        # Si hay documento abierto con cambios, preguntar
        if self.document_manager and self.document_manager.is_modified:
            if not self.confirm_close_document():
                return
        
        # Abrir documento con diálogo
        doc_manager, success = open_document_dialog(self)
        
        if success and doc_manager:
            # Cerrar documento anterior si existe
            if self.document_manager:
                self.close_document()
            
            # Establecer documento abierto
            self.document_manager = doc_manager
            self.connect_document_signals()
            
            # Cambiar a estado con documento
            self.show_document_state()
            
            patient_name = doc_manager.get_patient_data().get("name", "Sin nombre")
            show_success("Documento Abierto", 
                        f"Documento abierto: {patient_name}")
            
            print(f"✅ Documento abierto: {patient_name}")
    
    def save_document(self):
        """Guardar documento actual"""
        if not self.document_manager:
            return
        
        success = self.document_manager.save_document()
        if success:
            show_success("Documento Guardado", "El documento se guardó correctamente")
        else:
            show_error("Error", "No se pudo guardar el documento")
    
    def save_document_as(self):
        """Guardar documento con nuevo nombre"""
        if not self.document_manager:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Documento Como",
            "",
            "Documentos VideoSIEV (*.siev);;Todos los archivos (*)"
        )
        
        if file_path:
            if not file_path.endswith('.siev'):
                file_path += '.siev'
            
            success = self.document_manager.save_document(file_path)
            if success:
                show_success("Documento Guardado", f"Documento guardado como: {file_path}")
            else:
                show_error("Error", "No se pudo guardar el documento")
    
    def close_document(self):
        """Cerrar documento actual"""
        if not self.document_manager:
            return
        
        # Verificar cambios sin guardar
        if not self.confirm_close_document():
            return
        
        # Cerrar documento
        self.document_manager.close_document()
        self.document_manager = None
        
        # Volver a estado de bienvenida
        self.show_welcome_state()
        
        print("📄 Documento cerrado")
    
    def confirm_close_document(self) -> bool:
        """Confirmar cierre de documento con cambios"""
        if not self.document_manager or not self.document_manager.is_modified:
            return True
        
        return ask_confirmation(
            "Cambios Sin Guardar",
            "El documento tiene cambios sin guardar.\n\n"
            "¿Desea guardar antes de cerrar?",
            self
        )
    
    def connect_document_signals(self):
        """Conectar señales del DocumentManager"""
        if self.document_manager:
            self.document_manager.document_saved.connect(self.on_document_saved)
            self.document_manager.test_added.connect(self.on_test_added)
            self.document_manager.test_removed.connect(self.on_test_removed)
            self.document_manager.error_occurred.connect(self.on_document_error)
    
    # === CONFIGURACIÓN DE PANELES ===
    
    def clear_all_panels(self):
        """Limpiar todos los paneles"""
        self.clear_panel(self.left_panel)
        self.clear_panel(self.central_panel)
        self.clear_panel(self.right_panel)
    
    def clear_panel(self, panel: QWidget):
        """Limpiar contenido de un panel"""
        if panel and panel.layout():
            while panel.layout().count():
                child = panel.layout().takeAt(0)
                if child.widget():
                    child.widget().setParent(None)
    
    def set_central_widget(self, widget: QWidget):
        """Establecer widget en panel central"""
        self.clear_panel(self.central_panel)
        
        if self.central_panel.layout():
            self.central_panel.layout().addWidget(widget)
        else:
            layout = QVBoxLayout(self.central_panel)
            layout.addWidget(widget)
    
    def setup_left_panel_protocols_only(self):
        """Configurar panel izquierdo solo con protocolos"""
        self.clear_panel(self.left_panel)
        
        # Crear ProtocolTreeWidget
        if not self.protocol_tree_widget:
            self.protocol_tree_widget = ProtocolTreeWidget()
            self.protocol_tree_widget.protocol_execution_requested.connect(self.execute_protocol)
            self.protocol_tree_widget.protocol_selected.connect(self.on_protocol_selected)
        
        # Agregar al panel
        if self.left_panel.layout():
            self.left_panel.layout().addWidget(self.protocol_tree_widget)
        else:
            layout = QVBoxLayout(self.left_panel)
            layout.addWidget(self.protocol_tree_widget)
    
    def setup_left_panel_with_document(self):
        """Configurar panel izquierdo con protocolos + pruebas del documento"""
        self.clear_panel(self.left_panel)
        
        # Crear layout vertical
        layout = QVBoxLayout(self.left_panel)
        layout.setSpacing(10)
        
        # ProtocolTreeWidget (superior)
        if not self.protocol_tree_widget:
            self.protocol_tree_widget = ProtocolTreeWidget()
            self.protocol_tree_widget.protocol_execution_requested.connect(self.execute_protocol)
            self.protocol_tree_widget.protocol_selected.connect(self.on_protocol_selected)
        
        layout.addWidget(self.protocol_tree_widget)
        
        # DocumentTestsWidget (inferior)
        if not self.document_tests_widget:
            self.document_tests_widget = DocumentTestsWidget()
            self.document_tests_widget.test_view_requested.connect(self.view_test_results)
            self.document_tests_widget.test_delete_requested.connect(self.delete_test)
            self.document_tests_widget.test_export_requested.connect(self.export_test)
        
        # Conectar con DocumentManager
        self.document_tests_widget.set_document_manager(self.document_manager)
        
        layout.addWidget(self.document_tests_widget)
    
    def show_neutral_central_state(self):
        """Mostrar estado neutral en el centro (documento abierto, sin protocolo)"""
        from widgets.welcome_widget import NoDocumentWidget
        
        neutral_widget = NoDocumentWidget()
        # Personalizar para estado con documento
        neutral_widget.findChild(QLabel).setText("Seleccione un protocolo para comenzar")
        
        self.set_central_widget(neutral_widget)
    
    # === EJECUCIÓN DE PROTOCOLOS ===
    
    def execute_protocol(self, protocol_data: Dict[str, Any]):
        """Ejecutar protocolo seleccionado"""
        protocol_name = protocol_data.get("name", "Protocolo")
        behavior_type = protocol_data.get("behavior_type", "recording")
        
        print(f"🚀 Ejecutando protocolo: {protocol_name} ({behavior_type})")
        
        # Detectar hardware necesario según protocolo
        hardware_needed = self.determine_hardware_needed(protocol_data)
        
        # Configurar widgets centrales según el protocolo
        self.setup_central_widgets_for_protocol(protocol_data)
        
        # Configurar ProtocolExecutor
        self.configure_protocol_executor(protocol_data, hardware_needed)
        
        # Ejecutar protocolo
        success = self.protocol_executor.execute_protocol(protocol_data)
        
        if not success:
            show_error("Error de Ejecución", 
                      "No se pudo iniciar la ejecución del protocolo")
    
    def determine_hardware_needed(self, protocol_data: Dict[str, Any]) -> str:
        """Determinar qué hardware se necesita según el protocolo"""
        behavior_type = protocol_data.get("behavior_type", "recording")
        category = protocol_data.get("category", "")
        
        if behavior_type in ["recording", "window", "caloric"]:
            return "videosiev"  # Requiere cámara
        elif category == "equilibrio":
            return "axissiev"  # Requiere sensores de movimiento
        elif "postura" in protocol_data.get("name", "").lower():
            return "posturosiev"  # Requiere plataforma de presión
        else:
            return "videosiev"  # Por defecto
    
    def setup_central_widgets_for_protocol(self, protocol_data: Dict[str, Any]):
        """Configurar widgets centrales según el protocolo"""
        hardware_type = self.determine_hardware_needed(protocol_data)
        
        if hardware_type == "videosiev":
            self.setup_videosiev_widgets(protocol_data)
        elif hardware_type == "axissiev":
            self.setup_axissiev_widgets(protocol_data)
        elif hardware_type == "posturosiev":
            self.setup_posturosiev_widgets(protocol_data)
    
    def setup_videosiev_widgets(self, protocol_data: Dict[str, Any]):
        """Configurar widgets para VideoSIEV (cámara + gráficos)"""
        print("📹 Configurando widgets VideoSIEV")
        
        # Crear splitter vertical para cámara + gráficos
        splitter = QSplitter(Qt.Vertical)
        
        # Widget de cámara
        camera_widget = ModularCameraWidget()
        splitter.addWidget(camera_widget)
        
        # Widget de gráficos
        graph_widget = VCLGraphWidget()
        splitter.addWidget(graph_widget)
        
        # Configurar proporciones
        splitter.setSizes([400, 200])
        
        # Establecer en el centro
        self.set_central_widget(splitter)
        
        # Configurar executor con widgets
        self.protocol_executor.set_camera_widget(camera_widget)
        self.protocol_executor.set_graph_widget(graph_widget)
        
        # Configurar panel derecho con controles de cámara
        self.setup_videosiev_right_panel()
        
        # Detectar e inicializar hardware VideoSIEV cuando sea necesario
        QTimer.singleShot(500, lambda: self.detect_and_init_videosiev(camera_widget))
    
    def setup_axissiev_widgets(self, protocol_data: Dict[str, Any]):
        """Configurar widgets para AxisSIEV (sensores de movimiento)"""
        print("📊 Configurando widgets AxisSIEV")
        
        # TODO: Implementar widgets específicos para AxisSIEV
        # Por ahora, mostrar placeholder
        placeholder = QWidget()
        layout = QVBoxLayout(placeholder)
        
        from PySide6.QtWidgets import QLabel
        label = QLabel("Widget AxisSIEV - En desarrollo")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        
        self.set_central_widget(placeholder)
    
    def setup_posturosiev_widgets(self, protocol_data: Dict[str, Any]):
        """Configurar widgets para PosturoSIEV"""
        print("⚖️ Configurando widgets PosturoSIEV")
        
        # TODO: Implementar widgets específicos para PosturoSIEV
        # Por ahora, mostrar placeholder
        placeholder = QWidget()
        layout = QVBoxLayout(placeholder)
        
        from PySide6.QtWidgets import QLabel
        label = QLabel("Widget PosturoSIEV - En desarrollo")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        
        self.set_central_widget(placeholder)
    
    def setup_videosiev_right_panel(self):
        """Configurar panel derecho para controles VideoSIEV"""
        self.clear_panel(self.right_panel)
        
        # TODO: Implementar controles específicos de VideoSIEV
        # Controles de cámara, herramientas de gráfico, etc.
        
        layout = QVBoxLayout(self.right_panel)
        
        from PySide6.QtWidgets import QLabel
        label = QLabel("Controles VideoSIEV")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
    
    def configure_protocol_executor(self, protocol_data: Dict[str, Any], hardware_type: str):
        """Configurar ProtocolExecutor según protocolo y hardware"""
        # Configurar control de hardware si es necesario
        hardware_control = protocol_data.get("hardware_control", {})
        if hardware_control.get("led_control", False):
            # TODO: Configurar puerto serie cuando se detecte hardware
            pass
    
    def detect_and_init_videosiev(self, camera_widget):
        """Detectar e inicializar hardware VideoSIEV"""
        print("🔍 Detectando hardware VideoSIEV...")
        
        # TODO: Implementar detección de VideoSIEV
        # Por ahora, intentar inicializar cámara con índice por defecto
        try:
            success = camera_widget.init_camera(0)  # Índice 0 por defecto
            if success:
                camera_widget.start_capture()
                self.statusBar().showMessage("VideoSIEV: Cámara conectada")
            else:
                self.statusBar().showMessage("VideoSIEV: Cámara no disponible")
        except Exception as e:
            print(f"⚠️ Error inicializando cámara: {e}")
            self.statusBar().showMessage("VideoSIEV: Error de hardware")
    
    # === MANEJADORES DE EVENTOS ===
    
    def on_protocol_selected(self, protocol_key: str):
        """Manejar selección de protocolo"""
        self.statusBar().showMessage(f"Protocolo seleccionado: {protocol_key}")
    
    def on_execution_started(self, protocol_name: str):
        """Manejar inicio de ejecución"""
        self.statusBar().showMessage(f"🚀 Ejecutando: {protocol_name}")
    
    def on_execution_finished(self, protocol_name: str, success: bool):
        """Manejar finalización de ejecución"""
        if success:
            self.statusBar().showMessage(f"✅ {protocol_name} completado")
            
            # Si hay documento abierto, agregar la prueba
            if self.document_manager:
                # TODO: Obtener datos de la prueba del executor
                test_data = {
                    "timestamp": "2025-07-03T12:00:00",
                    "duration": 120,
                    "results": {}
                }
                
                test_id = self.document_manager.add_test_data(protocol_name, test_data)
                if test_id:
                    show_success("Prueba Guardada", 
                               f"La prueba '{protocol_name}' se guardó en el documento")
        else:
            self.statusBar().showMessage(f"❌ {protocol_name} cancelado")
    
    def on_execution_progress(self, progress: float, message: str):
        """Manejar progreso de ejecución"""
        self.statusBar().showMessage(message)
    
    def on_event_triggered(self, event_data: Dict[str, Any]):
        """Manejar evento temporal"""
        event_desc = event_data.get("description", "Evento")
        self.statusBar().showMessage(f"⚡ {event_desc}")
    
    def on_hardware_command(self, command: str):
        """Manejar comando de hardware"""
        self.statusBar().showMessage(f"📡 {command}")
    
    def on_execution_error(self, error_msg: str):
        """Manejar error de ejecución"""
        show_error("Error de Ejecución", error_msg)
    
    def on_document_saved(self, file_path: str):
        """Manejar documento guardado"""
        self.statusBar().showMessage(f"💾 Documento guardado: {os.path.basename(file_path)}")
    
    def on_test_added(self, test_data: Dict[str, Any]):
        """Manejar prueba agregada"""
        protocol_name = test_data.get("protocol_name", "Prueba")
        self.statusBar().showMessage(f"📝 Prueba agregada: {protocol_name}")
    
    def on_test_removed(self, test_id: str):
        """Manejar prueba eliminada"""
        self.statusBar().showMessage(f"🗑️ Prueba eliminada: {test_id}")
    
    def on_document_error(self, error_msg: str):
        """Manejar error de documento"""
        show_error("Error de Documento", error_msg)
    
    # === GESTIÓN DE PRUEBAS ===
    
    def view_test_results(self, test_id: str, test_data: Dict[str, Any]):
        """Ver resultados de una prueba"""
        protocol_name = test_data.get("protocol_name", "Prueba")
        
        # TODO: Implementar visor de resultados
        show_info("Ver Resultados", 
                 f"Visualizando resultados de: {protocol_name}\n\n"
                 f"ID: {test_id}\n"
                 f"Fecha: {test_data.get('timestamp', 'N/A')}")
    
    def delete_test(self, test_id: str):
        """Eliminar prueba del documento"""
        if self.document_manager:
            success = self.document_manager.remove_test(test_id)
            if success:
                self.statusBar().showMessage(f"Prueba {test_id} eliminada")
            else:
                show_error("Error", "No se pudo eliminar la prueba")
    
    def export_test(self, test_id: str, test_data: Dict[str, Any]):
        """Exportar datos de una prueba"""
        protocol_name = test_data.get("protocol_name", "Prueba")
        
        # TODO: Implementar exportación
        show_info("Exportar Prueba", 
                 f"Exportando: {protocol_name}\n\n"
                 f"Funcionalidad en desarrollo")
    
    # === GESTIÓN DE PACIENTE ===
    
    def update_patient_info(self):
        """Actualizar información del paciente en la UI"""
        if not self.document_manager:
            return
        
        patient_data = self.document_manager.get_patient_data()
        if patient_data:
            patient_name = patient_data.get("name", "Sin nombre")
            patient_id = patient_data.get("patient_id", "Sin ID")
            doctor = patient_data.get("doctor", "Sin médico")
            
            info_text = f"👤 Paciente: {patient_name}\n📋 ID: {patient_id}\n👨‍⚕️ Médico: {doctor}"
            self.statusBar().showMessage(f"Documento: {patient_name}")
    
    def edit_patient_data(self):
        """Editar datos del paciente"""
        if not self.document_manager:
            return
        
        current_data = self.document_manager.get_patient_data()
        if not current_data:
            return
        
        # Mostrar diálogo de edición
        new_data = show_patient_data_dialog(
            parent=self, 
            edit_mode=True, 
            existing_data=current_data
        )
        
        if new_data:
            success = self.document_manager.update_patient_data(new_data)
            if success:
                self.update_patient_info()
                show_success("Datos Actualizados", 
                           "Los datos del paciente se actualizaron correctamente")
            else:
                show_error("Error", "No se pudieron actualizar los datos del paciente")
    
    # === MÉTODOS DE UTILIDAD ===
    
    def update_menus_state(self, has_document: bool):
        """Actualizar estado de menús según si hay documento"""
        self.save_action.setEnabled(has_document)
        self.save_as_action.setEnabled(has_document)
        self.close_doc_action.setEnabled(has_document)
        self.edit_patient_action.setEnabled(has_document)
    
    def show_configuration(self):
        """Mostrar configuración del sistema"""
        show_info("Configuración", 
                 "Configuración del sistema SIEV\n\n"
                 "Funcionalidad en desarrollo")
    
    def show_about(self):
        """Mostrar información sobre SIEV"""
        about_text = """
<b>SIEV v2.0</b><br>
Sistema Integrado de Evaluación Vestibular<br><br>

<b>Características:</b><br>
• Sistema de documentos .siev<br>
• Protocolos vestibulares estándar<br>
• Hardware modular (VideoSIEV, AxisSIEV, PosturoSIEV)<br>
• Análisis en tiempo real<br>
• Generación de informes<br><br>

<b>Hardware Soportado:</b><br>
• VideoSIEV: Cámara + ESP8266 + LEDs<br>
• AxisSIEV: Sensores de movimiento IMU<br>
• PosturoSIEV: Plataforma de presión<br><br>

© 2025 Proyecto SIEV
"""
        
        DialogUtils.show_info("Acerca de SIEV", about_text, self)
    
    # === EVENTOS DE VENTANA ===
    
    def closeEvent(self, event):
        """Manejar cierre de la aplicación"""
        print("🧹 Cerrando SIEV...")
        
        # Detener ejecución si está activa
        if self.protocol_executor and self.protocol_executor.is_protocol_executing():
            if ask_confirmation(
                "Protocolo en Ejecución",
                "Hay un protocolo ejecutándose. ¿Desea detenerlo y cerrar?",
                self
            ):
                self.protocol_executor.stop_execution()
            else:
                event.ignore()
                return
        
        # Verificar documento sin guardar
        if self.document_manager and self.document_manager.is_modified:
            if not self.confirm_close_document():
                event.ignore()
                return
        
        # Cleanup
        self.cleanup_on_exit()
        
        print("✅ SIEV cerrado correctamente")
        event.accept()
    
    def cleanup_on_exit(self):
        """Limpieza al cerrar"""
        # Cerrar documento
        if self.document_manager:
            self.document_manager.close_document()
        
        # Cleanup del executor
        if self.protocol_executor:
            self.protocol_executor.cleanup()
        
        # Limpiar widgets de cámara
        if hasattr(self, 'central_widgets'):
            for widget in self.central_widgets.values():
                if hasattr(widget, 'release_camera'):
                    widget.release_camera()


def main():
    """Función principal de SIEV"""
    # IMPORTANTE: Configurar atributos Qt ANTES de crear QApplication
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    print("🚀 Iniciando SIEV v2.0...")
    
    try:
        # Crear ventana principal
        window = SIEVMainWindow()
        
        # Mostrar ventana
        window.show()
        
        print("✅ SIEV v2.0 iniciado correctamente")
        print("📋 Sistema de documentos .siev activo")
        print("🔧 Hardware modular: VideoSIEV, AxisSIEV, PosturoSIEV")
        print("📊 Protocolos vestibulares integrados")
        
        return app.exec()
        
    except Exception as e:
        print(f"❌ Error iniciando SIEV: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())