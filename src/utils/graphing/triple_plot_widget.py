from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Signal, QTimer
import pyqtgraph as pg
import numpy as np
from typing import Optional, List, Dict
import time

# Importar el buffer optimizado
try:
    from ..optimized_buffer import OptimizedBuffer
except ImportError:
    try:
        from utils.optimized_buffer import OptimizedBuffer
    except ImportError:
        from optimized_buffer import OptimizedBuffer


class ConfigurablePlotWidget(QWidget):
    """
    Widget configurable que permite activar/desactivar gráficos y curvas específicas.
    VERSIÓN ULTRA-OPTIMIZADA con configuración flexible.
    """
    
    linePositionChanged = Signal(float)
    
    def __init__(self, parent=None, visible_window=60.0, update_fps=10, plot_config=None):
        super().__init__(parent)
        
        # Configuración por defecto
        self.default_config = {
            'show_position_x': True,
            'show_position_y': True, 
            'show_imu': True,
            'show_left_eye': True,
            'show_right_eye': True,
            'line_width': 1,
            'colors': {
                'left_eye': (0, 0, 200),    # Azul
                'right_eye': (200, 0, 0)    # Rojo
            }
        }
        
        # Aplicar configuración personalizada
        self.config = self.default_config.copy()
        if plot_config:
            self.config.update(plot_config)
        
        print(f"Inicializando widget configurable:")
        print(f"  - Posición X: {'✓' if self.config['show_position_x'] else '✗'}")
        print(f"  - Posición Y: {'✓' if self.config['show_position_y'] else '✗'}")
        print(f"  - IMU: {'✓' if self.config['show_imu'] else '✗'}")
        print(f"  - Ojo izquierdo: {'✓' if self.config['show_left_eye'] else '✗'}")
        print(f"  - Ojo derecho: {'✓' if self.config['show_right_eye'] else '✗'}")
        
        # Configuración optimizada
        self.visible_window = visible_window
        self.update_interval = int(1000 / update_fps)
        
        # Buffer inteligente para visualización
        self.display_buffer = OptimizedBuffer(
            visible_window=visible_window,
            max_buffer_size=max(10000, int(visible_window * 200))
        )
        
        # Layout principal
        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)
        
        # Estado de control
        self.is_recording = False
        self.auto_scroll = True
        self._updating_range = False
        
        # Crear gráficos y elementos visuales según configuración
        self.plots = []
        self.curves = []
        self.curve_mapping = {}  # Mapeo de curva a tipo de dato
        self.vLines = []
        self.blink_regions = []
        
        # Configurar PyQtGraph para máximo rendimiento
        pg.setConfigOptions(antialias=False)
        
        # Crear los gráficos según configuración
        self._setup_plots()
        
        # Timer optimizado para actualización visual
        self.display_timer = QTimer()
        self.display_timer.timeout.connect(self._update_display)
        self.display_timer.start(self.update_interval)
        
        # Control de performance
        self.last_update_time = 0
        self.frame_skip_threshold = 0.016  # 60 FPS máximo
        self.update_count = 0
        self.data_points_received = 0
        
        print(f"Timer de visualización iniciado cada {self.update_interval}ms")
        print(f"Total de gráficos creados: {len(self.plots)}")
        print(f"Total de curvas creadas: {len(self.curves)}")
    
    def _setup_plots(self):
        """Configura los gráficos según la configuración especificada."""
        plots_to_create = []
        
        # Determinar qué gráficos crear
        if self.config['show_position_x']:
            plots_to_create.append(('Posición X', 'px'))
        
        if self.config['show_position_y']:
            plots_to_create.append(('Posición Y', 'px'))
        
        if self.config['show_imu']:
            plots_to_create.append(('IMU', 'g'))
        
        if not plots_to_create:
            print("ADVERTENCIA: No se configuró ningún gráfico para mostrar")
            return
        
        print(f"Configurando {len(plots_to_create)} gráficos...")
        
        for i, (label, unit) in enumerate(plots_to_create):
            # Crear gráfico optimizado
            plot = pg.PlotWidget()
            plot.setBackground('w')
            plot.getAxis('bottom').setPen(pg.mkPen(color='black', width=1))
            plot.getAxis('left').setPen(pg.mkPen(color='black', width=1))
            plot.getAxis('bottom').setTextPen(pg.mkPen(color='black'))
            plot.getAxis('left').setTextPen(pg.mkPen(color='black'))
            
            # Configurar etiquetas
            labelStyle = {'color': '#000', 'font-size': '10pt'}
            plot.setLabel('left', label, units=unit, **labelStyle)
            
            # Solo el último gráfico tiene etiqueta de tiempo
            if i == len(plots_to_create) - 1:
                plot.setLabel('bottom', 'Tiempo', units='s', **labelStyle)
            
            # Optimizaciones de rendimiento
            plot.showGrid(x=True, y=True)
            plot.setDownsampling(auto=True, mode='peak')
            plot.setClipToView(True)
            plot.setMouseEnabled(x=True, y=False)
            
            # Crear curvas según configuración
            curves_created = 0
            
            # Ojo izquierdo
            if self.config['show_left_eye']:
                curve_left = plot.plot(
                    pen=pg.mkPen(color=self.config['colors']['left_eye'], 
                               width=self.config['line_width']),
                    name=f"Ojo Izquierdo {label}"
                )
                curve_left.setDownsampling(auto=True, method='peak')
                curve_left.setClipToView(True)
                self.curves.append(curve_left)
                
                # Mapear curva a tipo de dato
                data_type = self._get_data_type_for_plot(label, 'left')
                self.curve_mapping[len(self.curves) - 1] = data_type
                curves_created += 1
            
            # Ojo derecho
            if self.config['show_right_eye']:
                curve_right = plot.plot(
                    pen=pg.mkPen(color=self.config['colors']['right_eye'], 
                               width=self.config['line_width']),
                    name=f"Ojo Derecho {label}"
                )
                curve_right.setDownsampling(auto=True, method='peak')
                curve_right.setClipToView(True)
                self.curves.append(curve_right)
                
                # Mapear curva a tipo de dato
                data_type = self._get_data_type_for_plot(label, 'right')
                self.curve_mapping[len(self.curves) - 1] = data_type
                curves_created += 1
            
            # Solo crear línea vertical si hay curvas
            if curves_created > 0:
                vLine = pg.InfiniteLine(angle=90, movable=True)
                plot.addItem(vLine)
                vLine.sigPositionChanged.connect(self._line_moved_event)
                self.vLines.append(vLine)
                
                # Conectar eventos de rango
                plot.sigRangeChanged.connect(self._on_range_changed)
                
                # Almacenar referencias
                self.plots.append(plot)
                self.blink_regions.append([])
                self.layout.addWidget(plot)
                
                print(f"Gráfico {i+1} configurado: {label} ({curves_created} curvas)")
        
        # Vincular ejes X para sincronización
        for i in range(1, len(self.plots)):
            self.plots[i].setXLink(self.plots[0])
        
        print(f"Todos los gráficos configurados y vinculados")
        print(f"Mapeo de curvas: {self.curve_mapping}")
    
    def _get_data_type_for_plot(self, plot_label: str, eye: str) -> str:
        """Determina el tipo de dato para una curva específica."""
        if plot_label == 'Posición X':
            return f'{eye}_eye_x'
        elif plot_label == 'Posición Y':
            return f'{eye}_eye_y'
        elif plot_label == 'IMU':
            if eye == 'left':
                return 'imu_x'
            else:
                return 'imu_y'
        return 'unknown'
    
    def add_data_point(self, left_eye: Optional[List[float]], right_eye: Optional[List[float]], 
                      imu_x: float, imu_y: float, timestamp: Optional[float] = None):
        """Añade un punto de datos al buffer de visualización."""
        if timestamp is None:
            timestamp = time.time()
        
        # Debug: contar puntos recibidos
        self.data_points_received += 1
        
        # Añadir al buffer inteligente
        self.display_buffer.add_data_point(left_eye, right_eye, imu_x, imu_y, timestamp)
        
        # Debug cada 100 puntos
        if self.data_points_received % 100 == 0:
            buffer_info = self.display_buffer.get_buffer_info()
            #print(f"Puntos recibidos: {self.data_points_received}, Buffer: {buffer_info['current_size']}")
    
    def _update_display(self):
        """Actualiza la visualización de manera optimizada."""
        current_real_time = time.time()
        
        # Control de framerate
        if current_real_time - self.last_update_time < self.frame_skip_threshold:
            return
        
        self.update_count += 1
        
        # Obtener datos visibles
        try:
            visible_data = self.display_buffer.get_downsampled_data(
                max_points=2000,
                current_time=None
            )
            
            if len(visible_data['timestamps']) == 0:
                if self.update_count % 300 == 0:
                    buffer_info = self.display_buffer.get_buffer_info()
                    print(f"Update {self.update_count}: Sin datos visibles. Buffer size: {buffer_info['current_size']}")
                return
            
            # Debug menos frecuente
            if self.update_count % 300 == 0:
                print(f"Update {self.update_count}: {len(visible_data['timestamps'])} puntos visibles")
            
            # Aplicar auto-scroll si está activo
            if self.auto_scroll and self.is_recording:
                self._apply_auto_scroll(visible_data['timestamps'])
            
            # Actualizar curvas según mapeo
            timestamps = visible_data['timestamps']
            for curve_idx, curve in enumerate(self.curves):
                if curve_idx in self.curve_mapping:
                    data_type = self.curve_mapping[curve_idx]
                    
                    if data_type in visible_data:
                        data = visible_data[data_type]
                        
                        if len(data) > 0 and len(timestamps) == len(data):
                            try:
                                curve.setData(timestamps, data)
                            except Exception as e:
                                print(f"Error actualizando curva {curve_idx} ({data_type}): {e}")
                        elif len(data) > 0:
                            print(f"Error: timestamps ({len(timestamps)}) != data ({len(data)}) para {data_type}")
            
            # Actualizar regiones de parpadeo
            self._update_blink_regions(visible_data)
            
            self.last_update_time = current_real_time
            
            # Debug exitoso
            if self.update_count % 500 == 0:
                active_plots = len(self.plots)
                active_curves = len(self.curves)
                print(f"Display actualizado exitosamente #{self.update_count} ({active_plots} gráficos, {active_curves} curvas)")
            
        except Exception as e:
            print(f"Error en actualización de display: {e}")
            import traceback
            traceback.print_exc()
    
    def _apply_auto_scroll(self, timestamps: np.ndarray):
        """Aplica auto-scroll optimizado."""
        if len(timestamps) == 0:
            return
        
        current_time = timestamps[-1]
        
        # Calcular ventana visible
        if current_time < self.visible_window * 2/3:
            window_start = 0
            window_end = self.visible_window
        else:
            window_start = current_time - (self.visible_window * 2/3)
            window_end = window_start + self.visible_window
        
        # Aplicar rango con flag para evitar bucles
        self._updating_range = True
        try:
            for plot in self.plots:
                plot.setXRange(window_start, window_end, padding=0)
        except Exception as e:
            print(f"Error en auto-scroll: {e}")
        finally:
            self._updating_range = False
    
    def _update_blink_regions(self, visible_data: Dict):
        """Actualiza las regiones de parpadeo de manera eficiente."""
        try:
            # Obtener regiones de parpadeo
            left_regions, right_regions = self.display_buffer.get_blink_regions()
            
            # Limpiar regiones existentes
            for plot_idx, plot in enumerate(self.plots):
                for region in self.blink_regions[plot_idx]:
                    try:
                        plot.removeItem(region)
                    except:
                        pass
                self.blink_regions[plot_idx].clear()
            
            # Añadir nuevas regiones solo si se muestran los ojos correspondientes
            for plot_idx, plot in enumerate(self.plots):
                # Regiones de ojo izquierdo (azul)
                if self.config['show_left_eye']:
                    for start, end in left_regions:
                        if end > start and (end - start) > 0.01:
                            try:
                                region = pg.LinearRegionItem(
                                    values=[start, end],
                                    brush=pg.mkBrush(0, 0, 255, 50),
                                    movable=False
                                )
                                plot.addItem(region)
                                self.blink_regions[plot_idx].append(region)
                            except Exception as e:
                                print(f"Error añadiendo región izquierda: {e}")
                
                # Regiones de ojo derecho (rojo)
                if self.config['show_right_eye']:
                    for start, end in right_regions:
                        if end > start and (end - start) > 0.01:
                            try:
                                region = pg.LinearRegionItem(
                                    values=[start, end], 
                                    brush=pg.mkBrush(255, 0, 0, 50),
                                    movable=False
                                )
                                plot.addItem(region)
                                self.blink_regions[plot_idx].append(region)
                            except Exception as e:
                                print(f"Error añadiendo región derecha: {e}")
                        
        except Exception as e:
            print(f"Error actualizando regiones de parpadeo: {e}")
    
    def _line_moved_event(self):
        """Maneja el movimiento de la línea vertical."""
        try:
            sender = self.sender()
            newX = sender.value()
            
            # Sincronizar todas las líneas
            for vLine in self.vLines:
                if vLine != sender:
                    vLine.setValue(newX)
            
            self.linePositionChanged.emit(newX)
        except Exception as e:
            print(f"Error en line_moved_event: {e}")
    
    def _on_range_changed(self, plot, ranges):
        """Maneja cambios de rango para controlar auto-scroll."""
        try:
            if len(self.plots) > 0 and plot == self.plots[0] and not self._updating_range:
                if not self.is_recording:
                    view_range = self.plots[0].viewRange()
                    current_max = view_range[0][1]
                    
                    if self.display_buffer.last_update_time > 0:
                        data_max = self.display_buffer.last_update_time
                        if abs(current_max - data_max) < self.visible_window / 10:
                            self.auto_scroll = True
                        else:
                            self.auto_scroll = False
        except Exception as e:
            print(f"Error en range_changed: {e}")
    
    def set_recording_state(self, is_recording: bool):
        """Establece el estado de grabación."""
        self.is_recording = is_recording
        if is_recording:
            self.auto_scroll = True
            print("Gráfico configurable: Auto-scroll activado para grabación")
        else:
            print("Gráfico configurable: Grabación detenida, modo exploración disponible")
    
    def clear_data(self):
        """Limpia todos los datos del buffer de visualización."""
        print("Limpiando datos del gráfico configurable...")
        
        self.display_buffer.clear()
        self.auto_scroll = True
        
        # Limpiar curvas
        for curve in self.curves:
            try:
                curve.setData([], [])
            except:
                pass
        
        # Limpiar regiones de parpadeo
        for plot_idx, plot in enumerate(self.plots):
            for region in self.blink_regions[plot_idx]:
                try:
                    plot.removeItem(region)
                except:
                    pass
            self.blink_regions[plot_idx].clear()
        
        # Reset contadores
        self.update_count = 0
        self.data_points_received = 0
        
        print("Datos del gráfico configurable limpiados")
    
    def set_visible_window(self, seconds: float):
        """Cambia el tamaño de la ventana visible."""
        self.visible_window = seconds
        self.display_buffer.set_visible_window(seconds)
        print(f"Ventana visible cambiada a {seconds}s")
    
    def set_update_fps(self, fps: int):
        """Cambia la frecuencia de actualización."""
        new_interval = int(1000 / max(1, min(fps, 60)))
        self.update_interval = new_interval
        self.display_timer.setInterval(self.update_interval)
        
        self.frame_skip_threshold = 1.0 / (fps * 1.5)
        
        print(f"FPS cambiado a {fps} (intervalo: {new_interval}ms)")
    
    def get_buffer_info(self) -> Dict:
        """Obtiene información del estado del buffer."""
        return self.display_buffer.get_buffer_info()
    
    def optimize_performance(self):
        """Aplica optimizaciones automáticas de performance."""
        self.display_buffer.optimize_for_performance()
        
        buffer_info = self.get_buffer_info()
        if buffer_info['utilization_percent'] > 80:
            self.set_update_fps(5)
            print("Performance optimizada: FPS reducido a 5")
        elif buffer_info['utilization_percent'] < 50:
            self.set_update_fps(10)
    
    def export_visible_data(self) -> Dict:
        """Exporta los datos actualmente visibles."""
        return self.display_buffer.get_visible_data()
    
    def get_configuration_summary(self) -> str:
        """Retorna un resumen de la configuración actual."""
        summary = f"Configuración del widget de gráficos:\n"
        summary += f"  - Gráficos activos: {len(self.plots)}\n"
        summary += f"  - Curvas activas: {len(self.curves)}\n"
        summary += f"  - Posición X: {'✓' if self.config['show_position_x'] else '✗'}\n"
        summary += f"  - Posición Y: {'✓' if self.config['show_position_y'] else '✗'}\n"
        summary += f"  - IMU: {'✓' if self.config['show_imu'] else '✗'}\n"
        summary += f"  - Ojo izquierdo: {'✓' if self.config['show_left_eye'] else '✗'}\n"
        summary += f"  - Ojo derecho: {'✓' if self.config['show_right_eye'] else '✗'}\n"
        return summary
    
    def closeEvent(self, event):
        """Limpia recursos al cerrar."""
        print("Cerrando widget de gráficos configurable...")
        self.display_timer.stop()
        self.clear_data()
        super().closeEvent(event)


