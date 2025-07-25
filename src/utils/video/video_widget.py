import numpy as np
from PySide6.QtCore import QThread, Signal,QObject
from PySide6.QtGui import QImage, QPixmap
import time
from utils.video.video_thread import VideoThread

class VideoWidget(QObject):
    sig_pos = Signal(list)

    def __init__(self, camera_frame, sliders, cbres, camera_id=2, video_callback=None):
        super().__init__()

        self.video_callback = video_callback

        # Guardar referencias a los widgets de UI
        self.cbres = cbres        
        self.sliders = sliders
        self.camera_frame = camera_frame
        self.pos_eye = []
        
        slider_contrast = next((slider for slider in self.sliders if slider.objectName() == "slider_contrast"), None)
        slider_brightness = next((slider for slider in self.sliders if slider.objectName() == "slider_brightness"), None)

        #brightness = sliders[]

        # Conectar señales
        self.resolution_changed()
        self.sliders_changed()
        resolucion = self.cbres.currentText()
        # Crear el hilo de video
        res_partes = resolucion.split('@')
        width, height = map(int, res_partes[0].split('x'))
        fps = int(res_partes[1])
        
        self.video_thread = VideoThread(camera_id=camera_id, 
                                        cap_width=width, 
                                        cap_height=height, 
                                        cap_fps=fps, brightness=slider_brightness.value(), 
                                        contrast=slider_contrast.value())
        self.video_thread.frame_ready.connect(self.update_frame)
                
        self.current_fps = 0
        self.video_thread.start(QThread.HighPriority)

    #def set_video_color(self, text_label, value):
        """Método para cambiar el brillo o contraste de la cámara"""
    #    try:
            # Llamar al método correspondiente en el hilo de video
    #        self.video_thread.set_video_color(text_label, value)
    #    except Exception as e:
    #        print(f"Error al cambiar configuración de color: {e}")

    def resolution_changed(self):
        """Conecta el cambio de resolución"""
        # Desconectar primero por si ya estaba conectado
        first_time = not hasattr(self, '_resolution_connected') or not self._resolution_connected

        if not first_time:
            # Solo intentar desconectar si ya se había conectado previamente
            try:
                self.cbres.currentIndexChanged.disconnect(self.handle_resolution_change)
            except Exception:
                # Silenciar cualquier error de desconexión
                pass
    
        # Conectar la señal y marcar como conectada
        self.cbres.currentIndexChanged.connect(self.handle_resolution_change)
        self._resolution_connected = True
    
    def handle_resolution_change(self):
        """Método para manejar el cambio de resolución"""
        try:
            # Obtener la nueva resolución
            new_resolution = self.cbres.currentText()
            print(f"Cambiando a resolución: {new_resolution}")
            
            # Extraer los valores de resolución
            resolution_part, fps = new_resolution.split("@")
            width, height = resolution_part.split("x")
            new_width = int(width)
            new_height = int(height)
            new_fps = int(fps)
            
            # Obtener valores actuales para transferir
            old_thread = self.video_thread
            camera_id = old_thread.camera_id
            threslhold = list(old_thread.threslhold)
            erode = list(old_thread.erode)
            nose_width = old_thread.nose_width
            brightness_value = old_thread.vp.brightness.value  
            contrast_value = old_thread.vp.contrast.value
            print(f"Guardando valores: Brillo={brightness_value}, Contraste={contrast_value}")
        
            # Detener el hilo actual
            print("Deteniendo captura de video para cambio de resolución...")
            old_thread.stop()
            
            # Esperar a que termine completamente
            if old_thread.isRunning():
                print("Esperando a que termine el hilo anterior...")
                if not old_thread.wait(3000):  # Esperar hasta 3 segundos
                    print("ADVERTENCIA: El hilo anterior no terminó, forzando...")
                    old_thread.terminate()
            
            # Esperar un momento para liberar recursos
            time.sleep(1.0)
            
            slider_contrast = next((slider for slider in self.sliders if slider.objectName() == "slider_contrast"), None)
            slider_brightness = next((slider for slider in self.sliders if slider.objectName() == "slider_brightness"), None)


            # Crear un nuevo VideoThread con la nueva resolución
            print("Creando nuevo hilo de video...")
            self.video_thread = VideoThread(
                camera_id=camera_id,
                cap_width=new_width,
                cap_height=new_height,
                cap_fps=new_fps,
                brightness=slider_brightness.value(),
                contrast=slider_contrast.value()
            )
            
            # Transferir otras configuraciones
            self.video_thread.threslhold = threslhold
            self.video_thread.erode = erode
            self.video_thread.nose_width = nose_width

        
            # Conectar señales al nuevo hilo
            self.video_thread.frame_ready.connect(self.update_frame)
            
            # Iniciar el nuevo hilo
            print("Iniciando nuevo hilo de video...")
            self.video_thread.start(QThread.HighPriority)
            
            # Reconectar controles de deslizadores al nuevo hilo
            self.reconnect_sliders()
            
            print("Cambio de resolución completado.")
            
        except Exception as e:
            print(f"Error durante el cambio de resolución: {e}")
            import traceback
            traceback.print_exc()
    def sliders_changed(self):
        """Conecta los deslizadores al thread actual"""
        
        # Desconectar solo las conexiones al video_thread anterior
        for slider in self.sliders:
            try:
                # Desconectar solo valueChanged que va al video_thread
                slider.valueChanged.disconnect()
            except Exception:
                pass
            # Mantener sliderPressed y sliderReleased conectados
        
        # Reconectar al nuevo video_thread
        for slider in self.sliders:
            slider_name = slider.objectName()
            
            # Conectar al nuevo thread
            slider.valueChanged.connect(lambda value, name=slider_name: self.video_thread.set_threshold(value, name))
            
            # Solo conectar estos si no estaban conectados antes
            if not hasattr(self, '_ui_connections_done'):
                slider.sliderPressed.connect(self.on_slider_pressed)
                slider.sliderReleased.connect(self.on_slider_released)
                
                if slider_name in ["slider_vertical_cut_up", "slider_vertical_cut_down"]:
                    slider.valueChanged.connect(lambda value, name=slider_name: self.config_slider_cut_vertical(value, name))
        
        self._ui_connections_done = True
    
    def config_slider_cut_vertical(self, value, name):
        pass


    def on_slider_pressed(self):
        """Maneja el evento cuando un slider es presionado"""
        self.video_thread.slider_th_pressed = True

    def on_slider_released(self):
        """Maneja el evento cuando un slider es soltado"""
        self.video_thread.slider_th_pressed = False

    def reconnect_sliders(self):
        """Reconecta los controles deslizantes al nuevo hilo de video"""
        # Reconectar los deslizadores de umbral
        self.sliders_changed()
        
        # Aplicar los valores actuales de los sliders al nuevo thread
        for slider in self.sliders:
            slider_name = slider.objectName()
            current_value = slider.value()
            self.video_thread.set_threshold(current_value, slider_name)
    
   

    def update_frame(self, frame, pupil_positions, gray_frame=None):
        """Actualiza el frame de video y las posiciones de las pupilas"""
        try:          
            # Actualizar la imagen
            if frame is not None and frame.size > 0:
                # Verificar que frame sea una matriz continua en memoria
                if not frame.flags['C_CONTIGUOUS']:
                    frame = np.ascontiguousarray(frame)
                
                height, width = frame.shape[:2]
                bytes_per_line = 3 * width
                
                # Crear imagen QImage desde los datos
                image = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
                
                if not image.isNull():
                    # Crear QPixmap y establecer en el widget
                    pixmap = QPixmap.fromImage(image)
                    self.camera_frame.setPixmap(pixmap)
                    
                    # Ajustar el tamaño del QLabel si es necesario
                    current_size = self.camera_frame.size()
                    if current_size.width() != width or current_size.height() != height:
                        print(f"Ajustando tamaño del widget a {width}x{height}")
                        self.camera_frame.setFixedSize(width, height)

            if gray_frame is not None and self.video_callback:
                self.video_callback(gray_frame)  # main_window decide si procesar o no

            # Actualizar posiciones de ojos
            self.pos_eye = pupil_positions
            
            # Emitir la señal con las posiciones
            self.sig_pos.emit(self.pos_eye)

        except Exception as e:
            print(f"Error en update_frame: {e}")
            import traceback
            traceback.print_exc()

    def set_yolo_enabled(self, enabled):
        """Activa o desactiva el uso de YOLO"""
        try:
            print(f"Estableciendo YOLO a: {'Activado' if enabled else 'Desactivado'}")
            self.video_thread.toggle_yolo(enabled)
        except Exception as e:
            print(f"Error al cambiar modo YOLO: {e}")



    
    def cleanup(self):
        """Limpia los recursos al cerrar la aplicación"""
        try:
            # Desconectar señales
            try:
                self.video_thread.frame_ready.disconnect()
            except:
                pass
            
            # Detener el hilo
            print("Deteniendo VideoThread...")
            self.video_thread.stop()
            
            # Esperar a que termine (con timeout)
            if self.video_thread.isRunning():
                if not self.video_thread.wait(2000):  # 2 segundos de timeout
                    print("Forzando terminación del hilo de video")
                    self.video_thread.terminate()
        except Exception as e:
            print(f"Error durante la limpieza: {e}")