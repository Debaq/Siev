from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt

class DemoUI:
    """Demo UI that shows basic functionality"""
    def setupUi(self, window):
        # Widget central
        central_widget = QWidget()
        window.setCentralWidget(central_widget)
        
        # Layout principal
        layout = QVBoxLayout(central_widget)
        
        # Etiqueta de bienvenida
        welcome_text = window.tr("Welcome to {}").format(window.config["app_name"])
        welcome_label = QLabel(welcome_text)
        welcome_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(welcome_label)
        
        # Información de la aplicación
        version_label = QLabel(window.tr("Version: {}").format(window.config["version"]))
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)
        
        # Botón de demo
        demo_button = QPushButton(window.tr("Demo Button"))
        demo_button.clicked.connect(lambda: window.statusBar().showMessage(window.tr("Demo button clicked!")))
        layout.addWidget(demo_button)
        
        # Agregar un poco de espacio
        layout.addStretch()
        
        # Mostrar mensaje en la barra de estado
        window.statusBar().showMessage(window.tr("Demo mode - Create main_ui.py to customize"))
