import numpy as np
import time
from typing import Optional, Tuple, List, Dict
from PySide6.QtCore import QObject, Signal


class CalibrationManager(QObject):
    """
    Gestor de calibración que convierte posiciones oculares de píxeles a grados.
    MODIFICADO: Ahora recibe listas completas de posiciones en lugar de una por una.
    """
    
    # === VARIABLES GEOMÉTRICAS ===
    LED_DISTANCE_FROM_MIDLINE = 6.0  # cm - Distancia de cada LED desde línea media (nariz)
    LED_DISTANCE_FROM_EYE = 9.0      # cm - Distancia perpendicular de LEDs a cada ojo
    LED_SEPARATION_TOTAL = LED_DISTANCE_FROM_MIDLINE * 2  # cm - Separación total entre LEDs (14cm)
    
    # Comandos seriales para LEDs
    LED_LEFT_ON = "L_12_ON"
    LED_LEFT_OFF = "L_12_OFF"
    LED_RIGHT_ON = "L_14_ON"
    LED_RIGHT_OFF = "L_14_OFF"
    PAUSE_COMMAND = "PAUSE"
    
    # Señales para comunicación con UI
    calibration_progress = Signal(str)  # Mensaje de progreso
    calibration_completed = Signal(bool)  # True si exitosa, False si falló
    
    def __init__(self, serial_handler=None):
        super().__init__()
        
        # Referencia al manejador serial
        self.serial_handler = serial_handler
        
        # Estado de calibración
        self.is_calibrated = False
        
        # MODIFICADO: Ahora almacenamos las listas completas de posiciones
        self.calibration_data = {
            'left_led': {
                'raw_positions': [],  # Lista completa de posiciones capturadas
                'average_left_eye': None,  # Promedio calculado del ojo izquierdo
                'average_right_eye': None  # Promedio calculado del ojo derecho
            },
            'right_led': {
                'raw_positions': [],  # Lista completa de posiciones capturadas
                'average_left_eye': None,  # Promedio calculado del ojo izquierdo
                'average_right_eye': None  # Promedio calculado del ojo derecho
            }
        }
        
        # Factores de conversión píxel → grados
        self.conversion_factors = {
            'left_eye': {'px_per_degree_x': 1.0, 'px_per_degree_y': 1.0},
            'right_eye': {'px_per_degree_x': 1.0, 'px_per_degree_y': 1.0}
        }
        
        # Punto de referencia (centro de calibración)
        self.reference_points = {
            'left_eye': {'x': 0.0, 'y': 0.0},
            'right_eye': {'x': 0.0, 'y': 0.0}
        }
        
        print(f"CalibrationManager inicializado:")
        print(f"  - Separación LEDs: {self.LED_SEPARATION_TOTAL} cm")
        print(f"  - Distancia a ojos: {self.LED_DISTANCE_FROM_EYE} cm")
        print(f"  - Ángulo teórico entre LEDs: {self._calculate_theoretical_angle():.1f}°")
    
    def _calculate_theoretical_angle(self) -> float:
        """
        Calcula el ángulo teórico entre los dos LEDs desde la perspectiva del ojo.
        """
        angle_rad = np.arctan(self.LED_SEPARATION_TOTAL / self.LED_DISTANCE_FROM_EYE)
        angle_deg = np.degrees(angle_rad)
        return angle_deg
    
    def start_calibration(self) -> bool:
        """
        Inicia el proceso de calibración.
        """
        if not self.serial_handler:
            print("Error: No hay conexión serial disponible")
            return False
        
        print("=== INICIANDO CALIBRACIÓN OCULAR ===")
        
        # Pausar el IMU para evitar interferencias
        self.serial_handler.send_data(self.PAUSE_COMMAND)
        time.sleep(0.1)
        
        # Resetear datos de calibración
        self.calibration_data = {
            'left_led': {
                'raw_positions': [],
                'average_left_eye': None,
                'average_right_eye': None
            },
            'right_led': {
                'raw_positions': [],
                'average_left_eye': None,
                'average_right_eye': None
            }
        }
        self.is_calibrated = False
        
        self.calibration_progress.emit("Calibración iniciada - Preparando LEDs...")
        return True
    
    def start_left_led_capture(self) -> bool:
        """
        Enciende el LED izquierdo para iniciar captura.
        """
        if not self.serial_handler:
            return False
            
        print("=== ENCENDIENDO LED IZQUIERDO ===")
        self.serial_handler.send_data(self.LED_LEFT_ON)
        print("LED izquierdo encendido")
        self.calibration_progress.emit("LED izquierdo encendido - Mire la luz verde")
        
        return True
    
    def finish_left_led_capture(self) -> bool:
        """
        Apaga el LED izquierdo.
        """
        print("=== APAGANDO LED IZQUIERDO ===")
        self.serial_handler.send_data(self.LED_LEFT_OFF)
        print("LED izquierdo apagado")
        return True
    
    def start_right_led_capture(self) -> bool:
        """
        Enciende el LED derecho para iniciar captura.
        """
        if not self.serial_handler:
            return False
            
        print("=== ENCENDIENDO LED DERECHO ===")
        self.serial_handler.send_data(self.LED_RIGHT_ON)
        print("LED derecho encendido")
        self.calibration_progress.emit("LED derecho encendido - Mire la luz verde")
        
        return True
    
    def finish_right_led_capture(self) -> bool:
        """
        Apaga el LED derecho.
        """
        print("=== APAGANDO LED DERECHO ===")
        self.serial_handler.send_data(self.LED_RIGHT_OFF)
        print("LED derecho apagado")
        return True
    
    def process_led_data(self, led_name: str, position_list: List[Dict]) -> bool:
        """
        NUEVO: Procesa una lista completa de posiciones capturadas para un LED.
        
        Args:
            led_name: 'left' o 'right'
            position_list: Lista de diccionarios con estructura:
                          [{'timestamp': float, 'left_eye': [x,y] o None, 'right_eye': [x,y] o None}, ...]
        
        Returns:
            True si el procesamiento fue exitoso
        """
        if led_name not in ['left', 'right']:
            print(f"Error: led_name debe ser 'left' o 'right', recibido: {led_name}")
            return False
        
        if not position_list:
            print(f"Error: No hay datos para procesar en LED {led_name}")
            return False
        
        print(f"=== PROCESANDO DATOS LED {led_name.upper()} ===")
        print(f"Total de muestras recibidas: {len(position_list)}")
        
        # Almacenar datos crudos
        led_key = f"{led_name}_led"
        self.calibration_data[led_key]['raw_positions'] = position_list.copy()
        
        # Separar posiciones válidas por ojo
        left_eye_positions = []
        right_eye_positions = []
        
        for record in position_list:
            if record.get('left_eye') is not None:
                left_eye_positions.append(record['left_eye'])
            
            if record.get('right_eye') is not None:
                right_eye_positions.append(record['right_eye'])
        
        print(f"Posiciones válidas ojo izquierdo: {len(left_eye_positions)}")
        print(f"Posiciones válidas ojo derecho: {len(right_eye_positions)}")
        
        # Calcular promedios si hay suficientes datos
        if len(left_eye_positions) >= 3:  # Mínimo 3 puntos para promedio confiable
            avg_left = self._calculate_robust_average(left_eye_positions)
            self.calibration_data[led_key]['average_left_eye'] = avg_left
            print(f"Promedio ojo izquierdo → LED {led_name}: {avg_left}")
        else:
            print(f"Insuficientes datos para ojo izquierdo en LED {led_name}")
        
        if len(right_eye_positions) >= 3:  # Mínimo 3 puntos para promedio confiable
            avg_right = self._calculate_robust_average(right_eye_positions)
            self.calibration_data[led_key]['average_right_eye'] = avg_right
            print(f"Promedio ojo derecho → LED {led_name}: {avg_right}")
        else:
            print(f"Insuficientes datos para ojo derecho en LED {led_name}")
        
        # Verificar que se capturó al menos un ojo
        success = (self.calibration_data[led_key]['average_left_eye'] is not None or 
                  self.calibration_data[led_key]['average_right_eye'] is not None)
        
        if success:
            self.calibration_progress.emit(f"Datos LED {led_name} procesados exitosamente")
        else:
            self.calibration_progress.emit(f"Error: No se pudieron procesar datos LED {led_name}")
        
        return success
    
    def _calculate_robust_average(self, positions: List[List[float]]) -> List[float]:
        """
        Calcula un promedio robusto eliminando outliers.
        
        Args:
            positions: Lista de posiciones [[x, y], [x, y], ...]
        
        Returns:
            [x_promedio, y_promedio]
        """
        if not positions:
            return [0.0, 0.0]
        
        # Convertir a array numpy para facilitar cálculos
        pos_array = np.array(positions)
        
        # Si hay pocos puntos, simplemente promediar
        if len(positions) <= 5:
            return [float(np.mean(pos_array[:, 0])), float(np.mean(pos_array[:, 1]))]
        
        # Para más puntos, eliminar outliers usando percentiles
        x_positions = pos_array[:, 0]
        y_positions = pos_array[:, 1]
        
        # Calcular percentiles 25 y 75 para detectar outliers
        x_q25, x_q75 = np.percentile(x_positions, [25, 75])
        y_q25, y_q75 = np.percentile(y_positions, [25, 75])
        
        # Calcular IQR (Interquartile Range)
        x_iqr = x_q75 - x_q25
        y_iqr = y_q75 - y_q25
        
        # Definir límites para outliers (1.5 * IQR)
        x_lower = x_q25 - 1.5 * x_iqr
        x_upper = x_q75 + 1.5 * x_iqr
        y_lower = y_q25 - 1.5 * y_iqr
        y_upper = y_q75 + 1.5 * y_iqr
        
        # Filtrar outliers
        valid_mask = (
            (x_positions >= x_lower) & (x_positions <= x_upper) &
            (y_positions >= y_lower) & (y_positions <= y_upper)
        )
        
        filtered_positions = pos_array[valid_mask]
        
        if len(filtered_positions) > 0:
            avg_x = float(np.mean(filtered_positions[:, 0]))
            avg_y = float(np.mean(filtered_positions[:, 1]))
            print(f"  Outliers eliminados: {len(positions) - len(filtered_positions)}/{len(positions)}")
        else:
            # Si todos son outliers, usar promedio simple
            avg_x = float(np.mean(pos_array[:, 0]))
            avg_y = float(np.mean(pos_array[:, 1]))
            print(f"  Sin outliers detectados")
        
        return [avg_x, avg_y]
    
    def calculate_calibration(self) -> bool:
        """
        Calcula los factores de conversión píxel → grados basado en las capturas.
        """
        print("=== CALCULANDO CALIBRACIÓN ===")
        
        theoretical_angle = self._calculate_theoretical_angle()
        print(f"Ángulo teórico entre LEDs: {theoretical_angle:.2f}°")
        
        # Calcular para ojo izquierdo
        if (self.calibration_data['left_led']['average_left_eye'] and 
            self.calibration_data['right_led']['average_left_eye']):
            
            left_pos = self.calibration_data['left_led']['average_left_eye']
            right_pos = self.calibration_data['right_led']['average_left_eye']
            
            # Diferencia en píxeles entre las dos posiciones
            pixel_diff_x = abs(right_pos[0] - left_pos[0])
            pixel_diff_y = abs(right_pos[1] - left_pos[1])
            
            # Factor de conversión (píxeles por grado)
            if pixel_diff_x > 0:
                self.conversion_factors['left_eye']['px_per_degree_x'] = pixel_diff_x / theoretical_angle
            if pixel_diff_y > 0:
                self.conversion_factors['left_eye']['px_per_degree_y'] = pixel_diff_y / theoretical_angle
            
            # Punto de referencia (centro entre ambas posiciones)
            self.reference_points['left_eye']['x'] = (left_pos[0] + right_pos[0]) / 2
            self.reference_points['left_eye']['y'] = (left_pos[1] + right_pos[1]) / 2
            
            print(f"Ojo izquierdo calibrado:")
            print(f"  - Píxeles/grado X: {self.conversion_factors['left_eye']['px_per_degree_x']:.2f}")
            print(f"  - Píxeles/grado Y: {self.conversion_factors['left_eye']['px_per_degree_y']:.2f}")
            print(f"  - Centro de referencia: ({self.reference_points['left_eye']['x']:.1f}, {self.reference_points['left_eye']['y']:.1f})")
        
        # Calcular para ojo derecho
        if (self.calibration_data['left_led']['average_right_eye'] and 
            self.calibration_data['right_led']['average_right_eye']):
            
            left_pos = self.calibration_data['left_led']['average_right_eye']
            right_pos = self.calibration_data['right_led']['average_right_eye']
            
            # Diferencia en píxeles entre las dos posiciones
            pixel_diff_x = abs(right_pos[0] - left_pos[0])
            pixel_diff_y = abs(right_pos[1] - left_pos[1])
            
            # Factor de conversión (píxeles por grado)
            if pixel_diff_x > 0:
                self.conversion_factors['right_eye']['px_per_degree_x'] = pixel_diff_x / theoretical_angle
            if pixel_diff_y > 0:
                self.conversion_factors['right_eye']['px_per_degree_y'] = pixel_diff_y / theoretical_angle
            
            # Punto de referencia (centro entre ambas posiciones)
            self.reference_points['right_eye']['x'] = (left_pos[0] + right_pos[0]) / 2
            self.reference_points['right_eye']['y'] = (left_pos[1] + right_pos[1]) / 2
            
            print(f"Ojo derecho calibrado:")
            print(f"  - Píxeles/grado X: {self.conversion_factors['right_eye']['px_per_degree_x']:.2f}")
            print(f"  - Píxeles/grado Y: {self.conversion_factors['right_eye']['px_per_degree_y']:.2f}")
            print(f"  - Centro de referencia: ({self.reference_points['right_eye']['x']:.1f}, {self.reference_points['right_eye']['y']:.1f})")
        
        # Verificar si al menos un ojo fue calibrado
        left_calibrated = (self.conversion_factors['left_eye']['px_per_degree_x'] > 1.0)
        right_calibrated = (self.conversion_factors['right_eye']['px_per_degree_x'] > 1.0)
        
        self.is_calibrated = left_calibrated or right_calibrated
        
        if self.is_calibrated:
            self.calibration_progress.emit("¡Calibración completada exitosamente!")
            print("=== CALIBRACIÓN EXITOSA ===")
        else:
            self.calibration_progress.emit("Error: Calibración falló")
            print("=== CALIBRACIÓN FALLÓ ===")
        
        self.calibration_completed.emit(self.is_calibrated)
        return self.is_calibrated
    
    def convert_to_degrees(self, left_eye_pos: Optional[List[float]], 
                          right_eye_pos: Optional[List[float]]) -> Tuple[Optional[List[float]], Optional[List[float]]]:
        """
        Convierte posiciones de píxeles a grados usando la calibración.
        """
        if not self.is_calibrated:
            return left_eye_pos, right_eye_pos
        
        left_eye_degrees = None
        right_eye_degrees = None
        
        # Convertir ojo izquierdo
        if left_eye_pos and len(left_eye_pos) >= 2:
            ref_x = self.reference_points['left_eye']['x']
            ref_y = self.reference_points['left_eye']['y']
            px_per_deg_x = self.conversion_factors['left_eye']['px_per_degree_x']
            px_per_deg_y = self.conversion_factors['left_eye']['px_per_degree_y']
            
            if px_per_deg_x > 0 and px_per_deg_y > 0:
                degree_x = (left_eye_pos[0] - ref_x) / px_per_deg_x
                degree_y = (left_eye_pos[1] - ref_y) / px_per_deg_y
                left_eye_degrees = [degree_x, degree_y]
        
        # Convertir ojo derecho
        if right_eye_pos and len(right_eye_pos) >= 2:
            ref_x = self.reference_points['right_eye']['x']
            ref_y = self.reference_points['right_eye']['y']
            px_per_deg_x = self.conversion_factors['right_eye']['px_per_degree_x']
            px_per_deg_y = self.conversion_factors['right_eye']['px_per_degree_y']
            
            if px_per_deg_x > 0 and px_per_deg_y > 0:
                degree_x = (right_eye_pos[0] - ref_x) / px_per_deg_x
                degree_y = (right_eye_pos[1] - ref_y) / px_per_deg_y
                right_eye_degrees = [degree_x, degree_y]
        
        return left_eye_degrees, right_eye_degrees
    
    def get_calibration_summary(self) -> Dict:
        """
        Obtiene un resumen de la calibración actual.
        """
        return {
            'is_calibrated': self.is_calibrated,
            'theoretical_angle': self._calculate_theoretical_angle(),
            'led_separation_cm': self.LED_SEPARATION_TOTAL,
            'led_distance_cm': self.LED_DISTANCE_FROM_EYE,
            'conversion_factors': self.conversion_factors.copy(),
            'reference_points': self.reference_points.copy(),
            'calibration_data': self.calibration_data.copy()
        }
    
    def reset_calibration(self):
        """Resetea toda la calibración."""
        print("Reseteando calibración...")
        
        self.is_calibrated = False
        self.calibration_data = {
            'left_led': {
                'raw_positions': [],
                'average_left_eye': None,
                'average_right_eye': None
            },
            'right_led': {
                'raw_positions': [],
                'average_left_eye': None,
                'average_right_eye': None
            }
        }
        self.conversion_factors = {
            'left_eye': {'px_per_degree_x': 1.0, 'px_per_degree_y': 1.0},
            'right_eye': {'px_per_degree_x': 1.0, 'px_per_degree_y': 1.0}
        }
        self.reference_points = {
            'left_eye': {'x': 0.0, 'y': 0.0},
            'right_eye': {'x': 0.0, 'y': 0.0}
        }
        
        self.calibration_progress.emit("Calibración reseteada")