#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIEV - Window Handler
Manejo básico de la ventana principal con sistema de plugins
"""

import os
from utils.path_manager import get_ui_file  # ← AGREGAR ESTA LÍNEA
from PySide6.QtWidgets import QMainWindow, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtUiTools import QUiLoader
from core.plugin_loader import PluginLoader


class WindowHandler:
    """
    Maneja la ventana principal de la aplicación
    Funcionalidad básica para cargar y mostrar MainWindow
    """
    
    def __init__(self):
        """Inicializar handler de ventana"""
        self.main_window = None
        self.ui_loader = QUiLoader()
        self.plugin_loader = None
        
    def setup_main_window(self):
        """Configurar y cargar ventana principal desde .ui"""
        try:
            # Ruta al archivo .ui principal
            ui_file_path = get_ui_file("main_window.ui")
            
            # Verificar que el archivo existe
            if not ui_file_path.exists():
                raise FileNotFoundError(f"Archivo UI no encontrado: {ui_file_path}")
            
            # Cargar archivo .ui
            self.main_window = self.ui_loader.load(str(ui_file_path))

            
            # Configuraciones básicas de ventana
            self.main_window.setWindowTitle("SIEV - Sistema Integrado de Evaluación Vestibular")
            self.main_window.resize(1200, 800)  # Tamaño inicial
            self.main_window.setMinimumSize(1024, 600)  # Tamaño mínimo
            
            # Centrar ventana en pantalla
            self._center_window()
            
            # Configurar sistema de plugins
            self._setup_plugin_system()
            
            # Conectar botones de navegación
            self._connect_navigation_buttons()
            
        except Exception as e:
            # Si no se puede cargar .ui, crear ventana básica
            print(f"⚠️  No se pudo cargar UI file: {e}")
            print("📄 Creando ventana básica como fallback")
            self._create_fallback_window()
            
    def _center_window(self):
        """Centrar ventana en la pantalla"""
        if self.main_window:
            # Obtener geometría de la pantalla
            screen = self.main_window.screen()
            screen_geometry = screen.availableGeometry()
            
            # Calcular posición central
            window_geometry = self.main_window.frameGeometry()
            center_point = screen_geometry.center()
            window_geometry.moveCenter(center_point)
            
            # Mover ventana al centro
            self.main_window.move(window_geometry.topLeft())
            
    def _create_fallback_window(self):
        """Crear ventana básica si no se puede cargar .ui"""
        self.main_window = QMainWindow()
        self.main_window.setWindowTitle("SIEV - Sistema Integrado de Evaluación Vestibular")
        self.main_window.resize(1200, 800)
        self.main_window.setMinimumSize(1024, 600)
        self._center_window()
        
    def _setup_plugin_system(self):
        """Configurar sistema de carga de plugins"""
        try:
            self.plugin_loader = PluginLoader(self.main_window)
            
            # Conectar señales del plugin loader
            self.plugin_loader.plugin_loaded.connect(self._on_plugin_loaded)
            self.plugin_loader.plugin_error.connect(self._on_plugin_error)
            self.plugin_loader.loading_started.connect(self._on_loading_started)
            self.plugin_loader.loading_finished.connect(self._on_loading_finished)
            
            print("✅ Sistema de plugins configurado")
            
        except Exception as e:
            print(f"❌ Error configurando sistema de plugins: {e}")
            
    def _connect_navigation_buttons(self):
        """Conectar botones de navegación con plugins"""
        if not self.main_window:
            return
            
        try:
            # Mapeo de botones a plugins
            button_plugin_map = {
                'btn_dashboard': 'dashboard',
                'btn_patients': 'patients', 
                'btn_vng': 'vng',
                'btn_reports': 'reports',
                'btn_settings': 'settings'
            }
            
            # Conectar cada botón disponible
            for button_name, plugin_name in button_plugin_map.items():
                button = getattr(self.main_window, button_name, None)
                
                if button and isinstance(button, QPushButton):
                    # Usar lambda con valor por defecto para capturar plugin_name
                    button.clicked.connect(
                        lambda checked=False, p=plugin_name: self.load_plugin(p)
                    )
                    print(f"✅ Conectado {button_name} -> {plugin_name}")
                else:
                    print(f"⚠️  Botón {button_name} no encontrado en UI")
                    
            print("✅ Botones de navegación conectados")
            
        except Exception as e:
            print(f"❌ Error conectando botones de navegación: {e}")
            
    def load_plugin(self, plugin_name: str):
        """
        Cargar plugin específico
        
        Args:
            plugin_name: Nombre del plugin a cargar
        """
        if self.plugin_loader:
            self.plugin_loader.load_plugin(plugin_name)
        else:
            print(f"⚠️  Plugin loader no disponible para cargar: {plugin_name}")
            
    def _on_plugin_loaded(self, plugin_name: str):
        """Callback cuando plugin se carga exitosamente"""
        print(f"🎉 Plugin cargado: {plugin_name}")
        self._update_navigation_state(plugin_name)
        
    def _on_plugin_error(self, plugin_name: str, error_message: str):
        """Callback cuando hay error en plugin"""
        print(f"🚨 Error en plugin {plugin_name}: {error_message}")
        
    def _on_loading_started(self, plugin_name: str):
        """Callback cuando inicia carga de plugin"""
        print(f"⏳ Iniciando carga de plugin: {plugin_name}")
        
    def _on_loading_finished(self, plugin_name: str):
        """Callback cuando termina carga de plugin"""
        print(f"✅ Terminó carga de plugin: {plugin_name}")
        
    def _update_navigation_state(self, active_plugin: str):
        """
        Actualizar estado visual de navegación
        
        Args:
            active_plugin: Plugin actualmente activo
        """
        if not self.main_window:
            return
            
        # Mapeo inverso para encontrar botón activo
        plugin_button_map = {
            'dashboard': 'btn_dashboard',
            'patients': 'btn_patients',
            'vng': 'btn_vng', 
            'reports': 'btn_reports',
            'settings': 'btn_settings'
        }
        
        # Resetear todos los botones
        for plugin_name, button_name in plugin_button_map.items():
            button = getattr(self.main_window, button_name, None)
            if button:
                # Remover estado activo
                button.setProperty("active", "false")
                button.setStyleSheet(button.styleSheet())  # Forzar actualización
                
        # Activar botón actual
        if active_plugin in plugin_button_map:
            active_button_name = plugin_button_map[active_plugin]
            active_button = getattr(self.main_window, active_button_name, None)
            if active_button:
                active_button.setProperty("active", "true")
                active_button.setStyleSheet(active_button.styleSheet())  # Forzar actualización
        
    def show_window(self):
        """Mostrar ventana principal"""
        if self.main_window:
            self.main_window.show()
            self.main_window.raise_()  # Traer al frente
            self.main_window.activateWindow()  # Activar ventana
            
    def cleanup(self):
        """Limpiar recursos de ventana"""
        try:
            # Limpiar sistema de plugins
            if self.plugin_loader:
                self.plugin_loader.cleanup()
                self.plugin_loader = None
                
            # Cerrar ventana principal
            if self.main_window:
                self.main_window.close()
                self.main_window = None
                
            print("🧹 WindowHandler limpiado correctamente")
            
        except Exception as e:
            print(f"⚠️  Error en cleanup de WindowHandler: {e}")