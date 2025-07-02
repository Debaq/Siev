import cv2
import platform
import subprocess
import re
import os
import sys
from typing import List, Dict, Optional, Any, Tuple

# Importaciones condicionales para Windows
try:
    import win32com.client
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False


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
    
    def __init__(self, **kwargs):
        """
        Inicializa el buscador de cámaras con criterios de búsqueda opcionales.
        
        Args:
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


# Ejemplo de uso
if __name__ == "__main__":
    print("=== FUSIÓN DE SISTEMAS DE DETECCIÓN DE CÁMARAS ===\n")
    
    # Listar todas las cámaras
    finder = CameraFinder()
    all_cameras = finder.list_all_cameras()
    
    print("=== TODAS LAS CÁMARAS DETECTADAS ===")
    for i, camera in enumerate(all_cameras):
        print(f"Cámara {i+1}:")
        print(f"  Nombre: {camera.get('name', 'N/A')}")
        print(f"  Índice OpenCV: {camera.get('opencv_index', 'N/A')}")
        print(f"  Plataforma: {camera.get('platform', 'N/A')}")
        print(f"  Device Path: {camera.get('device_path', 'N/A')}")
        print()
    
    # Buscar una cámara específica
    print("=== BÚSQUEDA ESPECÍFICA ===")
    specific_finder = CameraFinder(name="Microsoft")
    camera_info = specific_finder.get_camera_info()
    
    if camera_info:
        print(f"Cámara encontrada: {camera_info['name']}")
        print(f"Índice OpenCV: {camera_info.get('opencv_index')}")
        
        # Crear controlador y conectar
        controller = specific_finder.create_controller(camera_info)
        if controller:
            print("✓ Controlador creado exitosamente")
            
            # Probar conexión OpenCV
            opencv_index = camera_info.get('opencv_index')
            if opencv_index is not None:
                cap = cv2.VideoCapture(opencv_index)
                if cap.isOpened():
                    print(f"✓ Conectado a OpenCV en índice {opencv_index}")
                    cap.release()
                else:
                    print(f"✗ Error conectando a OpenCV en índice {opencv_index}")
        else:
            print("✗ No se pudo crear el controlador")
    else:
        print("No se encontró la cámara especificada")