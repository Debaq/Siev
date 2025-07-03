#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Patient Data Dialog - Diálogo para capturar datos básicos del paciente
"""

from datetime import datetime, date
from typing import Optional, Dict, Any
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                              QLineEdit, QDateEdit, QSpinBox, QTextEdit, 
                              QPushButton, QLabel, QFrame, QMessageBox)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont
from utils.icon_utils import get_icon, IconColors


class PatientDataDialog(QDialog):
    """
    Diálogo para capturar datos básicos del paciente al crear un nuevo documento.
    """
    
    def __init__(self, parent=None, edit_mode=False, existing_data=None):
        super().__init__(parent)
        
        self.edit_mode = edit_mode
        self.patient_data = {}
        
        # Configurar ventana
        title = "Editar Datos del Paciente" if edit_mode else "Nuevo Documento - Datos del Paciente"
        self.setWindowTitle(title)
        self.setFixedSize(500, 600)
        self.setModal(True)
        
        # Setup UI
        self.setup_ui()
        
        # Si hay datos existentes, cargarlos
        if existing_data:
            self.load_existing_data(existing_data)
        
        # Configurar conexiones
        self.setup_connections()
    
    def setup_ui(self):
        """Configurar interfaz de usuario"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # === HEADER ===
        self.create_header(main_layout)
        
        # === FORMULARIO ===
        self.create_form(main_layout)
        
        # === BOTONES ===
        self.create_buttons(main_layout)
        
        # Aplicar estilos
        self.apply_styles()
    
    def create_header(self, parent_layout):
        """Crear header con icono y título"""
        header_layout = QHBoxLayout()
        
        # Icono
        icon_label = QLabel()
        icon_label.setFixedSize(48, 48)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        icon = get_icon("user", 48, IconColors.BLUE)
        icon_label.setPixmap(icon.pixmap(48, 48))
        header_layout.addWidget(icon_label)
        
        # Textos
        text_layout = QVBoxLayout()
        
        title_text = "Editar Información del Paciente" if self.edit_mode else "Crear Nuevo Documento"
        title_label = QLabel(title_text)
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #2c3e50;")
        text_layout.addWidget(title_label)
        
        subtitle_text = "Modifique los datos del paciente" if self.edit_mode else "Ingrese los datos básicos del paciente para crear el documento"
        subtitle_label = QLabel(subtitle_text)
        subtitle_label.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        subtitle_label.setWordWrap(True)
        text_layout.addWidget(subtitle_label)
        
        header_layout.addLayout(text_layout, 1)
        parent_layout.addLayout(header_layout)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        parent_layout.addWidget(separator)
    
    def create_form(self, parent_layout):
        """Crear formulario de datos"""
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        
        # Nombre completo
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Ingrese nombre completo del paciente")
        form_layout.addRow("Nombre completo *:", self.name_edit)
        
        # ID del paciente
        self.patient_id_edit = QLineEdit()
        self.patient_id_edit.setPlaceholderText("RUT, DNI, o identificador único")
        form_layout.addRow("ID del paciente *:", self.patient_id_edit)
        
        # Fecha de nacimiento
        self.birth_date_edit = QDateEdit()
        self.birth_date_edit.setCalendarPopup(True)
        self.birth_date_edit.setDate(QDate(1990, 1, 1))
        self.birth_date_edit.setMaximumDate(QDate.currentDate())
        form_layout.addRow("Fecha de nacimiento *:", self.birth_date_edit)
        
        # Edad (calculada automáticamente)
        self.age_label = QLabel("0 años")
        self.age_label.setStyleSheet("color: #7f8c8d; font-weight: bold;")
        form_layout.addRow("Edad:", self.age_label)
        
        # Sexo
        self.gender_edit = QLineEdit()
        self.gender_edit.setPlaceholderText("M/F/Otro")
        form_layout.addRow("Sexo:", self.gender_edit)
        
        # Médico/Evaluador
        self.doctor_edit = QLineEdit()
        self.doctor_edit.setPlaceholderText("Nombre del médico o especialista")
        form_layout.addRow("Médico/Evaluador *:", self.doctor_edit)
        
        # Institución
        self.institution_edit = QLineEdit()
        self.institution_edit.setPlaceholderText("Hospital, clínica o centro médico")
        form_layout.addRow("Institución:", self.institution_edit)
        
        # Diagnóstico preliminar
        self.diagnosis_edit = QLineEdit()
        self.diagnosis_edit.setPlaceholderText("Sospecha diagnóstica o motivo de evaluación")
        form_layout.addRow("Diagnóstico preliminar:", self.diagnosis_edit)
        
        # Observaciones
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Observaciones adicionales, antecedentes relevantes...")
        self.notes_edit.setMaximumHeight(80)
        form_layout.addRow("Observaciones:", self.notes_edit)
        
        parent_layout.addLayout(form_layout)
        
        # Nota sobre campos requeridos
        required_note = QLabel("* Campos requeridos")
        required_note.setStyleSheet("color: #e74c3c; font-size: 10px; font-style: italic;")
        parent_layout.addWidget(required_note)
    
    def create_buttons(self, parent_layout):
        """Crear botones de acción"""
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # Botón Cancelar
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setIcon(get_icon("x", 16, IconColors.WHITE))
        self.btn_cancel.clicked.connect(self.reject)
        button_layout.addWidget(self.btn_cancel)
        
        # Botón principal
        main_text = "Guardar Cambios" if self.edit_mode else "Crear Documento"
        self.btn_main = QPushButton(main_text)
        self.btn_main.setIcon(get_icon("check", 16, IconColors.WHITE))
        self.btn_main.clicked.connect(self.validate_and_accept)
        button_layout.addWidget(self.btn_main)
        
        parent_layout.addLayout(button_layout)
    
    def setup_connections(self):
        """Configurar conexiones"""
        # Actualizar edad cuando cambie la fecha de nacimiento
        self.birth_date_edit.dateChanged.connect(self.update_age)
        
        # Actualizar edad inicial
        self.update_age()
    
    def apply_styles(self):
        """Aplicar estilos CSS"""
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
            }
            QLineEdit, QDateEdit, QTextEdit {
                padding: 8px;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                font-size: 12px;
                background-color: white;
            }
            QLineEdit:focus, QDateEdit:focus, QTextEdit:focus {
                border-color: #3498db;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
            QFormLayout QLabel {
                color: #2c3e50;
                font-weight: bold;
            }
        """)
        
        # Estilo específico para botón cancelar
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
            QPushButton:pressed {
                background-color: #6c7b7d;
            }
        """)
    
    def update_age(self):
        """Actualizar cálculo de edad"""
        birth_date = self.birth_date_edit.date().toPython()
        today = date.today()
        
        age = today.year - birth_date.year
        if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
            age -= 1
        
        self.age_label.setText(f"{age} años")
    
    def validate_and_accept(self):
        """Validar datos y aceptar"""
        # Validar campos requeridos
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Campo Requerido", "El nombre del paciente es requerido.")
            self.name_edit.setFocus()
            return
        
        if not self.patient_id_edit.text().strip():
            QMessageBox.warning(self, "Campo Requerido", "El ID del paciente es requerido.")
            self.patient_id_edit.setFocus()
            return
        
        if not self.doctor_edit.text().strip():
            QMessageBox.warning(self, "Campo Requerido", "El médico/evaluador es requerido.")
            self.doctor_edit.setFocus()
            return
        
        # Validar fecha de nacimiento razonable
        birth_date = self.birth_date_edit.date().toPython()
        today = date.today()
        age = today.year - birth_date.year
        
        if age < 0 or age > 120:
            QMessageBox.warning(self, "Fecha Inválida", "La fecha de nacimiento no es válida.")
            self.birth_date_edit.setFocus()
            return
        
        # Construir datos del paciente
        self.patient_data = {
            "name": self.name_edit.text().strip(),
            "patient_id": self.patient_id_edit.text().strip(),
            "birth_date": birth_date.isoformat(),
            "age": age,
            "gender": self.gender_edit.text().strip(),
            "doctor": self.doctor_edit.text().strip(),
            "institution": self.institution_edit.text().strip(),
            "preliminary_diagnosis": self.diagnosis_edit.text().strip(),
            "notes": self.notes_edit.toPlainText().strip(),
            "created_date": datetime.now().isoformat(),
            "created_by": self.doctor_edit.text().strip() or "Usuario"
        }
        
        self.accept()
    
    def load_existing_data(self, data: Dict[str, Any]):
        """Cargar datos existentes en el formulario"""
        self.name_edit.setText(data.get("name", ""))
        self.patient_id_edit.setText(data.get("patient_id", ""))
        
        # Cargar fecha de nacimiento
        if "birth_date" in data:
            try:
                birth_date = datetime.fromisoformat(data["birth_date"]).date()
                self.birth_date_edit.setDate(QDate(birth_date))
            except:
                pass
        
        self.gender_edit.setText(data.get("gender", ""))
        self.doctor_edit.setText(data.get("doctor", ""))
        self.institution_edit.setText(data.get("institution", ""))
        self.diagnosis_edit.setText(data.get("preliminary_diagnosis", ""))
        self.notes_edit.setPlainText(data.get("notes", ""))
    
    def get_patient_data(self) -> Dict[str, Any]:
        """Obtener datos del paciente"""
        return self.patient_data.copy()


# Función de conveniencia
def show_patient_data_dialog(parent=None, edit_mode=False, existing_data=None) -> Optional[Dict[str, Any]]:
    """
    Mostrar diálogo de datos del paciente.
    
    Args:
        parent: Widget padre
        edit_mode: True para editar, False para crear nuevo
        existing_data: Datos existentes si está en modo edición
        
    Returns:
        Dict con datos del paciente o None si se canceló
    """
    dialog = PatientDataDialog(parent, edit_mode, existing_data)
    
    if dialog.exec() == QDialog.Accepted:
        return dialog.get_patient_data()
    else:
        return None