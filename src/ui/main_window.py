import os
import time
from PySide6.QtWidgets import (QMainWindow, QSlider, QMessageBox, QTreeWidgetItem)
from PySide6.QtCore import Qt, QTimer

# Managers - Toda la lógica de negocio está aquí
from managers import VideoManager, HardwareManager, DataManager, TestManager

# Solo las librerías esenciales que MainWindow necesita directamente
from libs.core.config_manager import ConfigManager
from libs.hardware.camera_resolution_detector import CameraResolutionDetector
from libs.common.utils import select_max_resolution
from datetime import datetime


class MainWindow(QMainWindow):
    """
    Ventana principal del sistema VNG - VERSIÓN REFACTORIZADA
    
    Responsabilidades:
    - Configuración inicial y UI
    - Coordinación entre managers
    - Manejo de eventos de UI
    - Estados globales de la aplicación
    """
    
    def __init__(self):
        super().__init__()
        
        # === CONFIGURACIÓN BÁSICA ===
        self.config_manager = ConfigManager()
        
        # Configurar UI
        self.setupUi()
        self.load_config()
        
        # === MANAGERS - TODA LA LÓGICA ESTÁ AQUÍ ===
        self.video_manager = VideoManager(self)
        self.hardware_manager = HardwareManager(self)
        self.data_manager = DataManager(self.config_manager, self)
        self.test_manager = TestManager(self)
        
        # === VARIABLES DE ESTADO GLOBALES ===
        self.camera_index = 2
        self.is_recording = False
        self.is_calibrating = False
        self.MAX_RECORDING_TIME = 5 * 60  # 5 minutos
        self.CALIBRATION_TIME = 1  # 1 segundo
        
        # === INICIALIZACIÓN COMPLETA ===
        self.initialize_application()
        
        self.showMaximized()
        print("=== SISTEMA VNG REFACTORIZADO INICIADO ===")
    
    def initialize_application(self):
        """Inicialización completa de la aplicación usando managers"""
        try:
            # 1. Configurar referencias UI para managers
            self._setup_manager_ui_references()
            
            # 2. Inicializar todos los sistemas
            self._initialize_all_systems()
            
            # 3. Conectar señales entre managers y MainWindow
            self._connect_manager_signals()
            
            # 4. Configurar UI y eventos
            self._setup_ui_and_events()
            
            print("Aplicación inicializada exitosamente")
            
        except Exception as e:
            print(f"Error inicializando aplicación: {e}")
            QMessageBox.critical(self, "Error", f"Error crítico inicializando: {e}")
    
    def _setup_manager_ui_references(self):
        """Configura referencias UI para todos los managers"""
        
        # Detectar resoluciones de cámara (esto todavía se hace en MainWindow)
        res_video = CameraResolutionDetector()
        resolution_video = res_video.listar_resoluciones(self.camera_index)
        max_res = select_max_resolution(resolution_video, True)
        self.fill_cmbres(self.ui.cb_resolution, resolution_video, max_res)
        
        # Referencias para VideoManager
        slider_brightness = self.findChild(QSlider, "slider_brightness")
        slider_contrast = self.findChild(QSlider, "slider_contrast")
        slider_list = [
            self.ui.slider_th_right, self.ui.slider_th_left,
            self.ui.slider_erode_right, self.ui.slider_erode_left,
            self.ui.slider_nose_width, self.ui.slider_vertical_cut_up,
            self.ui.slider_vertical_cut_down, slider_brightness, 
            slider_contrast
        ]
        
        self.video_manager.set_ui_references(
            self.ui.CameraFrame,
            self.ui.cb_resolution,
            slider_list
        )
        self.video_manager.set_camera_index(self.camera_index)
        
        # Referencias para DataManager
        self.data_manager.set_ui_references(self.ui.layout_graph)
        
        # Referencias para TestManager
        self.test_manager.set_references(self, self.ui.listTestWidget)
    
    def _initialize_all_systems(self):
        """Inicializa todos los sistemas usando managers"""
        
        # Video System
        success = self.video_manager.initialize_video_system()
        if not success:
            print("ADVERTENCIA: Error inicializando sistema de video")
        
        # Hardware System
        success = self.hardware_manager.initialize_hardware('/dev/ttyUSB0', 115200)
        if not success:
            print("ADVERTENCIA: Error inicializando hardware")
        
        # Data System
        success = self.data_manager.initialize_data_system()
        if not success:
            print("ADVERTENCIA: Error inicializando sistema de datos")
        
        # Test System
        success = self.test_manager.initialize_test_system()
        if not success:
            print("ADVERTENCIA: Error inicializando sistema de tests")
    
    def _connect_manager_signals(self):
        """Conecta señales entre managers y MainWindow"""
        
        # === SEÑALES DEL VIDEO MANAGER ===
        self.video_manager.eye_positions_updated.connect(self.on_eye_positions_updated)
        self.video_manager.video_frame_ready.connect(self.on_video_frame_ready)
        self.video_manager.video_mode_changed.connect(self.on_video_mode_changed)
        
        # === SEÑALES DEL HARDWARE MANAGER ===
        self.hardware_manager.imu_data_received.connect(self.on_imu_data_received)
        self.hardware_manager.hardware_status_changed.connect(self.on_hardware_status_changed)
        self.hardware_manager.calibration_progress.connect(self.on_calibration_progress)
        self.hardware_manager.calibration_completed.connect(self.on_calibration_completed)
        
        # === SEÑALES DEL DATA MANAGER ===
        self.data_manager.recording_started.connect(self.on_recording_started)
        self.data_manager.recording_stopped.connect(self.on_recording_stopped)
        self.data_manager.data_point_processed.connect(self.on_data_point_processed)
        
        # === SEÑALES DEL TEST MANAGER ===
        self.test_manager.user_loaded.connect(self.on_user_loaded)
        self.test_manager.user_closed.connect(self.on_user_closed)
        self.test_manager.test_created.connect(self.on_test_created)
        self.test_manager.test_started.connect(self.on_test_started)
        self.test_manager.test_completed.connect(self.on_test_completed)
        self.test_manager.stimulus_window_opened.connect(self.on_stimulus_window_opened)
        self.test_manager.stimulus_window_closed.connect(self.on_stimulus_window_closed)
        self.test_manager.evaluator_changed.connect(self.on_evaluator_changed)
    
    def _setup_ui_and_events(self):
        """Configura UI y eventos básicos"""
        
        # Configurar eventos de UI
        self.setup_menu_and_controls()
        self.connect_events()
        
        # Configurar sliders
        self.load_slider_configuration()
        
        # Configurar sistema de selección de tests
        self.ui.listTestWidget.currentItemChanged.connect(self.on_test_selection_changed)
        
        # Configurar referencias adicionales
        if hasattr(self.video_manager, 'video_widget') and self.video_manager.video_widget:
            self.video_manager.video_widget.set_ui_references(self.ui.slider_time, self.ui.btn_start)
        
        # Configurar event filter para click derecho
        self.installEventFilter(self)
        
        # Estado inicial
        self.enable_test_functions(False)
    
    # =========================================================================
    # MANEJADORES DE SEÑALES DE LOS MANAGERS
    # =========================================================================
    
    # === VIDEO MANAGER SIGNALS ===
    
    def on_eye_positions_updated(self, positions):
        """Manejar nuevas posiciones de ojos del VideoManager"""
        # Procesar con DataManager
        if len(positions) >= 2:
            left_eye = positions[0] if positions[0] else None
            right_eye = positions[1] if positions[1] else None
            
            # Enviar a DataManager para procesamiento
            self.data_manager.process_eye_data(left_eye, right_eye)
    
    def on_video_frame_ready(self, frame):
        """Manejar frame listo para procesamiento"""
        # El DataManager ya maneja la lógica de grabación
        pass
    
    def on_video_mode_changed(self, mode):
        """Manejar cambio de modo de video"""
        print(f"Modo de video: {mode}")
        # Aquí puedes actualizar UI según el modo
    
    # === HARDWARE MANAGER SIGNALS ===
    
    def on_imu_data_received(self, imu_data):
        """Manejar datos del IMU"""
        if imu_data.get('is_valid', False):
            # Procesar con DataManager
            self.data_manager.process_imu_data(imu_data)
            
            # Enviar datos combinados a gráficos si hay datos de ojos
            if hasattr(self, '_last_eye_data'):
                self.data_manager.add_combined_data_point(
                    self._last_eye_data.get('left_eye'),
                    self._last_eye_data.get('right_eye'),
                    imu_data.get('yaw', 0.0),
                    imu_data.get('pitch', 0.0),
                    imu_data.get('timestamp')
                )
    
    def on_hardware_status_changed(self, status):
        """Manejar cambio de estado del hardware"""
        print(f"Hardware: {status}")
        # Actualizar UI según estado
    
    def on_calibration_progress(self, message):
        """Manejar progreso de calibración"""
        print(f"Calibración: {message}")
        # Mostrar en UI
    
    def on_calibration_completed(self, success):
        """Manejar finalización de calibración"""
        if success:
            print("✓ Calibración completada exitosamente")
        else:
            print("✗ Error en calibración")
    
    # === DATA MANAGER SIGNALS ===
    
    def on_recording_started(self, filename):
        """Manejar inicio de grabación"""
        self.is_recording = True
        print(f"Grabación iniciada: {filename}")
        self.update_ui_recording_state(True)
    
    def on_recording_stopped(self, filename):
        """Manejar fin de grabación"""
        self.is_recording = False
        print(f"Grabación finalizada: {filename}")
        self.update_ui_recording_state(False)
    
    def on_data_point_processed(self, data_point):
        """Manejar punto de datos procesado"""
        # Guardar para coordinación con IMU
        self._last_eye_data = data_point
    
    # === TEST MANAGER SIGNALS ===
    
    def on_user_loaded(self, user_data):
        """Manejar usuario cargado"""
        user_info = self.test_manager.get_current_user_info()
        self.setWindowTitle(f"SIEV - {user_info}")
        self.enable_test_functions(True)
        print(f"Usuario cargado: {user_data.get('nombre', 'Desconocido')}")
    
    def on_user_closed(self):
        """Manejar usuario cerrado"""
        self.setWindowTitle("SIEV")
        self.enable_test_functions(False)
        print("Usuario cerrado")
    
    def on_test_created(self, test_id, test_data):
        """Manejar test creado"""
        print(f"Test creado: {test_id}")
        # Limpiar gráficos para nuevo test
        if hasattr(self.data_manager, 'plot_widget') and self.data_manager.plot_widget:
            self.data_manager.plot_widget.clear_data()
    
    def on_test_started(self, test_id):
        """Manejar test iniciado"""
        print(f"Test iniciado: {test_id}")
    
    def on_test_completed(self, test_id, results):
        """Manejar test completado"""
        print(f"Test completado: {test_id}")
        self.is_recording = False
        self.update_ui_recording_state(False)
    
    def on_stimulus_window_opened(self, protocol):
        """Manejar ventana de estímulos abierta"""
        print(f"Estímulos abiertos para: {protocol}")
        self.update_ui_stimulus_state(True)
    
    def on_stimulus_window_closed(self):
        """Manejar ventana de estímulos cerrada"""
        print("Estímulos cerrados")
        self.update_ui_stimulus_state(False)
    
    def on_evaluator_changed(self, evaluator):
        """Manejar cambio de evaluador"""
        print(f"Evaluador: {evaluator}")
    
    # =========================================================================
    # MÉTODOS DELEGADOS A MANAGERS
    # =========================================================================
    
    # === VIDEO OPERATIONS ===
    
    def start_video_recording(self):
        """Iniciar grabación de video"""
        return self.video_manager.start_recording()
    
    def stop_video_recording(self):
        """Detener grabación de video"""
        self.video_manager.stop_recording()
    
    def switch_to_live_video(self):
        """Cambiar a modo video en vivo"""
        self.video_manager.switch_to_live_mode()
    
    def switch_to_video_player(self, video_data):
        """Cambiar a modo reproductor"""
        return self.video_manager.switch_to_player_mode(video_data)
    
    # === HARDWARE OPERATIONS ===
    
    def send_hardware_command(self, command):
        """Enviar comando al hardware"""
        return self.hardware_manager.send_command(command)
    
    def start_calibration(self):
        """Iniciar calibración"""
        return self.hardware_manager.start_calibration()
    
    def pause_imu(self):
        """Pausar IMU"""
        return self.hardware_manager.pause_imu()
    
    def turn_on_left_led(self):
        """Encender LED izquierdo"""
        return self.hardware_manager.turn_on_left_led()
    
    def turn_on_right_led(self):
        """Encender LED derecho"""
        return self.hardware_manager.turn_on_right_led()
    
    def turn_off_all_leds(self):
        """Apagar todos los LEDs"""
        return self.hardware_manager.turn_off_all_leds()
    
    # === DATA OPERATIONS ===
    
    def start_data_recording(self, test_name=None):
        """Iniciar grabación de datos"""
        return self.data_manager.start_recording(test_name)
    
    def stop_data_recording(self):
        """Detener grabación de datos"""
        return self.data_manager.stop_recording()
    
    def get_recording_status(self):
        """Obtener estado de grabación"""
        return self.data_manager.get_recording_status()
    
    def get_data_statistics(self):
        """Obtener estadísticas de datos"""
        return self.data_manager.get_statistics()
    
    # === TEST OPERATIONS ===
    
    def open_new_user_dialog(self):
        """Abrir diálogo de nuevo usuario"""
        return self.test_manager.open_new_user_dialog()
    
    def open_user_file(self):
        """Abrir archivo de usuario"""
        return self.test_manager.open_user_file()
    
    def close_current_user(self):
        """Cerrar usuario actual"""
        self.test_manager.close_current_user()
    
    
    def change_evaluator(self):
        """Cambiar evaluador"""
        return self.test_manager.change_evaluator()
    
    # =========================================================================
    # CONTROL PRINCIPAL DE TESTS
    # =========================================================================
    
    def toggle_recording(self):
        """Control principal de grabación/tests"""
        try:
            # Obtener info del test actual
            test_info = self.test_manager.get_current_test_info()
            
            if not test_info['test_id']:
                # No hay test seleccionado
                QMessageBox.warning(self, "Sin Test", "Seleccione un test para iniciar")
                return
            
            protocol = test_info['protocol']
            needs_stimulus = test_info['needs_stimulus']
            
            if needs_stimulus:
                self._handle_stimulus_test(test_info)
            else:
                self._handle_normal_test()
                
        except Exception as e:
            print(f"Error en toggle_recording: {e}")
    
    def _handle_stimulus_test(self, test_info):
        """Maneja tests que requieren estímulos"""
        if not test_info['preparation_mode'] and not self.is_recording:
            # Paso 1: Preparar test con estímulos
            print(f"Preparando test con estímulos: {test_info['protocol']}")
            success = self.test_manager.prepare_test_with_stimulus(test_info['protocol'])
            if success:
                self.update_ui_button_state("stimulus_ready")
            
        elif test_info['preparation_mode'] and not self.is_recording:
            # Paso 2: Iniciar grabación
            self._start_complete_recording()
            
        elif self.is_recording:
            # Paso 3: Detener todo
            self._stop_complete_recording()
    
    def _handle_normal_test(self):
        """Maneja tests normales sin estímulos"""
        if not self.is_recording and not self.is_calibrating:
            self._start_complete_recording()
        else:
            self._stop_complete_recording()
    
    def _start_complete_recording(self):
        """Inicia grabación completa (calibración + test)"""
        try:
            print("=== INICIANDO GRABACIÓN COMPLETA ===")
            
            # 1. Iniciar test en TestManager
            test_info = self.test_manager.get_current_test_info()
            success = self.test_manager.start_current_test()
            if not success:
                raise Exception("Error iniciando test")
            
            # 2. Iniciar grabación de datos
            test_name = f"test_{test_info['test_id']}"
            success = self.data_manager.start_recording(test_name)
            if not success:
                raise Exception("Error iniciando grabación de datos")
            
            # 3. Iniciar grabación de video
            success = self.video_manager.start_recording()
            if not success:
                print("ADVERTENCIA: Error iniciando grabación de video")
            
            # 4. Actualizar estado
            self.is_recording = True
            self.update_ui_button_state("recording")
            
            # 5. Configurar timer de duración máxima
            QTimer.singleShot(self.MAX_RECORDING_TIME * 1000, self._stop_complete_recording)
            
        except Exception as e:
            print(f"Error iniciando grabación: {e}")
            self._cleanup_failed_recording()
    
    def _stop_complete_recording(self):
        """Detiene grabación completa"""
        try:
            print("=== DETENIENDO GRABACIÓN COMPLETA ===")
            
            # 1. Detener grabación de datos
            data_filename = self.data_manager.stop_recording()
            
            # 2. Detener grabación de video
            self.video_manager.stop_recording()
            
            # 3. Finalizar test
            test_info = self.test_manager.get_current_test_info()
            if test_info['test_id']:
                results = self.data_manager.analyze_current_session()
                self.test_manager.finalize_current_test(results, stopped_manually=True)
            
            # 4. Actualizar estado
            self.is_recording = False
            self.update_ui_button_state("completed")
            
        except Exception as e:
            print(f"Error deteniendo grabación: {e}")
    
    def _cleanup_failed_recording(self):
        """Limpia estado en caso de error"""
        self.is_recording = False
        self.data_manager.stop_recording()
        self.video_manager.stop_recording()
        self.update_ui_button_state("error")
    
    # =========================================================================
    # MÉTODOS DE UI Y EVENTOS
    # =========================================================================
    
    def on_test_selection_changed(self, current_item, previous_item):
        """Manejar cambio de selección de test"""
        try:
            self.update_test_ui_state()
            
            # Lógica para reproductores de video de tests completados
            # (mantener lógica existente si es necesaria)
            
        except Exception as e:
            print(f"Error en selección de test: {e}")
    
    def update_ui_recording_state(self, recording):
        """Actualizar UI según estado de grabación"""
        if recording:
            self.ui.btn_start.setText("Grabando...")
            self.ui.btn_start.setEnabled(True)
        else:
            self.ui.btn_start.setText("Iniciar")
            self.ui.btn_start.setEnabled(True)
    
    def update_ui_stimulus_state(self, stimulus_open):
        """Actualizar UI según estado de estímulos"""
        if stimulus_open:
            self.ui.btn_start.setText("Iniciar Test")
        else:
            self.ui.btn_start.setText("Iniciar")
    
    def update_ui_button_state(self, state):
        """Actualizar estado del botón principal"""
        states = {
            "ready": ("Iniciar", True),
            "stimulus_ready": ("Iniciar Test", True),
            "recording": ("Detener", True),
            "completed": ("Finalizado", False),
            "error": ("Error", False)
        }
        
        if state in states:
            text, enabled = states[state]
            self.ui.btn_start.setText(text)
            self.ui.btn_start.setEnabled(enabled)
    
    def enable_test_functions(self, enabled):
        """Habilitar/deshabilitar funciones de test"""
        # Implementar según UI específica
        pass
    
    def update_test_ui_state(self):
        """Actualizar estado de UI de tests"""
        # Implementar según UI específica
        pass
    
    # =========================================================================
    # MÉTODOS BÁSICOS DE MAINWINDOW
    # =========================================================================
    
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
    
    def load_config(self):
        """Cargar configuración de la aplicación"""
        try:
            window_config = self.config_manager.get_window_config()
            self.setWindowTitle(window_config["title"])
            
            size = window_config["size"]
            self.resize(size["width"], size["height"])
            
            print(f"Configuración cargada: {window_config['title']}")
            
        except Exception as e:
            print(f"Error cargando configuración: {e}")
            self.setWindowTitle("SIEV")
            self.resize(800, 600)
    
    def fill_cmbres(self, combo, resolution_list, selected_resolution):
        """Llenar combo de resoluciones"""
        combo.clear()
        for resolution in resolution_list:
            combo.addItem(resolution)
        
        if selected_resolution in resolution_list:
            index = resolution_list.index(selected_resolution)
            combo.setCurrentIndex(index)
    
    def eventFilter(self, obj, event):
        """Capturar eventos globales (click derecho)"""
        from PySide6.QtCore import QEvent
        from PySide6.QtGui import QMouseEvent
        
        if event.type() == QEvent.MouseButtonPress:
            if isinstance(event, QMouseEvent) and event.button() == Qt.RightButton:
                self.ui.btn_start.click()
                return True
        return super().eventFilter(obj, event)
    
    # === MÉTODOS PLACEHOLDER PARA IMPLEMENTAR ===
    
    def setup_menu_and_controls(self):
        """Configurar menús y controles - IMPLEMENTAR"""
        pass
    
    def connect_events(self):
        """Conectar eventos de UI - IMPLEMENTAR"""
        pass
    
    def save_slider_configuration(self):
        """Guardar configuración de sliders - DELEGADO AL VIDEO MANAGER"""
        self.video_manager.save_slider_configuration()
    
    def load_slider_configuration(self):
        """Cargar configuración de sliders - DELEGADO AL VIDEO MANAGER"""
        self.video_manager.load_slider_configuration()
    
    # =========================================================================
    # CLEANUP
    # =========================================================================
    
    def closeEvent(self, event):
        """Manejar cierre de la aplicación"""
        try:
            print("Cerrando aplicación...")
            
            # Cleanup de todos los managers
            self.video_manager.cleanup()
            self.hardware_manager.cleanup()
            self.data_manager.cleanup()
            self.test_manager.cleanup()
            
            event.accept()
            
        except Exception as e:
            print(f"Error durante cierre: {e}")
            event.accept()