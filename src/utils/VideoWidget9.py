from ultralytics import YOLO
import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal, QTimer, Qt, QObject
from PySide6.QtGui import QImage, QPixmap
import torch
import multiprocessing as mp
from multiprocessing import Process, Queue, Value, Array
import time
import ctypes

class VideoProcesses:
    def __init__(self, camera_id=2, cap_width=960, cap_height=540, cap_fps=120):
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
        self.changed_nose = Value(ctypes.c_bool, False)
        self.threslhold = Array('i', [40, 3])
        self.erode = Array('i', [0, 0])
        self.cap_error = Value(ctypes.c_bool, False)
        
        # Procesos
        self.capture_process = None
        self.detection_process = None
        self.processing_process = None
        
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
        model = YOLO('best_color.pt')
        
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
            
            # Extraer ROIs
            roi_y = frame_info['roi_y']
            roi_height = frame_info['roi_height']
            eyes_width = w - roi_nose
            roi_eye_width = int(eyes_width / 2)
            
            roi_right_eye = frame[roi_y:roi_y+roi_height, :roi_eye_width]
            roi_left_eye = frame[roi_y:roi_y+roi_height, roi_eye_width+roi_nose:]
            
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
            else:
                boxes = last_boxes
            
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
                    
                    # Dibujar círculo de la pupila
                    color = (0, 255, 0)
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
                'pupil_positions': pupil_positions
            }
            
            self.ui_queue.put(output)
        
        print("Proceso de procesamiento finalizado")
    
    def process_eye_region(self, data):
        try:
            eye_gray, ex, ey, ew, eh, is_right_eye = data
            
            # Usar threshold diferente según el ojo
            threshold_value = self.threslhold[0] if is_right_eye else self.threslhold[1]
            _, thresh = cv2.threshold(eye_gray, threshold_value, 255, cv2.THRESH_BINARY_INV)
            
            # Aplicar erosión
            erode_value = self.erode[0] if is_right_eye else self.erode[1]
            kernel = np.ones((2, 2), np.uint8)
            thresh_eroded = cv2.erode(thresh, kernel, iterations=erode_value)
            
            # Aplicar dilatación
            dilate_kernel = np.ones((3, 3), np.uint8)
            thresh_processed = cv2.dilate(thresh_eroded, dilate_kernel, iterations=1)
            
            # Crear máscara para visualización
            mask = cv2.cvtColor(thresh_processed, cv2.COLOR_GRAY2BGR)
            
            # Encontrar contornos
            contours, _ = cv2.findContours(thresh_processed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return None
            
            # Ordenar contornos
            if len(contours) > 1:
                contours = sorted(contours, key=lambda x: cv2.contourArea(x), reverse=True)
                
            # Calcular círculo
            (cx, cy), radius = cv2.minEnclosingCircle(contours[0])
            return (int(cx), int(cy), int(radius), ex, ey, ew, eh, mask)
                
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


class VideoThread(QThread):
    frame_ready = Signal(np.ndarray, object)
    
    def __init__(self, camera_id=2):
        super().__init__()
        self.running = True
        
        # Crear y configurar los procesos
        self.vp = VideoProcesses(camera_id=camera_id)
        
        # Variables de configuración
        self.threslhold = [40, 3]
        self.erode = [0, 0]
        self.nose_width = 0.25
        self.slider_th_pressed = False
        self.changed_prop_cap = False
        self.cap_width = 960
        self.cap_height = 540
        self.cap_fps = 120
    
    def set_resolution(self, resolution):
        """
        Cambia la resolución de la cámara de manera segura, asegurando que los
        procesos anteriores se cierren completamente antes de crear nuevos.
        """
        print(f"Cambiando resolución a: {resolution}")
        
        try:
            # Extraer los valores de resolución
            resolution_part, fps = resolution.split("@")
            width, height = resolution_part.split("x")
            
            new_width = int(width)
            new_height = int(height)
            new_fps = int(fps)
            
            # Almacenar nuevos valores
            self.cap_width = new_width
            self.cap_height = new_height
            self.cap_fps = new_fps
            
            # 1. Pausar la emisión de señales de frame_ready
            self.running = False
            
            # 2. Guardar la instancia actual
            old_vp = self.vp
            
            # 3. Detener completamente los procesos antiguos
            print("Deteniendo procesos anteriores...")
            old_vp.stop()
            
            # 4. Esperar a que se liberen los recursos (especialmente la cámara)
            time.sleep(1.5)  # Esperar un poco más para asegurar liberación de recursos
            
            # 5. Crear una nueva instancia con la nueva resolución
            print("Creando nuevos procesos...")
            self.vp = VideoProcesses(
                camera_id=old_vp.camera_id,
                cap_width=self.cap_width,
                cap_height=self.cap_height,
                cap_fps=self.cap_fps
            )
            
            # 6. Transferir configuraciones
            self.vp.threslhold[0] = self.threslhold[0]
            self.vp.threslhold[1] = self.threslhold[1]
            self.vp.erode[0] = self.erode[0]
            self.vp.erode[1] = self.erode[1]
            self.vp.nose_width.value = self.nose_width
            
            # 7. Iniciar los nuevos procesos
            self.vp.start()
            
            # 8. Reanudar la ejecución y reiniciar el bucle de procesamiento
            self.running = True
            print("Cambio de resolución completado")
            
            # 9. NUEVO: Reiniciar explícitamente el loop de procesamiento de frames
            self._restart_processing_loop()
            
        except Exception as e:
            print(f"Error al cambiar resolución: {e}")
            import traceback
            traceback.print_exc()
            
            # En caso de error, intentar restaurar el estado
            self.running = True

    def _restart_processing_loop(self):
        """
        Reinicia el loop de procesamiento de frames después de un cambio de resolución.
        Esto asegura que se vuelvan a emitir señales frame_ready.
        """
        print("Reiniciando loop de procesamiento de frames...")
        
        # Implementar un temporizador de un solo disparo para permitir que los procesos se inicien
        QTimer.singleShot(500, self._resume_frame_processing)

    def _resume_frame_processing(self):
        """
        Reanuda el procesamiento de frames después de un breve retraso.
        """
        print("Reanudando emisión de señales...")
        
        # Asegurarse que la cola UI esté vacía para evitar frames antiguos
        while not self.vp.ui_queue.empty():
            try:
                self.vp.ui_queue.get_nowait()
            except:
                break
        
        # Forzar la emisión de una señal inicial para actualizar la UI
        dummy_frame = np.zeros((self.cap_height, self.cap_width, 3), dtype=np.uint8)
        dummy_frame[:, :] = (0, 0, 0)  # Negro
        
        # Colocar texto "Reiniciando..." en el frame
        cv2.putText(dummy_frame, "Reiniciando...", (self.cap_width//4, self.cap_height//2),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        # Emitir este frame directamente para actualizar la UI
        dummy_frame_rgb = cv2.cvtColor(dummy_frame, cv2.COLOR_BGR2RGB)
        self.frame_ready.emit(dummy_frame_rgb, [None, None])
        
        print("Señales reiniciadas")


    def set_threshold(self, threshold):
        if len(threshold) != 2:
            print("Error: Se requieren dos valores de threshold")
            return
        
        if threshold[1] == 0:
            self.threslhold[0] = threshold[0]
            self.vp.threslhold[0] = threshold[0]
        elif threshold[1] == 1:
            self.threslhold[1] = threshold[0]
            self.vp.threslhold[1] = threshold[0]
        elif threshold[1] == 2:
            self.erode[0] = threshold[0]
            self.vp.erode[0] = threshold[0]
        elif threshold[1] == 3:
            self.erode[1] = threshold[0]
            self.vp.erode[1] = threshold[0]
        elif threshold[1] == 4:
            self.nose_width = threshold[0]/100
            self.vp.nose_width.value = threshold[0]/100
            self.vp.changed_nose.value = True
        else:
            print(f"Error: Índice de threshold incorrecto: {threshold[1]}")
    
    def set_color(self, text_label, value):
        # Esta funcionalidad ahora requeriría un canal de comunicación adicional
        # Por simplicidad, no se implementa en esta versión
        pass
    
    def run(self):
        # Iniciar procesos
        self.vp.start()
        
        while self.running:
            try:
                if not self.vp.ui_queue.empty():
                    output = self.vp.ui_queue.get()
                    frame = output['frame']
                    pupil_positions = output['pupil_positions']
                    
                    # Emitir frame y posiciones
                    self.frame_ready.emit(frame, pupil_positions)
                else:
                    # Dormir un poco para no sobrecargar la CPU
                    time.sleep(0.001)
            except Exception as e:
                print(f"Error en VideoThread.run: {e}")
                import traceback
                traceback.print_exc()
        
        # Detener procesos al salir
        self.vp.stop()
    
    def stop(self):
        """Detiene el hilo de manera segura."""
        print("Deteniendo VideoThread...")
        
        # Primero señalizar la terminación
        self.running = False
        
        # Detener los procesos de VideoProcesses
        if hasattr(self, 'vp'):
            try:
                print("Deteniendo procesos de video...")
                self.vp.stop()
            except Exception as e:
                print(f"Error al detener procesos: {e}")
        
        # Esperar a que el hilo termine (con timeout más largo)
        timeout = 3.0  # Usar 3 segundos en lugar de 1
        start_time = time.time()
        
        while self.isRunning() and (time.time() - start_time) < timeout:
            time.sleep(0.1)
        
        # Si el hilo sigue ejecutándose, intentar usar quit y wait
        if self.isRunning():
            print("Usando quit() y wait() para terminar el hilo")
            self.quit()
            if not self.wait(2000):  # Esperar 2 segundos más
                print("ADVERTENCIA: No se pudo terminar el hilo limpiamente")


# El resto de la clase VideoWidget permanece prácticamente igual
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
        """
        Gestiona el cambio de resolución y asegura que la UI se actualice correctamente.
        """
        def on_resolution_change():
            # Desconectar temporalmente las señales
            try:
                self.video_thread.frame_ready.disconnect()
            except:
                pass
            
            # Cambiar la resolución
            resolution = self.cbres.currentText()
            self.video_thread.set_resolution(resolution)
            
            # Reconectar la señal después de un breve retraso
            QTimer.singleShot(1000, self._reconnect_signals)
        
        # Conectar el cambio de índice al método
        self.cbres.currentIndexChanged.connect(on_resolution_change)

    def _reconnect_signals(self):
        """
        Reconecta las señales de frame_ready después de un cambio de resolución.
        """
        print("Reconectando señales...")
        try:
            # Asegurarse que la señal no esté conectada antes de reconectar
            self.video_thread.frame_ready.disconnect()
        except:
            pass
        
        # Reconectar la señal
        self.video_thread.frame_ready.connect(self.update_frame)
        
        # Limpiar el frame actual como indicación visual
        blank_image = QImage(self.video_thread.cap_width, 
                            self.video_thread.cap_height,
                            QImage.Format_RGB888)
        blank_image.fill(Qt.black)
        self.camera_frame.setPixmap(QPixmap.fromImage(blank_image))
        
        print("Señales reconectadas")


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
            
            # Actualizar posiciones de ojos
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