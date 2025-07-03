#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SievController - Interfaz de alto nivel para comandos ESP8266 SIEV
"""

import time
from typing import Optional, Dict, Any, List
from PySide6.QtCore import QObject, Signal
from .serial_connection import SerialConnection


class SievController(QObject):
    """
    Controlador de alto nivel para ESP8266 SIEV.
    Proporciona métodos convenientes y parsing de respuestas.
    """
    
    # Señales de alto nivel
    device_connected = Signal()
    device_disconnected = Signal()
    led_state_changed = Signal(str, bool)  # (side, state)
    imu_data_updated = Signal(dict)        # datos IMU procesados
    calibration_updated = Signal(dict)     # estado de calibración
    controller_error = Signal(str)         # errores del controlador
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Conexión serial subyacente
        self.serial_conn = SerialConnection(self)
        
        # Estado del dispositivo
        self.device_info = {}
        self.led_states = {'LEFT': False, 'RIGHT': False}
        self.imu_calibration = {}
        self.last_imu_data = {}
        
        # Configuración
        self.default_timeout = 3.0
        
        # Conectar señales de SerialConnection
        self._connect_serial_signals()
        
        print("🎮 SievController inicializado")
    
    def _connect_serial_signals(self):
        """Conectar señales de SerialConnection."""
        self.serial_conn.connected.connect(self._on_serial_connected)
        self.serial_conn.disconnected.connect(self._on_serial_disconnected)
        self.serial_conn.command_response.connect(self._on_command_response)
        self.serial_conn.imu_data_received.connect(self._on_imu_data_received)
        self.serial_conn.error_occurred.connect(self._on_serial_error)
    
    # ===== MÉTODOS DE CONEXIÓN =====
    
    def connect(self, port: str) -> bool:
        """
        Conectar al dispositivo SIEV.
        
        Args:
            port: Puerto serial del ESP8266
            
        Returns:
            bool: True si la conexión fue exitosa
        """
        print(f"🎮 Conectando SievController a {port}")
        success = self.serial_conn.connect(port)
        
        if success:
            # Obtener información inicial del dispositivo
            self._initialize_device_info()
        
        return success
    
    def disconnect(self):
        """Desconectar del dispositivo SIEV."""
        print("🎮 Desconectando SievController")
        self.serial_conn.disconnect()
    
    def is_connected(self) -> bool:
        """Verificar si está conectado."""
        return self.serial_conn.is_connected()
    
    # ===== COMANDOS BÁSICOS =====
    
    def ping(self) -> Dict[str, Any]:
        """
        Test de conectividad básico.
        
        Returns:
            dict: Resultado del ping
        """
        response = self.serial_conn.send_command_sync("PING", self.default_timeout)
        
        if response and "SIEV_ESP_OK" in response:
            version = response.replace("SIEV_ESP_OK_v", "").strip()
            return {
                'success': True,
                'version': version,
                'response': response
            }
        else:
            return {
                'success': False,
                'error': 'No response or invalid response',
                'response': response
            }
    
    def get_status(self) -> Dict[str, Any]:
        """
        Obtener estado del sistema.
        
        Returns:
            dict: Estado parseado del sistema
        """
        response = self.serial_conn.send_command_sync("STATUS", self.default_timeout)
        
        if not response:
            return {'success': False, 'error': 'No response'}
        
        try:
            # Parsear: STATUS:OK,UPTIME:12345,FREE_HEAP:45678,CHIP_ID:ABC123
            if response.startswith("STATUS:"):
                parts = response[7:].split(',')  # Remover "STATUS:"
                
                status_data = {}
                for part in parts:
                    if ':' in part:
                        key, value = part.split(':', 1)
                        
                        # Convertir valores numéricos
                        if key in ['UPTIME', 'FREE_HEAP', 'FLASH']:
                            try:
                                status_data[key.lower()] = int(value)
                            except ValueError:
                                status_data[key.lower()] = value
                        else:
                            status_data[key.lower()] = value
                
                return {
                    'success': True,
                    'status': status_data.get('status', 'unknown'),
                    'uptime': status_data.get('uptime', 0),
                    'free_heap': status_data.get('free_heap', 0),
                    'chip_id': status_data.get('chip_id', 'unknown'),
                    'raw_response': response
                }
            else:
                return {'success': False, 'error': 'Invalid status format', 'response': response}
                
        except Exception as e:
            return {'success': False, 'error': f'Parse error: {e}', 'response': response}
    
    def get_version(self) -> Dict[str, Any]:
        """
        Obtener información de versión del firmware.
        
        Returns:
            dict: Información de versión parseada
        """
        response = self.serial_conn.send_command_sync("VERSION", self.default_timeout)
        
        if not response:
            return {'success': False, 'error': 'No response'}
        
        try:
            # Parsear: VERSION:SIEV_ESP8266,FW:1.0.0,SDK:3.0.2,CORE:2.7.4,FLASH:4194304
            if response.startswith("VERSION:"):
                parts = response[8:].split(',')  # Remover "VERSION:"
                
                version_data = {'device': parts[0] if parts else 'unknown'}
                
                for part in parts[1:]:
                    if ':' in part:
                        key, value = part.split(':', 1)
                        version_data[key.lower()] = value
                
                return {
                    'success': True,
                    'device': version_data.get('device', 'unknown'),
                    'firmware': version_data.get('fw', 'unknown'),
                    'sdk': version_data.get('sdk', 'unknown'),
                    'core': version_data.get('core', 'unknown'),
                    'flash': version_data.get('flash', 'unknown'),
                    'raw_response': response
                }
            else:
                return {'success': False, 'error': 'Invalid version format', 'response': response}
                
        except Exception as e:
            return {'success': False, 'error': f'Parse error: {e}', 'response': response}
    
    def reset_device(self) -> Dict[str, Any]:
        """
        Reiniciar el dispositivo ESP8266.
        
        Returns:
            dict: Resultado del reset
        """
        response = self.serial_conn.send_command_sync("RESET", self.default_timeout)
        
        if response and "RESET_OK" in response:
            # El dispositivo se reiniciará, desconectar
            self.serial_conn.disconnect()
            return {'success': True, 'message': 'Device reset initiated'}
        else:
            return {'success': False, 'error': 'Reset failed', 'response': response}
    
    # ===== CONTROL DE LEDs =====
    
    def led_control(self, side: str, state: bool) -> Dict[str, Any]:
        """
        Controlar LEDs del dispositivo.
        
        Args:
            side: 'LEFT' o 'RIGHT'
            state: True para encender, False para apagar
            
        Returns:
            dict: Resultado del comando
        """
        side = side.upper()
        if side not in ['LEFT', 'RIGHT']:
            return {'success': False, 'error': f'Invalid side: {side}. Use LEFT or RIGHT'}
        
        command = f"LED_{'ON' if state else 'OFF'}:{side}"
        response = self.serial_conn.send_command_sync(command, self.default_timeout)
        
        if not response:
            return {'success': False, 'error': 'No response'}
        
        # Verificar respuesta esperada: LED:LEFT:ON o LED:RIGHT:OFF
        expected = f"LED:{side}:{'ON' if state else 'OFF'}"
        if response == expected:
            # Actualizar estado local
            self.led_states[side] = state
            self.led_state_changed.emit(side, state)
            
            return {
                'success': True,
                'side': side,
                'state': state,
                'response': response
            }
        else:
            return {'success': False, 'error': 'Unexpected response', 'response': response}
    
    def led_on(self, side: str) -> Dict[str, Any]:
        """Encender LED específico."""
        return self.led_control(side, True)
    
    def led_off(self, side: str) -> Dict[str, Any]:
        """Apagar LED específico."""
        return self.led_control(side, False)
    
    def get_led_states(self) -> Dict[str, bool]:
        """Obtener estados actuales de los LEDs."""
        return self.led_states.copy()
    
    # ===== COMANDOS IMU =====
    
    def imu_read_single(self) -> Dict[str, Any]:
        """
        Leer una muestra única del IMU.
        
        Returns:
            dict: Datos IMU parseados
        """
        response = self.serial_conn.send_command_sync("IMU_READ_ONE", self.default_timeout)
        
        if not response:
            return {'success': False, 'error': 'No response'}
        
        try:
            # Parsear: IMU:ACC:1.23,-0.45,9.81,GYRO:0.01,-0.02,0.00,MAG:25.6,-12.3,45.7,TEMP:23.5,QUAT:0.707,0.0,0.0,0.707
            if response.startswith("IMU:"):
                return self._parse_imu_single_response(response)
            else:
                return {'success': False, 'error': 'Invalid IMU response format', 'response': response}
                
        except Exception as e:
            return {'success': False, 'error': f'Parse error: {e}', 'response': response}
    
    def imu_start_live(self) -> Dict[str, Any]:
        """
        Iniciar stream continuo de datos IMU.
        
        Returns:
            dict: Resultado del comando
        """
        response = self.serial_conn.send_command_sync("IMU_READ_LIVE_ON", self.default_timeout)
        
        if response and "IMU_LIVE:STARTED" in response:
            return {
                'success': True,
                'message': 'IMU live stream started',
                'response': response
            }
        else:
            return {'success': False, 'error': 'Failed to start IMU stream', 'response': response}
    
    def imu_stop_live(self) -> Dict[str, Any]:
        """
        Detener stream continuo de datos IMU.
        
        Returns:
            dict: Resultado del comando
        """
        response = self.serial_conn.send_command_sync("IMU_READ_LIVE_OFF", self.default_timeout)
        
        if response and "IMU_LIVE:STOPPED" in response:
            return {
                'success': True,
                'message': 'IMU live stream stopped',
                'response': response
            }
        else:
            return {'success': False, 'error': 'Failed to stop IMU stream', 'response': response}
    
    def imu_get_calibration(self) -> Dict[str, Any]:
        """
        Obtener estado de calibración del IMU.
        
        Returns:
            dict: Estado de calibración parseado
        """
        response = self.serial_conn.send_command_sync("IMU_CALIBRATE", self.default_timeout)
        
        if not response:
            return {'success': False, 'error': 'No response'}
        
        try:
            # Parsear: CALIBRATE:SYS:2,GYRO:3,ACC:3,MAG:1,STATUS:PARTIAL
            if response.startswith("CALIBRATE:"):
                return self._parse_calibration_response(response)
            else:
                return {'success': False, 'error': 'Invalid calibration response', 'response': response}
                
        except Exception as e:
            return {'success': False, 'error': f'Parse error: {e}', 'response': response}
    
    def get_last_imu_data(self) -> Dict[str, Any]:
        """Obtener los últimos datos IMU recibidos."""
        return self.last_imu_data.copy()
    
    # ===== MÉTODOS DE PARSING PRIVADOS =====
    
    def _parse_imu_single_response(self, response: str) -> Dict[str, Any]:
        """Parsear respuesta de IMU_READ_ONE."""
        # IMU:ACC:1.23,-0.45,9.81,GYRO:0.01,-0.02,0.00,MAG:25.6,-12.3,45.7,TEMP:23.5,QUAT:0.707,0.0,0.0,0.707
        parts = response[4:].split(',')  # Remover "IMU:"
        
        if len(parts) < 15:
            raise ValueError(f"Insufficient data points: {len(parts)}")
        
        # Extraer secciones
        acc_data = parts[0:3]
        gyro_data = parts[3:6]
        mag_data = parts[6:9]
        temp_data = parts[9]
        quat_data = parts[10:14]
        
        # Remover prefijos (ACC:, GYRO:, etc.)
        acc_data[0] = acc_data[0].split(':')[-1]  # Remover "ACC:"
        gyro_data[0] = gyro_data[0].split(':')[-1]  # Remover "GYRO:"
        mag_data[0] = mag_data[0].split(':')[-1]  # Remover "MAG:"
        temp_data = temp_data.split(':')[-1]  # Remover "TEMP:"
        quat_data[0] = quat_data[0].split(':')[-1]  # Remover "QUAT:"
        
        return {
            'success': True,
            'timestamp': int(time.time() * 1000),  # Timestamp local
            'accelerometer': {
                'x': float(acc_data[0]),
                'y': float(acc_data[1]),
                'z': float(acc_data[2])
            },
            'gyroscope': {
                'x': float(gyro_data[0]),
                'y': float(gyro_data[1]),
                'z': float(gyro_data[2])
            },
            'magnetometer': {
                'x': float(mag_data[0]),
                'y': float(mag_data[1]),
                'z': float(mag_data[2])
            },
            'temperature': float(temp_data),
            'quaternion': {
                'w': float(quat_data[0]),
                'x': float(quat_data[1]),
                'y': float(quat_data[2]),
                'z': float(quat_data[3])
            },
            'raw_response': response
        }
    
    def _parse_calibration_response(self, response: str) -> Dict[str, Any]:
        """Parsear respuesta de IMU_CALIBRATE."""
        # CALIBRATE:SYS:2,GYRO:3,ACC:3,MAG:1,STATUS:PARTIAL
        parts = response[10:].split(',')  # Remover "CALIBRATE:"
        
        calibration_data = {}
        status_text = 'UNKNOWN'
        
        for part in parts:
            if ':' in part:
                key, value = part.split(':', 1)
                if key in ['SYS', 'GYRO', 'ACC', 'MAG']:
                    calibration_data[key.lower()] = int(value)
                elif key == 'STATUS':
                    status_text = value
        
        # Interpretar estado general
        overall_status = self._interpret_calibration_status(calibration_data)
        
        result = {
            'success': True,
            'system': calibration_data.get('sys', 0),
            'gyroscope': calibration_data.get('gyro', 0),
            'accelerometer': calibration_data.get('acc', 0),
            'magnetometer': calibration_data.get('mag', 0),
            'status_text': status_text,
            'overall_status': overall_status,
            'fully_calibrated': all(v >= 3 for v in calibration_data.values()),
            'raw_response': response
        }
        
        # Actualizar estado local
        self.imu_calibration = result
        self.calibration_updated.emit(result)
        
        return result
    
    def _interpret_calibration_status(self, cal_data: Dict[str, int]) -> str:
        """Interpretar estado general de calibración."""
        if not cal_data:
            return 'UNCALIBRATED'
        
        avg_calibration = sum(cal_data.values()) / len(cal_data)
        
        if avg_calibration >= 3.0:
            return 'FULLY_CALIBRATED'
        elif avg_calibration >= 2.0:
            return 'GOOD'
        elif avg_calibration >= 1.0:
            return 'PARTIAL'
        else:
            return 'UNCALIBRATED'
    
    # ===== MANEJADORES DE SEÑALES =====
    
    def _on_serial_connected(self):
        """Manejar conexión de SerialConnection."""
        print("🎮 SievController: Dispositivo conectado")
        self.device_connected.emit()
    
    def _on_serial_disconnected(self):
        """Manejar desconexión de SerialConnection."""
        print("🎮 SievController: Dispositivo desconectado")
        self.device_disconnected.emit()
        
        # Limpiar estados
        self.led_states = {'LEFT': False, 'RIGHT': False}
        self.device_info = {}
        self.imu_calibration = {}
        self.last_imu_data = {}
    
    def _on_command_response(self, command: str, response: str):
        """Manejar respuestas de comandos."""
        print(f"🎮 Comando '{command}' -> Respuesta: {response}")
    
    def _on_imu_data_received(self, imu_data: Dict[str, Any]):
        """Manejar datos IMU del stream."""
        self.last_imu_data = imu_data
        self.imu_data_updated.emit(imu_data)
    
    def _on_serial_error(self, error_msg: str):
        """Manejar errores de SerialConnection."""
        error_message = f"Serial error: {error_msg}"
        print(f"🎮 ❌ {error_message}")
        self.controller_error.emit(error_message)
    
    def _initialize_device_info(self):
        """Inicializar información del dispositivo al conectar."""
        # Obtener información básica
        version_info = self.get_version()
        if version_info['success']:
            self.device_info.update(version_info)
        
        status_info = self.get_status()
        if status_info['success']:
            self.device_info.update(status_info)
        
        print(f"🎮 Información del dispositivo obtenida: {self.device_info.get('device', 'unknown')}")
    
    # ===== MÉTODOS DE ESTADO =====
    
    def get_controller_status(self) -> Dict[str, Any]:
        """Obtener estado completo del controlador."""
        return {
            'connected': self.is_connected(),
            'device_info': self.device_info.copy(),
            'led_states': self.led_states.copy(),
            'imu_calibration': self.imu_calibration.copy(),
            'last_imu_data': self.last_imu_data.copy(),
            'serial_connection': self.serial_conn.get_connection_info()
        }