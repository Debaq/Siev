#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIEV - Plugin Loader
Sistema completo de carga dinámica de plugins
"""

import importlib
import sys
import os
from pathlib import Path
from utils.path_manager import get_plugin_dir, paths  # ← AGREGAR ESTA LÍNEA
from typing import Dict, Optional, List, Any
from PySide6.QtWidgets import QWidget, QVBoxLayout, QStackedWidget, QLabel, QFrame, QPushButton
from PySide6.QtCore import QObject, Signal, QTimer, Qt
from PySide6.QtGui import QMovie

from core.base_plugin import BasePlugin, PluginRegistry, PluginMetadata, PluginStatus


class PluginLoader(QObject):
    """
    Cargador dinámico de plugins con gestión completa del ciclo de vida
    """
    
    # Señales para comunicación
    plugin_loaded = Signal(str)  # plugin_name
    plugin_unloaded = Signal(str)  # plugin_name
    plugin_error = Signal(str, str)  # plugin_name, error_message
    loading_started = Signal(str)  # plugin_name
    loading_finished = Signal(str)  # plugin_name
    
    def __init__(self, main_window=None):
        """
        Inicializar cargador de plugins
        
        Args:
            main_window: Ventana principal con área central
        """
        super().__init__()
        
        self.main_window = main_window
        self.plugins_path = paths.get_path('plugins')
        
        # Gestión de plugins
        self.loaded_plugins: Dict[str, BasePlugin] = {}
        self.current_plugin: Optional[str] = None
        self.plugin_instances: Dict[str, BasePlugin] = {}
        
        # Widget stack para área central
        self.central_stack = None
        self.central_area = None
        
        # Cache de widgets
        self.plugin_widgets: Dict[str, QWidget] = {}
        
        # Estado interno
        self.is_loading = False
        self.pending_plugin = None
        
        # Timer para carga diferida
        self.load_timer = QTimer()
        self.load_timer.setSingleShot(True)
        self.load_timer.timeout.connect(self._perform_delayed_load)
        
        # Inicializar
        self._setup_central_area()
        self._discover_plugins()
        
    def _setup_central_area(self):
        """Configurar área central con stack widget"""
        if not self.main_window:
            return
            
        try:
            # Buscar área central en la ventana principal
            self.central_area = getattr(self.main_window, 'plugin_container', None)
            
            if self.central_area is None:
                # Buscar por findChild si no está como atributo directo
                self.central_area = self.main_window.findChild(QWidget, 'plugin_container')
                
            if self.central_area is None:
                print("⚠️  No se encontró 'plugin_container' en MainWindow")
                return
                
            # Limpiar área central existente
            self._clear_central_area()
            
            # Crear stack widget
            self.central_stack = QStackedWidget()
            
            # Configurar layout del área central
            if self.central_area.layout() is None:
                layout = QVBoxLayout(self.central_area)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.setSpacing(0)
            else:
                layout = self.central_area.layout()
                
            layout.addWidget(self.central_stack)
            
            # Agregar widget placeholder inicial
            self._add_placeholder_widget()
            
            print("✅ Área central configurada con StackWidget")
            
        except Exception as e:
            print(f"❌ Error configurando área central: {e}")
            
    def _clear_central_area(self):
        """Limpiar widgets existentes del área central"""
        if self.central_area and self.central_area.layout():
            layout = self.central_area.layout()
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
                    
    def _add_placeholder_widget(self):
        """Agregar widget placeholder inicial"""
        placeholder = QWidget()
        layout = QVBoxLayout(placeholder)
        layout.setAlignment(Qt.AlignCenter)
        
        welcome_frame = QFrame()
        welcome_frame.setFrameStyle(QFrame.Box)
        welcome_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #E5E7EB;
                border-radius: 12px;
                padding: 40px;
                margin: 20px;
            }
        """)
        
        welcome_layout = QVBoxLayout(welcome_frame)
        welcome_layout.setAlignment(Qt.AlignCenter)
        
        title = QLabel("🏥 SIEV")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                font-size: 32px;
                font-weight: 700;
                color: #6B46C1;
                margin-bottom: 16px;
            }
        """)
        
        subtitle = QLabel("Sistema Integrado de Evaluación Vestibular")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #6B7280;
                margin-bottom: 24px;
            }
        """)
        
        instruction = QLabel("Selecciona una opción del menú lateral para comenzar")
        instruction.setAlignment(Qt.AlignCenter)
        instruction.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #9CA3AF;
            }
        """)
        
        welcome_layout.addWidget(title)
        welcome_layout.addWidget(subtitle)
        welcome_layout.addWidget(instruction)
        
        layout.addWidget(welcome_frame)
        
        self.central_stack.addWidget(placeholder)
        
    def _discover_plugins(self):
        """Descubrir plugins disponibles en el directorio"""
        if not self.plugins_path.exists():
            print(f"⚠️  Directorio de plugins no encontrado: {self.plugins_path}")
            return
            
        discovered = []
        
        for item in self.plugins_path.iterdir():
            if item.is_dir() and not item.name.startswith('__'):
                plugin_file = item / f"{item.name}.py"
                
                if plugin_file.exists():
                    discovered.append(item.name)
                    
        print(f"🔍 Plugins descubiertos: {discovered}")
        
    def load_plugin(self, plugin_name: str, force_reload: bool = False):
        """
        Cargar plugin específico
        
        Args:
            plugin_name: Nombre del plugin a cargar
            force_reload: Forzar recarga si ya está cargado
        """
        try:
            # Validar estado
            if self.is_loading and not force_reload:
                print(f"⚠️  Ya hay un plugin cargándose, ignorando: {plugin_name}")
                return
                
            # Si es el mismo plugin actual, no hacer nada
            if self.current_plugin == plugin_name and not force_reload:
                print(f"📋 Plugin '{plugin_name}' ya está activo")
                return
                
            print(f"🔄 Cargando plugin: {plugin_name}")
            self.loading_started.emit(plugin_name)
            self.is_loading = True
            
            # Desactivar plugin actual
            self._deactivate_current_plugin()
            
            # Cargar nuevo plugin
            success = self._load_plugin_instance(plugin_name, force_reload)
            
            if success:
                self._activate_plugin(plugin_name)
                self.current_plugin = plugin_name
                self.plugin_loaded.emit(plugin_name)
                print(f"✅ Plugin '{plugin_name}' cargado exitosamente")
            else:
                print(f"❌ Error cargando plugin '{plugin_name}'")
                
        except Exception as e:
            error_msg = f"Error cargando plugin '{plugin_name}': {str(e)}"
            print(f"❌ {error_msg}")
            self.plugin_error.emit(plugin_name, error_msg)
            
        finally:
            self.is_loading = False
            self.loading_finished.emit(plugin_name)
            
    def _load_plugin_instance(self, plugin_name: str, force_reload: bool) -> bool:
        """
        Cargar instancia específica del plugin
        
        Args:
            plugin_name: Nombre del plugin
            force_reload: Forzar recarga
            
        Returns:
            bool: True si carga exitosa
        """
        try:
            # Si ya existe y no es force reload, usar existente
            if plugin_name in self.plugin_instances and not force_reload:
                return True
                
            # Construir ruta del módulo
            module_path = f"plugins.{plugin_name}.{plugin_name}"
            
            # Importar o recargar módulo
            if module_path in sys.modules and force_reload:
                importlib.reload(sys.modules[module_path])
            
            module = importlib.import_module(module_path)
            
            # Buscar clase plugin (debe seguir convención de nombre)
            plugin_class_name = f"{plugin_name.title()}Plugin"
            
            if not hasattr(module, plugin_class_name):
                # Intentar variaciones de nombres
                alternatives = [
                    f"{plugin_name.capitalize()}Plugin",
                    f"{plugin_name.upper()}Plugin",
                    f"{plugin_name}Plugin"
                ]
                
                plugin_class = None
                for alt_name in alternatives:
                    if hasattr(module, alt_name):
                        plugin_class = getattr(module, alt_name)
                        break
                        
                if plugin_class is None:
                    print(f"❌ No se encontró clase plugin en módulo {module_path}")
                    return False
            else:
                plugin_class = getattr(module, plugin_class_name)
                
            # Verificar que hereda de BasePlugin
            if not issubclass(plugin_class, BasePlugin):
                print(f"❌ Clase {plugin_class_name} no hereda de BasePlugin")
                return False
                
            # Crear instancia
            if plugin_name in self.plugin_instances:
                # Limpiar instancia anterior
                old_instance = self.plugin_instances[plugin_name]
                old_instance.cleanup()
                old_instance.deleteLater()
                
            plugin_instance = plugin_class(parent=self.main_window)
            
            # Conectar señales
            self._connect_plugin_signals(plugin_instance)
            
            # Almacenar instancia
            self.plugin_instances[plugin_name] = plugin_instance
            
            return True
            
        except ImportError as e:
            print(f"❌ Error importando plugin '{plugin_name}': {e}")
            return False
        except Exception as e:
            print(f"❌ Error creando instancia de plugin '{plugin_name}': {e}")
            return False
            
    def _connect_plugin_signals(self, plugin_instance: BasePlugin):
        """Conectar señales del plugin"""
        plugin_instance.plugin_error.connect(self._handle_plugin_error)
        plugin_instance.status_changed.connect(self._handle_status_change)
        plugin_instance.data_updated.connect(self._handle_data_update)
        
    def _activate_plugin(self, plugin_name: str):
        """Activar plugin específico"""
        if plugin_name not in self.plugin_instances:
            return
            
        plugin_instance = self.plugin_instances[plugin_name]
        
        try:
            # Obtener widget del plugin
            plugin_widget = plugin_instance.get_widget()
            
            if plugin_widget:
                # Agregar al stack si no está
                if plugin_name not in self.plugin_widgets:
                    self.central_stack.addWidget(plugin_widget)
                    self.plugin_widgets[plugin_name] = plugin_widget
                    
                # Mostrar widget
                self.central_stack.setCurrentWidget(plugin_widget)
                
                # Activar plugin
                plugin_instance.activate()
                
        except Exception as e:
            print(f"❌ Error activando plugin '{plugin_name}': {e}")
            
    def _deactivate_current_plugin(self):
        """Desactivar plugin actual"""
        if self.current_plugin and self.current_plugin in self.plugin_instances:
            try:
                current_instance = self.plugin_instances[self.current_plugin]
                current_instance.deactivate()
            except Exception as e:
                print(f"⚠️  Error desactivando plugin '{self.current_plugin}': {e}")
                
    def _handle_plugin_error(self, plugin_name: str, error_message: str):
        """Manejar errores de plugins"""
        print(f"🚨 Error en plugin '{plugin_name}': {error_message}")
        self.plugin_error.emit(plugin_name, error_message)
        
    def _handle_status_change(self, plugin_name: str, new_status: str):
        """Manejar cambios de estado de plugins"""
        print(f"📊 Plugin '{plugin_name}' cambió a estado: {new_status}")
        
    def _handle_data_update(self, plugin_name: str, data: dict):
        """Manejar actualizaciones de datos de plugins"""
        print(f"📄 Plugin '{plugin_name}' actualizó datos")
        
    def _perform_delayed_load(self):
        """Realizar carga diferida"""
        if self.pending_plugin:
            self.load_plugin(self.pending_plugin)
            self.pending_plugin = None
            
    def schedule_plugin_load(self, plugin_name: str, delay_ms: int = 100):
        """
        Programar carga de plugin con delay
        
        Args:
            plugin_name: Nombre del plugin
            delay_ms: Delay en milisegundos
        """
        self.pending_plugin = plugin_name
        self.load_timer.start(delay_ms)
        
    def get_loaded_plugins(self) -> List[str]:
        """Obtener lista de plugins cargados"""
        return list(self.plugin_instances.keys())
        
    def get_current_plugin(self) -> Optional[str]:
        """Obtener plugin actual"""
        return self.current_plugin
        
    def unload_plugin(self, plugin_name: str):
        """
        Descargar plugin específico
        
        Args:
            plugin_name: Nombre del plugin a descargar
        """
        if plugin_name not in self.plugin_instances:
            return
            
        try:
            # Desactivar si es el actual
            if self.current_plugin == plugin_name:
                self._deactivate_current_plugin()
                self.current_plugin = None
                
            # Limpiar instancia
            plugin_instance = self.plugin_instances[plugin_name]
            plugin_instance.cleanup()
            
            # Remover widget del stack
            if plugin_name in self.plugin_widgets:
                widget = self.plugin_widgets[plugin_name]
                self.central_stack.removeWidget(widget)
                widget.deleteLater()
                del self.plugin_widgets[plugin_name]
                
            # Remover instancia
            plugin_instance.deleteLater()
            del self.plugin_instances[plugin_name]
            
            self.plugin_unloaded.emit(plugin_name)
            print(f"🗑️  Plugin '{plugin_name}' descargado")
            
        except Exception as e:
            print(f"❌ Error descargando plugin '{plugin_name}': {e}")
            
    def reload_plugin(self, plugin_name: str):
        """
        Recargar plugin específico
        
        Args:
            plugin_name: Nombre del plugin a recargar
        """
        print(f"🔄 Recargando plugin: {plugin_name}")
        self.unload_plugin(plugin_name)
        self.load_plugin(plugin_name, force_reload=True)
        
    def cleanup(self):
        """Limpiar todos los recursos"""
        print("🧹 Limpiando PluginLoader...")
        
        # Descargar todos los plugins
        for plugin_name in list(self.plugin_instances.keys()):
            self.unload_plugin(plugin_name)
            
        # Limpiar timers
        if self.load_timer.isActive():
            self.load_timer.stop()