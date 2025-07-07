import numpy as np
import pyqtgraph as pg


class VisualManager:
    """Gestiona la representación visual de los datos en los gráficos."""
    
    def __init__(self, window_size=60):
        self.window_size = window_size
        self.auto_scroll = True
        self._updating_range = False
        
        # Configuración para optimización visual
        self.optimization_config = {
            'max_visible_points': 2000,         # Máximo de puntos a mostrar a la vez
            'max_visible_blinks': 50,           # Máximo de regiones de parpadeo visibles
            'downsampling_enabled': False,      # Activar/desactivar downsampling visual
            'auto_optimize': True               # Activar optimización automática según cantidad de datos
        }
    
    def update_plots(self, plots, curves, x_data, y_data, blink_detector):
        """
        Actualiza la visualización de los gráficos.
        
        Args:
            plots: Lista de objetos PlotWidget
            curves: Lista de objetos PlotDataItem
            x_data: Lista de valores de tiempo
            y_data: Lista de listas con datos para cada curva
            blink_detector: Instancia de BlinkDetector
            
        Returns:
            bool: True si la actualización fue exitosa
        """
        if not x_data:
            return False
            
        try:
            # Convertir a arrays para operaciones más rápidas
            x_array = np.array(x_data, dtype=np.float64)
            
            # Obtener rango de tiempo visible
            if self.auto_scroll:
                current_time = x_data[-1]
                view_start = max(0, current_time - (self.window_size * 2/3))
                view_end = view_start + self.window_size
            else:
                # Si auto_scroll está desactivado, obtener la vista actual
                view_range = plots[0].viewRange()
                view_start = view_range[0][0]
                view_end = view_range[0][1]
            
            # Aplicar auto-scroll si está activo
            if self.auto_scroll:
                self._apply_auto_scroll(plots, x_data)
            
            # Obtener datos visibles
            visible_indices = self._get_visible_indices(x_array, view_start, view_end)
            
            # Actualizar curvas con datos visibles
            if len(visible_indices) > 0:
                visible_x = x_array[visible_indices]
                
                for i, curve in enumerate(curves):
                    if i < len(y_data) and len(y_data[i]) == len(x_array):
                        y_array = np.array(y_data[i], dtype=np.float64)
                        visible_y = y_array[visible_indices]
                        curve.setData(visible_x, visible_y)
            
            # Actualizar regiones de parpadeo
            self._update_blink_regions(plots, blink_detector, view_start, view_end, x_data[-1])
            
            return True
        except Exception as e:
            print(f"Error al actualizar visualización: {e}")
            return False
    
    def _apply_auto_scroll(self, plots, x_data):
        """
        Aplica el auto-scroll a todos los gráficos.
        
        Args:
            plots: Lista de objetos PlotWidget
            x_data: Lista de valores de tiempo
        """
        if not x_data or not self.auto_scroll:
            return
            
        current_time = x_data[-1]
        
        # Verificar si hay suficientes datos para llenar 2/3 de la ventana
        if current_time < self.window_size * 2/3:
            # Etapa inicial: mostrar desde 0 hasta el tamaño de ventana fijo
            window_start = 0
            window_end = self.window_size
        else:
            # Etapa de deslizamiento: mantener el último dato a 2/3 de la ventana
            window_start = current_time - (self.window_size * 2/3)
            window_end = window_start + self.window_size
        
        # Establecer flag para evitar bucles de actualización
        self._updating_range = True
        
        # Aplicar el rango a todos los gráficos sin padding
        for plot in plots:
            plot.setXRange(window_start, window_end, padding=0)
            
        # Limpiar flag después de la actualización
        self._updating_range = False
    
    def _get_visible_indices(self, x_array, view_start, view_end):
        """
        Obtiene los índices de datos visibles en la ventana actual.
        
        Args:
            x_array: Array NumPy con valores de tiempo
            view_start: Tiempo de inicio de la ventana
            view_end: Tiempo de fin de la ventana
            
        Returns:
            numpy.ndarray: Array de índices para los datos visibles
        """
        # Si hay pocos datos, simplemente devolver todos los índices
        if len(x_array) <= self.optimization_config['max_visible_points']:
            return np.arange(len(x_array))
            
        # Para conjuntos de datos grandes, encontrar un subconjunto óptimo
        # 1. Encontrar el rango de índices dentro de la ventana visible
        in_range_mask = (x_array >= view_start) & (x_array <= view_end)
        indices_in_range = np.where(in_range_mask)[0]
        
        # Si no hay datos en el rango visible, retornar un array vacío
        if len(indices_in_range) == 0:
            return np.array([], dtype=int)
            
        # Si hay pocos puntos en la ventana visible, mostrarlos todos
        if len(indices_in_range) <= self.optimization_config['max_visible_points']:
            return indices_in_range
        
        # 2. Aplicar downsampling visual solo si está habilitado
        if self.optimization_config['downsampling_enabled']:
            # Calcular factor de downsampling para ajustar al número máximo de puntos visibles
            downsample_factor = max(1, len(indices_in_range) // self.optimization_config['max_visible_points'])
            return indices_in_range[::downsample_factor]
        else:
            # Si el downsampling está desactivado, mostrar todos los puntos en la ventana
            return indices_in_range
    
    def _update_blink_regions(self, plots, blink_detector, view_start, view_end, current_time):
        """
        Actualiza las regiones de parpadeo en los gráficos.
        
        Args:
            plots: Lista de objetos PlotWidget
            blink_detector: Instancia de BlinkDetector
            view_start: Tiempo de inicio de la ventana visible
            view_end: Tiempo de fin de la ventana visible
            current_time: Tiempo actual
        """
        # Obtener regiones de parpadeo visibles
        visible_left_blinks, visible_right_blinks = blink_detector.get_visible_blink_regions(
            view_start, view_end, self.optimization_config['max_visible_blinks']
        )
        
        # Limpiar regiones existentes en todos los gráficos
        for plot in plots:
            # Eliminar todas las regiones existentes
            for item in plot.items():
                if isinstance(item, pg.LinearRegionItem):
                    plot.removeItem(item)
            
            # Añadir regiones de parpadeo para ojo izquierdo
            for start, end in visible_left_blinks:
                if end > start:  # Asegurarse de que la región es válida
                    region = pg.LinearRegionItem(
                        values=[start, end],
                        brush=pg.mkBrush(0, 0, 255, 50),  # Azul semi-transparente
                        movable=False
                    )
                    plot.addItem(region)
            
            # Añadir regiones de parpadeo para ojo derecho
            for start, end in visible_right_blinks:
                if end > start:  # Asegurarse de que la región es válida
                    region = pg.LinearRegionItem(
                        values=[start, end],
                        brush=pg.mkBrush(255, 0, 0, 50),  # Rojo semi-transparente
                        movable=False
                    )
                    plot.addItem(region)
            
            # Añadir parpadeos en curso
            if blink_detector.left_blinking and blink_detector.blink_start_time["left"] is not None:
                region = pg.LinearRegionItem(
                    values=[blink_detector.blink_start_time["left"], current_time],
                    brush=pg.mkBrush(0, 0, 255, 50),  # Azul semi-transparente
                    movable=False
                )
                plot.addItem(region)
                
            if blink_detector.right_blinking and blink_detector.blink_start_time["right"] is not None:
                region = pg.LinearRegionItem(
                    values=[blink_detector.blink_start_time["right"], current_time],
                    brush=pg.mkBrush(255, 0, 0, 50),  # Rojo semi-transparente
                    movable=False
                )
                plot.addItem(region)
    
    def set_window_size(self, window_size):
        """Establece el tamaño de la ventana visible en segundos."""
        self.window_size = window_size
    
    def set_auto_scroll(self, enabled, is_recording=False):
        """
        Activa o desactiva el desplazamiento automático.
        
        Args:
            enabled: True para activar, False para desactivar
            is_recording: Si está grabando, forzar auto-scroll activo
        """
        if is_recording:
            self.auto_scroll = True
        else:
            self.auto_scroll = enabled
    
    def set_optimization_level(self, data_size):
        """
        Ajusta el nivel de optimización según el tamaño de los datos.
        
        Args:
            data_size: Tamaño actual de los datos
        """
        if not self.optimization_config['auto_optimize']:
            return
            
        # Activar optimizaciones para conjuntos de datos grandes
        if data_size > 5000 and not self.optimization_config['downsampling_enabled']:
            self.optimization_config['downsampling_enabled'] = True
            print(f"Optimización visual activada para {data_size} puntos")
        
        # Ajustar el número máximo de puntos visibles basado en el tamaño de datos
        if data_size > 10000:
            self.optimization_config['max_visible_points'] = 1000
        elif data_size > 5000:
            self.optimization_config['max_visible_points'] = 1500
        else:
            self.optimization_config['max_visible_points'] = 2000