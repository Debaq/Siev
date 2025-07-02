import cv2
import platform
import subprocess
import re
import os
import sys
import json
import serial.tools.list_ports
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
                    "names": ["CH340", "USB-SERIAL CH340", "USB2.0-Serial"]
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
                # Crear archivo por defecto
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
    
    def get_hub_config(self) -> Dict[str, str]:
        """Obtener configuración del hub."""
        return self.config["siev_hardware"]["hub"]
    
    def get_ch340_config(self) -> Dict[str, Any]:
        """Obtener configuración del CH340."""
        return self.config["siev_hardware"]["ch340"]
    
    def get_cameras_config(self) -> List[Dict[str, str]]:
        """Obtener configuración de cámaras."""
        return self.config["siev_hardware"]["cameras"]
    
    def add_camera_config(self, vendor_id: str, product_id: str, name: str):
        """Agregar nueva configuración de cámara."""
        new_camera = {
            "vendor_id": vendor_id,
            "product_id": product_id,
            "name": name
        }
        self.config["siev_hardware"]["cameras"].append(new_camera)
        self.save_config()
    
    def update_hardware_config(self, section: str, updates: Dict[str, Any]):
        """Actualizar sección específica de hardware."""
        if section in self.config["siev_hardware"]:
            self.config["siev_hardware"][section].update(updates)
            self.save_config()


