import cv2
import platform
import subprocess
import re
import os
import sys
import json
import glob
import serial
import serial.tools.list_ports
import time
from typing import List, Dict, Optional, Any, Tuple

# Importaciones condicionales para Windows
try:
    import win32com.client
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False


class SIEVHardwareConfig:
    """Manejo de configuración de hardware SIEV desde JSON."""
    
    def __init__(self, config_file: str = "hardware_config.json"):
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Cargar configuración desde archivo JSON."""
        default_config = {
            "siev_hardware": {
                "hub": {
                    "vendor_id": "1a40",
                    "product_id": "0101",
                    "name": "Terminus Technology Inc. Hub"
                },
                "ch340": {
                    "vendor_id": "1a86",
                    "product_id": "7523",
                    "baudrate": 115200,
                    "timeout": 2,
                    "names": ["CH340", "USB-SERIAL CH340", "USB2.0-Serial"]
                },
                "esp8266": {
                    "baudrate": 115200,
                    "timeout": 2,
                    "ping_command": "PING",
                    "expected_response": "SIEV_ESP_OK_",
                    "version_command": "VERSION",
                    "status_command": "STATUS"
                },
                "cameras": [
                    {
                        "vendor_id": "0bda",
                        "product_id": "2076",
                        "name": "Realtek Camera"
                    },
                    {
                        "vendor_id": "0edc",
                        "product_id": "2076", 
                        "name": "Alternative Camera"
                    }
                ]
            }
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                self.save_config(default_config)
                return default_config
        except Exception as e:
            print(f"Error cargando configuración: {e}")
            return default_config
    
    def save_config(self, config: Dict[str, Any] = None):
        """Guardar configuración en archivo JSON."""
        if config is None:
            config = self.config
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando configuración: {e}")


class USBDeviceDetector:
    """Detector de dispositivos USB multiplataforma."""
    
    @staticmethod
    def get_usb_devices() -> List[Dict[str, Any]]:
        """Obtener todos los dispositivos USB del sistema."""
        system = platform.system().lower()
        
        if system == 'linux':
            return USBDeviceDetector._get_linux_usb_devices()
        elif system == 'windows':
            return USBDeviceDetector._get_windows_usb_devices()
        elif system == 'darwin':
            return USBDeviceDetector._get_macos_usb_devices()
        
        return []
    
    @staticmethod
    def _get_linux_usb_devices() -> List[Dict[str, Any]]:
        """Obtener dispositivos USB en Linux."""
        devices = []
        try:
            result = subprocess.run(['lsusb'], stdout=subprocess.PIPE, text=True, timeout=5)
            for line in result.stdout.split('\n'):
                if line.strip():
                    # Bus 001 Device 016: ID 1a40:0101 Terminus Technology Inc. Hub
                    match = re.match(r'Bus (\d+) Device (\d+): ID ([0-9a-f]{4}):([0-9a-f]{4}) (.+)', line)
                    if match:
                        bus, device, vendor_id, product_id, name = match.groups()
                        devices.append({
                            'bus': int(bus),
                            'device': int(device),
                            'vendor_id': vendor_id,
                            'product_id': product_id,
                            'name': name,
                            'platform': 'linux'
                        })
        except Exception as e:
            print(f"Error obteniendo dispositivos USB Linux: {e}")
        
        return devices
    
    @staticmethod
    def _get_windows_usb_devices() -> List[Dict[str, Any]]:
        """Obtener dispositivos USB en Windows."""
        devices = []
        try:
            result = subprocess.run(
                ['wmic', 'path', 'Win32_USBHub', 'get', 'DeviceID,Name', '/format:csv'],
                stdout=subprocess.PIPE, text=True, timeout=10
            )
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            
            for line in lines:
                if line.strip():
                    parts = line.split(',')
                    if len(parts) >= 3:
                        device_id = parts[1].strip()
                        name = parts[2].strip()
                        
                        # Extraer vendor_id y product_id del DeviceID
                        vid_match = re.search(r'VID_([0-9A-F]{4})', device_id, re.IGNORECASE)
                        pid_match = re.search(r'PID_([0-9A-F]{4})', device_id, re.IGNORECASE)
                        
                        if vid_match and pid_match:
                            devices.append({
                                'device_id': device_id,
                                'vendor_id': vid_match.group(1).lower(),
                                'product_id': pid_match.group(1).lower(),
                                'name': name,
                                'platform': 'windows'
                            })
        except Exception as e:
            print(f"Error obteniendo dispositivos USB Windows: {e}")
        
        return devices
    
    @staticmethod
    def _get_macos_usb_devices() -> List[Dict[str, Any]]:
        """Obtener dispositivos USB en macOS."""
        devices = []
        try:
            result = subprocess.run(
                ['system_profiler', 'SPUSBDataType', '-json'],
                stdout=subprocess.PIPE, text=True, timeout=10
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                USBDeviceDetector._parse_macos_usb_tree(data.get('SPUSBDataType', []), devices)
                
        except Exception as e:
            print(f"Error obteniendo dispositivos USB macOS: {e}")
        
        return devices
    
    @staticmethod
    def _parse_macos_usb_tree(usb_data: List[Dict], devices: List[Dict]):
        """Parsear árbol USB de macOS recursivamente."""
        for item in usb_data:
            if '_name' in item:
                vendor_id = item.get('vendor_id', '').replace('0x', '').lower()
                product_id = item.get('product_id', '').replace('0x', '').lower()
                
                devices.append({
                    'name': item['_name'],
                    'vendor_id': vendor_id,
                    'product_id': product_id,
                    'platform': 'macos'
                })
            
            # Procesar dispositivos anidados
            if '_items' in item:
                USBDeviceDetector._parse_macos_usb_tree(item['_items'], devices)


class SerialPortDetector:
    """Detector de puertos serie y comunicación con ESP8266."""
    
    @staticmethod
    def get_platform_serial_ports() -> List[str]:
        """Obtener puertos serie específicos por plataforma."""
        system = platform.system().lower()
        ports = []
        
        try:
            if system == 'linux':
                ports.extend(glob.glob('/dev/ttyUSB*'))
                ports.extend(glob.glob('/dev/ttyACM*'))
            elif system == 'windows':
                result = subprocess.run(
                    ['wmic', 'path', 'Win32_SerialPort', 'get', 'DeviceID', '/format:csv'],
                    stdout=subprocess.PIPE, text=True, timeout=5
                )
                for line in result.stdout.split('\n'):
                    if 'COM' in line:
                        com_match = re.search(r'(COM\d+)', line)
                        if com_match:
                            ports.append(com_match.group(1))
            elif system == 'darwin':
                ports.extend(glob.glob('/dev/tty.usbserial*'))
                ports.extend(glob.glob('/dev/cu.usbserial*'))
        except Exception as e:
            print(f"Error obteniendo puertos específicos de plataforma: {e}")
        
        return sorted(list(set(ports)))
    
    @staticmethod
    def test_esp8266_communication(port: str, baudrate: int = 115200, timeout: int = 2) -> bool:
        """Probar comunicación con ESP8266 en puerto específico."""
        try:
            print(f"  🔗 Probando comunicación en {port}...")
            
            with serial.Serial(port, baudrate, timeout=timeout) as ser:
                time.sleep(0.1)  # Pausa para estabilizar
                
                # Limpiar buffers
                ser.reset_input_buffer()
                ser.reset_output_buffer()
                
                # Enviar comando PING
                ser.write(b'PING\r\n')
                ser.flush()
                
                # Esperar respuesta
                time.sleep(0.3)
                if ser.in_waiting > 0:
                    response = ser.readline().decode('utf-8', errors='ignore').strip()
                    
                    if 'SIEV_ESP_OK_' in response:
                        print(f"  ✅ ESP8266 encontrado: {response}")
                        return True
                    else:
                        print(f"  ⚠️ Respuesta inesperada: {response}")
                else:
                    print(f"  ❌ Sin respuesta en {port}")
                        
        except serial.SerialException as e:
            print(f"  ❌ Error serie en {port}: {e}")
        except Exception as e:
            print(f"  ❌ Error comunicación en {port}: {e}")
        
        return False
    
    @staticmethod
    def find_esp8266_port() -> Optional[str]:
        """Encontrar puerto del ESP8266 usando comunicación directa."""
        print("🔍 Buscando ESP8266 en puertos serie...")
        
        # Obtener puertos por patrones de plataforma
        platform_ports = SerialPortDetector.get_platform_serial_ports()
        print(f"📡 Puertos encontrados: {platform_ports}")
        
        # Probar comunicación en cada puerto
        for port in platform_ports:
            if SerialPortDetector.test_esp8266_communication(port):
                return port
        
        # Fallback: usar pyserial para obtener más puertos
        print("🔄 Fallback: buscando con pyserial...")
        try:
            all_ports = [port.device for port in serial.tools.list_ports.comports()]
            for port in all_ports:
                if port not in platform_ports:  # Solo probar puertos no probados antes
                    if SerialPortDetector.test_esp8266_communication(port):
                        return port
        except Exception as e:
            print(f"Error en fallback pyserial: {e}")
        
        print("❌ No se encontró ESP8266 funcional")
        return None
    
    @staticmethod
    def get_esp8266_info(port: str) -> Dict[str, str]:
        """Obtener información del ESP8266."""
        info = {}
        try:
            with serial.Serial(port, 115200, timeout=2) as ser:
                time.sleep(0.1)
                ser.reset_input_buffer()
                ser.reset_output_buffer()
                
                # Comando VERSION
                ser.write(b'VERSION\r\n')
                ser.flush()
                time.sleep(0.3)
                if ser.in_waiting > 0:
                    response = ser.readline().decode('utf-8', errors='ignore').strip()
                    info['version'] = response
                
                # Comando STATUS
                ser.write(b'STATUS\r\n')
                ser.flush()
                time.sleep(0.3)
                if ser.in_waiting > 0:
                    response = ser.readline().decode('utf-8', errors='ignore').strip()
                    info['status'] = response
                
        except Exception as e:
            print(f"Error obteniendo info ESP8266: {e}")
        
        return info


class CameraDetector:
    """Detector de cámaras multiplataforma."""
    
    @staticmethod
    def get_system_cameras() -> List[Dict[str, Any]]:
        """Obtener cámaras del sistema."""
        system = platform.system().lower()
        
        if system == 'linux':
            return CameraDetector._get_linux_cameras()
        elif system == 'windows':
            return CameraDetector._get_windows_cameras()
        elif system == 'darwin':
            return CameraDetector._get_macos_cameras()
        
        return []
    
    @staticmethod
    def _get_linux_cameras() -> List[Dict[str, Any]]:
        """Detecta cámaras en Linux usando v4l2-ctl."""
        cameras = []
        try:
            result = subprocess.run(['v4l2-ctl', '--list-devices'], 
                                  stdout=subprocess.PIPE, text=True, timeout=5)
            if result.returncode != 0:
                return cameras
                
            devices = result.stdout.split('\n\n')
            
            for device in devices:
                if device.strip():
                    lines = device.split('\n')
                    if len(lines) >= 2:
                        camera_name = lines[0].strip()
                        device_path = lines[1].strip()
                        
                        # Extraer índice de /dev/videoX
                        video_match = re.search(r'/dev/video(\d+)', device_path)
                        opencv_index = int(video_match.group(1)) if video_match else None
                        
                        cameras.append({
                            'name': camera_name,
                            'device_path': device_path,
                            'opencv_index': opencv_index,
                            'platform': 'linux'
                        })
        except Exception as e:
            print(f"Error detectando cámaras Linux: {e}")
        
        return cameras
    
    @staticmethod
    def _get_windows_cameras() -> List[Dict[str, Any]]:
        """Detecta cámaras en Windows."""
        cameras = []
        if not WIN32_AVAILABLE:
            return cameras
            
        try:
            system_device_enum = win32com.client.Dispatch("SystemDeviceEnum")
            moniker_enum = system_device_enum.CreateClassEnumerator(
                "{860BB310-5D01-11D0-BD3B-00A0C911CE86}", 0)
            
            if moniker_enum:
                moniker_enum.Reset()
                index = 0
                while True:
                    moniker = moniker_enum.Next(1)
                    if not moniker:
                        break
                    
                    name = moniker[0].GetDisplayName()
                    friendly_name = name.split('@')[-1] if '@' in name else name
                    
                    cameras.append({
                        'name': friendly_name,
                        'opencv_index': index,
                        'platform': 'windows'
                    })
                    index += 1
        except Exception as e:
            print(f"Error detectando cámaras Windows: {e}")
        
        return cameras
    
    @staticmethod
    def _get_macos_cameras() -> List[Dict[str, Any]]:
        """Detecta cámaras en macOS."""
        cameras = []
        try:
            cmd = ['system_profiler', 'SPCameraDataType', '-json']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                
                if 'SPCameraDataType' in data:
                    for index, device in enumerate(data['SPCameraDataType']):
                        name = device.get('_name', '')
                        cameras.append({
                            'name': name,
                            'opencv_index': index,
                            'platform': 'macos'
                        })
        except Exception as e:
            print(f"Error detectando cámaras macOS: {e}")
        
        return cameras
    
    @staticmethod
    def test_opencv_camera(index: int) -> bool:
        """Probar si cámara funciona con OpenCV."""
        try:
            cap = cv2.VideoCapture(index)
            if cap.isOpened():
                ret, frame = cap.read()
                cap.release()
                return ret and frame is not None
        except Exception:
            pass
        return False
    
    @staticmethod
    def map_opencv_indices(cameras: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Mapear y verificar índices OpenCV."""
        for camera in cameras:
            opencv_index = camera.get('opencv_index')
            if opencv_index is not None:
                if CameraDetector.test_opencv_camera(opencv_index):
                    camera['opencv_working'] = True
                else:
                    camera['opencv_working'] = False
                    camera['opencv_index'] = None
        
        # Detectar cámaras adicionales solo OpenCV
        detected_indices = {cam.get('opencv_index') for cam in cameras if cam.get('opencv_index') is not None}
        
        for i in range(10):  # Probar índices 0-9
            if i not in detected_indices:
                if CameraDetector.test_opencv_camera(i):
                    cameras.append({
                        'name': f'OpenCV Camera {i}',
                        'opencv_index': i,
                        'opencv_working': True,
                        'platform': 'opencv_only'
                    })
        
        return cameras


