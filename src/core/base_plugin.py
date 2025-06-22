#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIEV - Base Plugin System
Sistema completo de plugins con interfaz abstracta y utilidades comunes
"""

from typing import Optional, Dict, Any, List
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QPushButton
from PySide6.QtCore import QObject, Signal, QTimer, Qt
from PySide6.QtGui import QIcon


class PluginMetadata:
    """
    Metadatos de plugin para registro y gestión
    """
    def __init__(self, name: str, display_name: str, version: str = "1.0.0", 
                 description: str = "", author: str = "", category: str = "general"):
        self.name = name
        self.display_name = display_name
        self.version = version
        self.description = description
        self.author = author
        self.category = category
        self.enabled = True
        self.dependencies = []
        self.icon_path = None


class PluginStatus:
    """
    Estados posibles de un plugin
    """
    INACTIVE = "inactive"
    LOADING = "loading"
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"


class BasePlugin(QWidget):
    """
    Clase base abstracta para todos los plugins del sistema SIEV
    Proporciona interfaz común y funcionalidades básicas
    """
    
    # Señales para comunicación entre plugins
    plugin_activated = Signal(str)  # nombre del plugin
    plugin_deactivated = Signal(str)
    plugin_error = Signal(str, str)  # plugin_name, error_message
    data_updated = Signal(str, dict)  # plugin_name, data
    status_changed = Signal(str, str)  # plugin_name, new_status
    
    def __init__(self, parent=None):
        """
        Inicializar plugin base
        
        Args:
            parent: Widget padre (típicamente MainWindow)
        """
        super().__init__(parent)
        
        # Estado del plugin
        self._status = PluginStatus.INACTIVE
        self._is_initialized = False
        self._error_message = None
        
        # Widgets internos
        self._main_widget = None
        self._error_widget = None
        self._loading_widget = None
        
        # Timer para actualizaciones periódicas
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._on_periodic_update)
        
        # Datos compartidos del plugin
        self._plugin_data = {}
        
        # Configurar layout base
        self._setup_base_layout()
        
    def _setup_base_layout(self):
        """Configurar layout base del plugin"""
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        
    # ===== MÉTODOS ABSTRACTOS (DEBEN SER IMPLEMENTADOS) =====
    
    def get_metadata(self) -> PluginMetadata:
        raise NotImplementedError("Subclases deben implementar get_metadata()")
        """
        Retorna metadatos del plugin
        
        Returns:
            PluginMetadata: Información del plugin
        """
        
    def initialize_plugin(self) -> bool:
        raise NotImplementedError("Subclases deben implementar initialize_plugin()")
        """
        Inicializar el plugin (cargar UI, configurar datos, etc.)
        
        Returns:
            bool: True si inicialización exitosa, False en caso contrario
        """
        
    def create_main_widget(self) -> QWidget:
        raise NotImplementedError("Subclases deben implementar create_main_widget()")
        """
        Crear el widget principal del plugin
        
        Returns:
            QWidget: Widget principal con la interfaz del plugin
        """
        
    # ===== MÉTODOS OPCIONALES (PUEDEN SER SOBRESCRITOS) =====
    
    def on_activate(self):
        """
        Llamado cuando el plugin se activa (se muestra)
        Sobrescribir para lógica específica de activación
        """
        pass
        
    def on_deactivate(self):
        """
        Llamado cuando el plugin se desactiva (se oculta)
        Sobrescribir para lógica específica de desactivación
        """
        pass
        
    def on_periodic_update(self):
        """
        Llamado periódicamente si el plugin tiene actualizaciones automáticas
        Sobrescribir para lógica de actualización
        """
        pass
        
    def validate_dependencies(self) -> bool:
        """
        Validar dependencias del plugin
        
        Returns:
            bool: True si dependencias satisfechas
        """
        return True
        
    def get_settings_widget(self) -> Optional[QWidget]:
        """
        Retorna widget de configuración específica del plugin
        
        Returns:
            QWidget: Widget de configuración o None
        """
        return None
        
    def save_plugin_data(self) -> Dict[str, Any]:
        """
        Guardar datos persistentes del plugin
        
        Returns:
            dict: Datos a persistir
        """
        return self._plugin_data.copy()
        
    def load_plugin_data(self, data: Dict[str, Any]):
        """
        Cargar datos persistentes del plugin
        
        Args:
            data: Datos previamente guardados
        """
        self._plugin_data.update(data)
        
    def cleanup(self):
        """
        Limpiar recursos del plugin al cerrar
        Sobrescribir para limpieza específica
        """
        if self._update_timer.isActive():
            self._update_timer.stop()
            
    # ===== MÉTODOS PÚBLICOS =====
    
    def get_widget(self) -> QWidget:
        """
        Obtener el widget principal del plugin
        
        Returns:
            QWidget: Widget a mostrar en el área central
        """
        if not self._is_initialized:
            success = self.initialize_plugin()
            if not success:
                return self._get_error_widget("Error inicializando plugin")
                
        if self._status == PluginStatus.ERROR:
            return self._get_error_widget(self._error_message or "Error desconocido")
        elif self._status == PluginStatus.LOADING:
            return self._get_loading_widget()
        else:
            if self._main_widget is None:
                try:
                    self._main_widget = self.create_main_widget()
                    self._set_status(PluginStatus.ACTIVE)
                except Exception as e:
                    self._set_error(f"Error creando widget: {str(e)}")
                    return self._get_error_widget(str(e))
                    
            return self._main_widget
            
    def activate(self):
        """Activar plugin"""
        try:
            if self._status != PluginStatus.ACTIVE:
                self._set_status(PluginStatus.LOADING)
                
            self.on_activate()
            self._set_status(PluginStatus.ACTIVE)
            self.plugin_activated.emit(self.get_metadata().name)
            
        except Exception as e:
            self._set_error(f"Error activando plugin: {str(e)}")
            
    def deactivate(self):
        """Desactivar plugin"""
        try:
            self.on_deactivate()
            self._set_status(PluginStatus.INACTIVE)
            self.plugin_deactivated.emit(self.get_metadata().name)
            
        except Exception as e:
            self._set_error(f"Error desactivando plugin: {str(e)}")
            
    def start_periodic_updates(self, interval_ms: int = 1000):
        """
        Iniciar actualizaciones periódicas
        
        Args:
            interval_ms: Intervalo en milisegundos
        """
        self._update_timer.start(interval_ms)
        
    def stop_periodic_updates(self):
        """Detener actualizaciones periódicas"""
        self._update_timer.stop()
        
    def set_plugin_data(self, key: str, value: Any):
        """
        Establecer dato del plugin
        
        Args:
            key: Clave del dato
            value: Valor del dato
        """
        self._plugin_data[key] = value
        self.data_updated.emit(self.get_metadata().name, self._plugin_data)
        
    def get_plugin_data(self, key: str, default: Any = None) -> Any:
        """
        Obtener dato del plugin
        
        Args:
            key: Clave del dato
            default: Valor por defecto
            
        Returns:
            Valor del dato o default
        """
        return self._plugin_data.get(key, default)
        
    def get_status(self) -> str:
        """Obtener estado actual del plugin"""
        return self._status
        
    def is_active(self) -> bool:
        """Verificar si plugin está activo"""
        return self._status == PluginStatus.ACTIVE
        
    def has_error(self) -> bool:
        """Verificar si plugin tiene error"""
        return self._status == PluginStatus.ERROR
        
    def get_error_message(self) -> Optional[str]:
        """Obtener mensaje de error actual"""
        return self._error_message
        
    # ===== MÉTODOS PRIVADOS =====
    
    def _set_status(self, status: str):
        """Establecer estado del plugin"""
        old_status = self._status
        self._status = status
        
        if old_status != status:
            self.status_changed.emit(self.get_metadata().name, status)
            
    def _set_error(self, error_message: str):
        """Establecer estado de error"""
        self._error_message = error_message
        self._set_status(PluginStatus.ERROR)
        self.plugin_error.emit(self.get_metadata().name, error_message)
        
    def _on_periodic_update(self):
        """Handler interno para actualizaciones periódicas"""
        try:
            self.on_periodic_update()
        except Exception as e:
            self._set_error(f"Error en actualización periódica: {str(e)}")
            
    def _get_loading_widget(self) -> QWidget:
        """Crear widget de carga"""
        if self._loading_widget is None:
            self._loading_widget = QWidget()
            layout = QVBoxLayout(self._loading_widget)
            layout.setAlignment(Qt.AlignCenter)
            
            label = QLabel("Cargando plugin...")
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("""
                QLabel {
                    font-size: 16px;
                    color: #6B7280;
                    padding: 40px;
                }
            """)
            
            layout.addWidget(label)
            
        return self._loading_widget
        
    def _get_error_widget(self, error_message: str) -> QWidget:
        """
        Crear widget de error
        
        Args:
            error_message: Mensaje de error a mostrar
        """
        if self._error_widget is None or self._error_message != error_message:
            self._error_widget = QWidget()
            layout = QVBoxLayout(self._error_widget)
            layout.setAlignment(Qt.AlignCenter)
            
            # Frame de error
            error_frame = QFrame()
            error_frame.setFrameStyle(QFrame.Box)
            error_frame.setStyleSheet("""
                QFrame {
                    background-color: #FEF2F2;
                    border: 1px solid #EF4444;
                    border-radius: 8px;
                    padding: 24px;
                    margin: 20px;
                }
            """)
            
            error_layout = QVBoxLayout(error_frame)
            
            # Título de error
            title_label = QLabel("Error en Plugin")
            title_label.setAlignment(Qt.AlignCenter)
            title_label.setStyleSheet("""
                QLabel {
                    font-size: 18px;
                    font-weight: 600;
                    color: #DC2626;
                    margin-bottom: 12px;
                }
            """)
            
            # Mensaje de error
            message_label = QLabel(error_message)
            message_label.setAlignment(Qt.AlignCenter)
            message_label.setWordWrap(True)
            message_label.setStyleSheet("""
                QLabel {
                    font-size: 14px;
                    color: #991B1B;
                    margin-bottom: 16px;
                }
            """)
            
            # Botón de reintentar
            retry_button = QPushButton("Reintentar")
            retry_button.setStyleSheet("""
                QPushButton {
                    background-color: #EF4444;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #DC2626;
                }
            """)
            retry_button.clicked.connect(self._retry_initialization)
            
            error_layout.addWidget(title_label)
            error_layout.addWidget(message_label)
            error_layout.addWidget(retry_button)
            
            layout.addWidget(error_frame)
            
        return self._error_widget
        
    def _retry_initialization(self):
        """Reintentar inicialización del plugin"""
        self._error_message = None
        self._main_widget = None
        self._is_initialized = False
        self._set_status(PluginStatus.INACTIVE)
        
        # Forzar recreación del widget
        self.get_widget()


class PluginRegistry:
    """
    Registro global de plugins disponibles
    """
    _instance = None
    _plugins = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
        
    @classmethod
    def register_plugin(cls, plugin_class: type):
        """
        Registrar clase de plugin
        
        Args:
            plugin_class: Clase que hereda de BasePlugin
        """
        if not issubclass(plugin_class, BasePlugin):
            raise ValueError("Plugin debe heredar de BasePlugin")
            
        # Crear instancia temporal para obtener metadatos
        temp_instance = plugin_class()
        metadata = temp_instance.get_metadata()
        
        cls._plugins[metadata.name] = {
            'class': plugin_class,
            'metadata': metadata
        }
        
    @classmethod
    def get_plugin_class(cls, plugin_name: str) -> Optional[type]:
        """Obtener clase de plugin por nombre"""
        plugin_info = cls._plugins.get(plugin_name)
        return plugin_info['class'] if plugin_info else None
        
    @classmethod
    def get_available_plugins(cls) -> List[PluginMetadata]:
        """Obtener lista de plugins disponibles"""
        return [info['metadata'] for info in cls._plugins.values()]
        
    @classmethod
    def get_plugins_by_category(cls, category: str) -> List[PluginMetadata]:
        """Obtener plugins por categoría"""
        return [info['metadata'] for info in cls._plugins.values() 
                if info['metadata'].category == category]