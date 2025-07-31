from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import QApplication

class VideoFullscreenWidget(QWidget):
    """Ventana separada para mostrar video en pantalla completa"""
    
    def __init__(self, video_widget=None):
        super().__init__()
        self.video_widget = video_widget
        self.setup_window()
        self.setup_ui()
        
    def setup_window(self):
        """Configurar ventana fullscreen en pantalla externa si existe"""
        # Detectar pantallas disponibles
        screens = QApplication.screens()
        
        if len(screens) > 1:
            # Usar pantalla secundaria
            target_screen = screens[1]
            print(f"Ventana video fullscreen - Usando pantalla secundaria: {target_screen.name()}")
        else:
            # Usar pantalla principal
            target_screen = screens[0]
            print(f"Ventana video fullscreen - Usando pantalla principal: {target_screen.name()}")
        
        # Configurar ventana
        self.setWindowTitle("Video - Pantalla Completa")
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        
        # Posicionar en la pantalla objetivo
        geometry = target_screen.geometry()
        self.setGeometry(geometry)
        self.showFullScreen()
        
        print(f"Pantalla video: {geometry.width()}x{geometry.height()} px")
        
    def setup_ui(self):
        """Configurar interfaz"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Frame de video (ocupa la mayor parte)
        self.video_frame = QLabel()
        self.video_frame.setStyleSheet("background-color: black;")
        self.video_frame.setAlignment(Qt.AlignCenter)
        self.video_frame.setScaledContents(True)
        layout.addWidget(self.video_frame, stretch=1)
        
        # Contador de tiempo (esquina superior derecha)
        self.time_label = QLabel("00:00 / 05:00")
        self.time_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 180);
                color: white;
                font-size: 24px;
                font-weight: bold;
                padding: 10px 15px;
                border-radius: 8px;
                margin: 20px;
            }
        """)
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setFixedSize(200, 60)
        
        # Posicionar el label de tiempo en esquina superior derecha
        self.time_label.setParent(self)
        self.time_label.move(self.width() - 220, 20)
        
        # Punto verde central (inicialmente oculto)
        self.green_dot = QLabel()
        self.green_dot.setStyleSheet("""
            QLabel {
                background-color: #00FF00;
                border-radius: 8px;
                border: 2px solid #FFFFFF;
            }
        """)
        self.green_dot.setFixedSize(16, 16)
        self.green_dot.setParent(self)
        self.green_dot.hide()
        
    def resizeEvent(self, event):
        """Reposicionar elementos al cambiar tamaño"""
        super().resizeEvent(event)
        if hasattr(self, 'time_label'):
            self.time_label.move(self.width() - 220, 20)
        if hasattr(self, 'green_dot'):
            # Posicionar punto verde en el centro horizontal, margen superior
            self.green_dot.move(self.width() // 2 - 8, 30)
    
    def update_video_frame(self, pixmap):
        """Actualizar frame de video"""
        if isinstance(pixmap, QPixmap):
            self.video_frame.setPixmap(pixmap)
    
    def update_time_display(self, time_text):
        """Actualizar contador de tiempo"""
        self.time_label.setText(time_text)
    
    def show_green_dot(self):
        """Mostrar punto verde en el centro superior"""
        if hasattr(self, 'green_dot'):
            self.green_dot.move(self.width() // 2 - 8, 30)
            self.green_dot.show()
    
    def hide_green_dot(self):
        """Ocultar punto verde"""
        if hasattr(self, 'green_dot'):
            self.green_dot.hide()
    
    def mouseDoubleClickEvent(self, event):
        """Cerrar ventana con doble click"""
        self.close()