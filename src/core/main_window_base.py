#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main Window Base - Ventana principal base con carga UI y configuración básica
Maneja la inicialización fundamental del sistema SIEV
"""

import os
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                              QGroupBox, QPushButton)
from PySide6.QtCore import QTimer, QFile
from PySide6.QtUiTools import QUiLoader

# Imports de widgets personalizados
from utils.vcl_graph import VCLGraphWidget
from camera.camera_widget import ModularCameraWidget
from widgets.protocol_tree_widget import ProtocolTreeWidget

# Imports de módulos de protocolos
from utils.protocol_executor import ProtocolExecutor
from utils.protocol_manager import ProtocolManager
from utils.icon_utils import get_icon, IconColors
from utils.dialog_utils import show_error


class MainWindowBase(QMainWindow):
    """
    Ventana principal base con funcionalidad de carga UI y configuración básica.
    Maneja la inicialización fundamental sin lógica de negocio específica.
    """
    
    def __init__(self, ui_file_path="main_window.ui"):
        super().__init__()
        
        # Variables de estado básicas
        self.ui = None
        self.is_initialized = False
        
        # Módulos del sistema
        self.protocol_manager = None
        self.protocol_executor = None
        self.protocol_widget = None
        self.camera_widget = None
        self.vcl_graph_widget = None
        self.graph_tools_group = None
        
        # Botones de herramientas de gráfico
        self.btn_torok = None
        self.btn_peak_edit = None
        self.btn_tiempo_fijacion = None
        self.btn_zoom = None
        self.btn_crosshair_graph = None
        self.btn_peak_detection = None
        
        # Cargar UI
        if not self.load_ui(ui_file_path):
            raise Exception(f"No se pudo cargar el archivo UI: {ui_file_path}")
        
        # Configurar ventana principal
        self.setup_main_window()
        
        # Inicializar sistema modular
        self.init_modular_system()
        
        # Configurar widgets personalizados
        self.setup_custom_widgets()
        
        # Configurar conexiones básicas
        self.setup_basic_connections()
        
        # Cargar iconos
        self.load_basic_icons()
        
        self.is_initialized = True
        print("✅ MainWindowBase inicializado correctamente")
    
    def load_ui(self, ui_file_path: str) -> bool:
        """Cargar archivo .ui con búsqueda en múltiples rutas"""
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
                    return False
            
            ui_file = QFile(ui_file_path)
            if not ui_file.open(QFile.ReadOnly):
                print(f"❌ No se puede abrir el archivo: {ui_file_path}")
                return False
            
            loader = QUiLoader()
            self.ui = loader.load(ui_file)
            ui_file.close()
            
            print(f"✅ UI cargado desde: {ui_file_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error cargando UI: {e}")
            return False
    
    def setup_main_window(self):
        """Configurar ventana principal con el UI cargado"""
        if not self.ui:
            return
        
        # Configurar ventana principal
        self.setCentralWidget(self.ui.centralwidget)
        self.setMenuBar(self.ui.menubar)
        self.setStatusBar(self.ui.statusbar)
        self.setWindowTitle(self.ui.windowTitle())
        self.setGeometry(self.ui.geometry())
        
        print("✅ Ventana principal configurada")
    
    def init_modular_system(self):
        """Inicializar sistema modular de protocolos"""
        try:
            # Inicializar ProtocolManager
            self.protocol_manager = ProtocolManager()
            self.protocol_manager.load_protocols()
            
            # Inicializar ProtocolExecutor
            self.protocol_executor = ProtocolExecutor()
            
            print("✅ Sistema modular inicializado")
            
        except Exception as e:
            print(f"❌ Error inicializando sistema modular: {e}")
            show_error("Error de Inicialización", 
                      f"No se pudo inicializar el sistema de protocolos: {e}", self)
    
    def setup_custom_widgets(self):
        """Configurar widgets personalizados en el UI"""
        
        # Configurar widget de cámara
        self.setup_camera_widget()
        
        # Configurar widget de gráfico
        self.setup_graph_widget()
        
        # Configurar widget de protocolos
        self.setup_protocol_widget()
        
        # Agregar controles de gráfico
        self.setup_graph_controls()
        
        print("✅ Widgets personalizados configurados")
    
    def setup_camera_widget(self):
        """Configurar widget de cámara modular"""
        if not hasattr(self.ui, 'widget_camera_placeholder'):
            print("⚠️ widget_camera_placeholder no encontrado en UI")
            return
        
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
            if self.protocol_executor:
                self.protocol_executor.set_camera_widget(self.camera_widget)
            
            print("✅ Widget de cámara integrado")
    
    def setup_graph_widget(self):
        """Configurar widget de gráfico modular"""
        if not hasattr(self.ui, 'widget_plot_placeholder'):
            print("⚠️ widget_plot_placeholder no encontrado en UI")
            return
        
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
            if self.protocol_executor:
                self.protocol_executor.set_graph_widget(self.vcl_graph_widget)
            
            print("✅ VCLGraphWidget integrado")
    
    def setup_protocol_widget(self):
        """Configurar widget de protocolos modular"""
        if not hasattr(self.ui, 'layout_left_vertical'):
            print("⚠️ layout_left_vertical no encontrado en UI")
            return
        
        # Obtener layout izquierdo
        left_layout = self.ui.layout_left_vertical
        
        # Crear widget de protocolos
        self.protocol_widget = ProtocolTreeWidget()
        
        # Insertar al inicio del layout
        left_layout.insertWidget(0, self.protocol_widget)
        
        print("✅ Widget de protocolos integrado")
    
    def setup_graph_controls(self):
        """Agregar controles de gráfico en panel derecho"""
        if not hasattr(self.ui, 'layout_right_vertical'):
            print("⚠️ layout_right_vertical no encontrado en UI")
            return
        
        self.graph_tools_group = QGroupBox("Herramientas de Gráfico")
        if hasattr(self.ui, 'group_controles_analisis'):
            self.graph_tools_group.setFont(self.ui.group_controles_analisis.font())
        
        graph_tools_layout = QVBoxLayout(self.graph_tools_group)
        graph_tools_layout.setSpacing(8)
        
        # Crear botones de herramientas
        self.btn_torok = QPushButton("Activar Torok")
        self.btn_torok.setCheckable(True)
        graph_tools_layout.addWidget(self.btn_torok)
        
        self.btn_peak_edit = QPushButton("Activar Edición Picos")
        self.btn_peak_edit.setCheckable(True)
        graph_tools_layout.addWidget(self.btn_peak_edit)
        
        self.btn_tiempo_fijacion = QPushButton("Agregar Tiempo Fijación")
        graph_tools_layout.addWidget(self.btn_tiempo_fijacion)
        
        self.btn_zoom = QPushButton("Activar Zoom")
        self.btn_zoom.setCheckable(True)
        graph_tools_layout.addWidget(self.btn_zoom)
        
        self.btn_crosshair_graph = QPushButton("Activar Cursor Cruz")
        self.btn_crosshair_graph.setCheckable(True)
        graph_tools_layout.addWidget(self.btn_crosshair_graph)
        
        self.btn_peak_detection = QPushButton("Detección Automática")
        self.btn_peak_detection.setCheckable(True)
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
    
    def setup_basic_connections(self):
        """Configurar conexiones básicas del UI"""
        if not self.ui:
            return
        
        # Verificar que existen los elementos básicos
        if not hasattr(self.ui, 'btn_conectar_camara'):
            print("⚠️ No se encontraron algunos botones básicos en el UI")
            return
        
        # Configurar botón principal SIEV (sin conectar aún)
        self.ui.btn_conectar_camara.setText("Buscar SIEV")
        
        print("✅ Conexiones básicas configuradas")
    
    def load_basic_icons(self):
        """Cargar iconos básicos en elementos UI"""
        try:
            if not self.ui:
                return
            
            # Icono del botón principal
            if hasattr(self.ui, 'btn_conectar_camara'):
                search_icon = get_icon("search", 16, IconColors.BLUE)
                self.ui.btn_conectar_camara.setIcon(search_icon)
            
            # Icono de grabación
            if hasattr(self.ui, 'btn_grabar'):
                record_icon = get_icon("circle", 16, IconColors.RED)
                self.ui.btn_grabar.setIcon(record_icon)
            
            print("✅ Iconos básicos cargados")
        except Exception as e:
            print(f"⚠️ Error cargando iconos básicos: {e}")
    
    def get_protocol_manager(self) -> ProtocolManager:
        """Obtener referencia al ProtocolManager"""
        return self.protocol_manager
    
    def get_protocol_executor(self) -> ProtocolExecutor:
        """Obtener referencia al ProtocolExecutor"""
        return self.protocol_executor
    
    def get_camera_widget(self) -> ModularCameraWidget:
        """Obtener referencia al widget de cámara"""
        return self.camera_widget
    
    def get_graph_widget(self) -> VCLGraphWidget:
        """Obtener referencia al widget de gráfico"""
        return self.vcl_graph_widget
    
    def get_protocol_widget(self) -> ProtocolTreeWidget:
        """Obtener referencia al widget de protocolos"""
        return self.protocol_widget
    
    def is_ready(self) -> bool:
        """Verificar si la ventana está completamente inicializada"""
        return (self.is_initialized and 
                self.ui is not None and 
                self.protocol_manager is not None and 
                self.protocol_executor is not None)
    
    def cleanup(self):
        """Limpieza al cerrar aplicación"""
        print("🧹 Limpiando MainWindowBase...")
        
        # Cleanup del executor
        if self.protocol_executor:
            self.protocol_executor.cleanup()
        
        # Liberar cámara
        if self.camera_widget and self.camera_widget.is_connected:
            self.camera_widget.release_camera()
        
        # Guardar protocolos
        if self.protocol_manager:
            self.protocol_manager.save_protocols()
        
        print("✅ MainWindowBase limpiado correctamente")