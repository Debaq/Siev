from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton)
from PySide6.QtCore import Qt


class TrackingCalibrationDialog(QDialog):
    """Ventana para decidir si calibrar seguimiento primero"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración de Seguimiento")
        self.setModal(True)
        self.setFixedSize(400, 200)
        self.user_choice = None
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        title = QLabel("Configuración de Seguimiento Ocular")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        message = QLabel(
            "Para una calibración precisa se recomienda\n"
            "ajustar primero el seguimiento ocular con los sliders."
        )
        message.setAlignment(Qt.AlignCenter)
        message.setStyleSheet("font-size: 12px; color: #666; margin-bottom: 15px;")
        layout.addWidget(message)
        
        button_layout = QHBoxLayout()
        
        self.continue_btn = QPushButton("Calibrar Seguimiento Primero")
        self.continue_btn.clicked.connect(self.choose_tracking_first)
        self.continue_btn.setStyleSheet("""
            QPushButton {
                font-size: 12px; padding: 10px 15px; background-color: #4CAF50;
                color: white; border: none; border-radius: 4px;
            }
            QPushButton:hover { background-color: #45a049; }
        """)
        
        self.skip_btn = QPushButton("Saltar a Calibración")
        self.skip_btn.clicked.connect(self.skip_to_calibration)
        self.skip_btn.setStyleSheet("""
            QPushButton {
                font-size: 12px; padding: 10px 15px; background-color: #f44336;
                color: white; border: none; border-radius: 4px;
            }
            QPushButton:hover { background-color: #da190b; }
        """)
        
        button_layout.addWidget(self.continue_btn)
        button_layout.addWidget(self.skip_btn)
        layout.addLayout(button_layout)
    
    def choose_tracking_first(self):
        self.user_choice = "tracking_first"
        self.accept()
    
    def skip_to_calibration(self):
        self.user_choice = "skip_to_calibration"
        self.accept()
    
    def get_user_choice(self):
        return self.user_choice