import numpy as np
from collections import deque
from typing import List, Dict, Tuple, Optional
import time


class OptimizedBlinkDetector:
    """
    Detector de parpadeos optimizado que procesa los datos por lotes
    en lugar de punto por punto para máximo rendimiento.
    """
    
    def __init__(self, max_history_size=5000):
        """
        Args:
            max_history_size: Máximo número de puntos a mantener en el historial
        """
        self.max_history_size = max_history_size
        
        # Buffers circulares para datos históricos
        self.left_eye_history = deque(maxlen=max_history_size)
        self.right_eye_history = deque(maxlen=max_history_size)
        self.timestamp_history = deque(maxlen=max_history_size)
        
        # Regiones de parpadeo detectadas
        self.left_blink_regions = []
        self.right_blink_regions = []
        
        # Estado actual de parpadeo
        self.left_blinking = False
        self.right_blinking = False
        self.left_blink_start = None
        self.right_blink_start = None
        
        # Configuración de detección
        self.min_blink_duration = 0.05   # 50ms mínimo
        self.max_blink_duration = 2.0    # 2s máximo
        self.batch_size = 100            # Procesar en lotes de 100 puntos
        
        # Buffer de procesamiento por lotes
        self.processing_buffer = []
        
        # Estadísticas
        self.total_blinks_detected = {'left': 0, 'right': 0}
        self.last_processing_time = 0
        self.processing_times = deque(maxlen=50)  # Para promedio móvil
        
        # Cache de regiones visibles
        self._cached_visible_regions = None
        self._cache_timestamp = 0
        self._cache_duration = 0.1  # 100ms
    
    def add_data_point(self, left_eye_visible: bool, right_eye_visible: bool, timestamp: float):
        """
        Añade un punto de datos al buffer de procesamiento.
        
        Args:
            left_eye_visible: True si el ojo izquierdo está visible
            right_eye_visible: True si el ojo derecho está visible
            timestamp: Marca de tiempo
        """
        # Añadir al buffer de procesamiento
        self.processing_buffer.append({
            'left_visible': left_eye_visible,
            'right_visible': right_eye_visible,
            'timestamp': timestamp
        })
        
        # Procesar por lotes cuando el buffer esté lleno
        if len(self.processing_buffer) >= self.batch_size:
            self.process_batch()
    
    def process_batch(self):
        """Procesa un lote completo de datos de manera eficiente."""
        if not self.processing_buffer:
            return
        
        start_time = time.time()
        
        # Procesar cada punto del lote
        for data_point in self.processing_buffer:
            self._process_single_point(
                data_point['left_visible'],
                data_point['right_visible'], 
                data_point['timestamp']
            )
        
        # Limpiar buffer
        self.processing_buffer.clear()
        
        # Actualizar estadísticas de performance
        processing_time = time.time() - start_time
        self.processing_times.append(processing_time)
        self.last_processing_time = processing_time
        
        # Invalidar cache
        self._cached_visible_regions = None
    
    def _process_single_point(self, left_visible: bool, right_visible: bool, timestamp: float):
        """
        Procesa un punto individual de datos.
        
        Args:
            left_visible: Estado del ojo izquierdo
            right_visible: Estado del ojo derecho
            timestamp: Marca de tiempo
        """
        # Añadir a historial
        self.left_eye_history.append(left_visible)
        self.right_eye_history.append(right_visible)
        self.timestamp_history.append(timestamp)
        
        # Procesar ojo izquierdo
        self._process_eye_state(
            left_visible, timestamp, 'left',
            self.left_blinking, self.left_blink_start,
            self.left_blink_regions
        )
        
        # Procesar ojo derecho
        self._process_eye_state(
            right_visible, timestamp, 'right',
            self.right_blinking, self.right_blink_start,
            self.right_blink_regions
        )
    
    def _process_eye_state(self, is_visible: bool, timestamp: float, eye: str,
                          currently_blinking: bool, blink_start: Optional[float],
                          blink_regions: List[Tuple]):
        """
        Procesa el estado de un ojo específico.
        
        Args:
            is_visible: Si el ojo está visible
            timestamp: Marca de tiempo actual
            eye: 'left' o 'right'
            currently_blinking: Estado actual de parpadeo
            blink_start: Tiempo de inicio del parpadeo actual
            blink_regions: Lista de regiones de parpadeo
        """
        if not is_visible and not currently_blinking:
            # Inicio de parpadeo
            if eye == 'left':
                self.left_blinking = True
                self.left_blink_start = timestamp
            else:
                self.right_blinking = True
                self.right_blink_start = timestamp
                
        elif is_visible and currently_blinking:
            # Fin de parpadeo
            blink_start = self.left_blink_start if eye == 'left' else self.right_blink_start
            
            if blink_start is not None:
                duration = timestamp - blink_start
                
                # Validar duración del parpadeo
                if self.min_blink_duration <= duration <= self.max_blink_duration:
                    blink_regions.append((blink_start, timestamp))
                    self.total_blinks_detected[eye] += 1
            
            # Resetear estado
            if eye == 'left':
                self.left_blinking = False
                self.left_blink_start = None
            else:
                self.right_blinking = False
                self.right_blink_start = None
    
    def get_blink_regions(self, current_time: Optional[float] = None) -> Tuple[List[Tuple], List[Tuple]]:
        """
        Obtiene las regiones de parpadeo detectadas.
        
        Args:
            current_time: Tiempo actual para incluir parpadeos en curso
            
        Returns:
            Tupla con (regiones_ojo_izquierdo, regiones_ojo_derecho)
        """
        # Procesar datos pendientes si los hay
        if self.processing_buffer:
            self.process_batch()
        
        left_regions = self.left_blink_regions.copy()
        right_regions = self.right_blink_regions.copy()
        
        # Añadir parpadeos en curso si hay tiempo actual
        if current_time is not None:
            if self.left_blinking and self.left_blink_start is not None:
                left_regions.append((self.left_blink_start, current_time))
            
            if self.right_blinking and self.right_blink_start is not None:
                right_regions.append((self.right_blink_start, current_time))
        
        return left_regions, right_regions
    
    def get_visible_blink_regions(self, start_time: float, end_time: float, 
                                 max_regions: int = 50) -> Tuple[List[Tuple], List[Tuple]]:
        """
        Obtiene regiones de parpadeo visibles en una ventana de tiempo específica.
        
        Args:
            start_time: Tiempo de inicio de la ventana
            end_time: Tiempo de fin de la ventana
            max_regions: Máximo número de regiones a retornar
            
        Returns:
            Tupla con regiones visibles (izquierdo, derecho)
        """
        # Verificar cache
        cache_key = (start_time, end_time, max_regions)
        current_time = time.time()
        
        if (self._cached_visible_regions is not None and 
            current_time - self._cache_timestamp < self._cache_duration):
            return self._cached_visible_regions
        
        # Obtener todas las regiones
        left_all, right_all = self.get_blink_regions()
        
        # Filtrar por ventana de tiempo
        left_visible = [
            (start, end) for start, end in left_all
            if not (end < start_time or start > end_time)  # Hay intersección
        ]
        
        right_visible = [
            (start, end) for start, end in right_all
            if not (end < start_time or start > end_time)  # Hay intersección
        ]
        
        # Limitar número de regiones
        if len(left_visible) > max_regions:
            left_visible = left_visible[-max_regions:]
        
        if len(right_visible) > max_regions:
            right_visible = right_visible[-max_regions:]
        
        # Actualizar cache
        result = (left_visible, right_visible)
        self._cached_visible_regions = result
        self._cache_timestamp = current_time
        
        return result
    
    def get_blink_statistics(self) -> Dict:
        """
        Obtiene estadísticas de parpadeos detectados.
        
        Returns:
            Diccionario con estadísticas
        """
        # Calcular frecuencia de parpadeo si hay suficientes datos
        blink_rate_left = 0.0
        blink_rate_right = 0.0
        
        if len(self.timestamp_history) > 0:
            total_time = self.timestamp_history[-1] - self.timestamp_history[0]
            if total_time > 0:
                blink_rate_left = self.total_blinks_detected['left'] / (total_time / 60)  # por minuto
                blink_rate_right = self.total_blinks_detected['right'] / (total_time / 60)
        
        # Promedio de tiempo de procesamiento
        avg_processing_time = (
            np.mean(self.processing_times) * 1000 if self.processing_times else 0
        )
        
        return {
            'total_blinks_left': self.total_blinks_detected['left'],
            'total_blinks_right': self.total_blinks_detected['right'],
            'blink_rate_left_per_minute': blink_rate_left,
            'blink_rate_right_per_minute': blink_rate_right,
            'total_data_points': len(self.timestamp_history),
            'avg_processing_time_ms': avg_processing_time,
            'last_processing_time_ms': self.last_processing_time * 1000,
            'buffer_utilization_percent': len(self.timestamp_history) / self.max_history_size * 100,
            'pending_processing': len(self.processing_buffer)
        }
    
    def clear_history(self):
        """Limpia todo el historial de datos."""
        self.left_eye_history.clear()
        self.right_eye_history.clear()
        self.timestamp_history.clear()
        self.left_blink_regions.clear()
        self.right_blink_regions.clear()
        self.processing_buffer.clear()
        
        # Resetear estado
        self.left_blinking = False
        self.right_blinking = False
        self.left_blink_start = None
        self.right_blink_start = None
        
        # Resetear estadísticas
        self.total_blinks_detected = {'left': 0, 'right': 0}
        self.processing_times.clear()
        
        # Limpiar cache
        self._cached_visible_regions = None
    
    def force_process_pending(self):
        """Fuerza el procesamiento de todos los datos pendientes."""
        if self.processing_buffer:
            self.process_batch()
    
    def set_detection_parameters(self, min_duration: float = 0.05, max_duration: float = 2.0,
                                batch_size: int = 100):
        """
        Configura los parámetros de detección.
        
        Args:
            min_duration: Duración mínima de parpadeo en segundos
            max_duration: Duración máxima de parpadeo en segundos
            batch_size: Tamaño del lote de procesamiento
        """
        self.min_blink_duration = max(0.01, min_duration)
        self.max_blink_duration = max(min_duration, max_duration)
        self.batch_size = max(1, min(batch_size, 1000))
    
    def optimize_for_performance(self, high_load: bool = False):
        """
        Optimiza la configuración para mayor rendimiento.
        
        Args:
            high_load: True si el sistema está bajo alta carga
        """
        if high_load:
            # Configuración para alta carga
            self.batch_size = 200  # Lotes más grandes
            self._cache_duration = 0.2  # Cache más duradero
            self.max_history_size = 3000  # Menos historial
            print("BlinkDetector: Optimizado para alta carga")
        else:
            # Configuración normal
            self.batch_size = 100
            self._cache_duration = 0.1
            self.max_history_size = 5000
            print("BlinkDetector: Configuración normal")
    
    def get_current_blink_state(self) -> Dict:
        """
        Obtiene el estado actual de parpadeo.
        
        Returns:
            Diccionario con el estado actual
        """
        return {
            'left_blinking': self.left_blinking,
            'right_blinking': self.right_blinking,
            'left_blink_start': self.left_blink_start,
            'right_blink_start': self.right_blink_start,
            'left_blink_duration': (
                time.time() - self.left_blink_start 
                if self.left_blinking and self.left_blink_start else 0
            ),
            'right_blink_duration': (
                time.time() - self.right_blink_start 
                if self.right_blinking and self.right_blink_start else 0
            )
        }
    
    def export_blink_data(self) -> Dict:
        """
        Exporta todos los datos de parpadeos para análisis externo.
        
        Returns:
            Diccionario con todos los datos de parpadeos
        """
        return {
            'left_blink_regions': self.left_blink_regions.copy(),
            'right_blink_regions': self.right_blink_regions.copy(),
            'statistics': self.get_blink_statistics(),
            'current_state': self.get_current_blink_state(),
            'configuration': {
                'min_blink_duration': self.min_blink_duration,
                'max_blink_duration': self.max_blink_duration,
                'batch_size': self.batch_size,
                'max_history_size': self.max_history_size
            }
        }