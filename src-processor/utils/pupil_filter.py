#!/usr/bin/env python3
"""
Pupil Signal Filter
Filtro para suavizar señales de pupila preservando morfología de la curva.
Maneja interpolación para valores no detectados y suavizado configurable.
"""

import numpy as np
from typing import Optional, Tuple
from scipy.signal import savgol_filter, medfilt
from collections import deque


class PupilSignalFilter:
    """
    Filtro de señal para coordenadas de pupila que preserva morfología
    mientras reduce ruido mediante suavizado e interpolación.
    """
    
    def __init__(self, window_size: int = 7, filter_type: str = "savgol"):
        """
        Inicializar filtro de pupila
        
        Args:
            window_size: Tamaño de ventana para filtrado (debe ser impar)
            filter_type: Tipo de filtro ("savgol", "median", "moving_avg")
        """
        # Asegurar ventana impar para Savitzky-Golay
        self.window_size = window_size if window_size % 2 == 1 else window_size + 1
        self.filter_type = filter_type
        
        # Buffer circular para mantener histórico
        self.buffer = deque(maxlen=self.window_size * 2)  # Buffer más grande para interpolación
        self.timestamps = deque(maxlen=self.window_size * 2)
        
        # Estado para interpolación
        self.last_valid_value = 0.0
        self.last_valid_timestamp = 0.0
        
        # Contador para frames no detectados consecutivos
        self.missing_frames = 0
        self.max_interpolation_gap = 5  # Máximo frames a interpolar
        
    def process_pupil_x(self, timestamp: float, pupil_x: float, detected: bool) -> float:
        """
        Procesar coordenada X de pupila con filtrado y suavizado
        
        Args:
            timestamp: Tiempo actual
            pupil_x: Coordenada X detectada (o 0.0 si no detectada)
            detected: Si la pupila fue detectada en este frame
            
        Returns:
            float: Valor filtrado y suavizado de pupil_x
        """
        if detected:
            # Valor válido detectado
            self.missing_frames = 0
            self.last_valid_value = pupil_x
            self.last_valid_timestamp = timestamp
            processed_value = pupil_x
        else:
            # Valor no detectado - interpolar
            self.missing_frames += 1
            processed_value = self._interpolate_missing_value(timestamp)
        
        # Agregar al buffer
        self.buffer.append(processed_value)
        self.timestamps.append(timestamp)
        
        # Aplicar filtrado si tenemos suficientes datos
        if len(self.buffer) >= self.window_size:
            return self._apply_filter()
        else:
            # No hay suficientes datos para filtrar, retornar valor actual
            return processed_value
    
    def _interpolate_missing_value(self, current_timestamp: float) -> float:
        """
        Interpolar valor faltante basado en valores previos
        
        Args:
            current_timestamp: Timestamp actual
            
        Returns:
            float: Valor interpolado
        """
        if self.missing_frames > self.max_interpolation_gap:
            # Demasiados frames perdidos, usar último valor conocido
            return self.last_valid_value
        
        if len(self.buffer) < 2:
            # No hay suficiente histórico, usar último valor válido
            return self.last_valid_value
        
        # Interpolación lineal simple basada en tendencia reciente
        recent_values = list(self.buffer)[-3:]  # Últimos 3 valores
        recent_timestamps = list(self.timestamps)[-3:]
        
        if len(recent_values) >= 2:
            # Calcular tendencia
            dt = recent_timestamps[-1] - recent_timestamps[-2]
            dx = recent_values[-1] - recent_values[-2]
            
            if dt > 0:
                # Proyectar basado en tendencia
                time_elapsed = current_timestamp - self.last_valid_timestamp
                projected_change = (dx / dt) * time_elapsed
                
                # Limitar cambio proyectado para evitar saltos grandes
                max_change = abs(dx) * 2  # Máximo 2x el último cambio
                projected_change = np.clip(projected_change, -max_change, max_change)
                
                return self.last_valid_value + projected_change
        
        # Fallback: usar último valor válido
        return self.last_valid_value
    
    def _apply_filter(self) -> float:
        """
        Aplicar filtro seleccionado a los datos del buffer
        
        Returns:
            float: Valor filtrado
        """
        data = np.array(list(self.buffer))
        
        try:
            if self.filter_type == "savgol":
                # Savitzky-Golay preserva morfología
                poly_order = min(3, self.window_size - 1)  # Orden polinómico
                filtered_data = savgol_filter(data, self.window_size, poly_order)
                return float(filtered_data[-1])  # Retornar último valor filtrado
                
            elif self.filter_type == "median":
                # Filtro de mediana elimina picos de ruido
                filtered_data = medfilt(data, kernel_size=self.window_size)
                return float(filtered_data[-1])
                
            elif self.filter_type == "moving_avg":
                # Media móvil simple
                window_data = data[-self.window_size:]
                return float(np.mean(window_data))
                
            else:
                # Tipo no reconocido, retornar valor sin filtrar
                return float(data[-1])
                
        except Exception as e:
            print(f"Error aplicando filtro {self.filter_type}: {e}")
            # En caso de error, retornar valor sin filtrar
            return float(data[-1])
    
    def update_config(self, window_size: Optional[int] = None, 
                     filter_type: Optional[str] = None,
                     max_interpolation_gap: Optional[int] = None):
        """
        Actualizar configuración del filtro
        
        Args:
            window_size: Nuevo tamaño de ventana
            filter_type: Nuevo tipo de filtro
            max_interpolation_gap: Nueva distancia máxima de interpolación
        """
        if window_size is not None:
            # Asegurar ventana impar
            self.window_size = window_size if window_size % 2 == 1 else window_size + 1
            # Redimensionar buffer
            new_buffer = deque(list(self.buffer), maxlen=self.window_size * 2)
            new_timestamps = deque(list(self.timestamps), maxlen=self.window_size * 2)
            self.buffer = new_buffer
            self.timestamps = new_timestamps
        
        if filter_type is not None:
            self.filter_type = filter_type
            
        if max_interpolation_gap is not None:
            self.max_interpolation_gap = max_interpolation_gap
    
    def reset(self):
        """Reiniciar filtro limpiando todo el histórico"""
        self.buffer.clear()
        self.timestamps.clear()
        self.last_valid_value = 0.0
        self.last_valid_timestamp = 0.0
        self.missing_frames = 0
    
    def get_config(self) -> dict:
        """
        Obtener configuración actual del filtro
        
        Returns:
            dict: Configuración actual
        """
        return {
            'window_size': self.window_size,
            'filter_type': self.filter_type,
            'max_interpolation_gap': self.max_interpolation_gap,
            'buffer_size': len(self.buffer),
            'missing_frames': self.missing_frames
        }