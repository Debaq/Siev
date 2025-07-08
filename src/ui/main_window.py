import json
import os
import sys
from PySide6.QtWidgets import (QMainWindow, QMenu, QWidgetAction, QSlider, 
                            QHBoxLayout, QWidget, QLabel, QCheckBox, 
                            QMessageBox, QPushButton, QDialog, QVBoxLayout, 
                            QRadioButton, QButtonGroup)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtCore import QThread, Signal
from utils.SerialHandler import SerialHandler
from utils.VideoWidget import VideoWidget
from utils.DetectorNistagmo import DetectorNistagmo
from utils.EyeDataProcessor import EyeDataProcessor
from utils.RecordHandler import RecordingController
from utils.CalibrationManager import CalibrationManager
from ui.calibration_dialog import CalibrationDialog

# Importar los módulos de gráficos optimizados
from utils.graphing.triple_plot_widget import TriplePlotWidget
from utils.graphing.triple_plot_widget import PlotConfigurations


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


class TrackingCalibrationDialog(QDialog):
    """
    Ventana modal para decidir si calibrar seguimiento primero
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Configuración de Seguimiento")
        self.setModal(True)
        self.setFixedSize(400, 200)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint)
        
        self.user_choice = None
        self.setup_ui()
    
    def setup_ui(self):
        """Configura la interfaz de usuario"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Título
        title = QLabel("Configuración de Seguimiento Ocular")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Mensaje explicativo
        message = QLabel(
            "Para una calibración precisa se recomienda\n"
            "ajustar primero el seguimiento ocular con los sliders."
        )
        message.setAlignment(Qt.AlignCenter)
        message.setStyleSheet("font-size: 12px; color: #666; margin-bottom: 15px;")
        layout.addWidget(message)
        
        # Botones
        button_layout = QHBoxLayout()
        
        self.continue_btn = QPushButton("Calibrar Seguimiento Primero")
        self.continue_btn.clicked.connect(self.choose_tracking_first)
        self.continue_btn.setStyleSheet("""
            QPushButton {
                font-size: 12px;
                padding: 10px 15px;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        self.skip_btn = QPushButton("Saltar a Calibración")
        self.skip_btn.clicked.connect(self.skip_to_calibration)
        self.skip_btn.setStyleSheet("""
            QPushButton {
                font-size: 12px;
                padding: 10px 15px;
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        
        button_layout.addWidget(self.continue_btn)
        button_layout.addWidget(self.skip_btn)
        
        layout.addLayout(button_layout)
    
    def choose_tracking_first(self):
        """Usuario eligió calibrar seguimiento primero"""
        self.user_choice = "tracking_first"
        self.accept()
    
    def skip_to_calibration(self):
        """Usuario eligió saltar directo a calibración"""
        self.user_choice = "skip_to_calibration"
        self.accept()
    
    def get_user_choice(self):
        """Retorna la elección del usuario"""
        return self.user_choice


class ProtocolSelectionDialog(QDialog):
    """
    Ventana modal de selección de protocolo con lista de radiobuttons
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Selección de Protocolo")
        self.setModal(True)
        self.setFixedSize(350, 250)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint)
        
        self.selected_protocol = None
        self.setup_ui()
    
    def setup_ui(self):
        """Configura la interfaz de usuario"""
        from PySide6.QtWidgets import QVBoxLayout, QRadioButton, QButtonGroup
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Título
        title = QLabel("Seleccione el protocolo de evaluación:")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Grupo de radiobuttons para selección única
        self.button_group = QButtonGroup()
        
        # Opciones de protocolo
        protocols = [
            ("Bitermal Alternada", "bitermal_alternada"),
            ("Monotermal Caliente", "monotermal_caliente"), 
            ("Monotermal Fría", "monotermal_fria"),
            ("Sin Protocolo", "sin_protocolo")
        ]
        
        self.protocol_buttons = {}
        
        for display_name, protocol_id in protocols:
            radio_btn = QRadioButton(display_name)
            radio_btn.setStyleSheet("font-size: 12px; padding: 5px;")
            self.button_group.addButton(radio_btn)
            self.protocol_buttons[radio_btn] = protocol_id
            layout.addWidget(radio_btn)
        
        # Seleccionar el primer protocolo por defecto
        list(self.protocol_buttons.keys())[0].setChecked(True)
        
        # Espaciador
        layout.addStretch()
        
        # Botón de confirmación
        self.accept_btn = QPushButton("Continuar")
        self.accept_btn.setDefault(True)
        self.accept_btn.clicked.connect(self.accept_selection)
        self.accept_btn.setStyleSheet("""
            QPushButton {
                font-size: 12px;
                padding: 8px 20px;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        # Layout para centrar el botón
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.accept_btn)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
    
    def accept_selection(self):
        """Acepta la selección y cierra el diálogo"""
        # Encontrar el radiobutton seleccionado
        for radio_btn, protocol_id in self.protocol_buttons.items():
            if radio_btn.isChecked():
                self.selected_protocol = protocol_id
                break
        
        self.accept()
    
    def get_selected_protocol(self):
        """Retorna el protocolo seleccionado"""
        return self.selected_protocol


class MainWindow(QMainWindow, RecordingController):
    def __init__(self):
        super().__init__()
        
        # Cargar configuración
        self.load_config()
        
        # Configurar UI
        self.setupUi()
        
        # Variables de datos
        self.pos_eye = []
        self.pos_hit = []
        
        # === CONFIGURACIÓN DE CÁMARA ===
        self.camera_index = 3

        # === INICIALIZAR PROCESAMIENTO DE VIDEO ===
        self.slider_thresholds = [
            self.ui.slider_th_right, 
            self.ui.slider_th_left,
            self.ui.slider_erode_right,
            self.ui.slider_erode_left,
            self.ui.slider_nose_width
        ]
        
        self.video_widget = VideoWidget(
            self.ui.CameraFrame, 
            self.slider_thresholds,
            self.ui.cb_resolution,
            camera_id=self.camera_index
        )
        
        # Conectar al sistema de grabación
        self.video_widget.sig_pos.connect(self.set_pos_eye)

        # === INICIALIZAR COMUNICACIÓN SERIAL ===
        try:
            self.serial_handler = SerialHandler('/dev/ttyUSB0', 115200)
            self.serial_thread = SerialReadThread(self.serial_handler)
            self.serial_thread.data_received.connect(self.handle_serial_data)
            self.serial_thread.start()
            print("Comunicación serial iniciada en /dev/ttyUSB0")
        except Exception as e:
            print(f"Error iniciando comunicación serial: {e}")
            self.serial_handler = None
            self.serial_thread = None

        # === INICIALIZAR SISTEMA DE CALIBRACIÓN ===
        self.calibration_manager = CalibrationManager(self.serial_handler)
        self.calibration_controller = None
        
        # === INICIALIZAR GRÁFICOS OPTIMIZADOS ===
        print("Inicializando sistema de gráficos...")
        config = PlotConfigurations.get_horizontal_only()  # Solo movimientos horizontales por defecto

        self.plot_widget = TriplePlotWidget(
            parent=None,
            window_size=60,
            update_interval=50,
            plot_config=config
        )
        
        # Añadir widget de gráficos al layout
        self.ui.layout_graph.addWidget(self.plot_widget)

        # === INICIALIZAR DETECTOR DE NISTAGMOS ===
        self.nistagmo_detector = DetectorNistagmo(frecuencia_muestreo=200)
        self.eye_positions_buffer = []
        
        # Timer para procesamiento de nistagmos
        self.nistagmo_timer = QTimer()
        self.nistagmo_timer.timeout.connect(self.process_nystagmus)
        self.nistagmo_timer.start(2000)

        # === INICIALIZAR SISTEMA DE GRABACIÓN ===
        self.setup_recording()

        # === CONFIGURAR INTERFAZ ===
        self.setup_menu_and_controls()
        self.connect_events()
        
        # === CARGAR CONFIGURACIÓN DE SLIDERS ===
        self.load_slider_configuration()
        
        # === MOSTRAR SELECCIÓN DE PROTOCOLO ===
        QTimer.singleShot(500, self.show_protocol_selection)

        # Mostrar ventana maximizada
        self.showMaximized()
        
        print("=== SISTEMA VNG INICIADO ===")

    def load_config(self):
        """Cargar configuración desde config.json"""
        if getattr(sys, "frozen", False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        config_path = os.path.join(base_path, "config", "config.json")
        try:
            with open(config_path, "r") as f:
                self.config = json.load(f)
            
            self.setWindowTitle(self.tr(self.config["window_title"]))
            self.resize(
                self.config["window_size"]["width"],
                self.config["window_size"]["height"]
            )
        except Exception as e:
            print(self.tr("Error loading configuration: {}").format(e))
            self.config = {
                "app_name": "VNG App",
                "window_title": self.tr("VNG Application"),
                "window_size": {"width": 800, "height": 600}
            }
            self.setWindowTitle(self.config["window_title"])
            self.resize(
                self.config["window_size"]["width"],
                self.config["window_size"]["height"]
            )
    
    def setupUi(self):
        """Configurar la interfaz de usuario"""
        try:
            from .main_ui import Ui_MainWindow
            self.ui = Ui_MainWindow()
            print(self.tr("Loading custom UI from main_ui.py"))
        except ImportError:
            try:
                from ui.main_ui import Ui_MainWindow
                self.ui = Ui_MainWindow()
                print(self.tr("Loading UI from ui.main_ui"))
            except ImportError:
                print(self.tr("Warning: Could not load custom UI, using fallback"))
                self._create_fallback_ui()
                return
        
        self.ui.setupUi(self)

    def _create_fallback_ui(self):
        """Crea una UI mínima de fallback"""
        from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        class FallbackUI:
            def __init__(self, parent):
                self.CameraFrame = QLabel("Camera Frame")
                self.CameraFrame.setMinimumSize(640, 480)
                self.CameraFrame.setStyleSheet("border: 1px solid black;")
                
                self.btn_start = QPushButton("Start/Stop")
                self.lbl_time = QLabel("00:00 / 05:00")
                
                self.layout_graph = QHBoxLayout()
                self.layout_toolbar = QHBoxLayout()
                
                # Sliders mínimos
                self.slider_th_right = QSlider(Qt.Horizontal)
                self.slider_th_left = QSlider(Qt.Horizontal)
                self.slider_erode_right = QSlider(Qt.Horizontal)
                self.slider_erode_left = QSlider(Qt.Horizontal)
                self.slider_nose_width = QSlider(Qt.Horizontal)
                
                from PySide6.QtWidgets import QComboBox
                self.cb_resolution = QComboBox()
                self.cb_resolution.addItems([
                    "1028x720@120",
                    "960x540@120", 
                    "640x360@210",
                    "420x240@210",
                    "320x240@210"
                ])
                self.cb_resolution.setCurrentIndex(1)
        
        self.ui = FallbackUI(self)
        
        main_layout.addWidget(self.ui.CameraFrame)
        main_layout.addWidget(self.ui.btn_start)
        main_layout.addWidget(self.ui.lbl_time)
        main_layout.addLayout(self.ui.layout_graph)

    def show_protocol_selection(self):
        """Muestra la ventana de selección de protocolo al inicio."""
        dialog = ProtocolSelectionDialog(self)
        result = dialog.exec()
        
        # Siempre habrá una selección porque no hay botón cancelar
        if result == QDialog.Accepted:
            selected_protocol = dialog.get_selected_protocol()
            print(f"Protocolo seleccionado: {selected_protocol}")
            
            if selected_protocol != "sin_protocolo":
                # Si hay protocolo, mostrar opción de seguimiento
                QTimer.singleShot(500, self.show_tracking_calibration_choice)
            else:
                print("Iniciando sin protocolo - sistema listo")
        else:
            # En caso de que se cierre la ventana de alguna forma, usar protocolo por defecto
            print("Usando protocolo por defecto: sin protocolo")
            selected_protocol = "sin_protocolo"
    
    def show_tracking_calibration_choice(self):
        """Muestra la ventana de elección para calibración de seguimiento."""
        dialog = TrackingCalibrationDialog(self)
        result = dialog.exec()
        
        if result == QDialog.Accepted:
            choice = dialog.get_user_choice()
            print(f"Elección de seguimiento: {choice}")
            
            if choice == "tracking_first":
                # Usuario quiere calibrar seguimiento primero
                self.start_tracking_adjustment_mode()
            elif choice == "skip_to_calibration":
                # Usuario quiere saltar directo a calibración
                QTimer.singleShot(1000, self.start_calibration)
        else:
            # Por defecto, ir a ajuste de seguimiento
            self.start_tracking_adjustment_mode()
    
    def start_tracking_adjustment_mode(self):
        """Inicia el modo de ajuste de seguimiento."""
        print("=== MODO AJUSTE DE SEGUIMIENTO ===")
        
        # Cambiar el botón Start por "Continuar Calibración"
        if hasattr(self.ui, 'btn_start'):
            self.ui.btn_start.setText("Continuar Calibración")
            self.ui.btn_start.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    font-weight: bold;
                    font-size: 14px;
                    padding: 10px;
                    border: none;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
            
            # Desconectar eventos anteriores y conectar nuevo
            try:
                self.ui.btn_start.clicked.disconnect()
            except:
                pass
            self.ui.btn_start.clicked.connect(self.continue_to_calibration)
        
        # Mostrar mensaje en el label de tiempo
        if hasattr(self.ui, 'lbl_time'):
            self.ui.lbl_time.setText("AJUSTE EL SEGUIMIENTO CON LOS SLIDERS")
            self.ui.lbl_time.setStyleSheet("""
                QLabel {
                    color: #FF9800;
                    font-weight: bold;
                    font-size: 14px;
                }
            """)
        
        print("Ajuste los sliders de seguimiento y presione 'Continuar Calibración'")
    
    def continue_to_calibration(self):
        """Continúa a la calibración después del ajuste de seguimiento."""
        print("Guardando configuración de sliders y continuando a calibración...")
        
        # Guardar configuración actual de sliders
        self.save_slider_configuration()
        
        # Restaurar botón Start a su función original
        if hasattr(self.ui, 'btn_start'):
            self.ui.btn_start.setText("Start")
            self.ui.btn_start.setStyleSheet("")  # Limpiar estilos personalizados
            
            # Reconectar a función de grabación original
            try:
                self.ui.btn_start.clicked.disconnect()
            except:
                pass
            self.ui.btn_start.clicked.connect(self.toggle_recording)
        
        # Restaurar label de tiempo
        if hasattr(self.ui, 'lbl_time'):
            self.ui.lbl_time.setText("00:00 / 05:00")
            self.ui.lbl_time.setStyleSheet("")  # Limpiar estilos
        
        # Iniciar calibración
        QTimer.singleShot(500, self.start_calibration)
    
    def save_slider_configuration(self):
        """Guarda la configuración actual de los sliders en config.json."""
        try:
            # Obtener valores actuales de sliders
            slider_config = {
                "slider_th_right": self.ui.slider_th_right.value(),
                "slider_th_left": self.ui.slider_th_left.value(), 
                "slider_erode_right": self.ui.slider_erode_right.value(),
                "slider_erode_left": self.ui.slider_erode_left.value(),
                "slider_nose_width": self.ui.slider_nose_width.value()
            }
            
            # Añadir a configuración existente
            self.config["slider_settings"] = slider_config
            
            # Guardar en archivo
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                "config", "config.json"
            )
            
            with open(config_path, "w") as f:
                json.dump(self.config, f, indent=4)
            
            print(f"Configuración de sliders guardada: {slider_config}")
            
        except Exception as e:
            print(f"Error guardando configuración de sliders: {e}")
    
    def load_slider_configuration(self):
        """Carga la configuración de sliders desde config.json."""
        try:
            if "slider_settings" in self.config:
                slider_config = self.config["slider_settings"]
                
                # Aplicar valores guardados a los sliders
                self.ui.slider_th_right.setValue(slider_config.get("slider_th_right", 0))
                self.ui.slider_th_left.setValue(slider_config.get("slider_th_left", 0))
                self.ui.slider_erode_right.setValue(slider_config.get("slider_erode_right", 0))
                self.ui.slider_erode_left.setValue(slider_config.get("slider_erode_left", 0))
                self.ui.slider_nose_width.setValue(slider_config.get("slider_nose_width", 25))
                
                print(f"Configuración de sliders cargada: {slider_config}")
            else:
                print("No hay configuración de sliders guardada, usando valores por defecto")
                
        except Exception as e:
            print(f"Error cargando configuración de sliders: {e}")

    def setup_menu_and_controls(self):
        """Configura menú y controles adicionales"""
        # Crear menú personalizado con controles de cámara
        menu = QMenu(self)

        # Sliders para controles de cámara
        slider1 = self.create_labeled_slider("Brightness:", -64, 64, -21)
        slider2 = self.create_labeled_slider("Contrast", 0, 100, 50)
        
        # Checkbox para YOLO
        checkbox_container = QWidget()
        checkbox_layout = QHBoxLayout()
        checkbox_layout.setContentsMargins(5, 5, 5, 5)
        
        self.ui.chk_use_yolo = QCheckBox("Usar YOLO (precisión)")
        self.ui.chk_use_yolo.setChecked(True)
        self.ui.chk_use_yolo.setToolTip("Desactivar para mayor velocidad")
        self.ui.chk_use_yolo.toggled.connect(self.on_yolo_toggled)
        
        checkbox_layout.addWidget(self.ui.chk_use_yolo)
        checkbox_container.setLayout(checkbox_layout)

        # Añadir al menú
        menu.addAction(self.create_widget_action(menu, checkbox_container))
        menu.addAction(self.create_widget_action(menu, slider1))
        menu.addAction(self.create_widget_action(menu, slider2))

        # Asignar menú al toolButton si existe
        if hasattr(self.ui, 'toolButton'):
            self.ui.toolButton.setMenu(menu)

        # Guardar referencias
        self.brightness_slider = slider1.findChild(QSlider)
        self.contrast_slider = slider2.findChild(QSlider)
        
        # Añadir botón de calibración en la toolbar
        if hasattr(self.ui, 'layout_toolbar'):
            self.btn_calibrate = QPushButton("Calibrar Sistema")
            self.btn_calibrate.setToolTip("Iniciar proceso de calibración ocular")
            self.btn_calibrate.clicked.connect(self.start_calibration)
            self.ui.layout_toolbar.addWidget(self.btn_calibrate)

    def connect_events(self):
        """Conecta eventos y señales"""
        if hasattr(self.ui, 'menuArchivo'):
            if hasattr(self.ui, 'actionSalir'):
                self.ui.actionSalir.triggered.connect(self.close)
        
        if hasattr(self.plot_widget, 'linePositionChanged'):
            self.plot_widget.linePositionChanged.connect(self.on_graph_line_changed)


    def start_calibration(self):
        """Inicia el proceso de calibración SIN CONTROLLER."""
        if not self.serial_handler:
            QMessageBox.warning(
                self,
                "Error de Calibración",
                "No hay conexión serial disponible.\nVerifique la conexión del dispositivo IMU."
            )
            return
        
        print("Iniciando proceso de calibración SIMPLIFICADO...")
        
        # Crear el dialog DIRECTAMENTE con el manager
        from ui.calibration_dialog import CalibrationDialog
        
        calibration_dialog = CalibrationDialog(
            calibration_manager=self.calibration_manager,
            parent_window=self  # Pasar referencia a MainWindow
        )
        
        # Conectar señal de finalización
        calibration_dialog.calibration_finished.connect(self.on_calibration_finished)
        
        # Mostrar dialog modal
        result = calibration_dialog.exec()
        
        if result == QDialog.Accepted:
            print("Calibración completada exitosamente")
        else:
            print("Calibración cancelada")

    def on_calibration_finished(self, success):
        """Maneja el final de la calibración."""
        if success:
            print("=== CALIBRACIÓN EXITOSA ===")
            summary = self.calibration_manager.get_calibration_summary()
            print(f"Ángulo teórico: {summary['theoretical_angle']:.1f}°")
            
            # Actualizar UI
            if hasattr(self, 'btn_calibrate'):
                self.btn_calibrate.setText("Sistema Calibrado ✓")
                self.btn_calibrate.setStyleSheet("color: green; font-weight: bold;")
            
            # Actualizar límites del gráfico
            self.update_graph_limits_after_calibration()
            
            # Mostrar mensaje de éxito
            QMessageBox.information(
                self,
                "Calibración Exitosa",
                f"El sistema ha sido calibrado correctamente.\n\n"
                f"Ángulo medido: {summary['theoretical_angle']:.1f}°\n"
                f"Los gráficos ahora mostrarán datos en grados."
            )
        else:
            print("Calibración cancelada o falló")
            QMessageBox.information(
                self,
                "Calibración Cancelada",
                "La calibración no se completó."
            )


    def on_yolo_toggled(self, checked):
        """Maneja el cambio del checkbox YOLO"""
        print(f"Checkbox YOLO cambiado a: {'Activado' if checked else 'Desactivado'}")
        if hasattr(self.video_widget, 'set_yolo_enabled'):
            self.video_widget.set_yolo_enabled(checked)

    def create_labeled_slider(self, label_text, min_value, max_value, initial_value):
        """Crea un slider con etiqueta"""
        container = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)

        label = QLabel(label_text)
        layout.addWidget(label)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(min_value)
        slider.setMaximum(max_value)
        slider.setValue(initial_value)
        
        if hasattr(self, 'video_widget'):
            slider.valueChanged.connect(
                lambda value: self.video_widget.set_video_color(label_text, value)
            )
        
        layout.addWidget(slider)
        
        value_label = QLabel(str(initial_value))
        layout.addWidget(value_label)
        slider.valueChanged.connect(lambda value: value_label.setText(str(value)))
                         
        container.setLayout(layout)
        return container

    def create_widget_action(self, parent, widget):
        """Crea una QWidgetAction para menús"""
        widget_action = QWidgetAction(parent)
        widget_action.setDefaultWidget(widget)
        return widget_action

    def handle_serial_data(self, data):
        """Maneja datos del puerto serial"""
        try:
            string_list = data.split(",")
            if len(string_list) >= 3:
                self.pos_hit = [float(string_list[0]), float(string_list[1]), float(string_list[2])]
        except (ValueError, IndexError) as e:
            print(f"Error procesando datos serial: {e}")

    def set_pos_eye(self, pos):
        """
        Procesa posiciones oculares - INTEGRADO CON CALIBRACIÓN
        """
        self.pos_eye = pos
        
        # Si hay calibración en progreso, enviar datos al controlador
        if hasattr(self, 'calibration_in_progress') and self.calibration_in_progress:
            if self.calibration_controller:
                left_eye = self.pos_eye[1]  # Según tu estructura
                right_eye = self.pos_eye[0]
                self.calibration_controller.process_eye_positions(left_eye, right_eye)
        
        # Procesar datos normalmente para grabación/visualización
        if hasattr(self, 'send_to_graph') and self.send_to_graph:
            left_eye = self.pos_eye[1]
            right_eye = self.pos_eye[0]
            
            # APLICAR CALIBRACIÓN SI ESTÁ DISPONIBLE
            if self.calibration_manager.is_calibrated:
                left_eye_degrees, right_eye_degrees = self.calibration_manager.convert_to_degrees(
                    left_eye, right_eye
                )
                # Usar datos calibrados en grados
                processed_left = left_eye_degrees
                processed_right = right_eye_degrees
            else:
                # Usar datos en píxeles si no hay calibración
                processed_left = left_eye
                processed_right = right_eye
            
            # Procesar a través del EyeDataProcessor
            processed_points = self.eye_processor.process_eye_data(
                processed_left, 
                processed_right, 
                float(self.pos_hit[0]),
                float(self.pos_hit[1]),
                self.graph_time
            )
            
            # Continuar con el sistema de grabación existente
            if self.is_recording:
                for point in processed_points:
                    processed_left, processed_right, imu_x, imu_y, point_time = point
                    self.data_storage.add_data_point(
                        processed_left, processed_right, imu_x, imu_y, point_time
                    )
                    self.total_data_points += 1
            
            # Enviar a gráficos
            current_time = time.time()
            if current_time - self.last_graph_update >= (self.graph_update_interval / 1000.0):
                if processed_points:
                    latest_point = processed_points[-1]
                    self.graph_data_buffer.append(latest_point)
                    self.last_graph_update = current_time

    def process_nystagmus(self):
        """Procesa nistagmos (simplificado)"""
        if len(self.eye_positions_buffer) > 100:
            try:
                resultados = self.nistagmo_detector.procesar_datos(self.eye_positions_buffer)
                if resultados['total_nistagmos'] > 0:
                    print(f"VCL promedio: {resultados['vcl_promedio']:.2f}°/s")
                    print(f"Nistagmos detectados: {resultados['total_nistagmos']}")
            except Exception as e:
                print(f"Error en procesamiento de nistagmos: {e}")

    def on_graph_line_changed(self, position):
        """Maneja cambios en la línea de tiempo del gráfico"""
        pass

    def update_graph_limits_after_calibration(self):
        """
        Actualiza los límites del gráfico después de calibración exitosa.
        Usa los grados calculados + margen configurable.
        """
        if not self.calibration_manager.is_calibrated:
            return
        
        summary = self.calibration_manager.get_calibration_summary()
        theoretical_angle = summary['theoretical_angle']
        
        # Calcular límites: ángulo teórico + margen
        margin = CalibrationDialog.GRAPH_MARGIN_DEGREES
        max_limit = theoretical_angle / 2 + margin  # La mitad del ángulo + margen
        min_limit = -max_limit
        
        print(f"Actualizando límites del gráfico:")
        print(f"  Rango: {min_limit:.1f}° a {max_limit:.1f}°")
        print(f"  Unidades: GRADOS (calibrado)")
        
        # TODO: Aplicar límites a los gráficos
        # Esto requerirá acceso a los plots del TriplePlotWidget
        
        # Actualizar título o etiquetas para indicar que está calibrado
        if hasattr(self, 'btn_calibrate'):
            self.btn_calibrate.setText("Sistema Calibrado ✓")
            self.btn_calibrate.setStyleSheet("color: green; font-weight: bold;")

            # APLICAR A LOS PLOTS REALES
        for plot in self.plot_widget.plots:
            plot.setYRange(min_limit, max_limit)

    def closeEvent(self, event):
        """Maneja el cierre de la aplicación"""
        try:
            print("Cerrando aplicación VNG...")
            
            # Detener grabación si está activa
            if hasattr(self, 'is_recording') and self.is_recording:
                print("Deteniendo grabación...")
                self.stop_recording()
            
            # Limpiar video widget
            if hasattr(self, 'video_widget'):
                print("Cerrando sistema de video...")
                self.video_widget.cleanup()
            
            # Detener thread serial
            if hasattr(self, 'serial_thread') and self.serial_thread:
                print("Cerrando comunicación serial...")
                self.serial_thread.stop()
            
            # Detener timers
            if hasattr(self, 'nistagmo_timer'):
                self.nistagmo_timer.stop()
            
            print("Aplicación cerrada correctamente")
            
        except Exception as e:
            print(f"Error durante el cierre: {e}")
        
        super().closeEvent(event)