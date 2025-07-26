from ultralytics import YOLO
import cv2
import numpy as np
import torch
import multiprocessing as mp
from multiprocessing import Value, Array
import time
import ctypes
from utils.path_utils import get_model_file_path
from utils.video.simulated_box import SimulatedBox


class VideoProcesses:
    def __init__(self, camera_id=2, cap_width=960, 
                 cap_height=540, cap_fps=120, 
                 brightness=-21, contrast=50):
        # Configuración de la cámara
        self.camera_id = camera_id
        self.cap_width = cap_width
        self.cap_height = cap_height
        self.cap_fps = cap_fps
        
        # Variables compartidas
        self.running = Value(ctypes.c_bool, True)
        self.frame_queue = mp.Queue(maxsize=2)
        self.detection_queue = mp.Queue(maxsize=2)
        self.result_queue = mp.Queue(maxsize=2)
        
        # Configuración de cámara compartida
        self.nose_width = Value(ctypes.c_float, 0.25)
        self.eye_heigh = Value(ctypes.c_float, 0.25)

        self.changed_nose = Value(ctypes.c_bool, False)
        self.changed_eye_height = Value(ctypes.c_bool, False)

        self.threslhold = Array('i', [0, 0])
        self.erode = Array('i', [0, 0])
        self.cap_error = Value(ctypes.c_bool, False)
        self.slider_th_pressed = Value(ctypes.c_bool, False)
        
        # Variables compartidas para control de color
        self.brightness = Value(ctypes.c_int, brightness) 
        self.contrast = Value(ctypes.c_int, contrast)    
        self.color_changed = Value(ctypes.c_bool, False)  
        
        # Variables para toggle YOLO/ROI fija
        self.use_yolo = Value(ctypes.c_bool, True)  
        self.fixed_roi_updated = Value(ctypes.c_bool, False)  
    
        # [x1, y1, x2, y2] para ojo derecho e izquierdo
        roi_right_default = [0, int(cap_height * 0.1), int(cap_width * 0.4), int(cap_height * 0.5)]
        roi_left_default = [int(cap_width * 0.6), int(cap_height * 0.1), 
                            int(cap_width), int(cap_height * 0.5)]
        
        # Usar Arrays compartidos para las ROIs fijas
        self.fixed_roi_right = Array('i', roi_right_default)
        self.fixed_roi_left = Array('i', roi_left_default)

        # Procesos
        self.capture_process = None
        self.detection_process = None
        self.processing_process = None
        
    
    def setup_camera(self):
        """Configura la cámara con los parámetros actuales"""
        print(f"Configurando cámara {self.camera_id} a {self.cap_width}x{self.cap_height}@{self.cap_fps}")
        
        cap = cv2.VideoCapture(self.camera_id)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.cap_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.cap_height)
        cap.set(cv2.CAP_PROP_FPS, self.cap_fps)
        cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 3)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        # Aplicar configuraciones de color actuales
        cap.set(cv2.CAP_PROP_BRIGHTNESS, self.brightness.value)
        cap.set(cv2.CAP_PROP_CONTRAST, self.contrast.value)
        
        # Resto de configuraciones
        return cap
    
    def capture_worker(self):
        """Proceso dedicado exclusivamente a capturar frames"""
        print("Iniciando proceso de captura")
        cap_try = 0
        
        # Intentar abrir la cámara con un número limitado de intentos
        while cap_try < 5 and not self.cap_error.value:
            cap = self.setup_camera()
            if cap.isOpened():
                break
            cap.release()
            cap_try += 1
            time.sleep(0.5)
        
        if not cap.isOpened():
            print("Error: No se pudo abrir la cámara después de 5 intentos")
            self.cap_error.value = True
            return
        
        # Obtener primer frame para calcular dimensiones
        ret, init_frame = cap.read()
        if not ret:
            print("Error: No se pudo leer el primer frame")
            self.cap_error.value = True
            cap.release()
            return
            
        h, w = init_frame.shape[:2]
        frame_info = {
            'height': h,
            'width': w,
            'roi_y': int(h * 0.1),
            'roi_height': int(h * 0.4),
            'new_height': int(h - (h*0.4))
        }
        
        # Enviar info del frame al proceso de detección
        self.detection_queue.put(frame_info)
        
        last_time = time.time()
        fps_values = []
        fps_avg = 0
        
        try:
            # Bucle principal de captura optimizado para rendimiento
            while self.running.value:
                if self.color_changed.value:
                    cap.set(cv2.CAP_PROP_BRIGHTNESS, self.brightness.value)
                    cap.set(cv2.CAP_PROP_CONTRAST, self.contrast.value)
                    self.color_changed.value = False
                
                ret, frame = cap.read()
                if not ret:
                    # Solo una verificación simple sin esperas adicionales
                    continue
                
                # Calcular FPS - código optimizado sin verificaciones adicionales
                current_time = time.time()
                instantaneous_fps = 1.0 / max(current_time - last_time, 0.001)  # Evita división por cero
                last_time = current_time
                
                fps_values.append(instantaneous_fps)
                if len(fps_values) >= 30:
                    fps_avg = sum(fps_values) / len(fps_values)
                    fps_values = []
                
                # Poner el frame en la cola solo si no está llena - sin bloqueos
                if not self.frame_queue.full():
                    self.frame_queue.put((frame, fps_avg))
        except Exception as e:
            print(f"Error en proceso de captura: {e}")
        finally:
            # Siempre asegurar la liberación de la cámara
            cap.release()
            print("Proceso de captura finalizado")
    
    def detection_worker(self):
        """Proceso dedicado a detectar ojos con YOLO"""
        print("Iniciando proceso de detección")
        
        # Cargar modelo YOLO
        model_path = get_model_file_path('siev_vng_r01.pt')
        model = YOLO(model_path)
        
        # Optimizaciones para CPU
        if not torch.cuda.is_available():
            torch.set_num_threads(1)
            print(f"Usando CPU con {torch.get_num_threads()} hilos")
            torch.set_num_interop_threads(1)
        else:
            print("Usando GPU para inferencia")
        # Parámetros para detección
        detect_params = {
            'conf': 0.5,      # Umbral de confianza
            'iou': 0.45,      # Umbral IOU para NMS
            'verbose': False, # Sin mensajes de depuración
            'max_det': 2      # Máximo 2 detecciones (ojos)
        }
        
        # Esperar la información del frame
        frame_info = self.detection_queue.get()
        
        # Variables para controlar frecuencia de detección
        detection_counter = 0
        detection_frequency = 4
        last_boxes = []
        scale_factor = 0.5
        
        while self.running.value:
            if self.frame_queue.empty():
                time.sleep(0.001)
                continue
            
            frame, fps = self.frame_queue.get()
            h, w = frame.shape[:2]
            
            # Actualizar dimensiones ROI si cambió el ancho de nariz
            if self.changed_nose.value:
                self.changed_nose.value = False
                roi_nose = int(w * self.nose_width.value)
            else:
                roi_nose = int(w * self.nose_width.value)


            if self.changed_eye_height.value:
                self.changed_eye_height.value = False
                roi_nose_height = int(h * self.eye_heigh.value)
            else:
                roi_nose_height = int(h * self.eye_heigh.value)


            
            # Extraer ROIs
            roi_y = frame_info['roi_y']
            roi_height = frame_info['roi_height']
            eyes_width = w - roi_nose
            roi_eye_width = int(eyes_width / 2)


            
            roi_right_eye = frame[roi_y:roi_y+roi_height, :roi_eye_width]
            roi_left_eye = frame[roi_y:roi_y+roi_height, roi_eye_width+roi_nose:]
            
            #roi_right_eye = frame[0:roi_y+roi_height, :roi_eye_width]
            #roi_left_eye = frame[0:roi_y+roi_height, roi_eye_width+roi_nose:]

            # Verificar ROIs
            if roi_right_eye.size == 0 or roi_left_eye.size == 0:
                continue
            
            # Unir horizontalmente
            combined_roi = np.hstack((roi_right_eye, roi_left_eye))
            
            # Redimensionar para mantener proporción
            current_width = combined_roi.shape[1]
            current_height = combined_roi.shape[0]
            new_width = w
            new_height = int((current_height * new_width) / current_width)
            new_h = frame_info['new_height']
            
            if new_height > new_h:
                new_height = new_h
                new_width = int((current_width * new_height) / current_height)
            
            resized_combined = cv2.resize(combined_roi, (new_width, new_height))
            
            # Crear frame final
            final_frame = np.zeros((new_h, w, 3), dtype=np.uint8)
            y_offset = (new_h - new_height) // 2
            x_offset = (w - new_width) // 2
            final_frame[y_offset:y_offset+new_height, x_offset:x_offset+new_width] = resized_combined


            # Convertir a gris para detección
            gray = cv2.cvtColor(final_frame, cv2.COLOR_BGR2GRAY)
            
            # Solo detectar cada N frames
            if self.use_yolo.value:
                if detection_counter % detection_frequency == 0:
                    roi_frame = final_frame[y_offset:y_offset+new_height, x_offset:x_offset+new_width]
                    small_roi = cv2.resize(roi_frame, None, fx=scale_factor, fy=scale_factor)
                    
                    with torch.no_grad():
                        results = model(small_roi, **detect_params)
                    
                    boxes = []
                    for r in results:
                        boxes = r.boxes.cpu().numpy()
                    
                    if len(boxes) > 0:
                        last_boxes = boxes

                        if len(boxes) >= 2:  # Si se detectaron ambos ojos
                            sorted_boxes = sorted(boxes, key=lambda box: box.xyxy[0][0])
                            
                            # Convertir coordenadas a tamaño original
                            for i, box in enumerate(sorted_boxes[:2]):  # Solo los primeros 2 ojos
                                x1, y1, x2, y2 = map(int, box.xyxy[0])
                                # Escalar a coordenadas de imagen completa
                                x1 = int(x1 / scale_factor) + x_offset
                                y1 = int(y1 / scale_factor) + y_offset
                                x2 = int(x2 / scale_factor) + x_offset
                                y2 = int(y2 / scale_factor) + y_offset
                                
                                # Guardar en ROIs fijas (derecho = 0, izquierdo = 1)
                                if i == 0:  # Ojo derecho (el que aparece más a la izquierda)
                                    self.fixed_roi_right[0] = x1
                                    self.fixed_roi_right[1] = y1
                                    self.fixed_roi_right[2] = x2
                                    self.fixed_roi_right[3] = y2
                                else:  # Ojo izquierdo
                                    self.fixed_roi_left[0] = x1
                                    self.fixed_roi_left[1] = y1
                                    self.fixed_roi_left[2] = x2
                                    self.fixed_roi_left[3] = y2
                else:
                    boxes = last_boxes
            else:
                # MODO ROI FIJA: Crear "boxes" sintéticas desde las ROIs fijas
                boxes = []
                
                # Convertir ROIs fijas a formato compatible con el resto del código
                # Convertir de coordenadas globales a coordenadas de escala
                # Ojo derecho
                x1_r = (self.fixed_roi_right[0] - x_offset) * scale_factor
                y1_r = (self.fixed_roi_right[1] - y_offset) * scale_factor
                x2_r = (self.fixed_roi_right[2] - x_offset) * scale_factor
                y2_r = (self.fixed_roi_right[3] - y_offset) * scale_factor
                
                # Ojo izquierdo
                x1_l = (self.fixed_roi_left[0] - x_offset) * scale_factor
                y1_l = (self.fixed_roi_left[1] - y_offset) * scale_factor
                x2_l = (self.fixed_roi_left[2] - x_offset) * scale_factor
                y2_l = (self.fixed_roi_left[3] - y_offset) * scale_factor
                
                # Crear "boxes" simuladas
                box_right = SimulatedBox(x1_r, y1_r, x2_r, y2_r)
                box_left = SimulatedBox(x1_l, y1_l, x2_l, y2_l)
                
                # Añadir a la lista de boxes (derecho primero, luego izquierdo)
                boxes = [box_right, box_left]
        

            detection_counter += 1
            
            # Pasar datos al proceso de procesamiento
            detection_data = {
                'frame': final_frame,
                'gray': gray,
                'boxes': boxes,
                'y_offset': y_offset,
                'scale_factor': scale_factor,
                'fps': fps,
                'w': w,
                'h': new_h
            }
            
            if not self.result_queue.full():
                self.result_queue.put(detection_data)
        
        print("Proceso de detección finalizado")
    
    def processing_worker(self):
        """Proceso para procesar resultados y detectar pupilas"""
        print("Iniciando proceso de procesamiento")

        while self.running.value:
            if self.result_queue.empty():
                time.sleep(0.001)
                continue
            
            data = self.result_queue.get()
            final_frame = data['frame']
            gray = data['gray']
            boxes = data['boxes']
            y_offset = data['y_offset']
            scale_factor = data['scale_factor']
            fps = data['fps']
            w = data['w']
            h = data['h']
            # Obtener timestamp para cálculo de velocidad
            timestamp = cv2.getTickCount() / cv2.getTickFrequency()
            
            # Procesar detecciones
            eye_regions = []
            if len(boxes) > 0:
                # Ordenar cajas por coordenada X
                sorted_boxes = sorted(boxes, key=lambda box: box.xyxy[0][0])
                
                for j, box in enumerate(sorted_boxes):
                    # Obtener coordenadas
                    x1_small, y1_small, x2_small, y2_small = box.xyxy[0]
                    
                    # Ajustar coordenadas a la imagen original
                    x1 = int(x1_small / scale_factor)
                    y1 = int(y1_small / scale_factor) + y_offset
                    x2 = int(x2_small / scale_factor)
                    y2 = int(y2_small / scale_factor) + y_offset
                    
                    # Convertir a enteros
                    ex, ey = x1, y1
                    ew, eh = x2 - x1, y2 - y1
                    
                    # Determinar si es ojo derecho
                    image_center_x = w / 2
                    eye_center_x = ex + (ew / 2)
                    is_right_eye = eye_center_x < image_center_x
                    
                    # Verificar límites
                    if ey >= 0 and ey+eh <= h and ex >= 0 and ex+ew <= w and eh > 0 and ew > 0:
                        eye_gray = gray[ey:ey+eh, ex:ex+ew]
                        eye_regions.append((eye_gray, ex, ey, ew, eh, is_right_eye))
            
            # Lista para guardar posiciones de pupilas
            pupil_positions = [None, None]
            
            # Procesar cada región
            for data in eye_regions:
                result = self.process_eye_region(data)
                if result:
                    cx, cy, radius, ex, ey, ew, eh, mask = result

                    if self.slider_th_pressed.value:
                        cv2.rectangle(final_frame, (ex, ey), (ex+ew, ey+eh), (0, 255, 0), 1)
                        roi = final_frame[ey:ey+eh, ex:ex+ew]
                        cv2.addWeighted(roi, 1, mask, 1, 0, roi) # addWeighted(image, alpha, mask, beta, gamma)
                    if not self.use_yolo.value:
                        cv2.rectangle(final_frame, (ex, ey), (ex+ew, ey+eh), (0, 255, 0), 1)
                    # Dibujar círculo de la pupila
                    #color = (0, 255, 0)
                    if data[5]:  # is_right_eye
                        color = (0, 0, 255)  # Rojo para ojo derecho (BGR)
                    else:
                        color = (255, 191, 0)  # Azul claro para ojo izquierdo (BGR)
                                            
                    cv2.circle(final_frame[ey:ey+eh, ex:ex+ew], (cx, cy), radius, color, 1)
                    
                    # Calcular coordenadas absolutas
                    abs_x = ex + cx
                    abs_y = ey + cy
                    
                    # Dibujar cruces
                    longitud_cruz = 5
                    cv2.line(final_frame, (abs_x - longitud_cruz, abs_y), (abs_x + longitud_cruz, abs_y), color, 1)
                    cv2.line(final_frame, (abs_x, abs_y - longitud_cruz), (abs_x, abs_y + longitud_cruz), color, 1)
                    # Guardar posición
                    abs_y = abs_y * -1
                    if data[5]:  # is_right_eye
                        pupil_positions[0] = [abs_x, abs_y]
                    else:
                        pupil_positions[1] = [abs_x, abs_y]
            
            # Convertir y agregar texto FPS
            final_frame = cv2.cvtColor(final_frame, cv2.COLOR_BGR2RGB)
            lbl_fps_position = (w - 45, 15)
            cv2.putText(final_frame, f"{fps:.1f}", lbl_fps_position, 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (248, 243, 43), 1, cv2.LINE_AA)
            
            # Publicar resultado final para la UI
            output = {
                'frame': final_frame,
                'pupil_positions': pupil_positions,
                'gray' : gray
            }
            
            self.ui_queue.put(output)
        
        print("Proceso de procesamiento finalizado")
    
    def process_eye_region(self, data):
        try:
            eye_gray, ex, ey, ew, eh, is_right_eye = data
            
            # 1. PREPROCESAMIENTO OPTIMIZADO
            # Suavizado para reducir ruido pero conservar bordes
            blurred = cv2.GaussianBlur(eye_gray, (5, 5), 0)
            
            # Mejorar contraste - opcional, solo si ayuda
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(blurred)
            #enhanced = blurred  # Usar directamente la imagen suavizada
        
            # 2. UMBRAL MANUAL - como el original, pero con mejor preprocesamiento

            threshold_value = self.threslhold[0] if is_right_eye else self.threslhold[1]
            if threshold_value == 0:
                #implementar para tener diferentes opciones
                otsu_thresh, _ = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                adjusted_thresh = max(0, min(255, otsu_thresh + threshold_value))
                _, thresh = cv2.threshold(enhanced, adjusted_thresh, 255, cv2.THRESH_BINARY_INV)


            else:    
                _, thresh = cv2.threshold(enhanced, threshold_value, 255, cv2.THRESH_BINARY_INV )
            
            # 3. OPERACIONES MORFOLÓGICAS MEJORADAS
            # Usar elementos estructurantes circulares
            kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            kernel_medium = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

            # Aplicar erosión si es necesario (usando parámetro existente)
            erode_value = self.erode[0] if is_right_eye else self.erode[1]
            if erode_value > 0:
                thresh_eroded = cv2.erode(thresh, kernel_small, iterations=erode_value)
            else:
                thresh_eroded = thresh

            # Cerrar para eliminar pequeños huecos (conectar regiones)
            thresh_closed = cv2.morphologyEx(thresh_eroded, cv2.MORPH_CLOSE, kernel_small, iterations=1)
        
            # Dilatar ligeramente para asegurar capturar toda la pupila
            thresh_processed = cv2.dilate(thresh_closed, kernel_small, iterations=1)
        
            # 4. ENCONTRAR Y FILTRAR CONTORNOS
            contours, _ = cv2.findContours(thresh_processed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Crear máscara para visualización
            mask = cv2.cvtColor(thresh_processed, cv2.COLOR_GRAY2BGR)

            #min_area = 10
            #contours = [c for c in contours if cv2.contourArea(c) > min_area]
            #NOTA: no suelo tener contornos pequeños pero si unos muy grandes
        
            if not contours:
                return None
                    
            # Filtrar por área para eliminar ruido
            valid_contours = []
            for c in contours:
                area = cv2.contourArea(c)
                # Ajustar estos umbrales según la resolución
                if area > 20 and area < (ew * eh * 0.5):  # Pupila no debería ser más del 50% del ojo
                    valid_contours.append(c)
            

                #areas = np.array([cv2.contourArea(c) for c in contours])
                #valid_mask = (areas > 20) & (areas < (ew * eh * 0.5))
                #valid_contours = [contours[i] for i in np.where(valid_mask)[0]]

            if not valid_contours:
                return None
        
            # Ordenar por área (mayor primero)
            valid_contours = sorted(valid_contours, key=cv2.contourArea, reverse=True)

            # 5. REGULARIZACIÓN DE CONTORNO
            largest_contour = valid_contours[0]

            # Calcular centro e intentar ajustar mejor al círculo
            M = cv2.moments(largest_contour)
            if M["m00"] != 0:
                center_x = int(M["m10"] / M["m00"])
                center_y = int(M["m01"] / M["m00"])
            else:
                # Si el cálculo del momento falla, usar boundingRect
                x, y, w, h = cv2.boundingRect(largest_contour)
                center_x = x + w // 2
                center_y = y + h // 2
            
            # 6. ESTABILIZACIÓN DE CENTRO
            # Obtener todos los puntos del contorno y calcular la distancia al centro
            distances = []
            
            for point in largest_contour.reshape(-1, 2):
                dx = point[0] - center_x
                dy = point[1] - center_y
                distance = np.sqrt(dx*dx + dy*dy)
                distances.append(distance)

            # ESTO es rápido - operación vectorizada:
            #points = largest_contour.reshape(-1, 2)
            #dx = points[:, 0] - center_x
            #dy = points[:, 1] - center_y
            #distances = np.sqrt(dx*dx + dy*dy)
            
            # Calcular radio como la mediana de las distancias (más estable que la media)
            if distances:
                radius = int(np.median(distances))
            else:
                # Fallback: Usar el método tradicional
                (cx, cy), radius = cv2.minEnclosingCircle(largest_contour)
                radius = int(radius)
            
            # 7. LIMITAR CAMBIOS BRUSCOS EN EL RADIO
            # Usar un rango razonable para el radio (ajustar según resolución)
            min_radius = 5
            max_radius = min(ew, eh) // 3
            
            radius = max(min_radius, min(radius, max_radius))
            
            # 8. DIBUJAR INFORMACIÓN EN LA MÁSCARA
            # Dibujar contorno original
            cv2.drawContours(mask, [largest_contour], 0, (0, 0, 255), 1)
            
            # Dibujar círculo calculado
            cv2.circle(mask, (center_x, center_y), radius, (0, 255, 0), 1)
            
            # Dibujar centro
            cv2.circle(mask, (center_x, center_y), 2, (255, 0, 0), -1)
            
            return (center_x, center_y, radius, ex, ey, ew, eh, mask)
                    
        except Exception as e:
            print(f"Error en process_eye_region: {e}")
            return None

    def start(self):
        """Inicia todos los procesos"""
        self.ui_queue = mp.Queue(maxsize=2)
        
        self.capture_process = mp.Process(target=self.capture_worker)
        self.detection_process = mp.Process(target=self.detection_worker)
        self.processing_process = mp.Process(target=self.processing_worker)
        
        self.capture_process.start()
        self.detection_process.start()
        self.processing_process.start()
    
    def stop(self):
        """Detiene todos los procesos de forma segura"""
        print("Iniciando detención de procesos...")
        
        # Primero señalizar que los procesos deben terminar
        if hasattr(self, 'running'):
            self.running.value = False
        
        # Dar tiempo para que los procesos terminen normalmente
        time.sleep(0.5)
        
        # Limpiar colas para evitar bloqueos
        for queue_name in ['frame_queue', 'detection_queue', 'result_queue', 'ui_queue']:
            if hasattr(self, queue_name):
                self._clear_queue(getattr(self, queue_name))
        
        # Verificar y terminar procesos uno por uno
        for process_name in ['capture_process', 'detection_process', 'processing_process']:
            if hasattr(self, process_name):
                process = getattr(self, process_name)
                if process and process.is_alive():
                    print(f"Terminando {process_name}")
                    process.join(timeout=1.0)  # Dar más tiempo para terminar limpiamente
                    
                    if process.is_alive():
                        print(f"Forzando terminación de {process_name}")
                        process.terminate()
                        process.join(timeout=0.5)
                        
                        # Si sigue vivo después de terminate, usar SIGKILL como último recurso
                        if process.is_alive():
                            print(f"Usando SIGKILL para {process_name}")
                            try:
                                import os, signal
                                os.kill(process.pid, signal.SIGKILL)
                            except Exception as e:
                                print(f"Error al terminar proceso: {e}")
        
        print("Todos los procesos detenidos")

    def _clear_queue(self, q):
        """Vacía una cola sin bloquear"""
        try:
            while True:
                q.get_nowait()
        except Exception:
            # Queue.Empty o cualquier otro error indica que no hay más elementos
            pass