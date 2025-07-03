#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modal para detección de hardware SIEV - Versión con iconos SVG exclusivamente
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QPushButton, QProgressBar, QApplication, QWidget)
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QFont, QPixmap
from utils.siev_detection_thread import SievDetectionThread
from utils.icon_utils import get_icon, IconColors

class SievDetectionModal(QDialog):
    """Modal para detección SIEV usando exclusivamente iconos SVG."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Detectando Hardware SIEV")
        self.setFixedSize(500, 300)
        self.setModal(True)
        
        # Variables
        self.detection_result = None
        self.detection_thread = None
        
        # Setup UI
        self.setup_ui()
        
        # Iniciar detección con delay
        QTimer.singleShot(300, self.start_detection)
    
    def setup_ui(self):
        """Configurar interfaz de usuario"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # === HEADER ===
        header_layout = QHBoxLayout()
        
        # Icono principal usando SVG
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(48, 48)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_main_icon("search", IconColors.BLUE)
        header_layout.addWidget(self.icon_label)
        
        # Texto principal
        text_layout = QVBoxLayout()
        
        self.status_label = QLabel("Detectando hardware SIEV...")
        self.status_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.status_label.setStyleSheet("color: #2c3e50;")
        text_layout.addWidget(self.status_label)
        
        self.detail_label = QLabel("Verificando conexión del dispositivo...")
        self.detail_label.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        self.detail_label.setWordWrap(True)
        text_layout.addWidget(self.detail_label)
        
        header_layout.addLayout(text_layout, 1)
        layout.addLayout(header_layout)
        
        # === PROGRESS BAR ===
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminado
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # === INFORMATION AREA ===
        self.info_widget = QWidget()
        self.info_layout = QVBoxLayout(self.info_widget)
        self.info_layout.setContentsMargins(0, 0, 0, 0)
        self.info_layout.setSpacing(5)
        
        # Widget de información inicial
        self.create_info_line("info", "Conecte el dispositivo SIEV si no está enchufado", IconColors.BLUE)
        
        layout.addWidget(self.info_widget)
        
        # === BUTTONS ===
        self.button_layout = QHBoxLayout()
        
        # Botón Reintentar
        self.btn_retry = QPushButton("Reintentar")
        self.btn_retry.setIcon(get_icon("rotate-cw", 16, IconColors.WHITE))
        self.btn_retry.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
        """)
        self.btn_retry.clicked.connect(self.retry_detection)
        self.btn_retry.hide()
        
        # Botón Continuar sin SIEV
        self.btn_continue = QPushButton("Continuar sin SIEV")
        self.btn_continue.setIcon(get_icon("x", 16, IconColors.WHITE))
        self.btn_continue.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        self.btn_continue.clicked.connect(self.reject)
        self.btn_continue.hide()
        
        # Botón Continuar (éxito)
        self.btn_close = QPushButton("Continuar")
        self.btn_close.setIcon(get_icon("circle-check", 16, IconColors.WHITE))
        self.btn_close.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
        """)
        self.btn_close.clicked.connect(self.accept)
        self.btn_close.hide()
        
        self.button_layout.addWidget(self.btn_retry)
        self.button_layout.addWidget(self.btn_continue)
        self.button_layout.addWidget(self.btn_close)
        
        layout.addLayout(self.button_layout)
    
    def set_main_icon(self, icon_name, color):
        """Establecer icono principal"""
        icon = get_icon(icon_name, 48, color)
        pixmap = icon.pixmap(QSize(48, 48))
        self.icon_label.setPixmap(pixmap)
    
    def create_info_line(self, icon_name, text, color):
        """Crear línea de información con icono SVG"""
        line_widget = QWidget()
        line_layout = QHBoxLayout(line_widget)
        line_layout.setContentsMargins(10, 5, 10, 5)
        line_layout.setSpacing(10)
        
        # Icono pequeño
        icon_label = QLabel()
        icon_label.setFixedSize(16, 16)
        icon = get_icon(icon_name, 16, color)
        pixmap = icon.pixmap(QSize(16, 16))
        icon_label.setPixmap(pixmap)
        line_layout.addWidget(icon_label)
        
        # Texto
        text_label = QLabel(text)
        text_label.setStyleSheet(f"color: {color}; font-size: 11px;")
        text_label.setWordWrap(True)
        line_layout.addWidget(text_label, 1)
        
        # Estilo del contenedor
        line_widget.setStyleSheet("""
            QWidget {
                background-color: #ecf0f1;
                border-radius: 5px;
                border: 1px solid #bdc3c7;
            }
        """)
        
        return line_widget
    
    def clear_info_area(self):
        """Limpiar área de información"""
        while self.info_layout.count():
            child = self.info_layout.takeAt(0)
            if child.widget():
                child.widget().setParent(None)
    
    def add_info_line(self, icon_name, text, color):
        """Agregar línea de información"""
        line_widget = self.create_info_line(icon_name, text, color)
        self.info_layout.addWidget(line_widget)
    
    def start_detection(self):
        """Iniciar proceso de detección"""
        print("Iniciando detección SIEV desde modal...")
        
        # Reset UI al estado inicial
        self.set_main_icon("search", IconColors.BLUE)
        
        self.status_label.setText("Detectando hardware SIEV...")
        self.detail_label.setText("Verificando conexión del dispositivo...")
        
        # Limpiar y mostrar info inicial
        self.clear_info_area()
        self.add_info_line("info", "Conecte el dispositivo SIEV si no está enchufado", IconColors.BLUE)
        
        self.progress_bar.setRange(0, 0)
        self.progress_bar.show()
        
        # Ocultar todos los botones
        self.btn_retry.hide()
        self.btn_continue.hide()
        self.btn_close.hide()
        
        # Procesar eventos pendientes
        QApplication.processEvents()
        
        # Crear e iniciar hilo de detección
        if self.detection_thread and self.detection_thread.isRunning():
            self.detection_thread.terminate()
            self.detection_thread.wait()
        
        self.detection_thread = SievDetectionThread()
        self.detection_thread.detection_finished.connect(self.on_detection_finished)
        self.detection_thread.start()
    
    def retry_detection(self):
        """Reintentar detección"""
        print("Reintentando detección SIEV...")
        self.start_detection()
    
    def on_detection_finished(self, result):
        """Manejar resultado de detección"""
        print(f"Resultado detección recibido: {result['success']}")
        
        self.detection_result = result
        self.progress_bar.hide()
        
        if result['success']:
            self.show_success_state(result['setup'])
        else:
            self.show_error_state(result.get('error', 'Hardware no detectado'))
    
    def show_success_state(self, setup):
        """Mostrar estado de éxito"""
        # Cambiar icono principal
        self.set_main_icon("circle-check", IconColors.GREEN)
        
        # Actualizar textos
        self.status_label.setText("SIEV detectado correctamente!")
        self.status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
        
        self.detail_label.setText("Hardware conectado y funcionando")
        
        # Limpiar y mostrar información detallada
        self.clear_info_area()
        
        hub_name = setup['hub']['name']
        esp_port = setup['esp8266']['port']
        camera_index = setup['camera'].get('opencv_index', 'N/A')
        camera_name = setup['camera']['name']
        
        self.add_info_line("circle-check", f"Hub: {hub_name}", IconColors.GREEN)
        self.add_info_line("circle-check", f"ESP8266: {esp_port}", IconColors.GREEN)
        self.add_info_line("circle-check", f"Cámara: {camera_name} (OpenCV: {camera_index})", IconColors.GREEN)
        
        # Cambiar estilo del área de información
        self.info_widget.setStyleSheet("""
            QWidget {
                background-color: #d5ead4;
                border-radius: 5px;
                border: 1px solid #27ae60;
                padding: 5px;
            }
        """)
        
        # Mostrar botón de continuar
        self.btn_close.show()
    
    def show_error_state(self, error_message):
        """Mostrar estado de error"""
        # Cambiar icono principal
        self.set_main_icon("circle-x", IconColors.RED)
        
        # Actualizar textos
        self.status_label.setText("SIEV no encontrado")
        self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        
        self.detail_label.setText("No se pudo conectar con el hardware")
        
        # Limpiar y mostrar información de error
        self.clear_info_area()
        
        self.add_info_line("circle-x", f"Error: {error_message}", IconColors.RED)
        self.add_info_line("triangle-alert", "Verifique que:", IconColors.ORANGE)
        self.add_info_line("circle", "El dispositivo esté conectado correctamente", IconColors.GRAY)
        self.add_info_line("circle", "Los drivers USB estén instalados", IconColors.GRAY)
        self.add_info_line("circle", "El ESP8266 esté funcionando (LED parpadeando)", IconColors.GRAY)
        self.add_info_line("circle", "No haya otros programas usando el puerto serie", IconColors.GRAY)
        
        # Cambiar estilo del área de información
        self.info_widget.setStyleSheet("""
            QWidget {
                background-color: #fdeaea;
                border-radius: 5px;
                border: 1px solid #e74c3c;
                padding: 5px;
            }
        """)
        
        # Mostrar botones de acción
        self.btn_retry.show()
        self.btn_continue.show()
    
    def get_detection_result(self):
        """Obtener resultado de la detección"""
        return self.detection_result
    
    def closeEvent(self, event):
        """Manejar cierre del modal"""
        print("Cerrando modal de detección SIEV...")
        if self.detection_thread and self.detection_thread.isRunning():
            print("Terminando hilo de detección...")
            self.detection_thread.stop_detection()
        
        event.accept()
    
    def reject(self):
        """Override reject para cleanup"""
        print("Modal rechazado, limpiando...")
        if self.detection_thread and self.detection_thread.isRunning():
            self.detection_thread.stop_detection()
        
        super().reject()
    
    def accept(self):
        """Override accept para cleanup"""
        print("Modal aceptado, limpiando...")
        if self.detection_thread and self.detection_thread.isRunning():
            self.detection_thread.stop_detection()
        
        super().accept()