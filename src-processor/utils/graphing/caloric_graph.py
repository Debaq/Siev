#!/usr/bin/env python3
"""
CaloricPlotWidget - Creado desde cero
Widget de gráfico calórico que funciona exactamente igual que el gráfico simple
pero con áreas de fases y características específicas para pruebas calóricas.
"""

import pyqtgraph as pg
import numpy as np
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Signal


class CaloricPlotWidget(QWidget):
    """
    Widget de gráfico calórico que imita exactamente el comportamiento del gráfico simple
    pero añade áreas de fases para pruebas calóricas.
    """
    
    def __init__(self, total_duration=60.0, parent=None):
        super().__init__(parent)
        
        self.total_duration = total_duration
        
        # Layout principal
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Crear PlotWidget exactamente como el simple
        self.plot_widget = pg.PlotWidget(title="Nistagmo Calórico - Velocidad Angular")
        self.plot_widget.setLabel('left', 'Velocidad (°/s)')
        self.plot_widget.setLabel('bottom', 'Tiempo (s)')
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.setBackground('white')
        
        # Configurar rango inicial
        self.plot_widget.setXRange(0, total_duration, padding=0.02)
        
        # Crear áreas de fases ANTES de la curva (para que estén atrás)
        self._create_phase_areas()
        
        # Crear curva de datos - IGUAL que el simple
        self.data_curve = self.plot_widget.plot([], [], pen='b', name='Ojo Derecho')
        
        # Crear línea de tiempo - IGUAL que el simple
        self.time_line = pg.InfiniteLine(
            pos=0, angle=90, pen=pg.mkPen(color='r', width=2),
            movable=True, label="Tiempo"
        )
        self.plot_widget.addItem(self.time_line)
        
        # Agregar plot al layout
        layout.addWidget(self.plot_widget)
        
        print(f"CaloricPlotWidget creado para {total_duration}s")
    
    def _create_phase_areas(self):
        """Crear áreas sombreadas para fases calóricas"""
        # Fase 1: Irrigación (0-40s) - Azul claro
        irrigation_region = pg.LinearRegionItem(
            values=[0, min(40, self.total_duration * 0.4)],
            orientation='vertical',
            brush=pg.mkBrush(100, 150, 255, 50),  # Azul transparente
            movable=False
        )
        self.plot_widget.addItem(irrigation_region)
        
        # Fase 2: Respuesta (40-90s) - Naranja claro  
        if self.total_duration > 40:
            response_start = min(40, self.total_duration * 0.4)
            response_end = min(90, self.total_duration * 0.8)
            response_region = pg.LinearRegionItem(
                values=[response_start, response_end],
                orientation='vertical',
                brush=pg.mkBrush(255, 150, 100, 50),  # Naranja transparente
                movable=False
            )
            self.plot_widget.addItem(response_region)
        
        # Fase 3: Fijación (90s-final) - Verde claro
        if self.total_duration > 90:
            fixation_start = min(90, self.total_duration * 0.8)
            fixation_region = pg.LinearRegionItem(
                values=[fixation_start, self.total_duration],
                orientation='vertical',
                brush=pg.mkBrush(150, 255, 150, 50),  # Verde transparente
                movable=False
            )
            self.plot_widget.addItem(fixation_region)
        
        # Etiquetas de texto para las fases
        self._add_phase_labels()
    
    def _add_phase_labels(self):
        """Agregar etiquetas de texto para las fases"""
        # Etiqueta Irrigación
        irrigation_text = pg.TextItem("Irrigación", color=(0, 0, 150), anchor=(0.5, 1))
        irrigation_center = min(20, self.total_duration * 0.2)
        irrigation_text.setPos(irrigation_center, 0)
        self.plot_widget.addItem(irrigation_text)
        
        # Etiqueta Respuesta
        if self.total_duration > 40:
            response_text = pg.TextItem("Respuesta", color=(150, 75, 0), anchor=(0.5, 1))
            response_center = min(65, self.total_duration * 0.6)
            response_text.setPos(response_center, 0)
            self.plot_widget.addItem(response_text)
        
        # Etiqueta Fijación
        if self.total_duration > 90:
            fixation_text = pg.TextItem("Fijación", color=(0, 150, 0), anchor=(0.5, 1))
            fixation_center = min(105, self.total_duration * 0.9)
            fixation_text.setPos(fixation_center, 0)
            self.plot_widget.addItem(fixation_text)
    
    # ========== MÉTODOS IGUALES AL GRÁFICO SIMPLE ==========
    
    def setData(self, x_data, y_data):
        """Método igual al simple - actualizar datos de la curva"""
        if self.data_curve:
            self.data_curve.setData(x_data, y_data)
    
    def plot(self, x_data, y_data, **kwargs):
        """Método igual al simple - crear/actualizar curva"""
        return self.plot_widget.plot(x_data, y_data, **kwargs)
    
    def setXRange(self, min_val, max_val, padding=0.02):
        """Método igual al simple - establecer rango X"""
        self.plot_widget.setXRange(min_val, max_val, padding=padding)
    
    def setYRange(self, min_val, max_val, padding=0.1):
        """Método igual al simple - establecer rango Y"""
        self.plot_widget.setYRange(min_val, max_val, padding=padding)
    
    def addItem(self, item):
        """Método igual al simple - agregar elementos"""
        self.plot_widget.addItem(item)
    
    def removeItem(self, item):
        """Método igual al simple - remover elementos"""
        self.plot_widget.removeItem(item)
    
    def clear(self):
        """Método igual al simple - limpiar datos"""
        if self.data_curve:
            self.data_curve.setData([], [])
    
    # ========== MÉTODOS ESPECÍFICOS PARA INTEGRACIÓN ==========
    
    def set_pos_time_video(self, position: float):
        """Actualizar posición de línea de tiempo - compatible con UI"""
        if hasattr(self, 'time_line') and self.time_line:
            self.time_line.setPos(position)
    
    def add_data_point(self, timestamp: float, value: float):
        """Agregar punto individual - compatible con UI"""
        # Para mantener compatibilidad, pero el gráfico se actualiza principalmente con setData
        pass
    
    def rebuild_phases(self):
        """Reconstruir fases - compatible con UI"""
        # Las fases se crean una vez y no necesitan reconstrucción frecuente
        pass
    
    def adjust_to_duration(self, duration: float):
        """Ajustar a nueva duración - compatible con UI"""
        self.total_duration = duration
        self.setXRange(0, duration, padding=0.02)
        
        # Recrear widget completo para nueva duración
        self._recreate_for_new_duration(duration)
    
    def _recreate_for_new_duration(self, duration: float):
        """Recrear widget completo para nueva duración"""
        # Limpiar elementos existentes (excepto curva principal)
        items_to_remove = []
        for item in self.plot_widget.items():
            if item != self.data_curve and item != self.time_line:
                items_to_remove.append(item)
        
        for item in items_to_remove:
            self.plot_widget.removeItem(item)
        
        # Recrear fases con nueva duración
        self.total_duration = duration
        self._create_phase_areas()
    
    # ========== COMPATIBILIDAD TOTAL CON SIMPLE ==========
    
    def getViewBox(self):
        """Acceso al ViewBox - igual que PlotWidget"""
        return self.plot_widget.getViewBox()
    
    def setLabel(self, axis, text, units=None, **kwargs):
        """Establecer etiquetas - igual que PlotWidget"""
        self.plot_widget.setLabel(axis, text, units, **kwargs)
    
    def setTitle(self, title):
        """Establecer título - igual que PlotWidget"""
        self.plot_widget.setTitle(title)
    
    def showGrid(self, x=None, y=None, alpha=None):
        """Mostrar grilla - igual que PlotWidget"""
        self.plot_widget.showGrid(x, y, alpha)
    
    def setBackground(self, background):
        """Establecer fondo - igual que PlotWidget"""
        self.plot_widget.setBackground(background)
    
    def setMouseEnabled(self, x=None, y=None):
        """Configurar mouse - igual que PlotWidget"""
        self.plot_widget.setMouseEnabled(x, y)
    
    def autoRange(self):
        """Auto rango - igual que PlotWidget"""
        self.plot_widget.autoRange()
    
    def enableAutoRange(self, axis=None, enable=True):
        """Habilitar auto rango - igual que PlotWidget"""
        self.plot_widget.enableAutoRange(axis, enable)


# ========== FUNCIÓN DE CREACIÓN COMPATIBLE ==========

def create_caloric_graph(total_duration=60.0, parent=None):
    """
    Función helper para crear gráfico calórico de forma compatible
    con el sistema existente.
    """
    caloric_widget = CaloricPlotWidget(total_duration, parent)
    
    print(f"Gráfico calórico creado y listo para usar")
    
    return caloric_widget