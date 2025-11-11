from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QScreen
from PySide6.QtWidgets import QApplication

class StimulusWindow(QWidget):
    """Ventana fullscreen para mostrar estímulos visuales"""
    
    stimulus_closed = Signal()
    
    def __init__(self, stimulus_type="seguimiento_lento"):
        super().__init__()
        self.stimulus_type = stimulus_type
        self.setup_window()
        self.setup_ui()
        
    def setup_window(self):
        """Configurar ventana fullscreen en pantalla secundaria si existe"""
        # Detectar pantallas disponibles
        screens = QApplication.screens()
        
        if len(screens) > 1:
            # Usar pantalla secundaria
            target_screen = screens[1]
            print(f"Usando pantalla secundaria: {target_screen.name()}")
        else:
            # Usar pantalla principal
            target_screen = screens[0]
            print(f"Usando pantalla principal: {target_screen.name()}")
        
        # Configurar ventana
        self.setWindowTitle(f"Estímulos - {self.stimulus_type}")
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        
        # Posicionar en la pantalla objetivo
        geometry = target_screen.geometry()
        self.setGeometry(geometry)
        self.showFullScreen()
        
        # Mostrar info de la pantalla
        print(f"Pantalla: {geometry.width()}x{geometry.height()} px")
        
    def setup_ui(self):
        """Configurar interfaz básica"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Área principal para estímulos (ocupa todo el espacio)
        self.stimulus_area = QWidget()
        self.stimulus_area.setStyleSheet("background-color: black;")
        layout.addWidget(self.stimulus_area, stretch=1)
        
        # Área de controles (abajo, inicialmente oculta)
        self.controls_area = QWidget()
        self.controls_area.setFixedHeight(80)
        self.controls_area.setStyleSheet("""
            QWidget { 
                background-color: rgba(50, 50, 50, 200); 
                border-top: 2px solid #555; 
            }
        """)
        self.setup_controls()
        layout.addWidget(self.controls_area)
        
        # Inicialmente ocultar controles
        self.controls_area.hide()
        
    def setup_controls(self):
        """Configurar controles básicos"""
        layout = QHBoxLayout(self.controls_area)
        
        # Info del estímulo
        info_label = QLabel(f"Estímulo: {self.stimulus_type}")
        info_label.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        layout.addWidget(info_label)
        
        layout.addStretch()
        
        # Placeholder para controles específicos
        controls_label = QLabel("Controles aparecerán aquí")
        controls_label.setStyleSheet("color: white; font-size: 12px;")
        layout.addWidget(controls_label)
        
        layout.addStretch()
        
        # Info de pantalla
        screens = QApplication.screens()
        screen_info = f"Pantallas: {len(screens)}"
        if len(screens) > 1:
            screen_info += " (Secundaria activa)"
        else:
            screen_info += " (Principal activa)"
            
        screen_label = QLabel(screen_info)
        screen_label.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(screen_label)
    
    def toggle_controls(self):
        """Mostrar/ocultar controles"""
        if self.controls_area.isVisible():
            self.controls_area.hide()
        else:
            self.controls_area.show()
    
    def keyPressEvent(self, event):
        """Manejar teclas"""
        if event.key() == Qt.Key_Escape:
            self.close_stimulus()
        elif event.key() == Qt.Key_C:
            self.toggle_controls()
        elif event.key() == Qt.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
    
    def close_stimulus(self):
        """Cerrar ventana de estímulos"""
        print("Cerrando ventana de estímulos")
        self.stimulus_closed.emit()
        self.close()


class StimulusManager:
    """Gestor para ventanas de estímulos"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.stimulus_window = None
        self.current_stimulus_type = None
        
    def detect_screens(self):
        """Detectar y mostrar información de pantallas"""
        screens = QApplication.screens()
        print(f"\n=== DETECCIÓN DE PANTALLAS ===")
        print(f"Total de pantallas: {len(screens)}")
        
        for i, screen in enumerate(screens):
            geometry = screen.geometry()
            print(f"Pantalla {i+1}: {screen.name()}")
            print(f"  Resolución: {geometry.width()}x{geometry.height()}")
            print(f"  Posición: ({geometry.x()}, {geometry.y()})")
            print(f"  DPI: {screen.logicalDotsPerInch()}")
            if screen == QApplication.primaryScreen():
                print(f"  ★ PRINCIPAL")
        print("="*35)
        
        return len(screens) > 1
    
    def open_stimulus_window(self, stimulus_type):
        """Abrir ventana de estímulos"""
        # Cerrar ventana anterior si existe
        self.close_stimulus_window()
        
        # Detectar pantallas
        has_secondary = self.detect_screens()
        
        # Crear nueva ventana
        self.current_stimulus_type = stimulus_type
        self.stimulus_window = StimulusWindow(stimulus_type)
        self.stimulus_window.stimulus_closed.connect(self.on_stimulus_closed)
        
        print(f"Ventana de estímulos abierta: {stimulus_type}")
        return True
    
    def close_stimulus_window(self):
        """Cerrar ventana de estímulos"""
        if self.stimulus_window:
            self.stimulus_window.close()
            self.stimulus_window = None
            self.current_stimulus_type = None
            print("Ventana de estímulos cerrada")
    
    def on_stimulus_closed(self):
        """Manejar cierre de ventana de estímulos"""
        self.stimulus_window = None
        self.current_stimulus_type = None
        
        # Notificar a ventana principal
        if hasattr(self.main_window, 'on_stimulus_window_closed'):
            self.main_window.on_stimulus_window_closed()
    
    def is_stimulus_active(self):
        """Verificar si hay ventana de estímulos activa"""
        return self.stimulus_window is not None


