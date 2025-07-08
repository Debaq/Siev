from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QProgressBar, QFrame)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QPixmap, QPainter, QBrush, QColor
import time


class CalibrationDialog(QDialog):
    """
    Ventana modal para guiar al usuario a través del proceso de calibración.
    """
    
    # Señales para comunicar con el sistema principal
    step_completed = Signal()  # Usuario presionó continuar
    calibration_finished = Signal(bool)  # True si exitosa, False si cancelada
    
    # Configuración de tiempos - AJUSTADO AL TIMING REAL
    RECORDING_TIME_PER_LED = 6.0  # segundos totales por LED (3s preparación + 1s setup + 2s grabación)
    GRAPH_MARGIN_DEGREES = 20.0   # grados adicionales para límites del gráfico
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configurar ventana modal
        self.setModal(True)
        self.setWindowTitle("Calibración del Sistema")
        self.setFixedSize(400, 300)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint)
        
        # Variables de estado
        self.current_step = 0
        self.recording_timer = None
        self.countdown_time = 0
        
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
        
        # Barra de progreso (oculta inicialmente)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Label de tiempo restante
        self.time_label = QLabel()
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setVisible(False)
        layout.addWidget(self.time_label)
        
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
    
    def set_led_color(self, color_name):
        """
        Cambia el color del indicador LED.
        
        Args:
            color_name: 'green', 'red', 'gray', 'yellow'
        """
        colors = {
            'green': '#4CAF50',
            'red': '#F44336', 
            'gray': '#9E9E9E',
            'yellow': '#FFC107',
            'blue': '#2196F3'
        }
        
        color = colors.get(color_name, '#9E9E9E')
        self.led_indicator.setStyleSheet(f"""
            QLabel {{
                border: 2px solid #333;
                border-radius: 25px;
                background-color: {color};
            }}
        """)
    
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
        self.progress_bar.setVisible(False)
        self.time_label.setVisible(False)
    
    def show_step_2(self):
        """Paso 2: Grabando LED izquierdo."""
        self.current_step = 2
        self.title_label.setText("Calibración - LED Izquierdo")
        self.content_label.setText(
            "¡MIRE EL LED VERDE FÍSICO!\n\n"
            "El LED está encendido.\n"
            "Mantenga la mirada fija en el LED verde.\n"
            "No mueva la cabeza ni los ojos.\n\n"
            "Proceso automático en curso..."
        )
        
        self.continue_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.time_label.setVisible(True)
        
        # Iniciar grabación temporizada
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
        self.progress_bar.setVisible(False)
        self.time_label.setVisible(False)
    
    def show_step_4(self):
        """Paso 4: Grabando LED derecho."""
        self.current_step = 4
        self.title_label.setText("Calibración - LED Derecho")
        self.content_label.setText(
            "¡MIRE EL LED VERDE FÍSICO!\n\n"
            "El LED derecho está encendido.\n"
            "Mantenga la mirada fija en el LED verde.\n"
            "No mueva la cabeza ni los ojos.\n\n"
            "Proceso automático en curso..."
        )
        
        self.continue_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.time_label.setVisible(True)
        
        # Iniciar grabación temporizada
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
        
        # Simular tiempo de procesamiento
        QTimer.singleShot(2000, self.show_step_6)
    
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
        self.progress_bar.setVisible(False)
        self.time_label.setVisible(False)
    
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
        self.progress_bar.setVisible(False)
        self.time_label.setVisible(False)
    
    def start_recording_timer(self):
        """Inicia el timer para la grabación temporizada - AJUSTADO A 6 SEGUNDOS."""
        self.countdown_time = int(self.RECORDING_TIME_PER_LED)
        self.progress_bar.setRange(0, self.countdown_time)
        self.progress_bar.setValue(0)
        
        # Timer que se ejecuta cada segundo
        self.recording_timer = QTimer()
        self.recording_timer.timeout.connect(self.update_recording_progress)
        self.recording_timer.start(1000)  # 1000ms = 1 segundo
        
        self.update_recording_progress()
    
    def update_recording_progress(self):
        """Actualiza el progreso de la grabación."""
        if self.countdown_time > 0:
            self.time_label.setText(f"Tiempo restante: {self.countdown_time} segundos")
            self.progress_bar.setValue(int(self.RECORDING_TIME_PER_LED) - self.countdown_time)
            self.countdown_time -= 1
        else:
            # Tiempo completado
            self.recording_timer.stop()
            self.time_label.setText("¡Grabación completada!")
            self.progress_bar.setValue(int(self.RECORDING_TIME_PER_LED))
            
            # Avanzar al siguiente paso
            QTimer.singleShot(1000, self.auto_continue)
    
    def auto_continue(self):
        """Continúa automáticamente después de completar la grabación."""
        if self.current_step == 2:
            # Terminó grabación LED izquierdo
            # Notificar al controller que termine la captura
            if hasattr(self, '_controller_ref'):
                self._controller_ref.auto_continue_from_dialog()
            self.step_completed.emit()
            self.show_step_3()
        elif self.current_step == 4:
            # Terminó grabación LED derecho
            # Notificar al controller que termine la captura
            if hasattr(self, '_controller_ref'):
                self._controller_ref.auto_continue_from_dialog()
            self.step_completed.emit()
            self.show_step_5()
    
    def set_controller_reference(self, controller):
        """Permite al controller registrarse para recibir eventos del timer."""
        self._controller_ref = controller
    
    def continue_step(self):
        """Maneja el clic en el botón continuar."""
        if self.current_step == 1:
            # Usuario listo para LED izquierdo
            self.step_completed.emit()
            self.show_step_2()
            
        elif self.current_step == 3:
            # Usuario listo para LED derecho
            self.step_completed.emit()
            self.show_step_4()
            
        elif self.current_step == 6:
            # Calibración completada
            self.calibration_finished.emit(True)
            self.accept()
            
        elif self.current_step == -1:
            # Reintentar después de error
            self.show_step_1()
    
    def cancel_calibration(self):
        """Cancela la calibración."""
        if self.recording_timer:
            self.recording_timer.stop()
        
        self.calibration_finished.emit(False)
        self.reject()
    
    def closeEvent(self, event):
        """Maneja el cierre de la ventana."""
        self.cancel_calibration()
        event.accept()


