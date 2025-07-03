#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Welcome Widget - Pantalla de bienvenida para crear/abrir documentos
"""

from typing import Optional
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                              QLabel, QFrame, QSizePolicy, QSpacerItem,
                              QGraphicsDropShadowEffect)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor
from utils.icon_utils import get_icon, IconColors


class WelcomeWidget(QWidget):
    """
    Widget de bienvenida mostrado en el área central cuando no hay documento abierto.
    Permite crear nuevo documento o abrir documento existente.
    """
    
    # Señales
    create_document_requested = Signal()
    open_document_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configurar widget
        self.setMinimumSize(600, 400)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Setup UI
        self.setup_ui()
        self.setup_connections()
        
        print("✅ WelcomeWidget inicializado")
    
    def setup_ui(self):
        """Configurar interfaz de usuario"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(30)
        
        # Spacer superior para centrar verticalmente
        main_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        # === LOGO Y TÍTULO ===
        self.create_header(main_layout)
        
        # === DESCRIPCIÓN ===
        self.create_description(main_layout)
        
        # === BOTONES PRINCIPALES ===
        self.create_main_buttons(main_layout)
        
        # === INFORMACIÓN ADICIONAL ===
        self.create_info_section(main_layout)
        
        # Spacer inferior para centrar verticalmente
        main_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        # Aplicar estilos
        self.apply_styles()
    
    def create_header(self, parent_layout):
        """Crear header con logo y título"""
        header_layout = QVBoxLayout()
        header_layout.setAlignment(Qt.AlignCenter)
        header_layout.setSpacing(15)
        
        # Logo/Icono principal
        logo_label = QLabel()
        logo_label.setFixedSize(80, 80)
        logo_label.setAlignment(Qt.AlignCenter)
        
        # Crear icono compuesto
        logo_icon = self.create_logo_icon()
        logo_label.setPixmap(logo_icon)
        
        header_layout.addWidget(logo_label)
        
        # Título principal
        title_label = QLabel("VideoSIEV")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #2c3e50; margin: 10px 0;")
        header_layout.addWidget(title_label)
        
        # Subtítulo
        subtitle_label = QLabel("Sistema Integrado de Evaluación Vestibular")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setFont(QFont("Arial", 14))
        subtitle_label.setStyleSheet("color: #7f8c8d; margin-bottom: 10px;")
        header_layout.addWidget(subtitle_label)
        
        parent_layout.addLayout(header_layout)
    
    def create_description(self, parent_layout):
        """Crear sección de descripción"""
        desc_layout = QVBoxLayout()
        desc_layout.setAlignment(Qt.AlignCenter)
        
        # Texto principal
        main_text = QLabel("Bienvenido al sistema VideoSIEV")
        main_text.setAlignment(Qt.AlignCenter)
        main_text.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        main_text.setStyleSheet("color: #34495e; margin: 10px 0;")
        desc_layout.addWidget(main_text)
        
        # Texto descriptivo
        desc_text = QLabel(
            "Para comenzar, cree un nuevo documento de paciente o abra un documento existente.\n"
            "Cada documento contiene los datos del paciente y todas las pruebas realizadas."
        )
        desc_text.setAlignment(Qt.AlignCenter)
        desc_text.setFont(QFont("Arial", 12))
        desc_text.setStyleSheet("color: #7f8c8d; line-height: 1.4; margin: 10px 20px;")
        desc_text.setWordWrap(True)
        desc_layout.addWidget(desc_text)
        
        parent_layout.addLayout(desc_layout)
    
    def create_main_buttons(self, parent_layout):
        """Crear botones principales de acción"""
        buttons_layout = QHBoxLayout()
        buttons_layout.setAlignment(Qt.AlignCenter)
        buttons_layout.setSpacing(30)
        
        # === BOTÓN CREAR DOCUMENTO ===
        create_frame = self.create_action_button(
            icon_name="file-plus",
            title="Nuevo Documento",
            description="Crear documento para\nnuevo paciente",
            color="#27ae60",
            hover_color="#2ecc71"
        )
        self.btn_create = create_frame.findChild(QPushButton)
        buttons_layout.addWidget(create_frame)
        
        # === BOTÓN ABRIR DOCUMENTO ===
        open_frame = self.create_action_button(
            icon_name="folder-open", 
            title="Abrir Documento",
            description="Abrir documento\nexistente (.siev)",
            color="#3498db",
            hover_color="#5dade2"
        )
        self.btn_open = open_frame.findChild(QPushButton)
        buttons_layout.addWidget(open_frame)
        
        parent_layout.addLayout(buttons_layout)
    
    def create_action_button(self, icon_name: str, title: str, description: str, 
                           color: str, hover_color: str) -> QFrame:
        """Crear botón de acción con frame contenedor"""
        # Frame contenedor
        frame = QFrame()
        frame.setFixedSize(200, 160)
        frame.setFrameStyle(QFrame.Box)
        frame.setStyleSheet(f"""
            QFrame {{
                border: 2px solid #ecf0f1;
                border-radius: 12px;
                background-color: white;
            }}
            QFrame:hover {{
                border-color: {color};
                background-color: #f8f9fa;
            }}
        """)
        
        # Agregar sombra
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, 5)
        frame.setGraphicsEffect(shadow)
        
        # Layout del frame
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(20, 20, 20, 20)
        frame_layout.setSpacing(12)
        frame_layout.setAlignment(Qt.AlignCenter)
        
        # Icono
        icon_label = QLabel()
        icon_label.setFixedSize(48, 48)
        icon_label.setAlignment(Qt.AlignCenter)
        icon = get_icon(icon_name, 48, color)
        icon_label.setPixmap(icon.pixmap(48, 48))
        frame_layout.addWidget(icon_label)
        
        # Título
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {color}; margin: 5px 0;")
        frame_layout.addWidget(title_label)
        
        # Descripción
        desc_label = QLabel(description)
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setFont(QFont("Arial", 10))
        desc_label.setStyleSheet("color: #7f8c8d; line-height: 1.3;")
        desc_label.setWordWrap(True)
        frame_layout.addWidget(desc_label)
        
        # Botón invisible que cubre todo el frame
        button = QPushButton(frame)
        button.setGeometry(0, 0, 200, 160)
        button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
            }
            QPushButton:hover {
                background-color: rgba(52, 152, 219, 0.1);
                border-radius: 12px;
            }
            QPushButton:pressed {
                background-color: rgba(52, 152, 219, 0.2);
            }
        """)
        
        return frame
    
    def create_info_section(self, parent_layout):
        """Crear sección de información adicional"""
        info_layout = QVBoxLayout()
        info_layout.setAlignment(Qt.AlignCenter)
        info_layout.setSpacing(15)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("color: #ecf0f1; margin: 20px 100px;")
        info_layout.addWidget(separator)
        
        # Información sobre formatos
        format_layout = QHBoxLayout()
        format_layout.setAlignment(Qt.AlignCenter)
        format_layout.setSpacing(30)
        
        # Info sobre .siev
        siev_info = self.create_info_item(
            "file-text",
            "Formato .siev",
            "Documentos comprimidos con\ndatos del paciente y pruebas"
        )
        format_layout.addWidget(siev_info)
        
        # Info sobre pruebas
        tests_info = self.create_info_item(
            "activity",
            "Múltiples Pruebas",
            "Calóricas, oculomotoras,\nposicionales y equilibrio"
        )
        format_layout.addWidget(tests_info)
        
        # Info sobre hardware
        hardware_info = self.create_info_item(
            "cpu",
            "Hardware Integrado",
            "VideoSIEV, 9Axis y\nPosturógrafo"
        )
        format_layout.addWidget(hardware_info)
        
        info_layout.addLayout(format_layout)
        
        # Versión
        version_label = QLabel("VideoSIEV v2.0 - Sistema modular de evaluación vestibular")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setFont(QFont("Arial", 9))
        version_label.setStyleSheet("color: #bdc3c7; margin-top: 20px;")
        info_layout.addWidget(version_label)
        
        parent_layout.addLayout(info_layout)
    
    def create_info_item(self, icon_name: str, title: str, description: str) -> QWidget:
        """Crear item de información"""
        widget = QWidget()
        widget.setFixedWidth(160)
        
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(8)
        
        # Icono
        icon_label = QLabel()
        icon_label.setFixedSize(32, 32)
        icon_label.setAlignment(Qt.AlignCenter)
        icon = get_icon(icon_name, 32, IconColors.BLUE)
        icon_label.setPixmap(icon.pixmap(32, 32))
        layout.addWidget(icon_label)
        
        # Título
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #34495e;")
        layout.addWidget(title_label)
        
        # Descripción
        desc_label = QLabel(description)
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setFont(QFont("Arial", 9))
        desc_label.setStyleSheet("color: #7f8c8d; line-height: 1.2;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        return widget
    
    def create_logo_icon(self) -> QPixmap:
        """Crear icono de logo compuesto"""
        pixmap = QPixmap(80, 80)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Círculo de fondo
        painter.setBrush(QColor("#3498db"))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, 80, 80)
        
        # Icono de ojo en el centro
        eye_icon = get_icon("eye", 40, IconColors.WHITE)
        eye_pixmap = eye_icon.pixmap(40, 40)
        painter.drawPixmap(20, 20, eye_pixmap)
        
        painter.end()
        return pixmap
    
    def setup_connections(self):
        """Configurar conexiones de señales"""
        if hasattr(self, 'btn_create'):
            self.btn_create.clicked.connect(self.create_document_requested.emit)
        if hasattr(self, 'btn_open'):
            self.btn_open.clicked.connect(self.open_document_requested.emit)
    
    def apply_styles(self):
        """Aplicar estilos globales"""
        self.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
            }
        """)
    
    def paintEvent(self, event):
        """Pintar fondo con gradiente sutil"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Gradiente de fondo
        from PySide6.QtGui import QLinearGradient
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor("#f8f9fa"))
        gradient.setColorAt(1, QColor("#e9ecef"))
        
        painter.fillRect(self.rect(), gradient)
        painter.end()
        
        super().paintEvent(event)


# Widget de estado "Sin documento"
class NoDocumentWidget(QWidget):
    """Widget simple para mostrar cuando no hay documento (alternativa minimalista)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Configurar interfaz minimalista"""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)
        
        # Icono
        icon_label = QLabel()
        icon_label.setFixedSize(64, 64)
        icon_label.setAlignment(Qt.AlignCenter)
        icon = get_icon("file-text", 64, IconColors.GRAY)
        icon_label.setPixmap(icon.pixmap(64, 64))
        layout.addWidget(icon_label)
        
        # Mensaje
        message_label = QLabel("No hay documento abierto")
        message_label.setAlignment(Qt.AlignCenter)
        message_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        message_label.setStyleSheet("color: #95a5a6;")
        layout.addWidget(message_label)
        
        # Instrucción
        instruction_label = QLabel("Use el menú Archivo para crear o abrir un documento")
        instruction_label.setAlignment(Qt.AlignCenter)
        instruction_label.setFont(QFont("Arial", 12))
        instruction_label.setStyleSheet("color: #bdc3c7;")
        layout.addWidget(instruction_label)
        
        self.setStyleSheet("background-color: #f8f9fa;")