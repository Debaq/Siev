import numpy as np
from queue import Queue


class DataProcessor:
    """Clase que maneja el procesamiento de datos para los gráficos."""
    
    def __init__(self):
        # Buffers para los datos
        self.x_data = []
        self.y_data = [[] for _ in range(6)]  # 3 gráficos x 2 ojos
        
        # Cola para nuevos datos
        self.data_queue = Queue()
        
        # Último estado conocido para interpolación
        self.last_known_left = None
        self.last_known_right = None
        
    def process_queue(self, max_process=100):
        """
        Procesa los datos en la cola.
        
        Args:
            max_process: Número máximo de elementos a procesar por llamada
        
        Returns:
            bool: True si se procesaron datos, False si la cola estaba vacía
        """
        processed = 0
        data_processed = False
        
        while not self.data_queue.empty() and processed < max_process:
            data = self.data_queue.get()
            data_processed = True
            
            if data is None:  # Señal para limpiar
                self.clear_data()
            else:
                self._process_data_point(data)
                
            processed += 1
            
        return data_processed
    
    def _process_data_point(self, data):
        """
        Procesa un punto de datos individual.
        
        Args:
            data: Lista con los datos [ojo_izq, ojo_der, imu_x, imu_y, tiempo]
        """
        try:
            # Extraer datos
            right_eye = data[0]  # [x, y] o None
            left_eye = data[1]   # [x, y] o None
            imu_x = float(data[2])
            imu_y = float(data[3])
            current_time = float(data[4])  # timestamp
            
            # Añadir timestamp
            self.x_data.append(current_time)
            
            # Procesar ojo izquierdo - Gráfico 1 (posición X)
            if left_eye is not None:
                self.y_data[0].append(float(left_eye[0]))  # Posición X
                self.last_known_left = left_eye.copy()
            else:
                # Usar último valor conocido o 0 si es el primer punto
                last_value = float(self.last_known_left[0]) if self.last_known_left else 0.0
                self.y_data[0].append(last_value)

            # Procesar ojo derecho - Gráfico 1 (posición X)
            if right_eye is not None:
                self.y_data[1].append(float(right_eye[0]))  # Posición X
                self.last_known_right = right_eye.copy()
            else:
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
            self.y_data[4].append(imu_x)  # IMU X
            self.y_data[5].append(imu_y)  # IMU Y
            
        except Exception as e:
            print(f"Error procesando datos: {e}")
    
    def clear_data(self):
        """Limpia todos los datos almacenados."""
        for i in range(6):
            self.y_data[i].clear()
        self.x_data.clear()
        self.last_known_left = None
        self.last_known_right = None
    
    def add_data(self, data):
        """
        Añade nuevos datos a la cola de procesamiento.
        
        Args:
            data: Lista con los datos [ojo_izq, ojo_der, imu_x, imu_y, tiempo]
        """
        if len(data) != 5:
            raise ValueError("Se requieren exactamente 5 valores (ojo_izq, ojo_der, imu_x, imu_y, tiempo)")
        self.data_queue.put(data)
    
    def get_data_copy(self):
        """
        Obtiene una copia de todos los datos almacenados.
        
        Returns:
            dict: Diccionario con los datos
        """
        return {
            'x_data': self.x_data.copy(),
            'y_data': [y.copy() for y in self.y_data]
        }
    
    def get_visible_indices(self, view_start, view_end, max_points=2000):
        """
        Obtiene los índices de los datos visibles en una ventana de tiempo.
        
        Args:
            view_start: Tiempo de inicio de la ventana
            view_end: Tiempo de fin de la ventana
            max_points: Máximo número de puntos a mostrar
            
        Returns:
            numpy.ndarray: Array de índices para los datos visibles
        """
        if not self.x_data:
            return np.array([], dtype=int)
            
        # Convertir a array para operaciones más rápidas
        x_array = np.array(self.x_data, dtype=np.float64)
        
        # Si hay pocos datos, devolver todos los índices
        if len(x_array) <= max_points:
            return np.arange(len(x_array))
            
        # Encontrar datos en el rango visible
        in_range_mask = (x_array >= view_start) & (x_array <= view_end)
        indices_in_range = np.where(in_range_mask)[0]
        
        # Si hay pocos puntos en el rango, mostrarlos todos
        if len(indices_in_range) <= max_points:
            return indices_in_range
            
        # Aplicar downsampling para limitar puntos
        downsample_factor = max(1, len(indices_in_range) // max_points)
        return indices_in_range[::downsample_factor]
    
    def export_to_csv(self, filename):
        """
        Exporta los datos almacenados a un archivo CSV.
        
        Args:
            filename: Ruta del archivo donde guardar los datos
        """
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