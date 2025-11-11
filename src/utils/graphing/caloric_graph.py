# src/ui/widgets/caloric_plot_widget.py

import pyqtgraph as pg
import numpy as np
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Signal, QTimer
from PySide6.QtGui import QColor
import time
from typing import Optional, List, Dict, Any

class CaloricPlotWidget(QWidget):
    """
    Widget de gráfico especializado para pruebas calóricas.
    
    Características específicas:
    - Calibración a 0 (no permite X negativos)
    - Autoscale controlado
    - Áreas sombreadas configurables para fases del test
    - Línea vertical móvil sincronizada con video
    """
    
    # Señales
    time_position_changed = Signal(float)  # Cuando se mueve la línea manualmente
    phase_config_changed = Signal(dict)    # Cuando cambia la configuración de fases
    
    # Configuración DEFAULT de fases calóricas (en segundos)
    DEFAULT_PHASE_CONFIG = {
        'irrigation': {'start': 0, 'end': 40, 'color': (100, 150, 255, 80), 'label': 'Irrigación'},
        'torok': {'start': 60, 'end': 90, 'color': (255, 150, 100, 80), 'label': 'Período Torok'},
        'fixation': {'start': 90, 'end': 100, 'color': (150, 255, 150, 80), 'label': 'Fijación'}
    }
    
    def __init__(self, parent=None, total_duration=120, phase_config=None):
        super().__init__(parent)
        
        # Configuración
        self.total_duration = total_duration  # Duración total en segundos
        self.current_video_time = 0.0
        self.data_buffer = []
        
        # Configuración de fases (usar default o personalizada)
        self.phase_config = phase_config.copy() if phase_config else self.DEFAULT_PHASE_CONFIG.copy()
        
        # Referencias a elementos gráficos
        self.phase_regions = {}
        self.phase_text_items = {}
        
        # Setup UI
        self.setup_ui()
        self.setup_plot()
        self.setup_phases()
        self.setup_video_line()
        
        print(f"CaloricPlotWidget inicializado para {total_duration}s")
        print(f"Fases configuradas: {list(self.phase_config.keys())}")
    
    def setup_ui(self):
        """Configura el layout básico."""
        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)
    
    def setup_plot(self):
        """Configura el gráfico principal."""
        # Crear gráfico con configuración optimizada
        self.plot_widget = pg.PlotWidget(
            title="Nistagmo Calórico - Velocidad Angular",
            labels={'left': 'Velocidad (°/s)', 'bottom': 'Tiempo (s)'}
        )
        
        # Configuración visual
        self.plot_widget.setBackground('white')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setMouseEnabled(x=True, y=True)
        
        # RESTRICCIÓN CRÍTICA: No permitir X negativos
        self.plot_widget.setXRange(0, self.total_duration, padding=0)
        self.plot_widget.setLimits(xMin=0, xMax=None)  # No X negativos
        
        # Configurar autoscale controlado
        view_box = self.plot_widget.getViewBox()
        view_box.sigRangeChanged.connect(self._on_range_changed)
        
        # Curva principal de datos
        self.data_curve = self.plot_widget.plot(
            pen=pg.mkPen(color=(200, 50, 50), width=2),
            name="Velocidad Angular"
        )
        
        self.layout.addWidget(self.plot_widget)
    
    def setup_phases(self):
        """Configura las áreas sombreadas para cada fase."""
        self.phase_regions = {}
        self.phase_text_items = {}
        
        for phase_name, config in self.phase_config.items():
            # Crear región sombreada
            region = pg.LinearRegionItem(
                values=[config['start'], config['end']],
                orientation='vertical',
                brush=pg.mkBrush(config['color']),
                movable=False,
                bounds=[0, self.total_duration]
            )
            
            # Agregar al gráfico
            self.plot_widget.addItem(region)
            self.phase_regions[phase_name] = region
            
            # Agregar etiqueta de texto
            text_item = pg.TextItem(
                text=config['label'],
                color=(50, 50, 50),
                anchor=(0.5, 0)
            )
            text_item.setPos((config['start'] + config['end']) / 2, 0)
            self.plot_widget.addItem(text_item)
            self.phase_text_items[phase_name] = text_item
            
            print(f"Fase '{phase_name}': {config['start']}-{config['end']}s")
    
    def _rebuild_phases(self):
        """Reconstruye todas las fases después de un cambio de configuración."""
        # Limpiar fases existentes
        for region in self.phase_regions.values():
            self.plot_widget.removeItem(region)
        for text_item in self.phase_text_items.values():
            self.plot_widget.removeItem(text_item)
        
        # Recrear fases
        self.setup_phases()
        
        print("Fases reconstruidas con nueva configuración")
    
    def setup_video_line(self):
        """Configura la línea vertical móvil para sincronización con video."""
        self.video_line = pg.InfiniteLine(
            pos=0,
            angle=90,
            pen=pg.mkPen(color=(255, 0, 0), width=3, style=pg.QtCore.Qt.SolidLine),
            movable=True,
            bounds=[0, self.total_duration],
            label="Video"
        )
        
        # Conectar eventos
        self.video_line.sigPositionChanged.connect(self._on_video_line_moved)
        
        # Agregar al gráfico
        self.plot_widget.addItem(self.video_line)
        
        print("Línea de video configurada")
    
    def _on_range_changed(self, view_box, ranges):
        """Controla los cambios de rango para mantener restricciones."""
        x_range, y_range = ranges
        
        # RESTRICCIÓN 1: No permitir X negativos
        if x_range[0] < 0:
            view_box.setXRange(0, x_range[1], padding=0)
        
        # RESTRICCIÓN 2: No permitir zoom out más allá del total
        range_width = x_range[1] - x_range[0]
        if range_width > self.total_duration:
            center = (x_range[0] + x_range[1]) / 2
            half_total = self.total_duration / 2
            view_box.setXRange(
                max(0, center - half_total), 
                center + half_total, 
                padding=0
            )
    
    def _on_video_line_moved(self, line):
        """Maneja el movimiento manual de la línea de video."""
        new_pos = line.getPos()[0]
        self.current_video_time = max(0, min(new_pos, self.total_duration))
        
        # Emitir señal para sincronizar video
        self.time_position_changed.emit(self.current_video_time)
        
        print(f"Video sincronizado a: {self.current_video_time:.2f}s")
    
    def set_pos_time_video(self, seconds: float):
        """
        Establece la posición de la línea de video programáticamente.
        
        Args:
            seconds: Posición en segundos (0 a total_duration)
        """
        # Validar rango
        seconds = max(0, min(seconds, self.total_duration))
        
        # Actualizar línea (desconectar temporalmente para evitar loops)
        self.video_line.sigPositionChanged.disconnect()
        self.video_line.setPos(seconds)
        self.video_line.sigPositionChanged.connect(self._on_video_line_moved)
        
        # Actualizar estado interno
        self.current_video_time = seconds
        
        # Auto-scroll para seguir la línea si está fuera de vista
        x_range = self.plot_widget.getViewBox().viewRange()[0]
        if not (x_range[0] <= seconds <= x_range[1]):
            # Centrar la vista en la línea actual
            window_size = x_range[1] - x_range[0]
            new_start = max(0, seconds - window_size / 2)
            new_end = min(self.total_duration, new_start + window_size)
            
            self.plot_widget.setXRange(new_start, new_end, padding=0)
    
    def add_data_point(self, timestamp: float, angular_velocity: float):
        """
        Añade un punto de datos al gráfico.
        
        Args:
            timestamp: Tiempo en segundos desde el inicio
            angular_velocity: Velocidad angular en grados/segundo
        """
        # Validar timestamp
        if timestamp < 0:
            return
        
        # Añadir al buffer
        self.data_buffer.append((timestamp, angular_velocity))
        
        # Mantener buffer limitado (últimos 10000 puntos)
        if len(self.data_buffer) > 10000:
            self.data_buffer = self.data_buffer[-5000:]
        
        # Actualizar curva
        if self.data_buffer:
            timestamps, velocities = zip(*self.data_buffer)
            self.data_curve.setData(timestamps, velocities)
    
    def add_data_batch(self, timestamps: List[float], angular_velocities: List[float]):
        """
        Añade múltiples puntos de datos de una vez (más eficiente).
        
        Args:
            timestamps: Lista de tiempos en segundos
            angular_velocities: Lista de velocidades angulares
        """
        if len(timestamps) != len(angular_velocities):
            print("Error: timestamps y angular_velocities deben tener la misma longitud")
            return
        
        # Filtrar datos válidos (timestamp >= 0)
        valid_data = [(t, v) for t, v in zip(timestamps, angular_velocities) if t >= 0]
        
        if valid_data:
            self.data_buffer.extend(valid_data)
            
            # Mantener buffer limitado
            if len(self.data_buffer) > 10000:
                self.data_buffer = self.data_buffer[-5000:]
            
            # Actualizar curva
            timestamps, velocities = zip(*self.data_buffer)
            self.data_curve.setData(timestamps, velocities)
            
            print(f"Agregados {len(valid_data)} puntos de datos")
    
    def clear_data(self):
        """Limpia todos los datos del gráfico."""
        self.data_buffer.clear()
        self.data_curve.setData([], [])
        self.set_pos_time_video(0)
        
        print("Datos del gráfico calórico limpiados")
    
    def get_current_phase(self, timestamp: float = None) -> Optional[str]:
        """
        Determina en qué fase se encuentra un timestamp dado.
        
        Args:
            timestamp: Tiempo en segundos (usa current_video_time si es None)
            
        Returns:
            Nombre de la fase actual o None si no está en ninguna
        """
        if timestamp is None:
            timestamp = self.current_video_time
        
        for phase_name, config in self.phase_config.items():
            if config['start'] <= timestamp <= config['end']:
                return phase_name
        
        return None
    
    def get_phase_info(self) -> Dict[str, Any]:
        """
        Retorna información completa sobre las fases y estado actual.
        """
        current_phase = self.get_current_phase()
        
        return {
            'current_time': self.current_video_time,
            'current_phase': current_phase,
            'total_duration': self.total_duration,
            'phases': self.phase_config.copy(),
            'data_points': len(self.data_buffer)
        }
    
    def set_total_duration(self, duration: float):
        """
        Cambia la duración total del gráfico.
        
        Args:
            duration: Nueva duración en segundos
        """
        self.total_duration = duration
        
        # Actualizar límites
        self.plot_widget.setXRange(0, duration, padding=0)
        self.plot_widget.setLimits(xMin=0, xMax=None)
        
        # Actualizar línea de video
        self.video_line.setBounds([0, duration])
        
        # Actualizar regiones de fases si es necesario
        for phase_name, region in self.phase_regions.items():
            config = self.phase_config[phase_name]
            if config['end'] <= duration:
                region.setBounds([0, duration])
        
        print(f"Duración actualizada a {duration}s")
    
    # =========================================================================
    # MÉTODOS PARA CONFIGURACIÓN DE FASES
    # =========================================================================
    
    def set_phase_config(self, new_config: Dict[str, Dict]):
        """
        Establece una nueva configuración completa de fases.
        
        Args:
            new_config: Diccionario con la nueva configuración
                       Formato: {
                           'phase_name': {
                               'start': float, 'end': float, 
                               'color': tuple, 'label': str
                           }
                       }
        """
        if not isinstance(new_config, dict):
            print("Error: new_config debe ser un diccionario")
            return False
        
        # Validar configuración
        for phase_name, config in new_config.items():
            required_keys = ['start', 'end', 'color', 'label']
            if not all(key in config for key in required_keys):
                print(f"Error: Fase '{phase_name}' debe tener keys: {required_keys}")
                return False
            
            if config['start'] >= config['end']:
                print(f"Error: Fase '{phase_name}' - start debe ser menor que end")
                return False
        
        # Aplicar nueva configuración
        self.phase_config = new_config.copy()
        self._rebuild_phases()
        
        # Emitir señal de cambio
        self.phase_config_changed.emit(self.phase_config)
        
        print(f"Nueva configuración de fases aplicada: {list(self.phase_config.keys())}")
        return True
    
    def get_phase_config(self) -> Dict[str, Dict]:
        """
        Obtiene la configuración actual de fases.
        
        Returns:
            Copia de la configuración actual
        """
        return self.phase_config.copy()
    
    def set_phase_timing(self, phase_name: str, start: float, end: float) -> bool:
        """
        Modifica los tiempos de una fase específica.
        
        Args:
            phase_name: Nombre de la fase a modificar
            start: Nuevo tiempo de inicio en segundos
            end: Nuevo tiempo de fin en segundos
            
        Returns:
            True si se modificó exitosamente
        """
        if phase_name not in self.phase_config:
            print(f"Error: Fase '{phase_name}' no existe")
            return False
        
        if start >= end:
            print(f"Error: start ({start}) debe ser menor que end ({end})")
            return False
        
        if start < 0 or end > self.total_duration:
            print(f"Error: Tiempos fuera del rango válido (0-{self.total_duration})")
            return False
        
        # Actualizar configuración
        self.phase_config[phase_name]['start'] = start
        self.phase_config[phase_name]['end'] = end
        
        # Actualizar región visual
        if phase_name in self.phase_regions:
            self.phase_regions[phase_name].setRegion([start, end])
        
        # Actualizar posición del texto
        if phase_name in self.phase_text_items:
            self.phase_text_items[phase_name].setPos((start + end) / 2, 0)
        
        # Emitir señal de cambio
        self.phase_config_changed.emit(self.phase_config)
        
        print(f"Fase '{phase_name}' actualizada: {start}-{end}s")
        return True
    
    def get_phase_timing(self, phase_name: str) -> Optional[Dict[str, float]]:
        """
        Obtiene los tiempos de una fase específica.
        
        Args:
            phase_name: Nombre de la fase
            
        Returns:
            {'start': float, 'end': float} o None si no existe
        """
        if phase_name not in self.phase_config:
            return None
        
        config = self.phase_config[phase_name]
        return {'start': config['start'], 'end': config['end']}
    
    def add_phase(self, phase_name: str, start: float, end: float, 
                  color: tuple = (200, 200, 200, 80), label: str = None) -> bool:
        """
        Añade una nueva fase al gráfico.
        
        Args:
            phase_name: Nombre único de la fase
            start: Tiempo de inicio en segundos
            end: Tiempo de fin en segundos
            color: Color RGBA de la región
            label: Etiqueta visible (usa phase_name si es None)
            
        Returns:
            True si se añadió exitosamente
        """
        if phase_name in self.phase_config:
            print(f"Error: Fase '{phase_name}' ya existe")
            return False
        
        if start >= end or start < 0 or end > self.total_duration:
            print(f"Error: Tiempos inválidos ({start}-{end})")
            return False
        
        # Crear configuración de la nueva fase
        new_phase = {
            'start': start,
            'end': end,
            'color': color,
            'label': label or phase_name
        }
        
        # Añadir a configuración
        self.phase_config[phase_name] = new_phase
        
        # Crear elementos visuales
        region = pg.LinearRegionItem(
            values=[start, end],
            orientation='vertical',
            brush=pg.mkBrush(color),
            movable=False,
            bounds=[0, self.total_duration]
        )
        self.plot_widget.addItem(region)
        self.phase_regions[phase_name] = region
        
        text_item = pg.TextItem(
            text=new_phase['label'],
            color=(50, 50, 50),
            anchor=(0.5, 0)
        )
        text_item.setPos((start + end) / 2, 0)
        self.plot_widget.addItem(text_item)
        self.phase_text_items[phase_name] = text_item
        
        # Emitir señal de cambio
        self.phase_config_changed.emit(self.phase_config)
        
        print(f"Nueva fase añadida: '{phase_name}' ({start}-{end}s)")
        return True
    
    def remove_phase(self, phase_name: str) -> bool:
        """
        Elimina una fase del gráfico.
        
        Args:
            phase_name: Nombre de la fase a eliminar
            
        Returns:
            True si se eliminó exitosamente
        """
        if phase_name not in self.phase_config:
            print(f"Error: Fase '{phase_name}' no existe")
            return False
        
        # Eliminar elementos visuales
        if phase_name in self.phase_regions:
            self.plot_widget.removeItem(self.phase_regions[phase_name])
            del self.phase_regions[phase_name]
        
        if phase_name in self.phase_text_items:
            self.plot_widget.removeItem(self.phase_text_items[phase_name])
            del self.phase_text_items[phase_name]
        
        # Eliminar de configuración
        del self.phase_config[phase_name]
        
        # Emitir señal de cambio
        self.phase_config_changed.emit(self.phase_config)
        
        print(f"Fase '{phase_name}' eliminada")
        return True
    
    def reset_to_default_phases(self):
        """
        Restaura la configuración de fases al default.
        """
        self.set_phase_config(self.DEFAULT_PHASE_CONFIG)
        print("Configuración de fases restaurada al default")


