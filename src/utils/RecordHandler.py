import time
from PySide6.QtCore import QTimer
from utils.data_storage import DataStorage


class RecordingController:
    """
    Controlador optimizado para grabación y visualización de datos oculares.
    Separa completamente el almacenamiento (sin pérdida) de la visualización (optimizada).
    """
    
    def setup_recording(self):
        """Configura los componentes necesarios para la grabación optimizada."""
        # === ALMACENAMIENTO COMPLETO (SIN PÉRDIDA) ===
        self.data_storage = DataStorage(
            auto_save_interval=2.0,  # Guardar cada 2 segundos
            buffer_size=500          # Buffer de 500 puntos antes de escribir
        )
        
        # === CONTROL DE GRABACIÓN ===
        self.is_recording = False
        self.is_calibrating = False
        self.recording_start_time = None
        self.MAX_RECORDING_TIME = 5 * 60  # 5 minutos en segundos
        self.CALIBRATION_TIME = 1  # 1 segundo para calibración
        
        # === TIEMPO DE GRÁFICA (independiente del almacenamiento) ===
        self.graph_time = 0.0
        self.last_update_time = None
        
        # === CONTROL DE ENVÍO A GRÁFICOS (OPTIMIZADO) ===
        self.send_to_graph = False
        self.graph_update_interval = 50  # Enviar a gráfico cada 50ms (20 FPS)
        self.last_graph_update = 0
        self.graph_data_buffer = []  # Buffer temporal para envío a gráficos
        
        # === PROCESADOR DE DATOS OCULARES ===
        self.init_processor()
        
        # === TIMERS OPTIMIZADOS ===
        # Timer principal para tiempo de grabación
        self.recording_timer = QTimer()
        self.recording_timer.timeout.connect(self.update_recording_time)
        self.recording_timer.start(100)  # Actualizar cada 100ms
        
        # Timer optimizado para envío a gráficos (menos frecuente)
        self.graph_timer = QTimer()
        self.graph_timer.timeout.connect(self.flush_graph_buffer)
        self.graph_timer.start(self.graph_update_interval)
        
        # === CONECTAR BOTÓN ===
        self.ui.btn_start.clicked.connect(self.toggle_recording)
        
        # === ESTADO INICIAL ===
        self.ui.lbl_time.setText("00:00 / 05:00")
        
        # === ESTADÍSTICAS DE PERFORMANCE ===
        self.total_data_points = 0
        self.points_sent_to_graph = 0
        self.last_performance_check = time.time()
    
    def init_processor(self):
        """Inicializa el procesador de datos oculares con configuración optimizada."""
        from utils.EyeDataProcessor import EyeDataProcessor
        
        # Inicializar procesador con configuración más ligera
        self.eye_processor = EyeDataProcessor()
        
        # Configuración optimizada para performance
        self.eye_processor.set_filter_strength(0.4)      # Menos filtrado = más rápido
        self.eye_processor.set_interpolation_steps(2)    # Menos interpolación = más rápido
        self.eye_processor.set_history_size(3)           # Buffer más pequeño = más rápido
        
        # Mantener procesamiento de calidad pero más eficiente
        self.eye_processor.set_smoothing_enabled(True)
        self.eye_processor.set_interpolation_enabled(True)
        
        # Configurar Kalman con parámetros más conservadores
        self.eye_processor.set_kalman_enabled(True)
        self.eye_processor.set_kalman_parameters(
            process_noise=0.001,     # Menos agresivo
            measurement_noise=0.3,   # Menos agresivo
            stability_factor=0.01
        )
        
        # Suavizado extra más ligero
        self.eye_processor.set_extra_smoothing(True, buffer_size=5)
    
    def toggle_recording(self):
        """Inicia o detiene la grabación."""
        if not self.is_recording and not self.is_calibrating:
            self.start_calibration()
        else:
            self.stop_recording()
    
    def start_calibration(self):
        """Inicia fase de calibración."""
        print("=== INICIANDO CALIBRACIÓN ===")
        
        self.is_calibrating = True
        self.eye_processor.reset_calibration()
        
        # Inicializar tiempos
        self.recording_start_time = time.time()
        self.last_update_time = time.time()
        self.graph_time = -self.CALIBRATION_TIME
        
        # UI
        self.ui.btn_start.setText("Calibrando...")
        self.ui.btn_start.setEnabled(False)
        self.ui.lbl_time.setText(f"Calibrando: {self.CALIBRATION_TIME}s")
        
        # Habilitar envío a gráficos para calibración
        self.send_to_graph = True
        
        # Programar fin de calibración
        QTimer.singleShot(self.CALIBRATION_TIME * 1000, self.start_recording)
    
    def start_recording(self):
        """Inicia la grabación después de la calibración."""
        print("=== INICIANDO GRABACIÓN ===")
        
        self.is_calibrating = False
        self.is_recording = True
        self.recording_start_time = time.time()
        
        # Reiniciar tiempo de gráfica
        self.graph_time = 0.0
        self.last_update_time = time.time()
        
        # Iniciar almacenamiento de datos
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"vng_recording_{timestamp}.csv"
        self.data_storage.start_recording(filename)
        
        # Limpiar gráfica y configurar para grabación
        self.plot_widget.clear_data()
        self.plot_widget.set_recording_state(True)
        
        # UI
        self.ui.btn_start.setText("Detener")
        self.ui.btn_start.setEnabled(True)
        
        # Resetear estadísticas
        self.total_data_points = 0
        self.points_sent_to_graph = 0
        self.last_performance_check = time.time()
        
        print(f"Grabación iniciada: {filename}")
    
    def stop_recording(self):
        """Detiene la grabación."""
        print("=== DETENIENDO GRABACIÓN ===")
        
        was_recording = self.is_recording
        
        # Estados
        self.is_recording = False
        self.is_calibrating = False
        self.recording_start_time = None
        self.last_update_time = None
        self.graph_time = 0.0
        self.send_to_graph = False
        
        # Detener almacenamiento
        if was_recording:
            self.data_storage.stop_recording()
            
            # Mostrar estadísticas finales
            stats = self.data_storage.get_statistics()
            print(f"Grabación completada:")
            print(f"  - Total de muestras: {stats.get('total_samples', 0)}")
            print(f"  - Duración: {stats.get('duration_seconds', 0):.1f}s")
            print(f"  - Tasa de muestreo: {stats.get('sample_rate', 0):.1f} Hz")
            print(f"  - Detección ojo izq: {stats.get('left_eye_detection_rate', 0):.1f}%")
            print(f"  - Detección ojo der: {stats.get('right_eye_detection_rate', 0):.1f}%")
        
        # Configurar gráfica para exploración
        self.plot_widget.set_recording_state(False)
        
        # UI
        self.ui.btn_start.setText("Iniciar")
        self.ui.lbl_time.setText("00:00 / 05:00")
        
        print("Grabación detenida")
    
    def update_recording_time(self):
        """Actualiza el contador de tiempo (optimizado)."""
        current_time = time.time()
        
        # Actualizar tiempo de gráfica
        if self.last_update_time is not None:
            delta_time = current_time - self.last_update_time
            
            if self.is_recording:
                self.graph_time += delta_time
                
                # Verificar tiempo máximo
                elapsed = current_time - self.recording_start_time
                if elapsed >= self.MAX_RECORDING_TIME:
                    self.stop_recording()
                    return
                
                # Actualizar UI
                minutes = int(self.graph_time // 60)
                seconds = int(self.graph_time % 60)
                self.ui.lbl_time.setText(f"{minutes:02d}:{seconds:02d} / 05:00")
                
            elif self.is_calibrating:
                elapsed_calib = current_time - self.recording_start_time
                remaining = max(0, self.CALIBRATION_TIME - elapsed_calib)
                self.graph_time = -remaining
                self.ui.lbl_time.setText(f"Calibrando: {int(remaining)}s")
        
        # Actualizar tiempo de referencia
        self.last_update_time = current_time
        
        # Mostrar estadísticas de performance cada 5 segundos
        if current_time - self.last_performance_check > 5.0:
            self._show_performance_stats()
            self.last_performance_check = current_time
    
    def set_pos_eye(self, pos):
        """
        Procesa datos de ojos con sistema optimizado.
        Separa almacenamiento de visualización.
        """
        # Guardar datos originales
        self.pos_eye = pos
        
        # Solo procesar si estamos en modo activo
        if not self.send_to_graph:
            return
        
        # Extraer datos
        left_eye = self.pos_eye[1]   # Nota: índices según tu código original
        right_eye = self.pos_eye[0]
        
        # Procesar datos a través del EyeDataProcessor
        processed_points = self.eye_processor.process_eye_data(
            left_eye, 
            right_eye, 
            float(self.pos_hit[0]),  # IMU X 
            float(self.pos_hit[1]),  # IMU Y
            self.graph_time  # Tiempo de gráfica interno
        )
        
        # === ALMACENAMIENTO COMPLETO (TODOS LOS PUNTOS) ===
        if self.is_recording:
            for point in processed_points:
                processed_left, processed_right, imu_x, imu_y, point_time = point
                
                # Almacenar TODOS los datos sin pérdida
                self.data_storage.add_data_point(
                    processed_left, processed_right, imu_x, imu_y, point_time
                )
                self.total_data_points += 1
        
        # === VISUALIZACIÓN OPTIMIZADA (SOLO ALGUNOS PUNTOS) ===
        current_time = time.time()
        
        # Solo enviar a gráficos cada cierto intervalo para reducir carga
        if current_time - self.last_graph_update >= (self.graph_update_interval / 1000.0):
            # Añadir al buffer de gráficos (solo el último punto)
            if processed_points:
                latest_point = processed_points[-1]
                self.graph_data_buffer.append(latest_point)
                self.last_graph_update = current_time
    
    # En RecordHandler.py - modificar flush_graph_buffer()
    def flush_graph_buffer(self):
        """Solo envía datos al gráfico cada X segundos"""
        current_time = time.time()
        
        # Solo actualizar gráficos cada 5 segundos
        if current_time - getattr(self, '_last_batch_update', 0) < 5.0:
            return
        
        if not self.graph_data_buffer:
            return
        
        # Enviar TODOS los datos acumulados de una vez
        for point in self.graph_data_buffer:
            processed_left, processed_right, imu_x, imu_y, point_time = point
            self.plot_widget.add_data_point(
                processed_left, processed_right, imu_x, imu_y, point_time
            )
        
        self.graph_data_buffer.clear()
        self._last_batch_update = current_time
        print(f"Gráficos actualizados - lote de {len(self.graph_data_buffer)} puntos")
    
    def _show_performance_stats(self):
        """Muestra estadísticas de performance para debug."""
        if self.is_recording and self.total_data_points > 0:
            efficiency = (self.points_sent_to_graph / self.total_data_points) * 100
            print(f"Performance: {self.total_data_points} datos almacenados, "
                  f"{self.points_sent_to_graph} enviados a gráfico ({efficiency:.1f}% eficiencia)")
            
            # Obtener info del buffer de gráficos
            buffer_info = self.plot_widget.get_buffer_info()
            print(f"Buffer gráfico: {buffer_info['current_size']}/{buffer_info['max_size']} "
                  f"({buffer_info['utilization_percent']:.1f}% usado)")
    
    def export_recording_data(self, filename: str = None) -> bool:
        """
        Exporta todos los datos grabados a un archivo CSV.
        
        Args:
            filename: Nombre del archivo de destino
            
        Returns:
            True si la exportación fue exitosa
        """
        return self.data_storage.export_to_csv(filename)
    
    def get_recording_statistics(self) -> dict:
        """Obtiene estadísticas de la grabación actual."""
        return self.data_storage.get_statistics()
    
    def load_recording_data(self, filename: str) -> bool:
        """
        Carga datos de un archivo CSV para visualización.
        
        Args:
            filename: Nombre del archivo a cargar
            
        Returns:
            True si la carga fue exitosa
        """
        success = self.data_storage.load_from_csv(filename)
        if success:
            # Opcional: Cargar datos en el gráfico para visualización
            print(f"Datos cargados exitosamente desde {filename}")
            # TODO: Implementar visualización de datos históricos si es necesario
        return success
    
    def optimize_performance(self):
        """Aplica optimizaciones automáticas de performance."""
        # Optimizar gráficos
        self.plot_widget.optimize_performance()
        
        # Ajustar intervalo de envío a gráficos basado en carga
        buffer_info = self.plot_widget.get_buffer_info()
        
        if buffer_info['utilization_percent'] > 80:
            # Sistema sobrecargado, reducir frecuencia
            self.graph_update_interval = 100  # 10 FPS
            self.graph_timer.setInterval(self.graph_update_interval)
            print("Performance: Reduciendo frecuencia de gráficos a 10 FPS")
            
        elif buffer_info['utilization_percent'] < 30:
            # Sistema con recursos, aumentar frecuencia
            self.graph_update_interval = 33   # 30 FPS
            self.graph_timer.setInterval(self.graph_update_interval)
            print("Performance: Aumentando frecuencia de gráficos a 30 FPS")
    
    def get_system_status(self) -> dict:
        """Obtiene el estado completo del sistema."""
        return {
            'is_recording': self.is_recording,
            'is_calibrating': self.is_calibrating,
            'total_data_points': self.total_data_points,
            'points_sent_to_graph': self.points_sent_to_graph,
            'graph_efficiency': (self.points_sent_to_graph / max(1, self.total_data_points)) * 100,
            'storage_stats': self.data_storage.get_statistics(),
            'buffer_info': self.plot_widget.get_buffer_info() if hasattr(self, 'plot_widget') else {},
            'current_graph_time': self.graph_time
        }