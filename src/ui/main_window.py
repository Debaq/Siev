import os
import time
from PySide6.QtWidgets import (QMainWindow, QMenu, QWidgetAction, QSlider, 
                            QHBoxLayout, QWidget, QLabel, QCheckBox, 
                            QMessageBox, QDialog, QFileDialog, QTreeWidgetItem)

from PySide6.QtCore import Qt, QTimer

# Diálogos
from ui.dialogs.tracking_dialog import TrackingCalibrationDialog

# Utils
from utils.serial_thread import SerialReadThread
from utils.stimulus_system import StimulusManager
from utils.SerialHandler import SerialHandler
from utils.video.video_widget import VideoWidget
from utils.DetectorNistagmo import DetectorNistagmo
from utils.EyeDataProcessor import EyeDataProcessor
from utils.CalibrationManager import CalibrationManager
from utils.data_storage import DataStorage
from utils.graphing.triple_plot_widget import TriplePlotWidget, PlotConfigurations
from utils.config_manager import ConfigManager
from utils.CameraResolutionDetector import CameraResolutionDetector
from utils.utils import select_max_resolution
from ui.dialogs.user_dialog import NewUserDialog
from utils.SievManager import SievManager
from utils.protocol_manager import ProtocolManager
from datetime import datetime
from ui.views.video_fullscreen_widget import VideoFullscreenWidget
from ui.dialogs.calculadora_hipo_dp_dialog import CalculadoraHipoDpDialog
from ui.dialogs.report_wizard import open_report_wizard


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
        max_res = select_max_resolution(resolution_video, True)
        self.fill_cmbres(self.ui.cb_resolution, resolution_video, max_res)
        # === SISTEMA DE GRABACIÓN ===
        self.is_recording = False
        self.is_calibrating = False
        self.recording_start_time = None
        self.graph_time = 0.0
        self.last_update_time = None
        self.MAX_RECORDING_TIME = 5 * 60  # 5 minutos
        self.CALIBRATION_TIME = 1  # 1 segundo

        # === GESTOR DE USUARIOS ===
        self.siev_manager = None
        self.current_user_siev = None
        self.current_user_data = None
        # === GESTOR DE PROTOCOLOS ===
        self.protocol_manager = ProtocolManager(self)
        self.current_evaluator = None  # Por compatibilidad, aunque se maneja en protocol_manager


        self.calculadorahidp = CalculadoraHipoDpDialog()


        self.enable_test_functions(False)


        # === CONFIGURAR UI ===
        self.setup_menu_and_controls()
        self.connect_events()
        self.load_slider_configuration()

        # === INICIALIZAR COMPONENTES ===
        self.init_video_system()
        self.init_fullscreen_system()
        self.init_serial_system()
        self.init_calibration_system()
        self.init_graphics_system()
        self.init_recording_system()
        self.init_video_recorder()

        self.init_processing_system()
        self.init_user_system()

        # === TIMERS ===
        self.setup_timers()
        self.init_stimulus_system()
        self.setup_right_click_trigger()
        self.init_test_selection_system()
        
       # === CONFIGURAR REFERENCIAS UI PARA VIDEO WIDGET ===
        if self.video_widget:
            self.video_widget.set_ui_references(self.ui.slider_time, self.ui.btn_start)
            print("Referencias UI configuradas para VideoWidget")
            
        self.setup_video_graph_sync()

        # === MOSTRAR PROTOCOLO ===
        #QTimer.singleShot(500, self.show_protocol_selection)
        
        self.showMaximized()
        print("=== SISTEMA VNG INICIADO CORRECTAMENTE ===")

                # Conectar todos los sliders

    def calculadora_hipo_dp(self):
        self.calculadorahidp.exec()


    def handle_gray_frame_for_video(self, gray_frame):
        """Callback para manejar frames gray para grabación"""
        if (self.video_recorder and 
            self.video_recorder.is_recording and 
            self.is_recording):
            self.video_recorder.add_frame(gray_frame)
            
    def init_fullscreen_system(self):
        """Inicializar sistema de pantalla completa"""
        self.fullscreen_widget = None
        
        # Conectar botón fullscreen
        self.ui.btn_FullScreen.clicked.connect(self.toggle_fullscreen)
        
        print("Sistema fullscreen inicializado")


    def init_video_recorder(self):
        """Inicializar grabador de video"""
        try:
            from utils.VideoRecorder import VideoRecorder
            self.video_recorder = VideoRecorder(self)
            print("VideoRecorder inicializado")
        except Exception as e:
            print(f"Error inicializando VideoRecorder: {e}")
            self.video_recorder = None

    def init_test_selection_system(self):
        """
        Inicializar sistema de selección de pruebas
        AGREGAR AL FINAL DE __init__ en MainWindow
        """
        try:
            # Variables de estado
            self.is_reproducing = False
            
            # Conectar señal de selección del tree
            self.ui.listTestWidget.currentItemChanged.connect(self.on_test_selection_changed)
            
            # Inicializar estado del botón
            self.update_test_ui_state()
            
            print("Sistema de selección de pruebas inicializado")
            
        except Exception as e:
            print(f"Error inicializando sistema de selección: {e}")



    # ========================================
    # MANEJO DE SELECCIÓN DE PRUEBAS
    # ========================================




    def on_test_selection_changed(self, current_item, previous_item):
        """MODIFICAR método existente para manejar alternancia de video"""
        try:
            # === LÓGICA EXISTENTE ===
            self.update_test_ui_state()
            self.update_graph_for_selection(current_item)
            
            # === NUEVA LÓGICA: ALTERNANCIA DE VIDEO ===
            selected_test_data = self.get_selected_test_data()
            
            if selected_test_data:
                test_data = selected_test_data['test_data']
                test_estado = test_data.get('estado', '').lower()
                test_id = selected_test_data['test_id']
                hora_fin = test_data.get('hora_fin')
                
                # === USAR LA MISMA LÓGICA QUE update_graph_for_selection ===
                is_completed = (test_estado in ['completada', 'completado'] or hora_fin is not None)
                
                print(f"Evaluando prueba {test_id}: estado='{test_estado}', hora_fin={hora_fin}, is_completed={is_completed}")
                
                if is_completed:
                    # Cargar video para reproducción
                    print(f"Cargando video para prueba completada: {test_id}")
                    video_data = self.load_video_for_test(test_id)
                    if video_data and self.video_widget:
                        self.video_widget.switch_to_player_mode(video_data)
                        self.enable_fullscreen_button()
                    else:
                        print("No se encontró video para la prueba o no hay VideoWidget")
                        # Cambiar a modo live como fallback
                        if self.video_widget:
                            self.video_widget.switch_to_live_mode(self.camera_index)
                else:
                    # Prueba nueva/pendiente - cambiar a modo live
                    print("Prueba no completada - cambiando a modo live")
                    if self.video_widget:
                        self.video_widget.switch_to_live_mode(self.camera_index)
            else:
                # Sin selección - modo live
                print("Sin selección - cambiando a modo live")
                if self.video_widget:
                    self.video_widget.switch_to_live_mode(self.camera_index)
                    
        except Exception as e:
            print(f"Error en cambio de selección: {e}")
            


    def is_test_completed(self, test_data):
        """
        Evaluar si una prueba está completada usando lógica unificada
        
        Args:
            test_data: Datos de la prueba
            
        Returns:
            bool: True si está completada, False si no
        """
        test_estado = test_data.get('estado', '').lower()
        hora_fin = test_data.get('hora_fin')
        
        # Una prueba está completada si:
        # 1. Tiene estado "completada" o "completado", O
        # 2. Tiene hora_fin (aunque el estado esté vacío)
        return (test_estado in ['completada', 'completado'] or hora_fin is not None)

    def load_video_for_test(self, test_id):
        """Cargar video desde archivo .siev para una prueba específica"""
        try:
            if not self.siev_manager or not self.current_user_siev:
                print("Sistema de archivos no disponible")
                return None
            
            # === AGREGAR VERIFICACIÓN PREVIA ===
            if self.siev_manager.has_test_video(self.current_user_siev, test_id):
                print(f"Video confirmado en .siev para {test_id}")
            else:
                print(f"ADVERTENCIA: No se detectó video en .siev para {test_id}")
                return None
            
            # Extraer datos de video del archivo .siev
            video_data = self.siev_manager.extract_test_video_data(
                self.current_user_siev, 
                test_id
            )
            
            if video_data:
                print(f"Video cargado para prueba {test_id}: {len(video_data)} bytes")
                return video_data
            else:
                print(f"No se encontró video para prueba {test_id}")
                return None
                
        except Exception as e:
            print(f"Error cargando video para prueba {test_id}: {e}")
            return None
        

    def update_graph_for_selection(self, current_item):
        """
        Actualizar gráfico según la selección del tree
        """
        try:
            if not hasattr(self, 'plot_widget') or not self.plot_widget:
                print("Widget de gráfico no disponible")
                return
            
            # Si no hay selección o es un item de fecha, limpiar gráfico
            if not current_item or not current_item.parent():
                print("Sin selección válida - limpiando gráfico")
                self.plot_widget.clearPlots()
                return
            
            # Obtener datos de la prueba seleccionada
            item_data = current_item.data(0, Qt.UserRole)
            if not item_data:
                print("Sin datos de prueba - limpiando gráfico")
                self.plot_widget.clearPlots()
                return
            
            test_data = item_data.get('test_data')
            test_id = item_data.get('test_id')
            
            # === USAR MÉTODO HELPER UNIFICADO ===
            is_completed = self.is_test_completed(test_data)
            
            if is_completed:
                # Prueba completada: cargar datos CSV
                print(f"Cargando datos de prueba completada: {test_id} (estado: '{test_data.get('estado')}', hora_fin: {test_data.get('hora_fin')})")
                self.load_test_data_to_graph(test_id, test_data)
            else:
                # Prueba pendiente/en progreso: limpiar gráfico
                print(f"Prueba no completada (estado: '{test_data.get('estado')}', hora_fin: {test_data.get('hora_fin')}) - limpiando gráfico")
                self.plot_widget.clearPlots()
                
        except Exception as e:
            print(f"Error actualizando gráfico para selección: {e}")

    def load_test_data_to_graph(self, test_id, test_data):
        """Cargar datos CSV de una prueba completada al gráfico"""
        try:
            if not self.siev_manager or not self.current_user_siev:
                print("Sistema de archivos no disponible")
                return
            
            # Limpiar gráfico primero
            self.plot_widget.clearPlots()
            
            # Extraer datos CSV del archivo .siev
            csv_data = self.siev_manager.extract_test_csv_data(
                self.current_user_siev, 
                test_id
            )
            
            if not csv_data:
                print(f"No se encontraron datos CSV para prueba {test_id}")
                return
            
            print(f"Cargando {len(csv_data)} puntos de datos al gráfico")
            
            # CONVERTIR TIMESTAMPS A TIEMPO RELATIVO
            first_timestamp = None
            right_eye_x_values = []
            relative_timestamps = []
            
            for i, row in enumerate(csv_data):
                try:
                    timestamp = float(row.get('timestamp', 0))
                    
                    # Establecer tiempo de referencia
                    if first_timestamp is None:
                        first_timestamp = timestamp
                    
                    # Convertir a tiempo relativo (segundos desde el inicio)
                    relative_time = timestamp - first_timestamp
                    
                    right_eye = None  
                    if row.get('right_eye_detected', False) and row.get('right_eye_x') is not None:
                        right_eye_x = float(row.get('right_eye_x', 0))
                        right_eye_y = float(row.get('right_eye_y', 0))
                        right_eye = [right_eye_x, right_eye_y]
                        
                        # RECOLECTAR DATOS PARA DEBUG
                        right_eye_x_values.append(right_eye_x)
                        relative_timestamps.append(relative_time)
                    
                    left_eye = None
                    if row.get('left_eye_detected', False) and row.get('left_eye_x') is not None:
                        left_eye = [float(row.get('left_eye_x', 0)), float(row.get('left_eye_y', 0))]
                    
                    imu_x = float(row.get('imu_x', 0))
                    imu_y = float(row.get('imu_y', 0))
                    
                    # USAR TIEMPO RELATIVO PARA EL GRÁFICO
                    data_point = [left_eye, right_eye, imu_x, imu_y, relative_time]
                    self.plot_widget.updatePlots(data_point)
                    
                except (ValueError, TypeError) as e:
                    print(f"Error procesando punto {i}: {e}")
                    continue
            
            # === AJUSTE AUTOMÁTICO MEJORADO ===
            if right_eye_x_values and hasattr(self.plot_widget, 'plots') and self.plot_widget.plots:
                print("=== AJUSTANDO ZOOM MEJORADO ===")
                
                min_x = min(right_eye_x_values)
                max_x = max(right_eye_x_values)
                min_time = min(relative_timestamps)
                max_time = max(relative_timestamps)
                
                print(f"Datos finales:")
                print(f"  Tiempo: 0 → {max_time:.2f} segundos")
                print(f"  Posición X: {min_x} → {max_x}")
                print(f"  Variación: {max_x - min_x} píxeles")
                
                # Margen más agresivo para ver la curva
                x_margin = max(10, (max_x - min_x) * 0.2)  # Mínimo 10 píxeles de margen
                time_margin = max(0.5, (max_time - min_time) * 0.1)  # Mínimo 0.5s de margen
                
                # Ajustar cada gráfico
                for i, plot in enumerate(self.plot_widget.plots):
                    # Rango temporal (eje X del gráfico)
                    plot.setXRange(min_time - time_margin, max_time + time_margin, padding=0)
                    # Rango de datos (eje Y del gráfico)
                    plot.setYRange(min_x - x_margin, max_x + x_margin, padding=0)
                    
                    print(f"Gráfico {i+1} ajustado:")
                    print(f"  Tiempo: {min_time - time_margin:.2f} → {max_time + time_margin:.2f}s")
                    print(f"  Valores: {min_x - x_margin:.1f} → {max_x + x_margin:.1f}")
                    
                    # Forzar redibujado
                    plot.getViewBox().updateAutoRange()
            
            print(f"Datos cargados con tiempo relativo (0 → {max_time:.2f}s)")
            
        except Exception as e:
            print(f"Error cargando datos al gráfico: {e}")

    def get_selected_test_data(self):
        """Obtener datos de la prueba seleccionada"""
        try:
            current_item = self.ui.listTestWidget.currentItem()
            
            if current_item and current_item.parent():  # Es un item de prueba
                item_data = current_item.data(0, Qt.UserRole)
                if item_data:
                    return item_data
                    
            return None
            
        except Exception as e:
            print(f"Error obteniendo datos de prueba seleccionada: {e}")
            return None
        
    # ========================================
    # ACTUALIZACIÓN DE ESTADO DE UI
    # ========================================

    def update_test_ui_state(self):
        """Actualizar estado de UI según la prueba seleccionada"""
        try:
            selected_test_data = self.get_selected_test_data()
            
            if not selected_test_data:
                # Sin selección
                self._set_no_selection_state()
            else:
                test_data = selected_test_data['test_data']
                test_name = test_data.get('tipo', 'Prueba')
                test_estado = test_data.get('estado', '').lower()
                
                # Actualizar label de prueba
                self._set_test_name_display(test_name)
                
                # Configurar botón según estado
                if test_estado == 'completada':
                    self._set_reproduction_button_state()
                elif test_estado in ['pendiente', 'ejecutando']:
                    self._set_recording_button_state()
                else:
                    self._set_unknown_state()
                    
        except Exception as e:
            print(f"Error actualizando estado de UI: {e}")

    def _set_no_selection_state(self):
        """Estado: Sin prueba seleccionada"""
        self.ui.lbl_test.setText("Selecciona una prueba")
        self.ui.lbl_test.setStyleSheet("")
        self.ui.btn_start.setText("Iniciar")
        self.ui.btn_start.setEnabled(False)

    def _set_test_name_display(self, test_name):
        """Mostrar nombre de prueba con formato mejorado"""
        self.ui.lbl_test.setText(test_name)
        self.ui.lbl_test.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #2196F3;
                padding: 5px;
            }
        """)

    def _set_reproduction_button_state(self):
        """Estado: Prueba completada - botón de reproducción"""
        if self.is_reproducing:
            self.ui.btn_start.setText("Pausar")
            self.ui.btn_start.setStyleSheet("""
                QPushButton {
                    background-color: #FF9800; 
                    color: white; 
                    font-weight: bold;
                    font-size: 14px; 
                    padding: 10px; 
                    border: none; 
                    border-radius: 5px;
                }
                QPushButton:hover { background-color: #F57C00; }
            """)
        else:
            self.ui.btn_start.setText("Reproducir")
            self.ui.btn_start.setStyleSheet("""
                QPushButton {
                    background-color: #9C27B0; 
                    color: white; 
                    font-weight: bold;
                    font-size: 14px; 
                    padding: 10px; 
                    border: none; 
                    border-radius: 5px;
                }
                QPushButton:hover { background-color: #7B1FA2; }
            """)
        self.ui.btn_start.setEnabled(True)

    def _set_recording_button_state(self):
        """Estado: Prueba nueva/en ejecución - botón de grabación"""
        if self.is_recording or self.is_calibrating:
            self.ui.btn_start.setText("Detener")
            self.ui.btn_start.setStyleSheet("""
                QPushButton {
                    background-color: #f44336; 
                    color: white; 
                    font-weight: bold;
                    font-size: 14px; 
                    padding: 10px; 
                    border: none; 
                    border-radius: 5px;
                }
                QPushButton:hover { background-color: #da190b; }
            """)
        else:
            self.ui.btn_start.setText("Iniciar")
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
                QPushButton:hover { background-color: #45a049; }
            """)
        self.ui.btn_start.setEnabled(True)

    def _set_unknown_state(self):
        """Estado: Prueba con estado desconocido"""
        self.ui.btn_start.setText("Iniciar")
        self.ui.btn_start.setEnabled(False)


    # ========================================
    # 4. DISPLAY DE TIEMPO EN LBL_TEST
    # ========================================

    def update_time_display_in_test_label(self, time_text):
        """Actualizar display de tiempo en el label de prueba durante ejecución/reproducción"""
        try:
            selected_test_data = self.get_selected_test_data()
            
            if selected_test_data:
                test_name = selected_test_data['test_data'].get('tipo', 'Prueba')
                
                # Mostrar nombre y tiempo con formato grande y visible
                display_text = f"{test_name}\n{time_text}"
                
                self.ui.lbl_test.setText(display_text)
                self.ui.lbl_test.setStyleSheet("""
                    QLabel {
                        font-size: 18px;
                        font-weight: bold;
                        color: #1976D2;
                        background-color: #E3F2FD;
                        border: 2px solid #2196F3;
                        border-radius: 8px;
                        padding: 10px;
                        text-align: center;
                    }
                """)
                
        except Exception as e:
            print(f"Error actualizando display de tiempo: {e}")

    def update_recording_display(self):
        """Actualizar display de tiempo durante grabación"""
        try:
            if not (self.is_recording or self.is_calibrating):
                return
                
            current_time = time.time()
            
            if self.is_calibrating:
                # Durante calibración
                elapsed = current_time - self.recording_start_time
                remaining = max(0, self.CALIBRATION_TIME - elapsed)
                time_text = f"Calibrando: {remaining:.1f}s"
                
            elif self.is_recording:
                # Durante grabación
                elapsed = current_time - self.recording_start_time
                time_text = f"Grabando: {elapsed:.1f}s"
                
                # Agregar duración total si está disponible
                if hasattr(self, 'total_recording_time') and self.total_recording_time:
                    progress = (elapsed / self.total_recording_time) * 100
                    time_text += f" ({progress:.1f}%)"
            
            # Actualizar display en lbl_test
            self.update_time_display_in_test_label(time_text)
            
        except Exception as e:
            print(f"Error actualizando display de grabación: {e}")

    def update_reproduction_display(self, current_time, total_time):
        """Actualizar display durante reproducción"""
        try:
            if not self.is_reproducing:
                return
                
            progress = (current_time / total_time) * 100 if total_time > 0 else 0
            time_text = f"Reproduciendo: {current_time:.1f}s / {total_time:.1f}s ({progress:.1f}%)"
            
            self.update_time_display_in_test_label(time_text)
            
        except Exception as e:
            print(f"Error actualizando display de reproducción: {e}")







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
                camera_id=self.camera_index,
                video_callback=self.handle_gray_frame_for_video

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

    def init_user_system(self):
        """Inicializar sistema de usuarios"""
        try:
            # Crear directorio de usuarios si no existe
            users_path = os.path.join(self.data_path, "users")
            self.siev_manager = SievManager(users_path)
            print(f"Sistema de usuarios inicializado: {users_path}")
        except Exception as e:
            print(f"Error inicializando sistema de usuarios: {e}")
            self.siev_manager = None

    def init_processing_system(self):
        """Inicializar sistema de procesamiento de datos"""
        try:
            self.eye_processor = EyeDataProcessor()
            self.eye_processor.set_processing_enabled(False)  # ← DESACTIVAR PROCESAMIENTO
            self.eye_processor.set_smoothing_enabled(False)   # ← SIN SUAVIZADO
            self.eye_processor.set_interpolation_enabled(False) # ← SIN INTERPOLACIÓN
            self.eye_processor.set_kalman_enabled(False)      # ← SIN KALMAN
            self.eye_processor.set_extra_smoothing(False)     # ← SIN SUAVIZADO EXTRA
            # Configuración optimizada
            #self.eye_processor.set_filter_strength(0.4)
            #self.eye_processor.set_interpolation_steps(2)
            #self.eye_processor.set_history_size(3)
            #self.eye_processor.set_smoothing_enabled(True)
            #self.eye_processor.set_interpolation_enabled(True)
            
            # Kalman filter
            #self.eye_processor.set_kalman_enabled(True)
            #self.eye_processor.set_kalman_parameters(
            #    process_noise=0.001,
            #    measurement_noise=0.3,
            #    stability_factor=0.01
            #)
            
            #self.eye_processor.set_extra_smoothing(True, buffer_size=5)
            
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
        #self.nistagmo_timer = QTimer()
        #self.nistagmo_timer.timeout.connect(self.process_nystagmus)
        #self.nistagmo_timer.start(2000)

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

                
        except Exception as e:
            print(f"Error configurando menú: {e}")

    def connect_events(self):
        """Conectar eventos principales"""
        try:
            # Botón de grabación
            self.ui.btn_start.clicked.connect(self.handle_btn_start_click)
            
            # Conectar acciones del menú archivo
            self.ui.actionNewUser.triggered.connect(self.open_new_user_dialog)
            self.ui.actionExit.triggered.connect(self.close)
            self.ui.actionAbrir.triggered.connect(self.open_user_file)
            
            # Conectar cambio de evaluador
            if hasattr(self.ui, 'actionCambiar_evaluador'):
                self.ui.actionCambiar_evaluador.triggered.connect(self.protocol_manager.change_evaluator)

            # Conectar protocolos calóricos
            if hasattr(self.ui, 'actionOD_44'):
                self.ui.actionOD_44.triggered.connect(lambda: self.protocol_manager.open_protocol_dialog("OD_44"))
            if hasattr(self.ui, 'actionOI_44'):
                self.ui.actionOI_44.triggered.connect(lambda: self.protocol_manager.open_protocol_dialog("OI_44"))
            if hasattr(self.ui, 'actionOD_30'):
                self.ui.actionOD_30.triggered.connect(lambda: self.protocol_manager.open_protocol_dialog("OD_30"))
            if hasattr(self.ui, 'actionOI_30'):
                self.ui.actionOI_30.triggered.connect(lambda: self.protocol_manager.open_protocol_dialog("OI_30"))

            # Conectar protocolos oculomotores
            if hasattr(self.ui, 'actionSeguimiento_Lento'):
                self.ui.actionSeguimiento_Lento.triggered.connect(lambda: self.protocol_manager.open_protocol_dialog("seguimiento_lento"))
            if hasattr(self.ui, 'actionOptoquinetico'):
                self.ui.actionOptoquinetico.triggered.connect(lambda: self.protocol_manager.open_protocol_dialog("optoquinetico"))
            if hasattr(self.ui, 'actionSacadas'):
                self.ui.actionSacadas.triggered.connect(lambda: self.protocol_manager.open_protocol_dialog("sacadas"))
            if hasattr(self.ui, 'actionEspont_neo'):
                self.ui.actionEspont_neo.triggered.connect(lambda: self.protocol_manager.open_protocol_dialog("espontaneo"))

            # Conectar calibración
            if hasattr(self.ui, 'actionCalibrar'):
                self.ui.actionCalibrar.triggered.connect(self.start_calibration)
            if hasattr(self.ui, 'actionCalculadora_hipo_dp'):
                self.ui.actionCalculadora_hipo_dp.triggered.connect(self.calculadora_hipo_dp)
            if hasattr(self.ui, 'actionInforme'):
                self.ui.actionInforme.triggered.connect(self.openInforme)
                
                

        except Exception as e:
            print(f"Error conectando eventos: {e}")


    def openInforme(self):
        open_report_wizard(self)


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
            self.ui.btn_start.clicked.connect(self.handle_btn_start_click)
        
        # Restaurar label
        if hasattr(self.ui, 'lbl_time'):
            self.ui.lbl_time.setText("00:00 / 05:00")
            self.ui.lbl_time.setStyleSheet("")
        
        # Iniciar calibración
        QTimer.singleShot(500, self.start_calibration)


    def handle_btn_start_click(self):
        """Manejar click del botón start según el modo actual"""
        if (hasattr(self.video_widget, 'is_in_player_mode') and 
            self.video_widget.is_in_player_mode):
            # Modo reproductor - delegar al video_widget
            self.video_widget.toggle_playback()
        else:
            # Modo normal - función de grabación
            self.toggle_recording()

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
            
            # ===============================================
            # DATOS CRUDOS PARA CSV - SIN PROCESAMIENTO
            # ===============================================
            if self.is_recording:
                # Datos completamente crudos - sin procesar NADA
                raw_left = processed_left
                raw_right = processed_right
                raw_imu_x = float(self.pos_hit[0])
                raw_imu_y = float(self.pos_hit[1])
                raw_timestamp = time.time()
                
                # Almacenar datos tal como vienen de la cámara
                self.data_storage.add_data_point(
                    raw_left, raw_right, raw_imu_x, raw_imu_y, raw_timestamp
                )
                self.total_data_points += 1
                
                # Debug cada 100 puntos para ver qué se está guardando
                if self.total_data_points % 100 == 0:
                    print(f"DATOS CRUDOS #{self.total_data_points}:")
                    print(f"  Left: {raw_left}")
                    print(f"  Right: {raw_right}")
                    print(f"  IMU: ({raw_imu_x}, {raw_imu_y})")
                    print(f"  Timestamp: {raw_timestamp}")
            
            # ===============================================
            # GRÁFICA CON DATOS CRUDOS TAMBIÉN
            # ===============================================
            current_time = time.time()
            if current_time - self.last_graph_update >= (self.graph_update_interval / 1000.0):
                # Enviar datos crudos a la gráfica (sin procesamiento)
                raw_left = processed_left
                raw_right = processed_right
                raw_imu_x = float(self.pos_hit[0])
                raw_imu_y = float(self.pos_hit[1])
                
                # Crear un solo punto crudo para la gráfica
                graph_point = (raw_left, raw_right, raw_imu_x, raw_imu_y, self.graph_time)
                self.graph_data_buffer.append(graph_point)
                self.last_graph_update = current_time
            
        except Exception as e:
            print(f"Error en handle_eye_positions: {e}")
            import traceback
            traceback.print_exc()
        

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
        """MODIFICAR método existente para manejar ambos modos"""
        
        # === NUEVA LÓGICA: Si está en modo player, controlar reproducción ===
        if (hasattr(self.video_widget, 'is_in_player_mode') and 
            self.video_widget.is_in_player_mode):
            self.video_widget.toggle_playback()
            return
        
        # === LÓGICA ORIGINAL PARA GRABACIÓN ===
        try:
            if not self.is_recording and not self.is_calibrating:
                self.start_recording()
            else:
                self.stop_test_recording()  # ← CAMBIAR AQUÍ
        except Exception as e:
            print(f"Error en toggle_recording: {e}")

    def setup_video_graph_sync(self):
        """
        Configura la sincronización bidireccional entre video y gráficos.
        """
        if not (self.video_widget and self.plot_widget):
            return
        
        try:
            # Crear señal para sincronización video->gráfico
            from PySide6.QtCore import Signal
            
            # Agregar atributo de señal al plot_widget si no existe
            if not hasattr(self.plot_widget, 'video_sync_signal'):
                self.plot_widget.video_sync_signal = Signal(float)
            
            # Conectar: cuando cambie slider del video -> actualizar líneas del gráfico
            if hasattr(self.video_widget, 'slider_time'):
                self.video_widget.slider_time.valueChanged.connect(
                    self.on_video_slider_changed
                )
            
            # Conectar: cuando se mueva línea del gráfico -> actualizar video
            self.plot_widget.video_sync_signal.connect(
                self.on_graph_line_moved
            )
            
            print("Sincronización video-gráfico configurada")
            
        except Exception as e:
            print(f"Error configurando sincronización: {e}")

    def on_video_slider_changed(self, slider_value):
        """
        Callback cuando cambia el slider del video.
        Sincroniza las líneas del gráfico.
        """
        print("ajustando la linea vertical")
        try:
            # Convertir valor del slider a segundos
            time_seconds = slider_value / 100.0
            
            # Actualizar líneas del gráfico
            if (self.plot_widget and 
                hasattr(self.plot_widget, 'set_video_time_position')):
                self.plot_widget.set_video_time_position(time_seconds)
                
        except Exception as e:
            print(f"Error sincronizando desde video a gráfico: {e}")

    def on_graph_line_moved(self, seconds):
        """
        Callback cuando se mueve una línea del gráfico.
        Sincroniza el video a esa posición.
        """
        try:
            if (self.video_widget and 
                hasattr(self.video_widget, 'video_player_thread') and
                self.video_widget.video_player_thread and
                self.video_widget.is_in_player_mode):
                
                # Sincronizar video a la nueva posición
                self.video_widget.video_player_thread.seek_to_time(seconds)
                
                # Actualizar slider del video
                if hasattr(self.video_widget, 'slider_time'):
                    slider_value = int(seconds * 100)
                    self.video_widget.slider_time.blockSignals(True)
                    self.video_widget.slider_time.setValue(slider_value)
                    self.video_widget.slider_time.blockSignals(False)
                    
            print(f"Video sincronizado a: {seconds:.2f}s")
            
        except Exception as e:
            print(f"Error sincronizando desde gráfico a video: {e}")



    # ========================================
    # 6. FUNCIONES DE REPRODUCCIÓN
    # ========================================

    def iniciar_reproduccion(self):
        """Iniciar reproducción de una prueba completada"""
        try:
            selected_test_data = self.get_selected_test_data()
            
            if not selected_test_data:
                print("No hay prueba seleccionada para reproducir")
                return
                
            test_data = selected_test_data['test_data']
            test_id = selected_test_data['test_id']
            
            print(f"Iniciando reproducción de prueba: {test_data.get('tipo', 'Desconocida')}")
            
            # Llamar al método reproducir
            self.reproducir()
            
            # Actualizar estado
            self.is_reproducing = True
            self.update_test_ui_state()
            
        except Exception as e:
            print(f"Error iniciando reproducción: {e}")

    def pausar_reproduccion(self):
        """Pausar reproducción actual"""
        try:
            print("Pausando reproducción")
            
            # Pausar la reproducción (implementar según necesidades)
            
            self.is_reproducing = False
            self.update_test_ui_state()
            
        except Exception as e:
            print(f"Error pausando reproducción: {e}")

    def reproducir(self):
        """
        Método para reproducir una prueba completada
        IMPLEMENTACIÓN PENDIENTE - estructura base
        """
        try:
            selected_test_data = self.get_selected_test_data()
            
            if not selected_test_data:
                print("No hay prueba seleccionada para reproducir")
                return
                
            test_data = selected_test_data['test_data']
            test_id = selected_test_data['test_id']
            
            print(f"=== REPRODUCIENDO PRUEBA ===")
            print(f"ID: {test_id}")
            print(f"Tipo: {test_data.get('tipo', 'Desconocida')}")
            print(f"Fecha: {test_data.get('fecha', 'Sin fecha')}")
            print(f"Evaluador: {test_data.get('evaluador', 'Desconocido')}")
            
            # TODO: Implementar lógica específica de reproducción
            # - Cargar datos CSV de la prueba
            # - Configurar gráficos para mostrar datos grabados
            # - Implementar controles de reproducción
            # - Mostrar progreso en el display de tiempo
            
            print("Método reproducir() - estructura lista para implementación")
            
        except Exception as e:
            print(f"Error en método reproducir: {e}")



    def start_test_recording(self):
        """Iniciar grabación con integración de protocolo"""
        try:
            # Obtener ID de prueba actual
            current_test_id = self.protocol_manager.get_current_test_id()
            
            if not current_test_id:
                print("No hay prueba activa. Debe crear una prueba primero.")
                QMessageBox.warning(
                    self,
                    "Sin Prueba Activa",
                    "Debe crear una prueba antes de iniciar la grabación.\n"
                    "Use el menú Protocolos para crear una nueva prueba."
                )
                return
            
            # Marcar inicio en protocol_manager
            if not self.protocol_manager.start_test(current_test_id):
                print("Error iniciando prueba en protocol_manager")
                return
            
            # Iniciar calibración o grabación según corresponda
            if hasattr(self, 'current_protocol') and self.current_protocol in ['sacadas', 'seguimiento_lento', 'ng_optocinetico']:
                # Protocolos con estímulos
                self.toggle_recording_with_stimulus()
            else:
                # Protocolos normales
                self.start_calibration_phase()
            
            # Actualizar botón
            self.ui.btn_start.setText("Detener")
            self.ui.btn_start.setEnabled(True)
            
            print(f"Prueba {current_test_id} iniciada")
            
        except Exception as e:
            print(f"Error iniciando prueba: {e}")

    def stop_test_recording(self):
        """Detener grabación y finalizar prueba"""
        try:
            # Obtener ID de prueba actual
            current_test_id = self.protocol_manager.get_current_test_id()
            
            if not current_test_id:
                print("No se encontró prueba activa para finalizar")
            
            # Detener grabación
            was_recording = self.is_recording
            
            if was_recording or self.is_calibrating:
                self.stop_recording()  # Método original de detención
            
            # Cerrar ventana de estímulos si está abierta
            if hasattr(self, 'stimulus_manager') and self.stimulus_manager:
                self.stimulus_manager.close_stimulus_window()
                
            # Resetear estados de estímulos
            if hasattr(self, 'test_preparation_mode'):
                self.test_preparation_mode = False
                self.test_ready_to_start = False
            
            # Finalizar en protocol_manager
            if current_test_id and was_recording:
                self.protocol_manager.finalize_test(current_test_id, stopped_manually=True)
            
            # Actualizar botón a estado final
            self.ui.btn_start.setText("Finalizado")
            self.ui.btn_start.setEnabled(False)
            self.update_test_ui_state()  # Actualizar UI inmediatamente

            print(f"Prueba {current_test_id} finalizada")
            
        except Exception as e:
            print(f"Error deteniendo prueba: {e}")

    def on_recording_time_expired(self):
        """Manejar finalización automática por tiempo cumplido"""
        try:
            print("=== TIEMPO DE GRABACIÓN CUMPLIDO ===")
            
            # Obtener ID de prueba actual
            current_test_id = self.protocol_manager.get_current_test_id()
            
            # Detener grabación
            self.stop_recording()  # Método original
            
            # Finalizar en protocol_manager
            if current_test_id:
                self.protocol_manager.finalize_test(current_test_id, stopped_manually=False)
            
            # Actualizar botón a estado final
            self.ui.btn_start.setText("Finalizado")
            self.ui.btn_start.setEnabled(False)
            self.update_test_ui_state()  # Actualizar UI inmediatamente

            print(f"Prueba {current_test_id} finalizada automáticamente")
            
        except Exception as e:
            print(f"Error en finalización automática: {e}")

    def reset_button_for_new_test(self):
        """
        MODIFICAR EL MÉTODO EXISTENTE - Resetear botón para nueva prueba
        """
        try:
            # Resetear estados
            if hasattr(self, 'test_preparation_mode'):
                self.test_preparation_mode = False
                self.test_ready_to_start = False
            
            self.is_reproducing = False
            
            # Actualizar UI usando el nuevo sistema
            self.update_test_ui_state()
            
            print("Botón reseteado para nueva prueba")
            
        except Exception as e:
            print(f"Error reseteando botón: {e}")



    def update_time_displays(self):
        """
        Método unificado para actualizar displays de tiempo
        USAR EN TIMERS EXISTENTES en lugar de actualizar lbl_time directamente
        """
        try:
            # Durante calibración o grabación
            if self.is_recording or self.is_calibrating:
                self.update_recording_display()
            
            # Durante reproducción
            elif self.is_reproducing:
                # Integrar con sistema de reproducción cuando esté implementado
                # self.update_reproduction_display(current_time, total_time)
                pass
                
            # Otras actualizaciones de tiempo (nistagmo timer, etc.)
            # pueden continuar normalmente
            
        except Exception as e:
            print(f"Error actualizando displays de tiempo: {e}")


    # ========================================
    # 7. MODIFICACIONES A MÉTODOS EXISTENTES
    # ========================================

    def start_calibration_phase(self):
        """
        MODIFICAR EL MÉTODO EXISTENTE - Iniciar fase de calibración
        """
        print("=== INICIANDO CALIBRACIÓN ===")
        self.is_calibrating = True
        self.eye_processor.reset_calibration()
        
        self.recording_start_time = time.time()
        self.last_update_time = time.time()
        self.graph_time = -self.CALIBRATION_TIME
        
        # Actualizar UI con nuevo sistema
        self.update_test_ui_state()
        self.update_time_display_in_test_label(f"Calibrando: {self.CALIBRATION_TIME}s")
        
        self.send_to_graph = True
        QTimer.singleShot(self.CALIBRATION_TIME * 1000, self.start_recording)

    def start_recording(self):
        """
        MODIFICAR EL MÉTODO EXISTENTE - Iniciar grabación real
        """
        print("=== INICIANDO GRABACIÓN ENTRAMOS A START_RECORDING ===")
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
        
        # === INICIAR GRABACIÓN DE VIDEO ===
        if self.video_recorder:
            # Obtener protocolo de la prueba actual
            current_test_data = self.get_selected_test_data()
            if current_test_data:
                protocol = current_test_data['test_data'].get('tipo', 'desconocido')
                test_id = self.protocol_manager.get_current_test_id()
                self.video_recorder.start_recording(test_id)
        
        # Actualizar UI usando el nuevo sistema
        self.update_test_ui_state()
        self.send_to_graph = True  


    def stop_recording(self):
        """
        MODIFICAR EL MÉTODO EXISTENTE - Detener grabación
        """
        print("=== DETENIENDO GRABACIÓN ===")
        
        was_recording = self.is_recording
        
        # Estados
        self.is_recording = False
        self.is_calibrating = False
        self.recording_start_time = None
        self.last_update_time = None
        self.graph_time = 0.0
        self.send_to_graph = False
        
        # Detener almacenamiento de datos
        if was_recording:
            self.data_storage.stop_recording()
            
            # Mostrar estadísticas finales
            stats = self.data_storage.get_statistics()
            print(f"Grabación completada:")
            print(f"  - Total de muestras: {stats.get('total_samples', 0)}")
            print(f"  - Duración: {stats.get('duration_seconds', 0):.1f}s")
            print(f"  - Tasa de muestreo: {stats.get('sample_rate', 0):.1f} Hz")
            print(f"  - Detección ojo izq: {stats.get('left_eye_detection_rate', 0):.1f}%")
            print(f"  - Detección ojo der: {stats.get('right_eye_detection_rate', 0):.1f}%")
        
        # === DETENER Y GUARDAR VIDEO ===
        if self.video_recorder and self.video_recorder.is_recording:
            video_path = self.video_recorder.stop_recording()
            if video_path:
                # Guardar en .siev
                success = self.video_recorder.save_to_siev(video_path)
                if success:
                    print("Video guardado exitosamente en archivo .siev")
                else:
                    print("Error guardando video en archivo .siev")
            else:
                print("Error: No se pudo obtener el archivo de video")
        
        # Configurar gráfica para exploración
        if self.plot_widget:
            self.plot_widget.set_recording_state(False)
        
        # UI
        self.ui.btn_start.setText("Iniciar")
        self.ui.lbl_time.setText("00:00 / 05:00")
        
        # Actualizar estado del sistema de pruebas
        self.update_test_ui_state()
        
        print("Grabación detenida")
        
        try:
            # Después de guardar y completar la grabación
            if self.video_widget and hasattr(self.video_widget, 'is_in_player_mode'):
                # Pequeña demora para asegurar que la grabación terminó
                QTimer.singleShot(1000, lambda: self.video_widget.switch_to_live_mode(self.camera_index))
                print("Programado cambio a modo live post-grabación")
        except Exception as e:
            print(f"Error programando cambio a modo live: {e}")


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
        self.update_fullscreen_time()


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



    def open_user_file(self):
        """Abrir archivo de usuario existente (.siev)"""
        try:
            # Directorio inicial - ruta de usuarios predeterminada
            if self.siev_manager:
                initial_dir = self.siev_manager.base_path
            else:
                initial_dir = os.path.expanduser("~/siev_data/users")
            
            # Asegurar que el directorio existe
            os.makedirs(initial_dir, exist_ok=True)
            
            # Abrir diálogo de archivo
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Abrir Usuario - Sistema VNG",
                initial_dir,
                "Archivos SIEV (*.siev);;Todos los archivos (*.*)"
            )
            
            if file_path:
                self.load_user_from_file(file_path)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error abriendo archivo de usuario: {e}")

    def load_user_from_file(self, file_path):
        """Cargar usuario desde archivo .siev"""
        try:
            if not self.siev_manager:
                QMessageBox.critical(self, "Error", "Sistema de usuarios no inicializado")
                return
            
            # Validar archivo .siev
            validation = self.siev_manager.validate_siev(file_path)
            
            if not validation["valid"]:
                error_msg = "Archivo .siev inválido:\n\n" + "\n".join(validation["errors"])
                if validation["warnings"]:
                    error_msg += "\n\nAdvertencias:\n" + "\n".join(validation["warnings"])
                
                QMessageBox.warning(self, "Archivo Inválido", error_msg)
                return
            
            # Mostrar advertencias si las hay
            if validation["warnings"]:
                warning_msg = "El archivo se puede abrir pero tiene advertencias:\n\n" + "\n".join(validation["warnings"])
                QMessageBox.warning(self, "Advertencias", warning_msg)
            
            # Cargar datos del usuario
            user_data = self.siev_manager.get_user_info(file_path)
            
            if not user_data:
                QMessageBox.warning(self, "Error", "No se pudieron cargar los datos del usuario")
                return
            
            # Cerrar usuario anterior si existe
            self.close_current_user()
            
            # Establecer nuevo usuario
            self.current_user_siev = file_path
            self.current_user_data = user_data
            
            # Actualizar interfaz
            self.update_ui_for_user(user_data)
            
            # Cargar pruebas del usuario
            self.load_user_tests()
            
            # Mensaje de confirmación
            user_name = user_data.get('nombre', 'Usuario')
            file_name = os.path.basename(file_path)
            
            QMessageBox.information(
                self, 
                "Usuario Cargado", 
                f"Usuario '{user_name}' cargado exitosamente.\n\n"
                f"Archivo: {file_name}\n"
                f"Total de pruebas: {len(self.siev_manager.get_user_tests(file_path))}"
            )
            
            print(f"Usuario cargado: {user_name} desde {file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error cargando usuario: {e}")
            print(f"Error detallado cargando usuario: {e}")

    def close_current_user(self):
        """Cerrar usuario actual y limpiar interfaz"""
        try:
            if self.current_user_siev:
                print(f"Cerrando usuario: {self.current_user_data.get('nombre', 'Desconocido')}")
            
            # Limpiar variables
            self.current_user_siev = None
            self.current_user_data = None
            
            # Limpiar interfaz
            self.ui.listTestWidget.clear()
            self.ui.listTestWidget.setHeaderLabel("Sin usuario seleccionado")
            self.setWindowTitle("Sistema VNG")
            
            # Limpiar datos de sesión del protocolo
            if hasattr(self, 'protocol_manager'):
                self.protocol_manager.clear_session_data()
            
            # Deshabilitar funciones que requieren usuario
            self.enable_test_functions(False)
            
        except Exception as e:
            print(f"Error cerrando usuario actual: {e}")

    def get_current_user_info(self):
        """Obtener información del usuario actual para mostrar en la interfaz"""
        try:
            if not self.current_user_data:
                return "Sin usuario seleccionado"
            
            user_name = self.current_user_data.get('nombre', 'Desconocido')
            user_id = self.current_user_data.get('rut_id', '')
            
            if user_id:
                return f"{user_name} ({user_id})"
            else:
                return user_name
                
        except Exception as e:
            print(f"Error obteniendo info de usuario: {e}")
            return "Error obteniendo usuario"



    def open_new_user_dialog(self):
        """Abrir diálogo para crear nuevo usuario"""
        try:
            dialog = NewUserDialog(self)
            if dialog.exec() == QDialog.Accepted:
                user_data = dialog.get_user_data()
                if user_data:
                    self.create_new_user(user_data)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error abriendo diálogo de usuario: {e}")


    def create_new_user(self, user_data):
        """Crear nuevo usuario y archivo .siev"""
        try:
            if not self.siev_manager:
                QMessageBox.critical(self, "Error", "Sistema de usuarios no inicializado")
                return
            
            # Crear archivo .siev para el usuario
            siev_path = self.siev_manager.create_user_siev(user_data)
            
            # Establecer como usuario actual
            self.current_user_siev = siev_path
            self.current_user_data = user_data
            
            # Actualizar interfaz
            self.update_ui_for_user(user_data)
            
            # Limpiar lista de pruebas (nuevo usuario, sin pruebas)
            self.ui.listTestWidget.clear()
            
            # *** NUEVA LÓGICA: Limpiar gráfico para nuevo usuario ***
            if hasattr(self, 'plot_widget') and self.plot_widget:
                print("Nuevo usuario - limpiando gráfico")
                self.plot_widget.clearPlots()
            
            QMessageBox.information(
                self, 
                "Usuario Creado", 
                f"Usuario '{user_data['nombre']}' creado exitosamente.\n\n"
                f"Archivo: {os.path.basename(siev_path)}"
            )
            
            print(f"Nuevo usuario creado: {user_data['nombre']}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error creando usuario: {e}")

    def update_ui_for_user(self, user_data):
        """Actualizar interfaz con información del usuario actual"""
        try:
            # Actualizar título de ventana
            user_name = user_data.get('nombre', 'Usuario')
            self.setWindowTitle(f"Sistema VNG - {user_name}")
            
            # Actualizar header del tree widget
            self.update_tree_header(user_data)
            
            # Habilitar funciones que requieren usuario
            self.enable_test_functions(True)
            
        except Exception as e:
            print(f"Error actualizando UI para usuario: {e}")


    def update_tree_header(self, user_data):
        """Actualizar header del QTreeWidget con información del usuario"""
        try:
            if hasattr(self.ui, 'listTestWidget'):
                user_name = user_data.get('nombre', 'Usuario')
                user_id = user_data.get('rut_id', '')
                
                if user_id:
                    header_text = f"{user_name} ({user_id})"
                else:
                    header_text = user_name
                
                self.ui.listTestWidget.setHeaderLabel(header_text)
                print(f"Header del tree actualizado: {header_text}")
            
        except Exception as e:
            print(f"Error actualizando header del tree: {e}")

    def enable_test_functions(self, enabled):
        """Habilitar/deshabilitar funciones que requieren usuario"""
        try:


            # Habilitar botón de iniciar
            #self.ui.btn_start.setEnabled(enabled)
            
            # Habilitar menús de pruebas CALÓRICAS
            if hasattr(self.ui, 'actionOD_44'):
                self.ui.actionOD_44.setEnabled(enabled)
            if hasattr(self.ui, 'actionOI_44'):
                self.ui.actionOI_44.setEnabled(enabled)
            if hasattr(self.ui, 'actionOD_30'):
                self.ui.actionOD_30.setEnabled(enabled)
            if hasattr(self.ui, 'actionOI_30'):
                self.ui.actionOI_30.setEnabled(enabled)
            
            # AGREGAR ESTAS LÍNEAS para habilitar pruebas OCULOMOTORAS:
            if hasattr(self.ui, 'actionEspont_neo'):
                self.ui.actionEspont_neo.setEnabled(enabled)
            if hasattr(self.ui, 'actionSeguimiento_Lento'):
                self.ui.actionSeguimiento_Lento.setEnabled(enabled)
            if hasattr(self.ui, 'actionOptoquinetico'):
                self.ui.actionOptoquinetico.setEnabled(enabled)
            if hasattr(self.ui, 'actionSacadas'):
                self.ui.actionSacadas.setEnabled(enabled)
            
        except Exception as e:
            print(f"Error habilitando funciones de prueba: {e}")


    def load_user_tests(self):
        """Cargar y mostrar las pruebas del usuario actual en el QTreeWidget"""
        try:
            if not self.current_user_siev or not self.siev_manager:
                return
            
            # Limpiar tree
            self.ui.listTestWidget.clear()
            
            # Obtener lista de pruebas
            tests = self.siev_manager.get_user_tests(self.current_user_siev)
            
            if not tests:
                print("No hay pruebas para cargar")
                return
            
            # Organizar pruebas por fecha
            tests_by_date = {}
            for test in tests:
                try:
                    # Convertir timestamp a fecha
                    test_date = datetime.fromtimestamp(test.get('fecha', 0))
                    date_str = test_date.strftime("%d/%m/%Y")
                    
                    if date_str not in tests_by_date:
                        tests_by_date[date_str] = []
                    
                    tests_by_date[date_str].append(test)
                    
                except Exception as e:
                    print(f"Error procesando prueba: {e}")
                    continue
            
            # Crear estructura en el tree
            for date_str in sorted(tests_by_date.keys(), reverse=True):  # Más reciente primero
                # Crear item de fecha
                date_item = QTreeWidgetItem(self.ui.listTestWidget)
                date_item.setText(0, date_str)
                
                # Estilo para fecha
                font = date_item.font(0)
                font.setBold(True)
                date_item.setFont(0, font)
                
                # Agregar pruebas de esta fecha
                for test in tests_by_date[date_str]:
                    try:
                        test_date = datetime.fromtimestamp(test.get('fecha', 0))
                        time_str = test_date.strftime("%H:%M")
                        
                        test_name = test.get('tipo', 'Desconocido')
                        evaluator = test.get('evaluador', 'Sin evaluador')
                        estado = test.get('estado', 'completada').upper()
                        
                        test_text = f"{test_name} - {time_str} ({evaluator}) [{estado}]"
                        test_item = QTreeWidgetItem(date_item)
                        test_item.setText(0, test_text)
                        
                        # Guardar datos para referencia
                        test_item.setData(0, Qt.UserRole, {
                            'test_id': test.get('id'),
                            'test_data': test
                        })
                        
                    except Exception as e:
                        print(f"Error creando item de prueba: {e}")
                        continue
                
                # Expandir fecha si tiene pocas pruebas
                if len(tests_by_date[date_str]) <= 3:
                    date_item.setExpanded(True)
            
            print(f"Cargadas {len(tests)} pruebas del usuario organizadas por fecha")
            
        except Exception as e:
            print(f"Error cargando pruebas del usuario: {e}")




    def toggle_fullscreen(self):
        """Alternar ventana fullscreen"""
        if self.fullscreen_widget is None:
            self.open_fullscreen()
        else:
            self.close_fullscreen()

    def open_fullscreen(self):
        """Abrir ventana fullscreen"""
        try:
            if self.video_widget is None:
                print("No hay video disponible para fullscreen")
                return
            
            # Crear ventana fullscreen
            self.fullscreen_widget = VideoFullscreenWidget(self.video_widget)
            
            # Conectar señal de video del video_widget
            if hasattr(self.video_widget, 'sig_frame'):
                self.video_widget.sig_frame.connect(self.fullscreen_widget.update_video_frame)
            
            # Sincronizar tiempo inicial
            current_time = self.ui.lbl_time.text()
            self.fullscreen_widget.update_time_display(current_time)
            
            # Cambiar texto del botón
            self.ui.btn_FullScreen.setText("Cerrar FullScreen")
            
            print("Ventana fullscreen abierta")
            
        except Exception as e:
            print(f"Error abriendo fullscreen: {e}")

    def close_fullscreen(self):
        """Cerrar ventana fullscreen"""
        try:
            if self.fullscreen_widget:
                # Desconectar señales
                if hasattr(self.video_widget, 'sig_frame'):
                    try:
                        self.video_widget.sig_frame.disconnect(self.fullscreen_widget.update_video_frame)
                    except:
                        pass
                
                # Cerrar ventana
                self.fullscreen_widget.close()
                self.fullscreen_widget = None
                
                # Restaurar texto del botón
                self.ui.btn_FullScreen.setText("FullScreen")
                
                print("Ventana fullscreen cerrada")
                
        except Exception as e:
            print(f"Error cerrando fullscreen: {e}")

    def update_fullscreen_time(self):
        """Actualizar tiempo en ventana fullscreen (llamar desde update_recording_time)"""
        if self.fullscreen_widget:
            current_time = self.ui.lbl_time.text()
            self.fullscreen_widget.update_time_display(current_time)

    def enable_fullscreen_button(self):
        """Habilitar botón fullscreen cuando hay video"""
        self.ui.btn_FullScreen.setEnabled(True)

    def disable_fullscreen_button(self):
        """Deshabilitar botón fullscreen"""
        self.ui.btn_FullScreen.setEnabled(False)
        if self.fullscreen_widget:
            self.close_fullscreen()


    def keyPressEvent(self, event):
        """Manejar teclas de acceso rápido"""
        try:
            # Controles de video cuando está en modo player
            if (hasattr(self.video_widget, 'is_in_player_mode') and 
                self.video_widget.is_in_player_mode):
                
                if event.key() == Qt.Key_Space:
                    # Barra espaciadora = play/pause
                    self.video_widget.toggle_playback()
                    event.accept()
                    return
                elif event.key() == Qt.Key_Left:
                    # Flecha izquierda = retroceder 1 segundo
                    if self.video_widget.video_player_thread:
                        current_time = self.video_widget.video_player_thread.get_current_time()
                        new_time = max(0, current_time - 1.0)
                        self.video_widget.video_player_thread.seek_to_time(new_time)
                    event.accept()
                    return
                elif event.key() == Qt.Key_Right:
                    # Flecha derecha = avanzar 1 segundo
                    if self.video_widget.video_player_thread:
                        current_time = self.video_widget.video_player_thread.get_current_time()
                        max_time = self.video_widget.video_player_thread.get_duration()
                        new_time = min(max_time, current_time + 1.0)
                        self.video_widget.video_player_thread.seek_to_time(new_time)
                    event.accept()
                    return
            
            # Llamar al método padre para otros eventos
            super().keyPressEvent(event)
            
        except Exception as e:
            print(f"Error en keyPressEvent: {e}")
            super().keyPressEvent(event)
            


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
            
            
            if self.fullscreen_widget:
                self.close_fullscreen()
                
                
            print("Aplicación cerrada correctamente")
        except Exception as e:
            print(f"Error durante cierre: {e}")
        
        super().closeEvent(event)