import cv2
import os
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

class CameraThread(QThread):
    frameReady = Signal(QImage)
    
    def __init__(self):
        super().__init__()
        self.camera = None
        self.recording = False
        self.video_writer = None
        self.running = False
        self.camera_index = 2
        
    def get_available_cameras(self):
        """Detecta cámaras disponibles"""
        available_cameras = []
        for i in range(2):  # Buscar hasta 5 cámaras
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    available_cameras.append(i)
                cap.release()
        return available_cameras
        
    def start_camera(self, camera_index=2):
        """Inicia la cámara"""
        self.camera_index = camera_index
        if self.camera:
            self.camera.release()
            
        self.camera = cv2.VideoCapture(self.camera_index)
        
        if self.camera.isOpened():
            # Configurar resolución
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.camera.set(cv2.CAP_PROP_FPS, 30)
            
            self.running = True
            if not self.isRunning():
                self.start()
            return True
        return False
        
    def change_camera(self, camera_index):
        """Cambia la cámara activa"""
        was_recording = self.recording
        current_filename = getattr(self, 'current_filename', None)
        
        if was_recording:
            self.stop_recording()
            
        if self.camera:
            self.camera.release()
            
        success = self.start_camera(camera_index)
        
        if was_recording and success and current_filename:
            # Reanudar grabación si estaba grabando
            self.start_recording(current_filename)
            
        return success
        
    def stop_camera(self):
        """Detiene la cámara"""
        self.running = False
        if self.recording:
            self.stop_recording()
        if self.camera:
            self.camera.release()
        if self.isRunning():
            self.quit()
            self.wait()
        
    def start_recording(self, filename):
        """Inicia la grabación de video"""
        if self.camera and self.camera.isOpened():
            # Crear directorio si no existe
            directory = os.path.dirname(filename)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
                
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            fps = 30.0
            frame_size = (640, 480)
            self.video_writer = cv2.VideoWriter(filename, fourcc, fps, frame_size)
            self.recording = True
            self.current_filename = filename
            print(f"Iniciando grabación: {filename}")
            return True
        return False
            
    def stop_recording(self):
        """Detiene la grabación"""
        self.recording = False
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
            print("Grabación detenida")
            
    def run(self):
        """Hilo principal de la cámara"""
        while self.running:
            if self.camera and self.camera.isOpened():
                ret, frame = self.camera.read()
                if ret:
                    # Grabar frame si está grabando
                    if self.recording and self.video_writer:
                        self.video_writer.write(frame)
                    
                    # Convertir frame para Qt
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w, ch = rgb_frame.shape
                    bytes_per_line = ch * w
                    qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                    self.frameReady.emit(qt_image)
                else:
                    # Error en la cámara, intentar reconectar
                    print("Error leyendo cámara, intentando reconectar...")
                    self.camera.release()
                    self.camera = cv2.VideoCapture(self.camera_index)
            
            self.msleep(33)  # ~30 FPS