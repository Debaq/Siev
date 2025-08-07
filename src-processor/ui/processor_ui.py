#!/usr/bin/env python3
"""
Simple Processor UI
Interfaz de usuario para el procesador simple de videos.
Solo maneja la creación y actualización visual de componentes.
"""

import numpy as np

from PySide6.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QLabel, QSlider, QComboBox,
    QGroupBox, QGridLayout, QMenuBar, QMenu
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QImage

import pyqtgraph as pg
from utils.graphing.caloric_graph import CaloricPlotWidget 


from ui.styles.qt6_dark_styles import Qt6DarkStyles


class SimpleProcessorUI(QMainWindow):
    """
    Interfaz de usuario para el procesador simple.
    Solo maneja elementos visuales, sin lógica de negocio.
    """
    
    # Señales para comunicación con la lógica
    siev_file_requested = Signal()
    video_file_requested = Signal()
    siev_video_requested = Signal()
    test_selected = Signal(str)
    time_slider_changed = Signal(int)
    threshold_changed = Signal(str, object)  # param_name, value
    save_config_toggled = Signal(bool)
    graph_type_changed = Signal(str)
    frame_slider_changed = Signal(int)  # Frame directo en lugar de tiempo

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple Video Processor")
        self.setGeometry(100, 100, 1400, 900)
        
        # Referencias a widgets que necesitan ser actualizados
        self.video_label = None
        self.time_slider = None
        self.time_label = None
        self.switch_save_config = None
        self.combo_tests = None
        self.combo_graph_type = None
        self.btn_load_siev_video = None
        self.siev_group = None
        self.lbl_status = None
        
        # Labels de umbrales
        self.lbl_threshold_right = None
        self.lbl_erode_right = None
        self.lbl_nose_width = None
        self.lbl_eye_height = None
        
        # Labels de configuración
        self.lbl_current_frame = None
        self.lbl_saved_configs = None
        self.lbl_current_config = None
        
        # Componentes de gráfico
        self.graph_container = None
        self.graph_layout = None
        self.simple_plot = None
        self.simple_curve = None
        self.simple_time_line = None
        self.caloric_graph = None
        
        self.setup_menu_bar()
        self.setup_ui()
        self.apply_styles()  # ← Agregar esto



    def apply_styles(self):
            """Aplicar tema oscuro a toda la interfaz"""
            styles = Qt6DarkStyles()
            
            # Estilo principal de ventana
            self.setStyleSheet(f"""
                {styles.get_main_window_style()}
                {styles.get_group_style()}
                {styles.get_combo_style()}
                {styles.get_input_style()}
                {styles.get_small_button_style()}
                {styles.get_status_label_style()}
                {styles.get_slider_style()}
                {styles.get_scroll_bar_style()}
                {styles.get_menu_style()}
                {styles.get_camera_frame_style()}
            """)
            
            # Estilos específicos para botones
            if hasattr(self, 'btn_load_siev_video'):
                self.btn_load_siev_video.setStyleSheet(styles.get_info_button())
                
            if hasattr(self, 'switch_save_config'):
                # Mantener tu estilo custom para el switch ON/OFF
                pass
        
        
    def setup_menu_bar(self):
        """Configurar barra de menú"""
        menubar = self.menuBar()
        
        # Menú Archivo
        file_menu = menubar.addMenu('Archivo')
        
        # Submenu Abrir
        open_menu = file_menu.addMenu('Abrir')
        
        # Acción SIEV
        siev_action = open_menu.addAction('SIEV')
        siev_action.triggered.connect(self.siev_file_requested.emit)
        
        # Acción Video
        video_action = open_menu.addAction('Video')
        video_action.triggered.connect(self.video_file_requested.emit)
        
    def setup_ui(self):
        """Configurar interfaz de usuario"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal vertical
        main_layout = QVBoxLayout(central_widget)
        
        # Panel superior - Video y controles en horizontal
        top_panel = self.create_top_panel()
        main_layout.addWidget(top_panel)
        
        # Panel inferior - Gráfico que usa todo el ancho
        graph_panel = self.create_graph_panel()
        main_layout.addWidget(graph_panel)
        
        # Establecer proporciones: 40% superior, 60% gráfico
        main_layout.setStretchFactor(top_panel, 2)
        main_layout.setStretchFactor(graph_panel, 3)
        
    def create_top_panel(self) -> QWidget:
        """Crear panel superior con video y controles horizontales"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        # Video display (izquierda)
        video_group = QGroupBox("Video")
        video_layout = QVBoxLayout(video_group)
        
        self.video_label = QLabel("No hay video cargado")
        self.video_label.setMinimumSize(400, 300)
        self.video_label.setMaximumSize(500, 400)
        self.video_label.setStyleSheet("border: 1px solid gray;")
        self.video_label.setAlignment(Qt.AlignCenter)
        video_layout.addWidget(self.video_label)
        
        layout.addWidget(video_group)
        
        # Panel de controles (derecha)
        controls_widget = QWidget()
        controls_layout = QVBoxLayout(controls_widget)
        
        # Selector de prueba SIEV (solo visible cuando se carga SIEV)
        self.siev_group = self.create_siev_panel()
        controls_layout.addWidget(self.siev_group)
        
        # Controles de tiempo
        time_group = self.create_time_controls()
        controls_layout.addWidget(time_group)
        
        # Controles de umbrales
        threshold_group = self.create_threshold_controls()
        controls_layout.addWidget(threshold_group)
        
        # Información de configuraciones por frame
        config_info_group = self.create_config_info_panel()
        controls_layout.addWidget(config_info_group)
        
        # Estado
        self.lbl_status = QLabel("Usar menú Archivo → Abrir para cargar video")
        controls_layout.addWidget(self.lbl_status)
        
        controls_layout.addStretch()
        layout.addWidget(controls_widget)
        
        return widget
        
    def create_siev_panel(self) -> QWidget:
        """Crear panel de prueba SIEV"""
        group = QGroupBox("Prueba SIEV")
        layout = QVBoxLayout(group)
        
        # Selector de prueba
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("Prueba:"))
        self.combo_tests = QComboBox()
        self.combo_tests.currentTextChanged.connect(self.test_selected.emit)
        selector_layout.addWidget(self.combo_tests)
        layout.addLayout(selector_layout)
        
        # Botón para cargar video de la prueba SIEV
        self.btn_load_siev_video = QPushButton("Cargar Video de esta Prueba")
        self.btn_load_siev_video.clicked.connect(self.siev_video_requested.emit)
        self.btn_load_siev_video.setEnabled(False)
        layout.addWidget(self.btn_load_siev_video)
        
        group.setVisible(False)  # Oculto por defecto
        return group
        
    def create_time_controls(self) -> QWidget:
        """Crear controles de tiempo con switch de configuración"""
        group = QGroupBox("Control de Tiempo")
        layout = QVBoxLayout(group)
        
        # MODIFICADO: Slider ahora representa frames
        self.time_slider = QSlider(Qt.Horizontal)
        self.time_slider.setMinimum(0)
        self.time_slider.setMaximum(100)  # Se actualizará con total de frames
        self.time_slider.setValue(0)
        self.time_slider.setTickPosition(QSlider.TicksBelow)  # Mostrar ticks
        self.time_slider.setTickInterval(1)  # Un tick por frame
        self.time_slider.setSingleStep(1)  # Moverse de a 1 frame
        self.time_slider.setPageStep(10)  # Page up/down mueve 10 frames
        
        # IMPORTANTE: Conectar a nueva señal de frames
        self.time_slider.valueChanged.connect(self.frame_slider_changed.emit)
        
        layout.addWidget(self.time_slider)
        
        # Layout horizontal para tiempo y switch
        time_info_layout = QHBoxLayout()
        
        # MODIFICADO: Mostrar frame actual además del tiempo
        self.time_label = QLabel("Frame: 0/0 | Tiempo: 0.00s / 0.00s")
        time_info_layout.addWidget(self.time_label)
        
        time_info_layout.addStretch()
        
        # Switch para guardar configuración por frame (sin cambios)
        time_info_layout.addWidget(QLabel("Guardar Config:"))
        self.switch_save_config = QPushButton("OFF")
        self.switch_save_config.setCheckable(True)
        self.switch_save_config.setStyleSheet("""
            QPushButton {
                background-color: #ff4444;
                border: 2px solid #cc3333;
                border-radius: 10px;
                padding: 3px 10px;
                color: white;
                font-weight: bold;
                font-size: 10px;
            }
            QPushButton:checked {
                background-color: #44ff44;
                border: 2px solid #33cc33;
            }
        """)
        self.switch_save_config.clicked.connect(
            lambda checked: self.save_config_toggled.emit(checked)
        )
        time_info_layout.addWidget(self.switch_save_config)
        
        layout.addLayout(time_info_layout)
        
        # NUEVO: Controles adicionales de navegación por frames
        nav_layout = QHBoxLayout()
        
        self.btn_prev_frame = QPushButton("◀ Frame")
        self.btn_prev_frame.clicked.connect(self.prev_frame)
        nav_layout.addWidget(self.btn_prev_frame)
        
        self.btn_next_frame = QPushButton("Frame ▶")
        self.btn_next_frame.clicked.connect(self.next_frame)
        nav_layout.addWidget(self.btn_next_frame)
        
        nav_layout.addStretch()
        
        self.btn_prev_10 = QPushButton("◀◀ -10")
        self.btn_prev_10.clicked.connect(lambda: self.skip_frames(-10))
        nav_layout.addWidget(self.btn_prev_10)
        
        self.btn_next_10 = QPushButton("+10 ▶▶")
        self.btn_next_10.clicked.connect(lambda: self.skip_frames(10))
        nav_layout.addWidget(self.btn_next_10)
        
        layout.addLayout(nav_layout)
        
        return group
    def configure_slider_for_frames(self, total_frames: int):
        """NUEVO: Configurar slider para trabajar con frames"""
        self.time_slider.setMaximum(total_frames - 1)
        self.time_slider.setMinimum(0)
        self.time_slider.setValue(0)
        
        # Para videos largos, ajustar intervalo de ticks
        if total_frames > 1000:
            self.time_slider.setTickInterval(30)  # Un tick cada 30 frames (1 seg a 30fps)
        elif total_frames > 500:
            self.time_slider.setTickInterval(10)
        else:
            self.time_slider.setTickInterval(1)
    
    def update_frame_info(self, current_frame: int, total_frames: int, current_time: float, max_time: float):
        """NUEVO: Actualizar información mostrando frames y tiempo"""
        frame_text = f"Frame: {current_frame}/{total_frames}"
        time_text = f"Tiempo: {current_time:.2f}s / {max_time:.2f}s"
        self.time_label.setText(f"{frame_text} | {time_text}")
    
    def prev_frame(self):
        """NUEVO: Ir al frame anterior"""
        current = self.time_slider.value()
        if current > 0:
            self.time_slider.setValue(current - 1)
    
    def next_frame(self):
        """NUEVO: Ir al siguiente frame"""
        current = self.time_slider.value()
        if current < self.time_slider.maximum():
            self.time_slider.setValue(current + 1)
    
    def skip_frames(self, amount: int):
        """NUEVO: Saltar N frames"""
        current = self.time_slider.value()
        new_value = max(0, min(current + amount, self.time_slider.maximum()))
        self.time_slider.setValue(new_value)
        
    def create_threshold_controls(self) -> QWidget:
        """Crear controles de umbrales"""
        group = QGroupBox("Umbrales de Procesamiento")
        layout = QGridLayout(group)
        
        # Threshold Right (solo ojo derecho)
        layout.addWidget(QLabel("Threshold Right:"), 0, 0)
        slider_threshold_right = QSlider(Qt.Horizontal)
        slider_threshold_right.setMinimum(1)
        slider_threshold_right.setMaximum(255)
        slider_threshold_right.setValue(50)
        slider_threshold_right.valueChanged.connect(
            lambda v: self.threshold_changed.emit('threshold_right', v)
        )
        layout.addWidget(slider_threshold_right, 0, 1)
        self.lbl_threshold_right = QLabel("50")
        layout.addWidget(self.lbl_threshold_right, 0, 2)
        
        # Erode Right
        layout.addWidget(QLabel("Erode Right:"), 1, 0)
        slider_erode_right = QSlider(Qt.Horizontal)
        slider_erode_right.setMinimum(1)
        slider_erode_right.setMaximum(10)
        slider_erode_right.setValue(2)
        slider_erode_right.valueChanged.connect(
            lambda v: self.threshold_changed.emit('erode_right', v)
        )
        layout.addWidget(slider_erode_right, 1, 1)
        self.lbl_erode_right = QLabel("2")
        layout.addWidget(self.lbl_erode_right, 1, 2)
        
        # Nose Width
        layout.addWidget(QLabel("Nose Width:"), 2, 0)
        slider_nose_width = QSlider(Qt.Horizontal)
        slider_nose_width.setMinimum(10)
        slider_nose_width.setMaximum(50)
        slider_nose_width.setValue(25)
        slider_nose_width.valueChanged.connect(
            lambda v: self.threshold_changed.emit('nose_width', v/100.0)
        )
        layout.addWidget(slider_nose_width, 2, 1)
        self.lbl_nose_width = QLabel("0.25")
        layout.addWidget(self.lbl_nose_width, 2, 2)
        
        # Eye Height
        layout.addWidget(QLabel("Eye Height:"), 3, 0)
        slider_eye_height = QSlider(Qt.Horizontal)
        slider_eye_height.setMinimum(20)
        slider_eye_height.setMaximum(80)
        slider_eye_height.setValue(50)
        slider_eye_height.valueChanged.connect(
            lambda v: self.threshold_changed.emit('eye_height', v/100.0)
        )
        layout.addWidget(slider_eye_height, 3, 1)
        self.lbl_eye_height = QLabel("0.50")
        layout.addWidget(self.lbl_eye_height, 3, 2)
        
        return group
        
    def create_config_info_panel(self) -> QWidget:
        """Crear panel de información de configuraciones"""
        group = QGroupBox("Configuraciones por Frame")
        layout = QVBoxLayout(group)
        
        self.lbl_current_frame = QLabel("Frame actual: 0")
        layout.addWidget(self.lbl_current_frame)
        
        self.lbl_saved_configs = QLabel("Configs guardadas: 0")
        layout.addWidget(self.lbl_saved_configs)
        
        self.lbl_current_config = QLabel("Config actual: Global")
        layout.addWidget(self.lbl_current_config)
        
        return group
        
    def create_graph_panel(self) -> QWidget:
        """Crear panel de gráfico que usa todo el ancho"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Selector de tipo de gráfico
        graph_control = QHBoxLayout()
        graph_control.addWidget(QLabel("Tipo de gráfico:"))
        
        self.combo_graph_type = QComboBox()
        self.combo_graph_type.addItems(["Espontáneo (Simple)", "Calórico (Avanzado)"])
        self.combo_graph_type.currentTextChanged.connect(self.graph_type_changed.emit)
        graph_control.addWidget(self.combo_graph_type)
        graph_control.addStretch()
        
        layout.addLayout(graph_control)
        
        # Container para gráficos
        self.graph_container = QWidget()
        self.graph_layout = QVBoxLayout(self.graph_container)
        layout.addWidget(self.graph_container)
        
        # Inicializar con gráfico simple
        self.setup_simple_graph()
        
        return widget
        
    def setup_simple_graph(self):
        """Configurar gráfico simple para espontáneo"""
        self.clear_graph_container()
        
        # Gráfico PyQtGraph simple
        self.simple_plot = pg.PlotWidget(title="Posición Pupila - Ojo Derecho")
        self.simple_plot.setLabel('left', 'Posición X Pupila', units='px')
        self.simple_plot.setLabel('bottom', 'Tiempo', units='s')
        self.simple_plot.showGrid(x=True, y=True)
        
        # Curva de datos
        self.simple_curve = self.simple_plot.plot([], [], pen='b', name='Ojo Derecho')
        
        # Línea de tiempo
        self.simple_time_line = pg.InfiniteLine(
            pos=0, angle=90, pen=pg.mkPen(color='r', width=2),
            movable=True, label="Tiempo"
        )
        self.simple_plot.addItem(self.simple_time_line)
        
        self.graph_layout.addWidget(self.simple_plot)
        
        # INTERFAZ UNIFICADA: establecer referencias actuales
        self.current_graph = self.simple_plot
        self.current_curve = self.simple_curve
        self.current_time_line = self.simple_time_line
        
        print("Gráfico simple configurado")
        
    def setup_caloric_graph(self):
        """Configurar gráfico calórico"""
        self.clear_graph_container()
        
        # Crear gráfico calórico
        self.caloric_graph = CaloricPlotWidget(
            total_duration=60.0,
            parent=self.graph_container
        )
        self.graph_layout.addWidget(self.caloric_graph)
        
        # INTERFAZ UNIFICADA: establecer referencias actuales
        self.current_graph = self.caloric_graph
        self.current_curve = self.caloric_graph.data_curve  # Usar data_curve directamente
        self.current_time_line = self.caloric_graph.simple_time_line
        
        print("Gráfico calórico configurado")
    
            
    def clear_graph_container(self):
        """Limpiar container de gráficos - INTERFAZ UNIFICADA"""
        # Limpiar TODAS las referencias
        self.current_graph = None
        self.current_curve = None
        self.current_time_line = None
        
        # Referencias específicas
        self.simple_curve = None
        self.simple_time_line = None
        self.simple_plot = None
        self.caloric_graph = None
        
        # Eliminar widgets del layout
        while self.graph_layout.count():
            child = self.graph_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        print("Container de gráficos limpiado")
                
    # ========== MÉTODOS DE ACTUALIZACIÓN DE UI ==========
    
    def update_video_display(self, frame):
        """Actualizar display de video"""
        if frame is not None:
            try:
                # Convertir frame a QImage y mostrar
                height, width, channel = frame.shape
                bytes_per_line = 3 * width
                frame_contiguous = np.ascontiguousarray(frame)
                q_image = QImage(frame_contiguous.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()                
                # Escalar para mostrar
                pixmap = QPixmap.fromImage(q_image)
                scaled_pixmap = pixmap.scaled(
                    self.video_label.size(), 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                )
                self.video_label.setPixmap(scaled_pixmap)
            except Exception as e:
                print(f"Error mostrando frame: {e}")
    
    def update_time_label(self, current_time: float, max_time: float):
        """Actualizar label de tiempo"""
        self.time_label.setText(f"Tiempo: {current_time:.2f}s / {max_time:.2f}s")
    
    def update_status(self, message: str):
        """Actualizar mensaje de estado"""
        self.lbl_status.setText(message)
    
    def update_siev_panel(self, test_names: list[str]):
        """Actualizar panel SIEV con lista de pruebas"""
        self.combo_tests.clear()
        if test_names:
            self.combo_tests.addItems(test_names)
            self.siev_group.setVisible(True)
        else:
            self.siev_group.setVisible(False)
    
    def update_save_config_switch(self, enabled: bool):
        """Actualizar estado del switch de configuración"""
        self.switch_save_config.setChecked(enabled)
        self.switch_save_config.setText("ON" if enabled else "OFF")
    
    def enable_siev_video_button(self, enabled: bool):
        """Habilitar/deshabilitar botón de video SIEV"""
        self.btn_load_siev_video.setEnabled(enabled)
    
    def update_threshold_labels(self, param: str, value):
        """Actualizar labels de umbrales"""
        if param == 'threshold_right':
            self.lbl_threshold_right.setText(str(value))
        elif param == 'erode_right':
            self.lbl_erode_right.setText(str(value))
        elif param == 'nose_width':
            self.lbl_nose_width.setText(f"{value:.2f}")
        elif param == 'eye_height':
            self.lbl_eye_height.setText(f"{value:.2f}")
    
    def update_config_labels(self, current_frame: int, total_configs: int, current_config: str):
        """Actualizar labels de información de configuración"""
        self.lbl_current_frame.setText(f"Frame actual: {current_frame}")
        self.lbl_saved_configs.setText(f"Configs guardadas: {total_configs}")
        self.lbl_current_config.setText(f"Config actual: {current_config}")
    
    def update_time_line_position(self, position: float):
        """Actualizar posición de línea de tiempo - INTERFAZ UNIFICADA"""
        if hasattr(self, 'current_time_line') and self.current_time_line:
            try:
                self.current_time_line.setPos(position)
            except RuntimeError as e:
                print(f"Error actualizando línea de tiempo: {e}")
    
    def adjust_graph_to_duration(self, duration: float):
        """Ajustar gráfico al tiempo máximo del video - INTERFAZ UNIFICADA"""
        try:
            if hasattr(self, 'current_graph') and self.current_graph:
                # Para gráfico simple
                if hasattr(self.current_graph, 'setXRange'):
                    self.current_graph.setXRange(0, duration, padding=0.02)
                
                # Para gráfico calórico (tiene método específico)
                if hasattr(self.current_graph, 'adjust_to_duration'):
                    self.current_graph.adjust_to_duration(duration)
            
            print(f"Gráfico ajustado a duración: {duration:.2f}s")
            
        except Exception as e:
            print(f"Error ajustando gráfico a duración: {e}")
    
    def update_graph_data(self, timestamps: list[float], values: list[float]):
        """Actualizar datos del gráfico activo - INTERFAZ UNIFICADA"""
        if hasattr(self, 'current_curve') and self.current_curve:
            try:
                self.current_curve.setData(timestamps, values)
            except RuntimeError as e:
                print(f"Error actualizando gráfico: {e}")
    
    def add_point_to_caloric_graph(self, timestamp: float, value: float):
        """Agregar punto al gráfico calórico"""
        if hasattr(self, 'caloric_graph') and self.caloric_graph:
            try:
                self.caloric_graph.add_data_point(timestamp, value)
            except Exception as e:
                print(f"Error agregando punto a caloric_graph: {e}")
    
    def switch_to_simple_graph(self):
        """Cambiar a gráfico simple"""
        self.setup_simple_graph()
    
    def switch_to_caloric_graph(self):
        """Cambiar a gráfico calórico"""
        self.setup_caloric_graph()