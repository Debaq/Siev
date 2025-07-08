from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QProgressBar, QFrame)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont
import time


class CalibrationDialog(QDialog):
    """
    Ventana modal para calibración con comunicación DIRECTA al CalibrationManager.
    """
    
    # Señales para comunicar con el sistema principal
    calibration_finished = Signal(bool)  # True si exitosa, False si cancelada
    
    # Configuración de tiempos
    RECORDING_TIME_PER_LED = 6.0
    GRAPH_MARGIN_DEGREES = 20.0
    
    def __init__(self, calibration_manager, parent_window=None):
        super().__init__(parent_window)
        
        # Referencias directas - SIN CONTROLLER
        self.calibration_manager = calibration_manager
        self.parent_window = parent_window
        
        # Configurar ventana modal
        self.setModal(True)
        self.setWindowTitle("Calibración del Sistema")
        self.setFixedSize(400, 300)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint)
        
        # Variables de estado
        self.current_step = 0
        self.recording_timer = None
        self.countdown_time = 0
        
        # Variables para captura de datos
        self.capturing_data = False
        self.captured_positions = []
        self.current_led = None
        
        # Configurar UI
        self.setup_ui()
        
        # Mostrar primer paso
        self.show_step_1()
    
    def setup_ui(self):
        """Configura la interfaz de usuario."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Título principal
        self.title_label = QLabel("Calibración del Sistema")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        
        # Área de contenido principal
        self.content_label = QLabel()
        self.content_label.setWordWrap(True)
        self.content_label.setAlignment(Qt.AlignCenter)
        content_font = QFont()
        content_font.setPointSize(12)
        self.content_label.setFont(content_font)
        self.content_label.setMinimumHeight(120)
        layout.addWidget(self.content_label)
        
        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Label de tiempo restante
        self.time_label = QLabel()
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setVisible(False)
        layout.addWidget(self.time_label)
        
        # Label para mostrar datos capturados
        self.data_label = QLabel()
        self.data_label.setAlignment(Qt.AlignCenter)
        self.data_label.setVisible(False)
        self.data_label.setStyleSheet("color: green; font-size: 10px;")
        layout.addWidget(self.data_label)
        
        # Botones
        button_layout = QHBoxLayout()
        
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.clicked.connect(self.cancel_calibration)
        button_layout.addWidget(self.cancel_button)
        
        button_layout.addStretch()
        
        self.continue_button = QPushButton("Continuar")
        self.continue_button.clicked.connect(self.continue_step)
        self.continue_button.setDefault(True)
        button_layout.addWidget(self.continue_button)
        
        layout.addLayout(button_layout)
    
    def show_step_1(self):
        """Paso 1: Preparación para LED izquierdo."""
        self.current_step = 1
        self.title_label.setText("Calibración - Paso 1 de 2")
        self.content_label.setText(
            "Se encenderá un LED verde a su izquierda.\n\n"
            "Cuando presione 'Continuar':\n"
            "• El LED se encenderá\n"
            "• Mire directamente al LED verde\n"
            "• Mantenga la mirada fija durante la grabación\n"
            "• No mueva la cabeza\n\n"
            "¿Está listo para comenzar?"
        )
        
        self.continue_button.setText("Continuar")
        self.continue_button.setEnabled(True)
        self._hide_progress_ui()
    
    def show_step_2(self):
        """Paso 2: Grabando LED izquierdo."""
        self.current_step = 2
        self.current_led = 'left'
        self.title_label.setText("Calibración - LED Izquierdo")
        self.content_label.setText(
            "¡MIRE EL LED VERDE FÍSICO!\n\n"
            "El LED está encendido.\n"
            "Mantenga la mirada fija en el LED verde.\n"
            "No mueva la cabeza ni los ojos.\n\n"
            "Capturando posiciones oculares..."
        )
        
        self.continue_button.setEnabled(False)
        self._show_progress_ui()
        
        # ENCENDER LED DIRECTAMENTE
        print("=== ENCENDIENDO LED IZQUIERDO ===")
        success = self.calibration_manager.start_left_led_capture()
        if not success:
            self.show_error("Error encendiendo LED izquierdo")
            return
        
        # Inicializar captura de datos
        self.captured_positions = []
        self.capturing_data = True
        
        # Iniciar timer de grabación
        self.start_recording_timer()
    
    def show_step_3(self):
        """Paso 3: Preparación para LED derecho."""
        self.current_step = 3
        self.title_label.setText("Calibración - Paso 2 de 2")
        self.content_label.setText(
            "Excelente. Ahora se encenderá el LED derecho.\n\n"
            "Cuando presione 'Continuar':\n"
            "• El LED derecho se encenderá\n"
            "• Mire directamente al LED verde\n"
            "• Mantenga la mirada fija durante la grabación\n"
            "• No mueva la cabeza\n\n"
            "¿Está listo para el segundo paso?"
        )
        
        self.continue_button.setText("Continuar")
        self.continue_button.setEnabled(True)
        self._hide_progress_ui()
    
    def show_step_4(self):
        """Paso 4: Grabando LED derecho."""
        self.current_step = 4
        self.current_led = 'right'
        self.title_label.setText("Calibración - LED Derecho")
        self.content_label.setText(
            "¡MIRE EL LED VERDE FÍSICO!\n\n"
            "El LED derecho está encendido.\n"
            "Mantenga la mirada fija en el LED verde.\n"
            "No mueva la cabeza ni los ojos.\n\n"
            "Capturando posiciones oculares..."
        )
        
        self.continue_button.setEnabled(False)
        self._show_progress_ui()
        
        # ENCENDER LED DIRECTAMENTE
        print("=== ENCENDIENDO LED DERECHO ===")
        success = self.calibration_manager.start_right_led_capture()
        if not success:
            self.show_error("Error encendiendo LED derecho")
            return
        
        # Inicializar captura de datos
        self.captured_positions = []
        self.capturing_data = True
        
        # Iniciar timer de grabación
        self.start_recording_timer()
    
    def show_step_5(self):
        """Paso 5: Procesando calibración."""
        self.current_step = 5
        self.title_label.setText("Procesando Calibración")
        self.content_label.setText(
            "Calculando parámetros de calibración...\n\n"
            "Por favor espere un momento."
        )
        
        self.continue_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Modo indeterminado
        self.time_label.setVisible(False)
        self.data_label.setVisible(False)
        
        # CALCULAR CALIBRACIÓN DIRECTAMENTE
        print("=== CALCULANDO CALIBRACIÓN ===")
        QTimer.singleShot(500, self.calculate_calibration)
    
    def calculate_calibration(self):
        """Ejecuta el cálculo de calibración."""
        success = self.calibration_manager.calculate_calibration()
        
        if success:
            QTimer.singleShot(1500, self.show_step_6)
        else:
            self.show_error("Error calculando parámetros de calibración")
    
    def show_step_6(self):
        """Paso 6: Calibración completada."""
        self.current_step = 6
        self.title_label.setText("¡Calibración Exitosa!")
        self.content_label.setText(
            "El sistema ha sido calibrado correctamente.\n\n"
            "• Los gráficos ahora mostrarán datos en grados\n"
            "• Los límites se han ajustado automáticamente\n"
            "• El sistema está listo para usar\n\n"
            "Presione 'Finalizar' para continuar."
        )
        
        self.continue_button.setText("Finalizar")
        self.continue_button.setEnabled(True)
        self._hide_progress_ui()
    
    def show_error(self, message):
        """Muestra un error en la calibración."""
        self.current_step = -1
        self.title_label.setText("Error en Calibración")
        self.content_label.setText(
            f"Se produjo un error durante la calibración:\n\n"
            f"{message}\n\n"
            "Puede intentar nuevamente o cancelar."
        )
        
        self.continue_button.setText("Reintentar")
        self.continue_button.setEnabled(True)
        self._hide_progress_ui()
    
    def _show_progress_ui(self):
        """Muestra elementos de progreso."""
        self.progress_bar.setVisible(True)
        self.time_label.setVisible(True)
        self.data_label.setVisible(True)
    
    def _hide_progress_ui(self):
        """Oculta elementos de progreso."""
        self.progress_bar.setVisible(False)
        self.time_label.setVisible(False)
        self.data_label.setVisible(False)
    
    def start_recording_timer(self):
        """Inicia el timer para la grabación."""
        self.countdown_time = int(self.RECORDING_TIME_PER_LED)
        self.progress_bar.setRange(0, self.countdown_time)
        self.progress_bar.setValue(0)
        
        self.recording_timer = QTimer()
        self.recording_timer.timeout.connect(self.update_recording_progress)
        self.recording_timer.start(1000)  # Cada segundo
        
        self.update_recording_progress()
    
    def update_recording_progress(self):
        """Actualiza el progreso y captura posiciones."""
        if self.countdown_time > 0:
            self.time_label.setText(f"Tiempo restante: {self.countdown_time} segundos")
            self.progress_bar.setValue(int(self.RECORDING_TIME_PER_LED) - self.countdown_time)
            
            # CAPTURAR POSICIÓN ACTUAL DIRECTAMENTE
            if self.capturing_data:
                self.capture_current_position()
            
            self.countdown_time -= 1
        else:
            # Tiempo completado
            self.recording_timer.stop()
            self.time_label.setText("¡Grabación completada!")
            self.progress_bar.setValue(int(self.RECORDING_TIME_PER_LED))
            
            # Finalizar captura de datos
            self.finish_data_capture()
            
            # Avanzar al siguiente paso
            QTimer.singleShot(1000, self.auto_continue)
    
    def capture_current_position(self):
        """Captura la posición actual DIRECTAMENTE del parent_window."""
        if not self.parent_window or not hasattr(self.parent_window, 'pos_eye'):
            print("ERROR: No hay acceso a posiciones oculares")
            return
        
        try:
            # ACCESO DIRECTO A pos_eye
            pos_eye = self.parent_window.pos_eye
            
            if not pos_eye or len(pos_eye) < 2:
                print("WARNING: pos_eye no tiene datos suficientes")
                return
            
            # Según estructura: pos_eye[0] = derecho, pos_eye[1] = izquierdo
            right_eye = pos_eye[0] if pos_eye[0] and len(pos_eye[0]) >= 2 else None
            left_eye = pos_eye[1] if pos_eye[1] and len(pos_eye[1]) >= 2 else None
            
            # Crear registro
            position_record = {
                'timestamp': time.time(),
                'left_eye': [float(left_eye[0]), float(left_eye[1])] if left_eye else None,
                'right_eye': [float(right_eye[0]), float(right_eye[1])] if right_eye else None
            }
            
            self.captured_positions.append(position_record)
            
            # Actualizar UI
            total_captured = len(self.captured_positions)
            left_detected = sum(1 for p in self.captured_positions if p['left_eye'] is not None)
            right_detected = sum(1 for p in self.captured_positions if p['right_eye'] is not None)
            
            self.data_label.setText(
                f"Muestras: {total_captured} | Izq: {left_detected} | Der: {right_detected}"
            )
            
            print(f"Capturada muestra {total_captured} para LED {self.current_led}")
            
        except Exception as e:
            print(f"Error capturando posición: {e}")
    
    def finish_data_capture(self):
        """Finaliza la captura y envía datos al manager."""
        self.capturing_data = False
        
        if not self.captured_positions:
            print(f"ERROR: No se capturaron datos para LED {self.current_led}")
            self.data_label.setText("⚠ No se capturaron datos")
            return
        
        print(f"Finalizando captura LED {self.current_led}: {len(self.captured_positions)} muestras")
        
        # APAGAR LED DIRECTAMENTE
        if self.current_led == 'left':
            self.calibration_manager.finish_left_led_capture()
        elif self.current_led == 'right':
            self.calibration_manager.finish_right_led_capture()
        
        # PROCESAR DATOS DIRECTAMENTE
        success = self.calibration_manager.process_led_data(self.current_led, self.captured_positions)
        
        if success:
            self.data_label.setText(f"✓ {len(self.captured_positions)} muestras procesadas")
        else:
            self.show_error(f"Error procesando datos del LED {self.current_led}")
    
    def auto_continue(self):
        """Continúa automáticamente después de completar la grabación."""
        if self.current_step == 2:
            # Terminó LED izquierdo
            self.show_step_3()
        elif self.current_step == 4:
            # Terminó LED derecho
            self.show_step_5()
    
    def continue_step(self):
        """Maneja el clic en el botón continuar."""
        if self.current_step == 1:
            self.show_step_2()
        elif self.current_step == 3:
            self.show_step_4()
        elif self.current_step == 6:
            self.calibration_finished.emit(True)
            self.accept()
        elif self.current_step == -1:
            self.show_step_1()
    
    def cancel_calibration(self):
        """Cancela la calibración."""
        if self.recording_timer:
            self.recording_timer.stop()
        
        self.capturing_data = False
        self.calibration_finished.emit(False)
        self.reject()
    
    def closeEvent(self, event):
        """Maneja el cierre de la ventana."""
        self.cancel_calibration()
        event.accept()