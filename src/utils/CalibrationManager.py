import numpy as np
import time
from typing import Optional, Tuple, List, Dict
from PySide6.QtCore import QObject, Signal


class CalibrationManager(QObject):
    """
    Gestor de calibración que convierte posiciones oculares de píxeles a grados.
    Usa LEDs de referencia para establecer la escala angular.
    """
    
    # === VARIABLES GEOMÉTRICAS - MODIFICAR AQUÍ PARA CAMBIOS DE MÁSCARA ===
    LED_DISTANCE_FROM_MIDLINE = 7.0  # cm - Distancia de cada LED desde línea media (nariz)
    LED_DISTANCE_FROM_EYE = 5.0      # cm - Distancia perpendicular de LEDs a cada ojo
    LED_SEPARATION_TOTAL = LED_DISTANCE_FROM_MIDLINE * 2  # cm - Separación total entre LEDs (14cm)
    
    # Comandos seriales para LEDs
    LED_LEFT_ON = "L_12_ON"
    LED_LEFT_OFF = "L_12_OFF"
    LED_RIGHT_ON = "L_14_ON"
    LED_RIGHT_OFF = "L_14_OFF"
    PAUSE_COMMAND = "PAUSE"
    
    # Señales para comunicación con UI (si se necesita en el futuro)
    calibration_progress = Signal(str)  # Mensaje de progreso
    calibration_completed = Signal(bool)  # True si exitosa, False si falló
    
    def __init__(self, serial_handler=None):
        super().__init__()
        
        # Referencia al manejador serial
        self.serial_handler = serial_handler
        
        # Estado de calibración
        self.is_calibrated = False
        self.calibration_data = {
            'left_led': {'left_eye': None, 'right_eye': None},
            'right_led': {'left_eye': None, 'right_eye': None}
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
        
        Returns:
            Ángulo en grados
        """
        # Usando trigonometría: ángulo = arctan(separación_horizontal / distancia_perpendicular)
        angle_rad = np.arctan(self.LED_SEPARATION_TOTAL / self.LED_DISTANCE_FROM_EYE)
        angle_deg = np.degrees(angle_rad)
        return angle_deg
    
    def start_calibration(self) -> bool:
        """
        Inicia el proceso de calibración.
        
        Returns:
            True si se puede iniciar la calibración
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
            'left_led': {'left_eye': None, 'right_eye': None},
            'right_led': {'left_eye': None, 'right_eye': None}
        }
        self.is_calibrated = False
        
        self.calibration_progress.emit("Calibración iniciada - Preparando LEDs...")
        return True
    
    def start_left_led_capture(self) -> bool:
        """
        Inicia la captura del LED izquierdo - SOLO ENCIENDE EL LED.
        
        Returns:
            True si el LED se encendió correctamente
        """
        if not self.serial_handler:
            return False
            
        print("=== ENCENDIENDO LED IZQUIERDO ===")
        self.serial_handler.send_data(self.LED_LEFT_ON)
        print("LED izquierdo encendido")
        self.calibration_progress.emit("LED izquierdo encendido - Mire la luz verde")
        
        # Resetear datos de captura para este LED
        self.calibration_data['left_led']['left_eye'] = None
        self.calibration_data['left_led']['right_eye'] = None
        
        return True
    
    def capture_left_led_position(self, left_eye_pos: Optional[List[float]], 
                                 right_eye_pos: Optional[List[float]]) -> bool:
        """
        Captura UNA posición para el LED izquierdo - SIN TIMING.
        
        Args:
            left_eye_pos: [x, y] en píxeles del ojo izquierdo
            right_eye_pos: [x, y] en píxeles del ojo derecho
            
        Returns:
            True si se capturó al menos una posición
        """
        captured = False
        
        # Capturar posiciones si están disponibles
        if left_eye_pos and len(left_eye_pos) >= 2:
            self.calibration_data['left_led']['left_eye'] = [float(left_eye_pos[0]), float(left_eye_pos[1])]
            print(f"Ojo izquierdo → LED izquierdo: {self.calibration_data['left_led']['left_eye']}")
            captured = True
        
        if right_eye_pos and len(right_eye_pos) >= 2:
            self.calibration_data['left_led']['right_eye'] = [float(right_eye_pos[0]), float(right_eye_pos[1])]
            print(f"Ojo derecho → LED izquierdo: {self.calibration_data['left_led']['right_eye']}")
            captured = True
        
        return captured
    
    def finish_left_led_capture(self) -> bool:
        """
        Finaliza la captura del LED izquierdo - SOLO APAGA EL LED.
        
        Returns:
            True si se capturó correctamente
        """
        print("=== FINALIZANDO CAPTURA LED IZQUIERDO ===")
        
        # Apagar LED izquierdo
        self.serial_handler.send_data(self.LED_LEFT_OFF)
        print("LED izquierdo apagado")
        
        # Verificar que se capturó al menos un ojo
        success = (self.calibration_data['left_led']['left_eye'] is not None or 
                  self.calibration_data['left_led']['right_eye'] is not None)
        
        if success:
            self.calibration_progress.emit("Posición LED izquierdo capturada exitosamente")
            print("Captura LED izquierdo exitosa")
        else:
            self.calibration_progress.emit("Error: No se detectaron ojos en LED izquierdo")
            print("Error: No se detectaron ojos en LED izquierdo")
        
        return success
    
    def capture_right_led_position(self, left_eye_pos: Optional[List[float]], 
                                  right_eye_pos: Optional[List[float]]) -> bool:
        """
        Captura posiciones oculares cuando el paciente mira el LED derecho.
        
        Args:
            left_eye_pos: [x, y] en píxeles del ojo izquierdo
            right_eye_pos: [x, y] en píxeles del ojo derecho
            
        Returns:
            True si la captura fue exitosa
        """
        print("=== INICIANDO CAPTURA LED DERECHO ===")
        
        # Encender LED derecho PRIMERO
        self.serial_handler.send_data(self.LED_RIGHT_ON)
        print("LED derecho encendido")
        self.calibration_progress.emit("LED derecho encendido - Mire la luz roja")
        
        # Dar tiempo amplio para que el paciente mueva los ojos y se estabilice
        print("Esperando que el paciente enfoque el LED derecho...")
        time.sleep(3.0)  # 3 segundos para mover ojos
        
        self.calibration_progress.emit("Preparándose para grabar...")
        time.sleep(1.0)  # 1 segundo adicional de preparación
        
        # Ahora capturar posiciones (el LED sigue encendido)
        self.calibration_progress.emit("¡GRABANDO! Mantenga la mirada fija")
        
        if left_eye_pos and len(left_eye_pos) >= 2:
            self.calibration_data['right_led']['left_eye'] = [float(left_eye_pos[0]), float(left_eye_pos[1])]
            print(f"Ojo izquierdo → LED derecho: {self.calibration_data['right_led']['left_eye']}")
        
        if right_eye_pos and len(right_eye_pos) >= 2:
            self.calibration_data['right_led']['right_eye'] = [float(right_eye_pos[0]), float(right_eye_pos[1])]
            print(f"Ojo derecho → LED derecho: {self.calibration_data['right_led']['right_eye']}")
        
        # Mantener LED encendido durante la grabación
        time.sleep(2.0)  # 2 segundos más de grabación
        
        # AHORA SÍ apagar LED derecho
        self.serial_handler.send_data(self.LED_RIGHT_OFF)
        print("LED derecho apagado")
        
        # Verificar que se capturó al menos un ojo
        success = (self.calibration_data['right_led']['left_eye'] is not None or 
                  self.calibration_data['right_led']['right_eye'] is not None)
        
        if success:
            self.calibration_progress.emit("Posición LED derecho capturada exitosamente")
            print("Captura LED derecho exitosa")
        else:
            self.calibration_progress.emit("Error: No se detectaron ojos en LED derecho")
            print("Error: No se detectaron ojos en LED derecho")
        
        return success
    
    def calculate_calibration(self) -> bool:
        """
        Calcula los factores de conversión píxel → grados basado en las capturas.
        
        Returns:
            True si la calibración fue exitosa
        """
        print("=== CALCULANDO CALIBRACIÓN ===")
        
        theoretical_angle = self._calculate_theoretical_angle()
        print(f"Ángulo teórico entre LEDs: {theoretical_angle:.2f}°")
        
        # Calcular para ojo izquierdo
        if (self.calibration_data['left_led']['left_eye'] and 
            self.calibration_data['right_led']['left_eye']):
            
            left_pos = self.calibration_data['left_led']['left_eye']
            right_pos = self.calibration_data['right_led']['left_eye']
            
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
        if (self.calibration_data['left_led']['right_eye'] and 
            self.calibration_data['right_led']['right_eye']):
            
            left_pos = self.calibration_data['left_led']['right_eye']
            right_pos = self.calibration_data['right_led']['right_eye']
            
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
        
        Args:
            left_eye_pos: [x, y] en píxeles del ojo izquierdo
            right_eye_pos: [x, y] en píxeles del ojo derecho
            
        Returns:
            Tupla con posiciones en grados (left_eye_degrees, right_eye_degrees)
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
        
        Returns:
            Diccionario con información de calibración
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
            'left_led': {'left_eye': None, 'right_eye': None},
            'right_led': {'left_eye': None, 'right_eye': None}
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