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
        
        # Optimización 1: Procesamiento selectivo
        self.process_every_n_frames = 1
        self.frame_counter = 0
        self.last_detected_eyes = []
        
        # Optimización 5: Preallocación de memoria
        self.gray = None
        self.frame_draw = None
        self.roi_gray = None
        self.kernel_erode = np.ones((3,3), np.uint8)
        
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

    def process_eye_region(self, data):
        try:
            eye_gray, eye_color, ex, ey, ew, eh, is_first_eye = data
            
            # Umbral adaptativo
            thresh = cv2.adaptiveThreshold(
                eye_gray,
                255,
                cv2.ADAPTIVE_THRESH_MEAN_C,  # o cv2.ADAPTIVE_THRESH_GAUSSIAN_C
                cv2.THRESH_BINARY_INV,
                21,  # Tamaño del bloque - debe ser impar
                5    # Constante que se resta del valor medio
            )
            threshold_value = 40 if is_first_eye else 10

            _, thresh = cv2.threshold(eye_gray, threshold_value, 255, cv2.THRESH_BINARY_INV)

            
            # Crear una máscara en color para visualización
            mask = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)
        
            contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            contours = sorted(contours, key=lambda x: cv2.contourArea(x), reverse=True)
                
            if contours:
                (cx, cy), radius = cv2.minEnclosingCircle(contours[0])
                return (int(cx), int(cy), int(radius), ex, ey, ew, eh, mask)
                
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

            eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
            
            # Obtener primer frame para preallocación
            _, init_frame = cap.read()
            h, w = init_frame.shape[:2]
            
            # Optimización 5: Preallocar arrays
            self.gray = np.empty((h, w), dtype=np.uint8)
            self.frame_draw = np.empty_like(init_frame)
            
            # Optimización 2: Calcular ROI fija
            roi_y = int(h * 0.1)  # 20% desde arriba
            roi_height = int(h * 0.5)  # 60% del alto
            self.roi_gray = np.empty((roi_height, w), dtype=np.uint8)
            
            while self.running:
                ret, frame = cap.read()
                if not ret:
                    continue
                
                # Calcular FPS
                current_time = cv2.getTickCount()
                fps = cv2.getTickFrequency() / (current_time - self.last_time)
                self.last_time = current_time
                
                # Copiar frame para dibujo
                #np.copyto(self.frame_draw, frame)
                self.frame_draw = frame.copy()

               
                # Optimización 4: Procesamiento condicional
                cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY, dst=self.gray)

                self.frame_counter += 1
                if self.frame_counter % self.process_every_n_frames == 0:
                    # Convertir a gris y aplicar ROI
                    roi_frame = self.gray[roi_y:roi_y+roi_height, :]
                    
                    # Preprocesamiento en ROI
                    cv2.erode(roi_frame, self.kernel_erode, dst=self.roi_gray, iterations=1)
                    cv2.normalize(self.roi_gray, self.roi_gray, 0, 255, cv2.NORM_MINMAX)
                    
                    # Detección de ojos en ROI
                    eyes = eye_cascade.detectMultiScale(
                        self.roi_gray,
                        scaleFactor=1.1,
                        minNeighbors=3,
                        minSize=(50, 50),
                        maxSize=(90, 90)
                    )
                    if len(eyes) > 0:
                        self.last_detected_eyes = [(ex, ey + roi_y, ew, eh) for (ex, ey, ew, eh) in eyes[:2]]  # Limitamos a 2 ojos
                        
                        # Procesar ojos en paralelo
                        eye_regions = []
                        for i, (ex, ey, ew, eh) in enumerate(self.last_detected_eyes):
                            eye_gray = self.gray[ey:ey+eh, ex:ex+ew]
                            eye_color = self.frame_draw[ey:ey+eh, ex:ex+ew]
                            is_first_eye = (i == 0)  # True para el primer ojo, False para el segundo
                            eye_regions.append((eye_gray, eye_color, ex, ey, ew, eh, is_first_eye))
                        
                        results = list(self.executor.map(self.process_eye_region, eye_regions))


                        
                        for result in results:
                            if result:
                                cx, cy, radius, ex, ey, ew, eh, mask = result
                                cv2.rectangle(self.frame_draw, (ex, ey), (ex+ew, ey+eh), (0, 255, 0), 1)
                                cv2.circle(self.frame_draw[ey:ey+eh, ex:ex+ew], (cx, cy), radius, (255, 0, 0), 1)
                                roi = self.frame_draw[ey:ey+eh, ex:ex+ew]
                                cv2.addWeighted(roi, 0.1, mask, 0.9, 0, roi)


                    else:
                        # Usar últimas detecciones conocidas
                        for (ex, ey, ew, eh) in self.last_detected_eyes:
                            cv2.rectangle(self.frame_draw, (ex, ey), (ex+ew, ey+eh), (0, 255, 0), 1)

                # Dibujar las líneas ROI
                cv2.line(self.frame_draw, (0, roi_y), (w, roi_y), (0, 255, 255), 1)  # Línea superior amarilla
                cv2.line(self.frame_draw, (0, roi_y + roi_height), (w, roi_y + roi_height), (0, 255, 255), 1)  # Línea inferior amarilla

                # Convertir y emitir
                cv2.cvtColor(self.frame_draw, cv2.COLOR_BGR2RGB, dst=self.frame_draw)
                self.frame_ready.emit(self.frame_draw, fps)
                
                self.frame_count += 1
                if fps > self.fps_max:
                    self.fps_max = fps
                if fps >210:
                    self.fps_max = 0
                    
        except Exception as e:
            print(f"Error en run: {e}")
        finally:
            self.executor.shutdown()
            cap.release()

    def stop(self):
        self.running = False
        self.wait()

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