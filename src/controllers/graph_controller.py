#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Graph Controller - Controlador especializado para herramientas de gráfico
Maneja todas las herramientas y eventos del widget VCL Graph
"""

from typing import Optional, Dict, Any, List
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QPushButton

from utils.vcl_graph import VCLGraphWidget


class GraphController(QObject):
    """
    Controlador especializado para el manejo de herramientas de gráfico.
    Centraliza toda la lógica de herramientas VCL y eventos de gráfico.
    """
    
    # Señales
    tool_state_changed = Signal(str, bool)  # (tool_name, active)
    point_added = Signal(float, float, str)  # (tiempo, amplitud, tipo)
    point_removed = Signal(float, float, str)  # (tiempo, amplitud, tipo)
    torok_region_changed = Signal(float, float)  # (inicio, fin)
    graph_status_changed = Signal(str)  # mensaje de estado
    
    def __init__(self, graph_widget: VCLGraphWidget, parent=None):
        super().__init__(parent)
        
        # Widget de gráfico
        self.graph_widget = graph_widget
        
        # Referencias a botones UI (se configuran externamente)
        self.btn_torok = None
        self.btn_peak_edit = None
        self.btn_tiempo_fijacion = None
        self.btn_zoom = None
        self.btn_crosshair = None
        self.btn_peak_detection = None
        
        # Estado de herramientas
        self.tool_states = {
            'torok': False,
            'peak_editing': False,
            'tiempo_fijacion': False,
            'zoom': False,
            'crosshair': False,
            'peak_detection': False
        }
        
        # Conectar señales del widget
        self.connect_widget_signals()
        
        print("✅ GraphController inicializado")
    
    def set_ui_references(self, btn_torok: QPushButton = None,
                         btn_peak_edit: QPushButton = None,
                         btn_tiempo_fijacion: QPushButton = None,
                         btn_zoom: QPushButton = None,
                         btn_crosshair: QPushButton = None,
                         btn_peak_detection: QPushButton = None):
        """Configurar referencias a botones UI"""
        self.btn_torok = btn_torok
        self.btn_peak_edit = btn_peak_edit
        self.btn_tiempo_fijacion = btn_tiempo_fijacion
        self.btn_zoom = btn_zoom
        self.btn_crosshair = btn_crosshair
        self.btn_peak_detection = btn_peak_detection
        
        # Configurar conexiones de botones
        if self.btn_torok:
            self.btn_torok.clicked.connect(self.toggle_torok)
        
        if self.btn_peak_edit:
            self.btn_peak_edit.clicked.connect(self.toggle_peak_edit)
        
        if self.btn_tiempo_fijacion:
            self.btn_tiempo_fijacion.clicked.connect(self.add_tiempo_fijacion)
        
        if self.btn_zoom:
            self.btn_zoom.clicked.connect(self.toggle_zoom)
        
        if self.btn_crosshair:
            self.btn_crosshair.clicked.connect(self.toggle_crosshair)
        
        if self.btn_peak_detection:
            self.btn_peak_detection.clicked.connect(self.toggle_peak_detection)
        
        # Actualizar estado inicial de botones
        self.update_button_states()
        
        print("✅ Referencias UI configuradas en GraphController")
    
    def connect_widget_signals(self):
        """Conectar señales del widget de gráfico"""
        if not self.graph_widget:
            return
        
        # Conectar señales del VCLGraphWidget
        self.graph_widget.point_added.connect(self.on_point_added)
        self.graph_widget.point_removed.connect(self.on_point_removed)
        self.graph_widget.torok_region_changed.connect(self.on_torok_changed)
        
        print("✅ Señales del widget de gráfico conectadas")
    
    # ===== CONTROL DE HERRAMIENTAS =====
    
    def toggle_torok(self):
        """Toggle herramienta Torok"""
        if not self.graph_widget:
            return
        
        current_state = self.tool_states['torok']
        new_state = not current_state
        
        if new_state:
            self.graph_widget.activate_torok_tool()
            if self.btn_torok:
                self.btn_torok.setText("Desactivar Torok")
            print("🎯 Herramienta Torok activada")
        else:
            self.graph_widget.deactivate_torok_tool()
            if self.btn_torok:
                self.btn_torok.setText("Activar Torok")
            print("🎯 Herramienta Torok desactivada")
        
        self.tool_states['torok'] = new_state
        self.tool_state_changed.emit('torok', new_state)
        self.graph_status_changed.emit(f"Torok {'activado' if new_state else 'desactivado'}")
    
    def toggle_peak_edit(self):
        """Toggle edición de picos"""
        if not self.graph_widget:
            return
        
        current_state = self.tool_states['peak_editing']
        new_state = not current_state
        
        if new_state:
            self.graph_widget.activate_peak_editing()
            if self.btn_peak_edit:
                self.btn_peak_edit.setText("Desactivar Edición")
            print("✏️ Edición de picos activada")
        else:
            self.graph_widget.deactivate_peak_editing()
            if self.btn_peak_edit:
                self.btn_peak_edit.setText("Activar Edición Picos")
            print("✏️ Edición de picos desactivada")
        
        self.tool_states['peak_editing'] = new_state
        self.tool_state_changed.emit('peak_editing', new_state)
        self.graph_status_changed.emit(f"Edición de picos {'activada' if new_state else 'desactivada'}")
    
    def add_tiempo_fijacion(self):
        """Agregar tiempo de fijación"""
        if not self.graph_widget:
            return
        
        # Generar intervalo aleatorio para demostración
        import random
        inicio = random.uniform(5, 45)
        fin = inicio + random.uniform(3, 10)
        
        self.graph_widget.create_tiempo_fijacion(inicio, fin)
        
        message = f"Tiempo de fijación agregado: {inicio:.1f} - {fin:.1f}s"
        print(f"📍 {message}")
        self.graph_status_changed.emit(message)
    
    def toggle_zoom(self):
        """Toggle zoom"""
        if not self.graph_widget:
            return
        
        current_state = self.tool_states['zoom']
        new_state = not current_state
        
        if new_state:
            self.graph_widget.activate_zoom()
            if self.btn_zoom:
                self.btn_zoom.setText("Desactivar Zoom")
            print("🔍 Zoom activado")
        else:
            self.graph_widget.deactivate_zoom()
            if self.btn_zoom:
                self.btn_zoom.setText("Activar Zoom")
            print("🔍 Zoom desactivado")
        
        self.tool_states['zoom'] = new_state
        self.tool_state_changed.emit('zoom', new_state)
        self.graph_status_changed.emit(f"Zoom {'activado' if new_state else 'desactivado'}")
    
    def toggle_crosshair(self):
        """Toggle cursor cruz"""
        if not self.graph_widget:
            return
        
        current_state = self.tool_states['crosshair']
        new_state = not current_state
        
        if new_state:
            self.graph_widget.activate_crosshair()
            if self.btn_crosshair:
                self.btn_crosshair.setText("Desactivar Cruz")
            print("✚ Cursor cruz activado")
        else:
            self.graph_widget.deactivate_crosshair()
            if self.btn_crosshair:
                self.btn_crosshair.setText("Activar Cursor Cruz")
            print("✚ Cursor cruz desactivado")
        
        self.tool_states['crosshair'] = new_state
        self.tool_state_changed.emit('crosshair', new_state)
        self.graph_status_changed.emit(f"Cursor cruz {'activado' if new_state else 'desactivado'}")
    
    def toggle_peak_detection(self):
        """Toggle detección automática de picos"""
        if not self.graph_widget:
            return
        
        current_state = self.tool_states['peak_detection']
        new_state = not current_state
        
        if new_state:
            self.graph_widget.activate_peak_detection()
            if self.btn_peak_detection:
                self.btn_peak_detection.setText("Desactivar Detección")
            print("🤖 Detección automática activada")
        else:
            self.graph_widget.deactivate_peak_detection()
            if self.btn_peak_detection:
                self.btn_peak_detection.setText("Detección Automática")
            print("🤖 Detección automática desactivada")
        
        self.tool_states['peak_detection'] = new_state
        self.tool_state_changed.emit('peak_detection', new_state)
        self.graph_status_changed.emit(f"Detección automática {'activada' if new_state else 'desactivada'}")
    
    # ===== CONTROL PROGRAMÁTICO =====
    
    def activate_tool(self, tool_name: str) -> bool:
        """Activar herramienta programáticamente"""
        if tool_name not in self.tool_states:
            print(f"⚠️ Herramienta desconocida: {tool_name}")
            return False
        
        if self.tool_states[tool_name]:
            print(f"⚠️ Herramienta {tool_name} ya está activa")
            return True
        
        # Activar según tipo
        if tool_name == 'torok':
            self.toggle_torok()
        elif tool_name == 'peak_editing':
            self.toggle_peak_edit()
        elif tool_name == 'zoom':
            self.toggle_zoom()
        elif tool_name == 'crosshair':
            self.toggle_crosshair()
        elif tool_name == 'peak_detection':
            self.toggle_peak_detection()
        else:
            return False
        
        return True
    
    def deactivate_tool(self, tool_name: str) -> bool:
        """Desactivar herramienta programáticamente"""
        if tool_name not in self.tool_states:
            print(f"⚠️ Herramienta desconocida: {tool_name}")
            return False
        
        if not self.tool_states[tool_name]:
            print(f"⚠️ Herramienta {tool_name} ya está inactiva")
            return True
        
        # Desactivar según tipo
        if tool_name == 'torok':
            self.toggle_torok()
        elif tool_name == 'peak_editing':
            self.toggle_peak_edit()
        elif tool_name == 'zoom':
            self.toggle_zoom()
        elif tool_name == 'crosshair':
            self.toggle_crosshair()
        elif tool_name == 'peak_detection':
            self.toggle_peak_detection()
        else:
            return False
        
        return True
    
    def configure_tools_from_protocol(self, graph_tools: Dict[str, bool]):
        """Configurar herramientas según protocolo"""
        print("🔧 Configurando herramientas desde protocolo")
        
        for tool_name, should_be_active in graph_tools.items():
            if tool_name in self.tool_states:
                current_state = self.tool_states[tool_name]
                
                if should_be_active and not current_state:
                    self.activate_tool(tool_name)
                elif not should_be_active and current_state:
                    self.deactivate_tool(tool_name)
        
        print(f"✅ Herramientas configuradas: {graph_tools}")
    
    def deactivate_all_tools(self):
        """Desactivar todas las herramientas"""
        print("🔄 Desactivando todas las herramientas")
        
        for tool_name in self.tool_states:
            if self.tool_states[tool_name]:
                self.deactivate_tool(tool_name)
        
        print("✅ Todas las herramientas desactivadas")
    
    def create_tiempo_fijacion_custom(self, inicio: float, fin: float):
        """Crear tiempo de fijación con valores específicos"""
        if not self.graph_widget:
            return
        
        self.graph_widget.create_tiempo_fijacion(inicio, fin)
        
        message = f"Tiempo de fijación creado: {inicio:.1f} - {fin:.1f}s"
        print(f"📍 {message}")
        self.graph_status_changed.emit(message)
    
    # ===== MANEJADORES DE EVENTOS =====
    
    def on_point_added(self, tiempo: float, amplitud: float, tipo: str):
        """Manejar punto agregado en gráfico"""
        message = f"Punto agregado: t={tiempo:.2f}s, amp={amplitud:.2f}°, tipo={tipo}"
        print(f"📍 {message}")
        
        # Re-emitir señal
        self.point_added.emit(tiempo, amplitud, tipo)
        self.graph_status_changed.emit(message)
    
    def on_point_removed(self, tiempo: float, amplitud: float, tipo: str):
        """Manejar punto eliminado en gráfico"""
        message = f"Punto eliminado: t={tiempo:.2f}s, amp={amplitud:.2f}°, tipo={tipo}"
        print(f"🗑️ {message}")
        
        # Re-emitir señal
        self.point_removed.emit(tiempo, amplitud, tipo)
        self.graph_status_changed.emit(message)
    
    def on_torok_changed(self, inicio: float, fin: float):
        """Manejar cambio de región Torok"""
        message = f"Región Torok: {inicio:.1f} - {fin:.1f}s"
        print(f"🎯 {message}")
        
        # Re-emitir señal
        self.torok_region_changed.emit(inicio, fin)
        self.graph_status_changed.emit(message)
    
    # ===== GESTIÓN DE UI =====
    
    def update_button_states(self):
        """Actualizar estado visual de botones"""
        if self.btn_torok:
            self.btn_torok.setChecked(self.tool_states['torok'])
            self.btn_torok.setText("Desactivar Torok" if self.tool_states['torok'] else "Activar Torok")
        
        if self.btn_peak_edit:
            self.btn_peak_edit.setChecked(self.tool_states['peak_editing'])
            self.btn_peak_edit.setText("Desactivar Edición" if self.tool_states['peak_editing'] else "Activar Edición Picos")
        
        if self.btn_zoom:
            self.btn_zoom.setChecked(self.tool_states['zoom'])
            self.btn_zoom.setText("Desactivar Zoom" if self.tool_states['zoom'] else "Activar Zoom")
        
        if self.btn_crosshair:
            self.btn_crosshair.setChecked(self.tool_states['crosshair'])
            self.btn_crosshair.setText("Desactivar Cruz" if self.tool_states['crosshair'] else "Activar Cursor Cruz")
        
        if self.btn_peak_detection:
            self.btn_peak_detection.setChecked(self.tool_states['peak_detection'])
            self.btn_peak_detection.setText("Desactivar Detección" if self.tool_states['peak_detection'] else "Detección Automática")
    
    # ===== MÉTODOS DE INFORMACIÓN =====
    
    def get_tool_states(self) -> Dict[str, bool]:
        """Obtener estado de todas las herramientas"""
        return self.tool_states.copy()
    
    def is_tool_active(self, tool_name: str) -> bool:
        """Verificar si una herramienta está activa"""
        return self.tool_states.get(tool_name, False)
    
    def get_torok_data(self) -> Dict[str, Any]:
        """Obtener datos de la región Torok"""
        if not self.graph_widget:
            return {}
        
        return self.graph_widget.get_torok()
    
    def get_tiempos_fijacion(self) -> List[tuple]:
        """Obtener tiempos de fijación"""
        if not self.graph_widget:
            return []
        
        return self.graph_widget.get_tiempos_fijacion()
    
    def get_graph_data(self) -> Dict[str, Any]:
        """Obtener datos del gráfico"""
        if not self.graph_widget:
            return {}
        
        return self.graph_widget.get_data()
    
    def set_graph_data(self, data: Dict[str, Any]):
        """Establecer datos en el gráfico"""
        if self.graph_widget:
            self.graph_widget.set_data(data)
            print("📊 Datos establecidos en gráfico")
    
    def set_eye_visibility(self, ojo_izq_visible: bool, ojo_der_visible: bool):
        """Configurar visibilidad de ojos"""
        if self.graph_widget:
            self.graph_widget.set_eye_visibility(ojo_izq_visible, ojo_der_visible)
            print(f"👁️ Visibilidad de ojos: Izq={ojo_izq_visible}, Der={ojo_der_visible}")
    
    def get_graph_widget(self) -> Optional[VCLGraphWidget]:
        """Obtener referencia al widget de gráfico"""
        return self.graph_widget
    
    def cleanup(self):
        """Limpieza al cerrar"""
        print("🧹 Limpiando GraphController...")
        
        # Desactivar todas las herramientas
        self.deactivate_all_tools()
        
        print("✅ GraphController limpiado")