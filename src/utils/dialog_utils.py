#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dialog Utils - Ventanas emergentes reutilizables y consistentes para SIEV
Incluye confirmaciones, inputs, alertas e información con iconos SVG
"""

from typing import Optional, List, Dict, Any, Tuple
from PySide6.QtWidgets import (QMessageBox, QInputDialog, QDialog, QVBoxLayout, 
                              QHBoxLayout, QPushButton, QLabel, QLineEdit,
                              QTextEdit, QCheckBox, QComboBox, QSpinBox,
                              QDoubleSpinBox, QDialogButtonBox, QFrame,
                              QScrollArea, QWidget, QApplication)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QFont, QPixmap
from utils.icon_utils import get_icon, IconColors


class SIEVDialog(QDialog):
    """Dialog base personalizado para SIEV con estilo consistente"""
    
    def __init__(self, title: str, parent=None, size: Tuple[int, int] = (400, 300)):
        super().__init__(parent)
        
        self.setWindowTitle(title)
        self.setFixedSize(size[0], size[1])
        self.setModal(True)
        
        # Layout principal
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(15)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Configurar estilo
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
            }
            QLabel {
                color: #2c3e50;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)
    
    def add_icon_header(self, icon_name: str, title: str, subtitle: str = "", icon_color: str = IconColors.BLUE):
        """Agregar header con icono y títulos"""
        header_layout = QHBoxLayout()
        
        # Icono
        icon_label = QLabel()
        icon_label.setFixedSize(48, 48)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        icon = get_icon(icon_name, 48, icon_color)
        pixmap = icon.pixmap(QSize(48, 48))
        icon_label.setPixmap(pixmap)
        
        header_layout.addWidget(icon_label)
        
        # Textos
        text_layout = QVBoxLayout()
        
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #2c3e50;")
        text_layout.addWidget(title_label)
        
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setStyleSheet("color: #7f8c8d; font-size: 11px;")
            subtitle_label.setWordWrap(True)
            text_layout.addWidget(subtitle_label)
        
        header_layout.addLayout(text_layout, 1)
        
        self.main_layout.addLayout(header_layout)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        self.main_layout.addWidget(separator)


class DialogUtils:
    """Utilidades para ventanas emergentes reutilizables"""
    
    @staticmethod
    def show_info(title: str, message: str, icon_name: str = "info", 
                  parent=None) -> None:
        """Mostrar diálogo de información"""
        dialog = SIEVDialog(title, parent, (450, 250))
        dialog.add_icon_header(icon_name, title, message, IconColors.BLUE)
        
        # Botón OK
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        ok_button = QPushButton("Entendido")
        ok_button.setIcon(get_icon("check", 16, IconColors.WHITE))
        ok_button.clicked.connect(dialog.accept)
        button_layout.addWidget(ok_button)
        
        dialog.main_layout.addLayout(button_layout)
        dialog.exec()
    
    @staticmethod
    def show_success(title: str, message: str, parent=None) -> None:
        """Mostrar diálogo de éxito"""
        DialogUtils.show_info(title, message, "circle-check", parent)
    
    @staticmethod
    def show_warning(title: str, message: str, parent=None) -> None:
        """Mostrar diálogo de advertencia"""
        dialog = SIEVDialog(title, parent, (450, 250))
        dialog.add_icon_header("triangle-alert", title, message, IconColors.ORANGE)
        
        # Botón OK
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        ok_button = QPushButton("Entendido")
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
        """)
        ok_button.setIcon(get_icon("alert-triangle", 16, IconColors.WHITE))
        ok_button.clicked.connect(dialog.accept)
        button_layout.addWidget(ok_button)
        
        dialog.main_layout.addLayout(button_layout)
        dialog.exec()
    
    @staticmethod
    def show_error(title: str, message: str, parent=None) -> None:
        """Mostrar diálogo de error"""
        dialog = SIEVDialog(title, parent, (450, 250))
        dialog.add_icon_header("circle-x", title, message, IconColors.RED)
        
        # Botón OK
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        ok_button = QPushButton("Cerrar")
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        ok_button.setIcon(get_icon("x", 16, IconColors.WHITE))
        ok_button.clicked.connect(dialog.accept)
        button_layout.addWidget(ok_button)
        
        dialog.main_layout.addLayout(button_layout)
        dialog.exec()
    
    @staticmethod
    def ask_confirmation(title: str, message: str, confirm_text: str = "Confirmar",
                        cancel_text: str = "Cancelar", parent=None) -> bool:
        """Mostrar diálogo de confirmación"""
        dialog = SIEVDialog(title, parent, (500, 300))
        dialog.add_icon_header("help-circle", title, message, IconColors.BLUE)
        
        # Botones
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_button = QPushButton(cancel_text)
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        cancel_button.setIcon(get_icon("x", 16, IconColors.WHITE))
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_button)
        
        confirm_button = QPushButton(confirm_text)
        confirm_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
        """)
        confirm_button.setIcon(get_icon("check", 16, IconColors.WHITE))
        confirm_button.clicked.connect(dialog.accept)
        button_layout.addWidget(confirm_button)
        
        dialog.main_layout.addLayout(button_layout)
        
        return dialog.exec() == QDialog.Accepted
    
    @staticmethod
    def ask_delete_confirmation(item_name: str, parent=None) -> bool:
        """Mostrar confirmación específica para eliminación"""
        dialog = SIEVDialog("Confirmar Eliminación", parent, (500, 300))
        dialog.add_icon_header("trash-2", "¿Eliminar elemento?", 
                             f"¿Está seguro de que desea eliminar '{item_name}'?\n\n"
                             f"Esta acción no se puede deshacer.", IconColors.RED)
        
        # Botones
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_button = QPushButton("Cancelar")
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        cancel_button.setIcon(get_icon("x", 16, IconColors.WHITE))
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_button)
        
        delete_button = QPushButton("Eliminar")
        delete_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        delete_button.setIcon(get_icon("trash-2", 16, IconColors.WHITE))
        delete_button.clicked.connect(dialog.accept)
        button_layout.addWidget(delete_button)
        
        dialog.main_layout.addLayout(button_layout)
        
        return dialog.exec() == QDialog.Accepted
    
    @staticmethod
    def get_text_input(title: str, prompt: str, default_text: str = "",
                      placeholder: str = "", parent=None) -> Tuple[str, bool]:
        """Obtener input de texto del usuario"""
        dialog = SIEVDialog(title, parent, (500, 250))
        dialog.add_icon_header("edit", title, prompt, IconColors.GREEN)
        
        # Campo de texto
        input_layout = QVBoxLayout()
        
        text_input = QLineEdit()
        text_input.setText(default_text)
        text_input.setPlaceholderText(placeholder)
        text_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #3498db;
            }
        """)
        input_layout.addWidget(text_input)
        
        dialog.main_layout.addLayout(input_layout)
        
        # Botones
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_button = QPushButton("Cancelar")
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_button)
        
        ok_button = QPushButton("Aceptar")
        ok_button.setIcon(get_icon("check", 16, IconColors.WHITE))
        ok_button.clicked.connect(dialog.accept)
        button_layout.addWidget(ok_button)
        
        dialog.main_layout.addLayout(button_layout)
        
        # Configurar enter para aceptar
        text_input.returnPressed.connect(dialog.accept)
        text_input.setFocus()
        
        if dialog.exec() == QDialog.Accepted:
            return text_input.text().strip(), True
        else:
            return "", False
    
    @staticmethod
    def get_choice(title: str, prompt: str, choices: List[str],
                  default_choice: int = 0, parent=None) -> Tuple[str, bool]:
        """Obtener selección de lista del usuario"""
        dialog = SIEVDialog(title, parent, (450, 280))
        dialog.add_icon_header("list", title, prompt, IconColors.BLUE)
        
        # ComboBox
        choice_layout = QVBoxLayout()
        
        combo = QComboBox()
        combo.addItems(choices)
        combo.setCurrentIndex(default_choice)
        combo.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                font-size: 12px;
            }
        """)
        choice_layout.addWidget(combo)
        
        dialog.main_layout.addLayout(choice_layout)
        
        # Botones
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_button = QPushButton("Cancelar")
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_button)
        
        ok_button = QPushButton("Seleccionar")
        ok_button.setIcon(get_icon("check", 16, IconColors.WHITE))
        ok_button.clicked.connect(dialog.accept)
        button_layout.addWidget(ok_button)
        
        dialog.main_layout.addLayout(button_layout)
        
        if dialog.exec() == QDialog.Accepted:
            return combo.currentText(), True
        else:
            return "", False
    
    @staticmethod
    def show_protocol_info(protocol_data: Dict[str, Any], parent=None) -> None:
        """Mostrar información detallada de protocolo"""
        protocol_name = protocol_data.get("name", "Sin nombre")
        dialog = SIEVDialog(f"Protocolo: {protocol_name}", parent, (600, 500))
        
        # Determinar icono según tipo
        behavior_type = protocol_data.get("behavior_type", "recording")
        if behavior_type == "caloric":
            icon_name = "thermometer"
            icon_color = IconColors.RED
        elif behavior_type == "window":
            icon_name = "monitor"
            icon_color = IconColors.BLUE
        else:
            icon_name = "eye"
            icon_color = IconColors.GREEN
        
        dialog.add_icon_header(icon_name, protocol_name, 
                             protocol_data.get("description", ""), icon_color)
        
        # Área de información scrollable
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Información básica
        info_text = f"""