# Modificaciones para MainWindow (agregar al final de __init__):

def init_stimulus_system(self):
    """Inicializar sistema de estímulos - AGREGAR AL FINAL DE __init__"""
    try:
        self.stimulus_manager = StimulusManager(self)
        
        # Variables de estado para el flujo de pruebas
        self.test_preparation_mode = False
        self.test_ready_to_start = False
        
        print("Sistema de estímulos inicializado")
    except Exception as e:
        print(f"Error inicializando sistema de estímulos: {e}")
        self.stimulus_manager = None

def setup_right_click_trigger(self):
    """Configurar click derecho global - AGREGAR AL FINAL DE __init__"""
    try:
        # Instalar filtro de eventos para capturar click derecho
        self.installEventFilter(self)
        print("Trigger de click derecho configurado")
    except Exception as e:
        print(f"Error configurando click derecho: {e}")

def eventFilter(self, obj, event):
    """Filtro de eventos para click derecho global"""
    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QMouseEvent
    
    if event.type() == QEvent.MouseButtonPress:
        if isinstance(event, QMouseEvent) and event.button() == Qt.RightButton:
            # Click derecho detectado - triggear botón actual
            self.trigger_current_button()
            return True
    
    return super().eventFilter(obj, event)

def trigger_current_button(self):
    """Triggear el botón principal según el estado actual"""
    if hasattr(self.ui, 'btn_start'):
        print("🖱️ Click derecho - Triggeando botón principal")
        self.ui.btn_start.click()

def update_main_button_state(self):
    """Actualizar estado y texto del botón principal"""
    if not hasattr(self.ui, 'btn_start'):
        return
        
    # Determinar si estamos en una prueba que requiere estímulos
    needs_stimulus = hasattr(self, 'current_protocol') and self.current_protocol in [
        'sacadas', 'seguimiento_lento', 'ng_optocinetico'
    ]
    
    if needs_stimulus:
        if not self.test_preparation_mode and not self.is_recording:
            # Estado inicial: Preparar Prueba
            self.ui.btn_start.setText("Preparar Prueba")
            self.ui.btn_start.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3; color: white; font-weight: bold;
                    font-size: 14px; padding: 10px; border: none; border-radius: 5px;
                }
                QPushButton:hover { background-color: #1976D2; }
            """)
        elif self.test_preparation_mode and not self.is_recording:
            # Estado preparado: Iniciar Prueba
            self.ui.btn_start.setText("Iniciar Prueba")
            self.ui.btn_start.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50; color: white; font-weight: bold;
                    font-size: 14px; padding: 10px; border: none; border-radius: 5px;
                }
                QPushButton:hover { background-color: #45a049; }
            """)
        elif self.is_recording:
            # Estado grabando: Detener
            self.ui.btn_start.setText("Detener")
            self.ui.btn_start.setStyleSheet("""
                QPushButton {
                    background-color: #f44336; color: white; font-weight: bold;
                    font-size: 14px; padding: 10px; border: none; border-radius: 5px;
                }
                QPushButton:hover { background-color: #da190b; }
            """)
    else:
        # Pruebas normales (sin estímulos)
        if self.is_recording:
            self.ui.btn_start.setText("Detener")
            self.ui.btn_start.setStyleSheet("""
                QPushButton {
                    background-color: #f44336; color: white; font-weight: bold;
                    font-size: 14px; padding: 10px; border: none; border-radius: 5px;
                }
                QPushButton:hover { background-color: #da190b; }
            """)
        else:
            self.ui.btn_start.setText("Iniciar")
            self.ui.btn_start.setStyleSheet("")

def on_stimulus_window_closed(self):
    """Manejar cierre de ventana de estímulos"""
    print("Ventana de estímulos cerrada - Regresando a estado inicial")
    self.test_preparation_mode = False
    self.test_ready_to_start = False
    self.update_main_button_state()

# Modificar el método toggle_recording existente:

def toggle_recording_with_stimulus(self):
    """Nuevo toggle_recording que maneja estímulos"""
    # Determinar si necesita estímulos
    needs_stimulus = hasattr(self, 'current_protocol') and self.current_protocol in [
        'sacadas', 'seguimiento_lento', 'ng_optocinetico'
    ]
    
    if needs_stimulus:
        if not self.test_preparation_mode and not self.is_recording:
            # Paso 1: Preparar Prueba - Abrir ventana de estímulos
            print(f"=== PREPARANDO PRUEBA: {self.current_protocol} ===")
            
            if self.stimulus_manager and self.stimulus_manager.open_stimulus_window(self.current_protocol):
                self.test_preparation_mode = True
                self.test_ready_to_start = True
                self.update_main_button_state()
                print("Ventana de estímulos abierta - Lista para iniciar")
            else:
                print("Error abriendo ventana de estímulos")
                
        elif self.test_preparation_mode and not self.is_recording:
            # Paso 2: Iniciar Prueba - Comenzar grabación
            print("=== INICIANDO PRUEBA CON ESTÍMULOS ===")
            self.start_calibration_phase()  # Llamar al método original
            
        elif self.is_recording:
            # Paso 3: Detener - Parar todo
            print("=== DETENIENDO PRUEBA ===")
            self.stop_recording()
            if self.stimulus_manager:
                self.stimulus_manager.close_stimulus_window()
            self.test_preparation_mode = False
            self.test_ready_to_start = False
            
    else:
        # Pruebas normales sin estímulos
        if not self.is_recording and not self.is_calibrating:
            self.start_calibration_phase()
        else:
            self.stop_recording()
    
    # Actualizar estado del botón
    self.update_main_button_state()