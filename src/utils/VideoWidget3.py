from ultralytics import YOLO
import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal, QTimer, Qt, QObject
from PySide6.QtGui import QImage, QPixmap

class VideoThread(QThread):
    frame_ready = Signal(np.ndarray, float, object)  # frame, fps, pupil_positions
    
    def __init__(self, camera_id=2):
        super().__init__()
        self.running = True
        self.camera_id = camera_id
        self.frame_count = 0
        self.last_time = cv2.getTickCount()
        self.fps_max = 0
        
        # Cargar el modelo YOLO entrenado
        self.model = YOLO('best_color.pt')
        
        # Preallocación de memoria
        self.gray = None
        self.frame_draw = None
        
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
            
            #   Obtener primer frame para preallocación
            _, init_frame = cap.read()
            h, w = init_frame.shape[:2]
            
            # Preallocar arrays
            self.gray = np.empty((h, w), dtype=np.uint8)
            
            # Definir ROI fija
            roi_y = int(h * 0.1)
            roi_height = int(h * 0.4)
            
            # Factor de escala para reducir la resolución
            scale_factor = 0.5  # Reducir a la mitad



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
                
                # Convertir a gris para procesamiento de pupila
                cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY, dst=self.gray)
                
                # Aplicar ROI
                roi_frame = frame[roi_y:roi_y+roi_height, :]
                
                # Redimensionar ROI para YOLO
                small_roi = cv2.resize(roi_frame, None, fx=scale_factor, fy=scale_factor)
                
                # Detectar ojos con YOLO en la ROI reducida
                results = self.model(small_roi, conf=0.2, verbose=False)
                
                # Dibujar líneas de ROI
                cv2.line(self.frame_draw, (0, roi_y), (w, roi_y), (0, 255, 255), 1)
                cv2.line(self.frame_draw, (0, roi_y + roi_height), (w, roi_y + roi_height), (0, 255, 255), 1)
                
                # Procesar detecciones
                eye_regions = []
                for i, r in enumerate(results):
                    boxes = r.boxes.cpu().numpy()
                    # Ordenar cajas por coordenada X (izquierda a derecha)
                    sorted_boxes = sorted(boxes, key=lambda box: box.xyxy[0][0])
                    
                    for j, box in enumerate(sorted_boxes):
                        # Obtener coordenadas (xmin, ymin, xmax, ymax) en la imagen reducida
                        x1_small, y1_small, x2_small, y2_small = box.xyxy[0]
                        
                        # Ajustar coordenadas a la imagen original
                        x1 = int(x1_small / scale_factor)
                        y1 = int(y1_small / scale_factor) + roi_y
                        x2 = int(x2_small / scale_factor)
                        y2 = int(y2_small / scale_factor) + roi_y
                        
                        # Convertir a enteros para las coordenadas de la caja
                        ex, ey = x1, y1
                        ew, eh = x2 - x1, y2 - y1
                        
                        # Dibujar rectángulo en la imagen original
                        cv2.rectangle(self.frame_draw, (ex, ey), (ex+ew, ey+eh), (0, 255, 0), 1)
                        
                        # Determinar si es el primer ojo (más a la izquierda)
                        is_first_eye = (j == 0)
                        
                        # Procesar región del ojo para detectar pupila
                        eye_gray = self.gray[ey:ey+eh, ex:ex+ew]
                        eye_color = self.frame_draw[ey:ey+eh, ex:ex+ew]
                        eye_regions.append((eye_gray, eye_color, ex, ey, ew, eh, is_first_eye))
                
                # Lista para guardar posiciones de pupilas [x, y, is_first_eye]
                pupil_positions = []
                
                # Procesar cada región de ojo para detectar pupila
                for data in eye_regions:
                    result = self.process_eye_region(data)
                    if result:
                        cx, cy, radius, ex, ey, ew, eh, mask = result
                        
                        # Dibujar círculo de la pupila
                        cv2.circle(self.frame_draw[ey:ey+eh, ex:ex+ew], (cx, cy), radius, (255, 0, 0), 1)
                        
                        # Calcular coordenadas absolutas de la pupila
                        abs_x = ex + cx
                        abs_y = ey + cy
                        
                        # Guardar posición de la pupila con indicador de ojo izquierdo/derecho
                        pupil_positions.append([abs_x, abs_y, data[6]])  # data[6] es is_first_eye
                        
                        # Opcionalmente, mostrar la máscara de threshold
                        roi = self.frame_draw[ey:ey+eh, ex:ex+ew]
                        cv2.addWeighted(roi, 0.7, mask, 0.3, 0, roi)
                
                # Convertir y emitir
                cv2.cvtColor(self.frame_draw, cv2.COLOR_BGR2RGB, dst=self.frame_draw)
                
                # Emitir frame, fps y posiciones de pupilas (None si no se encontraron)
                positions = pupil_positions if pupil_positions else None
                self.frame_ready.emit(self.frame_draw, fps, positions)
                
                self.frame_count += 1
                if fps > self.fps_max:
                    self.fps_max = fps
                if fps > 210:
                    self.fps_max = 0
                    
        except Exception as e:
            print(f"Error en run: {e}")
        finally:
            cap.release()
            
    def stop(self):
        """Detiene el hilo de manera segura."""
        self.running = False  # Indica que el hilo debe detenerse
        self.wait()  # Espera a que el hilo termine completamente
        
                
class VideoWidget(QObject):
    sig_pos = Signal(list)

    def __init__(self, camera_frame, fps_label):
        super().__init__()

        self.camera_frame = camera_frame
        self.fps_label = fps_label
        self.pos_eye = []

        self.video_thread = VideoThread()
        self.video_thread.frame_ready.connect(self.update_frame)
        
        self.fps_timer = QTimer()
        self.fps_timer.timeout.connect(self.update_fps_display)
        self.fps_timer.start(500)
        
        self.current_fps = 0
        self.video_thread.start(QThread.HighPriority)
    
    def update_frame(self, frame, fps, pupil_positions):
        try:
            self.current_fps = fps
            
            # Actualizar la imagen
            if frame is not None and frame.size > 0:
                height, width = frame.shape[:2]
                bytes_per_line = 3 * width
                
                image = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
                if not image.isNull():
                    self.camera_frame.setPixmap(QPixmap.fromImage(image))
            
            # Procesar posiciones de pupilas (puedes hacer lo que necesites con ellas)
            pupils_pos = []
            if pupil_positions:
                for x, y, is_first_eye in pupil_positions:
                    eye_name = "Izquierdo" if is_first_eye else "Derecho"
                    pupils_pos.append([x, y])
                    #self.pos_eye.append([x, y])
                    #print(f"Pupila en ojo {eye_name}: ({x}, {y})")
                    # Ejemplo: actualizar algún elemento de UI con esta información
                    # self.ui.label_pupil_coords.setText(f"Pupila: ({x}, {y})")
                self.pos_eye = pupils_pos
                self.sig_pos.emit(self.pos_eye)

        except Exception as e:
            print(f"Error en update_frame: {e}")
    
    def update_fps_display(self):

        try:
            self.fps_label.setText(
                f"FPS: {self.current_fps:.1f} Max: {self.video_thread.fps_max:.1f}"
            )
            #print(f"Posición de la pupila: {self.pos_eye}", end="")

        except Exception as e:
            print(f"Error en update_fps_display: {e}")
    
    def cleanup(self):
        try:
            self.video_thread.stop()
            self.fps_timer.stop()
        except Exception as e:
            print(f"Error en cleanup: {e}")