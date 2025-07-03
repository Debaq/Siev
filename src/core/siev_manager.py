#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIEV Manager - Gestor especializado para hardware SIEV
Maneja detección, conexión y estado del sistema SIEV
"""

from typing import Optional, Dict, Any
from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtWidgets import QPushButton

from utils.siev_detection_modal import SievDetectionModal
from utils.icon_utils import get_icon, IconColors
from utils.dialog_utils import DialogUtils


class SievManager(QObject):
    """
    Gestor especializado para el hardware SIEV.
    Centraliza toda la lógica de detección, conexión y estado del sistema.
    """
    
    # Señales
    siev_connected = Signal(bool)  # Estado de conexión SIEV
    siev_status_changed = Signal(str)  # Mensaje de estado
    camera_mode_changed = Signal(bool)  # True=modo cámara, False=modo búsqueda
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Estado SIEV
        self.siev_setup = None
        self.siev_camera_index = None
        self.siev_serial_port = None
        self.siev_connected_flag = False
        
        # Referencias UI (se configuran externamente)
        self.main_button = None
        self.status_label = None
        self.patient_info_label = None
        
        print("✅ SievManager inicializado")
    
    def set_ui_references(self, main_button: QPushButton, 
                         status_label=None, patient_info_label=None):
        """Configurar referencias a elementos UI"""
        self.main_button = main_button
        self.status_label = status_label
        self.patient_info_label = patient_info_label
        
        # Configurar botón inicial
        if self.main_button:
            self.main_button.setText("Buscar SIEV")
            self.main_button.clicked.connect(self.handle_main_button)
        
        # Actualizar estado inicial
        self.update_siev_status()
        
        print("✅ Referencias UI configuradas en SievManager")
    
    def detect_siev_on_startup(self):
        """Detectar SIEV automáticamente al iniciar"""
        print("🔍 Iniciando detección SIEV automática...")
        QTimer.singleShot(2000, self.show_siev_detection_modal)
    
    def show_siev_detection_modal(self):
        """Mostrar modal de detección SIEV"""
        print("📋 Mostrando modal de detección SIEV...")
        
        modal = SievDetectionModal(self.parent() if self.parent() else None)
        result = modal.exec()
        
        detection_result = modal.get_detection_result()
        
        if detection_result and detection_result['success']:
            # SIEV detectado exitosamente
            self._on_siev_detected(detection_result['setup'])
        else:
            # SIEV no detectado
            self._on_siev_not_detected(detection_result.get('error') if detection_result else 'Sin resultado')
    
    def _on_siev_detected(self, siev_setup: Dict[str, Any]):
        """Manejar detección exitosa de SIEV"""
        print("✅ SIEV detectado exitosamente")
        
        # Guardar configuración SIEV
        self.siev_setup = siev_setup
        self.siev_camera_index = siev_setup['camera'].get('opencv_index')
        self.siev_serial_port = siev_setup['esp8266']['port']
        self.siev_connected_flag = True
        
        # Actualizar UI
        self.update_siev_status()
        self.switch_to_camera_mode()
        
        # Emitir señales
        self.siev_connected.emit(True)
        self.siev_status_changed.emit("✅ Hardware SIEV conectado y listo")
        
        # Mostrar información del hardware
        if self.parent():
            DialogUtils.show_hardware_status(self.siev_setup, self.parent())
        
        print(f"📡 ESP8266: {self.siev_serial_port}")
        print(f"📹 Cámara: OpenCV índice {self.siev_camera_index}")
    
    def _on_siev_not_detected(self, error_msg: str):
        """Manejar fallo en detección de SIEV"""
        print(f"❌ SIEV no detectado: {error_msg}")
        
        # Limpiar estado
        self.siev_setup = None
        self.siev_camera_index = None
        self.siev_serial_port = None
        self.siev_connected_flag = False
        
        # Actualizar UI
        self.update_siev_status()
        self.switch_to_siev_mode()
        
        # Emitir señales
        self.siev_connected.emit(False)
        self.siev_status_changed.emit("⚠️ Hardware SIEV no detectado")
    
    def handle_main_button(self):
        """Manejar click del botón principal según estado actual"""
        if not self.siev_connected_flag:
            # Modo búsqueda: buscar SIEV
            print("🔍 Iniciando búsqueda manual de SIEV")
            self.show_siev_detection_modal()
        else:
            # Modo cámara: toggle cámara (delegado externamente)
            print("📹 Toggle cámara solicitado")
            self.camera_mode_changed.emit(True)
    
    def switch_to_camera_mode(self):
        """Cambiar interfaz a modo cámara"""
        if self.main_button:
            self.main_button.setText("Conectar Cámara")
            camera_icon = get_icon("camera", 16, IconColors.GREEN)
            self.main_button.setIcon(camera_icon)
        
        print("🔄 Cambiado a modo cámara")
    
    def switch_to_siev_mode(self):
        """Cambiar interfaz a modo búsqueda SIEV"""
        if self.main_button:
            self.main_button.setText("Buscar SIEV")
            search_icon = get_icon("search", 16, IconColors.BLUE)
            self.main_button.setIcon(search_icon)
        
        print("🔄 Cambiado a modo búsqueda SIEV")
    
    def update_siev_status(self):
        """Actualizar estado SIEV en la interfaz"""
        if self.siev_connected_flag and self.siev_setup:
            self._update_connected_status()
        else:
            self._update_disconnected_status()
    
    def _update_connected_status(self):
        """Actualizar UI para estado conectado"""
        siev_info = (
            f"🔗 SIEV Conectado\n"
            f"📡 ESP8266: {self.siev_serial_port}\n"
            f"📹 Cámara: OpenCV índice {self.siev_camera_index}\n"
            f"🏥 Estado: Listo para evaluación"
        )
        
        connected_style = """
            QLabel {
                background-color: #d5ead4;
                padding: 10px;
                border-radius: 5px;
                color: #2c3e50;
                border: 1px solid #27ae60;
            }
        """
        
        self._apply_status_update(siev_info, connected_style)
        
        if self.status_label:
            self.status_label.showMessage("✅ Hardware SIEV conectado y listo")
    
    def _update_disconnected_status(self):
        """Actualizar UI para estado desconectado"""
        siev_info = (
            f"❌ SIEV No Conectado\n"
            f"📅 Fecha: --/--/----\n"
            f"🏥 Estado: Hardware no disponible\n"
            f"💡 Use 'Buscar SIEV' para conectar"
        )
        
        disconnected_style = """
            QLabel {
                background-color: #fdeaea;
                padding: 10px;
                border-radius: 5px;
                color: #2c3e50;
                border: 1px solid #e74c3c;
            }
        """
        
        self._apply_status_update(siev_info, disconnected_style)
        
        if self.status_label:
            self.status_label.showMessage("⚠️ Hardware SIEV no detectado")
        
        # Asegurar modo búsqueda
        self.switch_to_siev_mode()
    
    def _apply_status_update(self, info_text: str, style: str):
        """Aplicar actualización de estado a la UI"""
        if self.patient_info_label:
            self.patient_info_label.setText(info_text)
            self.patient_info_label.setStyleSheet(style)
    
    def force_reconnection(self):
        """Forzar nueva detección de SIEV"""
        print("🔄 Forzando reconexión SIEV...")
        
        # Limpiar estado actual
        self.siev_setup = None
        self.siev_camera_index = None
        self.siev_serial_port = None
        self.siev_connected_flag = False
        
        # Actualizar UI
        self.update_siev_status()
        
        # Iniciar nueva detección
        self.show_siev_detection_modal()
    
    def disconnect_siev(self):
        """Desconectar SIEV manualmente"""
        print("🔌 Desconectando SIEV...")
        
        # Limpiar estado
        self.siev_setup = None
        self.siev_camera_index = None
        self.siev_serial_port = None
        self.siev_connected_flag = False
        
        # Actualizar UI
        self.update_siev_status()
        
        # Emitir señales
        self.siev_connected.emit(False)
        self.siev_status_changed.emit("🔌 SIEV desconectado")
    
    # ===== GETTERS Y PROPIEDADES =====
    
    @property
    def is_connected(self) -> bool:
        """Verificar si SIEV está conectado"""
        return self.siev_connected_flag
    
    def get_camera_index(self) -> Optional[int]:
        """Obtener índice de cámara SIEV"""
        return self.siev_camera_index
    
    def get_serial_port(self) -> Optional[str]:
        """Obtener puerto serial ESP8266"""
        return self.siev_serial_port
    
    def get_siev_setup(self) -> Optional[Dict[str, Any]]:
        """Obtener configuración completa SIEV"""
        return self.siev_setup
    
    def get_hardware_info(self) -> Dict[str, Any]:
        """Obtener información de hardware"""
        if not self.siev_connected_flag or not self.siev_setup:
            return {
                'connected': False,
                'camera_index': None,
                'serial_port': None,
                'setup': None
            }
        
        return {
            'connected': True,
            'camera_index': self.siev_camera_index,
            'serial_port': self.siev_serial_port,
            'setup': self.siev_setup,
            'hub_info': self.siev_setup.get('hub', {}),
            'esp_info': self.siev_setup.get('esp8266', {}),
            'camera_info': self.siev_setup.get('camera', {})
        }
    
    def has_led_control(self) -> bool:
        """Verificar si hay control de LED disponible"""
        return (self.siev_connected_flag and 
                self.siev_serial_port is not None)
    
    def get_status_summary(self) -> str:
        """Obtener resumen del estado actual"""
        if self.siev_connected_flag:
            return f"Conectado - Cámara:{self.siev_camera_index} Serial:{self.siev_serial_port}"
        else:
            return "Desconectado - Hardware no disponible"