#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIEV - Sistema Integrado de Evaluación Vestibular (Main Simplificado)
Arquitectura modular con separación de responsabilidades
"""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

# Imports de módulos core
from core.main_window_base import MainWindowBase
from core.siev_manager import SievManager
from core.protocol_coordinator import ProtocolCoordinator

# Imports de controladores
from controllers.camera_controller import CameraController
from controllers.graph_controller import GraphController
from controllers.menu_actions import MenuActions

# Imports de utilidades
from utils.icon_utils import get_icon, IconColors
from utils.dialog_utils import ask_confirmation


class SIEVMainWindow(MainWindowBase):
    """
    Ventana principal SIEV con arquitectura modular.
    Hereda de MainWindowBase y coordina todos los controladores especializados.
    """
    
    def __init__(self, ui_file_path="main_window.ui"):
        # Inicializar base (carga UI, widgets, sistema modular)
        super().__init__(ui_file_path)
        
        # Controladores especializados
        self.siev_manager = None
        self.camera_controller = None
        self.graph_controller = None
        self.menu_actions = None
        
        # Inicializar controladores
        self.init_specialized_controllers()
        
        # Configurar conexiones entre módulos
        self.setup_controller_connections()
        
        # Configurar menús
        self.setup_application_menu()
        
        # Iniciar detección SIEV
        self.start_siev_detection()
        
        print("✅ SIEVMainWindow completamente inicializado")
    
    def init_specialized_controllers(self):
        """Inicializar controladores especializados"""
        
        # SievManager - Gestión de hardware SIEV
        self.siev_manager = SievManager(self)
        self.siev_manager.set_ui_references(
            main_button=self.ui.btn_conectar_camara,
            status_label=self.ui.statusbar,
            patient_info_label=getattr(self.ui, 'lbl_patient_info', None)
        )
        
        # CameraController - Control de cámara
        if self.camera_widget:
            self.camera_controller = CameraController(self.camera_widget, self)
            self.camera_controller.set_ui_references(
                connect_button=None,  # El botón principal lo maneja SievManager
                record_button=getattr(self.ui, 'btn_grabar', None),
                status_label=getattr(self.ui, 'lbl_estado_camara', None),
                crosshair_check=getattr(self.ui, 'check_crosshair', None),
                tracking_check=getattr(self.ui, 'check_tracking', None)
            )
        
        # GraphController - Control de gráficos
        if self.vcl_graph_widget:
            self.graph_controller = GraphController(self.vcl_graph_widget, self)
            self.graph_controller.set_ui_references(
                btn_torok=self.btn_torok,
                btn_peak_edit=self.btn_peak_edit,
                btn_tiempo_fijacion=self.btn_tiempo_fijacion,
                btn_zoom=self.btn_zoom,
                btn_crosshair=self.btn_crosshair_graph,
                btn_peak_detection=self.btn_peak_detection
            )
        
        # MenuActions - Acciones de menú
        self.menu_actions = MenuActions(self.protocol_manager, self)
        
        print("✅ Controladores especializados inicializados")
    
    def setup_controller_connections(self):
        """Configurar conexiones entre controladores y coordinadores"""
        
        # Conexiones del SievManager
        if self.siev_manager:
            self.siev_manager.siev_connected.connect(self.on_siev_connection_changed)
            self.siev_manager.siev_status_changed.connect(self.update_status_message)
            self.siev_manager.camera_mode_changed.connect(self.on_camera_mode_requested)
        
        # Conexiones del CameraController
        if self.camera_controller:
            self.camera_controller.camera_connected.connect(self.on_camera_connection_changed)
            self.camera_controller.recording_state_changed.connect(self.on_recording_state_changed)
            self.camera_controller.camera_status_changed.connect(self.update_status_message)
        
        # Conexiones del GraphController
        if self.graph_controller:
            self.graph_controller.tool_state_changed.connect(self.on_graph_tool_changed)
            self.graph_controller.point_added.connect(self.on_graph_point_added)
            self.graph_controller.point_removed.connect(self.on_graph_point_removed)
            self.graph_controller.torok_region_changed.connect(self.on_torok_region_changed)
            self.graph_controller.graph_status_changed.connect(self.update_status_message)
        
        # Conexiones del ProtocolCoordinator
        if self.protocol_executor:
            # Conectar señales del coordinator
            self.protocol_manager.protocols_loaded.connect(self.on_protocols_loaded)
            self.protocol_executor.execution_started.connect(self.on_protocol_execution_started)
            self.protocol_executor.execution_finished.connect(self.on_protocol_execution_finished)
            self.protocol_executor.execution_progress.connect(self.on_protocol_execution_progress)
            self.protocol_executor.event_triggered.connect(self.on_protocol_event_triggered)
            self.protocol_executor.hardware_command_sent.connect(self.on_hardware_command_sent)
            self.protocol_executor.execution_error.connect(self.on_protocol_execution_error)
        
        # Conexiones del ProtocolWidget
        if self.protocol_widget:
            self.protocol_widget.protocol_selected.connect(self.on_protocol_selected)
            self.protocol_widget.protocol_execution_requested.connect(self.on_protocol_execution_requested)
            self.protocol_widget.protocol_changed.connect(self.update_status_message)
        
        # Conexiones del MenuActions
        if self.menu_actions:
            self.menu_actions.status_message_changed.connect(self.update_status_message)
            self.menu_actions.protocols_refreshed.connect(self.on_protocols_refreshed)
        
        print("✅ Conexiones entre controladores configuradas")
    
    def setup_application_menu(self):
        """Configurar menú de la aplicación"""
        if not self.ui or not hasattr(self.ui, 'menubar'):
            return
        
        menubar = self.ui.menubar
        
        # Menú Sistema
        system_menu = menubar.addMenu("Sistema")
        
        info_action = system_menu.addAction("Información del Sistema")
        info_action.setIcon(get_icon("info", 16, IconColors.BLUE))
        info_action.triggered.connect(self.menu_actions.show_system_info)
        
        hardware_action = system_menu.addAction("Diagnósticos de Hardware")
        hardware_action.setIcon(get_icon("cpu", 16, IconColors.GREEN))
        hardware_action.triggered.connect(self.menu_actions.show_hardware_diagnostics)
        
        system_menu.addSeparator()
        
        exit_action = system_menu.addAction("Salir")
        exit_action.setIcon(get_icon("x", 16, IconColors.RED))
        exit_action.triggered.connect(self.close)
        
        # Menú Protocolos
        protocols_menu = menubar.addMenu("Protocolos")
        
        export_action = protocols_menu.addAction("Exportar Protocolos...")
        export_action.setIcon(get_icon("download", 16, IconColors.GREEN))
        export_action.triggered.connect(self.menu_actions.export_protocols)
        
        import_action = protocols_menu.addAction("Importar Protocolos...")
        import_action.setIcon(get_icon("upload", 16, IconColors.BLUE))
        import_action.triggered.connect(self.menu_actions.import_protocols)
        
        backup_action = protocols_menu.addAction("Crear Respaldo...")
        backup_action.setIcon(get_icon("save", 16, IconColors.ORANGE))
        backup_action.triggered.connect(self.menu_actions.backup_protocols)
        
        protocols_menu.addSeparator()
        
        stats_action = protocols_menu.addAction("Estadísticas")
        stats_action.setIcon(get_icon("bar-chart", 16, IconColors.ORANGE))
        stats_action.triggered.connect(self.menu_actions.show_protocol_statistics)
        
        validate_action = protocols_menu.addAction("Validar Todos")
        validate_action.setIcon(get_icon("check-circle", 16, IconColors.GREEN))
        validate_action.triggered.connect(self.menu_actions.validate_all_protocols)
        
        refresh_action = protocols_menu.addAction("Recargar desde Archivo")
        refresh_action.setIcon(get_icon("rotate-cw", 16, IconColors.BLUE))
        refresh_action.triggered.connect(self.menu_actions.refresh_protocols)
        
        protocols_menu.addSeparator()
        
        reset_action = protocols_menu.addAction("Resetear a Valores por Defecto")
        reset_action.setIcon(get_icon("rotate-ccw", 16, IconColors.RED))
        reset_action.triggered.connect(self.menu_actions.reset_to_defaults)
        
        # Menú Ayuda
        help_menu = menubar.addMenu("Ayuda")
        
        about_action = help_menu.addAction("Acerca de SIEV")
        about_action.setIcon(get_icon("help-circle", 16, IconColors.BLUE))
        about_action.triggered.connect(self.menu_actions.show_about_dialog)
        
        print("✅ Menús de aplicación configurados")
    
    def start_siev_detection(self):
        """Iniciar detección automática de SIEV"""
        if self.siev_manager:
            self.siev_manager.detect_siev_on_startup()
    
    # ===== MANEJADORES DE EVENTOS DE SIEV =====
    
    def on_siev_connection_changed(self, connected: bool):
        """Manejar cambio de conexión SIEV"""
        print(f"📡 SIEV {'conectado' if connected else 'desconectado'}")
        
        # Actualizar estado en MenuActions
        if self.menu_actions:
            self.menu_actions.update_system_status(siev_connected=connected)
        
        # Configurar cámara si SIEV está conectado
        if connected and self.camera_controller and self.siev_manager:
            camera_index = self.siev_manager.get_camera_index()
            self.camera_controller.set_siev_camera_index(camera_index)
    
    def on_camera_mode_requested(self, toggle_camera: bool):
        """Manejar solicitud de toggle de cámara desde SievManager"""
        if self.camera_controller:
            self.camera_controller.toggle_camera()
    
    # ===== MANEJADORES DE EVENTOS DE CÁMARA =====
    
    def on_camera_connection_changed(self, connected: bool):
        """Manejar cambio de conexión de cámara"""
        print(f"📹 Cámara {'conectada' if connected else 'desconectada'}")
        
        # Actualizar estado en MenuActions
        if self.menu_actions:
            self.menu_actions.update_system_status(camera_active=connected)
    
    def on_recording_state_changed(self, recording: bool):
        """Manejar cambio de estado de grabación"""
        print(f"🔴 {'Grabando' if recording else 'Grabación detenida'}")
    
    # ===== MANEJADORES DE EVENTOS DE GRÁFICO =====
    
    def on_graph_tool_changed(self, tool_name: str, active: bool):
        """Manejar cambio de herramienta de gráfico"""
        print(f"🔧 Herramienta {tool_name} {'activada' if active else 'desactivada'}")
    
    def on_graph_point_added(self, tiempo: float, amplitud: float, tipo: str):
        """Manejar punto agregado en gráfico"""
        print(f"📍 Punto agregado: {tiempo:.2f}s, {amplitud:.2f}°, {tipo}")
    
    def on_graph_point_removed(self, tiempo: float, amplitud: float, tipo: str):
        """Manejar punto eliminado en gráfico"""
        print(f"🗑️ Punto eliminado: {tiempo:.2f}s, {amplitud:.2f}°, {tipo}")
    
    def on_torok_region_changed(self, inicio: float, fin: float):
        """Manejar cambio de región Torok"""
        print(f"🎯 Región Torok: {inicio:.1f} - {fin:.1f}s")
    
    # ===== MANEJADORES DE EVENTOS DE PROTOCOLOS =====
    
    def on_protocols_loaded(self, count: int):
        """Manejar protocolos cargados"""
        print(f"📋 {count} protocolos cargados")
        
        # Actualizar estado en MenuActions
        if self.menu_actions:
            self.menu_actions.update_system_status(protocols_loaded=count)
    
    def on_protocol_selected(self, protocol_key: str):
        """Manejar selección de protocolo"""
        print(f"📋 Protocolo seleccionado: {protocol_key}")
    
    def on_protocol_execution_requested(self, protocol_data: dict):
        """Manejar solicitud de ejecución de protocolo"""
        protocol_name = protocol_data.get("name", "Sin nombre")
        print(f"🚀 Solicitada ejecución: {protocol_name}")
        
        # Verificar si ya hay ejecución en curso
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
        hardware_control = protocol_data.get("hardware_control", {})
        if hardware_control.get("led_control", False):
            if self.siev_manager and self.siev_manager.is_connected:
                serial_port = self.siev_manager.get_serial_port()
                self.protocol_executor.set_hardware_port(serial_port)
            else:
                # Preguntar si continuar sin hardware
                if not ask_confirmation(
                    "Hardware No Disponible",
                    f"El protocolo '{protocol_name}' requiere control de LED, "
                    f"pero el hardware SIEV no está conectado.\n\n"
                    f"¿Desea continuar sin control de hardware?",
                    self
                ):
                    return
        
        # Ejecutar protocolo
        success = self.protocol_executor.execute_protocol(protocol_data)
        if not success:
            from utils.dialog_utils import show_error
            show_error("Error de Ejecución", 
                      "No se pudo iniciar la ejecución del protocolo", self)
    
    def on_protocol_execution_started(self, protocol_name: str):
        """Manejar inicio de ejecución de protocolo"""
        print(f"🚀 Ejecución iniciada: {protocol_name}")
        
        # Actualizar estado en MenuActions
        if self.menu_actions:
            self.menu_actions.update_system_status(execution_active=True)
    
    def on_protocol_execution_finished(self, protocol_name: str, success: bool):
        """Manejar fin de ejecución de protocolo"""
        print(f"🏁 Ejecución terminada: {protocol_name} - {'Éxito' if success else 'Fallo'}")
        
        # Actualizar estado en MenuActions
        if self.menu_actions:
            self.menu_actions.update_system_status(execution_active=False)
    
    def on_protocol_execution_progress(self, progress_percent: float, status_message: str):
        """Manejar progreso de ejecución"""
        # Ya se maneja en ProtocolExecutor, solo logging
        if progress_percent % 10 == 0:  # Log cada 10%
            print(f"📊 Progreso: {progress_percent:.0f}% - {status_message}")
    
    def on_protocol_event_triggered(self, event_data: dict):
        """Manejar evento de protocolo disparado"""
        event_desc = event_data.get("description", "Evento")
        print(f"⚡ Evento: {event_desc}")
    
    def on_hardware_command_sent(self, command: str):
        """Manejar comando de hardware enviado"""
        print(f"📡 Hardware: {command}")
    
    def on_protocol_execution_error(self, error_msg: str):
        """Manejar error de ejecución de protocolo"""
        print(f"❌ Error ejecución: {error_msg}")
    
    def on_protocols_refreshed(self):
        """Manejar protocolos recargados"""
        if self.protocol_widget:
            self.protocol_widget.refresh_protocols()
        print("🔄 Protocolos recargados en UI")
    
    # ===== UTILIDADES =====
    
    def update_status_message(self, message: str):
        """Actualizar mensaje en status bar"""
        if self.ui and hasattr(self.ui, 'statusbar'):
            self.ui.statusbar.showMessage(message)
    
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
        
        # Cleanup de controladores
        if self.camera_controller:
            self.camera_controller.cleanup()
        
        if self.graph_controller:
            self.graph_controller.cleanup()
        
        if self.menu_actions:
            self.menu_actions.cleanup()
        
        # Cleanup base
        self.cleanup()
        
        print("✅ SIEV cerrado correctamente")
        event.accept()


def main():
    """Función principal de la aplicación"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    print("🚀 Iniciando SIEV v2.0 con arquitectura modular...")
    
    try:
        # Crear ventana principal
        window = SIEVMainWindow("main_window.ui")
        
        # Configurar ventana
        window.setWindowTitle("SIEV v2.0 - Sistema Integrado de Evaluación Vestibular")
        
        # Mostrar ventana
        window.show()
        
        print("✅ SIEV v2.0 iniciado correctamente")
        print("📋 Arquitectura modular cargada:")
        print("   • Core: MainWindowBase, SievManager, ProtocolCoordinator")
        print("   • Controllers: CameraController, GraphController, MenuActions")
        print("   • Widgets: ProtocolTreeWidget, ModularCameraWidget, VCLGraphWidget")
        print("   • Utils: ProtocolManager, ProtocolExecutor, DialogUtils")
        
        return app.exec()
        
    except Exception as e:
        print(f"❌ Error iniciando SIEV: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())