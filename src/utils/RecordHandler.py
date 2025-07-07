import time
from PySide6.QtCore import QTimer

class RecordingController:
    """Funciones para controlar la grabación y visualización de datos oculares"""
    
    def setup_recording(self):
        """Configura los componentes necesarios para la grabación"""
        # Inicializar variables de control de grabación
        self.is_recording = False
        self.is_calibrating = False
        self.recording_start_time = None
        self.MAX_RECORDING_TIME = 5 * 60  # 5 minutos en segundos
        self.CALIBRATION_TIME = 1  # 5 segundos para calibración
        
        # Variables para el tiempo de la gráfica (completamente independiente)
        self.graph_time = 0.0
        self.last_update_time = None
        
        # Inicializar procesador de datos oculares
        self.init_processor()
        
        # Inicializar timer para actualizar contador de tiempo
        self.recording_timer = QTimer()
        self.recording_timer.timeout.connect(self.update_recording_time)
        self.recording_timer.start(50)  # Actualizar cada 50ms para fluidez
        
        # Conectar botón de inicio
        self.ui.btn_start.clicked.connect(self.toggle_recording)
        
        # Deshabilitar envío de datos a la gráfica inicialmente
        self.send_to_graph = False
        
        # Mostrar estado inicial
        self.ui.lbl_time.setText("00:00 / 05:00")
    
    def init_processor(self):
        """Inicializa el procesador de datos oculares"""
        from utils.EyeDataProcessor import EyeDataProcessor
        
        # Inicializar el procesador de datos
        self.eye_processor = EyeDataProcessor()
        
        # Configuración óptima para suavizado
        self.eye_processor.set_filter_strength(0.3)
        self.eye_processor.set_interpolation_steps(3)
        self.eye_processor.set_history_size(5)
        
        # Asegurarnos que el procesamiento avanzado esté activado
        self.eye_processor.set_smoothing_enabled(True)
        self.eye_processor.set_interpolation_enabled(True)
    
    def toggle_recording(self):
        """Inicia o detiene la grabación al presionar el botón"""
        if not self.is_recording and not self.is_calibrating:
            # Iniciar calibración
            self.start_calibration()
        else:
            # Detener grabación
            self.stop_recording()
    
    def start_calibration(self):
        """Inicia fase de calibración"""
        self.is_calibrating = True
        self.eye_processor.reset_calibration()  # Reiniciar calibración
        
        # Inicializar tiempos de referencia
        self.recording_start_time = time.time()
        self.last_update_time = time.time()
        self.graph_time = -self.CALIBRATION_TIME  # Comenzar en tiempo negativo
        
        # Actualizar UI
        self.ui.btn_start.setText("Calibrando...")
        self.ui.btn_start.setEnabled(False)
        self.ui.lbl_time.setText(f"Calibrando: {self.CALIBRATION_TIME}s")
        
        # Habilitar envío de datos para calibración
        self.send_to_graph = True
        
        # Programar fin de calibración
        QTimer.singleShot(self.CALIBRATION_TIME * 1000, self.start_recording)
    
    def start_recording(self):
        """Inicia la grabación después de la calibración"""
        self.is_calibrating = False
        self.is_recording = True
        self.recording_start_time = time.time()
        
        # Reiniciar el tiempo de la gráfica a cero
        self.graph_time = 0.0
        self.last_update_time = time.time()
        
        # Limpiar gráfica antes de iniciar
        self.plot_widget.clearPlots()
        
        # Actualizar UI
        self.ui.btn_start.setText("Detener")
        self.ui.btn_start.setEnabled(True)
    
    def stop_recording(self):
        """Detiene la grabación"""
        self.is_recording = False
        self.is_calibrating = False
        self.recording_start_time = None
        self.last_update_time = None
        self.graph_time = 0.0
        self.send_to_graph = False
        
        # Actualizar UI
        self.ui.btn_start.setText("Iniciar")
        self.ui.lbl_time.setText("00:00 / 05:00")
    
    def update_recording_time(self):
        """
        Actualiza el contador de tiempo y el tiempo usado en la gráfica.
        Este método es llamado por el timer interno.
        """
        current_time = time.time()
        
        # Actualizar tiempo de la gráfica
        if self.last_update_time is not None:
            delta_time = current_time - self.last_update_time
            
            if self.is_recording:
                # Durante grabación, incrementar el tiempo normalmente
                self.graph_time += delta_time
                
                # Verificar si se alcanzó el tiempo máximo
                elapsed = current_time - self.recording_start_time
                if elapsed >= self.MAX_RECORDING_TIME:
                    self.stop_recording()
                    return
                
                # Actualizar etiqueta de tiempo
                minutes_elapsed = int(self.graph_time // 60)
                seconds_elapsed = int(self.graph_time % 60)
                self.ui.lbl_time.setText(f"{minutes_elapsed:02d}:{seconds_elapsed:02d} / 05:00")
                
            elif self.is_calibrating:
                # Durante calibración, avanzar desde tiempo negativo hacia cero
                elapsed_calib = current_time - self.recording_start_time
                remaining = max(0, self.CALIBRATION_TIME - elapsed_calib)
                self.graph_time = -remaining
                
                # Actualizar etiqueta de tiempo de calibración
                self.ui.lbl_time.setText(f"Calibrando: {int(remaining)}s")
        
        # Actualizar tiempo de referencia
        self.last_update_time = current_time
    
    def set_pos_eye(self, pos): 
        """Recibe posiciones de ojos y las procesa"""
        # Guardar datos originales
        self.pos_eye = pos
        # Solo procesar si estamos grabando o calibrando
        if not self.send_to_graph:
            return
        
        # Extraer datos
        left_eye = self.pos_eye[1]
        right_eye = self.pos_eye[0]
        
   
        # Usar el tiempo de gráfica actual gestionado por el controlador
        # Ignorar completamente el tiempo del SerialHandler
        #self.eye_processor.processing_enabled = False
        processed_points = self.eye_processor.process_eye_data(
            left_eye, 
            right_eye, 
            float(self.pos_hit[0]),  # IMU X 
            float(self.pos_hit[1]),  # IMU Y
            self.graph_time  # Tiempo de gráfica interno
        )
        
        # Enviar cada punto procesado a la gráfica
        for processed_point in processed_points:
            processed_left, processed_right, imu_x, imu_y, point_time = processed_point
            self.plot_widget.updatePlots([processed_left, processed_right, imu_x, imu_y, point_time])
    
