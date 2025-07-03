#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Menu Actions - Controlador para acciones de menú y utilidades
Maneja todas las acciones de menús, estadísticas, exportación e información del sistema
"""

from typing import Optional, Dict, Any
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QFileDialog, QWidget

from utils.protocol_manager import ProtocolManager
from utils.dialog_utils import (show_info, show_success, show_warning, show_error, 
                               ask_confirmation, DialogUtils)


class MenuActions(QObject):
    """
    Controlador especializado para acciones de menú y utilidades del sistema.
    Centraliza funciones de información, exportación, importación y estadísticas.
    """
    
    # Señales
    status_message_changed = Signal(str)  # Mensajes para status bar
    protocols_refreshed = Signal()  # Protocolos recargados
    
    def __init__(self, protocol_manager: ProtocolManager, parent=None):
        super().__init__(parent)
        
        # Referencias
        self.protocol_manager = protocol_manager
        self.main_window = parent  # Referencia a ventana principal
        
        # Estado del sistema (se actualizará externamente)
        self.system_status = {
            'siev_connected': False,
            'protocols_loaded': 0,
            'camera_active': False,
            'execution_active': False
        }
        
        print("✅ MenuActions inicializado")
    
    def update_system_status(self, **kwargs):
        """Actualizar estado del sistema"""
        self.system_status.update(kwargs)
    
    # ===== INFORMACIÓN DEL SISTEMA =====
    
    def show_system_info(self):
        """Mostrar información completa del sistema"""
        info_text = f"""
<b>SIEV - Sistema Integrado de Evaluación Vestibular</b><br><br>

<b>Estado del Sistema:</b><br>
• Hardware SIEV: {'Conectado' if self.system_status['siev_connected'] else 'No conectado'}<br>
• Protocolos cargados: {self.system_status['protocols_loaded']}<br>
• Cámara: {'Activa' if self.system_status['camera_active'] else 'Inactiva'}<br>
• Ejecución: {'En curso' if self.system_status['execution_active'] else 'Inactiva'}<br><br>

<b>Módulos del Sistema:</b><br>
• ProtocolTreeWidget: Gestión de protocolos<br>
• ProtocolExecutor: Ejecución con eventos temporales<br>
• ProtocolManager: Validación y persistencia<br>
• ModularCameraWidget: Captura y detección<br>
• VCLGraphWidget: Análisis de señales<br><br>

<b>Características:</b><br>
• ✅ Protocolos vestibulares estándar médicos<br>
• ✅ Control de hardware ESP8266 + LEDs<br>
• ✅ Eventos temporales automáticos<br>
• ✅ Editor avanzado de protocolos<br>
• ✅ Detección automática de ojos y pupilas<br>
• ✅ Análisis de gráficos con herramientas especializadas<br><br>

<b>Arquitectura Modular:</b><br>
• /core/ - Lógica central (MainWindowBase, SievManager, ProtocolCoordinator)<br>
• /controllers/ - Controladores especializados (Camera, Graph, MenuActions)<br>
• /widgets/ - Widgets reutilizables<br>
• /utils/ - Utilidades y helpers<br>
• /camera/ - Módulos de cámara y detección<br>
"""
        
        DialogUtils.show_info("Información del Sistema", info_text, self.main_window)
        self.status_message_changed.emit("ℹ️ Información del sistema mostrada")
    
    def show_about_dialog(self):
        """Mostrar diálogo Acerca de"""
        about_text = """
<b>SIEV v2.0 - Sistema Integrado de Evaluación Vestibular</b><br><br>

<b>Características Principales:</b><br>
• Protocolos vestibulares estándar médicos<br>
• Control de hardware ESP8266 + LEDs<br>
• Eventos temporales automáticos<br>
• Editor avanzado de protocolos<br>
• Detección de ojos y pupilas<br>
• Análisis de gráficos especializado<br><br>

