#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Protocol Config Dialog - Ventana de configuración avanzada de protocolos
Editor completo con formularios, validación y preview en tiempo real
"""

import json
import copy
from typing import Dict, Any, List, Optional, Tuple
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
                              QWidget, QLabel, QLineEdit, QSpinBox, QDoubleSpinBox,
                              QComboBox, QCheckBox, QPushButton, QTextEdit,
                              QGroupBox, QFormLayout, QScrollArea, QFrame,
                              QTableWidget, QTableWidgetItem, QHeaderView,
                              QMessageBox, QSplitter, QTreeWidget, QTreeWidgetItem)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QIcon, QPixmap, QTextCharFormat, QSyntaxHighlighter
from utils.icon_utils import get_icon, IconColors
from utils.dialog_utils import show_error, show_warning, ask_confirmation


class JSONHighlighter(QSyntaxHighlighter):
    """Syntax highlighter para JSON"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_highlighting_rules()
    
    def setup_highlighting_rules(self):
        """Configurar reglas de highlighting"""
        # Formato para strings
        string_format = QTextCharFormat()
        string_format.setForeground(Qt.darkGreen)
        
        # Formato para números
        number_format = QTextCharFormat()
        number_format.setForeground(Qt.darkBlue)
        
        # Formato para keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(Qt.darkMagenta)
        keyword_format.setFontWeight(QFont.Bold)
        
        self.highlighting_rules = [
            # Strings
            (r'"[^"]*"', string_format),
            # Numbers
            (r'\b\d+\.?\d*\b', number_format),
            # Keywords
            (r'\b(true|false|null)\b', keyword_format),
        ]
    
    def highlightBlock(self, text):
        """Aplicar highlighting al bloque de texto"""
        import re
        for pattern, format in self.highlighting_rules:
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), format)


class EventsTableWidget(QWidget):
    """Widget para editar eventos temporales de protocolos calóricos"""
    
    events_changed = Signal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.events = []
        self.setup_ui()
    
    def setup_ui(self):
        """Configurar interfaz"""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Eventos Temporales")
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Botón agregar
        self.btn_add_event = QPushButton("Agregar Evento")
        self.btn_add_event.setIcon(get_icon("plus", 16, IconColors.GREEN))
        self.btn_add_event.clicked.connect(self.add_event)
        header_layout.addWidget(self.btn_add_event)
        
        layout.addLayout(header_layout)
        
        # Tabla de eventos
        self.events_table = QTableWidget()
        self.events_table.setColumnCount(5)
        self.events_table.setHorizontalHeaderLabels([
            "Tiempo (s)", "Tipo", "Descripción", "Acción", "Eliminar"
        ])
        
        # Configurar tabla
        header = self.events_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        
        self.events_table.setColumnWidth(0, 80)
        self.events_table.setColumnWidth(1, 120)
        self.events_table.setColumnWidth(3, 150)
        self.events_table.setColumnWidth(4, 80)
        
        layout.addWidget(self.events_table)
    
    def set_events(self, events: List[Dict[str, Any]]):
        """Establecer eventos en la tabla"""
        self.events = events.copy()
        self.refresh_table()
    
    def get_events(self) -> List[Dict[str, Any]]:
        """Obtener eventos de la tabla"""
        return self.events.copy()
    
    def add_event(self):
        """Agregar nuevo evento"""
        new_event = {
            "time": 0,
            "type": "custom",
            "description": "Nuevo evento",
            "action": "led_on",
            "led_target": "LEFT",
            "duration": 10
        }
        self.events.append(new_event)
        self.refresh_table()
        self.events_changed.emit(self.events)
    
    def remove_event(self, index: int):
        """Eliminar evento por índice"""
        if 0 <= index < len(self.events):
            self.events.pop(index)
            self.refresh_table()
            self.events_changed.emit(self.events)
    
    def refresh_table(self):
        """Refrescar tabla con eventos actuales"""
        self.events_table.setRowCount(len(self.events))
        
        for i, event in enumerate(self.events):
            # Tiempo
            time_spin = QSpinBox()
            time_spin.setRange(0, 600)
            time_spin.setValue(event.get("time", 0))
            time_spin.valueChanged.connect(lambda v, idx=i: self.update_event_time(idx, v))
            self.events_table.setCellWidget(i, 0, time_spin)
            
            # Tipo
            type_combo = QComboBox()
            type_combo.addItems(["torok_start", "fixation_start", "fixation_end", "custom"])
            type_combo.setCurrentText(event.get("type", "custom"))
            type_combo.currentTextChanged.connect(lambda v, idx=i: self.update_event_type(idx, v))
            self.events_table.setCellWidget(i, 1, type_combo)
            
            # Descripción
            desc_item = QTableWidgetItem(event.get("description", ""))
            self.events_table.setItem(i, 2, desc_item)
            
            # Acción
            action_combo = QComboBox()
            action_combo.addItems([
                "activate_torok_tool", "led_on", "led_off", 
                "deactivate_torok_tool", "custom"
            ])
            action_combo.setCurrentText(event.get("action", "led_on"))
            action_combo.currentTextChanged.connect(lambda v, idx=i: self.update_event_action(idx, v))
            self.events_table.setCellWidget(i, 3, action_combo)
            
            # Botón eliminar
            btn_delete = QPushButton("Eliminar")
            btn_delete.setIcon(get_icon("trash-2", 14, IconColors.RED))
            btn_delete.clicked.connect(lambda checked, idx=i: self.remove_event(idx))
            self.events_table.setCellWidget(i, 4, btn_delete)
        
        # Conectar cambios en descripción
        self.events_table.itemChanged.connect(self.on_item_changed)
    
    def update_event_time(self, index: int, value: int):
        """Actualizar tiempo de evento"""
        if 0 <= index < len(self.events):
            self.events[index]["time"] = value
            self.events_changed.emit(self.events)
    
    def update_event_type(self, index: int, value: str):
        """Actualizar tipo de evento"""
        if 0 <= index < len(self.events):
            self.events[index]["type"] = value
            self.events_changed.emit(self.events)
    
    def update_event_action(self, index: int, value: str):
        """Actualizar acción de evento"""
        if 0 <= index < len(self.events):
            self.events[index]["action"] = value
            self.events_changed.emit(self.events)
    
    def on_item_changed(self, item):
        """Manejar cambio en item de tabla"""
        if item.column() == 2:  # Descripción
            row = item.row()
            if 0 <= row < len(self.events):
                self.events[row]["description"] = item.text()
                self.events_changed.emit(self.events)


