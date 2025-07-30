import time
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                            QLineEdit, QSpinBox, QComboBox, QTextEdit, 
                            QPushButton, QLabel, QGroupBox, QDateEdit,
                            QMessageBox, QDialogButtonBox)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont


class NewUserDialog(QDialog):
    """
    Diálogo para crear un nuevo usuario en el sistema VNG.
    Recopila información personal del paciente.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nuevo Usuario - Sistema VNG")
        self.setModal(True)
        self.resize(450, 600)
        
        # Datos del usuario que se retornarán
        self.user_data = None
        
        self.setup_ui()
        self.setup_connections()
    
    def setup_ui(self):
        """Configurar la interfaz del diálogo"""
        layout = QVBoxLayout(self)
        
        # Título
        title_label = QLabel("Crear Nuevo Usuario")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Información personal
        personal_group = QGroupBox("Información Personal")
        personal_layout = QFormLayout(personal_group)
        
        # Nombre completo
        self.nombre_edit = QLineEdit()
        self.nombre_edit.setPlaceholderText("Ingrese nombre completo")
        personal_layout.addRow("Nombre completo*:", self.nombre_edit)
        
        # RUT/ID del paciente
        self.rut_edit = QLineEdit()
        self.rut_edit.setPlaceholderText("12.345.678-9 o ID único")
        personal_layout.addRow("RUT/ID Paciente:", self.rut_edit)
        
        # Edad
        self.edad_spin = QSpinBox()
        self.edad_spin.setRange(0, 120)
        self.edad_spin.setValue(30)
        self.edad_spin.setSuffix(" años")
        personal_layout.addRow("Edad:", self.edad_spin)
        
        # Género
        self.genero_combo = QComboBox()
        self.genero_combo.addItems(["Seleccionar...", "Masculino", "Femenino", "Otro", "Prefiero no decir"])
        personal_layout.addRow("Género:", self.genero_combo)
        
        # Fecha de nacimiento
        self.fecha_nacimiento = QDateEdit()
        self.fecha_nacimiento.setCalendarPopup(True)
        self.fecha_nacimiento.setDate(QDate.currentDate().addYears(-30))
        self.fecha_nacimiento.setMaximumDate(QDate.currentDate())
        personal_layout.addRow("Fecha de nacimiento:", self.fecha_nacimiento)
        
        layout.addWidget(personal_group)
        import time
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                              QLineEdit, QSpinBox, QComboBox, QDateEdit, 
                              QTextEdit, QPushButton, QLabel, QMessageBox,
                              QTabWidget, QWidget, QFrame)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont

class NewUserDialog(QDialog):
    """Diálogo para crear nuevo usuario con sistema de pestañas"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.user_data = None
        self.setup_ui()
        self.connect_signals()
        
    def setup_ui(self):
        """Configurar interfaz de usuario con pestañas"""
        self.setWindowTitle("Nuevo Usuario")
        self.setModal(True)
        self.resize(500, 400)
        
        # Layout principal
        main_layout = QVBoxLayout(self)
        
        # Widget de pestañas
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Crear pestañas
        self.create_basic_tab()
        self.create_medical_tab()
        self.create_institutional_tab()
        self.create_contact_tab()
        self.create_observations_tab()
        
        # Botones
        button_layout = QHBoxLayout()
        self.cancel_button = QPushButton("Cancelar")
        self.save_button = QPushButton("Guardar Usuario")
        self.save_button.setDefault(True)
        
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.save_button)
        
        main_layout.addLayout(button_layout)
        
    def create_basic_tab(self):
        """Crear pestaña de información básica (obligatoria)"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Título
        title = QLabel("Información Básica")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title)
        
        # Separador
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # Formulario
        form_layout = QFormLayout()
        
        # Nombre (obligatorio)
        self.nombre_edit = QLineEdit()
        self.nombre_edit.setPlaceholderText("Ingrese el nombre completo")
        form_layout.addRow("Nombre *:", self.nombre_edit)
        
        # Nombre social (opcional)
        self.nombre_social_edit = QLineEdit()
        self.nombre_social_edit.setPlaceholderText("Nombre social (opcional)")
        form_layout.addRow("Nombre Social:", self.nombre_social_edit)
        
        # RUT/ID (obligatorio)
        self.rut_edit = QLineEdit()
        self.rut_edit.setPlaceholderText("Ej: 12345678-9")
        form_layout.addRow("RUT/ID *:", self.rut_edit)
        
        # Fecha de nacimiento (obligatorio)
        self.fecha_nacimiento = QDateEdit()
        self.fecha_nacimiento.setDate(QDate.currentDate().addYears(-30))
        self.fecha_nacimiento.setDisplayFormat("dd/MM/yyyy")
        self.fecha_nacimiento.setCalendarPopup(True)
        form_layout.addRow("Fecha Nacimiento *:", self.fecha_nacimiento)
        
        # Edad (calculada automáticamente)
        self.edad_label = QLabel("30 años")
        self.edad_label.setStyleSheet("color: #666; font-style: italic;")
        form_layout.addRow("Edad:", self.edad_label)
        
        # Género (opcional)
        self.genero_combo = QComboBox()
        self.genero_combo.addItems(["Seleccione...", "Masculino", "Femenino", "Otro", "Prefiero no decir"])
        form_layout.addRow("Género:", self.genero_combo)
        
        layout.addLayout(form_layout)
        layout.addStretch()
        
        # Nota sobre campos obligatorios
        note = QLabel("* Campos obligatorios")
        note.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(note)
        
        self.tab_widget.addTab(tab, "Información Básica")
        
    def create_medical_tab(self):
        """Crear pestaña de información médica"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Título
        title = QLabel("Información Médica")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title)
        
        # Separador
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # Formulario
        form_layout = QFormLayout()
        
        self.medico_edit = QLineEdit()
        self.medico_edit.setPlaceholderText("Nombre del médico tratante")
        form_layout.addRow("Médico Tratante:", self.medico_edit)
        
        self.diagnostico_edit = QLineEdit()
        self.diagnostico_edit.setPlaceholderText("Diagnóstico principal")
        form_layout.addRow("Diagnóstico:", self.diagnostico_edit)
        
        layout.addLayout(form_layout)
        
        # Historia clínica
        historia_label = QLabel("Historia Clínica:")
        layout.addWidget(historia_label)
        
        self.historia_text = QTextEdit()
        self.historia_text.setPlaceholderText("Información relevante de la historia clínica del paciente...")
        self.historia_text.setMaximumHeight(150)
        layout.addWidget(self.historia_text)
        
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "Información Médica")
        
    def create_institutional_tab(self):
        """Crear pestaña de información institucional"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Título
        title = QLabel("Información Institucional")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title)
        
        # Separador
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # Formulario
        form_layout = QFormLayout()
        
        self.institucion_edit = QLineEdit()
        self.institucion_edit.setPlaceholderText("Nombre de la institución")
        form_layout.addRow("Institución:", self.institucion_edit)
        
        self.numero_estudio_edit = QLineEdit()
        self.numero_estudio_edit.setPlaceholderText("Número o código del estudio")
        form_layout.addRow("Número de Estudio:", self.numero_estudio_edit)
        
        layout.addLayout(form_layout)
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "Información Institucional")
        
    def create_contact_tab(self):
        """Crear pestaña de información de contacto"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Título
        title = QLabel("Información de Contacto")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title)
        
        # Separador
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # Formulario
        form_layout = QFormLayout()
        
        self.telefono_edit = QLineEdit()
        self.telefono_edit.setPlaceholderText("Número de teléfono")
        form_layout.addRow("Teléfono:", self.telefono_edit)
        
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("correo@ejemplo.com")
        form_layout.addRow("Email:", self.email_edit)
        
        layout.addLayout(form_layout)
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "Contacto")
        
    def create_observations_tab(self):
        """Crear pestaña de observaciones"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Título
        title = QLabel("Observaciones Adicionales")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title)
        
        # Separador
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # Área de texto
        observaciones_label = QLabel("Observaciones:")
        layout.addWidget(observaciones_label)
        
        self.observaciones_text = QTextEdit()
        self.observaciones_text.setPlaceholderText("Observaciones adicionales, notas especiales, comentarios...")
        layout.addWidget(self.observaciones_text)
        
        self.tab_widget.addTab(tab, "Observaciones")
        
    def connect_signals(self):
        """Conectar señales"""
        # Botones
        self.cancel_button.clicked.connect(self.reject)
        self.save_button.clicked.connect(self.create_user)
        
        # Validación en tiempo real
        self.nombre_edit.textChanged.connect(self.validate_form)
        self.rut_edit.textChanged.connect(self.validate_form)
        
        # Cálculo automático de edad
        self.fecha_nacimiento.dateChanged.connect(self.calculate_age)
        
        # Validación inicial
        self.validate_form()
        self.calculate_age()
        
    def calculate_age(self):
        """Calcular edad basada en fecha de nacimiento"""
        try:
            birth_date = self.fecha_nacimiento.date()
            current_date = QDate.currentDate()
            
            age = current_date.year() - birth_date.year()
            
            # Ajustar si no ha cumplido años este año
            if (current_date.month(), current_date.day()) < (birth_date.month(), birth_date.day()):
                age -= 1
            
            self.edad_label.setText(f"{age} años")
            
        except Exception as e:
            self.edad_label.setText("Error calculando edad")
            print(f"Error calculando edad: {e}")
            
    def validate_form(self):
        """Validar formulario en tiempo real"""
        nombre_valid = len(self.nombre_edit.text().strip()) >= 2
        rut_valid = len(self.rut_edit.text().strip()) >= 3
        
        # Habilitar/deshabilitar botón guardar
        self.save_button.setEnabled(nombre_valid and rut_valid)
        
        # Cambiar estilo de campos según validación
        if not nombre_valid and len(self.nombre_edit.text()) > 0:
            self.nombre_edit.setStyleSheet("border: 2px solid red;")
        else:
            self.nombre_edit.setStyleSheet("")
            
        if not rut_valid and len(self.rut_edit.text()) > 0:
            self.rut_edit.setStyleSheet("border: 2px solid red;")
        else:
            self.rut_edit.setStyleSheet("")
    
    def create_user(self):
        """Crear usuario con los datos del formulario"""
        # Validar campos obligatorios
        if not self.validate_required_fields():
            return
        
        # Calcular edad actual
        birth_date = self.fecha_nacimiento.date()
        current_date = QDate.currentDate()
        age = current_date.year() - birth_date.year()
        if (current_date.month(), current_date.day()) < (birth_date.month(), birth_date.day()):
            age -= 1
        
        # Recopilar datos
        self.user_data = {
            "nombre": self.nombre_edit.text().strip(),
            "nombre_social": self.nombre_social_edit.text().strip() or None,
            "rut_id": self.rut_edit.text().strip(),
            "edad": age,
            "genero": self.genero_combo.currentText() if self.genero_combo.currentIndex() > 0 else None,
            "fecha_nacimiento": self.fecha_nacimiento.date().toString("yyyy-MM-dd"),
            "medico_tratante": self.medico_edit.text().strip() or None,
            "diagnostico": self.diagnostico_edit.text().strip() or None,
            "historia_clinica": self.historia_text.toPlainText().strip() or None,
            "institucion": self.institucion_edit.text().strip() or None,
            "numero_estudio": self.numero_estudio_edit.text().strip() or None,
            "observaciones": self.observaciones_text.toPlainText().strip() or None,
            "telefono": self.telefono_edit.text().strip() or None,
            "email": self.email_edit.text().strip() or None,
            "fecha_creacion": time.time(),
            "creado_por": "Sistema VNG"
        }
        
        # Confirmar creación
        user_display = self.user_data['nombre']
        if self.user_data['nombre_social']:
            user_display += f" ({self.user_data['nombre_social']})"
            
        reply = QMessageBox.question(
            self,
            "Confirmar Creación",
            f"¿Crear nuevo usuario para:\n\n{user_display}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self.accept()
    
    def validate_required_fields(self):
        """Validar que los campos obligatorios estén completos"""
        errors = []
        
        # Nombre obligatorio
        if len(self.nombre_edit.text().strip()) < 2:
            errors.append("• El nombre debe tener al menos 2 caracteres")
        
        # RUT obligatorio
        if len(self.rut_edit.text().strip()) < 3:
            errors.append("• El RUT/ID es obligatorio")
        
        # Validar email si se proporciona
        email = self.email_edit.text().strip()
        if email and "@" not in email:
            errors.append("• El formato del email no es válido")
        
        # Mostrar errores si existen
        if errors:
            QMessageBox.warning(
                self,
                "Campos Incompletos",
                "Por favor corrija los siguientes errores:\n\n" + "\n".join(errors)
            )
            return False
        
        return True
    
    def get_user_data(self):
        """Obtener los datos del usuario creado"""
        return self.user_data


class EditUserDialog(NewUserDialog):
    """
    Diálogo para editar un usuario existente.
    Hereda de NewUserDialog y precarga los datos.
    """
    
    def __init__(self, user_data, parent=None):
        self.original_user_data = user_data
        super().__init__(parent)
        self.setWindowTitle("Editar Usuario")
        self.save_button.setText("Guardar Cambios")
        self.load_user_data()
        
    def load_user_data(self):
        """Cargar datos del usuario en el formulario"""
        try:
            data = self.original_user_data
            
            # Información básica
            self.nombre_edit.setText(data.get('nombre', ''))
            self.nombre_social_edit.setText(data.get('nombre_social', ''))
            self.rut_edit.setText(data.get('rut_id', ''))
            
            # Fecha de nacimiento
            if data.get('fecha_nacimiento'):
                fecha = QDate.fromString(data['fecha_nacimiento'], "yyyy-MM-dd")
                self.fecha_nacimiento.setDate(fecha)
            
            # Género
            genero = data.get('genero', '')
            if genero:
                index = self.genero_combo.findText(genero)
                if index >= 0:
                    self.genero_combo.setCurrentIndex(index)
            
            # Información médica
            self.medico_edit.setText(data.get('medico_tratante', ''))
            self.diagnostico_edit.setText(data.get('diagnostico', ''))
            self.historia_text.setPlainText(data.get('historia_clinica', ''))
            
            # Información institucional
            self.institucion_edit.setText(data.get('institucion', ''))
            self.numero_estudio_edit.setText(data.get('numero_estudio', ''))
            
            # Contacto
            self.telefono_edit.setText(data.get('telefono', ''))
            self.email_edit.setText(data.get('email', ''))
            
            # Observaciones
            self.observaciones_text.setPlainText(data.get('observaciones', ''))
            
            # Recalcular edad
            self.calculate_age()
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error cargando datos del usuario: {e}")
            
    def create_user(self):
        """Modificar usuario existente - sobrescribe el método padre"""
        # Validar campos obligatorios
        if not self.validate_required_fields():
            return
        
        # Calcular edad actual
        birth_date = self.fecha_nacimiento.date()
        current_date = QDate.currentDate()
        age = current_date.year() - birth_date.year()
        if (current_date.month(), current_date.day()) < (birth_date.month(), birth_date.day()):
            age -= 1
        
        # Recopilar datos actualizados
        self.user_data = {
            "nombre": self.nombre_edit.text().strip(),
            "nombre_social": self.nombre_social_edit.text().strip() or None,
            "rut_id": self.rut_edit.text().strip(),
            "edad": age,
            "genero": self.genero_combo.currentText() if self.genero_combo.currentIndex() > 0 else None,
            "fecha_nacimiento": self.fecha_nacimiento.date().toString("yyyy-MM-dd"),
            "medico_tratante": self.medico_edit.text().strip() or None,
            "diagnostico": self.diagnostico_edit.text().strip() or None,
            "historia_clinica": self.historia_text.toPlainText().strip() or None,
            "institucion": self.institucion_edit.text().strip() or None,
            "numero_estudio": self.numero_estudio_edit.text().strip() or None,
            "observaciones": self.observaciones_text.toPlainText().strip() or None,
            "telefono": self.telefono_edit.text().strip() or None,
            "email": self.email_edit.text().strip() or None,
            "ultima_modificacion": time.time(),
            "modificado_por": "Sistema VNG"
        }
        
        # Confirmar cambios
        user_display = self.user_data['nombre']
        if self.user_data['nombre_social']:
            user_display += f" ({self.user_data['nombre_social']})"
            
        reply = QMessageBox.question(
            self,
            "Confirmar Cambios",
            f"¿Guardar cambios para:\n\n{user_display}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self.accept()
        
        # Botones
        button_layout = QHBoxLayout()
        
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_create = QPushButton("Crear Usuario")
        self.btn_create.setDefault(True)
        
        # Estilo para el botón principal
        self.btn_create.setStyleSheet("""
            QPushButton {
                background-color: #007ACC;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #005A9B;
            }
            QPushButton:pressed {
                background-color: #004080;
            }
        """)
        
        button_layout.addStretch()
        button_layout.addWidget(self.btn_cancel)
        button_layout.addWidget(self.btn_create)
        
        layout.addLayout(button_layout)
        
        # Nota sobre campos obligatorios
        note_label = QLabel("* Campos obligatorios")
        note_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(note_label)
    
    def setup_connections(self):
        """Configurar conexiones de señales"""
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_create.clicked.connect(self.create_user)
        
        # Validación en tiempo real del nombre
        self.nombre_edit.textChanged.connect(self.validate_form)
    
    def validate_form(self):
        """Validar formulario en tiempo real"""
        nombre_valid = len(self.nombre_edit.text().strip()) >= 2
        
        # Habilitar/deshabilitar botón de crear
        self.btn_create.setEnabled(nombre_valid)
        
        # Cambiar estilo del campo nombre si es inválido
        if not nombre_valid and len(self.nombre_edit.text()) > 0:
            self.nombre_edit.setStyleSheet("border: 2px solid red;")
        else:
            self.nombre_edit.setStyleSheet("")
    
    def create_user(self):
        """Crear usuario con los datos del formulario"""
        # Validar campos obligatorios
        if not self.validate_required_fields():
            return
        
        # Recopilar datos
        self.user_data = {
            "nombre": self.nombre_edit.text().strip(),
            "rut_id": self.rut_edit.text().strip() or None,
            "edad": self.edad_spin.value(),
            "genero": self.genero_combo.currentText() if self.genero_combo.currentIndex() > 0 else None,
            "fecha_nacimiento": self.fecha_nacimiento.date().toString("yyyy-MM-dd"),
            "medico_tratante": self.medico_edit.text().strip() or None,
            "diagnostico": self.diagnostico_edit.text().strip() or None,
            "historia_clinica": self.historia_text.toPlainText().strip() or None,
            "institucion": self.institucion_edit.text().strip() or None,
            "numero_estudio": self.numero_estudio_edit.text().strip() or None,
            "observaciones": self.observaciones_text.toPlainText().strip() or None,
            "telefono": self.telefono_edit.text().strip() or None,
            "email": self.email_edit.text().strip() or None,
            "fecha_creacion": time.time(),
            "creado_por": "Sistema VNG"
        }
        
        # Confirmar creación
        reply = QMessageBox.question(
            self,
            "Confirmar Creación",
            f"¿Crear nuevo usuario para:\n\n{self.user_data['nombre']}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self.accept()
    
    def validate_required_fields(self):
        """Validar que los campos obligatorios estén completos"""
        errors = []
        
        # Nombre obligatorio
        if len(self.nombre_edit.text().strip()) < 2:
            errors.append("• El nombre debe tener al menos 2 caracteres")
        
        # Validar email si se proporciona
        email = self.email_edit.text().strip()
        if email and "@" not in email:
            errors.append("• El formato del email no es válido")
        
        # Mostrar errores si existen
        if errors:
            QMessageBox.warning(
                self,
                "Campos Incompletos",
                "Por favor corrija los siguientes errores:\n\n" + "\n".join(errors)
            )
            return False
        
        return True
    
    def get_user_data(self):
        """Obtener los datos del usuario creado"""
        return self.user_data


class EditUserDialog(NewUserDialog):
    """
    Diálogo para editar un usuario existente.
    Hereda de NewUserDialog y precarga los datos.
    """
    
    def __init__(self, user_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Editar Usuario - Sistema VNG")
        
        # Cambiar texto del botón
        self.btn_create.setText("Guardar Cambios")
        
        # Precargar datos
        self.load_user_data(user_data)
    
    def load_user_data(self, data):
        """Cargar datos existentes del usuario"""
        try:
            if data.get('nombre'):
                self.nombre_edit.setText(data['nombre'])
            
            if data.get('rut_id'):
                self.rut_edit.setText(data['rut_id'])
            
            if data.get('edad'):
                self.edad_spin.setValue(data['edad'])
            
            if data.get('genero'):
                index = self.genero_combo.findText(data['genero'])
                if index >= 0:
                    self.genero_combo.setCurrentIndex(index)
            
            if data.get('fecha_nacimiento'):
                fecha = QDate.fromString(data['fecha_nacimiento'], "yyyy-MM-dd")
                if fecha.isValid():
                    self.fecha_nacimiento.setDate(fecha)
            
            if data.get('medico_tratante'):
                self.medico_edit.setText(data['medico_tratante'])
            
            if data.get('diagnostico'):
                self.diagnostico_edit.setText(data['diagnostico'])
            
            if data.get('historia_clinica'):
                self.historia_text.setPlainText(data['historia_clinica'])
            
            if data.get('institucion'):
                self.institucion_edit.setText(data['institucion'])
            
            if data.get('numero_estudio'):
                self.numero_estudio_edit.setText(data['numero_estudio'])
            
            if data.get('observaciones'):
                self.observaciones_text.setPlainText(data['observaciones'])
            
            if data.get('telefono'):
                self.telefono_edit.setText(data['telefono'])
            
            if data.get('email'):
                self.email_edit.setText(data['email'])
                
        except Exception as e:
            print(f"Error cargando datos de usuario: {e}")
    
    def create_user(self):
        """Sobrescribir para guardar cambios en lugar de crear"""
        # Validar campos obligatorios
        if not self.validate_required_fields():
            return
        
        # Recopilar datos actualizados
        self.user_data = {
            "nombre": self.nombre_edit.text().strip(),
            "rut_id": self.rut_edit.text().strip() or None,
            "edad": self.edad_spin.value(),
            "genero": self.genero_combo.currentText() if self.genero_combo.currentIndex() > 0 else None,
            "fecha_nacimiento": self.fecha_nacimiento.date().toString("yyyy-MM-dd"),
            "medico_tratante": self.medico_edit.text().strip() or None,
            "diagnostico": self.diagnostico_edit.text().strip() or None,
            "historia_clinica": self.historia_text.toPlainText().strip() or None,
            "institucion": self.institucion_edit.text().strip() or None,
            "numero_estudio": self.numero_estudio_edit.text().strip() or None,
            "observaciones": self.observaciones_text.toPlainText().strip() or None,
            "telefono": self.telefono_edit.text().strip() or None,
            "email": self.email_edit.text().strip() or None,
            "ultima_modificacion": time.time(),
            "modificado_por": "Sistema VNG"
        }
        
        # Confirmar cambios
        reply = QMessageBox.question(
            self,
            "Confirmar Cambios",
            f"¿Guardar cambios para:\n\n{self.user_data['nombre']}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self.accept()