# Configuraciones predefinidas para casos comunes
class PlotConfigurations:
    """Configuraciones predefinidas para el widget de gráficos."""
    
    @staticmethod
    def get_ultra_minimal():
        """Solo movimiento horizontal del ojo derecho (máximo rendimiento)."""
        return {
            'show_position_x': True,
            'show_position_y': False,
            'show_imu': False,
            'show_left_eye': False,
            'show_right_eye': True,
            'line_width': 2,
            'colors': {
                'right_eye': (200, 0, 0)
            }
        }
    
    @staticmethod
    def get_horizontal_only():
        """Solo movimientos horizontales de ambos ojos."""
        return {
            'show_position_x': True,
            'show_position_y': False,
            'show_imu': False,
            'show_left_eye': True,
            'show_right_eye': True,
            'line_width': 1,
            'colors': {
                'left_eye': (0, 0, 200),
                'right_eye': (200, 0, 0)
            }
        }
    
    @staticmethod
    def get_eyes_only():
        """Solo datos oculares (sin IMU)."""
        return {
            'show_position_x': True,
            'show_position_y': True,
            'show_imu': False,
            'show_left_eye': True,
            'show_right_eye': True,
            'line_width': 1,
            'colors': {
                'left_eye': (0, 0, 200),
                'right_eye': (200, 0, 0)
            }
        }
    
    @staticmethod
    def get_full():
        """Configuración completa (todos los gráficos y curvas)."""
        return {
            'show_position_x': True,
            'show_position_y': True,
            'show_imu': True,
            'show_left_eye': True,
            'show_right_eye': True,
            'line_width': 1,
            'colors': {
                'left_eye': (0, 0, 200),
                'right_eye': (200, 0, 0)
            }
        }
    
    @staticmethod
    def get_left_eye_only():
        """Solo ojo izquierdo (todos los gráficos)."""
        return {
            'show_position_x': True,
            'show_position_y': True,
            'show_imu': True,
            'show_left_eye': True,
            'show_right_eye': False,
            'line_width': 2,
            'colors': {
                'left_eye': (0, 0, 200)
            }
        }
    
    @staticmethod
    def get_right_eye_only():
        """Solo ojo derecho (todos los gráficos)."""
        return {
            'show_position_x': True,
            'show_position_y': True,
            'show_imu': True,
            'show_left_eye': False,
            'show_right_eye': True,
            'line_width': 2,
            'colors': {
                'right_eye': (200, 0, 0)
            }
        }


