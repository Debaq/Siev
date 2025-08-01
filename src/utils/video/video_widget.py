        
import numpy as np
from PySide6.QtCore import QThread, Signal,QObject
from PySide6.QtGui import QImage, QPixmap
import time
from utils.video.video_thread import VideoThread
from utils.video.video_player_thread import VideoPlayerThread
from PySide6.QtCore import QTimer

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

        # === NUEVAS PROPIEDADES PARA PLAYER ===
        self.video_player_thread = None
        self.is_in_player_mode = False
        self.current_video_data = None
        
        # === REFERENCIAS A UI ===
        self.slider_time = None  # Se asignará desde main_window
        self.btn_start = None    # Se asignará desde main_window
        
        # Timer para actualizar slider de tiempo
        self.time_update_timer = QTimer()
        self.time_update_timer.timeout.connect(self.update_time_slider)
                
        slider_contrast = next((slider for slider in self.sliders if slider.objectName() == "slider_contrast"), None)
        slider_brightness = next((slider for slider in self.sliders if slider.objectName() == "slider_brightness"), None)

        # Verificar si hay resoluciones disponibles
        resolucion = self.cbres.currentText()
        
        if not resolucion or resolucion.strip() == "":
            # Modo dummy - sin cámara
            print("No se detectaron resoluciones de cámara. Iniciando en modo dummy.")
            self._create_dummy_display()
            self.video_thread = None
            # Conectar señales básicas para compatibilidad
            self.resolution_changed()
            self.sliders_changed()
        else:
            # Modo normal - con cámara
            # Conectar señales
            self.resolution_changed()
            self.sliders_changed()
            
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

    def _create_dummy_display(self):
        """Crea una imagen dummy de 640x200 con texto 'sin cámara'"""
        from PySide6.QtGui import QPainter, QFont, QColor
        
        # Crear imagen negra de 640x200
        width, height = 640, 200
        dummy_image = QImage(width, height, QImage.Format_RGB888)
        dummy_image.fill(QColor(0, 0, 0))  # Negro
        
        # Dibujar texto centrado
        painter = QPainter(dummy_image)
        painter.setPen(QColor(255, 255, 255))  # Texto blanco
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        painter.setFont(font)
        
        text = "sin cámara"
        text_rect = painter.fontMetrics().boundingRect(text)
        x = (width - text_rect.width()) // 2
        y = (height + text_rect.height()) // 2
        
        painter.drawText(x, y, text)
        painter.end()
        
        # Convertir a QPixmap y mostrar
        pixmap = QPixmap.fromImage(dummy_image)
        self.camera_frame.setPixmap(pixmap)
        self.camera_frame.setFixedSize(width, height)
        
        print(f"VideoWidget dummy creado: {width}x{height}")
        

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
            slider.valueChanged.connect(lambda value, name=slider_name: self.set_threshold(value, name))

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
            self.set_threshold(current_value, slider_name)

    
   
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


    def set_ui_references(self, slider_time, btn_start):
        """Establecer referencias a controles de UI"""
        self.slider_time = slider_time
        self.btn_start = btn_start
        
        # Conectar eventos del slider de tiempo
        if self.slider_time:
            self.slider_time.sliderPressed.connect(self._on_time_slider_pressed)
            self.slider_time.sliderReleased.connect(self._on_time_slider_released)
            self.slider_time.valueChanged.connect(self._on_time_slider_changed)
            
        print("Referencias UI establecidas para VideoWidget")

    def switch_to_live_mode(self, camera_id=2):
        """Cambiar a modo cámara en vivo"""
        print("=== CAMBIANDO A MODO CÁMARA EN VIVO ===")
        
        # 1. Destruir VideoPlayerThread si existe
        if self.video_player_thread:
            print("Destruyendo VideoPlayerThread...")
            self.video_player_thread.stop()
            if self.video_player_thread.isRunning():
                self.video_player_thread.wait(3000)
            self.video_player_thread = None
        
        # 2. Parar timer de actualización
        self.time_update_timer.stop()
        
        # 3. Limpiar estado de player
        self.is_in_player_mode = False
        self.current_video_data = None
        
        # 4. Configurar UI para modo en vivo
        self._configure_ui_for_live_mode()
        
        # 5. Crear/Recrear VideoThread si no existe
        if not hasattr(self, 'video_thread') or not self.video_thread:
            print("Creando nuevo VideoThread...")
            self._create_new_video_thread(camera_id)
        
        print("Modo cámara en vivo activado")

    def switch_to_player_mode(self, video_data):
        """Cambiar a modo reproductor de video"""
        print("=== CAMBIANDO A MODO REPRODUCTOR ===")

        # 1. Destruir VideoThread si existe
        if hasattr(self, 'video_thread') and self.video_thread:
            print("Destruyendo VideoThread...")
            self.video_thread.stop()
            if self.video_thread.isRunning():
                self.video_thread.wait(3000)
            self.video_thread = None
        
        # 2. Configurar estado de player
        self.is_in_player_mode = True
        self.current_video_data = video_data
        
        # 3. Configurar UI para modo player
        self._configure_ui_for_player_mode()
        
        # 4. Crear VideoPlayerThread
        print("Creando VideoPlayerThread...")
        self._create_video_player_thread(video_data)
        
        # 5. Iniciar timer de actualización
        self.time_update_timer.start(100)  # Actualizar cada 100ms
        

        print("Modo reproductor activado")

    def _create_new_video_thread(self, camera_id):
        """Crear nuevo VideoThread con configuración actual"""
        try:
            # Obtener configuración actual
            resolucion = self.cbres.currentText()
            res_partes = resolucion.split('@')
            width, height = map(int, res_partes[0].split('x'))
            fps = int(res_partes[1])
            
            # Obtener valores de sliders
            slider_contrast = next((slider for slider in self.sliders if slider.objectName() == "slider_contrast"), None)
            slider_brightness = next((slider for slider in self.sliders if slider.objectName() == "slider_brightness"), None)
            
            # Crear VideoThread
            from utils.video.video_thread import VideoThread
            self.video_thread = VideoThread(
                camera_id=camera_id,
                cap_width=width,
                cap_height=height,
                cap_fps=fps,
                brightness=slider_brightness.value() if slider_brightness else -21,
                contrast=slider_contrast.value() if slider_contrast else 50
            )
            
            # Conectar señales
            self.video_thread.frame_ready.connect(self.update_frame)
            
            # Iniciar thread
            self.video_thread.start(QThread.HighPriority)
            
            # Reconectar sliders
            self.reconnect_sliders()
            
            print("VideoThread creado exitosamente")
            
        except Exception as e:
            print(f"Error creando VideoThread: {e}")

    def _create_video_player_thread(self, video_data):
        """Crear VideoPlayerThread"""
        try:
            # Configuración de análisis desde sliders actuales
            analysis_config = {
                'threslhold': [50, 50],
                'erode': [2, 2],
                'nose_width': 0.25,
                'eye_height': 0.5
            }
            
            # Actualizar con valores de sliders actuales
            self._update_analysis_config_from_sliders(analysis_config)
            
            # Crear VideoPlayerThread
            self.video_player_thread = VideoPlayerThread(video_data, analysis_config)
            
            # Conectar señales
            self.video_player_thread.frame_ready.connect(self.update_frame)
            self.video_player_thread.video_loaded.connect(self._on_video_loaded)
            self.video_player_thread.duration_changed.connect(self._on_duration_changed)
            
            # Iniciar thread
            self.video_player_thread.start()
            
            print("VideoPlayerThread creado exitosamente")
            
        except Exception as e:
            print(f"Error creando VideoPlayerThread: {e}")

    def _update_analysis_config_from_sliders(self, config):
        """Actualizar configuración de análisis desde sliders"""
        try:
            for slider in self.sliders:
                name = slider.objectName()
                value = slider.value()
                
                if name == "slider_th_right":
                    config['threslhold'][0] = value
                elif name == "slider_th_left":
                    config['threslhold'][1] = value
                elif name == "slider_erode_right":
                    config['erode'][0] = value
                elif name == "slider_erode_left":
                    config['erode'][1] = value
                elif name == "slider_nose_width":
                    config['nose_width'] = value / 100.0
                elif name == "slider_height":
                    config['eye_height'] = value / 100.0
        except Exception as e:
            print(f"Error actualizando config de análisis: {e}")

    def _configure_ui_for_live_mode(self):
        """Configurar UI para modo cámara en vivo"""
        if self.slider_time:
            self.slider_time.setEnabled(False)
            self.slider_time.setValue(0)
        
        if self.btn_start:
            self.btn_start.setText("Iniciar")

    def _configure_ui_for_player_mode(self):
        """Configurar UI para modo reproductor"""
        if self.slider_time:
            self.slider_time.setEnabled(True)
            self.slider_time.setValue(0)
        
        if self.btn_start:
            self.btn_start.setText("Reproducir")
            self.btn_start.setEnabled(True)  


    def _on_video_loaded(self, success):
        """Callback cuando se carga el video"""
        if success:
            print("Video cargado exitosamente")
        else:
            print("Error cargando video")

    def _on_duration_changed(self, duration):
        """Callback cuando cambia la duración del video"""
        if self.slider_time:
            # Configurar slider para la duración del video (precisión de centésimas)
            self.slider_time.setMaximum(int(duration * 100))
            self.slider_time.setValue(0)
        print(f"Duración del video: {duration:.2f} segundos")

    def _on_time_slider_pressed(self):
        """Cuando se presiona el slider de tiempo"""
        if self.video_player_thread:
            self.video_player_thread.pause()

    def _on_time_slider_released(self):
        """Cuando se suelta el slider de tiempo"""
        # No reanudar automáticamente, esperar botón play
        pass

    def _on_time_slider_changed(self, value):
        """Cuando cambia el valor del slider de tiempo"""
        if self.video_player_thread and self.is_in_player_mode:
            # Convertir valor a tiempo
            time_seconds = value / 100.0
            self.video_player_thread.seek_to_time(time_seconds)

    # === MÉTODOS PARA CONTROLES DE REPRODUCCIÓN ===

    def play_video(self):
        """Reproducir video"""
        if self.video_player_thread and self.is_in_player_mode:
            self.video_player_thread.play()
            if self.btn_start:
                self.btn_start.setText("Pause")

    def pause_video(self):
        """Pausar video"""
        if self.video_player_thread and self.is_in_player_mode:
            self.video_player_thread.pause()
            if self.btn_start:
                self.btn_start.setText("Play")

    def toggle_playback(self):
        """Alternar reproducción/pausa"""
        if self.video_player_thread and self.is_in_player_mode:
            if self.video_player_thread.is_playing:
                self.pause_video()
            else:
                self.play_video()

    def update_time_slider(self):
        """Actualizar slider de tiempo durante reproducción"""
        if (self.video_player_thread and self.slider_time and 
            self.is_in_player_mode and self.video_player_thread.is_playing):
            
            current_time = self.video_player_thread.get_current_time()
            slider_value = int(current_time * 100)
            
            # Actualizar sin triggear el evento
            self.slider_time.blockSignals(True)
            self.slider_time.setValue(slider_value)
            self.slider_time.blockSignals(False)
            
            
            self._update_graph_line_position(current_time)


    def _update_graph_line_position(self, time_seconds):
        """Actualizar posición de línea del gráfico durante reproducción automática"""
        try:
            # Buscar main_window a través de parent hierarchy
            widget = self.camera_frame
            while widget and not hasattr(widget, 'plot_widget'):
                widget = widget.parent()
            
            if (widget and hasattr(widget, 'plot_widget') and 
                hasattr(widget.plot_widget, 'set_video_time_position')):
                widget.plot_widget.set_video_time_position(time_seconds)
                
        except Exception as e:
            print(f"Error actualizando línea del gráfico: {e}")
        

    def cleanup(self):
        """Limpia los recursos al cerrar la aplicación"""
        try:
            # Detener timer
            self.time_update_timer.stop()
            
            # Limpiar VideoThread
            if hasattr(self, 'video_thread') and self.video_thread:
                try:
                    self.video_thread.frame_ready.disconnect()
                except:
                    pass
                
                print("Deteniendo VideoThread...")
                self.video_thread.stop()
                
                if self.video_thread.isRunning():
                    if not self.video_thread.wait(2000):
                        print("Forzando terminación del VideoThread")
                        self.video_thread.terminate()
            
            # Limpiar VideoPlayerThread
            if self.video_player_thread:
                print("Deteniendo VideoPlayerThread...")
                self.video_player_thread.stop()
                
                if self.video_player_thread.isRunning():
                    if not self.video_player_thread.wait(2000):
                        print("Forzando terminación del VideoPlayerThread")
                        self.video_player_thread.terminate()
                        
        except Exception as e:
            print(f"Error durante la limpieza: {e}")