# Ejemplo de uso y testing
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Configuración personalizada de ejemplo
    custom_config = {
        'irrigation': {'start': 0, 'end': 50, 'color': (100, 150, 255, 80), 'label': 'Irrigación Extended'},
        'torok': {'start': 70, 'end': 100, 'color': (255, 150, 100, 80), 'label': 'Período Torok'},
        'fixation': {'start': 100, 'end': 120, 'color': (150, 255, 150, 80), 'label': 'Fijación'}
    }
    
    # Crear widget con configuración personalizada
    widget = CaloricPlotWidget(total_duration=140, phase_config=custom_config)
    widget.show()
    
    # Simular algunos datos de prueba
    import random
    timestamps = np.linspace(0, 140, 1000)
    angular_velocities = [random.uniform(-50, 50) + 20*np.sin(t/10) for t in timestamps]
    
    widget.add_data_batch(timestamps.tolist(), angular_velocities)
    
    # Ejemplo de modificación de fases en tiempo real
    def test_phase_modifications():
        print("\n=== TESTING CONFIGURACIÓN DE FASES ===")
        
        # Obtener configuración actual
        current_config = widget.get_phase_config()
        print(f"Configuración actual: {list(current_config.keys())}")
        
        # Modificar timing de una fase
        widget.set_phase_timing('irrigation', 0, 45)
        
        # Añadir nueva fase
        widget.add_phase('test_phase', 110, 130, (255, 255, 0, 80), 'Fase Test')
        
        # Obtener timing específico
        torok_timing = widget.get_phase_timing('torok')
        print(f"Timing Torok: {torok_timing}")
        
        # Eliminar fase después de 5 segundos
        QTimer.singleShot(5000, lambda: widget.remove_phase('test_phase'))
    
    # Ejecutar tests después de 2 segundos
    QTimer.singleShot(2000, test_phase_modifications)
    
    # Simular movimiento de línea de video
    def simulate_video():
        current = widget.current_video_time + 0.5
        if current <= 140:
            widget.set_pos_time_video(current)
        else:
            widget.set_pos_time_video(0)
    
    timer = QTimer()
    timer.timeout.connect(simulate_video)
    timer.start(100)  # Actualizar cada 100ms
    
    sys.exit(app.exec())