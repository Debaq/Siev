import json
import os
import sys
from PySide6.QtWidgets import (QMainWindow, QMenu, QWidgetAction, QSlider, 
                            QHBoxLayout, QWidget, QLabel, QCheckBox, 
                            QMessageBox, QFileDialog, QPushButton)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtCore import QThread, Signal
from utils.SerialHandler import SerialHandler
from utils.VideoWidget import VideoWidget
from utils.DetectorNistagmo import DetectorNistagmo
from utils.EyeDataProcessor import EyeDataProcessor
from utils.RecordHandler import RecordingController

# Importar los nuevos módulos optimizados
from utils.graphing.triple_plot_widget import TriplePlotWidget

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
        
        # Cargar configuración
        self.load_config()
        
        # Configurar UI
        self.setupUi()
        
        # Configurar menús y presets
        self.menu_presets()
        
        # Variables de datos
        self.pos_eye = []
        self.pos_hit = []

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
            self.ui.cb_resolution
        )
        
        self.video_widget.sig_pos.connect(self.set_pos_eye)

        # === INICIALIZAR GRÁFICOS OPTIMIZADOS ===
        print("Inicializando sistema de gráficos optimizado...")
        self.plot_widget = TriplePlotWidget(
            parent=None,
            window_size=60,      # 60 segundos de ventana visible
            update_interval=50   # 20 FPS para gráficos (optimizado)
        )
        
        # Añadir widget de gráficos al layout
        self.ui.layout_graph.addWidget(self.plot_widget)
        
        # === INICIALIZAR COMUNICACIÓN SERIAL ===
        try:
            self.serial_handler = SerialHandler('/dev/ttyUSB0', 115200)
            self.serial_thread = SerialReadThread(self.serial_handler)
            self.serial_thread.data_received.connect(self.handle_serial_data)
            self.serial_thread.start()
            print("Comunicación serial iniciada en /dev/ttyUSB0")
        except Exception as e:
            print(f"Error iniciando comunicación serial: {e}")
            # Continuar sin serial para desarrollo/testing
            self.serial_handler = None
            self.serial_thread = None

        # === INICIALIZAR DETECTOR DE NISTAGMOS ===
        self.nistagmo_detector = DetectorNistagmo(frecuencia_muestreo=200)
        self.eye_positions_buffer = []
        
        # Timer para procesamiento de nistagmos (menos frecuente)
        self.nistagmo_timer = QTimer()
        self.nistagmo_timer.timeout.connect(self.process_nystagmus)
        self.nistagmo_timer.start(2000)  # Cada 2 segundos (optimizado)

        # === INICIALIZAR SISTEMA DE GRABACIÓN OPTIMIZADO ===
        self.setup_recording()

        # === CONFIGURAR INTERFAZ ADICIONAL ===
        self.setup_additional_ui()
        
        # === CONECTAR EVENTOS ===
        self.connect_events()

        # === ESTADÍSTICAS DE PERFORMANCE ===
        self.performance_timer = QTimer()
        self.performance_timer.timeout.connect(self.update_performance_display)
        self.performance_timer.start(5000)  # Cada 5 segundos

        # Mostrar ventana maximizada
        self.showMaximized()
        
        print("=== SISTEMA VNG OPTIMIZADO INICIADO ===")

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
                "app_name": "VNG App",
                "window_title": self.tr("VNG Application - Optimized"),
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
                # Crear UI mínima si no se encuentra la principal
                self._create_fallback_ui()
                return
        
        # Configurar la UI
        self.ui.setupUi(self)

    def _create_fallback_ui(self):
        """Crea una UI mínima de fallback si no se encuentra la principal"""
        from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
        
        # Widget central básico
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        
        # Crear objetos UI mínimos necesarios
        class FallbackUI:
            def __init__(self, parent):
                self.CameraFrame = QLabel("Camera Frame")
                self.CameraFrame.setMinimumSize(640, 480)
                self.CameraFrame.setStyleSheet("border: 1px solid black;")
                
                self.btn_start = QPushButton("Start/Stop")
                self.lbl_time = QLabel("00:00 / 05:00")
                
                # Layout para gráficos
                self.layout_graph = QHBoxLayout()
                
                # Sliders mínimos (crear con valores por defecto)
                self.slider_th_right = QSlider(Qt.Horizontal)
                self.slider_th_left = QSlider(Qt.Horizontal)
                self.slider_erode_right = QSlider(Qt.Horizontal)
                self.slider_erode_left = QSlider(Qt.Horizontal)
                self.slider_nose_width = QSlider(Qt.Horizontal)
                
                # ComboBox para resolución
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
        
        # Añadir elementos al layout
        main_layout.addWidget(self.ui.CameraFrame)
        main_layout.addWidget(self.ui.btn_start)
        main_layout.addWidget(self.ui.lbl_time)
        main_layout.addLayout(self.ui.layout_graph)

    def menu_presets(self):
        """Crear menú personalizado con controles de cámara"""
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

        # Asignar el menú al QToolButton si existe
        if hasattr(self.ui, 'toolButton'):
            self.ui.toolButton.setMenu(menu)

        # Guardar referencias para acceso posterior
        self.brightness_slider = slider1.findChild(QSlider)
        self.contrast_slider = slider2.findChild(QSlider)

    def setup_additional_ui(self):
        """Configura elementos adicionales de la interfaz"""
        # Crear botones de control adicionales
        if hasattr(self.ui, 'layout_toolbar'):
            # Botón para exportar datos
            self.btn_export = QPushButton("Exportar CSV")
            self.btn_export.setToolTip("Exportar datos de grabación a CSV")
            self.btn_export.clicked.connect(self.export_recording_data)
            self.ui.layout_toolbar.addWidget(self.btn_export)
            
            # Botón para cargar datos
            self.btn_load = QPushButton("Cargar CSV")
            self.btn_load.setToolTip("Cargar datos desde archivo CSV")
            self.btn_load.clicked.connect(self.load_recording_data)
            self.ui.layout_toolbar.addWidget(self.btn_load)
            
            # Botón para optimizar performance
            self.btn_optimize = QPushButton("Optimizar")
            self.btn_optimize.setToolTip("Aplicar optimizaciones automáticas")
            self.btn_optimize.clicked.connect(self.apply_optimizations)
            self.ui.layout_toolbar.addWidget(self.btn_optimize)
            
            # Label para estadísticas
            self.lbl_stats = QLabel("Sistema optimizado listo")
            self.ui.layout_toolbar.addWidget(self.lbl_stats)

    def connect_events(self):
        """Conecta eventos y señales adicionales"""
        # Conectar eventos del menú si existen
        if hasattr(self.ui, 'menuArchivo'):
            # Conectar acciones del menú
            if hasattr(self.ui, 'actionSalir'):
                self.ui.actionSalir.triggered.connect(self.close)
        
        # Conectar eventos de gráficos
        if hasattr(self.plot_widget, 'linePositionChanged'):
            self.plot_widget.linePositionChanged.connect(self.on_graph_line_changed)

    def on_yolo_toggled(self, checked):
        """Maneja el evento cuando el checkbox de YOLO cambia"""
        print(f"Checkbox YOLO cambiado a: {'Activado' if checked else 'Desactivado'}")
        if hasattr(self.video_widget, 'set_yolo_enabled'):
            self.video_widget.set_yolo_enabled(checked)

    def create_labeled_slider(self, label_text, min_value, max_value, initial_value):
        """Crea un slider horizontal con una etiqueta a la izquierda."""
        container = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)

        # Crear la etiqueta
        label = QLabel(label_text)
        layout.addWidget(label)

        # Crear el slider
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(min_value)
        slider.setMaximum(max_value)
        slider.setValue(initial_value)
        
        # Conectar al video widget si existe
        if hasattr(self, 'video_widget'):
            slider.valueChanged.connect(
                lambda value: self.video_widget.set_video_color(label_text, value)
            )
        
        layout.addWidget(slider)
        
        # Label para mostrar valor
        value_label = QLabel(str(initial_value))
        layout.addWidget(value_label)
        slider.valueChanged.connect(lambda value: value_label.setText(str(value)))
                         
        container.setLayout(layout)
        return container

    def create_widget_action(self, parent, widget):
        """Crea una QWidgetAction para añadir widgets a menús"""
        widget_action = QWidgetAction(parent)
        widget_action.setDefaultWidget(widget)
        return widget_action

    def handle_serial_data(self, data):
        """Maneja datos recibidos del puerto serial"""
        try:
            # Dividir el string
            string_list = data.split(",")
            if len(string_list) >= 3:
                self.pos_hit = [float(string_list[0]), float(string_list[1]), float(string_list[2])]
        except (ValueError, IndexError) as e:
            print(f"Error procesando datos serial: {e}")

    def process_nystagmus(self):
        """Procesa nistagmos de manera optimizada (menos frecuente)"""
        # Solo procesar si hay suficientes datos
        if len(self.eye_positions_buffer) > 100:  # Aumentado el umbral
            try:
                # Procesar los datos
                resultados = self.nistagmo_detector.procesar_datos(self.eye_positions_buffer)
                
                # Mostrar resultados solo si hay nistagmos
                if resultados['total_nistagmos'] > 0:
                    print(f"VCL promedio: {resultados['vcl_promedio']:.2f}°/s")
                    print(f"Nistagmos detectados: {resultados['total_nistagmos']}")
                    
                    # Actualizar UI si hay elemento para VCL
                    if hasattr(self.ui, 'lbl_vcl'):
                        self.ui.lbl_vcl.setText(f"VCL: {resultados['vcl_promedio']:.2f}°/s")
                        
            except Exception as e:
                print(f"Error en procesamiento de nistagmos: {e}")

    def export_recording_data(self):
        """Exporta los datos de grabación a un archivo CSV"""
        try:
            # Abrir diálogo para seleccionar archivo
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Exportar datos de grabación",
                f"vng_export_{int(time.time())}.csv",
                "CSV Files (*.csv);;All Files (*)"
            )
            
            if filename:
                # Usar el sistema optimizado de exportación
                success = self.export_recording_data_to_file(filename)
                
                if success:
                    # Obtener estadísticas para mostrar
                    stats = self.get_recording_statistics()
                    
                    QMessageBox.information(
                        self,
                        "Exportación exitosa",
                        f"Datos exportados exitosamente a:\n{filename}\n\n"
                        f"Total de muestras: {stats.get('total_samples', 0)}\n"
                        f"Duración: {stats.get('duration_seconds', 0):.1f}s"
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Error de exportación",
                        "No se pudieron exportar los datos.\nVerifique que haya datos grabados y permisos de escritura."
                    )
                    
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error durante la exportación: {str(e)}"
            )

    def load_recording_data(self):
        """Carga datos desde un archivo CSV"""
        try:
            filename, _ = QFileDialog.getOpenFileName(
                self,
                "Cargar datos de grabación",
                "",
                "CSV Files (*.csv);;All Files (*)"
            )
            
            if filename:
                success = self.load_recording_data_from_file(filename)
                
                if success:
                    QMessageBox.information(
                        self,
                        "Carga exitosa",
                        f"Datos cargados exitosamente desde:\n{filename}"
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Error de carga",
                        "No se pudieron cargar los datos.\nVerifique que el archivo sea válido."
                    )
                    
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error durante la carga: {str(e)}"
            )

    def apply_optimizations(self):
        """Aplica optimizaciones automáticas del sistema"""
        try:
            # Aplicar optimizaciones en el controlador de grabación
            if hasattr(self, 'optimize_performance'):
                self.optimize_performance()
            
            # Aplicar optimizaciones en los gráficos
            if hasattr(self.plot_widget, 'optimize_performance'):
                self.plot_widget.optimize_performance()
            
            # Mostrar mensaje de confirmación
            QMessageBox.information(
                self,
                "Optimización aplicada",
                "Se han aplicado optimizaciones automáticas al sistema.\n"
                "El rendimiento debería mejorar especialmente durante grabaciones largas."
            )
            
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error de optimización",
                f"Error aplicando optimizaciones: {str(e)}"
            )

    def update_performance_display(self):
        """Actualiza la información de performance en la UI"""
        try:
            if hasattr(self, 'get_system_status'):
                status = self.get_system_status()
                
                # Crear texto de estado
                status_text = f"Sistema: "
                
                if status.get('is_recording', False):
                    status_text += f"GRABANDO | "
                elif status.get('is_calibrating', False):
                    status_text += f"CALIBRANDO | "
                else:
                    status_text += f"LISTO | "
                
                # Añadir eficiencia si está disponible
                efficiency = status.get('graph_efficiency', 0)
                status_text += f"Eficiencia: {efficiency:.1f}%"
                
                # Actualizar label si existe
                if hasattr(self, 'lbl_stats'):
                    self.lbl_stats.setText(status_text)
                    
        except Exception as e:
            print(f"Error actualizando display de performance: {e}")

    def on_graph_line_changed(self, position):
        """Maneja cambios en la línea de tiempo del gráfico"""
        # Opcional: actualizar información basada en la posición de la línea
        pass

    def closeEvent(self, event):
        """Maneja el evento de cierre de la aplicación"""
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
            
            if hasattr(self, 'performance_timer'):
                self.performance_timer.stop()
            
            print("Aplicación cerrada correctamente")
            
        except Exception as e:
            print(f"Error durante el cierre: {e}")
        
        super().closeEvent(event)