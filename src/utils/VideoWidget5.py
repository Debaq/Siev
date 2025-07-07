import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal, QTimer, Qt, QObject
from PySide6.QtGui import QImage, QPixmap
import onnxruntime as ort

class VideoThread(QThread):
    frame_ready = Signal(np.ndarray, float, object)  # frame, fps, pupil_positions
    
    def __init__(self, camera_id=2):
        super().__init__()
        self.running = True
        self.camera_id = camera_id
        self.frame_count = 0
        self.last_time = cv2.getTickCount()
        self.fps_max = 0
        
        # Cargar el modelo ONNX
        print("Cargando modelo ONNX...")
        self.session = ort.InferenceSession("best_color.onnx", 
                                          providers=['CPUExecutionProvider'])
        
        # Obtener nombres de las capas de entrada y salida
        self.input_name = self.session.get_inputs()[0].name
        self.output_names = [output.name for output in self.session.get_outputs()]
        
        # Obtener dimensiones esperadas por el modelo
        self.input_shape = self.session.get_inputs()[0].shape
        self.model_height = self.input_shape[2]
        self.model_width = self.input_shape[3]
        
        print(f"Modelo ONNX cargado. Entrada: {self.input_name}")
        print(f"Dimensiones de entrada esperadas: {self.model_height}x{self.model_width}")
        print(f"Salidas: {self.output_names}")
        
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
    
    def preprocess_for_onnx(self, img):
        """Preprocesa la imagen para pasarla al modelo ONNX"""
        # Redimensionar a la resolución esperada por el modelo
        resized = cv2.resize(img, (self.model_width, self.model_height))
        
        # Convertir a float32 y normalizar a [0, 1]
        img_norm = resized.astype(np.float32) / 255.0
        
        # Convertir de HWC (Height, Width, Channels) a NCHW (N, Channels, Height, Width)
        img_transposed = img_norm.transpose(2, 0, 1)
        
        # Añadir dimensión de batch
        input_tensor = np.expand_dims(img_transposed, axis=0)
        
        return input_tensor
    
    def process_onnx_output(self, outputs, original_size, conf_threshold=0.05):
        """Procesa las salidas del modelo ONNX para obtener detecciones de ojos"""
        detections = outputs[0]  # Primera salida contiene las detecciones
        orig_h, orig_w = original_size
        
        print(f"Forma de salida ONNX: {detections.shape}")
        
        # Basado en los logs, parece que los datos tienen este formato:
        # [x, y, width, height, confidence] para cada detección
        
        boxes = []
        
        # Para este modelo específico vamos a probar con transposición
        if detections.shape[1] == 5 and detections.shape[2] > 10:
            # Transponer para tener (1, n_detections, 5)
            detections = np.transpose(detections, (0, 2, 1))
            print(f"Forma transpuesta: {detections.shape}")
        
        # Umbral de confianza bajo para pruebas
        conf_threshold = 0.0005  # Muy bajo para detectar algo
        
        for i in range(min(detections.shape[1], 100)):  # Limitar a 100 para evitar bucles muy largos
            # Obtener datos de muestra para depuración
            sample = detections[0, i, :]
            
            # Si la muestra tiene al menos 5 valores
            if len(sample) >= 5:
                # La última posición (índice 4) parece ser la confianza
                # Based on the log showing 5.5363774e-04 as a value
                confidence = float(sample[4])
                
                # Imprimir para depuración si supera un umbral mínimo
                if confidence > 0.0001:  # Cualquier valor no completamente cero
                    print(f"Muestra {i}: {sample[:5]}")
                    print(f"Confianza: {confidence:.6f}")
                
                # Si la confianza supera nuestro umbral
                if confidence >= conf_threshold:
                    # Los primeros 4 valores parecen ser coordenadas absolutas
                    x_center, y_center, width, height = sample[:4]
                    
                    # Si son valores muy grandes, pueden ser coordenadas absolutas
                    # en la escala del modelo de entrada (320x320)
                    is_absolute = False
                    if max(x_center, y_center, width, height) > 10:  # Valores típicamente mayores que 10
                        is_absolute = True
                    
                    if is_absolute:
                        # Convertir de coordenadas absolutas a relativas al tamaño de la imagen de entrada
                        scale_x = orig_w / self.model_width
                        scale_y = orig_h / self.model_height
                        
                        # Si es formato centro+ancho+alto
                        if width < self.model_width and height < self.model_height:
                            # Convertir de centro+ancho+alto a esquinas (x1,y1,x2,y2)
                            x1 = int((x_center - width/2) * scale_x)
                            y1 = int((y_center - height/2) * scale_y)
                            x2 = int((x_center + width/2) * scale_x)
                            y2 = int((y_center + height/2) * scale_y)
                        else:
                            # Posible formato x1,y1,x2,y2 directamente
                            x1 = int(x_center * scale_x)
                            y1 = int(y_center * scale_y)
                            x2 = int(width * scale_x)
                            y2 = int(height * scale_y)
                    else:
                        # Son valores normalizados [0,1]
                        # Si es formato centro+ancho+alto
                        x1 = int((x_center - width/2) * orig_w)
                        y1 = int((y_center - height/2) * orig_h)
                        x2 = int((x_center + width/2) * orig_w)
                        y2 = int((y_center + height/2) * orig_h)
                    
                    # Verificar que las coordenadas sean sensatas
                    if x1 < x2 and y1 < y2 and x1 >= 0 and y1 >= 0 and x2 <= orig_w and y2 <= orig_h:
                        boxes.append({
                            'xyxy': np.array([[x1, y1, x2, y2]]),
                            'conf': confidence,
                            'cls': 0
                        })
        
        # Una alternativa que podemos probar: usar la API de YOLO para procesar las salidas
        # si después de implementar esto sigue sin funcionar
        
        # Si no encontramos cajas, intentar un enfoque alternativo (solo x1,y1,x2,y2)
        if not boxes:
            print("Intentando enfoque alternativo...")
            for i in range(min(detections.shape[1], 100)):
                sample = detections[0, i, :]
                if len(sample) >= 5:
                    confidence = float(sample[4])
                    
                    if confidence >= conf_threshold:
                        # Probar asumiendo directamente x1,y1,x2,y2
                        x1, y1, x2, y2 = sample[:4]
                        
                        # Escalar a tamaño original
                        scale_x = orig_w / self.model_width
                        scale_y = orig_h / self.model_height
                        
                        x1 = int(x1 * scale_x)
                        y1 = int(y1 * scale_y)
                        x2 = int(x2 * scale_y)
                        y2 = int(y2 * scale_y)
                        
                        if x1 < x2 and y1 < y2:
                            boxes.append({
                                'xyxy': np.array([[x1, y1, x2, y2]]),
                                'conf': confidence,
                                'cls': 0
                            })
        
        # Ordenar cajas por coordenada X
        boxes = sorted(boxes, key=lambda box: box['xyxy'][0][0])
        
        print(f"Se encontraron {len(boxes)} cajas válidas")
        return boxes

    def run(self):
        try:
            cap = self.setup_camera()
            if not cap.isOpened():
                print("Error: No se pudo abrir la cámara")
                return
            
            # Obtener primer frame para preallocación
            _, init_frame = cap.read()
            h, w = init_frame.shape[:2]
            
            # Preallocar arrays
            self.gray = np.empty((h, w), dtype=np.uint8)
            
            # Definir ROI fija
            roi_y = int(h * 0.1)
            roi_height = int(h * 0.4)
            
            # Factor de escala para reducir la resolución
            scale_factor = 0.15

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
                
                # Redimensionar ROI para visualización y detección
                small_roi = cv2.resize(roi_frame, None, fx=scale_factor, fy=scale_factor)
                small_roi_size = small_roi.shape[:2]  # (height, width)
                
                # Preprocesar para ONNX (redimensionar a las dimensiones esperadas)
                input_tensor = self.preprocess_for_onnx(small_roi)
                
                # Inferencia con ONNX
                outputs = self.session.run(self.output_names, {self.input_name: input_tensor})
                
                # Procesar salidas ajustándolas a las dimensiones de small_roi
                boxes = self.process_onnx_output(outputs, small_roi_size, conf_threshold=0.05)
                
                # Dibujar líneas de ROI
                cv2.line(self.frame_draw, (0, roi_y), (w, roi_y), (0, 255, 255), 1)
                cv2.line(self.frame_draw, (0, roi_y + roi_height), (w, roi_y + roi_height), (0, 255, 255), 1)
                
                # Procesar detecciones
                eye_regions = []
                for j, box in enumerate(boxes):
                    # Obtener coordenadas en la ROI reducida
                    x1, y1, x2, y2 = box['xyxy'][0]
                    
                    # Ajustar coordenadas a la imagen original
                    ex = int(x1 / scale_factor)
                    ey = int(y1 / scale_factor) + roi_y
                    ew = int((x2 - x1) / scale_factor)
                    eh = int((y2 - y1) / scale_factor)
                    
                    # Dibujar rectángulo en la imagen original
                    cv2.rectangle(self.frame_draw, (ex, ey), (ex+ew, ey+eh), (0, 255, 0), 1)
                    
                    # Determinar si es el primer ojo (más a la izquierda)
                    is_first_eye = (j == 0)
                    
                    # Procesar región del ojo para detectar pupila
                    if 0 <= ey < h and 0 <= ey+eh <= h and 0 <= ex < w and 0 <= ex+ew <= w:
                        eye_gray = self.gray[ey:ey+eh, ex:ex+ew]
                        eye_color = self.frame_draw[ey:ey+eh, ex:ex+ew]
                        
                        if eye_gray.size > 0 and eye_color.size > 0:
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
            import traceback
            traceback.print_exc()
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