import json
import os
import sys
import time
from PySide6.QtWidgets import (QMainWindow, QMenu, QWidgetAction, QSlider, 
                            QHBoxLayout, QWidget, QLabel, QCheckBox, 
                            QMessageBox, QPushButton, QDialog)
from PySide6.QtCore import Qt, QTimer

# Diálogos
from ui.dialogs.protocol_dialog import ProtocolSelectionDialog
from ui.dialogs.tracking_dialog import TrackingCalibrationDialog

# Utils
from utils.serial_thread import SerialReadThread
from utils.stimulus_system import StimulusManager
from utils.SerialHandler import SerialHandler
from utils.VideoWidget import VideoWidget
from utils.DetectorNistagmo import DetectorNistagmo
from utils.EyeDataProcessor import EyeDataProcessor
from utils.CalibrationManager import CalibrationManager
from utils.data_storage import DataStorage
from utils.graphing.triple_plot_widget import TriplePlotWidget, PlotConfigurations
from utils.config_manager import ConfigManager
from utils.CameraResolutionDetector import CameraResolutionDetector
from utils.utils import select_max_resolution



class MainWindow(QMainWindow):
    """Ventana principal del sistema VNG - Versión limpia y funcional"""
    
    def __init__(self):
        super().__init__()
        
        # === CONFIGURACIÓN BÁSICA ===
        self.config_manager = ConfigManager()
        
        
        self.setupUi() #==> crea a self.ui
        self.load_config()
        
        # === VARIABLES DE ESTADO ===
        self.pos_eye = []
        self.pos_hit = [0.0, 0.0, 0.0]  # IMU data
        self.camera_index = 2
        res_video = CameraResolutionDetector()
        resolution_video =res_video.listar_resoluciones(self.camera_index)
        #aca vamos a seleccionar la mejor resolución
        max_res = select_max_resolution(resolution_video)
        self.fill_cmbres(self.ui.cb_resolution, resolution_video, max_res)
        # === SISTEMA DE GRABACIÓN ===
        self.is_recording = False
        self.is_calibrating = False
        self.recording_start_time = None
        self.graph_time = 0.0
        self.last_update_time = None
        self.MAX_RECORDING_TIME = 5 * 60  # 5 minutos
        self.CALIBRATION_TIME = 1  # 1 segundo
        # === CONFIGURAR UI ===
        self.setup_menu_and_controls()
        self.connect_events()
        self.load_slider_configuration()

        # === INICIALIZAR COMPONENTES ===
        self.init_video_system()
        self.init_serial_system()
        self.init_calibration_system()
        self.init_graphics_system()
        self.init_recording_system()
        self.init_processing_system()
        
   
        
        # === TIMERS ===
        self.setup_timers()
        self.init_stimulus_system()
        self.setup_right_click_trigger()
        
        # === MOSTRAR PROTOCOLO ===
        #QTimer.singleShot(500, self.show_protocol_selection)
        
        self.showMaximized()
        print("=== SISTEMA VNG INICIADO CORRECTAMENTE ===")
                # Conectar todos los sliders

    def fill_cmbres(self, cb_resolution, resoluciones, max_res):
        """
        Llena un combobox con las resoluciones disponibles
        
        Args:
            cb_resolution: QComboBox a llenar
            resoluciones: Lista de tuplas (width, height)
        """
        cb_resolution.clear()
        try:
            for width, height in resoluciones:
                texto = f"{width}x{height}"
                cb_resolution.addItem(texto, (width, height))
        except:
            # Filtrar resoluciones con ancho >= 640 y FPS >= 60
            resoluciones_filtradas = []
            for i in resoluciones:
                res, fps = i.split("@")
                width, height = res.split("x")
                
                if int(width) >= 640 and int(fps) >= 60:
                    resoluciones_filtradas.append((res, int(fps), i))
            
            # Obtener la resolución con mayor FPS para cada resolución única
            resoluciones_unicas = {}
            for res, fps, item_completo in resoluciones_filtradas:
                if res not in resoluciones_unicas or fps > resoluciones_unicas[res][0]:
                    resoluciones_unicas[res] = (fps, item_completo)
            
            # Agregar al combo box en orden inverso
            items_ordenados = list(resoluciones_unicas.items())
            items_ordenados.reverse()
            
            for res, (fps, item_completo) in items_ordenados:
                cb_resolution.addItem(item_completo)

        cb_resolution.setCurrentText(max_res)
            

    def load_config(self):
        """Cargar configuración usando ConfigManager"""
        try:
            # Obtener configuración de ventana
            window_config = self.config_manager.get_window_config()
            self.setWindowTitle(window_config["title"])
            self.resize(window_config["size"]["width"], window_config["size"]["height"])
            
            # Obtener ruta de datos expandida
            self.data_path = self.config_manager.get_data_path()
            
            print(f"Configuración cargada. Ruta de datos: {self.data_path}")
            
        except Exception as e:
            print(f"Error cargando configuración: {e}")
            # Valores por defecto
            self.setWindowTitle("SIEV")
            self.resize(800, 600)
            self.data_path = os.path.expanduser("~/siev")

    def init_stimulus_system(self):
        """Inicializar sistema de estímulos"""
        self.stimulus_manager = StimulusManager(self)
        self.test_preparation_mode = False
        print("Sistema de estímulos inicializado")

    def setup_right_click_trigger(self):
        """Configurar click derecho global"""
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        """Capturar click derecho"""
        from PySide6.QtCore import QEvent
        from PySide6.QtGui import QMouseEvent
        
        if event.type() == QEvent.MouseButtonPress:
            if isinstance(event, QMouseEvent) and event.button() == Qt.RightButton:
                self.ui.btn_start.click()
                return True
        return super().eventFilter(obj, event)


    def setupUi(self):
        """Configurar la interfaz de usuario"""
        try:
            from .main_ui import Ui_MainWindow
            self.ui = Ui_MainWindow()
            self.ui.setupUi(self)
            print("UI cargada exitosamente")
        except ImportError:
            try:
                from ui.main_ui import Ui_MainWindow
                self.ui = Ui_MainWindow()
                self.ui.setupUi(self)
                print("UI cargada desde ui.main_ui")
            except ImportError:
                print("ERROR: No se pudo cargar la UI")

    def init_video_system(self):
        """Inicializar sistema de video"""
        try:
            slider_brightness = self.findChild(QSlider, "slider_brightness")
            slider_contrast = self.findChild(QSlider, "slider_contrast")

            slider_list = [
                self.ui.slider_th_right, self.ui.slider_th_left,
                self.ui.slider_erode_right, self.ui.slider_erode_left,
                self.ui.slider_nose_width, self.ui.slider_vertical_cut_up,
                self.ui.slider_vertical_cut_down, slider_brightness, 
                slider_contrast
            ]
            
            self.video_widget = VideoWidget(
                self.ui.CameraFrame, 
                slider_list,
                self.ui.cb_resolution,
                camera_id=self.camera_index
            )

            for i, slider in enumerate(slider_list):
                #slider.valueChanged.connect(lambda value, i=i: self.video_thread.set_threshold([value, i]))
                slider.valueChanged.connect(self.save_slider_configuration)
                #slider.sliderPressed.connect(self.save_slider_configuration)
                #slider.sliderReleased.connect(self.save_slider_configuration)

            self.video_widget.sig_pos.connect(self.handle_eye_positions)
            print("Sistema de video inicializado")
            
        except Exception as e:
            print(f"Error inicializando video: {e}")
            self.video_widget = None

    def init_serial_system(self):
        """Inicializar comunicación serial"""
        try:
            self.serial_handler = SerialHandler('/dev/ttyUSB0', 115200)
            self.serial_thread = SerialReadThread(self.serial_handler)
            self.serial_thread.data_received.connect(self.handle_serial_data)
            self.serial_thread.start()
            print("Sistema serial inicializado")
        except Exception as e:
            print(f"Error inicializando serial: {e}")
            self.serial_handler = None
            self.serial_thread = None

    def init_calibration_system(self):
        """Inicializar sistema de calibración"""
        try:
            self.calibration_manager = CalibrationManager(self.serial_handler)
            print("Sistema de calibración inicializado")
        except Exception as e:
            print(f"Error inicializando calibración: {e}")
            self.calibration_manager = None

    def init_graphics_system(self):
        """Inicializar sistema de gráficos"""
        try:
            config = PlotConfigurations.get_ultra_minimal()
            self.plot_widget = TriplePlotWidget(
                parent=None,
                window_size=60,
                update_interval=50,
                plot_config=config
            )
            self.ui.layout_graph.addWidget(self.plot_widget)
            print("Sistema de gráficos inicializado")
        except Exception as e:
            print(f"Error inicializando gráficos: {e}")
            self.plot_widget = None

    def init_recording_system(self):
        """Inicializar sistema de grabación"""
        try:
            # Usar la ruta de datos del ConfigManager
            self.data_storage = DataStorage(
                auto_save_interval=2.0,
                buffer_size=500,
                data_path=self.data_path  # Usar ruta del config
            )
            
            # Variables de control de envío a gráficos
            self.send_to_graph = False
            self.graph_update_interval = 50  # ms
            self.last_graph_update = 0
            self.graph_data_buffer = []
            self.total_data_points = 0
            
            print("Sistema de grabación inicializado")
        except Exception as e:
            print(f"Error inicializando grabación: {e}")

    def init_processing_system(self):
        """Inicializar sistema de procesamiento de datos"""
        try:
            self.eye_processor = EyeDataProcessor()
            
            # Configuración optimizada
            self.eye_processor.set_filter_strength(0.4)
            self.eye_processor.set_interpolation_steps(2)
            self.eye_processor.set_history_size(3)
            self.eye_processor.set_smoothing_enabled(True)
            self.eye_processor.set_interpolation_enabled(True)
            
            # Kalman filter
            self.eye_processor.set_kalman_enabled(True)
            self.eye_processor.set_kalman_parameters(
                process_noise=0.001,
                measurement_noise=0.3,
                stability_factor=0.01
            )
            
            self.eye_processor.set_extra_smoothing(True, buffer_size=5)
            
            # Detector de nistagmos
            self.nistagmo_detector = DetectorNistagmo(frecuencia_muestreo=200)
            self.eye_positions_buffer = []
            
            print("Sistema de procesamiento inicializado")
        except Exception as e:
            print(f"Error inicializando procesamiento: {e}")

    def setup_timers(self):
        """Configurar timers del sistema"""
        # Timer principal de grabación
        self.recording_timer = QTimer()
        self.recording_timer.timeout.connect(self.update_recording_time)
        self.recording_timer.start(100)
        
        # Timer para gráficos
        self.graph_timer = QTimer()
        self.graph_timer.timeout.connect(self.flush_graph_buffer)
        self.graph_timer.start(self.graph_update_interval)
        
        # Timer para nistagmos
        self.nistagmo_timer = QTimer()
        self.nistagmo_timer.timeout.connect(self.process_nystagmus)
        self.nistagmo_timer.start(2000)

    def setup_menu_and_controls(self):
        """Configurar menú y controles adicionales"""
        try:
            # Crear menú de cámara
            menu = QMenu(self)
            
            # Controles de cámara
            brightness_slider = self.create_labeled_slider("slider_brightness","Brightness:", -64, 64, -21)
            contrast_slider = self.create_labeled_slider("slider_contrast","Contrast:", 0, 100, 50)
            
            # Checkbox YOLO
            checkbox_container = QWidget()
            checkbox_layout = QHBoxLayout()
            self.chk_use_yolo = QCheckBox("Usar YOLO (precisión)")
            self.chk_use_yolo.setChecked(True)
            self.chk_use_yolo.toggled.connect(self.on_yolo_toggled)
            checkbox_layout.addWidget(self.chk_use_yolo)
            checkbox_container.setLayout(checkbox_layout)
            
            # Añadir al menú
            menu.addAction(self.create_widget_action(menu, checkbox_container))
            menu.addAction(self.create_widget_action(menu, brightness_slider))
            menu.addAction(self.create_widget_action(menu, contrast_slider))
            
            if hasattr(self.ui, 'toolButton'):
                self.ui.toolButton.setMenu(menu)
            
            # Botón de calibración
            #if hasattr(self.ui, 'layout_toolbar'):
            #    self.btn_calibrate = QPushButton("Calibrar Sistema")
            #    self.btn_calibrate.clicked.connect(self.start_calibration)
            #    self.ui.layout_toolbar.addWidget(self.btn_calibrate)
                
        except Exception as e:
            print(f"Error configurando menú: {e}")

    def connect_events(self):
        """Conectar eventos principales"""
        try:
            # Botón de grabación
            if hasattr(self.ui, 'btn_start'):
                self.ui.btn_start.clicked.connect(self.toggle_recording)
            
            # Menú archivo
            if hasattr(self.ui, 'actionSalir'):
                self.ui.actionSalir.triggered.connect(self.close)
                
        except Exception as e:
            print(f"Error conectando eventos: {e}")


    def show_protocol_selection(self):
        """Mostrar selección completa de protocolo - ACTUALIZADO"""
        dialog = ProtocolSelectionDialog(self)
        result = dialog.exec()
        
        if result == QDialog.Accepted:
            selected_protocol = dialog.get_selected_protocol()
            spontaneous_enabled = dialog.is_spontaneous_enabled()
            
            print(f"Protocolo seleccionado: {selected_protocol}")
            print(f"Nistagmo espontáneo: {'SÍ' if spontaneous_enabled else 'NO'}")
            
            # Guardar configuración para uso posterior
            self.current_protocol = selected_protocol
            self.spontaneous_test_enabled = spontaneous_enabled
            
            if selected_protocol != "sin_protocolo":
                # Si hay protocolo, mostrar opción de seguimiento
                QTimer.singleShot(500, self.show_tracking_calibration_choice)
            else:
                print("Iniciando sin protocolo - sistema listo")
        else:
            # Usar protocolo por defecto
            print("Usando protocolo por defecto: sin protocolo")
            self.current_protocol = "sin_protocolo"
            self.spontaneous_test_enabled = False


    def show_tracking_calibration_choice(self):
        """Mostrar ventana de elección para calibración de seguimiento"""
        dialog = TrackingCalibrationDialog(self)
        result = dialog.exec()
        
        if result == QDialog.Accepted:
            choice = dialog.get_user_choice()
            print(f"Elección de seguimiento: {choice}")
            
            if choice == "tracking_first":
                self.start_tracking_adjustment_mode()
            elif choice == "skip_to_calibration":
                QTimer.singleShot(1000, self.start_calibration)
        else:
            # Por defecto, ir a ajuste de seguimiento
            self.start_tracking_adjustment_mode()

    def start_tracking_adjustment_mode(self):
        """Iniciar modo de ajuste de seguimiento"""
        print("=== MODO AJUSTE DE SEGUIMIENTO ===")
        
        # Cambiar botón Start por "Continuar Calibración"
        if hasattr(self.ui, 'btn_start'):
            self.ui.btn_start.setText("Continuar Calibración")
            self.ui.btn_start.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50; color: white; font-weight: bold;
                    font-size: 14px; padding: 10px; border: none; border-radius: 5px;
                }
                QPushButton:hover { background-color: #45a049; }
            """)
            
            # Reconectar evento
            try:
                self.ui.btn_start.clicked.disconnect()
            except:
                pass
            self.ui.btn_start.clicked.connect(self.continue_to_calibration)
        
        # Mostrar mensaje
        if hasattr(self.ui, 'lbl_time'):
            self.ui.lbl_time.setText("AJUSTE EL SEGUIMIENTO CON LOS SLIDERS")
            self.ui.lbl_time.setStyleSheet("""
                QLabel {
                    color: #FF9800; font-weight: bold; font-size: 14px;
                }
            """)
        
        print("Ajuste los sliders de seguimiento y presione 'Continuar Calibración'")

    def continue_to_calibration(self):
        """Continuar a calibración después del ajuste"""
        print("Guardando configuración de sliders y continuando a calibración...")
        
        # Guardar configuración
        self.save_slider_configuration()
        
        # Restaurar botón Start
        if hasattr(self.ui, 'btn_start'):
            self.ui.btn_start.setText("Start")
            self.ui.btn_start.setStyleSheet("")
            
            try:
                self.ui.btn_start.clicked.disconnect()
            except:
                pass
            self.ui.btn_start.clicked.connect(self.toggle_recording)
        
        # Restaurar label
        if hasattr(self.ui, 'lbl_time'):
            self.ui.lbl_time.setText("00:00 / 05:00")
            self.ui.lbl_time.setStyleSheet("")
        
        # Iniciar calibración
        QTimer.singleShot(500, self.start_calibration)


    def handle_serial_data(self, data):
        """Procesar datos seriales del IMU"""
        try:
            parts = data.split(",")
            if len(parts) >= 3:
                self.pos_hit = [float(parts[0]), float(parts[1]), float(parts[2])]
        except (ValueError, IndexError) as e:
            print(f"Error procesando datos serial: {e}")

    def handle_eye_positions(self, pos):
        """Procesar posiciones oculares principales - SISTEMA COMPLETO"""
        self.pos_eye = pos
        
        # Si hay calibración en progreso, enviar datos al sistema de calibración
        if hasattr(self, 'calibration_in_progress') and self.calibration_in_progress:
            if hasattr(self, 'calibration_controller') and self.calibration_controller:
                left_eye = self.pos_eye[1] if len(self.pos_eye) > 1 else None
                right_eye = self.pos_eye[0] if len(self.pos_eye) > 0 else None
                self.calibration_controller.process_eye_positions(left_eye, right_eye)
        
        # Procesar datos normalmente para grabación/visualización
        if not self.send_to_graph:
            return
            
        try:
            # Extraer posiciones según estructura original
            left_eye = self.pos_eye[1] if len(self.pos_eye) > 1 else None
            right_eye = self.pos_eye[0] if len(self.pos_eye) > 0 else None
            
            # APLICAR CALIBRACIÓN SI ESTÁ DISPONIBLE
            if self.calibration_manager and self.calibration_manager.is_calibrated:
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
                float(self.pos_hit[0]),  # IMU X
                float(self.pos_hit[1]),  # IMU Y
                self.graph_time
            )
            
            # === ALMACENAMIENTO COMPLETO (TODOS LOS PUNTOS) ===
            if self.is_recording:
                for point in processed_points:
                    processed_left, processed_right, imu_x, imu_y, point_time = point
                    self.data_storage.add_data_point(
                        processed_left, processed_right, imu_x, imu_y, point_time
                    )
                    self.total_data_points += 1
            
            # === VISUALIZACIÓN OPTIMIZADA ===
            current_time = time.time()
            if current_time - self.last_graph_update >= (self.graph_update_interval / 1000.0):
                if processed_points:
                    # Añadir al buffer de gráficos (solo los últimos puntos para eficiencia)
                    latest_point = processed_points[-1]
                    self.graph_data_buffer.append(latest_point)
                    self.last_graph_update = current_time
                    
        except Exception as e:
            print(f"Error procesando posiciones oculares: {e}")

    def flush_graph_buffer(self):
        """Enviar datos acumulados a los gráficos - SISTEMA COMPLETO"""
        if not self.graph_data_buffer or not self.plot_widget:
            return
            
        try:
            # Procesar en lotes para mejor performance
            for point in self.graph_data_buffer:
                processed_left, processed_right, imu_x, imu_y, point_time = point
                
                # Usar el método correcto según la implementación del plot_widget
                if hasattr(self.plot_widget, 'add_data_point'):
                    self.plot_widget.add_data_point(
                        processed_left, processed_right, imu_x, imu_y, point_time
                    )
                elif hasattr(self.plot_widget, 'updatePlots'):
                    # Formato para compatibilidad con TriplePlotWidget original
                    data = [processed_right, processed_left, imu_x, imu_y, point_time]
                    self.plot_widget.updatePlots(data)
            
            # Limpiar buffer después de enviar
            self.graph_data_buffer.clear()
            
        except Exception as e:
            print(f"Error enviando a gráficos: {e}")
            # En caso de error, limpiar buffer para evitar acumulación
            self.graph_data_buffer.clear()

    def toggle_recording(self):
        """Alternar grabación"""
        if not self.is_recording and not self.is_calibrating:
            self.start_calibration_phase()
        else:
            self.stop_recording()

    def start_calibration_phase(self):
        """Iniciar fase de calibración"""
        print("=== INICIANDO CALIBRACIÓN ===")
        self.is_calibrating = True
        self.eye_processor.reset_calibration()
        
        self.recording_start_time = time.time()
        self.last_update_time = time.time()
        self.graph_time = -self.CALIBRATION_TIME
        
        self.ui.btn_start.setText("Calibrando...")
        self.ui.btn_start.setEnabled(False)
        self.ui.lbl_time.setText(f"Calibrando: {self.CALIBRATION_TIME}s")
        
        self.send_to_graph = True
        QTimer.singleShot(self.CALIBRATION_TIME * 1000, self.start_recording)

    def start_recording(self):
        """Iniciar grabación real"""
        print("=== INICIANDO GRABACIÓN ===")
        self.is_calibrating = False
        self.is_recording = True
        self.recording_start_time = time.time()
        self.graph_time = 0.0
        self.last_update_time = time.time()
        
        # Iniciar almacenamiento
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"vng_recording_{timestamp}.csv"
        self.data_storage.start_recording(filename)
        
        # Configurar gráficos
        if self.plot_widget:
            self.plot_widget.clear_data()
            self.plot_widget.set_recording_state(True)
        
        self.ui.btn_start.setText("Detener")
        self.ui.btn_start.setEnabled(True)
        
        self.total_data_points = 0
        print(f"Grabación iniciada: {filename}")

    def stop_recording(self):
        """Detener grabación"""
        print("=== DETENIENDO GRABACIÓN ===")
        was_recording = self.is_recording
        
        self.is_recording = False
        self.is_calibrating = False
        self.recording_start_time = None
        self.last_update_time = None
        self.graph_time = 0.0
        self.send_to_graph = False
        
        if was_recording:
            self.data_storage.stop_recording()
            stats = self.data_storage.get_statistics()
            print(f"Grabación completada: {stats.get('total_samples', 0)} muestras")
        
        if self.plot_widget:
            self.plot_widget.set_recording_state(False)
        
        self.ui.btn_start.setText("Iniciar")
        self.ui.lbl_time.setText("00:00 / 05:00")

    def update_recording_time(self):
        """Actualizar tiempo de grabación"""
        current_time = time.time()
        
        if self.last_update_time is not None:
            delta_time = current_time - self.last_update_time
            
            if self.is_recording:
                self.graph_time += delta_time
                elapsed = current_time - self.recording_start_time
                
                if elapsed >= self.MAX_RECORDING_TIME:
                    self.stop_recording()
                    return
                
                minutes = int(self.graph_time // 60)
                seconds = int(self.graph_time % 60)
                self.ui.lbl_time.setText(f"{minutes:02d}:{seconds:02d} / 05:00")
                
            elif self.is_calibrating:
                elapsed = current_time - self.recording_start_time
                remaining = max(0, self.CALIBRATION_TIME - elapsed)
                self.graph_time = -remaining
                self.ui.lbl_time.setText(f"Calibrando: {int(remaining)}s")
        
        self.last_update_time = current_time

    def start_calibration(self):
        """Iniciar calibración del sistema"""
        if not self.calibration_manager:
            QMessageBox.warning(self, "Error", "Sistema de calibración no disponible")
            return
            
        try:
            from ui.calibration_dialog import CalibrationDialog
            dialog = CalibrationDialog(
                calibration_manager=self.calibration_manager,
                parent_window=self
            )
            dialog.calibration_finished.connect(self.on_calibration_finished)
            dialog.exec()
        except Exception as e:
            print(f"Error iniciando calibración: {e}")

    def on_calibration_finished(self, success):
        """Procesar resultado de calibración"""
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
            
            # Mensaje de éxito
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

    def update_graph_limits_after_calibration(self):
        """Actualizar límites del gráfico después de calibración"""
        if not self.calibration_manager or not self.calibration_manager.is_calibrated:
            return
        
        summary = self.calibration_manager.get_calibration_summary()
        theoretical_angle = summary['theoretical_angle']
        
        # Calcular límites con margen
        margin = 20.0  # grados de margen
        max_limit = theoretical_angle / 2 + margin
        min_limit = -max_limit
        
        print(f"Actualizando límites del gráfico:")
        print(f"  Rango: {min_limit:.1f}° a {max_limit:.1f}°")
        print(f"  Unidades: GRADOS (calibrado)")
        
        # Aplicar a los plots
        if self.plot_widget and hasattr(self.plot_widget, 'plots'):
            for plot in self.plot_widget.plots:
                plot.setYRange(min_limit, max_limit)

    def process_nystagmus(self):
        """Procesar detección de nistagmos"""
        if len(self.eye_positions_buffer) > 100:
            try:
                resultados = self.nistagmo_detector.procesar_datos(self.eye_positions_buffer)
                if resultados['total_nistagmos'] > 0:
                    print(f"Nistagmos: {resultados['total_nistagmos']}, VCL: {resultados['vcl_promedio']:.2f}°/s")
            except Exception as e:
                print(f"Error procesando nistagmos: {e}")

    def on_yolo_toggled(self, checked):
        """Manejar cambio de YOLO"""
        if self.video_widget:
            self.video_widget.set_yolo_enabled(checked)

    def create_labeled_slider(self, nameobj, label_text, min_val, max_val, initial_val):
        """Crear slider con etiqueta"""
        container = QWidget()
        layout = QHBoxLayout()
        
        layout.addWidget(QLabel(label_text))
        
        slider = QSlider(Qt.Horizontal)
        slider.setObjectName(nameobj)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(initial_val)
        slider.valueChanged.connect(self.save_slider_configuration)


        layout.addWidget(slider)
        container.setLayout(layout)
        return container

    def create_widget_action(self, parent, widget):
        """Crear QWidgetAction para menús"""
        action = QWidgetAction(parent)
        action.setDefaultWidget(widget)
        return action

    def load_slider_configuration(self):
        """Cargar configuraciones de sliders desde config.json"""
        try:
            slider_settings = self.config_manager.get_slider_settings()
            print("se carga setting")

            slider_mapping = {
                'slider_th_right': 'slider_th_right',
                'slider_th_left': 'slider_th_left',
                'slider_erode_right': 'slider_erode_right',
                'slider_erode_left': 'slider_erode_left',
                'slider_nose_width': 'slider_nose_width',
                'slider_vertical_cut_up': 'slider_vertical_cut_up',
                'slider_vertical_cut_down': 'slider_vertical_cut_down',
                'slider_brightness': 'slider_brightness',
                'slider_contrast': 'slider_contrast'
            }
            
            loaded_count = 0
            for config_name, ui_name in slider_mapping.items():
                if config_name in slider_settings:
                    value = slider_settings[config_name]  # ✅ Mover aquí
                    
                    if hasattr(self.ui, ui_name):
                        slider = getattr(self.ui, ui_name)
                    else:
                        slider = self.findChild(QSlider, config_name)
                    
                    if slider and slider.minimum() <= value <= slider.maximum():
                        slider.setValue(value)
                        loaded_count += 1
                        #print(f"Slider {ui_name} configurado a {value}")
                    else:
                        print(f"Valor {value} fuera de rango para {ui_name}")
            
            print(f"Configuración de sliders cargada: {loaded_count} sliders configurados")
        except Exception as e:
            print(f"Error cargando configuración de sliders: {e}")
        
    def save_slider_configuration(self):
        """Guardar configuraciones actuales de sliders"""

        sender_name = self.sender().objectName()
        sender_value = self.sender().value()
        #print(f"Me ha llamado {sender_name} con valor {sender_value}")

        try:
            if self.config_manager.set_slider_value(sender_name, sender_value):
                pass
                #print(f"Configuración de {sender_name} guardada")
            else:
                print(f"Error guardando configuración de {sender_name}")
                
        except Exception as e:
            print(f"Error guardando configuración de sliders: {e}")



    def closeEvent(self, event):
        """Manejar cierre de aplicación"""
        try:
            print("Cerrando aplicación...")
            
            if self.is_recording:
                self.stop_recording()
            
            if self.video_widget:
                self.video_widget.cleanup()
            
            if self.serial_thread:
                self.serial_thread.stop()
            
            if hasattr(self, 'nistagmo_timer'):
                self.nistagmo_timer.stop()
            if hasattr(self, 'recording_timer'):
                self.recording_timer.stop()
            if hasattr(self, 'graph_timer'):
                self.graph_timer.stop()
                
            print("Aplicación cerrada correctamente")
        except Exception as e:
            print(f"Error durante cierre: {e}")
        
        super().closeEvent(event)