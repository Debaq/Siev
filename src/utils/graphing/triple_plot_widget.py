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


class OptimizedTriplePlotWidget(QWidget):
    """
    Widget optimizado que muestra tres gráficos sincronizados.
    VERSIÓN CORREGIDA - Ahora grafica correctamente.
    """
    
    linePositionChanged = Signal(float)
    
    def __init__(self, parent=None, visible_window=60.0, update_fps=10):
        super().__init__(parent)
        
        print(f"Inicializando OptimizedTriplePlotWidget con ventana de {visible_window}s a {update_fps} FPS")
        
        # Configuración optimizada
        self.visible_window = visible_window
        self.update_interval = int(1000 / update_fps)  # Convertir FPS a ms
        
        # Buffer inteligente para visualización
        self.display_buffer = OptimizedBuffer(
            visible_window=visible_window,
            max_buffer_size=max(10000, int(visible_window * 200))  # ~200 Hz estimado
        )
        
        # Layout principal
        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)
        
        # Estado de control
        self.is_recording = False
        self.auto_scroll = True
        self._updating_range = False
        
        # Crear gráficos y elementos visuales
        self.plots = []
        self.curves = []
        self.vLines = []
        self.blink_regions = [[] for _ in range(3)]  # Para cada gráfico
        
        # Configurar PyQtGraph para máximo rendimiento
        pg.setConfigOptions(antialias=False)
        
        # Crear los tres gráficos
        self._setup_plots()
        
        # Timer optimizado para actualización visual
        self.display_timer = QTimer()
        self.display_timer.timeout.connect(self._update_display)
        self.display_timer.start(self.update_interval)
        print(f"Timer de visualización iniciado cada {self.update_interval}ms")
        
        # Control de performance
        self.last_update_time = 0
        self.frame_skip_threshold = 0.016  # 60 FPS máximo
        self.update_count = 0
        self.data_points_received = 0
    
    def _setup_plots(self):
        """Configura los tres gráficos optimizados."""
        plot_labels = [
            ('Posición X', 'px'),
            ('Posición Y', 'px'), 
            ('IMU', 'g')
        ]
        
        print("Configurando 3 gráficos...")
        
        for i, (label, unit) in enumerate(plot_labels):
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
            if i == 2:  # Solo el último gráfico tiene etiqueta de tiempo
                plot.setLabel('bottom', 'Tiempo', units='s', **labelStyle)
            
            # Optimizaciones de rendimiento
            plot.showGrid(x=True, y=True)
            plot.setDownsampling(auto=True, mode='peak')
            plot.setClipToView(True)
            plot.setMouseEnabled(x=True, y=False)
            
            # Crear curvas optimizadas
            # Ojo izquierdo (azul)
            curve_left = plot.plot(
                pen=pg.mkPen(color=(0, 0, 200), width=1),
                name="Ojo Izquierdo"
            )
            curve_left.setDownsampling(auto=True, method='peak')
            curve_left.setClipToView(True)
            
            # Ojo derecho (rojo)  
            curve_right = plot.plot(
                pen=pg.mkPen(color=(200, 0, 0), width=1),
                name="Ojo Derecho"
            )
            curve_right.setDownsampling(auto=True, method='peak')
            curve_right.setClipToView(True)
            
            # Línea vertical para tiempo seleccionado
            vLine = pg.InfiniteLine(angle=90, movable=True)
            plot.addItem(vLine)
            vLine.sigPositionChanged.connect(self._line_moved_event)
            
            # Conectar eventos de rango
            plot.sigRangeChanged.connect(self._on_range_changed)
            
            # Almacenar referencias
            self.plots.append(plot)
            self.curves.extend([curve_left, curve_right])
            self.vLines.append(vLine)
            self.layout.addWidget(plot)
            
            print(f"Gráfico {i+1} configurado: {label}")
        
        # Vincular ejes X para sincronización
        for i in range(1, 3):
            self.plots[i].setXLink(self.plots[0])
        
        print("Todos los gráficos configurados y vinculados")
    
    def add_data_point(self, left_eye: Optional[List[float]], right_eye: Optional[List[float]], 
                      imu_x: float, imu_y: float, timestamp: Optional[float] = None):
        """
        Añade un punto de datos al buffer de visualización.
        """
        if timestamp is None:
            timestamp = time.time()
        
        # Debug: contar puntos recibidos
        self.data_points_received += 1
        
        # Añadir al buffer inteligente
        self.display_buffer.add_data_point(left_eye, right_eye, imu_x, imu_y, timestamp)
        
        # Debug cada 100 puntos
        if self.data_points_received % 100 == 0:
            buffer_info = self.display_buffer.get_buffer_info()
            print(f"Puntos recibidos: {self.data_points_received}, Buffer: {buffer_info['current_size']}")
    
    def _update_display(self):
        """Actualiza la visualización de manera optimizada."""
        current_time = time.time()
        
        # Control de framerate - evitar actualizaciones demasiado frecuentes
        if current_time - self.last_update_time < self.frame_skip_threshold:
            return
        
        self.update_count += 1
        
        # Obtener datos visibles con downsampling automático
        try:
            visible_data = self.display_buffer.get_downsampled_data(
                max_points=2000,  # Máximo para performance
                current_time=current_time
            )
            
            if len(visible_data['timestamps']) == 0:
                # Debug: no hay datos disponibles
                if self.update_count % 100 == 0:  # Debug cada 100 updates
                    buffer_info = self.display_buffer.get_buffer_info()
                    print(f"Update {self.update_count}: Sin datos visibles. Buffer size: {buffer_info['current_size']}")
                return
            
            # Debug: datos disponibles
            if self.update_count % 100 == 0:
                print(f"Update {self.update_count}: {len(visible_data['timestamps'])} puntos visibles")
            
            # Aplicar auto-scroll si está activo
            if self.auto_scroll and self.is_recording:
                self._apply_auto_scroll(visible_data['timestamps'])
            
            # Actualizar las 6 curvas (3 gráficos x 2 ojos)
            data_arrays = [
                visible_data['left_eye_x'],    # Gráfico 0, ojo izquierdo X
                visible_data['right_eye_x'],   # Gráfico 0, ojo derecho X
                visible_data['left_eye_y'],    # Gráfico 1, ojo izquierdo Y  
                visible_data['right_eye_y'],   # Gráfico 1, ojo derecho Y
                visible_data['imu_x'],         # Gráfico 2, IMU X
                visible_data['imu_y']          # Gráfico 2, IMU Y
            ]
            
            # Actualizar curvas de manera eficiente
            timestamps = visible_data['timestamps']
            for i, (curve, data) in enumerate(zip(self.curves, data_arrays)):
                if len(data) > 0:
                    # Verificar que los datos son válidos
                    if len(timestamps) == len(data):
                        try:
                            curve.setData(timestamps, data)
                        except Exception as e:
                            print(f"Error actualizando curva {i}: {e}")
                    else:
                        print(f"Error: timestamps ({len(timestamps)}) != data ({len(data)}) para curva {i}")
            
            # Actualizar regiones de parpadeo
            self._update_blink_regions(visible_data)
            
            self.last_update_time = current_time
            
            # Debug exitoso cada 100 updates
            if self.update_count % 100 == 0:
                print(f"Display actualizado exitosamente #{self.update_count}")
            
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
            # Etapa inicial
            window_start = 0
            window_end = self.visible_window
        else:
            # Etapa de deslizamiento
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
                        pass  # Ignorar errores al remover
                self.blink_regions[plot_idx].clear()
            
            # Añadir nuevas regiones
            for plot_idx, plot in enumerate(self.plots):
                # Regiones de ojo izquierdo (azul)
                for start, end in left_regions:
                    if end > start and (end - start) > 0.01:  # Validar región mínima
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
                for start, end in right_regions:
                    if end > start and (end - start) > 0.01:  # Validar región mínima
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
            if plot == self.plots[0] and not self._updating_range:
                if not self.is_recording:
                    view_range = self.plots[0].viewRange()
                    current_max = view_range[0][1]
                    
                    if self.display_buffer.last_update_time > 0:
                        data_max = self.display_buffer.last_update_time
                        # Si está cerca del final, activar auto-scroll
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
            print("Gráfico optimizado: Auto-scroll activado para grabación")
        else:
            print("Gráfico optimizado: Grabación detenida, modo exploración disponible")
    
    def clear_data(self):
        """Limpia todos los datos del buffer de visualización."""
        print("Limpiando datos del gráfico...")
        
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
        
        # Reset contadores de debug
        self.update_count = 0
        self.data_points_received = 0
        
        print("Datos del gráfico limpiados")
    
    def set_visible_window(self, seconds: float):
        """Cambia el tamaño de la ventana visible."""
        self.visible_window = seconds
        self.display_buffer.set_visible_window(seconds)
        print(f"Ventana visible cambiada a {seconds}s")
    
    def set_update_fps(self, fps: int):
        """Cambia la frecuencia de actualización."""
        new_interval = int(1000 / max(1, min(fps, 60)))  # Límite entre 1-60 FPS
        self.update_interval = new_interval
        self.display_timer.setInterval(self.update_interval)
        
        # Ajustar threshold de frame skip
        self.frame_skip_threshold = 1.0 / (fps * 1.5)
        
        print(f"FPS cambiado a {fps} (intervalo: {new_interval}ms)")
    
    def get_buffer_info(self) -> Dict:
        """Obtiene información del estado del buffer."""
        return self.display_buffer.get_buffer_info()
    
    def optimize_performance(self):
        """Aplica optimizaciones automáticas de performance."""
        self.display_buffer.optimize_for_performance()
        
        # Ajustar FPS basado en carga
        buffer_info = self.get_buffer_info()
        if buffer_info['utilization_percent'] > 80:
            # Reducir FPS si el buffer está muy lleno
            self.set_update_fps(5)
            print("Performance optimizada: FPS reducido a 5")
        elif buffer_info['utilization_percent'] < 50:
            # Aumentar FPS si hay poco uso
            self.set_update_fps(10)
    
    def export_visible_data(self) -> Dict:
        """Exporta los datos actualmente visibles."""
        return self.display_buffer.get_visible_data()
    
    def closeEvent(self, event):
        """Limpia recursos al cerrar."""
        print("Cerrando OptimizedTriplePlotWidget...")
        self.display_timer.stop()
        self.clear_data()
        super().closeEvent(event)


# Mantener compatibilidad con código existente
class TriplePlotWidget(OptimizedTriplePlotWidget):
    """Alias para compatibilidad hacia atrás."""
    
    def __init__(self, parent=None, window_size=60, update_interval=16):
        # Convertir parámetros del formato anterior
        fps = int(1000 / update_interval) if update_interval > 0 else 10
        super().__init__(parent, visible_window=window_size, update_fps=fps)
        print(f"TriplePlotWidget inicializado con compatibilidad (window_size={window_size}, fps={fps})")
    
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