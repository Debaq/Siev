from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QRadioButton, QButtonGroup, QCheckBox, QFrame)
from PySide6.QtCore import Qt


class ProtocolSelectionDialog(QDialog):
    """Ventana de selección de protocolo completa - MEJORADA"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Selección de Protocolo")
        self.setModal(True)
        self.setFixedSize(400, 450)  # Aumentado de 350x250 a 400x450
        self.selected_protocol = None
        self.spontaneous_enabled = False
        self.setup_ui()
    
    def setup_ui(self):
        from PySide6.QtWidgets import QRadioButton, QButtonGroup
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Título
        title = QLabel("Seleccione el protocolo de evaluación:")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Grupo de radiobuttons
        self.button_group = QButtonGroup()
        protocols = [
            ("Bitermal Alternada", "bitermal_alternada"),
            ("Monotermal Caliente", "monotermal_caliente"), 
            ("Monotermal Fría", "monotermal_fria"),
            ("Sacadas", "sacadas"),
            ("Seguimiento Lento", "seguimiento_lento"),
            ("NG Optocinético", "ng_optocinetico"),
            ("Sin Protocolo", "sin_protocolo")
        ]
        
        self.protocol_buttons = {}
        for display_name, protocol_id in protocols:
            radio_btn = QRadioButton(display_name)
            radio_btn.setStyleSheet("font-size: 12px; padding: 5px;")
            self.button_group.addButton(radio_btn)
            self.protocol_buttons[radio_btn] = protocol_id
            layout.addWidget(radio_btn)
        
        # Seleccionar primero por defecto
        list(self.protocol_buttons.keys())[0].setChecked(True)
        
        # Separador visual
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("margin: 10px 0px;")
        layout.addWidget(separator)
        
        # Checkbox Espontáneo
        self.spontaneous_checkbox = QCheckBox("Iniciar con Nistagmo Espontáneo")
        self.spontaneous_checkbox.setStyleSheet("font-size: 12px; padding: 5px; font-weight: bold; color: #2196F3;")
        self.spontaneous_checkbox.setChecked(False)
        layout.addWidget(self.spontaneous_checkbox)
        
        layout.addStretch()
        
        # Botón continuar
        self.accept_btn = QPushButton("Continuar")
        self.accept_btn.clicked.connect(self.accept_selection)
        self.accept_btn.setStyleSheet("""
            QPushButton {
                font-size: 12px; padding: 10px 20px; background-color: #4CAF50;
                color: white; border: none; border-radius: 4px; min-height: 20px;
            }
            QPushButton:hover { background-color: #45a049; }
        """)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.accept_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
    
    def accept_selection(self):
        for radio_btn, protocol_id in self.protocol_buttons.items():
            if radio_btn.isChecked():
                self.selected_protocol = protocol_id
                break
        
        self.spontaneous_enabled = self.spontaneous_checkbox.isChecked()
        self.accept()
    
    def get_selected_protocol(self):
        return self.selected_protocol
    
    def is_spontaneous_enabled(self):
        return self.spontaneous_enabled