<b>Información General:</b><br>
• Tipo: {protocol_data.get('behavior_type', 'N/A')}<br>
• Categoría: {protocol_data.get('category', 'N/A')}<br>
• Duración máxima: {protocol_data.get('duration_max', 'N/A')} segundos<br><br>
"""
        
        # Información de protocolo específico
        protocol_config = protocol_data.get("protocol", {})
        if protocol_config:
            info_text += "<b>Configuración:</b><br>"
            for key, value in protocol_config.items():
                if key != "events":
                    info_text += f"• {key}: {value}<br>"
            info_text += "<br>"
        
        # Eventos si los hay
        events = protocol_config.get("events", [])
        if events:
            info_text += "<b>Eventos Programados:</b><br>"
            for event in events:
                info_text += f"• {event.get('time', 0)}s: {event.get('description', 'Sin descripción')}<br>"
            info_text += "<br>"
        
        # Configuración de hardware
        hardware_config = protocol_data.get("hardware_control", {})
        if hardware_config.get("led_control", False):
            info_text += "<b>Control de Hardware:</b><br>"
            info_text += f"• Control LED: Sí<br>"
            info_text += f"• LED por defecto: {hardware_config.get('default_led', 'N/A')}<br>"
            info_text += f"• Comandos: {', '.join(hardware_config.get('esp8266_commands', []))}<br><br>"
        
        # Herramientas de gráfico
        graph_tools = protocol_data.get("graph_tools", {})
        if graph_tools:
            info_text += "<b>Herramientas de Gráfico:</b><br>"
            for tool, enabled in graph_tools.items():
                status = "Sí" if enabled else "No"
                info_text += f"• {tool}: {status}<br>"
        
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        info_label.setTextFormat(Qt.RichText)
        info_label.setStyleSheet("""
            QLabel {
                background-color: white;
                padding: 15px;
                border: 1px solid #dee2e6;
                border-radius: 4px;
            }
        """)
        scroll_layout.addWidget(info_label)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        dialog.main_layout.addWidget(scroll_area)
        
        # Botón cerrar
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_button = QPushButton("Cerrar")
        close_button.setIcon(get_icon("x", 16, IconColors.WHITE))
        close_button.clicked.connect(dialog.accept)
        button_layout.addWidget(close_button)
        
        dialog.main_layout.addLayout(button_layout)
        dialog.exec()
    
    @staticmethod
    def show_execution_progress(protocol_name: str, duration_max: int, 
                              parent=None) -> 'ProgressDialog':
        """Crear diálogo de progreso para ejecución de protocolo"""
        dialog = ProgressDialog(protocol_name, duration_max, parent)
        dialog.show()
        return dialog
    
    @staticmethod
    def show_hardware_status(siev_setup: Dict[str, Any], parent=None) -> None:
        """Mostrar estado del hardware SIEV"""
        dialog = SIEVDialog("Estado del Hardware SIEV", parent, (550, 400))
        dialog.add_icon_header("cpu", "Hardware SIEV", 
                             "Información detallada del sistema conectado", IconColors.GREEN)
        
        # Información del hardware
        hub_info = siev_setup.get('hub', {})
        esp_info = siev_setup.get('esp8266', {})
        camera_info = siev_setup.get('camera', {})
        
        info_text = f"""
