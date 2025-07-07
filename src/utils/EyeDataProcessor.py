import numpy as np
from typing import List, Dict, Tuple, Optional, Union
import time
from collections import deque

class KalmanFilter:
    """
    Implementación avanzada del filtro de Kalman para seguimiento de posición ocular.
    Esta versión incluye aceleración en el modelo de estado para un seguimiento más suave.
    """
    def __init__(self, initial_state=None, process_noise=0.01, measurement_noise=0.1, stability_factor=0.01):
        # Inicializar filtro con valores por defecto si no se proporciona estado inicial
        if initial_state is None:
            self.state = np.zeros(6)  # [x, y, vel_x, vel_y, acc_x, acc_y]
        else:
            self.state = np.array([initial_state[0], initial_state[1], 0, 0, 0, 0])
        
        # Matriz de covarianza (incertidumbre del estado)
        self.P = np.eye(6) * 1.0
        
        # Factor para controlar la estabilidad (valores más bajos = más estable pero más lento)
        self.stability_factor = stability_factor
        
        # Matrices de ruido
        self.Q = np.eye(6) * process_noise      # Ruido del proceso
        # Dar más peso a la posición y menos a la aceleración
        self.Q[0,0] *= 0.1  # Menos ruido en posición x
        self.Q[1,1] *= 0.1  # Menos ruido en posición y
        self.Q[4,4] *= 10   # Más ruido permitido en aceleración x
        self.Q[5,5] *= 10   # Más ruido permitido en aceleración y
        
        self.R = np.eye(2) * measurement_noise  # Ruido de la medición
        
        # Matriz de transición de estado (modelo de movimiento con aceleración)
        # x' = x + vx + 0.5*ax
        # vx' = vx + ax
        # ax' = ax * stability_factor (la aceleración disminuye naturalmente)
        dt = 1.0  # Asumimos un delta de tiempo unitario
        self.A = np.array([
            [1, 0, dt, 0, 0.5*dt*dt, 0],          # x += vel_x + 0.5*acc_x
            [0, 1, 0, dt, 0, 0.5*dt*dt],          # y += vel_y + 0.5*acc_y
            [0, 0, 1, 0, dt, 0],                  # vel_x += acc_x
            [0, 0, 0, 1, 0, dt],                  # vel_y += acc_y
            [0, 0, 0, 0, stability_factor, 0],    # acc_x *= stability_factor
            [0, 0, 0, 0, 0, stability_factor]     # acc_y *= stability_factor
        ])
        
        # Matriz de observación (mapea estado a medición)
        self.H = np.array([
            [1, 0, 0, 0, 0, 0],  # Medimos x
            [0, 1, 0, 0, 0, 0]   # Medimos y
        ])
        
        # Historial para detección de movimientos bruscos
        self.measurement_history = deque(maxlen=3)
        self.sudden_movement = False
        
        # Bandera para saber si se ha inicializado
        self.initialized = initial_state is not None
    
    def predict(self):
        """Realiza la predicción del siguiente estado basado en el modelo"""
        # Predecir estado
        self.state = self.A @ self.state
        
        # Actualizar covarianza
        self.P = self.A @ self.P @ self.A.T + self.Q
        
        return self.state[:2]  # Devolver solo posición (x, y)
    
    def update(self, measurement):
        """
        Actualiza el estado con una nueva medición.
        
        Args:
            measurement: Lista o array [x, y] con la posición medida
        
        Returns:
            Array [x, y] con la posición estimada después de la actualización
        """
        if not self.initialized:
            # Si es la primera medición, inicializar el estado
            self.state[:2] = measurement
            self.initialized = True
            return self.state[:2]
        
        # Convertir medición a array numpy
        z = np.array(measurement)
        
        # Almacenar historial de mediciones para detectar movimientos bruscos
        self.measurement_history.append(z)
        
        # Detectar si hay un movimiento repentino significativo
        self.sudden_movement = False
        if len(self.measurement_history) >= 3:
            prev_pos = self.measurement_history[-2]
            prev_prev_pos = self.measurement_history[-3]
            
            # Calcular velocidades
            current_vel = z - prev_pos
            prev_vel = prev_pos - prev_prev_pos
            
            # Si hay un cambio brusco en la velocidad (aceleración alta)
            accel_magnitude = np.linalg.norm(current_vel - prev_vel)
            if accel_magnitude > 15.0:  # Umbral para considerar movimiento brusco
                self.sudden_movement = True
        
        # Ajustar la matriz de proceso si se detecta movimiento brusco
        if self.sudden_movement:
            # Aumentar temporalmente el process noise para adaptarse más rápido
            temp_Q = self.Q.copy()
            temp_Q *= 10.0  # Aumentar temporalmente la capacidad de adaptación
            self.P = self.A @ self.P @ self.A.T + temp_Q
        else:
            # Proceso normal
            self.P = self.A @ self.P @ self.A.T + self.Q
        
        # Calcular innovación (diferencia entre predicción y medición)
        y = z - (self.H @ self.state)
        
        # Calcular covarianza de la innovación
        S = self.H @ self.P @ self.H.T + self.R
        
        # Calcular ganancia de Kalman
        K = self.P @ self.H.T @ np.linalg.inv(S)
        
        # Actualizar estado
        self.state = self.state + K @ y
        
        # Si se detectó movimiento brusco, actualizar velocidad y aceleración más agresivamente
        if self.sudden_movement:
            if len(self.measurement_history) >= 2:
                prev_pos = self.measurement_history[-2]
                self.state[2:4] = (z - prev_pos) * 0.8 + self.state[2:4] * 0.2  # Actualizar velocidad
        
        # Actualizar covarianza
        I = np.eye(6)
        self.P = (I - K @ self.H) @ self.P
        
        # Aplicar suavizado adicional a través de spline cúbico para la salida
        smoothed_position = self._apply_smoothing(self.state[:2])
        
        return smoothed_position  # Devolver posición suavizada
    
    def _apply_smoothing(self, position):
        """
        Aplica suavizado adicional utilizando técnicas de interpolación avanzada.
        Esto ayuda a reducir el efecto escalonado en las trayectorias.
        """
        # Si no tenemos suficientes puntos en el historial, devolvemos la posición tal cual
        if len(self.measurement_history) < 3:
            return position
        
        # Obtener puntos recientes para el suavizado
        recent_points = list(self.measurement_history)
        
        # Si tenemos un movimiento brusco, confiar más en el Kalman
        if self.sudden_movement:
            return position
        
        # Calcular una posición intermedia suavizada usando una ponderación no lineal
        weights = [0.1, 0.2, 0.3]  # Pesos para los puntos anteriores (ordenados del más antiguo al más reciente)
        kalman_weight = 0.4        # Peso para la estimación de Kalman
        
        # Normalizar pesos
        total_weight = sum(weights) + kalman_weight
        weights = [w/total_weight for w in weights]
        kalman_weight /= total_weight
        
        # Calcular posición suavizada como combinación ponderada
        smoothed_x = sum(p[0] * w for p, w in zip(recent_points, weights)) + position[0] * kalman_weight
        smoothed_y = sum(p[1] * w for p, w in zip(recent_points, weights)) + position[1] * kalman_weight
        
        return np.array([smoothed_x, smoothed_y])
    
    def reset(self):
        """Reinicia el filtro"""
        self.state = np.zeros(6)
        self.P = np.eye(6) * 1.0
        self.initialized = False
        self.measurement_history.clear()
        self.sudden_movement = False


