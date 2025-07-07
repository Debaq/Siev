from ultralytics import YOLO
import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal, QTimer, Qt, QObject
from PySide6.QtGui import QImage, QPixmap
import torch

class VideoThread(QThread):
    frame_ready = Signal(np.ndarray, float, object)  # frame, fps, pupil_positions
    
    def __init__(self, camera_id=2, use_onnx=False):
        super().__init__()
        self.running = True
        self.camera_id = camera_id
        self.frame_count = 0
        self.last_time = cv2.getTickCount()
        self.fps_max = 0
        self.use_onnx = use_onnx
        
        # Cargar el modelo
        if use_onnx:
            try:
                import onnxruntime as ort
                print("Intentando cargar el modelo ONNX...")
                self.session = ort.InferenceSession("best_color.onnx", 
                                                  providers=['CPUExecutionProvider'])
                self.input_name = self.session.get_inputs()[0].name
                self.output_names = [output.name for output in self.session.get_outputs()]
                self.input_shape = self.session.get_inputs()[0].shape
                print(f"Modelo ONNX cargado con éxito. Entrada: {self.input_name}, forma: {self.input_shape}")
            except Exception as e:
                print(f"Error al cargar modelo ONNX: {e}")
                print("Fallback a PyTorch")
                self.use_onnx = False
        
        if not self.use_onnx:
            print("Cargando modelo PyTorch...")
            self.model = YOLO('best_color.pt')
            # Configuración más conservadora para CPU
            if not torch.cuda.is_available():
                torch.set_num_threads(1)  # Usar menos hilos
                print("Usando CPU con configuración conservadora")
        
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
            
            mask = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)
        
            contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                return None
                
            contours = sorted(contours, key=lambda x: cv2.contourArea(x), reverse=True)
                
            if contours:
                (cx, cy), radius = cv2.minEnclosingCircle(contours[0])
                return (int(cx), int(cy), int(radius), ex, ey, ew, eh, mask)
                
            return None
        except Exception as e:
            print(f"Error en process_eye_region: {e}")
            return None
    
    def preprocess_for_onnx(self, img):
        """Preprocesa la imagen para ONNX - versión revisada"""
        # Extraer dimensiones del modelo
        input_height = self.input_shape[2]
        input_width = self.input_shape[3]
        
        # Redimensionar con interpolación exacta que espera el modelo
        resized = cv2.resize(img, (input_width, input_height), interpolation=cv2.INTER_LINEAR)
        
        # Normalizar a [0, 1]
        img_norm = resized.astype(np.float32) / 255.0
        
        # Convertir de HWC a NCHW
        img_transposed = img_norm.transpose(2, 0, 1)
        
        # Añadir dimensión de batch
        input_tensor = np.expand_dims(img_transposed, axis=0)
        
        return input_tensor

    def run(self):
        try:
            cap = self.setup_camera()
            if not cap.isOpened():
                print("Error: No se pudo abrir la cámara")
                return
            
            # Obtener primer frame
            _, init_frame = cap.read()
            h, w = init_frame.shape[:2]
            
            # Preallocar arrays
            self.gray = np.empty((h, w), dtype=np.uint8)
            
            # Definir ROI
            roi_y = int(h * 0.1)
            roi_height = int(h * 0.4)
            
            # Factor de escala
            scale_factor = 0.5

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
                cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY, dst=self.gray)
                
                # Aplicar ROI
                roi_frame = frame[roi_y:roi_y+roi_height, :]
                
                # Redimensionar ROI para YOLO
                small_roi = cv2.resize(roi_frame, None, fx=scale_factor, fy=scale_factor)
                
                # Detectar ojos
                boxes = []
                
                if self.use_onnx:
                    try:
                        # Usar ONNX
                        input_tensor = self.preprocess_for_onnx(small_roi)
                        outputs = self.session.run(self.output_names, {self.input_name: input_tensor})
                        
                        # Depurar salidas de ONNX
                        print(f"Forma de salida ONNX: {outputs[0].shape}")
                        
                        # Extraer detecciones (versión simplificada)
                        detections = outputs[0]
                        small_h, small_w = small_roi.shape[:2]
                        
                        for i in range(detections.shape[1]):
                            # Usar un umbral más bajo para debug
                            confidence = float(detections[0, i, 4])
                            
                            if confidence > 0.01:  # Umbral muy bajo para depuración
                                print(f"Detección ONNX: conf={confidence:.4f}")
                                
                                # Las coordenadas vienen normalizadas [0-1]
                                x1 = int(float(detections[0, i, 0]) * small_w)
                                y1 = int(float(detections[0, i, 1]) * small_h)
                                x2 = int(float(detections[0, i, 2]) * small_w)
                                y2 = int(float(detections[0, i, 3]) * small_h)
                                
                                boxes.append({
                                    'xyxy': np.array([[x1, y1, x2, y2]]),
                                    'conf': confidence,
                                    'cls': 0
                                })
                    except Exception as e:
                        print(f"Error en inferencia ONNX: {e}")
                        # Cambio automático a PyTorch en caso de error
                        if self.use_onnx:
                            print("Fallback a PyTorch para esta imagen")
                            if not hasattr(self, 'model'):
                                self.model = YOLO('best_color.pt')
                            results = self.model(small_roi, conf=0.2, verbose=False)
                            for r in results:
                                boxes = r.boxes.cpu().numpy()
                else:
                    # Usar PyTorch
                    results = self.model(small_roi, conf=0.2, verbose=False)
                    for r in results:
                        boxes = r.boxes.cpu().numpy()
                
                # Dibujar líneas de ROI
                cv2.line(self.frame_draw, (0, roi_y), (w, roi_y), (0, 255, 255), 1)
                cv2.line(self.frame_draw, (0, roi_y + roi_height), (w, roi_y + roi_height), (0, 255, 255), 1)
                
                # Procesar detecciones
                eye_regions = []
                
                if self.use_onnx:
                    # Procesar detecciones ONNX
                    for j, box in enumerate(boxes):
                        try:
                            # Ajustar coordenadas de la caja
                            x1, y1, x2, y2 = box['xyxy'][0]
                            
                            # Convertir a coordenadas de frame original
                            ex = int(x1 / scale_factor)
                            ey = int(y1 / scale_factor) + roi_y
                            ew = int((x2 - x1) / scale_factor)
                            eh = int((y2 - y1) / scale_factor)
                            
                            # Dibujar rectángulo
                            cv2.rectangle(self.frame_draw, (ex, ey), (ex+ew, ey+eh), (0, 255, 0), 1)
                            
                            # Determinar si es el primer ojo
                            is_first_eye = (j == 0)
                            
                            # Procesar región del ojo
                            if ey >= 0 and ey+eh <= h and ex >= 0 and ex+ew <= w and eh > 0 and ew > 0:
                                eye_gray = self.gray[ey:ey+eh, ex:ex+ew]
                                eye_color = self.frame_draw[ey:ey+eh, ex:ex+ew]
                                eye_regions.append((eye_gray, eye_color, ex, ey, ew, eh, is_first_eye))
                        except Exception as e:
                            print(f"Error al procesar caja ONNX: {e}")
                else:
                    # Código original para procesar cajas de PyTorch
                    sorted_boxes = sorted(boxes, key=lambda box: box.xyxy[0][0])
                    
                    for j, box in enumerate(sorted_boxes):
                        # Obtener coordenadas
                        x1_small, y1_small, x2_small, y2_small = box.xyxy[0]
                        
                        # Ajustar a imagen original
                        x1 = int(x1_small / scale_factor)
                        y1 = int(y1_small / scale_factor) + roi_y
                        x2 = int(x2_small / scale_factor)
                        y2 = int(y2_small / scale_factor) + roi_y
                        
                        # Coordenadas de caja
                        ex, ey = x1, y1
                        ew, eh = x2 - x1, y2 - y1
                        
                        # Dibujar rectángulo
                        cv2.rectangle(self.frame_draw, (ex, ey), (ex+ew, ey+eh), (0, 255, 0), 1)
                        
                        # Determinar si es el primer ojo
                        is_first_eye = (j == 0)
                        
                        # Procesar región del ojo
                        eye_gray = self.gray[ey:ey+eh, ex:ex+ew]
                        eye_color = self.frame_draw[ey:ey+eh, ex:ex+ew]
                        eye_regions.append((eye_gray, eye_color, ex, ey, ew, eh, is_first_eye))
                
                # Lista para pupilas
                pupil_positions = []
                
                # Procesar cada región de ojo
                for data in eye_regions:
                    result = self.process_eye_region(data)
                    if result:
                        cx, cy, radius, ex, ey, ew, eh, mask = result
                        
                        # Dibujar círculo
                        cv2.circle(self.frame_draw[ey:ey+eh, ex:ex+ew], (cx, cy), radius, (255, 0, 0), 1)
                        
                        # Coordenadas absolutas
                        abs_x = ex + cx
                        abs_y = ey + cy
                        
                        # Guardar posición
                        pupil_positions.append([abs_x, abs_y, data[6]])
                        
                        # Mostrar máscara
                        roi = self.frame_draw[ey:ey+eh, ex:ex+ew]
                        cv2.addWeighted(roi, 0.7, mask, 0.3, 0, roi)
                
                # Convertir y emitir
                cv2.cvtColor(self.frame_draw, cv2.COLOR_BGR2RGB, dst=self.frame_draw)
                
                # Emitir frame
                positions = pupil_positions if pupil_positions else None
                self.frame_ready.emit(self.frame_draw, fps, positions)
                
                self.frame_count += 1
                if fps > self.fps_max:
                    self.fps_max = fps
                if fps > 210:
                    self.fps_max = 0
                    
        except Exception as e:
            print(f"Error en run: {e}")
            import traceback
            traceback.print_exc()
        finally:
            cap.release()
            
    def stop(self):
        """Detiene el hilo de manera segura."""
        self.running = False
        self.wait()
        
                
class VideoWidget(QObject):
    sig_pos = Signal(list)

    def __init__(self, camera_frame, fps_label, use_onnx=False):
        super().__init__()

        self.camera_frame = camera_frame
        self.fps_label = fps_label
        self.pos_eye = []

        self.video_thread = VideoThread(use_onnx=use_onnx)
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
            
            # Procesar posiciones de pupilas
            pupils_pos = []
            if pupil_positions:
                for x, y, is_first_eye in pupil_positions:
                    eye_name = "Izquierdo" if is_first_eye else "Derecho"
                    pupils_pos.append([x, y])
                self.pos_eye = pupils_pos
                self.sig_pos.emit(self.pos_eye)

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


# Ejemplo de uso:
# Para usar PyTorch (por defecto):
# video_widget = VideoWidget(camera_frame, fps_label)

# Para probar ONNX (con fallback a PyTorch):
# video_widget = VideoWidget(camera_frame, fps_label, use_onnx=True)