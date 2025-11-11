from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Signal, QTimer, Qt
import pyqtgraph as pg
import numpy as np
from collections import deque
from queue import Queue
import time

class TriplePlotWidget(QWidget):
    linePositionChanged = Signal(float)
    
    def __init__(self, parent=None, window_size=60, update_interval=16):
        super().__init__(parent)
        
        # Configuración inicial
        self.layout = QVBoxLayout(self)
        self.plots = []
        self.curves = []
        self.blink_regions = []  # Para almacenar regiones de parpadeo
        self.window_size = window_size
        self.auto_scroll = True
        self._updating_range = False  # Flag para evitar bucles en actualización
        
        # Datos para ambos ojos (izquierdo y derecho)
        # [0][x] = ojo izquierdo gráfico 1, [1][x] = ojo derecho gráfico 1, etc.
        self.y_data = [[] for _ in range(6)]  # 3 gráficos x 2 ojos
        self.x_data = []
        
        # Para seguimiento de parpadeos
        self.left_blink_regions = []  # Lista de tuplas (inicio_x, fin_x) para ojo izquierdo
        self.right_blink_regions = []  # Lista de tuplas (inicio_x, fin_x) para ojo derecho
        self.last_known_left = None   # Último valor conocido antes de parpadeo
        self.last_known_right = None  # Último valor conocido antes de parpadeo
        self.left_blinking = False    # Indicador de parpadeo en progreso
        self.right_blinking = False   # Indicador de parpadeo en progreso
        self.blink_start_time = {"left": None, "right": None}  # Tiempo de inicio del parpadeo
        
        # Cola para nuevos datos
        self.data_queue = Queue()
        
        # Estado de grabación
        self.is_recording = False
        
        # Configuración para optimización de visualización
        self.optimization_config = {
            'max_visible_points': 2000,         # Máximo de puntos a mostrar a la vez
            'max_visible_blinks': 50,           # Máximo de regiones de parpadeo visibles
            'visualization_mode': 'full',       # 'full' o 'optimized'
            'downsampling_enabled': False,      # Activar/desactivar downsampling visual
            'auto_optimize': True               # Activar optimización automática según cantidad de datos
        }
        
        # Configurar PyQtGraph para máximo rendimiento
        pg.setConfigOptions(antialias=False)
        
        # Crear los tres gráficos
        for i in range(3):
            plot = pg.PlotWidget()
            plot.setBackground('w')
            plot.getAxis('bottom').setPen(pg.mkPen(color='black', width=1))
            plot.getAxis('left').setPen(pg.mkPen(color='black', width=1))

            # Configurar color del texto de los ejes
            plot.getAxis('bottom').setTextPen(pg.mkPen(color='black'))
            plot.getAxis('left').setTextPen(pg.mkPen(color='black'))

            # Estilo de fuente para las etiquetas
            labelStyle = {'color': '#000', 'font-size': '12pt'}
            plot.setLabel('left', 'Posición X', units='px', **labelStyle)
            plot.setLabel('bottom', 'Tiempo', units='s', **labelStyle)

            plot.showGrid(x=True, y=True)
            plot.setDownsampling(auto=True, mode='peak')
            plot.setClipToView(True)
            self.plots.append(plot)
            self.layout.addWidget(plot)
            
            # Crear curvas para ambos ojos con configuración optimizada
            curve_right = plot.plot(pen=pg.mkPen(color=(200, 0, 0), width=1), name="Ojo Derecho")
            curve_right.setDownsampling(auto=True, method='peak')
            curve_right.setClipToView(True)
            
            curve_left = plot.plot(pen=pg.mkPen(color=(0, 0, 200), width=1), name="Ojo Izquierdo")
            curve_left.setDownsampling(auto=True, method='peak')
            curve_left.setClipToView(True)
            
            # Agregar curvas a la lista (primero ojo izq, luego ojo der)
            self.curves.append(curve_right)
            self.curves.append(curve_left)
            
            # Contenedor para almacenar regiones de parpadeo
            self.blink_regions.append([])
            
            # Configurar el comportamiento del mouse
            plot.setMouseEnabled(x=True, y=False)
            plot.sigRangeChanged.connect(self.on_range_changed)
        
        # Crear la línea infinita en cada gráfico
        self.vLines = []
        for plot in self.plots:
            vLine = pg.InfiniteLine(angle=90, movable=True)
            plot.addItem(vLine)
            self.vLines.append(vLine)
            vLine.sigPositionChanged.connect(self.lineMovedEvent)
        
        # Vincular los ejes X
        for i in range(1, 3):
            self.plots[i].setXLink(self.plots[0])
        
        # Añadir etiquetas a los gráficos
        self.plots[0].setLabel('left', 'Posición X', units='px')
        self.plots[1].setLabel('left', 'Posición Y', units='px')
        self.plots[2].setLabel('left', 'IMU', units='g')
        self.plots[2].setLabel('bottom', 'Tiempo', units='s')
        
        self.setLayout(self.layout)
        
        # Timer para actualización de gráficos
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.process_data_queue)
        self.update_timer.start(update_interval)
        
        # Timer para actualización de visualización
        self.display_timer = QTimer()
        self.display_timer.timeout.connect(self.update_display)
        self.display_timer.start(500)  # ~30 FPS para la visualización
    
    def set_recording_state(self, is_recording):
        """
        Establece el estado de grabación para controlar el comportamiento del auto-scroll.
        Durante la grabación se activa el auto-scroll automáticamente.
        Después de detener la grabación, el usuario puede explorar los datos libremente.
        
        Args:
            is_recording: True si está grabando, False si no
        """
        self.is_recording = is_recording
        if is_recording:
            # Activar auto_scroll cuando comienza la grabación
            self.auto_scroll = True
            print("Gráfico: Auto-scroll activado para grabación")
        else:
            # Al detener la grabación, mantener auto_scroll
            # (el usuario podrá desactivarlo moviendo la vista)
            print("Gráfico: Grabación detenida, modo exploración disponible")
    
    def get_visible_data_indices(self, x_array, view_start, view_end):
        """
        Obtiene los índices de los datos visibles en la ventana actual.
        Utiliza un enfoque optimizado para grandes conjuntos de datos.
        
        Args:
            x_array: Array de valores de tiempo
            view_start: Tiempo de inicio de la ventana visible
            view_end: Tiempo de fin de la ventana visible
            
        Returns:
            Array de índices para los datos visibles
        """
        # Si hay pocos datos, simplemente devolver todos los índices
        if len(x_array) <= self.optimization_config['max_visible_points']:
            return np.arange(len(x_array))
            
        # Para conjuntos de datos grandes, encontrar un subconjunto óptimo
        # que represente visualmente los datos sin sobrecargar la renderización
        
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
            
            # Realizar muestreo para reducir datos pero mantener la forma general
            # Esto solo afecta a la visualización, no a los datos almacenados
            return indices_in_range[::downsample_factor]
        else:
            # Si el downsampling está desactivado, mostrar todos los puntos en la ventana
            # (esto puede ser más lento para conjuntos de datos muy grandes)
            return indices_in_range
    
    def optimize_blink_regions(self):
        """
        Optimiza la visualización de regiones de parpadeo para mostrar solo las visibles
        sin afectar los datos almacenados.
        
        Returns:
            Tupla de (regiones izquierdas visibles, regiones derechas visibles)
        """
        try:
            # Obtener el rango de tiempo visible actual
            if len(self.x_data) > 0:
                if self.auto_scroll:
                    current_time = self.x_data[-1]
                    view_start = current_time - (self.window_size * 2/3)
                    view_end = view_start + self.window_size
                else:
                    # Si auto_scroll está desactivado, obtener la vista actual
                    view_range = self.plots[0].viewRange()
                    view_start = view_range[0][0]
                    view_end = view_range[0][1]
                    
                # Filtrar regiones de parpadeo que son visibles
                visible_left_blinks = [
                    (start, end) for start, end in self.left_blink_regions
                    if end >= view_start and start <= view_end
                ]
                
                visible_right_blinks = [
                    (start, end) for start, end in self.right_blink_regions
                    if end >= view_start and start <= view_end
                ]
                
                # Límite máximo de regiones a mostrar por rendimiento
                MAX_VISIBLE_REGIONS = self.optimization_config['max_visible_blinks']
                if len(visible_left_blinks) > MAX_VISIBLE_REGIONS:
                    visible_left_blinks = visible_left_blinks[-MAX_VISIBLE_REGIONS:]
                
                if len(visible_right_blinks) > MAX_VISIBLE_REGIONS:
                    visible_right_blinks = visible_right_blinks[-MAX_VISIBLE_REGIONS:]
                    
                return visible_left_blinks, visible_right_blinks
        except Exception as e:
            print(f"Error al optimizar regiones de parpadeo: {e}")
            
        # En caso de error, devolver listas vacías
        return [], []
    
    def lineMovedEvent(self):
        sender = self.sender()
        newX = sender.value()
        for vLine in self.vLines:
            if vLine != sender:
                vLine.setValue(newX)
        self.linePositionChanged.emit(newX)
    
    def on_range_changed(self, plot, ranges):
        """
        Detecta cuando el usuario ha cambiado manualmente el rango de visualización
        y actualiza el estado de auto_scroll correspondientemente.
        """
        # Solo procesar eventos del primer gráfico (los demás están vinculados)
        if plot == self.plots[0]:
            # Solo procesar si el cambio no fue causado por nuestro propio código
            # (evitar ciclos infinitos de eventos)
            if not hasattr(self, '_updating_range') or not self._updating_range:
                # Solo permitir control manual cuando no está grabando
                if not self.is_recording:
                    view_range = self.plots[0].viewRange()
                    current_max = view_range[0][1]
                    
                    if len(self.x_data) > 0:
                        data_max = self.x_data[-1]
                        # Si el extremo derecho de la vista está cerca del dato más reciente,
                        # consideramos que debe activarse el auto_scroll
                        if abs(current_max - data_max) < self.window_size / 10:
                            self.auto_scroll = True
                        else:
                            # Si el usuario ha movido la vista lejos del final,
                            # desactivamos el auto_scroll
                            self.auto_scroll = False
    
    def process_data_queue(self):
        """Procesa los datos en la cola"""
        # Procesar un número limitado de elementos por ciclo
        max_process = 100
        processed = 0
        
        while not self.data_queue.empty() and processed < max_process:
            data = self.data_queue.get()
            if data is None:  # Señal para limpiar
                for i in range(6):
                    self.y_data[i].clear()
                self.x_data.clear()
                self.left_blink_regions.clear()
                self.right_blink_regions.clear()
                self.left_blinking = False
                self.right_blinking = False
                self.last_known_left = None
                self.last_known_right = None
                self.blink_start_time = {"right": None, "left": None}
            else:
                try:
                    # Extraer datos según la estructura real:
                    # data = [[X_ojo_izq, Y_ojo_izq], [X_ojo_der, Y_ojo_der], imu_x, imu_y, tiempo]
                    right_eye = data[0] # [x, y] o None
                    left_eye = data[1]  # [x, y] o None
                    imu_x = float(data[2])
                    imu_y = float(data[3])
                    current_time = float(data[4])  # timestamp
                    
                    # Añadir timestamp
                    self.x_data.append(current_time)
                    
                    # Procesar ojo izquierdo - Gráfico 1 (posición X)
                    if left_eye is not None:
                        # Ojo detectado
                        self.y_data[0].append(float(left_eye[0]))  # Posición X
                        self.last_known_left = left_eye.copy()
                        
                        # Si estaba parpadeando, registrar fin de parpadeo
                        if self.left_blinking:
                            self.left_blinking = False
                            self.left_blink_regions.append((self.blink_start_time["left"], current_time))
                            self.blink_start_time["left"] = None
                    else:
                        # Ojo no detectado (parpadeo)
                        if not self.left_blinking:
                            # Inicio de parpadeo
                            self.left_blinking = True
                            self.blink_start_time["left"] = current_time
                        
                        # Usar último valor conocido o 0 si es el primer punto
                        last_value = float(self.last_known_left[0]) if self.last_known_left else 0.0
                        self.y_data[0].append(last_value)

                    # Procesar ojo derecho - Gráfico 1 (posición X)
                    if right_eye is not None:
                        # Ojo detectado
                        self.y_data[1].append(float(right_eye[0]))  # Posición X
                        self.last_known_right = right_eye.copy()
                        
                        # Si estaba parpadeando, registrar fin de parpadeo
                        if self.right_blinking:
                            self.right_blinking = False
                            self.right_blink_regions.append((self.blink_start_time["right"], current_time))
                            self.blink_start_time["right"] = None
                    else:
                        # Ojo no detectado (parpadeo)
                        if not self.right_blinking:
                            # Inicio de parpadeo
                            self.right_blinking = True
                            self.blink_start_time["right"] = current_time
                        
                        # Usar último valor conocido o 0 si es el primer punto
                        last_value = float(self.last_known_right[0]) if self.last_known_right else 0.0
                        self.y_data[1].append(last_value)
                    
                    # Procesar ojo izquierdo - Gráfico 2 (posición Y)
                    if left_eye is not None:
                        self.y_data[2].append(float(left_eye[1]))  # Posición Y
                    else:
                        last_value = float(self.last_known_left[1]) if self.last_known_left else 0.0
                        self.y_data[2].append(last_value)
                    
                    # Procesar ojo derecho - Gráfico 2 (posición Y)
                    if right_eye is not None:
                        self.y_data[3].append(float(right_eye[1]))  # Posición Y
                    else:
                        last_value = float(self.last_known_right[1]) if self.last_known_right else 0.0
                        self.y_data[3].append(last_value)
                    
                    # Gráfico 3 - IMU (acelerómetro)
                    # Gráfico del eje X del IMU (usando el mismo slot que ojo izquierdo)
                    self.y_data[4].append(imu_x)
                    
                    # Gráfico del eje Y del IMU (usando el mismo slot que ojo derecho)
                    self.y_data[5].append(imu_y)
                    
                    # Verificar automáticamente si debemos activar optimizaciones visuales
                    if self.optimization_config['auto_optimize'] and len(self.x_data) % 1000 == 0:
                        if len(self.x_data) > 5000:
                            # Para conjuntos de datos muy grandes, activar optimizaciones visuales
                            if self.optimization_config['visualization_mode'] != 'optimized':
                                self.optimization_config['visualization_mode'] = 'optimized'
                                self.optimization_config['downsampling_enabled'] = True
                                print(f"Activando optimizaciones visuales por cantidad de datos ({len(self.x_data)} puntos)")
                    
                except Exception as e:
                    print(f"Error procesando datos: {e}")
                    
            processed += 1
    
    def update_display(self):
        """Actualiza la visualización de los gráficos de manera más eficiente"""
        if not self.x_data:
            return
            
        try:
            # Convertir datos a arrays NumPy una sola vez (más eficiente)
            x_array = np.array(self.x_data, dtype=np.float64)
            
            # Obtener rango visible actual
            view_visible = False
            view_start = 0
            view_end = 0
            
            if self.auto_scroll and len(self.x_data) > 0:
                current_time = self.x_data[-1]
                view_start = max(0, current_time - (self.window_size * 2/3))
                view_end = view_start + self.window_size
                view_visible = True
            else:
                # Si auto_scroll está desactivado, obtener la vista actual
                view_range = self.plots[0].viewRange()
                view_start = view_range[0][0]
                view_end = view_range[0][1]
                view_visible = True
                
            # Obtener índices de datos visibles
            if view_visible:
                visible_indices = self.get_visible_data_indices(x_array, view_start, view_end)
                
                # Si hay datos visibles, actualizarlos
                if len(visible_indices) > 0:
                    visible_x = x_array[visible_indices]
                    
                    # Actualizar cada curva con los datos visibles
                    for i in range(6):
                        if i < len(self.y_data) and len(self.y_data[i]) == len(x_array):
                            y_array = np.array(self.y_data[i], dtype=np.float64)
                            visible_y = y_array[visible_indices]
                            
                            if i < len(self.curves):
                                self.curves[i].setData(visible_x, visible_y)
                else:
                    # Si no hay datos visibles en la ventana actual,
                    # podemos dejarlo vacío o mostrar un subconjunto de datos cercanos
                    pass
            else:
                # Si no hay rango definido, mostrar todos los datos o un subconjunto
                # representativo para mantener la eficiencia
                if len(x_array) <= self.optimization_config['max_visible_points']:
                    # Mostrar todos los puntos si son pocos
                    for i in range(6):
                        if i < len(self.y_data) and len(self.y_data[i]) == len(x_array):
                            y_array = np.array(self.y_data[i], dtype=np.float64)
                            if i < len(self.curves):
                                self.curves[i].setData(x_array, y_array)
                else:
                    # Para conjuntos grandes, mostrar un subconjunto representativo
                    # usando downsampling uniforme
                    step = max(1, len(x_array) // self.optimization_config['max_visible_points'])
                    indices = np.arange(0, len(x_array), step)
                    for i in range(6):
                        if i < len(self.y_data) and len(self.y_data[i]) == len(x_array):
                            y_array = np.array(self.y_data[i], dtype=np.float64)
                            if i < len(self.curves):
                                self.curves[i].setData(x_array[indices], y_array[indices])
                
            # Optimizar regiones de parpadeo para mostrar solo las visibles
            visible_left_blinks, visible_right_blinks = self.optimize_blink_regions()
                
            # Limpiar regiones de parpadeo anteriores
            for plot_idx, plot in enumerate(self.plots):
                # Eliminar todas las regiones de parpadeo existentes
                for region in self.blink_regions[plot_idx]:
                    plot.removeItem(region)
                self.blink_regions[plot_idx] = []
                
                # Añadir regiones de parpadeo visibles para ojo izquierdo
                for start, end in visible_left_blinks:
                    if end > start:  # Asegurarse de que la región es válida
                        region = pg.LinearRegionItem(
                            values=[start, end],
                            brush=pg.mkBrush(255, 0, 0, 50),  # Rojo semi-transparente
                            movable=False
                        )
                        plot.addItem(region)
                        self.blink_regions[plot_idx].append(region)
                
                # Añadir regiones de parpadeo visibles para ojo derecho
                for start, end in visible_right_blinks:
                    if end > start:  # Asegurarse de que la región es válida
                        region = pg.LinearRegionItem(
                            values=[start, end],
                            brush=pg.mkBrush(255, 165, 0, 50),  # Naranja semi-transparente
                            movable=False
                        )
                        plot.addItem(region)
                        self.blink_regions[plot_idx].append(region)
                        
            # Gestionar el desplazamiento automático
            if len(self.x_data) > 0 and self.auto_scroll:
                current_time = self.x_data[-1]
                
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
                for plot in self.plots:
                    plot.setXRange(window_start, window_end, padding=0)
                    
                # Limpiar flag después de la actualización
                self._updating_range = False
                
            # Marcar parpadeos en curso (aún no finalizados)
            current_time = self.x_data[-1] if self.x_data else 0
            if self.left_blinking and self.blink_start_time["left"] is not None:
                for plot_idx, plot in enumerate(self.plots):
                    region = pg.LinearRegionItem(
                        values=[self.blink_start_time["left"], current_time],
                        brush=pg.mkBrush(255, 0, 0, 50),  # Rojo semi-transparente
                        movable=False
                    )
                    plot.addItem(region)
                    self.blink_regions[plot_idx].append(region)
                    
            if self.right_blinking and self.blink_start_time["right"] is not None:
                for plot_idx, plot in enumerate(self.plots):
                    region = pg.LinearRegionItem(
                        values=[self.blink_start_time["right"], current_time],
                        brush=pg.mkBrush(255, 165, 0, 50),  # Naranja semi-transparente
                        movable=False
                    )
                    plot.addItem(region)
                    self.blink_regions[plot_idx].append(region)
                
        except Exception as e:
            print(f"Error al actualizar gráficos: {e}")
    
    def updatePlots(self, data):
        """
        Añade nuevos datos a la cola.
        Thread-safe.
        
        Formato de datos esperado:
        data[0] = posición ojo izquierdo [x,y] o None si no se detecta
        data[1] = posición ojo derecho [x,y] o None si no se detecta
        data[2] = datos IMU eje X
        data[3] = datos IMU eje Y
        data[4] = timestamp actual
        """
        if len(data) != 5:
            raise ValueError("Se requieren exactamente 5 valores (ojo_izq, ojo_der, imu_x, imu_y, tiempo)")
        self.data_queue.put(data)
    
    def clearPlots(self):
        """Limpia todos los datos de los gráficos"""
        self.data_queue.put(None)
        self.auto_scroll = True
        self.optimization_config['visualization_mode'] = 'full'
        self.optimization_config['downsampling_enabled'] = False
    
    def set_auto_scroll(self, enabled):
        """
        Activa o desactiva manualmente el auto-scroll.
        Nota: Durante grabación, el auto-scroll se mantiene siempre activo.
        """
        if not self.is_recording:
            self.auto_scroll = enabled
        else:
            if not enabled:
                print("No se puede desactivar auto-scroll durante la grabación")
    
    def get_data(self):
        """Retorna una copia de todos los datos almacenados"""
        return {
            'x_data': self.x_data.copy(),
            'y_data': [y.copy() for y in self.y_data],
            'left_blink_regions': self.left_blink_regions.copy(),
            'right_blink_regions': self.right_blink_regions.copy()
        }
    
    def export_data(self, filename):
        """Exporta los datos a un archivo CSV"""
        import csv
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            # Escribir encabezados
            writer.writerow(['Tiempo', 'Ojo_Izq_X', 'Ojo_Der_X', 'Ojo_Izq_Y', 'Ojo_Der_Y', 'IMU_X', 'IMU_Y'])
            # Escribir datos
            for i in range(len(self.x_data)):
                writer.writerow([
                    self.x_data[i], 
                    self.y_data[0][i] if i < len(self.y_data[0]) else None,
                    self.y_data[1][i] if i < len(self.y_data[1]) else None,
                    self.y_data[2][i] if i < len(self.y_data[2]) else None,
                    self.y_data[3][i] if i < len(self.y_data[3]) else None,
                    self.y_data[4][i] if i < len(self.y_data[4]) else None,
                    self.y_data[5][i] if i < len(self.y_data[5]) else None
                ])
    
    def closeEvent(self, event):
        self.update_timer.stop()
        self.display_timer.stop()
        super().closeEvent(event)
