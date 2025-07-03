#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Camera Controller - Controlador especializado para funciones de cámara
Maneja conexión, grabación y configuración del widget de cámara
"""

from typing import Optional, Dict, Any
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QPushButton, QLabel, QCheckBox

from camera.camera_widget import ModularCameraWidget


class CameraController(QObject):
    """
    Controlador especializado para el manejo de cámara.
    Centraliza toda la lógica de conexión, grabación y configuración.
    """
    
    # Señales
    camera_connected = Signal(bool)  # Estado de conexión
    recording_state_changed = Signal(bool)  # Estado de grabación
    camera_status_changed = Signal(str)  # Mensaje de estado
    
    def __init__(self, camera_widget: ModularCameraWidget, parent=None):
        super().__init__(parent)
        
        # Widget de cámara
        self.camera_widget = camera_widget
        
        # Referencias UI (se configuran externamente)
        self.connect_button = None
        self.record_button = None
        self.status_label = None
        
        # Checkboxes de opciones
        self.crosshair_check = None
        self.tracking_check = None
        
        # Estado del controlador
        self.siev_camera_index = None
        self.is_recording = False
        
        print("✅ CameraController inicializado")
    
    def set_ui_references(self, connect_button: QPushButton, 
                         record_button: QPushButton = None,
                         status_label: QLabel = None,
                         crosshair_check: QCheckBox = None,
                         tracking_check: QCheckBox = None):
        """Configurar referencias a elementos UI"""
        self.connect_button = connect_button
        self.record_button = record_button
        self.status_label = status_label
        self.crosshair_check = crosshair_check
        self.tracking_check = tracking_check
        
        # Configurar conexiones de UI
        if self.connect_button:
            self.connect_button.clicked.connect(self.toggle_camera)
        
        if self.record_button:
            self.record_button.clicked.connect(self.toggle_recording)
            self.record_button.setEnabled(False)  # Inicialmente deshabilitado
        
        # Opciones de visualización
        if self.crosshair_check:
            self.crosshair_check.toggled.connect(self.update_camera_options)
        
        if self.tracking_check:
            self.tracking_check.toggled.connect(self.update_camera_options)
        
        # Estado inicial
        self.update_ui_state()
        
        print("✅ Referencias UI configuradas en CameraController")
    
    def set_siev_camera_index(self, camera_index: Optional[int]):
        """Configurar índice de cámara SIEV"""
        self.siev_camera_index = camera_index
        print(f"📹 Índice de cámara SIEV configurado: {camera_index}")
    
    def toggle_camera(self):
        """Toggle conexión de cámara"""
        if not self.camera_widget:
            print("❌ Widget de cámara no disponible")
            return
        
        if not self.camera_widget.is_connected:
            self._connect_camera()
        else:
            self._disconnect_camera()
    
    def _connect_camera(self):
        """Conectar cámara usando índice SIEV"""
        if self.siev_camera_index is None:
            self._handle_connection_error("No hay índice de cámara SIEV disponible")
            return
        
        print(f"🔌 Conectando cámara en índice {self.siev_camera_index}")
        
        # Intentar inicializar cámara
        if self.camera_widget.init_camera(self.siev_camera_index):
            # Iniciar captura
            if self.camera_widget.start_capture():
                self._handle_connection_success()
            else:
                self._handle_connection_error("No se pudo iniciar captura")
        else:
            self._handle_connection_error(f"No se pudo abrir cámara en índice {self.siev_camera_index}")
    
    def _disconnect_camera(self):
        """Desconectar cámara"""
        print("🔌 Desconectando cámara")
        
        # Detener grabación si está activa
        if self.is_recording:
            self._stop_recording()
        
        # Liberar cámara
        self.camera_widget.release_camera()
        
        # Actualizar UI
        self._update_ui_for_disconnected()
        
        # Emitir señales
        self.camera_connected.emit(False)
        self.camera_status_changed.emit("Cámara desconectada")
    
    def _handle_connection_success(self):
        """Manejar conexión exitosa"""
        print("✅ Cámara conectada exitosamente")
        
        # Actualizar UI
        self._update_ui_for_connected()
        
        # Emitir señales
        self.camera_connected.emit(True)
        self.camera_status_changed.emit("✅ Cámara conectada")
    
    def _handle_connection_error(self, error_msg: str):
        """Manejar error de conexión"""
        print(f"❌ Error de conexión: {error_msg}")
        
        # Actualizar UI
        self._update_ui_for_error()
        
        # Emitir señales
        self.camera_connected.emit(False)
        self.camera_status_changed.emit(f"❌ Error: {error_msg}")
    
    def toggle_recording(self):
        """Toggle grabación"""
        if not self.camera_widget or not self.camera_widget.is_connected:
            print("⚠️ Cámara no conectada, no se puede grabar")
            return
        
        if not self.is_recording:
            self._start_recording()
        else:
            self._stop_recording()
    
    def _start_recording(self):
        """Iniciar grabación"""
        print("🔴 Iniciando grabación")
        
        self.camera_widget.start_recording()
        self.is_recording = True
        
        # Actualizar UI
        if self.record_button:
            self.record_button.setText("⏹️ Detener")
        
        # Emitir señales
        self.recording_state_changed.emit(True)
        self.camera_status_changed.emit("🔴 GRABANDO - Evaluación en curso")
    
    def _stop_recording(self):
        """Detener grabación"""
        print("⏹️ Deteniendo grabación")
        
        self.camera_widget.stop_recording()
        self.is_recording = False
        
        # Actualizar UI
        if self.record_button:
            self.record_button.setText("Grabar")
        
        # Emitir señales
        self.recording_state_changed.emit(False)
        self.camera_status_changed.emit("⏸️ Grabación detenida")
    
    def update_camera_options(self):
        """Actualizar opciones de visualización de cámara"""
        if not self.camera_widget:
            return
        
        # Recopilar estados de checkboxes
        crosshair_enabled = True
        tracking_enabled = True
        
        if self.crosshair_check:
            crosshair_enabled = self.crosshair_check.isChecked()
        
        if self.tracking_check:
            tracking_enabled = self.tracking_check.isChecked()
        
        # Aplicar opciones al widget
        self.camera_widget.set_overlay_options(
            crosshair=crosshair_enabled,
            tracking=tracking_enabled
        )
        
        print(f"🎨 Opciones de cámara actualizadas: Cruz={crosshair_enabled}, Tracking={tracking_enabled}")
    
    def set_overlay_options(self, crosshair: bool = None, tracking: bool = None,
                           eye_detection: bool = None, pupil_detection: bool = None):
        """Configurar opciones de overlay programáticamente"""
        if not self.camera_widget:
            return
        
        self.camera_widget.set_overlay_options(
            crosshair=crosshair,
            tracking=tracking,
            eye_detection=eye_detection,
            pupil_detection=pupil_detection
        )
        
        print("🎨 Opciones de overlay configuradas programáticamente")
    
    def set_processing_enabled(self, enabled: bool):
        """Habilitar/deshabilitar procesamiento de detección"""
        if self.camera_widget:
            self.camera_widget.set_processing_enabled(enabled)
            print(f"🔄 Procesamiento de cámara {'habilitado' if enabled else 'deshabilitado'}")
    
    def _update_ui_for_connected(self):
        """Actualizar UI para estado conectado"""
        if self.connect_button:
            self.connect_button.setText("🔌 Desconectar Cámara")
        
        if self.record_button:
            self.record_button.setEnabled(True)
        
        if self.status_label:
            self.status_label.setText("Estado: Conectado ✅")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
    
    def _update_ui_for_disconnected(self):
        """Actualizar UI para estado desconectado"""
        if self.connect_button:
            self.connect_button.setText("Conectar Cámara")
        
        if self.record_button:
            self.record_button.setEnabled(False)
            self.record_button.setText("Grabar")
        
        if self.status_label:
            self.status_label.setText("Estado: Desconectado")
            self.status_label.setStyleSheet("color: gray;")
        
        # Reset estado de grabación
        self.is_recording = False
    
    def _update_ui_for_error(self):
        """Actualizar UI para estado de error"""
        if self.connect_button:
            self.connect_button.setText("Conectar Cámara")
        
        if self.record_button:
            self.record_button.setEnabled(False)
            self.record_button.setText("Grabar")
        
        if self.status_label:
            self.status_label.setText("Estado: Error ❌")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
        
        # Reset estado de grabación
        self.is_recording = False
    
    def update_ui_state(self):
        """Actualizar estado completo de la UI"""
        if not self.camera_widget:
            self._update_ui_for_disconnected()
            return
        
        if self.camera_widget.is_connected:
            self._update_ui_for_connected()
            
            # Actualizar estado de grabación
            if self.is_recording:
                if self.record_button:
                    self.record_button.setText("⏹️ Detener")
        else:
            self._update_ui_for_disconnected()
    
    # ===== MÉTODOS DE INFORMACIÓN =====
    
    def is_camera_connected(self) -> bool:
        """Verificar si la cámara está conectada"""
        return self.camera_widget.is_connected if self.camera_widget else False
    
    def is_camera_recording(self) -> bool:
        """Verificar si está grabando"""
        return self.is_recording
    
    def get_camera_status(self) -> Dict[str, Any]:
        """Obtener estado completo de la cámara"""
        if not self.camera_widget:
            return {
                'connected': False,
                'recording': False,
                'camera_index': None,
                'error': 'Widget no disponible'
            }
        
        camera_info = self.camera_widget.get_camera_status()
        
        return {
            'connected': self.camera_widget.is_connected,
            'recording': self.is_recording,
            'camera_index': self.siev_camera_index,
            'widget_info': camera_info
        }
    
    def get_camera_widget(self) -> Optional[ModularCameraWidget]:
        """Obtener referencia al widget de cámara"""
        return self.camera_widget
    
    def force_disconnect(self):
        """Forzar desconexión de cámara"""
        print("🔌 Forzando desconexión de cámara")
        
        if self.camera_widget:
            # Detener todo sin emitir señales adicionales
            self.camera_widget.stop_capture()
            self.camera_widget.release_camera()
        
        # Reset estado interno
        self.is_recording = False
        
        # Actualizar UI
        self._update_ui_for_disconnected()
        
        # Emitir señal final
        self.camera_connected.emit(False)
    
    def cleanup(self):
        """Limpieza al cerrar"""
        print("🧹 Limpiando CameraController...")
        
        # Detener grabación
        if self.is_recording:
            self._stop_recording()
        
        # Desconectar cámara
        if self.camera_widget and self.camera_widget.is_connected:
            self.camera_widget.release_camera()
        
        print("✅ CameraController limpiado")