<b>🔗 Hub USB:</b><br>
• Nombre: {hub_info.get('name', 'N/A')}<br>
• ID del dispositivo: {hub_info.get('vendor_id', 'N/A')}:{hub_info.get('product_id', 'N/A')}<br><br>

<b>📡 ESP8266:</b><br>
• Puerto: {esp_info.get('port', 'N/A')}<br>
• Estado: Conectado y funcional<br>
• Versión: {esp_info.get('info', {}).get('version', 'N/A')}<br><br>

<b>📹 Cámara:</b><br>
• Nombre: {camera_info.get('name', 'N/A')}<br>
• Índice OpenCV: {camera_info.get('opencv_index', 'N/A')}<br>
• Estado: {'Funcional' if camera_info.get('opencv_working', False) else 'Error'}<br><br>

<b>✅ Sistema Completo:</b><br>
Todo el hardware SIEV está conectado y listo para evaluaciones vestibulares.
"""
        
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        info_label.setTextFormat(Qt.RichText)
        info_label.setStyleSheet("""
            QLabel {
                background-color: #d5ead4;
                padding: 15px;
                border: 1px solid #27ae60;
                border-radius: 4px;
            }
        """)
        dialog.main_layout.addWidget(info_label)
        
        # Botón cerrar
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_button = QPushButton("Cerrar")
        close_button.setIcon(get_icon("x", 16, IconColors.WHITE))
        close_button.clicked.connect(dialog.accept)
        button_layout.addWidget(close_button)
        
        dialog.main_layout.addLayout(button_layout)
        dialog.exec()


class ProgressDialog(QDialog):
    """Diálogo de progreso para ejecución de protocolos"""
    
    def __init__(self, protocol_name: str, duration_max: int, parent=None):
        super().__init__(parent)
        
        self.protocol_name = protocol_name
        self.duration_max = duration_max
        
        self.setWindowTitle(f"Ejecutando: {protocol_name}")
        self.setFixedSize(500, 200)
        self.setModal(False)  # No modal para permitir interacción
        
        self.setup_ui()
    
    def setup_ui(self):
        """Configurar interfaz"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header_layout = QHBoxLayout()
        
        # Icono
        icon_label = QLabel()
        icon_label.setFixedSize(32, 32)
        icon = get_icon("circle-play", 32, IconColors.GREEN)
        pixmap = icon.pixmap(QSize(32, 32))
        icon_label.setPixmap(pixmap)
        header_layout.addWidget(icon_label)
        
        # Título
        title_label = QLabel(f"Ejecutando: {self.protocol_name}")
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        header_layout.addWidget(title_label, 1)
        
        layout.addLayout(header_layout)
        
        # Estado
        self.status_label = QLabel("Iniciando protocolo...")
        self.status_label.setStyleSheet("color: #7f8c8d;")
        layout.addWidget(self.status_label)
        
        # Tiempo
        self.time_label = QLabel(f"0s / {self.duration_max}s")
        self.time_label.setFont(QFont("Arial", 10))
        layout.addWidget(self.time_label)
        
        # Botón detener
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.stop_button = QPushButton("Detener")
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        self.stop_button.setIcon(get_icon("circle-stop", 16, IconColors.WHITE))
        button_layout.addWidget(self.stop_button)
        
        layout.addLayout(button_layout)
    
    def update_progress(self, progress_percent: float, status_message: str):
        """Actualizar progreso"""
        current_time = (progress_percent / 100) * self.duration_max
        
        self.status_label.setText(status_message)
        self.time_label.setText(f"{current_time:.1f}s / {self.duration_max}s")
        
        # Actualizar título de ventana
        self.setWindowTitle(f"Ejecutando: {self.protocol_name} ({progress_percent:.1f}%)")
    
    def on_execution_finished(self, success: bool):
        """Manejar finalización de ejecución"""
        if success:
            self.status_label.setText("✅ Protocolo completado exitosamente")
            self.stop_button.setText("Cerrar")
            self.stop_button.setStyleSheet("""
                QPushButton {
                    background-color: #27ae60;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #2ecc71;
                }
            """)
        else:
            self.status_label.setText("❌ Protocolo cancelado o falló")
            self.stop_button.setText("Cerrar")
        
        self.stop_button.clicked.disconnect()
        self.stop_button.clicked.connect(self.accept)


# Funciones de conveniencia
def show_info(title: str, message: str, parent=None):
    """Mostrar información"""
    DialogUtils.show_info(title, message, parent=parent)

def show_success(title: str, message: str, parent=None):
    """Mostrar éxito"""
    DialogUtils.show_success(title, message, parent=parent)

def show_warning(title: str, message: str, parent=None):
    """Mostrar advertencia"""
    DialogUtils.show_warning(title, message, parent=parent)

def show_error(title: str, message: str, parent=None):
    """Mostrar error"""
    DialogUtils.show_error(title, message, parent=parent)

def ask_confirmation(title: str, message: str, parent=None) -> bool:
    """Pedir confirmación"""
    return DialogUtils.ask_confirmation(title, message, parent=parent)

def ask_delete_confirmation(item_name: str, parent=None) -> bool:
    """Pedir confirmación de eliminación"""
    return DialogUtils.ask_delete_confirmation(item_name, parent=parent)

def get_text_input(title: str, prompt: str, default_text: str = "", parent=None) -> Tuple[str, bool]:
    """Obtener input de texto"""
    return DialogUtils.get_text_input(title, prompt, default_text, parent=parent)