class CalibrationController:
    """
    Controlador que coordina entre CalibrationDialog y CalibrationManager.
    Ahora el Dialog controla el timing, el Manager solo ejecuta acciones.
    """
    
    def __init__(self, calibration_manager, parent_window=None):
        self.calibration_manager = calibration_manager
        self.parent_window = parent_window
        self.dialog = None
        
        # Variables para captura de datos
        self.capturing_left_led = False
        self.capturing_right_led = False
        self.captured_positions_left = []
        self.captured_positions_right = []
    
    def start_calibration_process(self):
        """
        Inicia el proceso completo de calibración con ventanas modales.
        
        Returns:
            True si se inició correctamente
        """
        if not self.calibration_manager.start_calibration():
            return False
        
        # Crear y mostrar ventana modal
        self.dialog = CalibrationDialog(self.parent_window)
        
        # Conectar señales
        self.dialog.step_completed.connect(self.handle_step_completed)
        self.dialog.calibration_finished.connect(self.handle_calibration_finished)
        
        # NUEVA CONEXIÓN: Registrar controller en el dialog
        self.dialog.set_controller_reference(self)
        
        # Mostrar ventana modal
        self.dialog.exec()
        
        return True
    
    def handle_step_completed(self):
        """Maneja cuando el usuario completa un paso."""
        if self.dialog.current_step == 2:
            # Paso 2: Iniciando LED izquierdo
            print("Iniciando captura LED izquierdo...")
            success = self.calibration_manager.start_left_led_capture()
            if success:
                self.capturing_left_led = True
                self.captured_positions_left = []
            else:
                self.dialog.show_error("Error encendiendo LED izquierdo")
            
        elif self.dialog.current_step == 4:
            # Paso 4: Iniciando LED derecho
            print("Iniciando captura LED derecho...")
            success = self.calibration_manager.start_right_led_capture()
            if success:
                self.capturing_right_led = True
                self.captured_positions_right = []
            else:
                self.dialog.show_error("Error encendiendo LED derecho")
    
    def capture_during_progress(self):
        """
        Se ejecuta cada segundo durante la barra de progreso.
        Captura posiciones oculares mientras el LED está encendido.
        """
        # Obtener posiciones actuales del sistema de video
        if hasattr(self.parent_window, 'pos_eye'):
            left_eye = self.parent_window.pos_eye[1] if len(self.parent_window.pos_eye) > 1 else None
            right_eye = self.parent_window.pos_eye[0] if len(self.parent_window.pos_eye) > 0 else None
            
            if self.capturing_left_led:
                # Capturando para LED izquierdo
                captured = self.calibration_manager.capture_left_led_position(left_eye, right_eye)
                if captured:
                    self.captured_positions_left.append({
                        'left_eye': left_eye,
                        'right_eye': right_eye,
                        'timestamp': time.time()
                    })
                    print(f"Capturada posición LED izquierdo: {len(self.captured_positions_left)} muestras")
                    
            elif self.capturing_right_led:
                # Capturando para LED derecho
                captured = self.calibration_manager.capture_right_led_position(left_eye, right_eye)
                if captured:
                    self.captured_positions_right.append({
                        'left_eye': left_eye,
                        'right_eye': right_eye,
                        'timestamp': time.time()
                    })
                    print(f"Capturada posición LED derecho: {len(self.captured_positions_right)} muestras")
    
    def auto_continue_from_dialog(self):
        """
        Llamado automáticamente cuando termina la barra de progreso del dialog.
        """
        if self.capturing_left_led:
            # Terminó captura LED izquierdo
            print("Finalizando captura LED izquierdo...")
            success = self.calibration_manager.finish_left_led_capture()
            self.capturing_left_led = False
            
            if not success or len(self.captured_positions_left) == 0:
                self.dialog.show_error("No se capturaron suficientes datos del LED izquierdo")
                return
            
            print(f"LED izquierdo: {len(self.captured_positions_left)} posiciones capturadas")
            
        elif self.capturing_right_led:
            # Terminó captura LED derecho
            print("Finalizando captura LED derecho...")
            success = self.calibration_manager.finish_right_led_capture()
            self.capturing_right_led = False
            
            if not success or len(self.captured_positions_right) == 0:
                self.dialog.show_error("No se capturaron suficientes datos del LED derecho")
                return
            
            print(f"LED derecho: {len(self.captured_positions_right)} posiciones capturadas")
            
            # Ambos LEDs completados, calcular calibración
            calibration_success = self.calibration_manager.calculate_calibration()
            
            if not calibration_success:
                self.dialog.show_error("Error calculando parámetros de calibración")
    
    def handle_calibration_finished(self, success):
        """Maneja cuando termina la calibración."""
        if success:
            print("=== CALIBRACIÓN COMPLETADA EXITOSAMENTE ===")
            summary = self.calibration_manager.get_calibration_summary()
            print(f"Ángulo teórico: {summary['theoretical_angle']:.1f}°")
            print("Factores de conversión calculados:")
            for eye, factors in summary['conversion_factors'].items():
                print(f"  {eye}: {factors['px_per_degree_x']:.2f} px/grado")
            
            # Notificar a la ventana principal para actualizar límites del gráfico
            if hasattr(self.parent_window, 'update_graph_limits_after_calibration'):
                self.parent_window.update_graph_limits_after_calibration()
                
        else:
            print("Calibración cancelada por el usuario")
        
        # Limpiar estado
        self.dialog = None
        self.capturing_left_led = False
        self.capturing_right_led = False
        self.captured_positions_left = []
        self.captured_positions_right = []