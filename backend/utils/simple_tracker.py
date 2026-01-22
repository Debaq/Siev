from collections import deque
import numpy as np
import cv2

class PrecisionTracker:
    """
    Tracker optimizado para mediciones precisas de velocidad.
    Elimina outliers pero preserva aceleraciones y velocidades reales.
    """
    def __init__(self, history_size=5, outlier_threshold=15):
        # Historia reciente de posiciones
        self.positions = deque(maxlen=history_size)
        
        # Para cálculo de velocidad
        self.velocities = deque(maxlen=history_size)
        self.last_position = None
        self.last_time = None
        
        # Contador de frames perdidos
        self.lost_frames = 0
        self.max_lost_frames = 5  # Más bajo que SimpleTracker para mejor precisión
        
        # Umbral para detección de outliers (en píxeles)
        self.outlier_threshold = outlier_threshold
        
        # Para la detección de fijación
        self.is_fixating = False
        self.fixation_count = 0
        self.fixation_threshold = 10  # Cuántos frames necesarios para considerar fijación
        self.fixation_distance = 5.0  # Distancia máxima para considerar fijación (px)
        
        # Centroide de la fijación actual
        self.fixation_centroid = None
        
    def update(self, circle, timestamp=None):
        """
        Actualiza el tracker con una nueva detección.
        
        Args:
            circle: Tupla (x, y, radio) o None si no se detectó
            timestamp: Timestamp para cálculo de velocidad (opcional)
            
        Returns:
            Tupla (x, y, radio) procesada o None
        """
        if timestamp is None:
            timestamp = cv2.getTickCount() / cv2.getTickFrequency()
        
        # Caso 1: No hay detección
        if circle is None:
            self.lost_frames += 1
            if self.lost_frames > self.max_lost_frames:
                # Reiniciar todo si llevamos demasiados frames perdidos
                self.last_position = None
                self.positions.clear()
                self.velocities.clear()
                self.is_fixating = False
                self.fixation_count = 0
                self.fixation_centroid = None
                
            # Si tenemos una posición anterior, la devolvemos para continuidad
            # pero no actualizamos velocidad
            return self.last_position
        
        # Convertir a numpy array para cálculos
        current_pos = np.array(circle, dtype=np.float32)
        
        # Caso 2: Primera detección o después de muchos frames perdidos
        if self.last_position is None:
            self.last_position = current_pos
            self.last_time = timestamp
            self.positions.append(current_pos)
            self.lost_frames = 0
            return current_pos.astype(np.int32)
        
        # Calcular distancia desde última posición
        distance = np.linalg.norm(current_pos[:2] - self.last_position[:2])
        
        # Caso 3: Detectar y filtrar outliers
        if distance > self.outlier_threshold and len(self.positions) >= 3:
            # Calcular mediana de posiciones recientes
            recent_positions = np.array(list(self.positions))
            median_position = np.median(recent_positions, axis=0)
            
            # Si la nueva posición está muy lejos de la mediana, podría ser outlier
            median_distance = np.linalg.norm(current_pos[:2] - median_position[:2])
            if median_distance > self.outlier_threshold:
                # Probable outlier - ignora pero no incrementa lost_frames
                # Devuelve última posición válida
                return self.last_position.astype(np.int32)
        
        # Calcular velocidad instantánea (píxeles/segundo)
        dt = timestamp - self.last_time
        if dt > 0:
            instant_velocity = distance / dt
            self.velocities.append(instant_velocity)
        
        # Actualizar "historia" de posiciones
        self.positions.append(current_pos)
        
        # Caso 4: Detectar si está en fijación (mirando un punto fijo)
        if distance < self.fixation_distance:
            self.fixation_count += 1
            
            # Actualizar o inicializar centroide de fijación
            if self.fixation_centroid is None:
                self.fixation_centroid = current_pos.copy()
            else:
                # Actualizar centroide incrementalmente (media móvil)
                alpha = 0.1  # Peso de la nueva observación
                self.fixation_centroid = self.fixation_centroid * (1 - alpha) + current_pos * alpha
            
            # Verificar si hemos alcanzado umbral de fijación
            if self.fixation_count >= self.fixation_threshold:
                self.is_fixating = True
                # Durante fijación, usar el centroide para mayor estabilidad
                processed_pos = self.fixation_centroid.copy()
                # Pero mantener el radio original para precisión
                processed_pos[2] = current_pos[2]
                
                # Guardar posición actual como referencia para próxima iteración
                self.last_position = current_pos
                self.last_time = timestamp
                
                return processed_pos.astype(np.int32)
        else:
            # Reiniciar detección de fijación
            self.is_fixating = False
            self.fixation_count = 0
            self.fixation_centroid = None
        
        # Caso 5: Movimiento normal (saccade)
        self.lost_frames = 0
        self.last_position = current_pos
        self.last_time = timestamp
        
        return current_pos.astype(np.int32)
    
    def get_velocity(self):
        """Obtiene la velocidad instantánea promediada sobre los últimos frames"""
        if not self.velocities:
            return 0.0
        return np.mean(self.velocities)
    
    def is_stable(self):
        """Indica si la mirada está estable (fijación)"""
        return self.is_fixating