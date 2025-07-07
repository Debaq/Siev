from ultralytics import YOLO
import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal, QTimer, Qt, QObject
from PySide6.QtGui import QImage, QPixmap
import torch

class VideoThread(QThread):
    frame_ready = Signal(np.ndarray, object)  # frame, fps, pupil_positions
    
    def __init__(self, camera_id=3):
        super().__init__()
        self.running = True
        self.camera_id = camera_id
        self.last_time = cv2.getTickCount()
        
        # Cargar el modelo YOLO entrenado
        print("Cargando modelo PyTorch optimizado...")
        self.model = YOLO('best_color.pt')
        
        # Optimizaciones para CPU (configuración conservadora)
        if not torch.cuda.is_available():
            # Usar solo 1 hilo para evitar sobrecarga del sistema
            torch.set_num_threads(1)
            print(f"Usando CPU con {torch.get_num_threads()} hilos")
            # Desactivar operaciones asíncronas para evitar sobrecarga
            torch.set_num_interop_threads(1)
        else:
            print("Usando GPU para inferencia")
        
        # Parámetros para detección
        self.detect_params = {
            'conf': 0.5,      # Umbral de confianza
            'iou': 0.45,      # Umbral IOU para NMS
            'verbose': False, # Sin mensajes de depuración
            'max_det': 2      # Máximo 2 detecciones (ojos)
        }
        
        # Preallocación de memoria
        self.gray = None
        self.frame_draw = None
        self.changed_nose = False

        self.threslhold = [40,3]
        self.erode = [0,0]
        self.nose_width = 0.25
        self.slider_th_pressed = False
        self.changed_prop_cap = False
        self.cap_width = 960
        self.cap_height = 540
        self.cap_fps = 120
        self.cap_try = 0
        self.cap_error = False

        # Variables para el cálculo de FPS promedio
        self.fps_values = []
        self.fps_update_interval = 1.0  # Intervalo en segundos para actualizar el FPS promedio
        self.last_fps_update_time = 0
        self.average_fps = 0
        
    def setup_camera(self):
        cap = cv2.VideoCapture(self.camera_id)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.cap_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.cap_height)
        cap.set(cv2.CAP_PROP_FPS, self.cap_fps)
        cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 3)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_BRIGHTNESS, -21)
        cap.set(cv2.CAP_PROP_CONTRAST, 50)
        return cap
    
    def set_resolution(self, resolution):
        resolution, fps = resolution.split("@")
        width, height = resolution.split("x")
        print(f"width: {width}, height: {height}, fps: {fps}")
        self.cap_width = int(width)
        self.cap_height = int(height)
        self.cap_fps = int(fps)
        self.changed_prop_cap = True

    def set_threshold(self, threshold):
        if len(threshold) != 2:
            print("Error: Se requieren dos valores de threshold")
            return
        if threshold[1] == 0:
            self.threslhold[0] = threshold[0]
        elif threshold[1] == 1:
            self.threslhold[1] = threshold[0]
        elif threshold[1] == 2:
            self.erode[0] = threshold[0]
        elif threshold[1] == 3:
            self.erode[1] = threshold[0]
        elif threshold[1] == 4:
            self.nose_width = threshold[0]/100
            self.changed_nose = True
        else:    
            print(f"Error: Índice de threshold incorrecto: {threshold[1]}")
            return

    def set_color(self, text_label, value):
        cap = self.cap
        if text_label == "Contrast":
            contrast = value
            cap.set(cv2.CAP_PROP_CONTRAST, contrast)
        elif text_label == "Brightness:":
            brightness = value
            cap.set(cv2.CAP_PROP_BRIGHTNESS, brightness)

    def process_eye_region(self, data):
        try:
            eye_gray, ex, ey, ew, eh, is_first_eye = data
            
            # Usar threshold diferente según el ojo
            threshold_value = self.threslhold[0] if is_first_eye else self.threslhold[1]
            _, thresh = cv2.threshold(eye_gray, threshold_value, 255, cv2.THRESH_BINARY_INV)
            
            # aplicar erosión
            erode_value = self.erode[0] if is_first_eye else self.erode[1]
            kernel = np.ones((2, 2), np.uint8)  # Ajusta el tamaño según necesites
            thresh_eroded = cv2.erode(thresh, kernel, iterations=erode_value)
        
            # Aplicar dilatación después de la erosión
            dilate_kernel_size = 3
            dilate_iterations = 1
            dilate_kernel = np.ones((dilate_kernel_size, dilate_kernel_size), np.uint8)
            thresh_processed = cv2.dilate(thresh_eroded, dilate_kernel, iterations=dilate_iterations)
        
            # Crear una máscara en color para visualización
            mask = cv2.cvtColor(thresh_processed, cv2.COLOR_GRAY2BGR)
        
            # Encontrar contornos (solo externos para mayor velocidad)
            contours, _ = cv2.findContours(thresh_processed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return None
            
            # Ordenar contornos solo si hay más de uno
            if len(contours) > 1:
                contours = sorted(contours, key=lambda x: cv2.contourArea(x), reverse=True)
                
            # Calcular círculo mínimo para el contorno más grande (pupila)
            (cx, cy), radius = cv2.minEnclosingCircle(contours[0])
            return (int(cx), int(cy), int(radius), ex, ey, ew, eh, mask)
                
        except Exception as e:
            print(f"Error en process_eye_region: {e}")
            return None
        
    def pre_loop(self):
        if self.cap_error:
            print("Error: No se pudo abrir la cámara no se puede continuar")
            return
        # Inicializar la cámara
        self.cap = self.setup_camera()
        if not self.cap.isOpened():
            print("Error: No se pudo abrir la cámara")
            self.cap.release()
            self.pre_loop()
            self.cap_try += 1
            if self.cap_try > 5:
                print("Error: No se pudo abrir la cámara se intentó 5 veces")
                self.cap_error = True
                return

        # Obtener primer frame para preallocación
        _, init_frame = self.cap.read()
        h, w = init_frame.shape[:2]

        new_h = int(h - (h*0.4))
        # Preallocar arrays
        self.gray = np.empty((new_h, w), dtype=np.uint8)   

        # Definir ROI fija
        roi_y = int(h * 0.1)
        roi_height = int(h * 0.4)

        # Definir ROIs para ojos y nariz
        roi_nose = int(w * self.nose_width)
        eyes = w - roi_nose
        roi_eye_width = int(eyes/2)
        
        # Variables para mostrar FPS en la imagen
        lbl_fps_position = (w - 45, 15)  # (desde la izquierda, desde arriba)

        return h, new_h, w, roi_y, roi_height, roi_eye_width,roi_nose, lbl_fps_position
    
    """from dataclasses import dataclass

@dataclass
class LayoutConfig:
    height: int
    new_height: int
    width: int
    roi_y: int
    roi_height: int
    roi_eye_width: int
    roi_nose: int
    lbl_fps_position: tuple

def pre_loop(self):
    # Tu lógica actual
    return LayoutConfig(h, new_h, w, roi_y, roi_height, roi_eye_width, roi_nose, lbl_fps_position)

# En run
layout = self.pre_loop()
# Acceder a los valores como layout.height, layout.roi_y, etc."""

    def run(self):
        try:
            h, new_h, w, roi_y, roi_height, roi_eye_width, roi_nose, lbl_fps_position = self.pre_loop()
            
            # Factor de escala para reducir la resolución
            scale_factor = 0.5
            # Variable para controlar la frecuencia de detección
            detection_counter = 0 # Contador de frames
            detection_frequency = 4  # Detectar cada N frames
            last_boxes = []  # Almacenar las últimas cajas detectadas
            # Variables para FPS label
            lbl_fps_font = cv2.FONT_HERSHEY_SIMPLEX
            lbl_fps_scale = 0.5
            lbl_fpt_color = (248, 243, 43)  
            lbl_fps_width = 1
            lbl_fps_typeline = cv2.LINE_AA

            while self.running:
                if self.changed_prop_cap:
                    h, new_h, w, roi_y, roi_height, roi_eye_width, roi_nose,lbl_fps_position = self.pre_loop()
                    self.changed_prop_cap = False

                ret, frame = self.cap.read()
                if not ret:
                    continue
                
                # Calcular FPS instantáneo
                current_time = cv2.getTickCount()
                instantaneous_fps = cv2.getTickFrequency() / (current_time - self.last_time)
                self.last_time = current_time

                # Añadir al arreglo de valores FPS
                self.fps_values.append(instantaneous_fps)

                # Verificar si es tiempo de actualizar el FPS promedio
                current_time_seconds = current_time / cv2.getTickFrequency()
                if current_time_seconds - self.last_fps_update_time >= self.fps_update_interval:
                    # Calcular promedio
                    if self.fps_values:
                        self.average_fps = sum(self.fps_values) / len(self.fps_values)
                        self.fps_values = []  # Reiniciar la lista
                    
                    # Actualizar el último tiempo de actualización
                    self.last_fps_update_time = current_time_seconds

                # Usar el FPS promedio para mostrar en pantalla (en lugar del instantáneo)
                fps_to_display = self.average_fps

                
                # Crear los ROIs
                if self.changed_nose:
                    roi_nose = int(w * self.nose_width)
                    eyes = w - roi_nose
                    roi_eye_width = int(eyes/2)
                    self.changed_nose = False

                roi_right_eye = frame[roi_y:roi_y+roi_height, :roi_eye_width]
                roi_left_eye = frame[roi_y:roi_y+roi_height, roi_eye_width+roi_nose:]

                # Verificar que los ROIs son válidos (no vacíos)
                if roi_right_eye.size == 0 or roi_left_eye.size == 0:
                    print("Error: ROIs vacíos")
                    return frame  # Devolver el frame original

                # Unir horizontalmente
                combined_roi = np.hstack((roi_right_eye, roi_left_eye))

                # Obtener dimensiones actuales
                current_width = combined_roi.shape[1]
                current_height = combined_roi.shape[0]

                # Calcular la nueva altura manteniendo la proporción
                new_width = w
                new_height = int((current_height * new_width) / current_width)

                # Asegurarse de que la altura no exceda el marco final
                if new_height > new_h:
                    # Si la altura es mayor que h, ajustar el ancho manteniendo la proporción
                    new_height = new_h
                    new_width = int((current_width * new_height) / current_height)

                # Redimensionar
                resized_combined = cv2.resize(combined_roi, (new_width, new_height))

                # Crear un marco vacío de hxw
                #h_new = int(h-(h*0.3))
                #h_new = h

                final_frame = np.zeros((new_h, w, 3), dtype=np.uint8)

                # Calcular la posición para centrar el ROI (tanto horizontal como vertical)
                y_offset = (new_h - new_height) // 2
                x_offset = (w - new_width) // 2

                # Colocar el ROI combinado en el centro del marco
                final_frame[y_offset:y_offset+new_height, x_offset:x_offset+new_width] = resized_combined

                # Convertir a gris para procesamiento de pupila
                cv2.cvtColor(final_frame, cv2.COLOR_BGR2GRAY, dst=self.gray)

                # Calcular coordenadas de ROI en el marco final
                y_start = y_offset
                y_end = y_offset + new_height
                x_start = x_offset
                x_end = x_offset + new_width

                # Crear un ROI que solo contenga la imagen combinada
                roi_frame = final_frame[y_start:y_end, x_start:x_end]

                # Variables para almacenar las cajas detectadas
                boxes = []
                
                # Ejecutar detección solo cada N frames para ahorrar CPU
                if detection_counter % detection_frequency == 0:
                    # Redimensionar ROI para YOLO
                    small_roi = cv2.resize(roi_frame, None, fx=scale_factor, fy=scale_factor)
                    
                    # Detectar ojos con YOLO en la ROI reducida
                    with torch.no_grad():  # Desactivar gradientes para ahorrar memoria
                        results = self.model(small_roi, **self.detect_params)
                    
                    for r in results:
                        boxes = r.boxes.cpu().numpy()
                    
                    # Guardar las cajas para los frames intermedios
                    if len(boxes) > 0:
                        last_boxes = boxes
                else:
                    # Usar las últimas cajas detectadas
                    boxes = last_boxes
                
                # Incrementar contador de frames
                detection_counter += 1
                
                # Procesar detecciones
                eye_regions = []
                if len(boxes) > 0:
                    # Ordenar cajas por coordenada X (izquierda a derecha)
                    sorted_boxes = sorted(boxes, key=lambda box: box.xyxy[0][0])
                    
                    for j, box in enumerate(sorted_boxes):
                        # Obtener coordenadas (xmin, ymin, xmax, ymax) en la imagen reducida
                        x1_small, y1_small, x2_small, y2_small = box.xyxy[0]
                        
                        # Ajustar coordenadas a la imagen original
                        x1 = int(x1_small / scale_factor)
                        y1 = int(y1_small / scale_factor) + y_offset
                        x2 = int(x2_small / scale_factor)
                        y2 = int(y2_small / scale_factor) + y_offset
                        
                        # Convertir a enteros para las coordenadas de la caja
                        ex, ey = x1, y1
                        ew, eh = x2 - x1, y2 - y1
                        
                        # Dibujar rectángulo en la imagen original si se activa el slider
                        if self.slider_th_pressed:
                            cv2.rectangle(final_frame, (ex, ey), (ex+ew, ey+eh), (0, 255, 0), 1)
                        
                        # Obtener el punto medio horizontal de la imagen
                        image_center_x = w / 2

                        # Determinar si es el ojo derecho (aparece en la mitad izquierda de la imagen)
                        # El punto medio del ojo está a la izquierda del centro de la imagen
                        eye_center_x = ex + (ew / 2)
                        is_right_eye = eye_center_x < image_center_x

                        # Procesar región del ojo para detectar pupila
                        # Verificar límites para evitar errores
                        if ey >= 0 and ey+eh <= h and ex >= 0 and ex+ew <= w and eh > 0 and ew > 0:
                            eye_gray = self.gray[ey:ey+eh, ex:ex+ew]
                            eye_regions.append((eye_gray, ex, ey, ew, eh, is_right_eye))

                # Lista para guardar posiciones de pupilas [x, y, is_right_eye]
                pupil_positions = [None,None]
                
                # Procesar cada región de ojo para detectar pupila
                for data in eye_regions:
                    result = self.process_eye_region(data)
                    if result:
                        cx, cy, radius, ex, ey, ew, eh, mask = result

                        # Opcionalmente, mostrar la máscara de threshold
                        if self.slider_th_pressed:
                            roi = final_frame[ey:ey+eh, ex:ex+ew]
                            cv2.addWeighted(roi, 1, mask, 1, 0, roi) # addWeighted(image, alpha, mask, beta, gamma)

                        # Dibujar círculo de la pupila
                        #color =  (0,0,255) if data[5] else (255,0,0)
                        color = (0, 255, 0)
                        cv2.circle(final_frame[ey:ey+eh, ex:ex+ew], (cx, cy), radius, color, 1)
                        # Calcular coordenadas absolutas de la pupila
                        abs_x = ex + cx
                        abs_y = ey + cy
                        # Dibujar cruces en la pupila
                        longitud_cruz = 5
                        punto_inicio_horizontal = (abs_x - longitud_cruz, abs_y)
                        punto_fin_horizontal = (abs_x + longitud_cruz, abs_y)
                        cv2.line(final_frame, punto_inicio_horizontal, punto_fin_horizontal, color, 1)

                        # Dibujar la línea vertical
                        punto_inicio_vertical = (abs_x, abs_y - longitud_cruz)
                        punto_fin_vertical = (abs_x, abs_y + longitud_cruz)
                        cv2.line(final_frame, punto_inicio_vertical, punto_fin_vertical, color, 1)
                        
                        # Guardar posición de la pupila con indicador de ojo izquierdo/derecho
                        abs_y = abs_y * -1
                        if data[5]:
                            pupil_positions[0] = [abs_x, abs_y]  # data[5] es is_right_eye
                        else:
                            pupil_positions[1] = [abs_x, abs_y]  # data[5] es is_right_eye

                # Convertir y emitir
                cv2.cvtColor(final_frame, cv2.COLOR_BGR2RGB, dst=final_frame)
                # Agregar texto a la imagen
                cv2.putText(final_frame, f"{fps_to_display:.1f}", lbl_fps_position, 
                            lbl_fps_font, lbl_fps_scale, lbl_fpt_color, 
                            lbl_fps_width, lbl_fps_typeline)

                # Emitir frame, fps y posiciones de pupilas (None si no se encontraron)
                self.frame_ready.emit(final_frame, pupil_positions)
                    
        except Exception as e:
            print(f"Error en run: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.cap.release()
            
    def stop(self):
        """Detiene el hilo de manera segura."""
        self.running = False  # Indica que el hilo debe detenerse
        self.wait()  # Espera a que el hilo termine completamente
                
class VideoWidget(QObject):
    sig_pos = Signal(list)

    def __init__(self, camera_frame, sliders, cbres):
        super().__init__()

        self.cbres = cbres        
        self.sliders = sliders
        self.resolution_changed()
        self.sliders_changed()
        self.camera_frame = camera_frame
        self.pos_eye = []

        self.video_thread = VideoThread()
        self.video_thread.frame_ready.connect(self.update_frame)
                
        self.current_fps = 0
        self.video_thread.start(QThread.HighPriority)

    def set_video_color(self, text_label, value):
        self.video_thread.set_color(text_label, value)

    def resolution_changed(self):
        self.cbres.currentIndexChanged.connect(lambda: self.video_thread.set_resolution(self.cbres.currentText()))

    def sliders_changed(self):
        for i, slider in enumerate(self.sliders):
            slider.valueChanged.connect(lambda value, i=i: self.video_thread.set_threshold([value, i]))
            slider.sliderPressed.connect(lambda: setattr(self.video_thread, 'slider_th_pressed', True))
            slider.sliderReleased.connect(lambda: setattr(self.video_thread, 'slider_th_pressed', False))
    
    def update_frame(self, frame, pupil_positions):
        try:          
            # Actualizar la imagen
            if frame is not None and frame.size > 0:
                if not frame.flags['C_CONTIGUOUS']:
                    frame = np.ascontiguousarray(frame)
                height, width = frame.shape[:2]
                bytes_per_line = 3 * width
                
                image = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
                if not image.isNull():
                    self.camera_frame.setPixmap(QPixmap.fromImage(image))
            

            # Crear lista de posiciones siempre con dos elementos [izquierdo, derecho]
            self.pos_eye = pupil_positions
            
            # Emitir la señal con las posiciones
            self.sig_pos.emit(self.pos_eye)

        except Exception as e:
            print(f"Error en update_frame: {e}")
    
  
    def cleanup(self):
        try:
            self.video_thread.stop()
        except Exception as e:
            print(f"Error en cleanup: {e}")