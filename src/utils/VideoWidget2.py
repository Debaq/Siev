import dlib
from PySide6.QtCore import QThread, Signal, QTimer, Qt
from PySide6.QtGui import QImage, QPixmap
import cv2
import numpy as np
from queue import Queue
from concurrent.futures import ThreadPoolExecutor
import time

class VideoThread(QThread):
    frame_ready = Signal(np.ndarray, float)
    
    def __init__(self, camera_id=2):
        super().__init__()
        self.running = True
        self.camera_id = camera_id
        self.frame_count = 0
        self.last_time = cv2.getTickCount()
        self.fps_max = 0
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Inicializar dlib
        self.detector = dlib.get_frontal_face_detector()
        self.predictor = dlib.shape_predictor('shape_predictor_5_face_landmarks.dat')
        
        # Preallocación de memoria
        self.gray = None
        self.frame_draw = None
        self.last_detected_eyes = []
    def setup_camera(self):
        cap = cv2.VideoCapture(self.camera_id)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 424)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
        cap.set(cv2.CAP_PROP_FPS, 210)
        cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 3)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap
    def get_eye_regions(self, shape, frame):
        # Extraer regiones de los ojos del predictor de 5 puntos
        # Los puntos 2 y 3 corresponden a los ojos izquierdo y derecho
        eye_regions = []
        
        # Obtener coordenadas de los ojos
        for i in range(2, 4):  # Puntos 2 y 3 son los ojos
            x = shape.part(i).x
            y = shape.part(i).y
            
            # Crear una región alrededor del punto del ojo
            eye_box_size = 40  # Ajustar según necesidad
            ex = max(0, x - eye_box_size // 2)
            ey = max(0, y - eye_box_size // 2)
            ew = eye_box_size
            eh = eye_box_size
            
            # Asegurar que no nos salimos de los límites del frame
            if ex + ew > frame.shape[1]: ew = frame.shape[1] - ex
            if ey + eh > frame.shape[0]: eh = frame.shape[0] - ey
            
            eye_regions.append((ex, ey, ew, eh))
            
        return eye_regions

    def process_eye_region(self, data):
        try:
            eye_gray, eye_color, ex, ey, ew, eh = data
            
            _, thresh = cv2.threshold(eye_gray, 40, 255, cv2.THRESH_BINARY_INV)
            contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            contours = sorted(contours, key=lambda x: cv2.contourArea(x), reverse=True)
                
            if contours:
                (cx, cy), radius = cv2.minEnclosingCircle(contours[0])
                return (int(cx), int(cy), int(radius), ex, ey, ew, eh)
                
            return None
        except Exception as e:
            print(f"Error en process_eye_region: {e}")
            return None

    def run(self):
        try:
            cap = self.setup_camera()
            if not cap.isOpened():
                print("Error: No se pudo abrir la cámara")
                return
            
            while self.running:
                ret, frame = cap.read()
                if not ret:
                    continue
                
                # Calcular FPS
                current_time = cv2.getTickCount()
                fps = cv2.getTickFrequency() / (current_time - self.last_time)
                self.last_time = current_time
                
                # Crear copia del frame
                self.frame_draw = frame.copy()
                
                # Convertir a gris
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # Detectar caras
                faces = self.detector(gray)
                
                # Procesar cada cara detectada
                for face in faces:
                    # Obtener landmarks
                    shape = self.predictor(gray, face)
                    
                    # Obtener regiones de los ojos
                    eye_regions = self.get_eye_regions(shape, frame)
                    self.last_detected_eyes = eye_regions
                    
                    # Procesar ojos en paralelo
                    eye_data = []
                    for ex, ey, ew, eh in eye_regions:
                        eye_gray = gray[ey:ey+eh, ex:ex+ew]
                        eye_color = self.frame_draw[ey:ey+eh, ex:ex+ew]
                        eye_data.append((eye_gray, eye_color, ex, ey, ew, eh))
                    
                    if eye_data:
                        results = list(self.executor.map(self.process_eye_region, eye_data))
                        
                        for result in results:
                            if result:
                                cx, cy, radius, ex, ey, ew, eh = result
                                cv2.rectangle(self.frame_draw, (ex, ey), (ex+ew, ey+eh), (0, 255, 0), 1)
                                cv2.circle(self.frame_draw[ey:ey+eh, ex:ex+ew], (cx, cy), radius, (255, 0, 0), 1)
                
                # Convertir y emitir
                cv2.cvtColor(self.frame_draw, cv2.COLOR_BGR2RGB, dst=self.frame_draw)
                self.frame_ready.emit(self.frame_draw, fps)
                
                self.frame_count += 1
                if fps > self.fps_max:
                    self.fps_max = fps
                if fps > 210:
                    self.fps_max = 0
                    
        except Exception as e:
            print(f"Error en run: {e}")
        finally:
            self.executor.shutdown()
            cap.release()


class VideoWidget:
    def __init__(self, camera_frame, fps_label):
        self.camera_frame = camera_frame
        self.fps_label = fps_label
        
        self.video_thread = VideoThread()
        self.video_thread.frame_ready.connect(self.update_frame)
        
        self.fps_timer = QTimer()
        self.fps_timer.timeout.connect(self.update_fps_display)
        self.fps_timer.start(500)
        
        self.current_fps = 0
        self.video_thread.start(QThread.HighPriority)
    
    def update_frame(self, frame, fps):
        try:
            self.current_fps = fps
            
            if frame is None or frame.size == 0:
                return
            
            height, width = frame.shape[:2]
            bytes_per_line = 3 * width
            
            image = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
            if not image.isNull():
                self.camera_frame.setPixmap(QPixmap.fromImage(image))
            
        except Exception as e:
            print(f"Error en update_frame: {e}")
    
    def update_fps_display(self):
        try:
            self.fps_label.setText(
                f"FPS: {self.current_fps:.1f} Max: {self.video_thread.fps_max:.1f}"
            )
        except Exception as e:
            print(f"Error en update_fps_display: {e}")
    
    def cleanup(self):
        try:
            self.video_thread.stop()
            self.fps_timer.stop()
        except Exception as e:
            print(f"Error en cleanup: {e}")