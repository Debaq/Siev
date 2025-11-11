import platform
import subprocess
import re
import cv2


class CameraResolutionDetector:
    """Detecta resoluciones y FPS disponibles de cámara según el OS"""
    
    def __init__(self):
        self.sistema = platform.system()
    
    def listar_resoluciones(self, device_id=0):
        """
        Lista resoluciones con FPS máximos disponibles
        
        Args:
            device_id: ID del dispositivo (int para Windows/macOS, se convierte a /dev/video{id} en Linux)
        
        Returns:
            list: Lista de strings con formato "widthxheight@fps"
        """
        if self.sistema == "Linux":
            return self._listar_v4l2(device_id)
        elif self.sistema == "Windows":
            return self._listar_windows(device_id)
        else:
            # Fallback para macOS y otros
            return self._listar_opencv(device_id)
    
    def _listar_v4l2(self, device_id):
        """Método para Linux usando V4L2"""
        device_path = f'/dev/video{device_id}'
        
        try:
            result = subprocess.run(['v4l2-ctl', '--device', device_path, '--list-formats-ext'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                print(f"Error ejecutando v4l2-ctl: {result.stderr}")
                return self._listar_opencv(device_id)
            
            resoluciones_fps = []
            lines = result.stdout.split('\n')
            
            current_resolution = None
            for line in lines:
                # Buscar resolución
                res_match = re.search(r'Size: Discrete (\d+)x(\d+)', line)
                if res_match:
                    current_resolution = (int(res_match.group(1)), int(res_match.group(2)))
                
                # Buscar FPS para la resolución actual
                if current_resolution:
                    fps_match = re.search(r'(\d+\.?\d*) fps', line)
                    if fps_match:
                        fps = int(float(fps_match.group(1)))
                        formato = f"{current_resolution[0]}x{current_resolution[1]}@{fps}"
                        if formato not in resoluciones_fps:
                            resoluciones_fps.append(formato)
            
            return sorted(resoluciones_fps)
            
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            print(f"Error con V4L2: {e}, usando OpenCV como fallback")
            return self._listar_opencv(device_id)
    
    def _listar_windows(self, device_id):
        """Método para Windows usando DirectShow (simplificado)"""
        try:
            # Intentar usar PowerShell para obtener info de dispositivos
            ps_cmd = """
            Get-WmiObject -Class Win32_PnPEntity | Where-Object {
                $_.Name -match 'camera|webcam|video' -and $_.Status -eq 'OK'
            } | Select-Object Name, DeviceID
            """
            
            result = subprocess.run(['powershell', '-Command', ps_cmd], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and result.stdout.strip():
                print("Dispositivos de video encontrados via PowerShell")
            
        except Exception as e:
            print(f"Error con PowerShell: {e}")
        
        # Fallback a OpenCV para Windows (más confiable por ahora)
        return self._listar_opencv(device_id)
    
    def _listar_opencv(self, device_id):
        """Método fallback usando OpenCV"""
        cap = cv2.VideoCapture(device_id)
        
        if not cap.isOpened():
            print(f"No se pudo abrir la cámara {device_id}")
            return []
        
        # Resoluciones comunes a probar
        resoluciones_prueba = [
            (320, 240), (640, 480), (800, 600), (1024, 768),
            (1280, 720), (1280, 960), (1920, 1080), (2560, 1440)
        ]
        
        # FPS comunes a probar
        fps_prueba = [15, 30, 60, 120]
        
        resoluciones_fps = []
        
        for ancho, alto in resoluciones_prueba:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, ancho)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, alto)
            
            ancho_real = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            alto_real = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Si la resolución se configuró correctamente
            if ancho_real > 0 and alto_real > 0:
                max_fps = 30  # FPS por defecto
                
                # Probar diferentes FPS para encontrar el máximo
                for fps in fps_prueba:
                    cap.set(cv2.CAP_PROP_FPS, fps)
                    fps_real = cap.get(cv2.CAP_PROP_FPS)
                    
                    if fps_real >= fps * 0.9:  # Tolerancia del 10%
                        max_fps = fps
                
                formato = f"{ancho_real}x{alto_real}@{max_fps}"
                if formato not in resoluciones_fps:
                    resoluciones_fps.append(formato)
        
        cap.release()
        return resoluciones_fps
    
    def obtener_info_sistema(self):
        """Retorna información del sistema detectado"""
        return {
            'sistema': self.sistema,
            'metodo': 'V4L2' if self.sistema == 'Linux' else 
                     'DirectShow' if self.sistema == 'Windows' else 'OpenCV'
        }