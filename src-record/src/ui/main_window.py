import sys
import os
import time
from datetime import datetime

from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout,
                              QHBoxLayout, QGridLayout, QLabel, QLineEdit,
                              QComboBox, QPushButton, QGroupBox,
                              QMessageBox)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from controllers.camera_controller import CameraController
from hardware.serial_handler import SerialHandler
from database.database import DatabaseManager
from utils.validators import validate_all_fields
from ui.styles import (get_dark_theme, get_group_style, get_input_style,
                      get_combo_style, get_button_style, get_status_style,
                      get_camera_label_style)

class PatientRecordSystem(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema de Registro con Cámara - Irrigación de Oído")
        self.setGeometry(100, 100, 1200, 800)
        
        # Variables de estado
        self.recording = False
        self.fixed_state = False
        self.start_time = None
        self.current_video_path = None
        
        # Crear carpeta de videos
        self.videos_folder = "videos_pacientes"
        if not os.path.exists(self.videos_folder):
            os.makedirs(self.videos_folder)
        
        # Inicializar componentes
        self.init_components()
        
        # Configurar interfaz
        self.setup_ui()
        self.apply_dark_theme()
        
        # Iniciar cámara por defecto
        if self.available_cameras:
            self.camera_controller.start_camera(self.available_cameras[0])
        
    def init_components(self):
        """Inicializa todos los componentes del sistema"""
        # Inicializar comunicación serial
        self.serial_handler = SerialHandler()
        
        # Inicializar base de datos
        try:
            self.db_manager = DatabaseManager()
        except Exception as e:
            QMessageBox.critical(self, "Error de Base de Datos", 
                               f"No se pudo inicializar la base de datos: {e}")
            sys.exit(1)
        
        # Configurar cámara
        self.camera_controller = CameraController()
        self.camera_controller.frame_ready.connect(self._handle_frame)
        self.available_cameras = self.camera_controller.get_available_cameras()
        
        if not self.available_cameras:
            QMessageBox.warning(self, "Sin Cámaras", 
                              "No se detectaron cámaras disponibles")
        
    def setup_ui(self):
        """Configura la interfaz de usuario"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # PANEL IZQUIERDO - CÁMARA
        left_panel = self.create_left_panel()
        
        # PANEL DERECHO - CONTROLES
        right_panel = self.create_right_panel()
        
        # Agregar paneles al layout principal
        main_layout.addLayout(left_panel, 2)  # 2/3 del espacio
        main_layout.addLayout(right_panel, 1)  # 1/3 del espacio
        
        central_widget.setLayout(main_layout)
        
        # Timer para actualizar tiempo de grabación
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_recording_time)
        
    def create_left_panel(self):
        """Crea el panel izquierdo con la cámara"""
        left_panel = QVBoxLayout()
        
        # Marco de la cámara
        camera_group = QGroupBox("Vista en Vivo")
        camera_group.setStyleSheet(get_group_style())
        camera_layout = QVBoxLayout()
        
        # Selector de cámara
        if self.available_cameras:
            camera_select_layout = QHBoxLayout()
            camera_select_layout.addWidget(QLabel("Cámara:"))
            
            self.camera_combo = QComboBox()
            self.camera_combo.setStyleSheet(get_combo_style())
            for i, cam_index in enumerate(self.available_cameras):
                self.camera_combo.addItem(f"Cámara {cam_index}", cam_index)
            self.camera_combo.currentIndexChanged.connect(self.change_camera)
            camera_select_layout.addWidget(self.camera_combo)
            camera_select_layout.addStretch()
            
            camera_layout.addLayout(camera_select_layout)
        
        # Label para mostrar video
        self.camera_label = QLabel()
        self.camera_label.setMinimumSize(640, 480)
        self.camera_label.setMaximumSize(640, 480)
        self.camera_label.setStyleSheet(get_camera_label_style())
        self.camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_label.setText("Iniciando cámara...")
        self.camera_label.setScaledContents(True)
        
        camera_layout.addWidget(self.camera_label)
        camera_group.setLayout(camera_layout)
        left_panel.addWidget(camera_group)
        
        # Botones de control de video
        video_controls = QHBoxLayout()
        
        self.record_btn = QPushButton("🔴 GRABAR")
        self.record_btn.clicked.connect(self.toggle_recording)
        self.record_btn.setMinimumHeight(50)
        self.record_btn.setStyleSheet(get_button_style("#ff4444"))
        
        self.fixed_btn = QPushButton("💡 LED: OFF")
        self.fixed_btn.clicked.connect(self.toggle_fixed)
        self.fixed_btn.setMinimumHeight(50)
        self.fixed_btn.setStyleSheet(get_button_style("#ff8c00"))
        
        video_controls.addWidget(self.record_btn)
        video_controls.addWidget(self.fixed_btn)
        left_panel.addLayout(video_controls)
        
        # Estado del sistema
        self.status_label = QLabel("Sistema listo")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #4aff6b; 
                font-weight: bold; 
                font-size: 14px;
                padding: 10px;
                border: 1px solid #4aff6b;
                border-radius: 6px;
                background-color: rgba(74, 255, 107, 0.1);
            }
        """)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_panel.addWidget(self.status_label)
        
        left_panel.addStretch()
        return left_panel
        
    def create_right_panel(self):
        """Crea el panel derecho con controles"""
        right_panel = QVBoxLayout()
        right_panel.setSpacing(20)
        
        # Título
        title_label = QLabel("DATOS DEL PACIENTE")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #4a9eff; padding: 15px;")
        right_panel.addWidget(title_label)
        
        # Campos de datos
        data_group = QGroupBox("Información del Procedimiento")
        data_group.setStyleSheet(get_group_style())
        data_layout = QGridLayout()
        data_layout.setSpacing(15)
        
        # Nombre del paciente
        name_label = QLabel("👤 NOMBRE DEL PACIENTE:")
        name_label.setStyleSheet("color: white; font-weight: bold; font-size: 12px;")
        self.name_input = QLineEdit()
        self.name_input.setStyleSheet(get_input_style())
        self.name_input.setMinimumHeight(40)
        self.name_input.setPlaceholderText("Ingrese nombre completo del paciente")
        
        data_layout.addWidget(name_label, 0, 0)
        data_layout.addWidget(self.name_input, 0, 1)
        
        # Oído irrigado
        ear_label = QLabel("👂 OÍDO IRRIGADO:")
        ear_label.setStyleSheet("color: white; font-weight: bold; font-size: 12px;")
        self.ear_combo = QComboBox()
        self.ear_combo.addItems(["Seleccionar...", "Oído Izquierdo", "Oído Derecho", "Ambos Oídos"])
        self.ear_combo.setStyleSheet(get_combo_style())
        self.ear_combo.setMinimumHeight(40)
        
        data_layout.addWidget(ear_label, 1, 0)
        data_layout.addWidget(self.ear_combo, 1, 1)
        
        # Temperatura
        temp_label = QLabel("🌡️ TEMPERATURA (°C):")
        temp_label.setStyleSheet("color: white; font-weight: bold; font-size: 12px;")
        self.temp_input = QLineEdit()
        self.temp_input.setStyleSheet(get_input_style())
        self.temp_input.setMinimumHeight(40)
        self.temp_input.setPlaceholderText("Ej: 37.5")
        
        data_layout.addWidget(temp_label, 2, 0)
        data_layout.addWidget(self.temp_input, 2, 1)
        
        data_group.setLayout(data_layout)
        right_panel.addWidget(data_group)
        
        # Botón guardar
        self.save_btn = QPushButton("💾 GUARDAR REGISTRO")
        self.save_btn.clicked.connect(self.save_record)
        self.save_btn.setMinimumHeight(60)
        self.save_btn.setStyleSheet(get_button_style("#4aff6b"))
        right_panel.addWidget(self.save_btn)
        
        # Botón limpiar
        clear_btn = QPushButton("🗑️ LIMPIAR CAMPOS")
        clear_btn.clicked.connect(self.clear_fields)
        clear_btn.setMinimumHeight(45)
        clear_btn.setStyleSheet(get_button_style("#666666"))
        right_panel.addWidget(clear_btn)
        
        # Información adicional
        info_group = QGroupBox("Información del Sistema")
        info_group.setStyleSheet(get_group_style())
        info_layout = QVBoxLayout()
        
        self.recording_time_label = QLabel("⏱️ Tiempo de grabación: 00:00")
        self.recording_time_label.setStyleSheet("color: white; font-size: 11px; padding: 5px;")
        
        self.video_count_label = QLabel(f"📁 Videos guardados: {self.count_videos()}")
        self.video_count_label.setStyleSheet("color: white; font-size: 11px; padding: 5px;")
        
        # Estado de conexión
        serial_status = "🔗 Arduino: Conectado" if self.serial_handler.is_connected() else "❌ Arduino: Desconectado"
        self.serial_status_label = QLabel(serial_status)
        self.serial_status_label.setStyleSheet("color: white; font-size: 11px; padding: 5px;")
        
        info_layout.addWidget(self.recording_time_label)
        info_layout.addWidget(self.video_count_label)
        info_layout.addWidget(self.serial_status_label)
        info_group.setLayout(info_layout)
        right_panel.addWidget(info_group)
        
        right_panel.addStretch()
        return right_panel
        
    def count_videos(self):
        """Cuenta los videos en la carpeta"""
        if os.path.exists(self.videos_folder):
            return len([f for f in os.listdir(self.videos_folder) if f.endswith('.mp4')])
        return 0
        
    def change_camera(self, index):
        """Cambia la cámara activa"""
        if index >= 0 and index < len(self.available_cameras):
            camera_index = self.available_cameras[index]
            success = self.camera_controller.change_camera(camera_index)
            if success:
                self.status_label.setText(f"📷 Cámara cambiada a: {camera_index}")
            else:
                self.status_label.setText("❌ Error al cambiar cámara")
                QMessageBox.warning(self, "Error", f"No se pudo acceder a la cámara {camera_index}")
        
    def apply_dark_theme(self):
        """Aplica tema oscuro"""
        self.setStyleSheet(get_dark_theme())

    def _handle_frame(self, pixmap):
        """Recibe imágenes del controlador y las muestra."""
        self.camera_label.setPixmap(pixmap)
        
    def toggle_recording(self):
        """Alterna grabación"""
        if not self.recording:
            self.start_recording()
        else:
            self.stop_recording()
            
    def start_recording(self):
        """Inicia grabación"""
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Error", "Debe ingresar el nombre del paciente antes de grabar")
            return
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        patient_name = self.name_input.text().strip().replace(" ", "_")
        filename = f"{patient_name}_{timestamp}.mp4"
        self.current_video_path = os.path.join(self.videos_folder, filename)
        
        success = self.camera_controller.start_recording(self.current_video_path)
        if not success:
            QMessageBox.warning(self, "Error", "No se pudo iniciar la grabación")
            return
            
        self.recording = True
        self.start_time = time.time()
        
        self.record_btn.setText("⏹️ DETENER")
        self.record_btn.setStyleSheet(get_button_style("#ff0000"))
        self.status_label.setText("🔴 GRABANDO...")
        self.status_label.setStyleSheet(self.status_label.styleSheet().replace("#4aff6b", "#ff4444"))
        
        self.timer.start(1000)  # Actualizar cada segundo
        
    def stop_recording(self):
        """Detiene grabación"""
        self.camera_controller.stop_recording()
        self.recording = False
        self.timer.stop()
        
        duration = int(time.time() - self.start_time) if self.start_time else 0
        
        self.record_btn.setText("🔴 GRABAR")
        self.record_btn.setStyleSheet(get_button_style("#ff4444"))
        self.status_label.setText(f"✅ Video guardado ({duration}s)")
        self.status_label.setStyleSheet(self.status_label.styleSheet().replace("#ff4444", "#4aff6b"))
        
        self.update_video_count()
        
    def toggle_fixed(self):
        """Alterna LED"""
        if not self.fixed_state:
            self.fixed_on()
        else:
            self.fixed_off()
            
    def fixed_on(self):
        """Activa LED"""
        success = self.serial_handler.send_data("L_12_ON")
        
        if success or not self.serial_handler.is_connected():
            self.fixed_state = True
            self.fixed_btn.setText("💡 LED: ON")
            self.fixed_btn.setStyleSheet(get_button_style("#4aff6b"))
            status_text = "💡 LED encendido" if success else "💡 LED encendido (sin Arduino)"
            self.status_label.setText(status_text)
        else:
            QMessageBox.warning(self, "Error", "No se pudo enviar comando al Arduino")
        
    def fixed_off(self):
        """Desactiva LED"""
        success = self.serial_handler.send_data("L_12_OFF")
        
        if success or not self.serial_handler.is_connected():
            self.fixed_state = False
            self.fixed_btn.setText("💡 LED: OFF")
            self.fixed_btn.setStyleSheet(get_button_style("#ff8c00"))
            status_text = "💡 LED apagado" if success else "💡 LED apagado (sin Arduino)"
            self.status_label.setText(status_text)
        else:
            QMessageBox.warning(self, "Error", "No se pudo enviar comando al Arduino")
        
    def update_recording_time(self):
        """Actualiza tiempo de grabación"""
        if self.recording and self.start_time:
            elapsed = int(time.time() - self.start_time)
            minutes = elapsed // 60
            seconds = elapsed % 60
            self.recording_time_label.setText(f"⏱️ Tiempo de grabación: {minutes:02d}:{seconds:02d}")
            
    def update_video_count(self):
        """Actualiza contador de videos"""
        count = self.count_videos()
        self.video_count_label.setText(f"📁 Videos guardados: {count}")
        
    def save_record(self):
        """Guarda registro"""
        # Validar campos usando el módulo de validaciones
        valid, message = validate_all_fields(
            self.name_input.text(),
            self.ear_combo.currentIndex(),
            self.temp_input.text()
        )
        
        if not valid:
            QMessageBox.warning(self, "Error", message)
            return
            
        try:
            nombre = self.name_input.text().strip()
            oido = self.ear_combo.currentText()
            temperatura = float(self.temp_input.text())
            archivo_video = self.current_video_path if self.current_video_path else ""
            duracion = int(time.time() - self.start_time) if self.start_time else 0
            
            success = self.db_manager.insert_record(
                nombre, oido, temperatura, archivo_video, duracion
            )
            
            if success:
                QMessageBox.information(self, "✅ Éxito", "Registro guardado correctamente")
                self.clear_fields()
                self.status_label.setText("💾 Registro guardado en base de datos")
            else:
                QMessageBox.critical(self, "❌ Error", "Error al guardar en la base de datos")
                
        except Exception as e:
            QMessageBox.critical(self, "❌ Error", f"Error inesperado: {str(e)}")
            
    def clear_fields(self):
        """Limpia campos"""
        self.name_input.clear()
        self.ear_combo.setCurrentIndex(0)
        self.temp_input.clear()
        self.current_video_path = None
        self.recording_time_label.setText("⏱️ Tiempo de grabación: 00:00")
        self.status_label.setText("🗑️ Campos limpiados")
        
    def closeEvent(self, event):
        """Maneja cierre de aplicación"""
        if self.recording:
            reply = QMessageBox.question(self, 'Confirmación', 
                                       '¿Está seguro de salir? La grabación se detendrá.',
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.stop_recording()
                self.cleanup_and_exit()
                event.accept()
            else:
                event.ignore()
        else:
            self.cleanup_and_exit()
            event.accept()
            
    def cleanup_and_exit(self):
        """Limpia recursos de forma más robusta"""
        print("Iniciando limpieza de recursos...")
        
        try:
            # Detener cámara PRIMERO
            if hasattr(self, 'camera_controller') and self.camera_controller:
                print("Deteniendo thread de cámara...")
                self.camera_controller.stop_camera()

                # Esperar a que termine completamente
                if self.camera_controller.isRunning():
                    if not self.camera_controller.wait(5000):  # 5 segundos
                        print("Forzando terminación de cámara...")
                        self.camera_controller.terminate()
                        self.camera_controller.wait(2000)
            
            # Desconectar serial
            if hasattr(self, 'serial_handler') and self.serial_handler:
                print("Desconectando serial...")
                self.serial_handler.disconnect()
            
            # Cerrar base de datos
            if hasattr(self, 'db_manager') and self.db_manager:
                print("Cerrando base de datos...")
                self.db_manager.close()
            
            print("Limpieza completada exitosamente")
            
        except Exception as e:
            print(f"Error durante la limpieza: {e}")


            

# Función de compatibilidad para el main.py original
def run_app():
    """Función para mantener compatibilidad con estructura anterior"""
    from PySide6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    app.setApplicationName("Sistema de Registro con Cámara")
    
    window = PatientRecordSystem()
    window.show()

    sys.exit(app.exec())