<b>Tecnologías:</b><br>
• PySide6 para interfaz gráfica<br>
• OpenCV para procesamiento de imagen<br>
• PyQtGraph para visualización de datos<br>
• Serial para comunicación hardware<br>
• JSON para configuración de protocolos<br><br>

<b>Desarrollado con arquitectura modular</b><br>
© 2025 Proyecto SIEV
"""
        
        DialogUtils.show_info("Acerca de SIEV v2.0", about_text, self.main_window)
    
    # ===== EXPORTACIÓN E IMPORTACIÓN =====
    
    def export_protocols(self):
        """Exportar protocolos a archivo"""
        if not self.protocol_manager:
            show_error("Error", "Sistema de protocolos no disponible", self.main_window)
            return
        
        # Diálogo de selección de archivo
        export_path, _ = QFileDialog.getSaveFileName(
            self.main_window,
            "Exportar Protocolos",
            "protocolos_siev_export.json",
            "JSON Files (*.json)"
        )
        
        if not export_path:
            return  # Usuario canceló
        
        # Realizar exportación
        success = self.protocol_manager.export_protocols(
            export_path, 
            include_defaults=True, 
            include_presets=True
        )
        
        if success:
            message = f"Protocolos exportados correctamente"
            self.status_message_changed.emit(f"📤 {message}")
            show_success("Exportación Exitosa", 
                       f"Protocolos exportados a:\n{export_path}",
                       self.main_window)
        else:
            show_error("Error de Exportación", 
                      "No se pudieron exportar los protocolos",
                      self.main_window)
    
    def import_protocols(self):
        """Importar protocolos desde archivo"""
        if not self.protocol_manager:
            show_error("Error", "Sistema de protocolos no disponible", self.main_window)
            return
        
        # Diálogo de selección de archivo
        import_path, _ = QFileDialog.getOpenFileName(
            self.main_window,
            "Importar Protocolos",
            "",
            "JSON Files (*.json)"
        )
        
        if not import_path:
            return  # Usuario canceló
        
        # Preguntar si sobrescribir existentes
        overwrite = ask_confirmation(
            "Importar Protocolos",
            "¿Desea sobrescribir protocolos existentes con el mismo nombre?",
            self.main_window
        )
        
        # Realizar importación
        success, count = self.protocol_manager.import_protocols(import_path, overwrite)
        
        if success:
            self.protocol_manager.save_protocols()
            message = f"{count} protocolos importados correctamente"
            self.status_message_changed.emit(f"📥 {message}")
            self.protocols_refreshed.emit()  # Señal para recargar UI
            
            show_success("Importación Exitosa", message, self.main_window)
        else:
            show_error("Error de Importación", 
                      "No se pudieron importar los protocolos",
                      self.main_window)
    
    # ===== ESTADÍSTICAS Y ANÁLISIS =====
    
    def show_protocol_statistics(self):
        """Mostrar estadísticas detalladas de protocolos"""
        if not self.protocol_manager:
            show_error("Error", "Sistema de protocolos no disponible", self.main_window)
            return
        
        stats = self.protocol_manager.get_statistics()
        
        # Formatear categorías
        categories_text = "<br>".join([
            f"• {cat}: {count}" for cat, count in stats["categories"].items()
        ]) if stats["categories"] else "• Sin categorías"
        
        # Formatear tipos de comportamiento
        behavior_types_text = "<br>".join([
            f"• {bt}: {count}" for bt, count in stats["behavior_types"].items()
        ]) if stats["behavior_types"] else "• Sin tipos"
        
        stats_text = f"""
<b>Estadísticas de Protocolos SIEV</b><br><br>

<b>Resumen General:</b><br>
• Total de protocolos: {stats['total_protocols']}<br>
• Protocolos estándar: {stats['default_protocols']}<br>
• Protocolos personalizados: {stats['preset_protocols']}<br><br>

<b>Distribución por Categoría:</b><br>
{categories_text}<br><br>

<b>Distribución por Tipo de Comportamiento:</b><br>
{behavior_types_text}<br><br>