class EyeDataProcessor:
    """
    Clase para procesar los datos de movimientos oculares antes de enviarlos a la gráfica.
    Realiza normalización, centrado, interpolación y filtrado de los datos.
    """
    
    def __init__(self):
        # Calibración y referencia
        self.left_eye_center = None  # Punto de referencia para ojo izquierdo
        self.right_eye_center = None  # Punto de referencia para ojo derecho
        self.calibration_samples = 30  # Número de muestras para calibración inicial
        self.calibration_data = {
            'left': [],  # Almacena muestras de ojo izquierdo para calibración
            'right': []  # Almacena muestras de ojo derecho para calibración
        }
        
        # Estado de procesamiento
        self.is_calibrated = False
        self.processing_enabled = True
        
        # Historial para suavizado avanzado
        self.history_size = 5  # Número de muestras para filtro de media móvil
        self.left_history_x = deque(maxlen=self.history_size)
        self.left_history_y = deque(maxlen=self.history_size)
        self.right_history_x = deque(maxlen=self.history_size)
        self.right_history_y = deque(maxlen=self.history_size)
        
        # Atributos para interpolación
        self.timestamps = deque(maxlen=10)
        self.left_values_x = deque(maxlen=10)
        self.left_values_y = deque(maxlen=10)
        self.right_values_x = deque(maxlen=10)
        self.right_values_y = deque(maxlen=10)
        self.last_left = None
        self.last_right = None
        self.last_timestamp = None
        self.last_imu_x = None
        self.last_imu_y = None
        
        # Atributos para filtrado
        self.alpha = 0.3  # Factor de filtro de paso bajo (0-1, menor = más suavizado)
        self.prev_left = None
        self.prev_right = None
        
        # Parámetros de suavizado
        self.smoothing_enabled = True
        self.interpolation_enabled = True
        self.interpolation_steps = 3  # Cuántos puntos interpolar entre cada muestra
        
        # Contador de datos
        self.sample_count = 0
        
        # Filtros Kalman para cada ojo
        self.kalman_left = KalmanFilter(process_noise=0.001, measurement_noise=0.2, stability_factor=0.01)
        self.kalman_right = KalmanFilter(process_noise=0.001, measurement_noise=0.2, stability_factor=0.01)
        
        # Parámetro para activar/desactivar filtro Kalman
        self.kalman_enabled = True
        
        # Parámetros adicionales para suavizado
        self.extra_smoothing = True   # Suavizado adicional post-kalman
        self.spline_buffer_size = 5   # Tamaño del buffer para spline (más grande = más suave pero más lag)
        self.left_spline_buffer_x = deque(maxlen=self.spline_buffer_size)
        self.left_spline_buffer_y = deque(maxlen=self.spline_buffer_size)
        self.right_spline_buffer_x = deque(maxlen=self.spline_buffer_size)
        self.right_spline_buffer_y = deque(maxlen=self.spline_buffer_size)
    
    def reset_calibration(self):
        """Reinicia la calibración para calcular nuevos puntos de referencia"""
        self.left_eye_center = None
        self.right_eye_center = None
        self.is_calibrated = False
        self.calibration_data = {'left': [], 'right': []}
        self.sample_count = 0
        
        # Reiniciar filtros Kalman
        self.kalman_left.reset()
        self.kalman_right.reset()
    
    def process_eye_data(self, 
                         left_eye: Optional[List[float]], 
                         right_eye: Optional[List[float]],
                         imu_x: float,
                         imu_y: float,
                         timestamp: float) -> List[Tuple[Optional[List[float]], 
                                                      Optional[List[float]], 
                                                      float, 
                                                      float, 
                                                      float]]:
        """
        Procesa los datos de posición ocular para centrarlos en el origen y aplicar
        interpolación y suavizado para reducir el efecto de muestreo escalonado.
        
        Args:
            left_eye: [x, y] o None si no se detecta
            right_eye: [x, y] o None si no se detecta
            imu_x: Valor del IMU en eje X
            imu_y: Valor del IMU en eje Y
            timestamp: Marca de tiempo
            
        Returns:
            Lista de tuplas de datos procesados. Cada tupla tiene el formato:
            (left_eye, right_eye, imu_x, imu_y, timestamp)
            Si la interpolación está activada, retorna múltiples puntos interpolados.
        """
        result_points = []
        
        # Si el procesamiento está deshabilitado, retornar datos sin modificar
        if not self.processing_enabled:
            return [(left_eye, right_eye, imu_x, imu_y, timestamp)]
        
        # Procesar datos crudos e inicializar valores
        raw_processed_left = None
        raw_processed_right = None
        
        # Procesar ojo izquierdo si se detectó
        if left_eye is not None:
            # Durante fase de calibración
            if not self.is_calibrated and len(self.calibration_data['left']) < self.calibration_samples:
                self.calibration_data['left'].append(left_eye.copy())
            
            # Aplicar centrado si está calibrado
            if self.left_eye_center is not None:
                # Centrar en el origen (0,0)
                raw_processed_left = [
                    left_eye[0] - self.left_eye_center[0],
                    left_eye[1] - self.left_eye_center[1]
                ]
            else:
                raw_processed_left = left_eye.copy()
            
            # Aplicar filtro Kalman después del centrado si está habilitado
            if self.kalman_enabled:
                # Predicción del filtro Kalman
                self.kalman_left.predict()
                # Actualización con la medición
                kalman_left = self.kalman_left.update(raw_processed_left)
                # Convertir resultado de numpy a lista
                raw_processed_left = kalman_left.tolist()
                
                # Aplicar suavizado adicional si está habilitado
                if self.extra_smoothing:
                    raw_processed_left = self._apply_spline_smoothing(
                        raw_processed_left, 
                        self.left_spline_buffer_x,
                        self.left_spline_buffer_y
                    )
        
        # Procesar ojo derecho si se detectó
        if right_eye is not None:
            # Durante fase de calibración
            if not self.is_calibrated and len(self.calibration_data['right']) < self.calibration_samples:
                self.calibration_data['right'].append(right_eye.copy())
            
            # Aplicar centrado si está calibrado
            if self.right_eye_center is not None:
                # Centrar en el origen (0,0)
                raw_processed_right = [
                    right_eye[0] - self.right_eye_center[0],
                    right_eye[1] - self.right_eye_center[1]
                ]
            else:
                raw_processed_right = right_eye.copy()
            
            # Aplicar filtro Kalman después del centrado si está habilitado
            if self.kalman_enabled:
                # Predicción del filtro Kalman
                self.kalman_right.predict()
                # Actualización con la medición
                kalman_right = self.kalman_right.update(raw_processed_right)
                # Convertir resultado de numpy a lista
                raw_processed_right = kalman_right.tolist()
                
                # Aplicar suavizado adicional si está habilitado
                if self.extra_smoothing:
                    raw_processed_right = self._apply_spline_smoothing(
                        raw_processed_right, 
                        self.right_spline_buffer_x,
                        self.right_spline_buffer_y
                    )
        
        # Aplicar interpolación si está habilitada y tenemos datos anteriores
        if self.interpolation_enabled and self.last_timestamp is not None:
            # Calcular cuántos puntos interpolar
            time_diff = timestamp - self.last_timestamp
            
            # Almacenar nuevos valores para interpolación futura
            if raw_processed_left is not None:
                self.left_values_x.append(raw_processed_left[0])
                self.left_values_y.append(raw_processed_left[1])
            
            if raw_processed_right is not None:
                self.right_values_x.append(raw_processed_right[0])
                self.right_values_y.append(raw_processed_right[1])
            
            self.timestamps.append(timestamp)
            
            # Interpolar entre el último punto y el actual
            if self.last_left is not None and raw_processed_left is not None:
                for i in range(1, self.interpolation_steps + 1):
                    # Calcular punto intermedio
                    t = i / (self.interpolation_steps + 1)
                    interp_time = self.last_timestamp + t * time_diff
                    
                    interp_left_x = self.last_left[0] + t * (raw_processed_left[0] - self.last_left[0])
                    interp_left_y = self.last_left[1] + t * (raw_processed_left[1] - self.last_left[1])
                    
                    # Aplicar suavizado a través de media móvil
                    if self.smoothing_enabled and len(self.left_history_x) > 0:
                        self.left_history_x.append(interp_left_x)
                        self.left_history_y.append(interp_left_y)
                        interp_left_x = sum(self.left_history_x) / len(self.left_history_x)
                        interp_left_y = sum(self.left_history_y) / len(self.left_history_y)
                    
                    interp_left = [interp_left_x, interp_left_y]
                    
                    # Interpolar valores para ojo derecho
                    interp_right = None
                    if self.last_right is not None and raw_processed_right is not None:
                        interp_right_x = self.last_right[0] + t * (raw_processed_right[0] - self.last_right[0])
                        interp_right_y = self.last_right[1] + t * (raw_processed_right[1] - self.last_right[1])
                        
                        # Aplicar suavizado a través de media móvil
                        if self.smoothing_enabled and len(self.right_history_x) > 0:
                            self.right_history_x.append(interp_right_x)
                            self.right_history_y.append(interp_right_y)
                            interp_right_x = sum(self.right_history_x) / len(self.right_history_x)
                            interp_right_y = sum(self.right_history_y) / len(self.right_history_y)
                        
                        interp_right = [interp_right_x, interp_right_y]
                    
                    # Interpolar valores del IMU (lineal)
                    if self.last_imu_x is not None and self.last_imu_y is not None:
                        interp_imu_x = self.last_imu_x + t * (imu_x - self.last_imu_x)
                        interp_imu_y = self.last_imu_y + t * (imu_y - self.last_imu_y)
                    else:
                        interp_imu_x = imu_x
                        interp_imu_y = imu_y
                    
                    # Añadir punto interpolado al resultado
                    result_points.append((interp_left, interp_right, interp_imu_x, interp_imu_y, interp_time))
        
        # Aplicar filtrado exponencial al punto actual
        if self.smoothing_enabled:
            # Ojo izquierdo
            if raw_processed_left is not None:
                # Actualizar historial para media móvil
                self.left_history_x.append(raw_processed_left[0])
                self.left_history_y.append(raw_processed_left[1])
                
                # Calcular valor suavizado
                smooth_left_x = sum(self.left_history_x) / len(self.left_history_x)
                smooth_left_y = sum(self.left_history_y) / len(self.left_history_y)
                
                # Aplicar filtro exponencial si hay valor previo
                if self.prev_left is not None:
                    smooth_left_x = self.alpha * smooth_left_x + (1 - self.alpha) * self.prev_left[0]
                    smooth_left_y = self.alpha * smooth_left_y + (1 - self.alpha) * self.prev_left[1]
                
                processed_left = [smooth_left_x, smooth_left_y]
                self.prev_left = processed_left.copy()
            else:
                processed_left = None
            
            # Ojo derecho
            if raw_processed_right is not None:
                # Actualizar historial para media móvil
                self.right_history_x.append(raw_processed_right[0])
                self.right_history_y.append(raw_processed_right[1])
                
                # Calcular valor suavizado
                smooth_right_x = sum(self.right_history_x) / len(self.right_history_x)
                smooth_right_y = sum(self.right_history_y) / len(self.right_history_y)
                
                # Aplicar filtro exponencial si hay valor previo
                if self.prev_right is not None:
                    smooth_right_x = self.alpha * smooth_right_x + (1 - self.alpha) * self.prev_right[0]
                    smooth_right_y = self.alpha * smooth_right_y + (1 - self.alpha) * self.prev_right[1]
                
                processed_right = [smooth_right_x, smooth_right_y]
                self.prev_right = processed_right.copy()
            else:
                processed_right = None
        else:
            processed_left = raw_processed_left
            processed_right = raw_processed_right
        
        # Almacenar valores actuales para futuras interpolaciones
        self.last_left = raw_processed_left
        self.last_right = raw_processed_right
        self.last_timestamp = timestamp
        self.last_imu_x = imu_x
        self.last_imu_y = imu_y
        
        # Añadir el punto actual procesado
        result_points.append((processed_left, processed_right, imu_x, imu_y, timestamp))
        
        # Incrementar contador de muestras
        self.sample_count += 1
        
        # Verificar si es momento de calcular centros después de recopilar suficientes muestras
        if not self.is_calibrated and min(len(self.calibration_data['left']), len(self.calibration_data['right'])) >= self.calibration_samples:
            self._calculate_centers()
        
        return result_points
    
    def _calculate_centers(self):
        """Calcula los puntos centrales de referencia para ambos ojos"""
        # Solo calcular si hay suficientes datos
        if len(self.calibration_data['left']) > 0:
            # Convertir a array numpy para facilitar cálculos
            left_samples = np.array(self.calibration_data['left'])
            # Calcular promedio de x e y para ojo izquierdo
            self.left_eye_center = [
                np.mean(left_samples[:, 0]),
                np.mean(left_samples[:, 1])
            ]
            print(f"Centro calculado para ojo izquierdo: {self.left_eye_center}")
        
        if len(self.calibration_data['right']) > 0:
            # Convertir a array numpy para facilitar cálculos
            right_samples = np.array(self.calibration_data['right'])
            # Calcular promedio de x e y para ojo derecho
            self.right_eye_center = [
                np.mean(right_samples[:, 0]),
                np.mean(right_samples[:, 1])
            ]
            print(f"Centro calculado para ojo derecho: {self.right_eye_center}")
        
        # Marcar como calibrado
        self.is_calibrated = True
        print("Calibración completada - Los datos ahora estarán centrados en 0")
    
    def set_filter_strength(self, alpha: float):
        """
        Establece la intensidad del filtro de suavizado.
        
        Args:
            alpha: Valor entre 0 y 1. Valores más bajos = más suavizado.
        """
        if 0 <= alpha <= 1:
            self.alpha = alpha
        else:
            raise ValueError("El valor alpha debe estar entre 0 y 1")
    
    def set_interpolation_steps(self, steps: int):
        """
        Establece el número de pasos de interpolación entre cada muestra.
        
        Args:
            steps: Número de puntos a interpolar entre muestras (1-5 recomendado)
        """
        if 0 <= steps <= 10:  # Límite superior arbitrario por rendimiento
            self.interpolation_steps = steps
        else:
            raise ValueError("Los pasos de interpolación deben estar entre 0 y 10")
    
    def set_smoothing_enabled(self, enabled: bool):
        """Activa o desactiva el suavizado"""
        self.smoothing_enabled = enabled
    
    def set_interpolation_enabled(self, enabled: bool):
        """Activa o desactiva la interpolación"""
        self.interpolation_enabled = enabled
    
    def set_kalman_enabled(self, enabled: bool):
        """Activa o desactiva el filtro Kalman"""
        self.kalman_enabled = enabled
    
    def set_kalman_parameters(self, process_noise: float, measurement_noise: float, stability_factor: float = 0.01):
        """
        Configura los parámetros del filtro Kalman.
        
        Args:
            process_noise: Ruido del proceso (0.0001-0.1 recomendado)
            measurement_noise: Ruido de la medición (0.01-1.0 recomendado)
            stability_factor: Factor de estabilidad (0.001-0.1 recomendado)
        """
        if process_noise <= 0 or measurement_noise <= 0 or stability_factor <= 0:
            raise ValueError("Los valores de ruido y estabilidad deben ser positivos")
        
        # Crear nuevos filtros con los parámetros actualizados
        # Preservamos el estado actual si los filtros estaban inicializados
        left_state = self.kalman_left.state if self.kalman_left.initialized else None
        right_state = self.kalman_right.state if self.kalman_right.initialized else None
        
        self.kalman_left = KalmanFilter(
            initial_state=left_state[:2] if left_state is not None else None,
            process_noise=process_noise,
            measurement_noise=measurement_noise,
            stability_factor=stability_factor
        )
        
        self.kalman_right = KalmanFilter(
            initial_state=right_state[:2] if right_state is not None else None,
            process_noise=process_noise,
            measurement_noise=measurement_noise,
            stability_factor=stability_factor
        )
        
    def set_extra_smoothing(self, enabled: bool, buffer_size: int = 5):
        """
        Activa o desactiva el suavizado adicional post-Kalman.
        
        Args:
            enabled: True para activar, False para desactivar
            buffer_size: Tamaño del buffer para spline (3-10 recomendado)
        """
        self.extra_smoothing = enabled
        
        if 3 <= buffer_size <= 20:
            self.spline_buffer_size = buffer_size
            # Reiniciar buffers con nuevo tamaño
            self.left_spline_buffer_x = deque(self.left_spline_buffer_x, maxlen=buffer_size)
            self.left_spline_buffer_y = deque(self.left_spline_buffer_y, maxlen=buffer_size)
            self.right_spline_buffer_x = deque(self.right_spline_buffer_x, maxlen=buffer_size)
            self.right_spline_buffer_y = deque(self.right_spline_buffer_y, maxlen=buffer_size)
        else:
            raise ValueError("El tamaño del buffer debe estar entre 3 y 20")
            
    def _apply_spline_smoothing(self, point, buffer_x, buffer_y):
        """
        Aplica suavizado mediante interpolación spline a un punto.
        
        Args:
            point: [x, y] punto a suavizar
            buffer_x: buffer de coordenadas x
            buffer_y: buffer de coordenadas y
            
        Returns:
            [x, y] punto suavizado
        """
        if point is None:
            return None
            
        # Añadir punto actual al buffer
        buffer_x.append(point[0])
        buffer_y.append(point[1])
        
        # Si no tenemos suficientes puntos, devolver el punto tal cual
        if len(buffer_x) < 4:
            return point
            
        # Realizar suavizado mediante promedio ponderado con más peso en puntos recientes
        weights = np.array([0.1, 0.15, 0.2, 0.25, 0.3][:len(buffer_x)])
        # Normalizar pesos
        weights = weights / np.sum(weights)
        
        # Calcular promedio ponderado
        smoothed_x = sum(x * w for x, w in zip(buffer_x, weights[-len(buffer_x):]))
        smoothed_y = sum(y * w for y, w in zip(buffer_y, weights[-len(buffer_y):]))
        
        return [smoothed_x, smoothed_y]
    
    def set_history_size(self, size: int):
        """
        Establece el tamaño de la ventana para la media móvil.
        
        Args:
            size: Número de muestras para promediar (3-10 recomendado)
        """
        if 1 <= size <= 20:  # Límite superior arbitrario
            self.history_size = size
            # Reiniciar colas con nuevo tamaño
            self.left_history_x = deque(self.left_history_x, maxlen=size)
            self.left_history_y = deque(self.left_history_y, maxlen=size)
            self.right_history_x = deque(self.right_history_x, maxlen=size)
            self.right_history_y = deque(self.right_history_y, maxlen=size)
        else:
            raise ValueError("El tamaño de historia debe estar entre 1 y 20")
    
    def get_center_offsets(self) -> Dict[str, Union[List[float], None]]:
        """Retorna los valores de referencia calculados para el centro de cada ojo"""
        return {
            'left': self.left_eye_center,
            'right': self.right_eye_center
        }
