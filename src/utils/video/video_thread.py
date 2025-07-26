import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal, QTimer
import time
from utils.video.video_processes import VideoProcesses

    
class VideoThread(QThread):
    frame_ready = Signal(np.ndarray, object, object)  
    
    def __init__(self, camera_id=2, cap_width=960,
                 cap_height=540, cap_fps=120, 
                 brightness=-21, contrast=50):
        

        super().__init__()
        self.running = True
        
        # IMPORTANTE: Ahora pasamos explícitamente los parámetros de resolución al constructor
        self.camera_id = camera_id
        self.cap_width = cap_width
        self.cap_height = cap_height
        self.cap_fps = cap_fps

        # Crear y configurar los procesos con los parámetros correctos
        self.vp = VideoProcesses(
            camera_id=camera_id,
            cap_width=self.cap_width,
            cap_height=self.cap_height,
            cap_fps=self.cap_fps, 
            brightness=brightness, 
            contrast=contrast
        )
        
        # Variables de configuración
        self.threslhold = [0, 0]
        self.erode = [0, 0]
        self.nose_width = 0.25
        self.slider_th_pressed = False
        self.changed_prop_cap = False

    def toggle_yolo(self, enabled):
        """Activa o desactiva el uso de YOLO para detección de ojos"""
        try:
            # Verificar si realmente hay un cambio para evitar mensajes duplicados
            if self.vp.use_yolo.value != enabled:
                self.vp.use_yolo.value = enabled
                print(f"Modo YOLO: {'Activado' if enabled else 'Desactivado'}")
        except Exception as e:
            print(f"Error al cambiar modo YOLO: {e}")

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



    def set_threshold(self, value, slider_name):
        """MODIFICAR método existente para manejar ambos modos"""
        
        # Actualizar VideoThread si está en modo live
        if hasattr(self, 'video_thread') and self.video_thread and not self.is_in_player_mode:
            # Lógica original para VideoThread
            if slider_name == "slider_th_right":
                self.video_thread.threslhold[0] = value
                self.video_thread.vp.threslhold[0] = value
            elif slider_name == "slider_th_left":
                self.video_thread.threslhold[1] = value
                self.video_thread.vp.threslhold[1] = value
            elif slider_name == "slider_erode_right":
                self.video_thread.erode[0] = value
                self.video_thread.vp.erode[0] = value
            elif slider_name == "slider_erode_left":
                self.video_thread.erode[1] = value
                self.video_thread.vp.erode[1] = value
            elif slider_name == "slider_nose_width":
                self.video_thread.nose_width = value/100
                self.video_thread.vp.nose_width.value = value/100
                self.video_thread.vp.changed_nose.value = True
            elif slider_name == "slider_height":
                self.video_thread.vp.eye_heigh.value = value/100
                self.video_thread.vp.changed_eye_height.value = True
            elif slider_name == "slider_brightness":
                self.video_thread.vp.brightness.value = value
                self.video_thread.vp.color_changed.value = True
            elif slider_name == "slider_contrast":
                self.video_thread.vp.contrast.value = value
                self.video_thread.vp.color_changed.value = True
            else:
                print(f"Error: Slider no reconocido: {slider_name}")
        
        # Actualizar VideoPlayerThread si está en modo player
        if self.video_player_thread and self.is_in_player_mode:
            config_update = {}
            
            if slider_name == "slider_th_right":
                config_update['threslhold'] = [value, self.video_player_thread.analysis_config['threslhold'][1]]
            elif slider_name == "slider_th_left":
                config_update['threslhold'] = [self.video_player_thread.analysis_config['threslhold'][0], value]
            elif slider_name == "slider_erode_right":
                config_update['erode'] = [value, self.video_player_thread.analysis_config['erode'][1]]
            elif slider_name == "slider_erode_left":
                config_update['erode'] = [self.video_player_thread.analysis_config['erode'][0], value]
            elif slider_name == "slider_nose_width":
                config_update['nose_width'] = value / 100.0
            elif slider_name == "slider_height":
                config_update['eye_height'] = value / 100.0
            
            if config_update:
                self.video_player_thread.update_analysis_config(config_update)

    def run(self):
        # Iniciar procesos
        self.vp.start()
        
        while self.running:
            try:
                if not self.vp.ui_queue.empty():
                    output = self.vp.ui_queue.get()
                    frame = output['frame']
                    pupil_positions = output['pupil_positions']
                    gray = output.get('gray', None)  # Obtener gray del output
                    # Aquí está el problema - necesitamos usar .value para acceder a la variable compartida
                    self.vp.slider_th_pressed.value = self.slider_th_pressed
                    
                    # Emitir frame y posiciones
                    self.frame_ready.emit(frame, pupil_positions, gray)
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
                
                