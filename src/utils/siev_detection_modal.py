#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modal para detección de hardware SIEV - Versión simple y robusta
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QPushButton, QProgressBar, QApplication)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from utils.siev_detection_thread import SievDetectionThread

class SievDetectionModal(QDialog):
    """Modal simple para detección SIEV sin dependencias complejas."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Detectando Hardware SIEV")
        self.setFixedSize(450, 250)
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
        
        # Icono simple con emoji
        self.icon_label = QLabel("🔍")
        self.icon_label.setStyleSheet("""
            QLabel {
                font-size: 32px;
                color: #3498db;
                padding: 10px;
            }
        """)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
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
        
        # === INFORMATION ===
        self.info_label = QLabel("Conecte el dispositivo SIEV si no está enchufado")
        self.info_label.setStyleSheet("""
            QLabel {
                background-color: #ecf0f1;
                padding: 10px;
                border-radius: 5px;
                color: #34495e;
                font-size: 10px;
            }
        """)
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)
        
        # === BUTTONS ===
        self.button_layout = QHBoxLayout()
        
        # Botón Reintentar
        self.btn_retry = QPushButton("🔄 Reintentar")
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
        self.btn_close = QPushButton("✅ Continuar")
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
    
    def start_detection(self):
        """Iniciar proceso de detección"""
        print("🔍 Iniciando detección SIEV desde modal...")
        
        # Reset UI al estado inicial
        self.icon_label.setText("🔍")
        self.icon_label.setStyleSheet("""
            QLabel {
                font-size: 32px;
                color: #3498db;
                padding: 10px;
            }
        """)
        
        self.status_label.setText("Detectando hardware SIEV...")
        self.detail_label.setText("Verificando conexión del dispositivo...")
        self.info_label.setText("Conecte el dispositivo SIEV si no está enchufado")
        
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
        print("🔄 Reintentando detección SIEV...")
        self.start_detection()
    
    def on_detection_finished(self, result):
        """Manejar resultado de detección"""
        print(f"📡 Resultado detección recibido: {result['success']}")
        
        self.detection_result = result
        self.progress_bar.hide()
        
        if result['success']:
            self.show_success_state(result['setup'])
        else:
            self.show_error_state(result.get('error', 'Hardware no detectado'))
    
    def show_success_state(self, setup):
        """Mostrar estado de éxito"""
        # Cambiar icono y colores
        self.icon_label.setText("✅")
        self.icon_label.setStyleSheet("""
            QLabel {
                font-size: 32px;
                color: #27ae60;
                padding: 10px;
            }
        """)
        
        # Actualizar textos
        self.status_label.setText("¡SIEV detectado correctamente!")
        self.status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
        
        self.detail_label.setText("Hardware conectado y funcionando")
        
        # Información detallada
        hub_name = setup['hub']['name']
        esp_port = setup['esp8266']['port']
        camera_index = setup['camera'].get('opencv_index', 'N/A')
        camera_name = setup['camera']['name']
        
        info_text = (
            f"✅ Hub: {hub_name}\n"
            f"✅ ESP8266: {esp_port}\n"
            f"✅ Cámara: {camera_name} (OpenCV: {camera_index})"
        )
        
        self.info_label.setText(info_text)
        self.info_label.setStyleSheet("""
            QLabel {
                background-color: #d5ead4;
                padding: 10px;
                border-radius: 5px;
                color: #27ae60;
                font-size: 10px;
                border: 1px solid #27ae60;
            }
        """)
        
        # Mostrar botón de continuar
        self.btn_close.show()
    
    def show_error_state(self, error_message):
        """Mostrar estado de error"""
        # Cambiar icono y colores
        self.icon_label.setText("❌")
        self.icon_label.setStyleSheet("""
            QLabel {
                font-size: 32px;
                color: #e74c3c;
                padding: 10px;
            }
        """)
        
        # Actualizar textos
        self.status_label.setText("SIEV no encontrado")
        self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        
        self.detail_label.setText("No se pudo conectar con el hardware")
        
        # Información de error
        error_text = (
            f"❌ Error: {error_message}\n\n"
            "Verifique que:\n"
            "• El dispositivo esté conectado correctamente\n"
            "• Los drivers USB estén instalados\n"
            "• El ESP8266 esté funcionando (LED parpadeando)\n"
            "• No haya otros programas usando el puerto serie"
        )
        
        self.info_label.setText(error_text)
        self.info_label.setStyleSheet("""
            QLabel {
                background-color: #fdeaea;
                padding: 10px;
                border-radius: 5px;
                color: #e74c3c;
                font-size: 10px;
                border: 1px solid #e74c3c;
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
        print("🚪 Cerrando modal de detección SIEV...")
        if self.detection_thread and self.detection_thread.isRunning():
            print("🛑 Terminando hilo de detección...")
            self.detection_thread.stop_detection()
        
        event.accept()
    
    def reject(self):
        """Override reject para cleanup"""
        print("❌ Modal rechazado, limpiando...")
        if self.detection_thread and self.detection_thread.isRunning():
            self.detection_thread.stop_detection()
        
        super().reject()
    
    def accept(self):
        """Override accept para cleanup"""
        print("✅ Modal aceptado, limpiando...")
        if self.detection_thread and self.detection_thread.isRunning():
            self.detection_thread.stop_detection()
        
        super().accept()