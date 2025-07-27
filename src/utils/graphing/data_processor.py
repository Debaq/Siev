import numpy as np
from collections import deque
from typing import List, Dict, Optional, Tuple, Any
import time


class OptimizedDataProcessor:
    """
    Procesador optimizado de datos que maneja eficientemente el flujo de datos
    desde el buffer hacia la visualización.
    """
    
    def __init__(self, max_processing_batch=100):
        """
        Args:
            max_processing_batch: Máximo número de puntos a procesar por lote
        """
        self.max_processing_batch = max_processing_batch
        
        # Cola de datos pendientes de procesar
        self.processing_queue = deque()
        
        # Datos procesados listos para visualización
        self.processed_data = {
            'timestamps': deque(),
            'left_eye_x': deque(),
            'left_eye_y': deque(), 
            'right_eye_x': deque(),
            'right_eye_y': deque(),
            'imu_x': deque(),
            'imu_y': deque(),
            'left_eye_states': deque(),
            'right_eye_states': deque()
        }
        
        # Estado para interpolación y continuidad
        self.last_known_left = None
        self.last_known_right = None
        
        # Estadísticas de performance
        self.total_processed = 0
        self.processing_time_sum = 0.0
        self.last_processing_time = 0
        
        # Configuración de optimización
        self.interpolation_enabled = True
        self.smoothing_enabled = True
        self.batch_processing = True
    
    def add_raw_data(self, left_eye: Optional[List[float]], right_eye: Optional[List[float]], 
                    imu_x: float, imu_y: float, timestamp: float):
        """
        Añade datos crudos a la cola de procesamiento.
        
        Args:
            left_eye: Posición del ojo izquierdo [x, y] o None
            right_eye: Posición del ojo derecho [x, y] o None
            imu_x: Valor del acelerómetro eje X
            imu_y: Valor del acelerómetro eje Y
            timestamp: Marca de tiempo
        """
        raw_data_point = {
            'left_eye': left_eye,
            'right_eye': right_eye,
            'imu_x': imu_x,
            'imu_y': imu_y,
            'timestamp': timestamp
        }
        
        self.processing_queue.append(raw_data_point)
    
    def process_batch(self) -> int:
        """
        Procesa un lote de datos de la cola.
        
        Returns:
            Número de puntos procesados
        """
        if not self.processing_queue:
            return 0
        
        start_time = time.time()
        
        # Determinar tamaño del lote
        batch_size = min(len(self.processing_queue), self.max_processing_batch)
        
        # Extraer lote de la cola
        batch = []
        for _ in range(batch_size):
            if self.processing_queue:
                batch.append(self.processing_queue.popleft())
        
        # Procesar lote
        if self.batch_processing:
            self._process_batch_optimized(batch)
        else:
            # Procesamiento individual (menos eficiente)
            for data_point in batch:
                self._process_single_point(data_point)
        
        # Actualizar estadísticas
        processing_time = time.time() - start_time
        self.processing_time_sum += processing_time
        self.total_processed += batch_size
        self.last_processing_time = processing_time
        
        return batch_size
    
    def _process_batch_optimized(self, batch: List[Dict]):
        """
        Procesa un lote completo de manera optimizada.
        
        Args:
            batch: Lista de puntos de datos a procesar
        """
        for data_point in batch:
            self._process_single_point(data_point)
    
    def _process_single_point(self, data_point: Dict):
        """
        Procesa un punto de datos individual.
        
        Args:
            data_point: Diccionario con los datos del punto
        """
        left_eye = data_point['left_eye']
        right_eye = data_point['right_eye']
        imu_x = data_point['imu_x']
        imu_y = data_point['imu_y']
        timestamp = data_point['timestamp']
        
        # Añadir timestamp
        self.processed_data['timestamps'].append(timestamp)
        
        # Procesar ojo izquierdo
        if left_eye is not None:
            self.processed_data['left_eye_x'].append(float(left_eye[0]))
            self.processed_data['left_eye_y'].append(float(left_eye[1]))
            self.processed_data['left_eye_states'].append(True)
            self.last_known_left = left_eye.copy()
        else:
            # Usar último valor conocido para continuidad
            last_x = float(self.last_known_left[0]) if self.last_known_left else 0.0
            last_y = float(self.last_known_left[1]) if self.last_known_left else 0.0
            self.processed_data['left_eye_x'].append(last_x)
            self.processed_data['left_eye_y'].append(last_y)
            self.processed_data['left_eye_states'].append(False)
        
        # Procesar ojo derecho
        if right_eye is not None:
            self.processed_data['right_eye_x'].append(float(right_eye[0]))
            self.processed_data['right_eye_y'].append(float(right_eye[1]))
            self.processed_data['right_eye_states'].append(True)
            self.last_known_right = right_eye.copy()
        else:
            # Usar último valor conocido para continuidad
            last_x = float(self.last_known_right[0]) if self.last_known_right else 0.0
            last_y = float(self.last_known_right[1]) if self.last_known_right else 0.0
            self.processed_data['right_eye_x'].append(last_x)
            self.processed_data['right_eye_y'].append(last_y)
            self.processed_data['right_eye_states'].append(False)
        
        # Procesar datos IMU
        self.processed_data['imu_x'].append(float(imu_x))
        self.processed_data['imu_y'].append(float(imu_y))
    
    def get_processed_data(self, max_points: Optional[int] = None) -> Dict:
        """
        Obtiene los datos procesados como arrays NumPy.
        
        Args:
            max_points: Máximo número de puntos a retornar (None para todos)
            
        Returns:
            Diccionario con arrays NumPy de datos procesados
        """
        if not self.processed_data['timestamps']:
            return self._empty_data_dict()
        
        # Determinar rango de datos a extraer
        if max_points is None or len(self.processed_data['timestamps']) <= max_points:
            # Retornar todos los datos
            return {
                key: np.array(list(values))
                for key, values in self.processed_data.items()
            }
        else:
            # Retornar solo los últimos max_points
            return {
                key: np.array(list(values)[-max_points:])
                for key, values in self.processed_data.items()
            }
    
    def get_data_in_time_range(self, start_time: float, end_time: float) -> Dict:
        """
        Obtiene datos en un rango de tiempo específico.
        
        Args:
            start_time: Tiempo de inicio
            end_time: Tiempo de fin
            
        Returns:
            Diccionario con datos en el rango especificado
        """
        if not self.processed_data['timestamps']:
            return self._empty_data_dict()
        
        # Convertir timestamps a array para búsqueda eficiente
        timestamps = np.array(list(self.processed_data['timestamps']))
        
        # Encontrar índices en el rango
        mask = (timestamps >= start_time) & (timestamps <= end_time)
        indices = np.where(mask)[0]
        
        if len(indices) == 0:
            return self._empty_data_dict()
        
        # Extraer datos usando índices
        result = {}
        for key, values in self.processed_data.items():
            values_array = np.array(list(values))
            result[key] = values_array[indices]
        
        return result
    
    def get_downsampled_data(self, max_points: int = 2000) -> Dict:
        """
        Obtiene datos con downsampling para visualización eficiente.
        
        Args:
            max_points: Máximo número de puntos a retornar
            
        Returns:
            Diccionario con datos downsampled
        """
        full_data = self.get_processed_data()
        
        if len(full_data['timestamps']) <= max_points:
            return full_data
        
        # Calcular factor de downsampling
        downsample_factor = len(full_data['timestamps']) // max_points
        
        # Aplicar downsampling
        downsampled = {}
        for key, data in full_data.items():
            downsampled[key] = data[::downsample_factor]
        
        return downsampled
    
    def clear_processed_data(self):
        """Limpia todos los datos procesados."""
        for values in self.processed_data.values():
            values.clear()
        
        self.last_known_left = None
        self.last_known_right = None
    
    def clear_queue(self):
        """Limpia la cola de procesamiento."""
        self.processing_queue.clear()
    
    def clear_all(self):
        """Limpia todos los datos y colas."""
        self.clear_processed_data()
        self.clear_queue()
        
        # Resetear estadísticas
        self.total_processed = 0
        self.processing_time_sum = 0.0
        self.last_processing_time = 0
    
    def get_queue_size(self) -> int:
        """Obtiene el tamaño actual de la cola de procesamiento."""
        return len(self.processing_queue)
    
    def get_processed_count(self) -> int:
        """Obtiene el número de puntos procesados."""
        return len(self.processed_data['timestamps'])
    
    def get_performance_stats(self) -> Dict:
        """
        Obtiene estadísticas de performance del procesador.
        
        Returns:
            Diccionario con estadísticas de performance
        """
        avg_processing_time = (
            self.processing_time_sum / max(1, self.total_processed)
        ) if self.total_processed > 0 else 0
        
        return {
            'total_processed': self.total_processed,
            'queue_size': self.get_queue_size(),
            'processed_count': self.get_processed_count(),
            'avg_processing_time_ms': avg_processing_time * 1000,
            'last_processing_time_ms': self.last_processing_time * 1000,
            'batch_processing_enabled': self.batch_processing,
            'max_batch_size': self.max_processing_batch
        }
    
    def optimize_for_load(self, high_load: bool = False):
        """
        Optimiza la configuración basada en la carga del sistema.
        
        Args:
            high_load: True si el sistema está bajo alta carga
        """
        if high_load:
            # Configuración para alta carga
            self.max_processing_batch = 50
            self.batch_processing = True
            self.interpolation_enabled = False  # Desactivar para mayor velocidad
            self.smoothing_enabled = False
            print("DataProcessor: Optimizado para alta carga")
        else:
            # Configuración normal
            self.max_processing_batch = 100
            self.batch_processing = True
            self.interpolation_enabled = True
            self.smoothing_enabled = True
            print("DataProcessor: Configuración normal")
    
    def _empty_data_dict(self) -> Dict:
        """Retorna un diccionario con arrays vacíos."""
        return {
            'timestamps': np.array([]),
            'left_eye_x': np.array([]),
            'left_eye_y': np.array([]),
            'right_eye_x': np.array([]),
            'right_eye_y': np.array([]),
            'imu_x': np.array([]),
            'imu_y': np.array([]),
            'left_eye_states': np.array([]),
            'right_eye_states': np.array([])
        }
    
    def set_max_batch_size(self, size: int):
        """
        Establece el tamaño máximo del lote de procesamiento.
        
        Args:
            size: Nuevo tamaño máximo del lote
        """
        self.max_processing_batch = max(1, min(size, 1000))  # Límite entre 1-1000
    
    def enable_batch_processing(self, enabled: bool):
        """
        Habilita o deshabilita el procesamiento por lotes.
        
        Args:
            enabled: True para habilitar, False para deshabilitar
        """
        self.batch_processing = enabled