import json
import os
import sys
import time
import cv2
from PySide6.QtWidgets import QMainWindow
from PySide6.QtCore import Qt, QLocale
from PySide6.QtCore import QTimer
from utils.camera_config import CameraConfig
from PySide6.QtGui import QImage, QPixmap
from utils.VideoHandler import VideoHandler
from PySide6.QtCore import QThread, Signal
from utils.SerialHandler import SerialHandler
from utils.GraphHandler import TriplePlotWidget
from collections import deque
from utils.VideoWidget8 import VideoWidget
from utils.DetectorNistagmo import DetectorNistagmo
from utils.EyeDataProcessor import EyeDataProcessor
from utils.RecordHandler import RecordingController

class SerialReadThread(QThread):
    data_received = Signal(str)

    def __init__(self, serial_handler):
        super().__init__()
        self.serial_handler = serial_handler
        self.start_time = None
        self._running = True

    def run(self):
        self.start_time = time.perf_counter()
        while self._running:
            tiempo_actual = time.perf_counter() - self.start_time
            data = self.serial_handler.read_data()
            if data:
                data = f"{data},{tiempo_actual:.2f}"
                self.data_received.emit(data)
                self.msleep(10)  

    def stop(self):
        self._running = False
        self.wait()

class MainWindow(QMainWindow, RecordingController):
    def __init__(self):
        super().__init__()
        self.load_config()
        self.setupUi()
        self.pos_eye = []
        self.pos_hit = []
        # Inicializar procesamiento de video
        self.video_widget = VideoWidget(
            self.ui.CameraFrame,
            self.ui.lbl_text_temp
                              )
        self.video_widget.sig_pos.connect(self.set_pos_eye)

        self.plot_widget = TriplePlotWidget()
        #self.plot_widget.linePositionChanged.connect(self.tu_funcion_para_manejar_cambio)
        self.ui.layout_graph.addWidget(self.plot_widget)
        
        self.serial_handler = SerialHandler('/dev/ttyUSB0', 115200)  # Ajusta 'COM3' al puerto correcto
        self.serial_thread = SerialReadThread(self.serial_handler)
        self.serial_thread.data_received.connect(self.handle_serial_data)
        self.serial_thread.start()

        self.init_processor()
        # Inicializar detector de nistagmos
        self.nistagmo_detector = DetectorNistagmo(frecuencia_muestreo=200)  # Ajusta según FPS de tu cámara
        self.eye_positions_buffer = []
        
        # Timer para procesar nistagmos periódicamente (si deseas)
        self.nistagmo_timer = QTimer()
        self.nistagmo_timer.timeout.connect(self.process_nystagmus)
        self.nistagmo_timer.start(1000)  # Cada 1 segundo

        # Inicializar controlador de grabación
        self.setup_recording()

    def load_config(self):
        """Cargar configuración desde config.json"""
        # Obtener el directorio base de la aplicación
        if getattr(sys, "frozen", False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        config_path = os.path.join(base_path, "config", "config.json")
        try:
            with open(config_path, "r") as f:
                self.config = json.load(f)
            
            # Aplicar configuración
            self.setWindowTitle(self.tr(self.config["window_title"]))
            self.resize(
                self.config["window_size"]["width"],
                self.config["window_size"]["height"]
            )
        except Exception as e:
            print(self.tr("Error loading configuration: {}").format(e))
            self.config = {
                "app_name": "App",
                "window_title": self.tr("Application"),
                "window_size": {"width": 800, "height": 600}
            }
            self.setWindowTitle(self.config["window_title"])
            self.resize(
                self.config["window_size"]["width"],
                self.config["window_size"]["height"]
            )
    
    def setupUi(self):
        """Configurar la interfaz de usuario"""
        # Intentar importar la UI personalizada
        try:
            from .main_ui import Ui_MainWindow
            self.ui = Ui_MainWindow()
            print(self.tr("Loading custom UI from main_ui.py"))
        except ImportError:
            # Si no existe, usar la UI de demo
            from .main_demo_ui import DemoUI
            self.ui = DemoUI()
            print(self.tr("Loading demo UI"))
        
        # Configurar la UI
        self.ui.setupUi(self)

    #def activate_camera(self):
    #    self.camera_open = True
    #    device_path = self.camera_config.get_connected_camera(camera_name="USB Camera: USB GS CAM")
    #    self.cap = self.camera_config.setup_camera()
    #    self.timer = QTimer(self)
    #    self.timer.timeout.connect(self.update_frame)
    #    self.timer.start(1000 // self.camera_config.fps)
    
    def update_frame(self):
        ret, frame = self.cap.read()
        if ret:
            # Procesar frame
            marked_frame = self.opencv_logic.process_frame(frame, self.frame_number)
            
            # Convertir solo si necesitamos mostrar
            if marked_frame.shape[2] == 3:
                self.rgb_frame = cv2.cvtColor(marked_frame, cv2.COLOR_BGR2RGB)
            else:
                self.rgb_frame = marked_frame
                
            # Usar bytes contiguos para evitar copia
            height, width = self.rgb_frame.shape[:2]
            bytes_per_line = 3 * width
            
            # Crear QImage sin copia de datos
            image = QImage(self.rgb_frame.data, width, height, 
                        bytes_per_line, QImage.Format_RGB888)
            
            # Actualizar el pixmap
            self.ui.CameraFrame.setPixmap(QPixmap.fromImage(image))
            
            # Calcular FPS como en tu código original
            self.frame_count += 1
            current_time = cv2.getTickCount()
            self.current_fps = cv2.getTickFrequency() / (current_time - self.last_time)
            self.last_time = current_time
            
            if self.current_fps > self.fps_max:
                self.fps_max = self.current_fps

    def handle_serial_data(self, data):
        # Dividir el string
        string_list = data.split(",")
        self.pos_hit = [float(string_list[0]), float(string_list[1]), float(string_list[2]), float(string_list[3])]

    def init_processor(self):
        # Inicializar el procesador de datos oculares
        self.eye_processor = EyeDataProcessor()
        
        # Desactivar métodos de filtrado anteriores
        self.eye_processor.set_smoothing_enabled(False)
        self.eye_processor.set_interpolation_enabled(False)
        
        # Configurar Kalman avanzado con máximo suavizado
        self.eye_processor.set_kalman_enabled(True)
        self.eye_processor.set_kalman_parameters(
            process_noise=0.0005,
            measurement_noise=0.5,
            stability_factor=0.005
        )
        
        # Activar suavizado adicional post-Kalman
        self.eye_processor.set_extra_smoothing(True, buffer_size=8)
    

    def closeEvent(self, event):
        self.video_widget.cleanup()
        super().closeEvent(event)

    def process_nystagmus(self):
        # Solo procesar si hay suficientes datos
        if len(self.eye_positions_buffer) > 50:
            # Procesar los datos
            resultados = self.nistagmo_detector.procesar_datos(self.eye_positions_buffer)
            
            # Mostrar resultados
            if resultados['total_nistagmos'] > 0:
                print(f"VCL promedio: {resultados['vcl_promedio']:.2f}°/s")
                print(f"Nistagmos detectados: {resultados['total_nistagmos']}")
                
                # Opcional: Actualizar algún elemento en la interfaz
                # self.ui.lbl_vcl.setText(f"VCL: {resultados['vcl_promedio']:.2f}°/s")