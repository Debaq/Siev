from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Signal, QTimer

from .base_plot import BasePlotFactory
from .data_processor import DataProcessor
from .blink_detector import BlinkDetector
from .visual_manager import VisualManager


class TriplePlotWidget(QWidget):
    """Widget que muestra tres gráficos sincronizados para visualizar datos oculares."""
    
    linePositionChanged = Signal(float)
    
    def __init__(self, parent=None, window_size=60, update_interval=16):
        super().__init__(parent)
        
        # Configuración inicial del widget
        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)
        
        # Inicializar componentes principales
        self.data_processor = DataProcessor()
        self.blink_detector = BlinkDetector()
        self.visual_manager = VisualManager(window_size=window_size)
        
        # Crear los gráficos
        self.plots = []
        self.curves = []
        self.vLines = []
        self._setup_plots()
        
        # Estado de grabación
        self.is_recording = False
        
        # Timers para actualización
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.process_data_queue)
        self.update_timer.start(update_interval)
        
        self.display_timer = QTimer()
        self.display_timer.timeout.connect(self.update_display)
        self.display_timer.start(1000)  # ~30 FPS para visualización
    
    def _setup_plots(self):
        """Configura los tres gráficos y sus curvas."""
        # Crear los tres gráficos
        for i in range(3):
            # Crear gráfico con configuración estándar
            plot = BasePlotFactory.create_plot()
            
            # Configurar etiquetas específicas
            if i == 0:
                plot.setLabel('left', 'Posición X', units='px')
            elif i == 1:
                plot.setLabel('left', 'Posición Y', units='px')
            else:  # i == 2
                plot.setLabel('left', 'IMU', units='g')
                plot.setLabel('bottom', 'Tiempo', units='s')
            
            # Añadir curvas para ojo izquierdo (azul) y derecho (rojo)
            curve_left = BasePlotFactory.create_curve(plot, is_left_eye=True)
            curve_right = BasePlotFactory.create_curve(plot, is_left_eye=False)
            
            # Añadir línea vertical para el tiempo seleccionado
            vLine = BasePlotFactory.create_infinite_line(plot)
            vLine.sigPositionChanged.connect(self.lineMovedEvent)
            self.vLines.append(vLine)
            
            # Añadir gráfico y curvas a las listas
            self.plots.append(plot)
            self.curves.append(curve_left)
            self.curves.append(curve_right)
            
            # Añadir al layout
            self.layout.addWidget(plot)
        
        # Vincular ejes X para sincronizar
        for i in range(1, 3):
            self.plots[i].setXLink(self.plots[0])
        
        # Configurar comportamiento del ratón
        for plot in self.plots:
            plot.setMouseEnabled(x=True, y=False)
            plot.sigRangeChanged.connect(self.on_range_changed)
    
    def lineMovedEvent(self):
        """Maneja el evento de movimiento de la línea vertical."""
        sender = self.sender()
        newX = sender.value()
        
        # Sincronizar todas las líneas verticales
        for vLine in self.vLines:
            if vLine != sender:
                vLine.setValue(newX)
        
        # Emitir señal con la nueva posición
        self.linePositionChanged.emit(newX)
    
    def on_range_changed(self, plot, ranges):
        """
        Maneja el evento de cambio de rango en los gráficos.
        Actualiza el estado de auto-scroll según el comportamiento del usuario.
        """
        # Solo procesar eventos del primer gráfico (los demás están vinculados)
        if plot == self.plots[0]:
            # Evitar bucles de actualización
            if not hasattr(self.visual_manager, '_updating_range') or not self.visual_manager._updating_range:
                # Solo permitir control manual cuando no está grabando
                if not self.is_recording:
                    view_range = self.plots[0].viewRange()
                    current_max = view_range[0][1]
                    
                    if len(self.data_processor.x_data) > 0:
                        data_max = self.data_processor.x_data[-1]
                        # Si el extremo derecho de la vista está cerca del dato más reciente,
                        # consideramos que debe activarse el auto_scroll
                        if abs(current_max - data_max) < self.visual_manager.window_size / 10:
                            self.visual_manager.set_auto_scroll(True)
                        else:
                            # Si el usuario ha movido la vista lejos del final,
                            # desactivamos el auto_scroll
                            self.visual_manager.set_auto_scroll(False)
    
    def process_data_queue(self):
        """Procesa los datos en la cola."""
        # Procesar datos de la cola
        data_processed = self.data_processor.process_queue(max_process=100)
        
        # Verificar nivel de optimización si hay nuevos datos
        if data_processed:
            data_size = len(self.data_processor.x_data)
            self.visual_manager.set_optimization_level(data_size)
    
    def update_display(self):
        """Actualiza la visualización de los gráficos."""
        # Si no hay datos, no hacer nada
        if not self.data_processor.x_data:
            return
        
        # Actualizar gráficos
        self.visual_manager.update_plots(
            self.plots,
            self.curves,
            self.data_processor.x_data,
            self.data_processor.y_data,
            self.blink_detector
        )
    
    def updatePlots(self, data):
        """
        Añade nuevos datos para visualizar.
        
        Args:
            data: Lista con [ojo_izq, ojo_der, imu_x, imu_y, tiempo]
        """
        if len(data) != 5:
            raise ValueError("Se requieren exactamente 5 valores (ojo_izq, ojo_der, imu_x, imu_y, tiempo)")
        
        # Actualizar datos
        self.data_processor.add_data(data)
        
        # Procesar parpadeos
        left_eye = data[0]
        right_eye = data[1]
        current_time = float(data[4])
        
        self.blink_detector.process_blink_left_eye(left_eye, current_time)
        self.blink_detector.process_blink_right_eye(right_eye, current_time)
    
    def clearPlots(self):
        """Limpia todos los datos de los gráficos."""
        self.data_processor.clear_data()
        self.blink_detector.clear()
        self.visual_manager.set_auto_scroll(True)
        
        # Restablecer configuraciones de optimización
        self.visual_manager.optimization_config['downsampling_enabled'] = False
    
    def set_recording_state(self, is_recording):
        """
        Establece el estado de grabación.
        
        Args:
            is_recording: True si está grabando, False si no
        """
        self.is_recording = is_recording
        self.visual_manager.set_auto_scroll(True, is_recording=is_recording)
        
        if is_recording:
            print("Gráfico: Auto-scroll activado para grabación")
        else:
            print("Gráfico: Grabación detenida, modo exploración disponible")
    
    def set_auto_scroll(self, enabled):
        """
        Activa o desactiva manualmente el auto-scroll.
        
        Args:
            enabled: True para activar, False para desactivar
        """
        self.visual_manager.set_auto_scroll(enabled, is_recording=self.is_recording)
    
    def get_data(self):
        """
        Obtiene una copia de todos los datos almacenados.
        
        Returns:
            dict: Datos de series temporales y parpadeos
        """
        data_copy = self.data_processor.get_data_copy()
        blink_data = self.blink_detector.get_blink_data()
        
        # Combinar datos
        data_copy.update(blink_data)
        return data_copy
    
    def export_data(self, filename):
        """
        Exporta los datos a un archivo CSV.
        
        Args:
            filename: Ruta del archivo donde guardar los datos
        """
        self.data_processor.export_to_csv(filename)
    
    def closeEvent(self, event):
        """Maneja el evento de cierre del widget."""
        self.update_timer.stop()
        self.display_timer.stop()
        super().closeEvent(event)