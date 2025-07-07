import numpy as np
from collections import deque
from typing import List, Dict, Optional, Tuple
import time


class OptimizedBuffer:
    """
    Buffer inteligente CORREGIDO que mantiene solo los datos necesarios para visualización.
    VERSIÓN SIMPLIFICADA que realmente funciona.
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
        
        # Estadísticas de performance
        self.total_points_added = 0
        self.last_update_time = 0
        
        # Variable para el primer timestamp (referencia)
        self.first_timestamp = None
    
    def add_data_point(self, left_eye: Optional[List[float]], right_eye: Optional[List[float]], 
                      imu_x: float, imu_y: float, timestamp: float):
        """
        Añade un punto de datos al buffer de visualización.
        VERSIÓN SIMPLIFICADA que funciona.
        """
        current_time = timestamp if timestamp is not None else time.time()
        
        # Añadir timestamp
        self.timestamps.append(current_time)
        
        # Procesar datos del ojo izquierdo
        if left_eye is not None and len(left_eye) >= 2:
            self.left_eye_x.append(float(left_eye[0]))
            self.left_eye_y.append(float(left_eye[1]))
            self.left_eye_states.append(True)  # Ojo detectado
        else:
            # Usar último valor conocido o 0
            last_x = self.left_eye_x[-1] if self.left_eye_x else 0.0
            last_y = self.left_eye_y[-1] if self.left_eye_y else 0.0
            self.left_eye_x.append(last_x)
            self.left_eye_y.append(last_y)
            self.left_eye_states.append(False)  # Ojo no detectado (parpadeo)
        
        # Procesar datos del ojo derecho
        if right_eye is not None and len(right_eye) >= 2:
            self.right_eye_x.append(float(right_eye[0]))
            self.right_eye_y.append(float(right_eye[1]))
            self.right_eye_states.append(True)  # Ojo detectado
        else:
            # Usar último valor conocido o 0
            last_x = self.right_eye_x[-1] if self.right_eye_x else 0.0
            last_y = self.right_eye_y[-1] if self.right_eye_y else 0.0
            self.right_eye_x.append(last_x)
            self.right_eye_y.append(last_y)
            self.right_eye_states.append(False)  # Ojo no detectado (parpadeo)
        
        # Añadir datos IMU
        self.imu_x.append(float(imu_x))
        self.imu_y.append(float(imu_y))
        
        # Actualizar estadísticas
        self.total_points_added += 1
        self.last_update_time = current_time
    
    def get_visible_data(self, current_time: Optional[float] = None) -> Dict:
        """
        Obtiene datos visibles - VERSIÓN SIMPLIFICADA que funciona.
        """
        if len(self.timestamps) == 0:
            return self._empty_data()
        
        if current_time is None:
            current_time = self.timestamps[-1]
        
        # CLAVE: Calcular ventana visible de manera más robusta
        if self.first_timestamp is None:
            start_time = 0
        else:
            # Usar tiempo relativo desde el inicio de la grabación
            elapsed_time = current_time - self.first_timestamp
            start_time = max(0, elapsed_time - self.visible_window)
            start_time += self.first_timestamp  # Convertir de nuevo a timestamp absoluto
        
        # Encontrar todos los puntos en la ventana visible
        visible_indices = []
        for i, timestamp in enumerate(self.timestamps):
            if timestamp >= start_time:
                visible_indices.append(i)
        
        if not visible_indices:
            print(f"DEBUG: No hay datos visibles. start_time={start_time}, current_time={current_time}")
            print(f"       Primer timestamp: {self.timestamps[0] if self.timestamps else 'N/A'}")
            print(f"       Último timestamp: {self.timestamps[-1] if self.timestamps else 'N/A'}")
            return self._empty_data()
        
        # Extraer datos visibles
        try:
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
            
            # Debug info
            if len(visible_data['timestamps']) > 0:
                print(f"DEBUG: Datos visibles encontrados: {len(visible_data['timestamps'])} puntos")
                print(f"       Rango de tiempo: {visible_data['timestamps'][0]:.2f} - {visible_data['timestamps'][-1]:.2f}")
            
            return visible_data
            
        except Exception as e:
            print(f"ERROR en get_visible_data: {e}")
            return self._empty_data()
    
    def get_downsampled_data(self, max_points: int = 2000, current_time: Optional[float] = None) -> Dict:
        """
        Obtiene datos visibles con downsampling para mejor performance.
        VERSIÓN SIMPLIFICADA.
        """
        visible_data = self.get_visible_data(current_time)
        
        # Si ya hay pocos puntos, retornar tal como está
        if len(visible_data['timestamps']) <= max_points:
            return visible_data
        
        # Calcular factor de downsampling
        downsample_factor = max(1, len(visible_data['timestamps']) // max_points)
        
        # Aplicar downsampling a todos los arrays
        downsampled_data = {}
        for key, data in visible_data.items():
            if len(data) > 0:
                downsampled_data[key] = data[::downsample_factor]
            else:
                downsampled_data[key] = data
        
        print(f"DEBUG: Downsampling de {len(visible_data['timestamps'])} a {len(downsampled_data['timestamps'])} puntos")
        
        return downsampled_data
    
    def _empty_data(self) -> Dict:
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
    
    def get_blink_regions(self, current_time: Optional[float] = None) -> Tuple[List[Tuple], List[Tuple]]:
        """
        Detecta regiones de parpadeo en los datos visibles.
        VERSIÓN SIMPLIFICADA.
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
    
    def _detect_blink_regions(self, timestamps: np.ndarray, eye_states: np.ndarray) -> List[Tuple]:
        """
        Detecta regiones donde el ojo no está visible (parpadeos).
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
        
        # Resetear estadísticas
        self.total_points_added = 0
        self.last_update_time = 0
    
    def get_buffer_info(self) -> Dict:
        """
        Obtiene información sobre el estado del buffer.
        """
        return {
            'current_size': len(self.timestamps),
            'max_size': self.max_buffer_size,
            'utilization_percent': len(self.timestamps) / self.max_buffer_size * 100,
            'visible_window_seconds': self.visible_window,
            'total_points_added': self.total_points_added,
            'last_update_time': self.last_update_time
        }
    
    def set_visible_window(self, seconds: float):
        """
        Cambia el tamaño de la ventana visible.
        """
        self.visible_window = seconds
        print(f"Ventana visible establecida a {seconds}s")
    
    def optimize_for_performance(self):
        """
        Aplica optimizaciones adicionales para mejorar performance.
        """
        # Reducir ventana visible si hay demasiados datos
        if len(self.timestamps) > self.max_buffer_size * 0.8:
            old_window = self.visible_window
            self.visible_window = min(self.visible_window, 30.0)  # Máximo 30 segundos
            if old_window != self.visible_window:
                print(f"Ventana visible reducida de {old_window}s a {self.visible_window}s para mejorar performance")