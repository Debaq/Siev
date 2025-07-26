import os
import time
from PySide6.QtWidgets import (QMainWindow, QSlider, QMessageBox, QTreeWidgetItem, 
                              QMenu, QHBoxLayout, QWidget, QLabel, QCheckBox, QWidgetAction)
from PySide6.QtCore import Qt, QTimer

# Managers
from managers import VideoManager, HardwareManager, DataManager, TestManager

# Libs básicas
from libs.core.config_manager import ConfigManager
from libs.hardware.camera_resolution_detector import CameraResolutionDetector
from libs.common.utils import select_max_resolution
from datetime import datetime


class MainWindow(QMainWindow):
    """MainWindow refactorizado - versión limpia"""
    
    def __init__(self):
        super().__init__()
        
        # Configuración básica
        self.config_manager = ConfigManager()
        self.setupUi()
        self.load_config()
        
        # Managers
        self.video_manager = VideoManager(self)
        self.hardware_manager = HardwareManager(self)
        self.data_manager = DataManager(self.config_manager, self)
        self.test_manager = TestManager(self)
        
        # Variables de estado
        self.camera_index = 2
        self.is_recording = False
        self.is_calibrating = False
        self.pos_eye = []
        self.pos_hit = [0.0, 0.0, 0.0]
        self.MAX_RECORDING_TIME = 5 * 60
        self.CALIBRATION_TIME = 1
        
        # Inicialización
        self.initialize_application()
        self.showMaximized()
    
    def initialize_application(self):
        """Inicializar aplicación"""
        # 1. Crear sliders de menú
        self.setup_menu_and_controls()
        
        # 2. Configurar referencias UI
        self._setup_ui_references()
        
        # 3. Inicializar sistemas
        self._initialize_systems()
        
        # 4. Conectar señales
        self._connect_signals()
        
        # 5. UI final
        self._setup_final_ui()
    
    def setup_menu_and_controls(self):
        """Crear menú con sliders de brightness/contrast"""
        menu = QMenu(self)
        
        # Crear sliders
        brightness_slider = self.create_labeled_slider("slider_brightness", "Brightness:", -64, 64, -21)
        contrast_slider = self.create_labeled_slider("slider_contrast", "Contrast:", 0, 100, 50)
        
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
    
    def create_labeled_slider(self, name, label_text, min_val, max_val, initial_val):
        """Crear slider con etiqueta"""
        container = QWidget()
        layout = QHBoxLayout()
        layout.addWidget(QLabel(label_text))
        
        slider = QSlider(Qt.Horizontal)
        slider.setObjectName(name)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(initial_val)
        slider.valueChanged.connect(self.save_slider_configuration)
        
        layout.addWidget(slider)
        container.setLayout(layout)
        return container
    
    def create_widget_action(self, parent, widget):
        """Crear QWidgetAction"""
        action = QWidgetAction(parent)
        action.setDefaultWidget(widget)
        return action
    
    def _setup_ui_references(self):
        """Configurar referencias UI para managers"""
        # Detectar resoluciones
        res_video = CameraResolutionDetector()
        resolution_video = res_video.listar_resoluciones(self.camera_index)
        max_res = select_max_resolution(resolution_video, True)
        self.fill_cmbres(self.ui.cb_resolution, resolution_video, max_res)
        
        # Sliders para VideoManager
        slider_brightness = self.findChild(QSlider, "slider_brightness")
        slider_contrast = self.findChild(QSlider, "slider_contrast")
        
        slider_list = [
            self.ui.slider_th_right, self.ui.slider_th_left,
            self.ui.slider_erode_right, self.ui.slider_erode_left,
            self.ui.slider_nose_width, self.ui.slider_vertical_cut_up,
            self.ui.slider_vertical_cut_down, slider_brightness, 
            slider_contrast
        ]
        
        # Configurar managers
        self.video_manager.set_ui_references(self.ui.CameraFrame, self.ui.cb_resolution, slider_list)
        self.video_manager.set_camera_index(self.camera_index)
        self.data_manager.set_ui_references(self.ui.layout_graph)
        self.test_manager.set_references(self, self.ui.listTestWidget)
    
    def _initialize_systems(self):
        """Inicializar sistemas"""
        # Video primero
        self.video_manager.initialize_video_system()
        
        # Hardware
        self.hardware_manager.initialize_hardware('/dev/ttyUSB0', 115200)
        
        # Data - manual porque DataStorage no acepta data_dir
        data_path = self.config_manager.get_data_path()
        from libs.data.data_storage import DataStorage
        
        self.data_manager.data_storage = DataStorage(
            auto_save_interval=2.0,
            buffer_size=500,
            data_path=data_path
        )
        self.data_manager._init_processing_system()
        self.data_manager._init_graphics_system()
        
        # Test
        self.test_manager.initialize_test_system()
    
    def _connect_signals(self):
        """Conectar señales esenciales"""
        # Video
        if hasattr(self.video_manager, 'video_widget') and self.video_manager.video_widget:
            self.video_manager.video_widget.sig_pos.connect(self.handle_eye_positions)
        
        # Hardware
        self.hardware_manager.imu_data_received.connect(self.handle_serial_data)
        
        # Test manager
        self.test_manager.user_loaded.connect(self.on_user_loaded)
        self.test_manager.user_closed.connect(self.on_user_closed)
    
    def _setup_final_ui(self):
        """UI final"""
        self.connect_events()
        self.load_slider_configuration()
        self.ui.listTestWidget.currentItemChanged.connect(self.on_test_selection_changed)
        
        if hasattr(self.video_manager, 'video_widget') and self.video_manager.video_widget:
            self.video_manager.video_widget.set_ui_references(self.ui.slider_time, self.ui.btn_start)
        
        self.installEventFilter(self)
        self.enable_test_functions(False)
    
    # =========================================================================
    # HANDLERS BÁSICOS
    # =========================================================================
    
    def handle_eye_positions(self, positions):
        """Manejar posiciones de ojos"""
        self.pos_eye = positions
        if len(positions) >= 2:
            left_eye = positions[0] if positions[0] else None
            right_eye = positions[1] if positions[1] else None
            self.data_manager.process_eye_data(left_eye, right_eye)
    
    def handle_serial_data(self, imu_data):
        """Manejar datos IMU"""
        if imu_data.get('is_valid', False):
            self.pos_hit = [
                imu_data.get('yaw', 0.0),
                imu_data.get('pitch', 0.0), 
                imu_data.get('roll', 0.0)
            ]
            self.data_manager.process_imu_data(imu_data)
    
    def on_user_loaded(self, user_data):
        """Usuario cargado"""
        user_info = self.test_manager.get_current_user_info()
        self.setWindowTitle(f"SIEV - {user_info}")
        self.enable_test_functions(True)
    
    def on_user_closed(self):
        """Usuario cerrado"""
        self.setWindowTitle("SIEV")
        self.enable_test_functions(False)
    
    def on_test_selection_changed(self, current_item, previous_item):
        """Cambio de selección de test"""
        self.update_test_ui_state()
    
    # =========================================================================
    # CONTROL DE GRABACIÓN
    # =========================================================================
    
    def toggle_recording(self):
        """Control principal de grabación"""
        if not self.is_recording:
            success = self.data_manager.start_recording()
            if success:
                self.video_manager.start_recording()
                self.is_recording = True
                self.ui.btn_start.setText("Detener")
        else:
            self.data_manager.stop_recording()
            self.video_manager.stop_recording()
            self.is_recording = False
            self.ui.btn_start.setText("Iniciar")
    
    # =========================================================================
    # CONFIGURACIÓN DE SLIDERS
    # =========================================================================
    
    def save_slider_configuration(self):
        """Guardar configuración de sliders"""
        sender = self.sender()
        if sender:
            sender_name = sender.objectName()
            sender_value = sender.value()
            self.config_manager.set_slider_value(sender_name, sender_value)
    
    def load_slider_configuration(self):
        """Cargar configuración de sliders"""
        slider_settings = self.config_manager.get_slider_settings()
        
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
        
        for config_name, ui_name in slider_mapping.items():
            if config_name in slider_settings:
                value = slider_settings[config_name]
                
                if hasattr(self.ui, ui_name):
                    slider = getattr(self.ui, ui_name)
                else:
                    slider = self.findChild(QSlider, config_name)
                
                if slider and slider.minimum() <= value <= slider.maximum():
                    slider.setValue(value)
    
    # =========================================================================
    # MÉTODOS DELEGADOS
    # =========================================================================
    
    def open_new_user_dialog(self):
        """Nuevo usuario"""
        return self.test_manager.open_new_user_dialog()
    
    def open_user_file(self):
        """Abrir usuario"""
        return self.test_manager.open_user_file()
    
    def close_current_user(self):
        """Cerrar usuario"""
        self.test_manager.close_current_user()
    
    def change_evaluator(self):
        """Cambiar evaluador"""
        return self.test_manager.change_evaluator()
    
    def show_protocol_selection(self, protocol_type=None):
        """Mostrar protocolo"""
        # Cambiar de create_protocol_test a open_protocol_dialog
        return self.test_manager.open_protocol_dialog(protocol_type)
    
    def start_calibration(self):
        """Iniciar calibración"""
        return self.hardware_manager.start_calibration()
    
    def on_yolo_toggled(self, checked):
        """Toggle YOLO"""
        if hasattr(self.video_manager, 'video_widget') and self.video_manager.video_widget:
            self.video_manager.video_widget.set_yolo_enabled(checked)
    
    # =========================================================================
    # MÉTODOS BÁSICOS UI
    # =========================================================================
    
    def setupUi(self):
        """Configurar UI"""
        try:
            from .main_ui import Ui_MainWindow
            self.ui = Ui_MainWindow()
            self.ui.setupUi(self)
        except ImportError:
            from ui.main_ui import Ui_MainWindow
            self.ui = Ui_MainWindow()
            self.ui.setupUi(self)
    
    def load_config(self):
        """Cargar configuración"""
        window_config = self.config_manager.get_window_config()
        self.setWindowTitle(window_config["title"])
        size = window_config["size"]
        self.resize(size["width"], size["height"])
    
    def fill_cmbres(self, combo, resolution_list, selected_resolution):
        """Llenar combo de resoluciones"""
        combo.clear()
        try:
            for width, height in resolution_list:
                texto = f"{width}x{height}"
                combo.addItem(texto, (width, height))
        except:
            # Formato con FPS
            resoluciones_filtradas = []
            for i in resolution_list:
                res, fps = i.split("@")
                width, height = res.split("x")
                if int(width) >= 640 and int(fps) >= 60:
                    resoluciones_filtradas.append((res, int(fps), i))
            
            resoluciones_unicas = {}
            for res, fps, item_completo in resoluciones_filtradas:
                if res not in resoluciones_unicas or fps > resoluciones_unicas[res][0]:
                    resoluciones_unicas[res] = (fps, item_completo)
            
            items_ordenados = list(resoluciones_unicas.items())
            items_ordenados.reverse()
            
            for res, (fps, item_completo) in items_ordenados:
                combo.addItem(item_completo)

        combo.setCurrentText(selected_resolution)
    
    def connect_events(self):
        """Conectar eventos"""
        # Botón principal
        self.ui.btn_start.clicked.connect(self.toggle_recording)
        
        # Menú archivo
        if hasattr(self.ui, 'actionNewUser'):
            self.ui.actionNewUser.triggered.connect(self.open_new_user_dialog)
        if hasattr(self.ui, 'actionExit'):
            self.ui.actionExit.triggered.connect(self.close)
        if hasattr(self.ui, 'actionAbrir'):
            self.ui.actionAbrir.triggered.connect(self.open_user_file)
        
        # Evaluador
        if hasattr(self.ui, 'actionCambiar_evaluador'):
            self.ui.actionCambiar_evaluador.triggered.connect(self.change_evaluator)

        # Protocolos calóricos
        if hasattr(self.ui, 'actionOD_44'):
            self.ui.actionOD_44.triggered.connect(lambda: self.show_protocol_selection("OD_44"))
        if hasattr(self.ui, 'actionOI_44'):
            self.ui.actionOI_44.triggered.connect(lambda: self.show_protocol_selection("OI_44"))
        if hasattr(self.ui, 'actionOD_37'):
            self.ui.actionOD_37.triggered.connect(lambda: self.show_protocol_selection("OD_37"))
        if hasattr(self.ui, 'actionOI37'):
            self.ui.actionOI37.triggered.connect(lambda: self.show_protocol_selection("OI_37"))

        # Protocolos oculomotores
        if hasattr(self.ui, 'actionSeguimiento_Lento'):
            self.ui.actionSeguimiento_Lento.triggered.connect(lambda: self.show_protocol_selection("seguimiento_lento"))
        if hasattr(self.ui, 'actionOptoquinetico'):
            self.ui.actionOptoquinetico.triggered.connect(lambda: self.show_protocol_selection("optoquinetico"))
        if hasattr(self.ui, 'actionSacadas'):
            self.ui.actionSacadas.triggered.connect(lambda: self.show_protocol_selection("sacadas"))
        if hasattr(self.ui, 'actionEspont_neo'):
            self.ui.actionEspont_neo.triggered.connect(lambda: self.show_protocol_selection("espontaneo"))

        # Calibración
        if hasattr(self.ui, 'actionCalibrar'):
            self.ui.actionCalibrar.triggered.connect(self.start_calibration)
    
    def enable_test_functions(self, enabled):
        """Habilitar/deshabilitar funciones de test"""
        if hasattr(self.ui, 'btn_start'):
            self.ui.btn_start.setEnabled(enabled)
        
        # Menús calóricos
        for action_name in ['actionOD_44', 'actionOI_44', 'actionOD_37', 'actionOI37']:
            if hasattr(self.ui, action_name):
                getattr(self.ui, action_name).setEnabled(enabled)
        
        # Menús oculomotores
        for action_name in ['actionEspont_neo', 'actionSeguimiento_Lento', 'actionOptoquinetico', 'actionSacadas']:
            if hasattr(self.ui, action_name):
                getattr(self.ui, action_name).setEnabled(enabled)
    
    def update_test_ui_state(self):
        """Actualizar estado UI"""
        pass
    
    def eventFilter(self, obj, event):
        """Event filter para click derecho"""
        from PySide6.QtCore import QEvent
        from PySide6.QtGui import QMouseEvent
        
        if event.type() == QEvent.MouseButtonPress:
            if isinstance(event, QMouseEvent) and event.button() == Qt.RightButton:
                self.ui.btn_start.click()
                return True
        return super().eventFilter(obj, event)
    
    # =========================================================================
    # CLEANUP
    # =========================================================================
    
    def closeEvent(self, event):
        """Cierre limpio"""
        if self.is_recording:
            self.toggle_recording()
        
        # Cleanup directo de video threads
        if hasattr(self, 'video_manager') and hasattr(self.video_manager, 'video_widget'):
            video_widget = self.video_manager.video_widget
            if video_widget:
                if hasattr(video_widget, 'video_thread') and video_widget.video_thread:
                    video_widget.video_thread.stop()
                    video_widget.video_thread.wait(3000)
                if hasattr(video_widget, 'video_player_thread') and video_widget.video_player_thread:
                    video_widget.video_player_thread.stop()
                    video_widget.video_player_thread.wait(3000)
        
        # Cleanup managers
        if hasattr(self, 'video_manager'):
            self.video_manager.cleanup()
        if hasattr(self, 'hardware_manager'):
            self.hardware_manager.cleanup()
        if hasattr(self, 'data_manager'):
            self.data_manager.cleanup()
        if hasattr(self, 'test_manager'):
            self.test_manager.cleanup()
        
        event.accept()