class SievFinder:
    """Buscador del hardware completo SIEV."""
    
    def __init__(self, config_file: str = "hardware_config.json"):
        self.config = SIEVHardwareConfig(config_file)
        self.usb_detector = USBDeviceDetector()
        self.serial_detector = SerialPortDetector()
        self.camera_detector = CameraDetector()
    
    def find_siev_setup(self) -> Optional[Dict[str, Any]]:
        """Buscar setup completo SIEV."""
        print("🔍 Buscando setup completo SIEV...")
        
        # 1. Buscar Hub USB
        hub_config = self.config.config["siev_hardware"]["hub"]
        hub_found = self._find_hub(hub_config)
        if not hub_found:
            return None
        
        # 2. Buscar ESP8266
        esp_port = self.serial_detector.find_esp8266_port()
        if not esp_port:
            print("❌ ESP8266 no encontrado")
            return None
        
        print(f"✅ ESP8266 encontrado en: {esp_port}")
        esp_info = self.serial_detector.get_esp8266_info(esp_port)
        
        # 3. Buscar cámara SIEV
        camera_found = self._find_siev_camera()
        if not camera_found:
            print("❌ Cámara SIEV no encontrada")
            return None
        
        print(f"✅ Cámara encontrada: {camera_found['name']} (OpenCV: {camera_found.get('opencv_index')})")
        
        # Setup completo
        return {
            'hub': hub_found,
            'esp8266': {
                'port': esp_port,
                'info': esp_info
            },
            'camera': camera_found,
            'setup_complete': True
        }
    
    def _find_hub(self, hub_config: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Buscar hub USB específico."""
        usb_devices = self.usb_detector.get_usb_devices()
        
        for device in usb_devices:
            if (device.get('vendor_id') == hub_config['vendor_id'] and 
                device.get('product_id') == hub_config['product_id']):
                print(f"✅ Hub encontrado: {device['name']}")
                return device
        
        print(f"❌ Hub {hub_config['name']} no encontrado")
        return None
    
    def _find_siev_camera(self) -> Optional[Dict[str, Any]]:
        """Buscar cámara SIEV específica."""
        cameras_config = self.config.config["siev_hardware"]["cameras"]
        all_cameras = self.camera_detector.get_system_cameras()
        mapped_cameras = self.camera_detector.map_opencv_indices(all_cameras)
        
        # Buscar por nombre coincidente
        for camera_cfg in cameras_config:
            target_name = camera_cfg['name'].lower()
            
            for camera in mapped_cameras:
                camera_name = camera.get('name', '').lower()
                if any(word in camera_name for word in ['usb', 'camera']) and camera.get('opencv_working'):
                    camera['matched_config'] = camera_cfg
                    return camera
        
        return None
    
    def get_siev_camera_index(self) -> Optional[int]:
        """Obtener índice OpenCV de cámara SIEV."""
        setup = self.find_siev_setup()
        if setup and setup.get('camera'):
            return setup['camera'].get('opencv_index')
        return None
    
    def get_siev_serial_port(self) -> Optional[str]:
        """Obtener puerto serie ESP8266."""
        setup = self.find_siev_setup()
        if setup and setup.get('esp8266'):
            return setup['esp8266'].get('port')
        return None
    
    def verify_siev_setup(self) -> bool:
        """Verificar setup completo."""
        setup = self.find_siev_setup()
        return setup is not None and setup.get('setup_complete', False)


# Funciones de conveniencia
def find_siev_camera() -> Optional[int]:
    """Función rápida para encontrar cámara SIEV."""
    finder = SievFinder()
    return finder.get_siev_camera_index()

def find_siev_serial() -> Optional[str]:
    """Función rápida para encontrar puerto serie SIEV."""
    finder = SievFinder()
    return finder.get_siev_serial_port()

def verify_siev_hardware() -> bool:
    """Función rápida para verificar hardware SIEV completo."""
    finder = SievFinder()
    return finder.verify_siev_setup()


# Ejemplo de uso y testing
if __name__ == "__main__":
    print("=== SISTEMA DE DETECCIÓN SIEV ROBUSTO ===\n")
    
    finder = SievFinder()
    
    print("1. Verificando hardware SIEV completo...")
    siev_setup = finder.find_siev_setup()
    
    if siev_setup:
        print("\n🎯 ¡SETUP SIEV ENCONTRADO!")
        print(f"Hub: {siev_setup['hub']['name']}")
        print(f"ESP8266 Puerto: {siev_setup['esp8266']['port']}")
        
        esp_info = siev_setup['esp8266'].get('info', {})
        if esp_info:
            print(f"ESP8266 Versión: {esp_info.get('version', 'N/A')}")
            print(f"ESP8266 Status: {esp_info.get('status', 'N/A')}")
        
        print(f"Cámara: {siev_setup['camera']['name']} (OpenCV: {siev_setup['camera'].get('opencv_index')})")
        
        # Probar conexión OpenCV
        camera_index = siev_setup['camera'].get('opencv_index')
        if camera_index is not None:
            cap = cv2.VideoCapture(camera_index)
            if cap.isOpened():
                print(f"✅ Conexión OpenCV exitosa en índice {camera_index}")
                cap.release()
            else:
                print(f"❌ Error conectando OpenCV en índice {camera_index}")
        
        # Probar comunicación ESP8266
        try:
            ser = serial.Serial(siev_setup['esp8266']['port'], 115200, timeout=1)
            ser.write(b'PING\r\n')
            ser.flush()
            time.sleep(0.2)
            
            if ser.in_waiting > 0:
                response = ser.readline().decode('utf-8', errors='ignore').strip()
                print(f"✅ Comunicación ESP8266: {response}")
            else:
                print("⚠️ ESP8266 no responde")
                
            ser.close()
        except Exception as e:
            print(f"❌ Error comunicación ESP8266: {e}")
    
    else:
        print("❌ Setup SIEV no encontrado")
        
        # Mostrar diagnósticos
        print("\n📋 Diagnóstico:")
        
        # USB devices
        usb_devices = USBDeviceDetector().get_usb_devices()
        print("\nDispositivos USB:")
        for device in usb_devices[:10]:
            print(f"  {device.get('vendor_id', 'N/A')}:{device.get('product_id', 'N/A')} - {device.get('name', 'N/A')}")
        
        # Serial ports
        serial_ports = SerialPortDetector.get_platform_serial_ports()
        print(f"\nPuertos Serie: {serial_ports}")
        
        # Cameras
        cameras = CameraDetector.get_system_cameras()
        mapped_cameras = CameraDetector.map_opencv_indices(cameras)
        print("\nCámaras:")
        for cam in mapped_cameras:
            print(f"  Índice {cam.get('opencv_index', 'N/A')}: {cam.get('name', 'N/A')}")
    
    print("\n=== FUNCIONES RÁPIDAS ===")
    print(f"find_siev_camera(): {find_siev_camera()}")
    print(f"find_siev_serial(): {find_siev_serial()}")
    print(f"verify_siev_hardware(): {verify_siev_hardware()}")