#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Protocol Executor - Ejecutor de protocolos vestibulares
Maneja la ejecución de diferentes tipos de protocolos según behavior_type
"""

import serial
import time
from typing import Dict, Any, Optional, List, Callable
from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtWidgets import QMessageBox, QApplication


class HardwareController:
    """Controlador de hardware ESP8266 para LEDs y comandos"""
    
    def __init__(self, serial_port: Optional[str] = None):
        self.serial_port = serial_port
        self.connection = None
        self.is_connected = False
        
    def connect(self) -> bool:
        """Conectar con ESP8266"""
        if not self.serial_port:
            return False
            
        try:
            self.connection = serial.Serial(
                self.serial_port, 
                115200, 
                timeout=2
            )
            time.sleep(0.1)  # Estabilizar conexión
            
            # Test de comunicación
            if self._test_communication():
                self.is_connected = True
                print(f"✅ Hardware conectado en {self.serial_port}")
                return True
            else:
                self.connection.close()
                self.connection = None
                return False
                
        except Exception as e:
            print(f"❌ Error conectando hardware: {e}")
            self.connection = None
            return False
    
    def disconnect(self):
        """Desconectar hardware"""
        if self.connection:
            try:
                self.connection.close()
            except:
                pass
            finally:
                self.connection = None
                self.is_connected = False
                print("🔌 Hardware desconectado")
    
    def _test_communication(self) -> bool:
        """Probar comunicación con ESP8266"""
        try:
            self.connection.write(b'PING\r\n')
            self.connection.flush()
            time.sleep(0.3)
            
            if self.connection.in_waiting > 0:
                response = self.connection.readline().decode('utf-8', errors='ignore').strip()
                return 'SIEV_ESP_OK_' in response
        except:
            pass
        return False
    
    def send_command(self, command: str) -> bool:
        """Enviar comando al ESP8266"""
        if not self.is_connected or not self.connection:
            print(f"⚠️ Hardware no conectado, comando ignorado: {command}")
            return False
        
        try:
            cmd_bytes = f"{command}\r\n".encode('utf-8')
            self.connection.write(cmd_bytes)
            self.connection.flush()
            print(f"📡 Comando enviado: {command}")
            return True
        except Exception as e:
            print(f"❌ Error enviando comando {command}: {e}")
            return False
    
    def led_on(self, led_target: str) -> bool:
        """Encender LED específico"""
        return self.send_command(f"LED_ON:{led_target.upper()}")
    
    def led_off(self, led_target: str) -> bool:
        """Apagar LED específico"""
        return self.send_command(f"LED_OFF:{led_target.upper()}")


class ProtocolEvent:
    """Evento temporal de protocolo"""
    
    def __init__(self, time: float, event_type: str, description: str, 
                 action: str, **kwargs):
        self.time = time
        self.event_type = event_type
        self.description = description
        self.action = action
        self.params = kwargs
        self.executed = False
    
    def __repr__(self):
        return f"ProtocolEvent({self.time}s, {self.event_type}, {self.action})"


class ProtocolExecutor(QObject):
    """
    Ejecutor de protocolos vestibulares con manejo de eventos temporales,
    control de hardware y coordinación con widgets de UI.
    """
    
    # Señales
    execution_started = Signal(str)  # protocol_name
    execution_finished = Signal(str, bool)  # protocol_name, success
    execution_progress = Signal(float, str)  # progress_percent, status_message
    event_triggered = Signal(dict)  # event_data
    hardware_command_sent = Signal(str)  # command
    execution_error = Signal(str)  # error_message
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Estado de ejecución
        self.current_protocol = None
        self.is_executing = False
        self.start_time = None
        self.events = []
        self.executed_events = []
        
        # Control de hardware
        self.hardware_controller = None
        self.hardware_enabled = False
        
        # Timers
        self.execution_timer = QTimer()
        self.execution_timer.timeout.connect(self._check_events)
        
        # Referencias a widgets (se configuran externamente)
        self.camera_widget = None
        self.graph_widget = None
        
        print("✅ ProtocolExecutor inicializado")
    
    def set_hardware_port(self, serial_port: str) -> bool:
        """Configurar puerto de hardware ESP8266"""
        self.hardware_controller = HardwareController(serial_port)
        self.hardware_enabled = self.hardware_controller.connect()
        return self.hardware_enabled
    
    def set_camera_widget(self, camera_widget):
        """Configurar referencia al widget de cámara"""
        self.camera_widget = camera_widget
    
    def set_graph_widget(self, graph_widget):
        """Configurar referencia al widget de gráfico"""
        self.graph_widget = graph_widget
    
    def execute_protocol(self, protocol_data: Dict[str, Any]) -> bool:
        """
        Ejecutar protocolo según su behavior_type.
        
        Args:
            protocol_data: Datos completos del protocolo desde JSON
            
        Returns:
            bool: True si la ejecución se inició correctamente
        """
        if self.is_executing:
            print("⚠️ Ya hay un protocolo en ejecución")
            return False
        
        protocol_name = protocol_data.get("name", "Sin nombre")
        behavior_type = protocol_data.get("behavior_type", "recording")
        
        print(f"🚀 Iniciando ejecución: {protocol_name} ({behavior_type})")
        
        # Configurar estado
        self.current_protocol = protocol_data
        self.is_executing = True
        self.start_time = time.time()
        self.events = []
        self.executed_events = []
        
        # Emitir señal de inicio
        self.execution_started.emit(protocol_name)
        
        try:
            # Ejecutar según tipo
            if behavior_type == "recording":
                return self._execute_recording_protocol()
            elif behavior_type == "window":
                return self._execute_window_protocol()
            elif behavior_type == "caloric":
                return self._execute_caloric_protocol()
            else:
                raise ValueError(f"Behavior type no soportado: {behavior_type}")
                
        except Exception as e:
            error_msg = f"Error ejecutando protocolo {protocol_name}: {e}"
            print(f"❌ {error_msg}")
            self.execution_error.emit(error_msg)
            self._finish_execution(False)
            return False
    
    def _execute_recording_protocol(self) -> bool:
        """Ejecutar protocolo de grabación libre"""
        protocol = self.current_protocol
        protocol_name = protocol["name"]
        
        print(f"🎬 Ejecutando protocolo de grabación: {protocol_name}")
        
        # Configurar herramientas de gráfico
        self._configure_graph_tools(protocol.get("graph_tools", {}))
        
        # Configurar UI de cámara
        self._configure_camera_ui(protocol.get("ui_settings", {}))
        
        # Mostrar información al usuario
        duration_info = ""
        if protocol.get("duration_max"):
            duration_info = f" (máx. {protocol['duration_max']}s)"
        
        self.execution_progress.emit(0, f"📹 {protocol_name} - Grabación manual{duration_info}")
        
        # Para protocolos de grabación, la ejecución es inmediata
        # El control lo tiene el usuario con los botones de grabación
        self._finish_execution(True)
        return True
    
    def _execute_window_protocol(self) -> bool:
        """Ejecutar protocolo que requiere ventana nueva"""
        protocol = self.current_protocol
        protocol_name = protocol["name"]
        window_type = protocol.get("protocol", {}).get("window_type", "unknown")
        
        print(f"🪟 Ejecutando protocolo de ventana: {protocol_name} ({window_type})")
        
        # TODO: Implementar ventanas específicas
        self.execution_progress.emit(50, f"Abriendo ventana para {protocol_name}")
        
        # Por ahora, simular ejecución con información
        self._show_window_protocol_info(protocol, window_type)
        
        # Simular finalización exitosa
        QTimer.singleShot(1000, lambda: self._finish_execution(True))
        return True
    
    def _execute_caloric_protocol(self) -> bool:
        """Ejecutar protocolo calórico con eventos temporales"""
        protocol = self.current_protocol
        protocol_name = protocol["name"]
        
        print(f"🌡️ Ejecutando protocolo calórico: {protocol_name}")
        
        # Configurar herramientas de gráfico
        self._configure_graph_tools(protocol.get("graph_tools", {}))
        
        # Configurar UI de cámara
        self._configure_camera_ui(protocol.get("ui_settings", {}))
        
        # Preparar eventos temporales
        self._prepare_caloric_events(protocol)
        
        # Verificar control de hardware si es necesario
        hardware_control = protocol.get("hardware_control", {})
        if hardware_control.get("led_control", False) and not self.hardware_enabled:
            # Preguntar si continuar sin hardware
            if not self._confirm_execution_without_hardware(protocol_name):
                self._finish_execution(False)
                return False
        
        # Iniciar timer de ejecución
        self.execution_timer.start(100)  # Verificar eventos cada 100ms
        
        self.execution_progress.emit(0, f"🌡️ {protocol_name} - Iniciando protocolo calórico")
        return True
    
    def _prepare_caloric_events(self, protocol: Dict[str, Any]):
        """Preparar eventos temporales para protocolo calórico"""
        protocol_events = protocol.get("protocol", {}).get("events", [])
        
        for event_data in protocol_events:
            event = ProtocolEvent(
                time=event_data["time"],
                event_type=event_data["type"],
                description=event_data["description"],
                action=event_data["action"],
                **{k: v for k, v in event_data.items() 
                   if k not in ["time", "type", "description", "action"]}
            )
            self.events.append(event)
        
        # Ordenar eventos por tiempo
        self.events.sort(key=lambda e: e.time)
        
        print(f"📅 {len(self.events)} eventos programados para protocolo calórico")
        for event in self.events:
            print(f"  - {event.time}s: {event.description}")
    
    def _check_events(self):
        """Verificar y ejecutar eventos temporales"""
        if not self.is_executing or not self.start_time:
            return
        
        current_time = time.time() - self.start_time
        
        # Buscar eventos listos para ejecutar
        for event in self.events:
            if not event.executed and current_time >= event.time:
                self._execute_event(event)
                event.executed = True
                self.executed_events.append(event)
        
        # Calcular progreso
        duration_max = self.current_protocol.get("duration_max", 300)
        progress = min((current_time / duration_max) * 100, 100)
        
        # Emitir progreso
        self.execution_progress.emit(
            progress, 
            f"⏱️ {current_time:.1f}s / {duration_max}s"
        )
        
        # Verificar si terminó el protocolo
        if current_time >= duration_max:
            self._finish_execution(True)
    
    def _execute_event(self, event: ProtocolEvent):
        """Ejecutar evento específico"""
        print(f"⚡ Ejecutando evento: {event}")
        
        # Emitir señal de evento
        event_data = {
            "time": event.time,
            "type": event.event_type,
            "description": event.description,
            "action": event.action,
            "params": event.params
        }
        self.event_triggered.emit(event_data)
        
        # Ejecutar acción según tipo
        if event.action == "activate_torok_tool":
            self._activate_torok_tool()
        
        elif event.action == "led_on":
            led_target = event.params.get("led_target", "LEFT")
            self._execute_led_command(True, led_target)
        
        elif event.action == "led_off":
            led_target = event.params.get("led_target", "LEFT")
            self._execute_led_command(False, led_target)
        
        else:
            print(f"⚠️ Acción no reconocida: {event.action}")
    
    def _activate_torok_tool(self):
        """Activar herramienta Torok en el gráfico"""
        if self.graph_widget and hasattr(self.graph_widget, 'activate_torok_tool'):
            self.graph_widget.activate_torok_tool()
            print("🎯 Herramienta Torok activada")
    
    def _execute_led_command(self, turn_on: bool, led_target: str):
        """Ejecutar comando de LED"""
        if self.hardware_controller and self.hardware_enabled:
            if turn_on:
                success = self.hardware_controller.led_on(led_target)
                action = "encendido"
            else:
                success = self.hardware_controller.led_off(led_target)
                action = "apagado"
            
            if success:
                self.hardware_command_sent.emit(f"LED_{led_target}_{action.upper()}")
                print(f"💡 LED {led_target} {action}")
            else:
                print(f"❌ Error en comando LED {led_target}")
        else:
            print(f"⚠️ Hardware no disponible, LED {led_target} {'encendido' if turn_on else 'apagado'} simulado")
    
    def _configure_graph_tools(self, graph_tools: Dict[str, bool]):
        """Configurar herramientas de gráfico según protocolo"""
        if not self.graph_widget:
            return
        
        # Activar herramientas según configuración
        torok_enabled = graph_tools.get("torok_tool", False)
        if torok_enabled and hasattr(self.graph_widget, 'activate_torok_tool'):
            # No activar inmediatamente, esperar al evento temporal
            pass
        
        peak_editing = graph_tools.get("peak_editing", False)
        if peak_editing and hasattr(self.graph_widget, 'activate_peak_editing'):
            self.graph_widget.activate_peak_editing()
        
        print(f"🔧 Herramientas de gráfico configuradas: Torok={torok_enabled}, PeakEdit={peak_editing}")
    
    def _configure_camera_ui(self, ui_settings: Dict[str, bool]):
        """Configurar UI de cámara según protocolo"""
        if not self.camera_widget:
            return
        
        if hasattr(self.camera_widget, 'set_overlay_options'):
            self.camera_widget.set_overlay_options(
                crosshair=ui_settings.get("show_crosshair", True),
                tracking=ui_settings.get("show_tracking_circles", True),
                eye_detection=ui_settings.get("show_eye_detection", True),
                pupil_detection=ui_settings.get("show_pupil_detection", True)
            )
        
        print(f"📹 UI de cámara configurada según protocolo")
    
    def _show_window_protocol_info(self, protocol: Dict[str, Any], window_type: str):
        """Mostrar información de protocolo de ventana (placeholder)"""
        protocol_config = protocol.get("protocol", {})
        
        if window_type == "saccades":
            info = (
                f"Configuración de Sacadas:\n"
                f"• Amplitud: ±{protocol_config.get('target_amplitude', 20)}°\n"
                f"• Repeticiones: {protocol_config.get('repetitions', 10)}\n"
                f"• Direcciones: {', '.join(protocol_config.get('directions', []))}"
            )
        
        elif window_type == "smooth_pursuit":
            info = (
                f"Configuración de Seguimiento Lento:\n"
                f"• Frecuencia: {protocol_config.get('frequency', 0.4)} Hz\n"
                f"• Amplitud: ±{protocol_config.get('amplitude', 20)}°\n"
                f"• Ciclos: {protocol_config.get('cycles', 5)}"
            )
        
        elif window_type == "optokinetic":
            info = (
                f"Configuración Optoquinética:\n"
                f"• Velocidades: {protocol_config.get('velocities', [])}°/s\n"
                f"• Direcciones: {', '.join(protocol_config.get('directions', []))}\n"
                f"• Duración por dirección: {protocol_config.get('duration_per_direction', 30)}s"
            )
        
        else:
            info = f"Tipo de ventana: {window_type}\n[Implementación en desarrollo]"
        
        # TODO: Aquí se abriría la ventana específica
        print(f"🪟 {info}")
    
    def _confirm_execution_without_hardware(self, protocol_name: str) -> bool:
        """Confirmar ejecución sin hardware disponible"""
        reply = QMessageBox.question(
            None,
            "Hardware SIEV No Conectado",
            f"El protocolo '{protocol_name}' requiere control de LED, "
            f"pero el hardware SIEV no está conectado.\n\n"
            f"¿Desea continuar sin control de hardware?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        return reply == QMessageBox.Yes
    
    def _finish_execution(self, success: bool):
        """Finalizar ejecución del protocolo"""
        if not self.is_executing:
            return
        
        protocol_name = self.current_protocol.get("name", "Sin nombre") if self.current_protocol else "Unknown"
        
        # Detener timer
        if self.execution_timer.isActive():
            self.execution_timer.stop()
        
        # Limpiar estado
        self.is_executing = False
        execution_time = time.time() - self.start_time if self.start_time else 0
        
        # Apagar LEDs si estaban encendidos
        if self.hardware_controller and self.hardware_enabled:
            self.hardware_controller.led_off("LEFT")
            self.hardware_controller.led_off("RIGHT")
        
        # Emitir señal de finalización
        self.execution_finished.emit(protocol_name, success)
        
        if success:
            self.execution_progress.emit(100, f"✅ {protocol_name} completado ({execution_time:.1f}s)")
            print(f"✅ Protocolo {protocol_name} completado exitosamente")
        else:
            self.execution_progress.emit(0, f"❌ {protocol_name} cancelado")
            print(f"❌ Protocolo {protocol_name} cancelado o falló")
        
        # Limpiar referencias
        self.current_protocol = None
        self.start_time = None
        self.events = []
        self.executed_events = []
    
    def stop_execution(self):
        """Detener ejecución actual"""
        if self.is_executing:
            print("🛑 Deteniendo ejecución de protocolo")
            self._finish_execution(False)
    
    def is_protocol_executing(self) -> bool:
        """Verificar si hay un protocolo ejecutándose"""
        return self.is_executing
    
    def get_execution_status(self) -> Dict[str, Any]:
        """Obtener estado de ejecución actual"""
        if not self.is_executing:
            return {"executing": False}
        
        current_time = time.time() - self.start_time if self.start_time else 0
        duration_max = self.current_protocol.get("duration_max", 300) if self.current_protocol else 300
        progress = min((current_time / duration_max) * 100, 100)
        
        return {
            "executing": True,
            "protocol_name": self.current_protocol.get("name", "Unknown") if self.current_protocol else "Unknown",
            "current_time": current_time,
            "duration_max": duration_max,
            "progress_percent": progress,
            "events_total": len(self.events),
            "events_executed": len(self.executed_events),
            "hardware_enabled": self.hardware_enabled
        }
    
    def cleanup(self):
        """Limpieza al cerrar"""
        print("🧹 Limpiando ProtocolExecutor")
        
        # Detener ejecución si está activa
        if self.is_executing:
            self.stop_execution()
        
        # Desconectar hardware
        if self.hardware_controller:
            self.hardware_controller.disconnect()
        
        # Detener timers
        if self.execution_timer.isActive():
            self.execution_timer.stop()