<b>Información del Archivo:</b><br>
• Ruta: {stats['file_path']}<br>
• Estado: {'Cargado correctamente' if stats['is_loaded'] else 'Error de carga'}<br><br>

<b>Recomendaciones:</b><br>
• Use protocolos estándar como base para evaluaciones<br>
• Cree copias personalizadas para casos específicos<br>
• Valide protocolos regularmente para mantener integridad<br>
"""
        
        DialogUtils.show_info("Estadísticas de Protocolos", stats_text, self.main_window)
        self.status_message_changed.emit("📊 Estadísticas de protocolos mostradas")
    
    def validate_all_protocols(self):
        """Validar todos los protocolos del sistema"""
        if not self.protocol_manager:
            show_error("Error", "Sistema de protocolos no disponible", self.main_window)
            return
        
        all_protocols = self.protocol_manager.get_all_protocols()
        
        valid_count = 0
        invalid_protocols = []
        
        # Validar cada protocolo
        for key, protocol in all_protocols.items():
            is_valid, errors = self.protocol_manager.validate_protocol(protocol)
            if is_valid:
                valid_count += 1
            else:
                invalid_protocols.append((key, errors))
        
        # Mostrar resultados
        if invalid_protocols:
            error_text = f"<b>Validación Completada con Errores</b><br><br>"
            error_text += f"✅ Protocolos válidos: {valid_count}<br>"
            error_text += f"❌ Protocolos inválidos: {len(invalid_protocols)}<br><br>"
            
            error_text += "<b>Protocolos con Errores:</b><br>"
            
            # Mostrar solo los primeros 5 para evitar ventanas muy largas
            for i, (key, errors) in enumerate(invalid_protocols[:5]):
                protocol_name = all_protocols[key].get('name', key)
                error_text += f"<br><b>• {protocol_name}:</b><br>"
                
                # Mostrar solo los primeros 3 errores
                for error in errors[:3]:
                    error_text += f"  - {error}<br>"
                
                if len(errors) > 3:
                    error_text += f"  ... y {len(errors) - 3} errores más<br>"
            
            if len(invalid_protocols) > 5:
                error_text += f"<br>... y {len(invalid_protocols) - 5} protocolos más con errores"
            
            show_warning("Protocolos Inválidos Encontrados", error_text, self.main_window)
        else:
            success_text = f"""
<b>✅ Validación Exitosa</b><br><br>

Todos los {valid_count} protocolos son válidos y cumplen con:<br><br>

• Campos requeridos presentes<br>
• Tipos de datos correctos<br>
• Rangos de valores válidos<br>
• Estructura JSON correcta<br>
• Configuraciones de hardware válidas<br><br>

<b>Estado del Sistema:</b> Óptimo para uso clínico
"""
            show_success("Validación Completada", success_text, self.main_window)
        
        message = f"Validación completada: {valid_count} válidos, {len(invalid_protocols)} con errores"
        self.status_message_changed.emit(f"✅ {message}")
    
    def show_hardware_diagnostics(self):
        """Mostrar diagnósticos de hardware"""
        diagnostic_text = f"""
<b>Diagnósticos de Hardware SIEV</b><br><br>

<b>Estado Actual:</b><br>
• SIEV Conectado: {'✅ Sí' if self.system_status['siev_connected'] else '❌ No'}<br>
• Cámara Activa: {'✅ Sí' if self.system_status['camera_active'] else '❌ No'}<br><br>

<b>Componentes Esperados:</b><br>
• Hub USB (VID:1a40 PID:0101)<br>
• ESP8266 con firmware SIEV<br>
• Cámara USB compatible<br>
• Puerto serie funcional<br><br>

<b>Resolución de Problemas:</b><br>
• Verifique conexiones USB<br>
• Reinstale drivers CH340/CP210x<br>
• Use 'Buscar SIEV' para re-detectar<br>
• Verifique puerto serie no esté en uso<br><br>