class ProtocolConfigDialog(QDialog):
    """
    Ventana de configuración avanzada para protocolos vestibulares.
    Editor completo con formularios, validación y preview.
    """
    
    protocol_saved = Signal(str, dict)  # protocol_key, protocol_data
    
    def __init__(self, protocol_key: str, protocol_data: Dict[str, Any], 
                 validation_schema: Dict[str, Any], parent=None):
        super().__init__(parent)
        
        self.original_protocol_key = protocol_key
        self.original_protocol_data = protocol_data.copy()
        self.current_protocol_data = protocol_data.copy()
        self.validation_schema = validation_schema
        self.is_modified = False
        
        # Configurar ventana
        self.setWindowTitle(f"Configurar Protocolo: {protocol_data.get('name', 'Sin nombre')}")
        self.setMinimumSize(900, 700)
        self.setModal(True)
        
        # Setup UI
        self.setup_ui()
        self.load_protocol_data()
        self.setup_connections()
        
        print(f"✅ ProtocolConfigDialog abierto para: {protocol_key}")
    
    def setup_ui(self):
        """Configurar interfaz de usuario"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        self.create_header(main_layout)
        
        # Splitter principal
        splitter = QSplitter(Qt.Horizontal)
        
        # Panel izquierdo - Formularios
        self.create_forms_panel(splitter)
        
        # Panel derecho - Preview JSON
        self.create_preview_panel(splitter)
        
        # Configurar splitter
        splitter.setSizes([600, 300])
        main_layout.addWidget(splitter)
        
        # Botones
        self.create_buttons(main_layout)
    
    def create_header(self, parent_layout):
        """Crear header con información del protocolo"""
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.Box)
        header_layout = QHBoxLayout(header_frame)
        
        # Icono
        icon_label = QLabel()
        icon_label.setFixedSize(48, 48)
        
        behavior_type = self.current_protocol_data.get("behavior_type", "recording")
        if behavior_type == "caloric":
            icon = get_icon("thermometer", 48, IconColors.RED)
        elif behavior_type == "window":
            icon = get_icon("monitor", 48, IconColors.BLUE)
        else:
            icon = get_icon("eye", 48, IconColors.GREEN)
        
        pixmap = icon.pixmap(48, 48)
        icon_label.setPixmap(pixmap)
        header_layout.addWidget(icon_label)
        
        # Información
        info_layout = QVBoxLayout()
        
        self.title_label = QLabel(self.current_protocol_data.get("name", "Sin nombre"))
        self.title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        info_layout.addWidget(self.title_label)
        
        self.info_label = QLabel(
            f"Tipo: {behavior_type} | "
            f"Categoría: {self.current_protocol_data.get('category', 'N/A')}"
        )
        self.info_label.setStyleSheet("color: #7f8c8d;")
        info_layout.addWidget(self.info_label)
        
        header_layout.addLayout(info_layout, 1)
        
        # Estado de modificación
        self.modified_label = QLabel("")
        self.modified_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        header_layout.addWidget(self.modified_label)
        
        parent_layout.addWidget(header_frame)
    
    def create_forms_panel(self, parent_splitter):
        """Crear panel de formularios con tabs"""
        # Scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumWidth(600)
        
        # Widget contenedor
        forms_widget = QWidget()
        scroll_area.setWidget(forms_widget)
        
        # Tab widget
        self.tab_widget = QTabWidget(forms_widget)
        
        # Tabs
        self.create_basic_tab()
        self.create_protocol_tab()
        self.create_ui_tab()
        self.create_hardware_tab()
        self.create_events_tab()
        
        # Layout del widget contenedor
        forms_layout = QVBoxLayout(forms_widget)
        forms_layout.addWidget(self.tab_widget)
        
        parent_splitter.addWidget(scroll_area)
    
    def create_basic_tab(self):
        """Crear tab de configuración básica"""
        tab = QWidget()
        layout = QFormLayout(tab)
        
        # Nombre
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Nombre del protocolo")
        layout.addRow("Nombre:", self.name_edit)
        
        # Descripción
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        self.description_edit.setPlaceholderText("Descripción del protocolo")
        layout.addRow("Descripción:", self.description_edit)
        
        # Categoría
        self.category_combo = QComboBox()
        self.category_combo.addItems(self.validation_schema.get("categories", []))
        layout.addRow("Categoría:", self.category_combo)
        
        # Behavior Type
        self.behavior_type_combo = QComboBox()
        self.behavior_type_combo.addItems(self.validation_schema.get("behavior_types", []))
        layout.addRow("Tipo de Comportamiento:", self.behavior_type_combo)
        
        # Duración máxima
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(0, 600)
        self.duration_spin.setSpecialValueText("Sin límite")
        self.duration_spin.setSuffix(" segundos")
        layout.addRow("Duración Máxima:", self.duration_spin)
        
        self.tab_widget.addTab(tab, "General")
    
    def create_protocol_tab(self):
        """Crear tab de configuración específica del protocolo"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Grupo para configuraciones específicas
        protocol_group = QGroupBox("Configuración del Protocolo")
        protocol_layout = QFormLayout(protocol_group)
        
        # Campos específicos según behavior_type
        # Temperatura (para calóricos)
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(20, 50)
        self.temperature_spin.setDecimals(1)
        self.temperature_spin.setSuffix(" °C")
        protocol_layout.addRow("Temperatura:", self.temperature_spin)
        
        # Oído objetivo
        self.ear_combo = QComboBox()
        self.ear_combo.addItems(["left", "right"])
        protocol_layout.addRow("Oído:", self.ear_combo)
        
        # Amplitud (para oculomotoras)
        self.amplitude_spin = QSpinBox()
        self.amplitude_spin.setRange(1, 90)
        self.amplitude_spin.setSuffix(" °")
        protocol_layout.addRow("Amplitud:", self.amplitude_spin)
        
        # Frecuencia
        self.frequency_spin = QDoubleSpinBox()
        self.frequency_spin.setRange(0.1, 10.0)
        self.frequency_spin.setDecimals(2)
        self.frequency_spin.setSuffix(" Hz")
        protocol_layout.addRow("Frecuencia:", self.frequency_spin)
        
        layout.addWidget(protocol_group)
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "Protocolo")
    
    def create_ui_tab(self):
        """Crear tab de configuración de UI"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Grupo de configuración de cámara
        camera_group = QGroupBox("Configuración de Cámara")
        camera_layout = QVBoxLayout(camera_group)
        
        self.show_crosshair_check = QCheckBox("Mostrar cruz central")
        camera_layout.addWidget(self.show_crosshair_check)
        
        self.show_tracking_check = QCheckBox("Mostrar círculos de tracking")
        camera_layout.addWidget(self.show_tracking_check)
        
        self.show_eye_detection_check = QCheckBox("Mostrar detección de ojos")
        camera_layout.addWidget(self.show_eye_detection_check)
        
        self.show_pupil_detection_check = QCheckBox("Mostrar detección de pupilas")
        camera_layout.addWidget(self.show_pupil_detection_check)
        
        layout.addWidget(camera_group)
        
        # Grupo de herramientas de gráfico
        graph_group = QGroupBox("Herramientas de Gráfico")
        graph_layout = QVBoxLayout(graph_group)
        
        self.torok_tool_check = QCheckBox("Herramienta Torok")
        graph_layout.addWidget(self.torok_tool_check)
        
        self.peak_editing_check = QCheckBox("Edición de picos")
        graph_layout.addWidget(self.peak_editing_check)
        
        self.tiempo_fijacion_check = QCheckBox("Tiempo de fijación")
        graph_layout.addWidget(self.tiempo_fijacion_check)
        
        self.zoom_check = QCheckBox("Zoom")
        graph_layout.addWidget(self.zoom_check)
        
        self.crosshair_graph_check = QCheckBox("Cursor cruz")
        graph_layout.addWidget(self.crosshair_graph_check)
        
        self.peak_detection_check = QCheckBox("Detección automática de picos")
        graph_layout.addWidget(self.peak_detection_check)
        
        layout.addWidget(graph_group)
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "Interfaz")
    
    def create_hardware_tab(self):
        """Crear tab de configuración de hardware"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Control de LED
        led_group = QGroupBox("Control de LED")
        led_layout = QFormLayout(led_group)
        
        self.led_control_check = QCheckBox("Habilitar control de LED")
        led_layout.addRow(self.led_control_check)
        
        self.default_led_combo = QComboBox()
        self.default_led_combo.addItems(["LEFT", "RIGHT"])
        led_layout.addRow("LED por defecto:", self.default_led_combo)
        
        layout.addWidget(led_group)
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "Hardware")
    
    def create_events_tab(self):
        """Crear tab de eventos temporales"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Widget de eventos
        self.events_widget = EventsTableWidget()
        layout.addWidget(self.events_widget)
        
        self.tab_widget.addTab(tab, "Eventos")
    
    def create_preview_panel(self, parent_splitter):
        """Crear panel de preview JSON"""
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        
        # Header del preview
        preview_header = QLabel("Preview JSON")
        preview_header.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        preview_layout.addWidget(preview_header)
        
        # Editor JSON
        self.json_preview = QTextEdit()
        self.json_preview.setReadOnly(True)
        self.json_preview.setFont(QFont("Consolas", 10))
        
        # Syntax highlighter
        self.highlighter = JSONHighlighter(self.json_preview.document())
        
        preview_layout.addWidget(self.json_preview)
        
        parent_splitter.addWidget(preview_widget)
    
    def create_buttons(self, parent_layout):
        """Crear botones de acción"""
        button_layout = QHBoxLayout()
        
        # Botón restaurar
        self.btn_restore = QPushButton("Restaurar Original")
        self.btn_restore.setIcon(get_icon("rotate-ccw", 16, IconColors.ORANGE))
        self.btn_restore.clicked.connect(self.restore_original)
        button_layout.addWidget(self.btn_restore)
        
        # Botón validar
        self.btn_validate = QPushButton("Validar")
        self.btn_validate.setIcon(get_icon("check-circle", 16, IconColors.BLUE))
        self.btn_validate.clicked.connect(self.validate_protocol)
        button_layout.addWidget(self.btn_validate)
        
        button_layout.addStretch()
        
        # Botón cancelar
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setIcon(get_icon("x", 16, IconColors.GRAY))
        self.btn_cancel.clicked.connect(self.reject)
        button_layout.addWidget(self.btn_cancel)
        
        # Botón guardar
        self.btn_save = QPushButton("Guardar Cambios")
        self.btn_save.setIcon(get_icon("save", 16, IconColors.GREEN))
        self.btn_save.clicked.connect(self.save_protocol)
        button_layout.addWidget(self.btn_save)
        
        parent_layout.addLayout(button_layout)
    
    def setup_connections(self):
        """Configurar conexiones de señales"""
        # Conexiones para detectar cambios
        self.name_edit.textChanged.connect(self.on_data_changed)
        self.description_edit.textChanged.connect(self.on_data_changed)
        self.category_combo.currentTextChanged.connect(self.on_data_changed)
        self.behavior_type_combo.currentTextChanged.connect(self.on_data_changed)
        self.duration_spin.valueChanged.connect(self.on_data_changed)
        
        # Protocolo específico
        self.temperature_spin.valueChanged.connect(self.on_data_changed)
        self.ear_combo.currentTextChanged.connect(self.on_data_changed)
        self.amplitude_spin.valueChanged.connect(self.on_data_changed)
        self.frequency_spin.valueChanged.connect(self.on_data_changed)
        
        # UI
        self.show_crosshair_check.toggled.connect(self.on_data_changed)
        self.show_tracking_check.toggled.connect(self.on_data_changed)
        self.show_eye_detection_check.toggled.connect(self.on_data_changed)
        self.show_pupil_detection_check.toggled.connect(self.on_data_changed)
        
        # Gráfico
        self.torok_tool_check.toggled.connect(self.on_data_changed)
        self.peak_editing_check.toggled.connect(self.on_data_changed)
        self.tiempo_fijacion_check.toggled.connect(self.on_data_changed)
        self.zoom_check.toggled.connect(self.on_data_changed)
        self.crosshair_graph_check.toggled.connect(self.on_data_changed)
        self.peak_detection_check.toggled.connect(self.on_data_changed)
        
        # Hardware
        self.led_control_check.toggled.connect(self.on_data_changed)
        self.default_led_combo.currentTextChanged.connect(self.on_data_changed)
        
        # Eventos
        self.events_widget.events_changed.connect(self.on_events_changed)
        
        # Timer para actualizar preview
        self.preview_timer = QTimer()
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self.update_preview)
        
        # Behavior type change para mostrar/ocultar campos
        self.behavior_type_combo.currentTextChanged.connect(self.on_behavior_type_changed)
    
    def load_protocol_data(self):
        """Cargar datos del protocolo en los formularios"""
        # General
        self.name_edit.setText(self.current_protocol_data.get("name", ""))
        self.description_edit.setPlainText(self.current_protocol_data.get("description", ""))
        
        category = self.current_protocol_data.get("category", "")
        if category:
            index = self.category_combo.findText(category)
            if index >= 0:
                self.category_combo.setCurrentIndex(index)
        
        behavior_type = self.current_protocol_data.get("behavior_type", "recording")
        index = self.behavior_type_combo.findText(behavior_type)
        if index >= 0:
            self.behavior_type_combo.setCurrentIndex(index)
        
        duration_max = self.current_protocol_data.get("duration_max")
        if duration_max:
            self.duration_spin.setValue(duration_max)
        else:
            self.duration_spin.setValue(0)
        
        # Protocolo específico
        protocol_config = self.current_protocol_data.get("protocol", {})
        self.temperature_spin.setValue(protocol_config.get("temperature", 37.0))
        
        ear = protocol_config.get("ear", "left")
        index = self.ear_combo.findText(ear)
        if index >= 0:
            self.ear_combo.setCurrentIndex(index)
        
        self.amplitude_spin.setValue(protocol_config.get("target_amplitude", 20))
        self.frequency_spin.setValue(protocol_config.get("frequency", 0.4))
        
        # UI Settings
        ui_settings = self.current_protocol_data.get("ui_settings", {})
        self.show_crosshair_check.setChecked(ui_settings.get("show_crosshair", True))
        self.show_tracking_check.setChecked(ui_settings.get("show_tracking_circles", True))
        self.show_eye_detection_check.setChecked(ui_settings.get("show_eye_detection", True))
        self.show_pupil_detection_check.setChecked(ui_settings.get("show_pupil_detection", True))
        
        # Graph Tools
        graph_tools = self.current_protocol_data.get("graph_tools", {})
        self.torok_tool_check.setChecked(graph_tools.get("torok_tool", False))
        self.peak_editing_check.setChecked(graph_tools.get("peak_editing", True))
        self.tiempo_fijacion_check.setChecked(graph_tools.get("tiempo_fijacion", False))
        self.zoom_check.setChecked(graph_tools.get("zoom", True))
        self.crosshair_graph_check.setChecked(graph_tools.get("crosshair", True))
        self.peak_detection_check.setChecked(graph_tools.get("peak_detection", False))
        
        # Hardware
        hardware_control = self.current_protocol_data.get("hardware_control", {})
        self.led_control_check.setChecked(hardware_control.get("led_control", False))
        
        default_led = hardware_control.get("default_led", "LEFT")
        index = self.default_led_combo.findText(default_led)
        if index >= 0:
            self.default_led_combo.setCurrentIndex(index)
        
        # Eventos
        events = protocol_config.get("events", [])
        self.events_widget.set_events(events)
        
        # Actualizar visibilidad según behavior type
        self.on_behavior_type_changed(behavior_type)
        
        # Actualizar preview
        self.update_preview()
    
    def on_behavior_type_changed(self, behavior_type: str):
        """Manejar cambio de behavior type"""
        # Mostrar/ocultar tabs según el tipo
        events_tab_index = self.tab_widget.indexOf(self.tab_widget.widget(4))  # Tab de eventos
        
        if behavior_type == "caloric":
            # Mostrar tab de eventos
            if events_tab_index == -1:
                self.tab_widget.addTab(self.events_widget.parent(), "Eventos")
        else:
            # Ocultar tab de eventos
            if events_tab_index >= 0:
                self.tab_widget.removeTab(events_tab_index)
        
        # Configurar visibilidad de campos en tab de protocolo
        # (Se podría expandir para mostrar campos específicos según el tipo)
    
    def on_data_changed(self):
        """Manejar cambio en los datos"""
        self.is_modified = True
        self.modified_label.setText("● Modificado")
        
        # Programar actualización de preview
        self.preview_timer.start(300)
    
    def on_events_changed(self, events: List[Dict[str, Any]]):
        """Manejar cambio en eventos"""
        self.on_data_changed()
    
    def update_preview(self):
        """Actualizar preview JSON"""
        try:
            # Construir protocolo desde formularios
            updated_protocol = self.build_protocol_from_forms()
            
            # Convertir a JSON con formato bonito
            json_text = json.dumps(updated_protocol, indent=2, ensure_ascii=False)
            
            # Actualizar preview
            self.json_preview.setPlainText(json_text)
            
        except Exception as e:
            self.json_preview.setPlainText(f"Error generando preview: {e}")
    
    def build_protocol_from_forms(self) -> Dict[str, Any]:
        """Construir protocolo desde los datos de los formularios"""
        protocol = self.current_protocol_data.copy()
        
        # General
        protocol["name"] = self.name_edit.text().strip()
        protocol["description"] = self.description_edit.toPlainText().strip()
        protocol["category"] = self.category_combo.currentText()
        protocol["behavior_type"] = self.behavior_type_combo.currentText()
        
        duration = self.duration_spin.value()
        protocol["duration_max"] = duration if duration > 0 else None
        
        # Protocolo específico
        if "protocol" not in protocol:
            protocol["protocol"] = {}
        
        protocol["protocol"]["temperature"] = self.temperature_spin.value()
        protocol["protocol"]["ear"] = self.ear_combo.currentText()
        protocol["protocol"]["target_amplitude"] = self.amplitude_spin.value()
        protocol["protocol"]["frequency"] = self.frequency_spin.value()
        
        # Eventos
        events = self.events_widget.get_events()
        if events:
            protocol["protocol"]["events"] = events
        
        # UI Settings
        protocol["ui_settings"] = {
            "show_crosshair": self.show_crosshair_check.isChecked(),
            "show_tracking_circles": self.show_tracking_check.isChecked(),
            "show_eye_detection": self.show_eye_detection_check.isChecked(),
            "show_pupil_detection": self.show_pupil_detection_check.isChecked()
        }
        
        # Graph Tools
        protocol["graph_tools"] = {
            "torok_tool": self.torok_tool_check.isChecked(),
            "peak_editing": self.peak_editing_check.isChecked(),
            "tiempo_fijacion": self.tiempo_fijacion_check.isChecked(),
            "zoom": self.zoom_check.isChecked(),
            "crosshair": self.crosshair_graph_check.isChecked(),
            "peak_detection": self.peak_detection_check.isChecked()
        }
        
        # Hardware Control
        protocol["hardware_control"] = {
            "led_control": self.led_control_check.isChecked(),
            "default_led": self.default_led_combo.currentText(),
            "esp8266_commands": [
                f"LED_ON:{self.default_led_combo.currentText()}",
                f"LED_OFF:{self.default_led_combo.currentText()}"
            ] if self.led_control_check.isChecked() else []
        }
        
        return protocol
    
    def validate_protocol(self):
        """Validar protocolo actual"""
        try:
            protocol = self.build_protocol_from_forms()
            
            # Validación básica
            errors = []
            
            # Campos requeridos
            if not protocol.get("name", "").strip():
                errors.append("El nombre es requerido")
            
            if not protocol.get("category"):
                errors.append("La categoría es requerida")
            
            if not protocol.get("behavior_type"):
                errors.append("El tipo de comportamiento es requerido")
            
            # Validaciones específicas
            if protocol.get("behavior_type") == "caloric":
                temp = protocol.get("protocol", {}).get("temperature", 0)
                if temp < 20 or temp > 50:
                    errors.append("Temperatura debe estar entre 20°C y 50°C")
            
            # Validar eventos
            events = protocol.get("protocol", {}).get("events", [])
            for i, event in enumerate(events):
                if not event.get("description", "").strip():
                    errors.append(f"Evento {i+1} requiere descripción")
                
                if event.get("time", 0) < 0:
                    errors.append(f"Evento {i+1} debe tener tiempo >= 0")
            
            if errors:
                show_error("Validación Fallida", "\n".join(f"• {error}" for error in errors), self)
                return False
            else:
                show_info("Validación Exitosa", "El protocolo es válido y está listo para guardar.", self)
                return True
                
        except Exception as e:
            show_error("Error de Validación", f"Error validando protocolo: {e}", self)
            return False
    
    def restore_original(self):
        """Restaurar protocolo original"""
        if self.is_modified:
            if ask_confirmation(
                "Restaurar Original", 
                "¿Está seguro de que desea descartar todos los cambios y "
                "restaurar la configuración original?", 
                self
            ):
                self.current_protocol_data = self.original_protocol_data.copy()
                self.load_protocol_data()
                self.is_modified = False
                self.modified_label.setText("")
    
    def save_protocol(self):
        """Guardar protocolo"""
        # Validar primero
        if not self.validate_protocol():
            return
        
        try:
            # Construir protocolo final
            final_protocol = self.build_protocol_from_forms()
            
            # Agregar metadatos de modificación
            if self.is_modified:
                final_protocol["last_modified"] = "2025-07-03"
                final_protocol["modified_by"] = "Usuario"
            
            # Emitir señal
            self.protocol_saved.emit(self.original_protocol_key, final_protocol)
            
            # Cerrar diálogo
            self.accept()
            
        except Exception as e:
            show_error("Error Guardando", f"No se pudo guardar el protocolo: {e}", self)
    
    def closeEvent(self, event):
        """Manejar cierre de ventana"""
        if self.is_modified:
            if ask_confirmation(
                "Cambios Sin Guardar",
                "Hay cambios sin guardar. ¿Está seguro de que desea cerrar sin guardar?",
                self
            ):
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
    
    def reject(self):
        """Override reject para manejar cambios"""
        if self.is_modified:
            if ask_confirmation(
                "Cambios Sin Guardar",
                "Hay cambios sin guardar. ¿Está seguro de que desea cancelar?",
                self
            ):
                super().reject()
        else:
            super().reject()


# Función de conveniencia
def show_protocol_config_dialog(protocol_key: str, protocol_data: Dict[str, Any],
                               validation_schema: Dict[str, Any], parent=None) -> Optional[Dict[str, Any]]:
    """
    Mostrar diálogo de configuración de protocolo.
    
    Args:
        protocol_key: Clave del protocolo
        protocol_data: Datos del protocolo
        validation_schema: Esquema de validación
        parent: Widget padre
        
    Returns:
        Protocolo modificado o None si se canceló
    """
    dialog = ProtocolConfigDialog(protocol_key, protocol_data, validation_schema, parent)
    
    result_protocol = None
    
    def on_protocol_saved(key, data):
        nonlocal result_protocol
        result_protocol = data
    
    dialog.protocol_saved.connect(on_protocol_saved)
    
    if dialog.exec() == QDialog.Accepted:
        return result_protocol
    else:
        return None