# Mantener compatibilidad con código existente
class TriplePlotWidget(ConfigurablePlotWidget):
    """Alias para compatibilidad hacia atrás con configuración por defecto."""
    
    def __init__(self, parent=None, window_size=60, update_interval=16, plot_config=None):
        # Convertir parámetros del formato anterior
        fps = int(1000 / update_interval) if update_interval > 0 else 10
        
        # Si no se especifica configuración, usar configuración eficiente por defecto
        if plot_config is None:
            plot_config = PlotConfigurations.get_horizontal_only()  # Solo horizontal para mejor rendimiento
        
        super().__init__(parent, visible_window=window_size, update_fps=fps, plot_config=plot_config)
        print(f"TriplePlotWidget inicializado con configuración optimizada")
        print(self.get_configuration_summary())
    
    def updatePlots(self, data):
        """Método de compatibilidad con la interfaz anterior."""
        if len(data) != 5:
            raise ValueError("Se requieren exactamente 5 valores")
        
        left_eye = data[0]
        right_eye = data[1] 
        imu_x = float(data[2])
        imu_y = float(data[3])
        timestamp = float(data[4])
        
        self.add_data_point(left_eye, right_eye, imu_x, imu_y, timestamp)
    
    def clearPlots(self):
        """Método de compatibilidad."""
        self.clear_data()