class CameraDetector:
    """Detector de cámaras multiplataforma usando la lógica de tus clases originales."""
    
    @staticmethod
    def get_windows_cameras() -> List[Dict[str, Any]]:
        """Detecta cámaras en Windows usando SystemDeviceEnum."""
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
                    # Extraer información del nombre del dispositivo
                    friendly_name = name.split('@')[-1] if '@' in name else name
                    
                    cameras.append({
                        'system_index': index,
                        'name': friendly_name,
                        'full_name': name,
                        'device_path': name,
                        'platform': 'windows'
                    })
                    index += 1
        except Exception as e:
            print(f"Error detectando cámaras Windows: {e}")
        
        return cameras
    
    @staticmethod
    def get_linux_cameras() -> List[Dict[str, Any]]:
        """Detecta cámaras en Linux usando v4l2-ctl."""
        cameras = []
        try:
            result = subprocess.run(['v4l2-ctl', '--list-devices'], 
                                  stdout=subprocess.PIPE, text=True, timeout=5)
            if result.returncode != 0:
                return cameras
                
            devices = result.stdout.split('\n\n')
            index = 0
            
            for device in devices:
                if device.strip():
                    lines = device.split('\n')
                    if len(lines) >= 2:
                        camera_name = lines[0].strip()
                        device_path = lines[1].strip()
                        
                        # Extraer vendor/product info si está disponible
                        vendor_id = product_id = None
                        usb_match = re.search(r'usb-([^-]+)-', device_path)
                        if usb_match:
                            usb_info = usb_match.group(1)
                        
                        cameras.append({
                            'system_index': index,
                            'name': camera_name,
                            'device_path': device_path,
                            'vendor_id': vendor_id,
                            'product_id': product_id,
                            'platform': 'linux'
                        })
                        index += 1
        except Exception as e:
            print(f"Error detectando cámaras Linux: {e}")
        
        return cameras
    
    @staticmethod
    def get_macos_cameras() -> List[Dict[str, Any]]:
        """Detecta cámaras en macOS usando system_profiler."""
        cameras = []
        try:
            cmd = ['system_profiler', 'SPCameraDataType', '-json']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                
                if 'SPCameraDataType' in data:
                    for index, device in enumerate(data['SPCameraDataType']):
                        name = device.get('_name', '')
                        cameras.append({
                            'system_index': index,
                            'name': name,
                            'model': device.get('spcamera_model', ''),
                            'vendor_id': device.get('spcamera_vendor-id', ''),
                            'product_id': device.get('spcamera_product-id', ''),
                            'platform': 'macos'
                        })
        except Exception as e:
            print(f"Error detectando cámaras macOS: {e}")
        
        return cameras


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
    """Detector de puertos serie multiplataforma."""
    
    @staticmethod
    def get_serial_ports() -> List[Dict[str, Any]]:
        """Obtener todos los puertos serie del sistema."""
        ports = []
        
        try:
            for port in serial.tools.list_ports.comports():
                port_info = {
                    'device': port.device,
                    'name': port.description,
                    'hwid': port.hwid,
                    'vendor_id': None,
                    'product_id': None
                }
                
                # Extraer vendor_id y product_id del hwid
                if port.hwid:
                    vid_match = re.search(r'VID[=:]([0-9A-F]{4})', port.hwid, re.IGNORECASE)
                    pid_match = re.search(r'PID[=:]([0-9A-F]{4})', port.hwid, re.IGNORECASE)
                    
                    if vid_match:
                        port_info['vendor_id'] = vid_match.group(1).lower()
                    if pid_match:
                        port_info['product_id'] = pid_match.group(1).lower()
                
                ports.append(port_info)
                
        except Exception as e:
            print(f"Error obteniendo puertos serie: {e}")
        
        return ports
    
    @staticmethod
    def get_platform_serial_ports() -> List[str]:
        """Obtener puertos serie específicos por plataforma."""
        system = platform.system().lower()
        ports = []
        
        try:
            if system == 'linux':
                # Buscar /dev/ttyUSB* y /dev/ttyACM*
                import glob
                ports.extend(glob.glob('/dev/ttyUSB*'))
                ports.extend(glob.glob('/dev/ttyACM*'))
                
            elif system == 'windows':
                # Usar wmic para obtener puertos COM
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
                # macOS: buscar /dev/tty.usbserial* y /dev/cu.usbserial*
                import glob
                ports.extend(glob.glob('/dev/tty.usbserial*'))
                ports.extend(glob.glob('/dev/cu.usbserial*'))
                
        except Exception as e:
            print(f"Error obteniendo puertos específicos de plataforma: {e}")
        
        return sorted(list(set(ports)))  # Eliminar duplicados y ordenar
    
    @staticmethod
    def test_esp8266_communication(port: str, config: Dict[str, Any]) -> bool:
        """Probar comunicación con ESP8266 en puerto específico."""
        try:
            import serial
            import time
            
            # Configuración de comunicación
            baudrate = config.get('baudrate', 115200)
            timeout = config.get('timeout', 2)
            
            # Abrir puerto serie
            with serial.Serial(port, baudrate, timeout=timeout) as ser:
                time.sleep(0.1)  # Pausa para estabilizar
                
                # Limpiar buffers
                ser.reset_input_buffer()
                ser.reset_output_buffer()
                
                # Enviar comando PING
                ping_command = config.get('commands', {}).get('ping', {}).get('command', 'PING')
                ser.write((ping_command + '\r\n').encode('utf-8'))
                ser.flush()
                
                # Esperar respuesta
                time.sleep(0.2)
                if ser.in_waiting > 0:
                    response = ser.readline().decode('utf-8', errors='ignore').strip()
                    
                    # Verificar respuesta esperada
                    expected_pattern = config.get('commands', {}).get('ping', {}).get('expected_response_pattern', 'SIEV_ESP_OK_')
                    
                    if expected_pattern in response:
                        print(f"✅ ESP8266 encontrado en {port}: {response}")
                        return True
                    else:
                        print(f"⚠️ Respuesta inesperada en {port}: {response}")
                        
        except serial.SerialException as e:
            print(f"❌ Error serie en {port}: {e}")
        except Exception as e:
            print(f"❌ Error comunicación en {port}: {e}")
        
        return False
    
    @staticmethod
    def find_ch340_port(ch340_config: Dict[str, Any]) -> Optional[str]:
        """Encontrar puerto del CH340 específico usando comunicación."""
        print("🔍 Buscando CH340 con ESP8266...")
        
        # Método 1: Buscar por patrones específicos de plataforma
        platform_ports = SerialPortDetector.get_platform_serial_ports()
        print(f"📡 Puertos encontrados por patrón: {platform_ports}")
        
        # Probar comunicación en cada puerto
        for port in platform_ports:
            print(f"🔗 Probando comunicación en {port}...")
            if SerialPortDetector.test_esp8266_communication(port, ch340_config):
                return port
        
        # Método 2: Fallback usando pyserial tradicional
        print("🔄 Fallback: usando detección pyserial...")
        serial_ports = SerialPortDetector.get_serial_ports()
        
        # Intentar por VID/PID primero
        target_vendor = ch340_config.get('vendor_id')
        target_product = ch340_config.get('product_id')
        
        for port_info in serial_ports:
            if (port_info.get('vendor_id') == target_vendor and 
                port_info.get('product_id') == target_product):
                port = port_info['device']
                print(f"🎯 VID/PID coincide, probando {port}...")
                if SerialPortDetector.test_esp8266_communication(port, ch340_config):
                    return port
        
        # Método 3: Probar por nombre/descripción
        print("🔄 Fallback: probando por nombre...")
        names = ch340_config.get('names', [])
        
        for port_info in serial_ports:
            port_name = port_info.get('name', '').lower()
            for target_name in names:
                if target_name.lower() in port_name:
                    port = port_info['device']
                    print(f"📝 Nombre coincide, probando {port}...")
                    if SerialPortDetector.test_esp8266_communication(port, ch340_config):
                        return port
        
        print("❌ No se encontró CH340 con ESP8266 funcional")
        return None
    
    @staticmethod
    def get_esp8266_info(port: str, config: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Obtener información detallada del ESP8266."""
        try:
            import serial
            import time
            
            esp_info = {}
            baudrate = config.get('baudrate', 115200)
            timeout = config.get('timeout', 2)
            
            with serial.Serial(port, baudrate, timeout=timeout) as ser:
                time.sleep(0.1)
                ser.reset_input_buffer()
                ser.reset_output_buffer()
                
                # Comando VERSION
                version_cmd = config.get('commands', {}).get('version', {}).get('command', 'VERSION')
                ser.write((version_cmd + '\r\n').encode('utf-8'))
                ser.flush()
                
                time.sleep(0.3)
                if ser.in_waiting > 0:
                    response = ser.readline().decode('utf-8', errors='ignore').strip()
                    esp_info['version_response'] = response
                
                # Comando STATUS
                status_cmd = config.get('commands', {}).get('status', {}).get('command', 'STATUS')
                ser.write((status_cmd + '\r\n').encode('utf-8'))
                ser.flush()
                
                time.sleep(0.3)
                if ser.in_waiting > 0:
                    response = ser.readline().decode('utf-8', errors='ignore').strip()
                    esp_info['status_response'] = response
                
                return esp_info
                
        except Exception as e:
            print(f"Error obteniendo info ESP8266: {e}")
            
        return None


class CameraController:
    """Controlador de cámara multiplataforma basado en tus clases originales."""
    
    def __init__(self, platform_type: str):
        self.platform = platform_type
        self.device = None
        self.device_path = None
        
        # Atributos específicos de Windows
        if platform_type == 'windows' and WIN32_AVAILABLE:
            self.capture_filter = None
            self.graph = None
            self.control = None
    
    def set_camera(self, device_path: str, width: int = 1280, height: int = 720):
        """Configura la cámara activa."""
        self.device_path = device_path
        
        if self.platform == 'linux':
            self.device = device_path
            self._set_frame_size_linux(width, height)
        elif self.platform == 'windows' and WIN32_AVAILABLE:
            self._setup_windows_camera(device_path)
    
    def _setup_windows_camera(self, device_path: str):
        """Configura cámara en Windows."""
        try:
            # Create the filter graph manager
            self.graph = win32com.client.Dispatch("FilterGraph")
            # Add the capture filter for the selected camera
            capture_filter = self._create_capture_filter(device_path)
            self.graph.AddFilter(capture_filter, "Capture Filter")
            self.capture_filter = capture_filter
            # Get the control interface
            self.control = self.graph.QueryInterface("IAMVideoProcAmp")
        except Exception as e:
            print(f"Error configurando cámara Windows: {e}")
    
    def _create_capture_filter(self, device_name: str):
        """Crea el filtro de captura para la cámara en Windows."""
        try:
            capture_filter = win32com.client.Dispatch("CaptureFilter")
            capture_filter.SetDevice(device_name)
            return capture_filter
        except Exception as e:
            print(f"Error creando filtro de captura: {e}")
            return None
    
    def _set_frame_size_linux(self, width: int, height: int):
        """Ajusta el tamaño del fotograma en Linux."""
        if not self.device:
            return
        try:
            command = ["v4l2-ctl", f"--device={self.device}", 
                      f"--set-fmt-video=width={width},height={height}"]
            result = subprocess.run(command, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0:
                print(f"Error setting frame size: {result.stderr}")
        except Exception as e:
            print(f"Error ajustando tamaño de frame: {e}")
    
    def set_control(self, control: str, value: int):
        """Ajusta un parámetro específico de la cámara."""
        if self.platform == 'linux':
            self._set_control_linux(control, value)
        elif self.platform == 'windows':
            self._set_control_windows(control, value)
    
    def _set_control_linux(self, control: str, value: int):
        """Ajusta control en Linux."""
        if not self.device:
            return
        try:
            command = ["v4l2-ctl", f"--device={self.device}", f"--set-ctrl={control}={value}"]
            result = subprocess.run(command, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0:
                print(f"Error setting control {control}: {result.stderr}")
        except Exception as e:
            print(f"Error ajustando control {control}: {e}")
    
    def _set_control_windows(self, control: str, value: int):
        """Ajusta control en Windows."""
        if not self.control:
            return
        
        control_dict = {
            'brightness': 0, 'contrast': 1, 'hue': 2, 'saturation': 3,
            'sharpness': 4, 'gamma': 5, 'color_enable': 6, 'white_balance': 7,
            'backlight_compensation': 8, 'gain': 9, 'focus': 10,
            'white_balance_automatic': 11, 'focus_automatic_continuous': 12,
        }
        
        if control in control_dict:
            try:
                self.control.Set(control_dict[control], value, 2)
            except Exception as e:
                print(f"Error ajustando control {control}: {e}")
    
    # Métodos de conveniencia
    def set_brightness(self, value: int):
        self.set_control('brightness', value)
    
    def set_contrast(self, value: int):
        self.set_control('contrast', value)
    
    def set_focus(self, value: int):
        control_name = 'focus_absolute' if self.platform == 'linux' else 'focus'
        self.set_control(control_name, value)
    
    def set_autofocus(self, value: int):
        self.set_control('focus_automatic_continuous', value)


class CameraFinder:
    """Buscador de cámaras mejorado que fusiona ambos enfoques."""
    
    def __init__(self, config_file: str = "hardware_config.json", **kwargs):
        """
        Inicializa el buscador de cámaras con criterios de búsqueda opcionales.
        
        Args:
            config_file: Archivo de configuración de hardware
            **kwargs: Criterios de búsqueda opcionales
                - name: Nombre o parte del nombre del dispositivo
                - vendor_id: ID del fabricante (hex)
                - product_id: ID del producto (hex)
                - description: Descripción del dispositivo
                - suppress_opencv_logs: Suprimir logs de OpenCV (default: True)
        """
        self.search_criteria = kwargs
        self.system = platform.system().lower()
        self._camera_list = None
        self.suppress_logs = kwargs.get('suppress_opencv_logs', True)
        self.detector = CameraDetector()
        self.usb_detector = USBDeviceDetector()
        self.serial_detector = SerialPortDetector()
        self.hardware_config = SIEVHardwareConfig(config_file)
        
        if self.suppress_logs:
            self._suppress_opencv_logs()
    
    def _suppress_opencv_logs(self):
        """Suprime los mensajes de warning y error de OpenCV."""
        os.environ['OPENCV_LOG_LEVEL'] = 'SILENT'
        os.environ['OPENCV_VIDEOIO_DEBUG'] = '0'
        try:
            cv2.setLogLevel(0)
        except:
            pass
    
    def _safe_opencv_capture(self, index: int) -> Tuple[bool, Optional[cv2.VideoCapture]]:
        """Abre una captura de OpenCV de forma segura."""
        if self.suppress_logs:
            old_stderr = sys.stderr
            sys.stderr = open(os.devnull, 'w')
        
        try:
            cap = cv2.VideoCapture(index)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    return True, cap
            cap.release()
            return False, None
        except Exception:
            return False, None
        finally:
            if self.suppress_logs:
                sys.stderr.close()
                sys.stderr = old_stderr
    
    def find_siev_setup(self) -> Optional[Dict[str, Any]]:
        """
        Buscar el setup completo de SIEV: Hub + CH340 + Cámara.
        
        Returns:
            Dict con información completa del setup encontrado o None
        """
        print("🔍 Buscando setup completo SIEV...")
        
        # Obtener configuraciones
        hub_config = self.hardware_config.get_hub_config()
        ch340_config = self.hardware_config.get_ch340_config()
        cameras_config = self.hardware_config.get_cameras_config()
        
        # 1. Buscar hub Terminus
        usb_devices = self.usb_detector.get_usb_devices()
        hub_found = None
        
        for device in usb_devices:
            if (device.get('vendor_id') == hub_config['vendor_id'] and 
                device.get('product_id') == hub_config['product_id']):
                hub_found = device
                print(f"✅ Hub encontrado: {device['name']}")
                break
        
        if not hub_found:
            print(f"❌ Hub {hub_config['name']} no encontrado")
            return None
        
        # 2. Buscar CH340 con ESP8266 comunicándose
        esp8266_config = self.hardware_config.get_ch340_config()
        esp8266_config.update(self.hardware_config.config["siev_hardware"]["esp8266"])
        
        ch340_port = self.serial_detector.find_ch340_port(esp8266_config)
        if not ch340_port:
            print(f"❌ CH340 con ESP8266 no encontrado")
            return None
        
        print(f"✅ CH340 con ESP8266 encontrado en puerto: {ch340_port}")
        
        # Obtener información adicional del ESP8266
        esp_info = self.serial_detector.get_esp8266_info(ch340_port, esp8266_config)
        if esp_info:
            print(f"📡 ESP8266 info: {esp_info.get('version_response', 'N/A')}")
        
        # 3. Buscar cámara SIEV
        camera_found = self.find_siev_camera(cameras_config)
        if not camera_found:
            print("❌ Cámara SIEV no encontrada")
            return None
        
        print(f"✅ Cámara encontrada: {camera_found['name']} (OpenCV índice: {camera_found.get('opencv_index')})")
        
        # Setup completo encontrado
        siev_setup = {
            'hub': hub_found,
            'ch340': {
                'port': ch340_port,
                'baudrate': esp8266_config['baudrate'],
                'config': ch340_config,
                'esp8266_info': esp_info
            },
            'camera': camera_found,
            'setup_complete': True
        }
        
        print("🎯 Setup SIEV completo encontrado!")
        return siev_setup
    
    def find_siev_camera(self, cameras_config: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
        """Buscar cámara SIEV específica."""
        # Obtener todas las cámaras
        all_cameras = self._get_all_cameras()
        
        # Buscar por vendor_id/product_id primero
        for camera_cfg in cameras_config:
            target_vendor = camera_cfg['vendor_id']
            target_product = camera_cfg['product_id']
            
            for camera in all_cameras:
                # Verificar por vendor_id en información USB
                if self._camera_matches_usb_ids(camera, target_vendor, target_product):
                    camera['matched_config'] = camera_cfg
                    return camera
        
        # Fallback: buscar por nombre
        for camera_cfg in cameras_config:
            target_name = camera_cfg['name'].lower()
            
            for camera in all_cameras:
                camera_name = camera.get('name', '').lower()
                if target_name in camera_name:
                    camera['matched_config'] = camera_cfg
                    return camera
        
        return None
    
    def _camera_matches_usb_ids(self, camera: Dict[str, Any], vendor_id: str, product_id: str) -> bool:
        """Verificar si cámara coincide con vendor_id/product_id."""
        # Buscar en dispositivos USB
        usb_devices = self.usb_detector.get_usb_devices()
        
        for usb_device in usb_devices:
            if (usb_device.get('vendor_id') == vendor_id and 
                usb_device.get('product_id') == product_id):
                # Verificar si esta cámara corresponde a este dispositivo USB
                # (por nombre o por correlación)
                usb_name = usb_device.get('name', '').lower()
                camera_name = camera.get('name', '').lower()
                
                # Buscar palabras clave comunes
                common_keywords = ['camera', 'webcam', 'usb', 'video']
                if any(keyword in both for keyword in common_keywords 
                       for both in [usb_name, camera_name]):
                    return True
        
        return False
    
    def _get_system_cameras(self) -> List[Dict[str, Any]]:
        """Obtiene cámaras del sistema usando la lógica de tus clases originales."""
        if self.system == 'windows':
            return self.detector.get_windows_cameras()
        elif self.system == 'linux':
            return self.detector.get_linux_cameras()
        elif self.system == 'darwin':
            return self.detector.get_macos_cameras()
        return []
    
    def _map_opencv_indices(self, system_cameras: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Mapea índices de OpenCV con cámaras del sistema."""
        mapped_cameras = []
        
        for camera in system_cameras:
            opencv_index = None
            
            # En Linux: extraer índice directamente de /dev/videoX
            if self.system == 'linux' and 'device_path' in camera:
                device_path = camera['device_path']
                video_match = re.search(r'/dev/video(\d+)', device_path)
                if video_match:
                    opencv_index = int(video_match.group(1))
            
            # En Windows: usar el system_index como base (puede necesitar ajuste)
            elif self.system == 'windows':
                opencv_index = camera.get('system_index')
            
            # En macOS: usar el system_index
            elif self.system == 'darwin':
                opencv_index = camera.get('system_index')
            
            # Verificar que el índice OpenCV realmente funcione
            if opencv_index is not None:
                success, cap = self._safe_opencv_capture(opencv_index)
                if success and cap:
                    camera['opencv_index'] = opencv_index
                    cap.release()
                else:
                    camera['opencv_index'] = None
            else:
                camera['opencv_index'] = None
            
            mapped_cameras.append(camera)
        
        # Detectar cámaras adicionales que solo OpenCV ve
        detected_indices = {cam.get('opencv_index') for cam in mapped_cameras if cam.get('opencv_index') is not None}
        
        for i in range(15):  # Probar índices adicionales
            if i not in detected_indices:
                success, cap = self._safe_opencv_capture(i)
                if success and cap:
                    mapped_cameras.append({
                        'name': f'OpenCV Camera {i}',
                        'opencv_index': i,
                        'system_index': None,
                        'platform': 'opencv_only'
                    })
                    cap.release()
        
        return mapped_cameras
    
    def _get_all_cameras(self) -> List[Dict[str, Any]]:
        """Obtiene todas las cámaras combinando detección del sistema y OpenCV."""
        if self._camera_list is not None:
            return self._camera_list
        
        # Obtener cámaras del sistema
        system_cameras = self._get_system_cameras()
        
        # Mapear con índices OpenCV
        all_cameras = self._map_opencv_indices(system_cameras)
        
        self._camera_list = all_cameras
        return all_cameras
    
    def _matches_criteria(self, camera: Dict[str, Any]) -> bool:
        """Verifica si una cámara coincide con los criterios de búsqueda."""
        if not self.search_criteria:
            return True
        
        for key, value in self.search_criteria.items():
            if key == 'suppress_opencv_logs':
                continue
            if value is None:
                continue
            
            camera_value = camera.get(key, '')
            if camera_value is None:
                continue
            
            value_str = str(value).lower()
            camera_value_str = str(camera_value).lower()
            
            if key in ['name', 'description', 'full_name', 'model']:
                if value_str not in camera_value_str:
                    return False
            else:
                if camera_value_str != value_str:
                    return False
        
        return True
    
    def get_camera_index(self) -> Optional[int]:
        """Busca una cámara que coincida con los criterios y devuelve su índice OpenCV."""
        cameras = self._get_all_cameras()
        
        for camera in cameras:
            if self._matches_criteria(camera) and camera.get('opencv_index') is not None:
                return camera['opencv_index']
        
        return None
    
    def get_camera_info(self) -> Optional[Dict[str, Any]]:
        """Busca una cámara y devuelve toda su información."""
        cameras = self._get_all_cameras()
        
        for camera in cameras:
            if self._matches_criteria(camera):
                return camera
        
        return None
    
    def list_all_cameras(self) -> List[Dict[str, Any]]:
        """Devuelve la lista completa de cámaras con información detallada."""
        return self._get_all_cameras()
    
    def find_cameras(self) -> List[Dict[str, Any]]:
        """Busca cámaras que coincidan con los criterios especificados."""
        cameras = self._get_all_cameras()
        return [camera for camera in cameras if self._matches_criteria(camera)]
    
    def create_controller(self, camera_info: Dict[str, Any] = None) -> Optional[CameraController]:
        """Crea un controlador de cámara para la cámara especificada o encontrada."""
        if camera_info is None:
            camera_info = self.get_camera_info()
        
        if camera_info is None:
            return None
        
        platform_type = camera_info.get('platform', self.system)
        controller = CameraController(platform_type)
        
        device_path = camera_info.get('device_path') or camera_info.get('full_name')
        if device_path:
            controller.set_camera(device_path)
        
        return controller
    
    def get_siev_camera_index(self) -> Optional[int]:
        """Obtener índice OpenCV de la cámara SIEV específica."""
        siev_setup = self.find_siev_setup()
        if siev_setup and siev_setup.get('camera'):
            return siev_setup['camera'].get('opencv_index')
        return None
    
    def get_siev_serial_port(self) -> Optional[str]:
        """Obtener puerto serie del CH340 en el setup SIEV."""
        siev_setup = self.find_siev_setup()
        if siev_setup and siev_setup.get('ch340'):
            return siev_setup['ch340'].get('port')
        return None
    
    def verify_siev_setup(self) -> bool:
        """Verificar que el setup SIEV completo esté disponible."""
        siev_setup = self.find_siev_setup()
        return siev_setup is not None and siev_setup.get('setup_complete', False)


# Funciones de conveniencia para SIEV
def find_siev_camera() -> Optional[int]:
    """Función rápida para encontrar cámara SIEV."""
    finder = CameraFinder()
    return finder.get_siev_camera_index()

def find_siev_serial() -> Optional[str]:
    """Función rápida para encontrar puerto serie SIEV."""
    finder = CameraFinder()
    return finder.get_siev_serial_port()

def verify_siev_hardware() -> bool:
    """Función rápida para verificar hardware SIEV completo."""
    finder = CameraFinder()
    return finder.verify_siev_setup()


# Ejemplo de uso
if __name__ == "__main__":
    print("=== SISTEMA DE DETECCIÓN SIEV ROBUSTO ===\n")
    
    # Verificar setup completo
    finder = CameraFinder()
    
    print("1. Verificando hardware SIEV completo...")
    siev_setup = finder.find_siev_setup()
    
    if siev_setup:
        print("\n🎯 ¡SETUP SIEV ENCONTRADO!")
        print(f"Hub: {siev_setup['hub']['name']}")
        print(f"CH340 Puerto: {siev_setup['ch340']['port']} @ {siev_setup['ch340']['baudrate']} baud")
        
        # Mostrar info del ESP8266 si está disponible
        esp_info = siev_setup['ch340'].get('esp8266_info', {})
        if esp_info:
            print(f"ESP8266: {esp_info.get('version_response', 'N/A')}")
            print(f"Status: {esp_info.get('status_response', 'N/A')}")
        
        print(f"Cámara: {siev_setup['camera']['name']} (Índice OpenCV: {siev_setup['camera'].get('opencv_index')})")
        
        # Probar conexión OpenCV
        camera_index = siev_setup['camera'].get('opencv_index')
        if camera_index is not None:
            cap = cv2.VideoCapture(camera_index)
            if cap.isOpened():
                print(f"✅ Conexión OpenCV exitosa en índice {camera_index}")
                cap.release()
            else:
                print(f"❌ Error conectando OpenCV en índice {camera_index}")
        
        # Probar conexión serie con ESP8266
        try:
            import serial
            ser = serial.Serial(siev_setup['ch340']['port'], siev_setup['ch340']['baudrate'], timeout=1)
            
            # Enviar comando PING
            ser.write(b'PING\r\n')
            ser.flush()
            import time
            time.sleep(0.2)
            
            if ser.in_waiting > 0:
                response = ser.readline().decode('utf-8', errors='ignore').strip()
                print(f"✅ Comunicación ESP8266 exitosa: {response}")
            else:
                print("⚠️ ESP8266 no responde a PING")
                
            ser.close()
        except Exception as e:
            print(f"❌ Error comunicación ESP8266: {e}")
    
    else:
        print("❌ Setup SIEV no encontrado")
        print("\n📋 Dispositivos disponibles:")
        
        # Mostrar dispositivos USB
        usb_detector = USBDeviceDetector()
        usb_devices = usb_detector.get_usb_devices()
        print("\nDispositivos USB:")
        for device in usb_devices[:10]:  # Mostrar solo primeros 10
            print(f"  {device.get('vendor_id', 'N/A')}:{device.get('product_id', 'N/A')} - {device.get('name', 'N/A')}")
        
        # Mostrar puertos serie
        serial_detector = SerialPortDetector()
        serial_ports = serial_detector.get_serial_ports()
        print("\nPuertos Serie:")
        for port in serial_ports:
            print(f"  {port['device']} - {port['name']} (VID: {port.get('vendor_id', 'N/A')})")
        
        # Mostrar cámaras
        all_cameras = finder.list_all_cameras()
        print("\nCámaras disponibles:")
        for cam in all_cameras:
            print(f"  Índice {cam.get('opencv_index', 'N/A')}: {cam.get('name', 'N/A')}")
    
    print("\n=== FUNCIONES RÁPIDAS ===")
    print(f"find_siev_camera(): {find_siev_camera()}")
    print(f"find_siev_serial(): {find_siev_serial()}")
    print(f"verify_siev_hardware(): {verify_siev_hardware()}")