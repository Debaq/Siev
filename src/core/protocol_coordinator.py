#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Protocol Coordinator - Coordinador de protocolos vestibulares
Maneja la coordinación entre ProtocolManager, ProtocolExecutor y UI
"""

from typing import Dict, Any, Optional
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QWidget

from utils.protocol_manager import ProtocolManager
from utils.protocol_executor import ProtocolExecutor
from utils.dialog_utils import (show_info, show_success, show_warning, show_error, 
                               ask_confirmation, DialogUtils)


class ProtocolCoordinator(QObject):
    """
    Coordinador central para el sistema de protocolos vestibulares.
    Maneja la comunicación entre ProtocolManager, ProtocolExecutor y la UI.
    """
    
    # Señales hacia la UI principal
    status_message_changed = Signal(str)  # Mensajes para status bar
    execution_progress_updated = Signal(float, str)  # progreso, mensaje
    protocol_execution_state_changed = Signal(bool)  # ejecutando/no ejecutando
    
    def __init__(self, protocol_manager: ProtocolManager, 
                 protocol_executor: ProtocolExecutor, parent=None):
        super().__init__(parent)
        
        # Referencias a módulos
        self.protocol_manager = protocol_manager
        self.protocol_executor = protocol_executor
        
        # Estado del coordinador
        self.current_protocol_name = None
        self.progress_dialog = None
        
        # Configurar conexiones
        self.setup_protocol_connections()
        
        print("✅ ProtocolCoordinator inicializado")
    
    def setup_protocol_connections(self):
        """Configurar conexiones con ProtocolManager y ProtocolExecutor"""
        
        # Conexiones del ProtocolManager
        if self.protocol_manager:
            self.protocol_manager.protocols_loaded.connect(self.on_protocols_loaded)
            self.protocol_manager.validation_error.connect(self.on_validation_error)
        
        # Conexiones del ProtocolExecutor
        if self.protocol_executor:
            self.protocol_executor.execution_started.connect(self.on_execution_started)
            self.protocol_executor.execution_finished.connect(self.on_execution_finished)
            self.protocol_executor.execution_progress.connect(self.on_execution_progress)
            self.protocol_executor.event_triggered.connect(self.on_event_triggered)
            self.protocol_executor.hardware_command_sent.connect(self.on_hardware_command)
            self.protocol_executor.execution_error.connect(self.on_execution_error)
        
        print("✅ Conexiones de protocolos configuradas")
    
    # ===== MANEJADORES DE PROTOCOLMANAGER =====
    
    def on_protocols_loaded(self, count: int):
        """Manejar carga de protocolos"""
        message = f"✅ {count} protocolos cargados correctamente"
        self.status_message_changed.emit(message)
        print(f"📋 {message}")
    
    def on_validation_error(self, error_msg: str):
        """Manejar error de validación"""
        show_error("Error de Validación", error_msg, self.parent())
        self.status_message_changed.emit(f"❌ Error de validación: {error_msg}")
    
    # ===== MANEJADORES DE PROTOCOLEXECUTOR =====
    
    def on_execution_started(self, protocol_name: str):
        """Manejar inicio de ejecución"""
        self.current_protocol_name = protocol_name
        message = f"🚀 Ejecutando: {protocol_name}"
        
        self.status_message_changed.emit(message)
        self.protocol_execution_state_changed.emit(True)
        
        # Crear diálogo de progreso si es protocolo con duración
        status = self.protocol_executor.get_execution_status()
        if status.get("duration_max", 0) > 0:
            self.progress_dialog = DialogUtils.show_execution_progress(
                protocol_name, 
                status["duration_max"], 
                self.parent()
            )
            # Conectar botón de detener
            if self.progress_dialog:
                self.progress_dialog.stop_button.clicked.connect(self.stop_protocol_execution)
        
        print(f"🚀 Ejecución iniciada: {protocol_name}")
    
    def on_execution_finished(self, protocol_name: str, success: bool):
        """Manejar finalización de ejecución"""
        self.current_protocol_name = None
        self.protocol_execution_state_changed.emit(False)
        
        if success:
            message = f"✅ {protocol_name} completado exitosamente"
            self.status_message_changed.emit(message)
            show_success("Protocolo Completado", 
                        f"El protocolo '{protocol_name}' se ejecutó correctamente", 
                        self.parent())
        else:
            message = f"❌ {protocol_name} cancelado o falló"
            self.status_message_changed.emit(message)
        
        # Cerrar diálogo de progreso si existe
        if self.progress_dialog:
            self.progress_dialog.on_execution_finished(success)
            self.progress_dialog = None
        
        print(f"🏁 Ejecución finalizada: {protocol_name} - {'Éxito' if success else 'Fallo'}")
    
    def on_execution_progress(self, progress_percent: float, status_message: str):
        """Manejar progreso de ejecución"""
        self.status_message_changed.emit(status_message)
        self.execution_progress_updated.emit(progress_percent, status_message)
        
        # Actualizar diálogo de progreso si existe
        if self.progress_dialog:
            self.progress_dialog.update_progress(progress_percent, status_message)
    
    def on_event_triggered(self, event_data: Dict[str, Any]):
        """Manejar evento temporal disparado"""
        event_desc = event_data.get("description", "Evento")
        message = f"⚡ {event_desc}"
        self.status_message_changed.emit(message)
        print(f"📅 Evento ejecutado: {event_data}")
    
    def on_hardware_command(self, command: str):
        """Manejar comando de hardware enviado"""
        message = f"📡 Hardware: {command}"
        self.status_message_changed.emit(message)
        print(f"🔧 Comando hardware: {command}")
    
    def on_execution_error(self, error_msg: str):
        """Manejar error de ejecución"""
        show_error("Error de Ejecución", error_msg, self.parent())
        self.status_message_changed.emit(f"❌ Error: {error_msg}")
        
        # Detener ejecución si hay error
        if self.protocol_executor.is_protocol_executing():
            self.protocol_executor.stop_execution()
    
    # ===== MÉTODOS DE COORDINACIÓN =====
    
    def execute_protocol(self, protocol_data: Dict[str, Any], 
                        siev_serial_port: Optional[str] = None) -> bool:
        """
        Coordinar ejecución de protocolo con verificaciones previas.
        
        Args:
            protocol_data: Datos del protocolo a ejecutar
            siev_serial_port: Puerto serial SIEV (opcional)
            
        Returns:
            bool: True si se inició correctamente
        """
        protocol_name = protocol_data.get("name", "Sin nombre")
        
        # Verificar si ya hay ejecución en curso
        if self.protocol_executor.is_protocol_executing():
            if ask_confirmation(
                "Protocolo en Ejecución",
                "Ya hay un protocolo ejecutándose. ¿Desea detenerlo y ejecutar el nuevo?",
                self.parent()
            ):
                self.protocol_executor.stop_execution()
            else:
                return False
        
        # Configurar hardware si es necesario
        hardware_control = protocol_data.get("hardware_control", {})
        if hardware_control.get("led_control", False):
            if siev_serial_port:
                # Configurar puerto hardware en executor
                self.protocol_executor.set_hardware_port(siev_serial_port)
                print(f"🔧 Hardware configurado: {siev_serial_port}")
            else:
                # Preguntar si continuar sin hardware
                if not ask_confirmation(
                    "Hardware No Disponible",
                    f"El protocolo '{protocol_name}' requiere control de LED, "
                    f"pero el hardware SIEV no está conectado.\n\n"
                    f"¿Desea continuar sin control de hardware?",
                    self.parent()
                ):
                    return False
        
        # Ejecutar protocolo
        success = self.protocol_executor.execute_protocol(protocol_data)
        if not success:
            show_error("Error de Ejecución", 
                      "No se pudo iniciar la ejecución del protocolo", 
                      self.parent())
        
        return success
    
    def stop_protocol_execution(self):
        """Detener ejecución de protocolo con confirmación"""
        if not self.protocol_executor.is_protocol_executing():
            return
        
        if ask_confirmation(
            "Detener Protocolo",
            "¿Está seguro de que desea detener la ejecución del protocolo?",
            self.parent()
        ):
            self.protocol_executor.stop_execution()
            print("🛑 Ejecución detenida por usuario")
    
    def show_protocol_editor(self, protocol_key: str) -> bool:
        """
        Mostrar editor de protocolo.
        
        Args:
            protocol_key: Clave del protocolo a editar
            
        Returns:
            bool: True si se guardaron cambios
        """
        protocol = self.protocol_manager.get_protocol(protocol_key)
        if not protocol:
            show_error("Error", f"No se encontró el protocolo: {protocol_key}", 
                      self.parent())
            return False
        
        # Importar el diálogo de configuración
        try:
            from widgets.protocol_config_dialog import show_protocol_config_dialog
        except ImportError:
            show_error("Error", 
                      "No se pudo cargar el editor de protocolos.\n"
                      "Verifique que el archivo protocol_config_dialog.py esté disponible.",
                      self.parent())
            return False
        
        # Obtener esquema de validación
        validation_schema = self.protocol_manager.get_validation_schema()
        
        # Mostrar diálogo de configuración
        updated_protocol = show_protocol_config_dialog(
            protocol_key,
            protocol,
            validation_schema,
            self.parent()
        )
        
        # Si se guardaron cambios, actualizar
        if updated_protocol:
            # Actualizar protocolo en el manager
            success = self.protocol_manager.update_protocol(protocol_key, updated_protocol)
            
            if success:
                # Guardar cambios
                self.protocol_manager.save_protocols()
                
                message = f"Protocolo actualizado: {updated_protocol['name']}"
                self.status_message_changed.emit(message)
                
                show_success("Protocolo Actualizado", 
                           f"El protocolo '{updated_protocol['name']}' se guardó correctamente",
                           self.parent())
                return True
            else:
                show_error("Error", "No se pudo actualizar el protocolo", 
                          self.parent())
        
        return False
    
    def copy_protocol(self, protocol_key: str, new_name: str) -> Optional[str]:
        """
        Crear copia de protocolo.
        
        Args:
            protocol_key: Protocolo origen
            new_name: Nombre para la copia
            
        Returns:
            str: Clave del nuevo protocolo o None si falló
        """
        new_key = self.protocol_manager.copy_protocol(protocol_key, new_name)
        
        if new_key:
            self.protocol_manager.save_protocols()
            message = f"Protocolo copiado: {new_name}"
            self.status_message_changed.emit(message)
            print(f"📋 {message}")
            return new_key
        else:
            show_error("Error", "No se pudo copiar el protocolo", self.parent())
            return None
    
    def delete_protocol(self, protocol_key: str, protocol_name: str) -> bool:
        """
        Eliminar protocolo con confirmación.
        
        Args:
            protocol_key: Clave del protocolo
            protocol_name: Nombre del protocolo
            
        Returns:
            bool: True si se eliminó
        """
        if self.protocol_manager.is_default_protocol(protocol_key):
            show_warning("No Permitido", 
                        "No se pueden eliminar protocolos estándar.",
                        self.parent())
            return False
        
        # Confirmar eliminación
        if not ask_confirmation(
            "Confirmar Eliminación",
            f"¿Está seguro de que desea eliminar el protocolo '{protocol_name}'?\n\n"
            f"Esta acción no se puede deshacer.",
            self.parent()
        ):
            return False
        
        success = self.protocol_manager.delete_protocol(protocol_key)
        
        if success:
            self.protocol_manager.save_protocols()
            message = "Protocolo eliminado correctamente"
            self.status_message_changed.emit(message)
            print(f"🗑️ Protocolo eliminado: {protocol_name}")
            return True
        else:
            show_error("Error", "No se pudo eliminar el protocolo", self.parent())
            return False
    
    # ===== MÉTODOS DE INFORMACIÓN =====
    
    def get_execution_status(self) -> Dict[str, Any]:
        """Obtener estado de ejecución actual"""
        return self.protocol_executor.get_execution_status()
    
    def is_protocol_executing(self) -> bool:
        """Verificar si hay un protocolo ejecutándose"""
        return self.protocol_executor.is_protocol_executing()
    
    def get_current_protocol_name(self) -> Optional[str]:
        """Obtener nombre del protocolo actual"""
        return self.current_protocol_name
    
    def get_protocols_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas de protocolos"""
        return self.protocol_manager.get_statistics()
    
    def refresh_protocols(self) -> bool:
        """Recargar protocolos desde archivo"""
        success = self.protocol_manager.load_protocols()
        if success:
            self.status_message_changed.emit("Protocolos recargados")
        return success
    
    # ===== MÉTODOS DE EXPORTACIÓN/IMPORTACIÓN =====
    
    def export_protocols(self, export_path: str, 
                        include_defaults: bool = True,
                        include_presets: bool = True) -> bool:
        """Exportar protocolos a archivo"""
        success = self.protocol_manager.export_protocols(
            export_path, include_defaults, include_presets
        )
        
        if success:
            message = f"Protocolos exportados a: {export_path}"
            self.status_message_changed.emit(message)
            show_success("Exportación Exitosa", message, self.parent())
        else:
            show_error("Error de Exportación", 
                      "No se pudieron exportar los protocolos", self.parent())
        
        return success
    
    def import_protocols(self, import_path: str, 
                        overwrite_existing: bool = False) -> tuple[bool, int]:
        """Importar protocolos desde archivo"""
        success, count = self.protocol_manager.import_protocols(
            import_path, overwrite_existing
        )
        
        if success:
            self.protocol_manager.save_protocols()
            message = f"{count} protocolos importados correctamente"
            self.status_message_changed.emit(message)
            show_success("Importación Exitosa", message, self.parent())
        else:
            show_error("Error de Importación", 
                      "No se pudieron importar los protocolos", self.parent())
        
        return success, count
    
    def cleanup(self):
        """Limpieza al cerrar"""
        print("🧹 Limpiando ProtocolCoordinator...")
        
        # Detener ejecución si está activa
        if self.protocol_executor.is_protocol_executing():
            self.protocol_executor.stop_execution()
        
        # Cerrar diálogo de progreso
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        
        # Guardar protocolos
        if self.protocol_manager:
            self.protocol_manager.save_protocols()
        
        print("✅ ProtocolCoordinator limpiado")