import numpy as np
from collections import deque
from typing import List, Dict, Optional, Tuple
import time


class OptimizedBuffer:
    """
    Buffer inteligente que mantiene solo los datos necesarios para visualización.
    Optimizado para performance, no para almacenamiento completo.
    """
    
    def __init__(self, visible_window=60.0, max_buffer_size=10000):
        """
        Args:
            visible_window: Ventana de tiempo visible en segundos
            max_buffer_size: Máximo número de puntos en el buffer
        """
        self.visible_window = visible_window
        self.max_buffer_size = max_buffer_size
        
        # Buffers circulares para datos de visualización
        self.timestamps = deque(maxlen=max_buffer_size)
        self.left_eye_x = deque(maxlen=max_buffer_size)
        self.left_eye_y = deque(maxlen=max_buffer_size)
        self.right_eye_x = deque(maxlen=max_buffer_size)
        self.right_eye_y = deque(maxlen=max_buffer_size)
        self.imu_x = deque(maxlen=max_buffer_size)
        self.imu_y = deque(maxlen=max_buffer_size)
        
        # Estados para detección de parpadeos
        self.left_eye_states = deque(maxlen=max_buffer_size)  # True/False
        self.right_eye_states = deque(maxlen=max_buffer_size)
        
        # Cache para datos visibles (evita recalcular constantemente)
        self._cached_visible_data = None
        self._cache_timestamp = 0
        self._cache_valid_duration = 0.1  # Cache válido por 100ms
        
        # Estadísticas de performance
        self.total_points_added = 0
        self.last_update_time = 0
    
    def add_data_point(self, left_eye: Optional[List[float]], right_eye: Optional[List[float]], 
                      imu_x: float, imu_y: float, timestamp: float):
        """
        Añade un punto de datos al buffer de visualización.
        
        Args:
            left_eye: Posición del ojo izquierdo [x, y] o None
            right_eye: Posición del ojo derecho [x, y] o None
            imu_x: Valor del acelerómetro eje X
            imu_y: Valor del acelerómetro eje Y
            timestamp: Marca de tiempo
        """
        # Añadir timestamp
        self.timestamps.append(timestamp)
        
        # Procesar ojo izquierdo
        if left_eye is not None:
            self.left_eye_x.append(left_eye[0])
            self.left_eye_y.append(left_eye[1])
            self.left_eye_states.append(True)
        else:
            # Usar último valor conocido para continuidad visual
            last_x = self.left_eye_x[-1] if self.left_eye_x else 0.0
            last_y = self.left_eye_y[-1] if self.left_eye_y else 0.0
            self.left_eye_x.append(last_x)
            self.left_eye_y.append(last_y)
            self.left_eye_states.append(False)
        
        # Procesar ojo derecho
        if right_eye is not None:
            self.right_eye_x.append(right_eye[0])
            self.right_eye_y.append(right_eye[1])
            self.right_eye_states.append(True)
        else:
            # Usar último valor conocido para continuidad visual
            last_x = self.right_eye_x[-1] if self.right_eye_x else 0.0
            last_y = self.right_eye_y[-1] if self.right_eye_y else 0.0
            self.right_eye_x.append(last_x)
            self.right_eye_y.append(last_y)
            self.right_eye_states.append(False)
        
        # Añadir datos IMU
        self.imu_x.append(imu_x)
        self.imu_y.append(imu_y)
        
        # Actualizar estadísticas
        self.total_points_added += 1
        self.last_update_time = timestamp
        
        # Invalidar cache
        self._cached_visible_data = None
    
    def get_visible_data(self, current_time: Optional[float] = None) -> Dict:
        """
        Obtiene solo los datos visibles en la ventana actual.
        Usa cache para evitar recálculos innecesarios.
        
        Args:
            current_time: Tiempo actual. Si es None, usa el último timestamp.
            
        Returns:
            Diccionario con arrays NumPy de datos visibles
        """
        if current_time is None:
            current_time = self.last_update_time
        
        # Verificar si el cache es válido
        if (self._cached_visible_data is not None and 
            abs(current_time - self._cache_timestamp) < self._cache_valid_duration):
            return self._cached_visible_data
        
        # Calcular ventana visible
        start_time = current_time - self.visible_window
        
        # Encontrar índices de datos visibles
        visible_indices = self._get_visible_indices(start_time, current_time)
        
        if not visible_indices:
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
        
        # Extraer datos visibles usando índices
        visible_data = {
            'timestamps': np.array([self.timestamps[i] for i in visible_indices]),
            'left_eye_x': np.array([self.left_eye_x[i] for i in visible_indices]),
            'left_eye_y': np.array([self.left_eye_y[i] for i in visible_indices]),
            'right_eye_x': np.array([self.right_eye_x[i] for i in visible_indices]),
            'right_eye_y': np.array([self.right_eye_y[i] for i in visible_indices]),
            'imu_x': np.array([self.imu_x[i] for i in visible_indices]),
            'imu_y': np.array([self.imu_y[i] for i in visible_indices]),
            'left_eye_states': np.array([self.left_eye_states[i] for i in visible_indices]),
            'right_eye_states': np.array([self.right_eye_states[i] for i in visible_indices])
        }
        
        # Actualizar cache
        self._cached_visible_data = visible_data
        self._cache_timestamp = current_time
        
        return visible_data
    
    def get_downsampled_data(self, max_points: int = 2000, current_time: Optional[float] = None) -> Dict:
        """
        Obtiene datos visibles con downsampling para mejor performance.
        
        Args:
            max_points: Máximo número de puntos a retornar
            current_time: Tiempo actual
            
        Returns:
            Diccionario con datos downsampled
        """
        visible_data = self.get_visible_data(current_time)
        
        # Si ya hay pocos puntos, retornar tal como está
        if len(visible_data['timestamps']) <= max_points:
            return visible_data
        
        # Calcular factor de downsampling
        downsample_factor = len(visible_data['timestamps']) // max_points
        
        # Aplicar downsampling a todos los arrays
        downsampled_data = {}
        for key, data in visible_data.items():
            downsampled_data[key] = data[::downsample_factor]
        
        return downsampled_data
    
    def get_blink_regions(self, current_time: Optional[float] = None) -> Tuple[List[Tuple], List[Tuple]]:
        """
        Detecta regiones de parpadeo en los datos visibles.
        
        Args:
            current_time: Tiempo actual
            
        Returns:
            Tupla con (regiones_ojo_izquierdo, regiones_ojo_derecho)
            Cada región es una tupla (tiempo_inicio, tiempo_fin)
        """
        visible_data = self.get_visible_data(current_time)
        
        if len(visible_data['timestamps']) == 0:
            return [], []
        
        # Detectar regiones de parpadeo para ojo izquierdo
        left_regions = self._detect_blink_regions(
            visible_data['timestamps'], 
            visible_data['left_eye_states']
        )
        
        # Detectar regiones de parpadeo para ojo derecho
        right_regions = self._detect_blink_regions(
            visible_data['timestamps'], 
            visible_data['right_eye_states']
        )
        
        return left_regions, right_regions
    
    def _get_visible_indices(self, start_time: float, end_time: float) -> List[int]:
        """
        Encuentra eficientemente los índices de datos en el rango de tiempo.
        
        Args:
            start_time: Tiempo de inicio
            end_time: Tiempo de fin
            
        Returns:
            Lista de índices que están en el rango
        """
        if not self.timestamps:
            return []
        
        indices = []
        for i, timestamp in enumerate(self.timestamps):
            if start_time <= timestamp <= end_time:
                indices.append(i)
        
        return indices
    
    def _detect_blink_regions(self, timestamps: np.ndarray, eye_states: np.ndarray) -> List[Tuple]:
        """
        Detecta regiones donde el ojo no está visible (parpadeos).
        
        Args:
            timestamps: Array de timestamps
            eye_states: Array de estados booleanos (True = ojo visible)
            
        Returns:
            Lista de tuplas (inicio, fin) de regiones de parpadeo
        """
        if len(timestamps) == 0:
            return []
        
        regions = []
        in_blink = False
        blink_start = None
        
        for i, (timestamp, is_visible) in enumerate(zip(timestamps, eye_states)):
            if not is_visible and not in_blink:
                # Inicio de parpadeo
                in_blink = True
                blink_start = timestamp
            elif is_visible and in_blink:
                # Fin de parpadeo
                in_blink = False
                if blink_start is not None:
                    regions.append((blink_start, timestamp))
                    blink_start = None
        
        # Si termina en parpadeo, cerrar la región
        if in_blink and blink_start is not None:
            regions.append((blink_start, timestamps[-1]))
        
        return regions
    
    def clear(self):
        """Limpia todos los datos del buffer."""
        self.timestamps.clear()
        self.left_eye_x.clear()
        self.left_eye_y.clear()
        self.right_eye_x.clear()
        self.right_eye_y.clear()
        self.imu_x.clear()
        self.imu_y.clear()
        self.left_eye_states.clear()
        self.right_eye_states.clear()
        
        # Limpiar cache
        self._cached_visible_data = None
        self._cache_timestamp = 0
        
        # Resetear estadísticas
        self.total_points_added = 0
        self.last_update_time = 0
    
    def get_buffer_info(self) -> Dict:
        """
        Obtiene información sobre el estado del buffer.
        
        Returns:
            Diccionario con estadísticas del buffer
        """
        return {
            'current_size': len(self.timestamps),
            'max_size': self.max_buffer_size,
            'utilization_percent': len(self.timestamps) / self.max_buffer_size * 100,
            'visible_window_seconds': self.visible_window,
            'total_points_added': self.total_points_added,
            'last_update_time': self.last_update_time,
            'cache_valid': self._cached_visible_data is not None
        }
    
    def set_visible_window(self, seconds: float):
        """
        Cambia el tamaño de la ventana visible.
        
        Args:
            seconds: Nueva ventana visible en segundos
        """
        self.visible_window = seconds
        # Invalidar cache al cambiar ventana
        self._cached_visible_data = None
    
    def optimize_for_performance(self):
        """
        Aplica optimizaciones adicionales para mejorar performance.
        Útil cuando hay muchos datos.
        """
        # Reducir ventana visible si hay demasiados datos
        if len(self.timestamps) > self.max_buffer_size * 0.8:
            self.visible_window = min(self.visible_window, 30.0)  # Máximo 30 segundos
        
        # Ajustar duración del cache
        if len(self.timestamps) > 5000:
            self._cache_valid_duration = 0.2  # Cache más duradero para datos grandes
        else:
            self._cache_valid_duration = 0.1  # Cache más frecuente para pocos datos