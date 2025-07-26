# src/managers/hardware_manager.py

from PySide6.QtCore import QObject, Signal
from typing import Optional, Dict, Any

from libs.hardware.serial_handler import SerialHandler
from libs.hardware.serial_thread import SerialReadThread
from libs.core.calibration_manager import CalibrationManager


class HardwareManager(QObject):
    """
    Gestiona todo el sistema de hardware: comunicación serial, IMU y calibración.
    Encapsula la lógica de hardware para desacoplarla de MainWindow.
    """
    
    # Señales para comunicarse con MainWindow
    imu_data_received = Signal(dict)        # Datos del IMU procesados
    calibration_progress = Signal(str)      # Progreso de calibración
    calibration_completed = Signal(bool)    # Calibración completada
    hardware_status_changed = Signal(str)   # Estado del hardware
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Componentes de hardware
        self.serial_handler = None
        self.serial_thread = None
        self.calibration_manager = None
        
        # Estado del hardware
        self.is_connected = False
        self.is_calibrating = False
        self.connection_status = "disconnected"
        
        # Configuración por defecto
        self.default_port = '/dev/ttyUSB0'
        self.default_baudrate = 115200
        
        # Buffer para datos IMU
        self.last_imu_data = {
            'timestamp': 0,
            'yaw': 0.0,
            'pitch': 0.0,
            'roll': 0.0,
            'is_valid': False
        }
        
        print("HardwareManager inicializado")
    
    def initialize_hardware(self, port: str = None, baudrate: int = None) -> bool:
        """
        Inicializa todo el sistema de hardware.
        
        Args:
            port: Puerto serial (usa default si None)
            baudrate: Velocidad de comunicación (usa default si None)
        
        Returns:
            bool: True si la inicialización fue exitosa
        """
        port = port or self.default_port
        baudrate = baudrate or self.default_baudrate
        
        try:
            success = self._init_serial_communication(port, baudrate)
            if success:
                self._init_calibration_system()
                print("Sistema de hardware inicializado exitosamente")
                return True
            else:
                print("Error inicializando comunicación serial")
                return False
                
        except Exception as e:
            print(f"Error inicializando hardware: {e}")
            self.hardware_status_changed.emit(f"Error: {e}")
            return False
    
    def _init_serial_communication(self, port: str, baudrate: int) -> bool:
        """Inicializa la comunicación serial"""
        try:
            # Crear handler serial
            self.serial_handler = SerialHandler(port, baudrate)
            
            # Crear y configurar thread de lectura
            self.serial_thread = SerialReadThread(self.serial_handler)
            self.serial_thread.data_received.connect(self._handle_serial_data)
            
            # Iniciar thread
            self.serial_thread.start()
            
            # Actualizar estado
            self.is_connected = True
            self.connection_status = "connected"
            self.hardware_status_changed.emit("Conectado")
            
            print(f"Comunicación serial establecida: {port}@{baudrate}")
            return True
            
        except Exception as e:
            print(f"Error inicializando comunicación serial: {e}")
            self.serial_handler = None
            self.serial_thread = None
            self.is_connected = False
            self.connection_status = "error"
            self.hardware_status_changed.emit(f"Error de conexión: {e}")
            return False
    
    def _init_calibration_system(self):
        """Inicializa el sistema de calibración"""
        try:
            self.calibration_manager = CalibrationManager(self.serial_handler)
            
            # Conectar señales de calibración
            self.calibration_manager.calibration_progress.connect(self.calibration_progress.emit)
            self.calibration_manager.calibration_completed.connect(self.calibration_completed.emit)
            
            print("Sistema de calibración inicializado")
            
        except Exception as e:
            print(f"Error inicializando calibración: {e}")
            self.calibration_manager = None
    
    # === MANEJO DE DATOS SERIALES ===
    
    def _handle_serial_data(self, raw_data: str):
        """
        Procesa datos seriales recibidos del IMU.
        
        Args:
            raw_data: Datos crudos del puerto serial
        """
        try:
            # Procesar datos según formato esperado
            imu_data = self._parse_imu_data(raw_data)
            
            if imu_data['is_valid']:
                # Actualizar buffer local
                self.last_imu_data = imu_data
                
                # Emitir señal con datos procesados
                self.imu_data_received.emit(imu_data)
            
        except Exception as e:
            print(f"Error procesando datos seriales: {e}")
    
    def _parse_imu_data(self, raw_data: str) -> Dict[str, Any]:
        """
        Parsea datos crudos del IMU.
        
        Formato esperado: "yaw,pitch,roll" o datos más complejos
        
        Args:
            raw_data: String crudo del serial
            
        Returns:
            Dict con datos parseados
        """
        try:
            # Limpiar datos
            data = raw_data.strip()
            
            if not data:
                return {'is_valid': False}
            
            # Parsear formato básico: yaw,pitch,roll
            if ',' in data:
                parts = data.split(',')
                
                if len(parts) >= 3:
                    try:
                        yaw = float(parts[0])
                        pitch = float(parts[1])
                        roll = float(parts[2])
                        
                        return {
                            'timestamp': self._get_current_timestamp(),
                            'yaw': yaw,
                            'pitch': pitch,
                            'roll': roll,
                            'is_valid': True,
                            'raw_data': raw_data
                        }
                    except ValueError:
                        pass
            
            # Si no puede parsear, marcar como inválido pero conservar datos
            return {
                'timestamp': self._get_current_timestamp(),
                'raw_data': raw_data,
                'is_valid': False
            }
            
        except Exception as e:
            print(f"Error parseando datos IMU: {e}")
            return {'is_valid': False, 'error': str(e)}
    
    def _get_current_timestamp(self) -> float:
        """Obtiene timestamp actual en milisegundos"""
        import time
        return time.time() * 1000
    
    # === CONTROL DE HARDWARE ===
    
    def send_command(self, command: str) -> bool:
        """
        Envía un comando al hardware.
        
        Args:
            command: Comando a enviar
            
        Returns:
            bool: True si se envió exitosamente
        """
        if not self.is_connected or not self.serial_handler:
            print("Error: Hardware no conectado")
            return False
        
        try:
            self.serial_handler.send_data(command)
            print(f"Comando enviado: {command}")
            return True
            
        except Exception as e:
            print(f"Error enviando comando: {e}")
            return False
    
    def pause_imu(self) -> bool:
        """Pausa la lectura del IMU"""
        return self.send_command("PAUSE")
    
    def set_euler_mode(self) -> bool:
        """Establece modo Euler en el IMU"""
        return self.send_command("MODE_EULER")
    
    def set_vhit_mode(self) -> bool:
        """Establece modo VHIT en el IMU"""
        return self.send_command("MODE_VHIT")
    
    def zero_position(self) -> bool:
        """Establece posición cero del IMU"""
        return self.send_command("ZERO")
    
    # === CONTROL DE LEDs ===
    
    def turn_on_left_led(self) -> bool:
        """Enciende LED izquierdo"""
        return self.send_command("L_12_ON")
    
    def turn_off_left_led(self) -> bool:
        """Apaga LED izquierdo"""
        return self.send_command("L_12_OFF")
    
    def turn_on_right_led(self) -> bool:
        """Enciende LED derecho"""
        return self.send_command("L_14_ON")
    
    def turn_off_right_led(self) -> bool:
        """Apaga LED derecho"""
        return self.send_command("L_14_OFF")
    
    def turn_off_all_leds(self) -> bool:
        """Apaga todos los LEDs"""
        success1 = self.turn_off_left_led()
        success2 = self.turn_off_right_led()
        return success1 and success2
    
    # === SISTEMA DE CALIBRACIÓN ===
    
    def start_calibration(self) -> bool:
        """
        Inicia el proceso de calibración ocular.
        
        Returns:
            bool: True si se inició exitosamente
        """
        if not self.calibration_manager:
            print("Error: Sistema de calibración no disponible")
            return False
        
        if self.is_calibrating:
            print("Advertencia: Calibración ya en progreso")
            return False
        
        self.is_calibrating = True
        success = self.calibration_manager.start_calibration()
        
        if not success:
            self.is_calibrating = False
        
        return success
    
    def finish_calibration(self) -> bool:
        """Finaliza el proceso de calibración"""
        self.is_calibrating = False
        return True
    
    def is_calibrated(self) -> bool:
        """Verifica si el sistema está calibrado"""
        if self.calibration_manager:
            return self.calibration_manager.is_calibrated
        return False
    
    def get_calibration_data(self) -> Optional[Dict]:
        """Obtiene datos de calibración"""
        if self.calibration_manager:
            return self.calibration_manager.calibration_data
        return None
    
    # === INFORMACIÓN DE ESTADO ===
    
    def get_connection_status(self) -> str:
        """Obtiene estado de conexión"""
        return self.connection_status
    
    def get_last_imu_data(self) -> Dict[str, Any]:
        """Obtiene últimos datos del IMU"""
        return self.last_imu_data.copy()
    
    def get_hardware_info(self) -> Dict[str, Any]:
        """Obtiene información completa del hardware"""
        return {
            'is_connected': self.is_connected,
            'connection_status': self.connection_status,
            'is_calibrating': self.is_calibrating,
            'is_calibrated': self.is_calibrated(),
            'port': getattr(self.serial_handler, 'serial_port', {}).get('port', 'N/A') if self.serial_handler else 'N/A',
            'baudrate': getattr(self.serial_handler, 'serial_port', {}).get('baudrate', 'N/A') if self.serial_handler else 'N/A',
            'last_data_timestamp': self.last_imu_data.get('timestamp', 0)
        }
    
    # === CONFIGURACIÓN ===
    
    def set_default_port(self, port: str):
        """Establece puerto por defecto"""
        self.default_port = port
        print(f"Puerto por defecto establecido: {port}")
    
    def set_default_baudrate(self, baudrate: int):
        """Establece baudrate por defecto"""
        self.default_baudrate = baudrate
        print(f"Baudrate por defecto establecido: {baudrate}")
    
    # === CLEANUP ===
    
    def cleanup(self):
        """Limpia recursos del sistema de hardware"""
        try:
            # Apagar LEDs
            self.turn_off_all_leds()
            
            # Detener thread serial
            if self.serial_thread and self.serial_thread.isRunning():
                self.serial_thread.stop()
                self.serial_thread.wait(3000)  # Esperar hasta 3 segundos
            
            # Cerrar conexión serial
            if self.serial_handler and hasattr(self.serial_handler, 'serial_port'):
                self.serial_handler.serial_port.close()
            
            # Resetear estado
            self.is_connected = False
            self.is_calibrating = False
            self.connection_status = "disconnected"
            
            print("HardwareManager limpiado")
            
        except Exception as e:
            print(f"Error durante cleanup de hardware: {e}")