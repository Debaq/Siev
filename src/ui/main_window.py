import json
import os
import sys
from PySide6.QtWidgets import (QMainWindow, QMenu,
                            QWidgetAction, QSlider, 
                            QHBoxLayout, QWidget, 
                            QLabel, QCheckBox)
from PySide6.QtCore import Qt
from PySide6.QtCore import QTimer
from PySide6.QtCore import QThread, Signal
from utils.SerialHandler import SerialHandler
from utils.graphing import TriplePlotWidget
from utils.VideoWidget11 import VideoWidget
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
        while self._running:
            data = self.serial_handler.read_data()
            if data:
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
        self.menu_presets()
        self.pos_eye = []
        self.pos_hit = []

        # Inicializar procesamiento de video
        self.slider_thresholds = [self.ui.slider_th_right, 
                                  self.ui.slider_th_left,
                                  self.ui.slider_erode_right,
                                  self.ui.slider_erode_left,
                                  self.ui.slider_nose_width]
        
        self.video_widget = VideoWidget(
            self.ui.CameraFrame, 
            self.slider_thresholds,
            self.ui.cb_resolution)
        
        self.video_widget.sig_pos.connect(self.set_pos_eye)

        self.plot_widget = TriplePlotWidget()
        #self.plot_widget.linePositionChanged.connect(self.tu_funcion_para_manejar_cambio)
        self.ui.layout_graph.addWidget(self.plot_widget)
        
        self.serial_handler = SerialHandler('/dev/ttyUSB0', 115200)  # Ajusta 'COM3' al puerto correcto
        self.serial_thread = SerialReadThread(self.serial_handler)
        self.serial_thread.data_received.connect(self.handle_serial_data)
        self.serial_thread.start()

        #self.init_processor()
        # Inicializar detector de nistagmos
        self.nistagmo_detector = DetectorNistagmo(frecuencia_muestreo=200)  # Ajusta según FPS de tu cámara
        self.eye_positions_buffer = []
        
        # Timer para procesar nistagmos periódicamente (si deseas)
        self.nistagmo_timer = QTimer()
        self.nistagmo_timer.timeout.connect(self.process_nystagmus)
        self.nistagmo_timer.start(1000)  # Cada 1 segundo

        # Inicializar controlador de grabación
        self.setup_recording()

        self.showMaximized()

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

    def menu_presets(self):
        # Crear un menú personalizado
        menu = QMenu(self)

        # Agregar sliders con etiquetas al menú
        slider1 = self.create_labeled_slider("Brightness:", -64, 64, -21)
        slider2 = self.create_labeled_slider("Contrast", 0, 100, 50)
        
        # Crear un widget contenedor para el checkbox
        checkbox_container = QWidget()
        checkbox_layout = QHBoxLayout()
        checkbox_layout.setContentsMargins(5, 5, 5, 5)
        
        # Crear el checkbox
        self.ui.chk_use_yolo = QCheckBox("Usar YOLO (precisión)")
        self.ui.chk_use_yolo.setChecked(True)  # Activado por defecto
        self.ui.chk_use_yolo.setToolTip("Desactivar para mayor velocidad")
        
        # Añadir el checkbox al layout
        checkbox_layout.addWidget(self.ui.chk_use_yolo)
        checkbox_container.setLayout(checkbox_layout)
        
        # Conectar la señal
        self.ui.chk_use_yolo.toggled.connect(self.on_yolo_toggled)


        # Añadir widgets al menú usando QWidgetAction
        menu.addAction(self.create_widget_action(menu, checkbox_container))
        menu.addAction(self.create_widget_action(menu, slider1))
        menu.addAction(self.create_widget_action(menu, slider2))

        # Asignar el menú al QToolButton
        self.ui.toolButton.setMenu(menu)

        # Guardar referencias para acceso posterior
        self.brightness_slider = slider1.findChild(QSlider)
        self.contrast_slider = slider2.findChild(QSlider)

    def on_yolo_toggled(self, checked):
        """Maneja el evento cuando el checkbox de YOLO cambia"""
        print(f"Checkbox YOLO cambiado a: {'Activado' if checked else 'Desactivado'}")
        self.video_widget.set_yolo_enabled(checked)

    def create_labeled_slider(self, label_text, min_value, max_value, initial_value):
        """
        Crea un slider horizontal con una etiqueta a la izquierda.
        """
        # Crear el contenedor principal
        container = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)  # Ajustar márgenes

        # Crear la etiqueta
        label = QLabel(label_text)
        layout.addWidget(label)

        # Crear el slider
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(min_value)
        slider.setMaximum(max_value)
        slider.setValue(initial_value)
        slider.valueChanged.connect(lambda value: self.video_widget.set_video_color(label_text, value))
        layout.addWidget(slider)
        value = str(slider.value())
        label_value = QLabel(value)
        layout.addWidget(label_value)
        slider.valueChanged.connect(lambda value: label_value.setText(str(value)))

                         
        # Configurar el layout en el contenedor
        container.setLayout(layout)
        return container

    def create_widget_action(self, parent, widget):
        widget_action = QWidgetAction(parent)
        widget_action.setDefaultWidget(widget)
        return widget_action

    def handle_serial_data(self, data):
        # Dividir el string
        string_list = data.split(",")
        self.pos_hit = [float(string_list[0]), float(string_list[1]), float(string_list[2])]

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