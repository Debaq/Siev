from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget,
                               QLabel, QLineEdit, QFileDialog, QMessageBox, QHBoxLayout)
from PySide6.QtCore import Qt
from camera_thread import CameraThread 
from serial_handler import SerialHandler 
from database import Database  
from pacient_controller import PatientController  
from styles import apply_styles  
import sys
import os

def run_app():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Registro de Procedimientos Médicos")
        self.setGeometry(100, 100, 800, 600)

        self.db = Database()
        self.controller = PatientController(self.db)

        self.setup_ui()
        self.camera_thread = None
        self.serial_handler = SerialHandler()

    def setup_ui(self):
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nombre del paciente")

        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("ID del paciente")

        self.start_btn = QPushButton("Iniciar Grabación")
        self.stop_btn = QPushButton("Detener Grabación")
        self.save_btn = QPushButton("Guardar Datos")

        self.start_btn.clicked.connect(self.start_recording)
        self.stop_btn.clicked.connect(self.stop_recording)
        self.save_btn.clicked.connect(self.save_data)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Nombre del paciente:"))
        layout.addWidget(self.name_input)
        layout.addWidget(QLabel("ID del paciente:"))
        layout.addWidget(self.id_input)

        layout.addWidget(self.start_btn)
        layout.addWidget(self.stop_btn)
        layout.addWidget(self.save_btn)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        apply_styles(self)

    def start_recording(self):
        name = self.name_input.text()
        patient_id = self.id_input.text()

        if not self.controller.validate_patient_info(name, patient_id):
            QMessageBox.warning(self, "Error", "Debe ingresar nombre e ID.")
            return

        # Detener grabación anterior si existe
        if self.camera_thread and self.camera_thread.is_alive():
            self.camera_thread.stop()
            self.camera_thread.join()

        filename = f"{name}_{patient_id}.avi".replace(" ", "_")
        output_path = os.path.join("videos_pacientes", filename)

        self.camera_thread = CameraThread(output_path)
        self.camera_thread.start()
        
        QMessageBox.information(self, "Información", "Grabación iniciada")

    def stop_recording(self):
        if self.camera_thread and self.camera_thread.is_alive():
            self.camera_thread.stop()
            self.camera_thread.join()
            QMessageBox.information(self, "Información", "Grabación detenida")
        else:
            QMessageBox.warning(self, "Advertencia", "No hay grabación en curso")

    def save_data(self):
        name = self.name_input.text()
        patient_id = self.id_input.text()
        if not self.controller.save_patient_info(name, patient_id):
            QMessageBox.warning(self, "Error", "Datos incompletos o no válidos.")
        else:
            QMessageBox.information(self, "Éxito", "Datos guardados correctamente.")
            # Limpiar campos después de guardar
            self.name_input.clear()
            self.id_input.clear()

    def closeEvent(self, event):
        # Limpiar recursos al cerrar
        if self.camera_thread and self.camera_thread.is_alive():
            self.camera_thread.stop()
            self.camera_thread.join()
        
        if self.serial_handler:
            self.serial_handler.close()
        
        event.accept()