<b>Comandos de Prueba ESP8266:</b><br>
• PING → SIEV_ESP_OK_v1.0.0<br>
• STATUS → Información del sistema<br>
• VERSION → Detalles del firmware<br>
"""
        
        DialogUtils.show_info("Diagnósticos de Hardware", diagnostic_text, self.main_window)
    
    # ===== GESTIÓN DE PROTOCOLOS =====
    
    def reset_to_defaults(self):
        """Resetear protocolos a valores por defecto"""
        if not ask_confirmation(
            "Resetear Protocolos",
            "¿Está seguro de que desea eliminar TODOS los protocolos "
            "personalizados y resetear a los valores por defecto?\n\n"
            "Esta acción no se puede deshacer.",
            self.main_window
        ):
            return
        
        if self.protocol_manager:
            # Limpiar presets
            if hasattr(self.protocol_manager, 'protocols_data'):
                self.protocol_manager.protocols_data["presets"] = {}
                
                # Guardar cambios
                if self.protocol_manager.save_protocols():
                    self.status_message_changed.emit("🔄 Protocolos restablecidos a valores por defecto")
                    self.protocols_refreshed.emit()  # Señal para recargar UI
                    
                    show_success("Reset Completado", 
                               "Protocolos restablecidos a valores por defecto",
                               self.main_window)
                else:
                    show_error("Error", "No se pudo resetear los protocolos", self.main_window)
    
    def refresh_protocols(self):
        """Recargar protocolos desde archivo"""
        if not self.protocol_manager:
            show_error("Error", "Sistema de protocolos no disponible", self.main_window)
            return
        
        success = self.protocol_manager.load_protocols()
        
        if success:
            self.status_message_changed.emit("🔄 Protocolos recargados desde archivo")
            self.protocols_refreshed.emit()  # Señal para recargar UI
            show_info("Protocolos Recargados", 
                     "Los protocolos se han recargado correctamente desde el archivo.",
                     self.main_window)
        else:
            show_error("Error de Recarga", 
                      "No se pudieron recargar los protocolos desde el archivo",
                      self.main_window)
    
    def backup_protocols(self):
        """Crear respaldo de protocolos"""
        if not self.protocol_manager:
            show_error("Error", "Sistema de protocolos no disponible", self.main_window)
            return
        
        from datetime import datetime
        
        # Generar nombre con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"protocolos_backup_{timestamp}.json"
        
        backup_path, _ = QFileDialog.getSaveFileName(
            self.main_window,
            "Crear Respaldo de Protocolos",
            default_name,
            "JSON Files (*.json)"
        )
        
        if not backup_path:
            return
        
        success = self.protocol_manager.export_protocols(backup_path)
        
        if success:
            message = "Respaldo creado correctamente"
            self.status_message_changed.emit(f"💾 {message}")
            show_success("Respaldo Creado", 
                       f"Respaldo guardado en:\n{backup_path}",
                       self.main_window)
        else:
            show_error("Error de Respaldo", 
                      "No se pudo crear el respaldo",
                      self.main_window)
    
    # ===== MÉTODOS DE INFORMACIÓN =====
    
    def get_system_summary(self) -> Dict[str, Any]:
        """Obtener resumen del estado del sistema"""
        protocol_stats = self.protocol_manager.get_statistics() if self.protocol_manager else {}
        
        return {
            'system_status': self.system_status.copy(),
            'protocol_stats': protocol_stats,
            'modules_loaded': [
                'MainWindowBase',
                'SievManager', 
                'ProtocolCoordinator',
                'CameraController',
                'GraphController',
                'MenuActions'
            ]
        }
    
    def cleanup(self):
        """Limpieza al cerrar"""
        print("🧹 Limpiando MenuActions...")
        
        # Guardar protocolos si hay cambios pendientes
        if self.protocol_manager:
            self.protocol_manager.save_protocols()
        
        print("✅ MenuActions limpiado")