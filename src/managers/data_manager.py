# src/managers/data_manager.py

from PySide6.QtCore import QObject, Signal, QTimer
from typing import List, Dict, Optional, Any
import time

from libs.data.data_storage import DataStorage
from libs.data.eye_data_processor import EyeDataProcessor
from libs.core.detector_nystamus import DetectorNistagmo
from libs.ui.graphing.triple_plot_widget import TriplePlotWidget, PlotConfigurations
from libs.core.config_manager import ConfigManager


class DataManager(QObject):
    """
    Gestiona todo el sistema de datos: almacenamiento, procesamiento, gráficos y análisis.
    Encapsula la lógica de datos para desacoplarla de MainWindow.
    """
    
    # Señales para comunicarse con MainWindow
    recording_started = Signal(str)         # Filename de grabación iniciada
    recording_stopped = Signal(str)        # Filename de grabación completada
    data_point_processed = Signal(dict)    # Punto de datos procesado
    analysis_completed = Signal(dict)      # Análisis completado
    buffer_full_warning = Signal(str)      # Advertencia de buffer lleno
    
    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        
        # Referencia al gestor de configuración
        self.config_manager = config_manager
        
        # Componentes de datos
        self.data_storage = None
        self.eye_processor = None
        self.detector_nistagmo = None
        self.plot_widget = None
        
        # Referencias de UI (se asignan desde MainWindow)
        self.graph_layout = None
        
        # Estado de grabación
        self.is_recording = False
        self.is_processing = False
        self.recording_start_time = None
        self.current_filename = None
        
        # Buffer para optimización de gráficos
        self.graph_data_buffer = []
        self.last_graph_update = 0
        self.graph_update_interval = 0.016  # ~60 FPS
        
        # Buffer para datos en tiempo real
        self.realtime_buffer = {
            'timestamps': [],
            'left_eye_positions': [],
            'right_eye_positions': [],
            'imu_data': [],
            'max_size': 1000
        }
        
        # Estadísticas
        self.total_points_processed = 0
        self.processing_errors = 0
        
        print("DataManager inicializado")
    
    def set_ui_references(self, graph_layout):
        """
        Establece referencias a elementos de UI necesarios.
        
        Args:
            graph_layout: Layout donde se colocará el widget de gráficos
        """
        self.graph_layout = graph_layout
        print("Referencias UI establecidas en DataManager")
    
    def initialize_data_system(self) -> bool:
        """Inicializa todo el sistema de datos"""
        try:
            self._init_storage_system()
            self._init_processing_system()
            self._init_graphics_system()
            
            print("Sistema de datos inicializado exitosamente")
            return True
            
        except Exception as e:
            print(f"Error inicializando sistema de datos: {e}")
            return False
    
    def _init_storage_system(self):
        """Inicializa el sistema de almacenamiento"""
        try:
            self.data_storage = DataStorage(
                auto_save_interval=2.0,
                buffer_size=500,
                data_dir=self.config_manager.get_data_dir()
            )
            print("Sistema de almacenamiento inicializado")
        except Exception as e:
            print(f"Error inicializando almacenamiento: {e}")
            self.data_storage = None
    
    def _init_processing_system(self):
        """Inicializa el sistema de procesamiento de datos"""
        try:
            self.eye_processor = EyeDataProcessor()
            self.detector_nistagmo = DetectorNistagmo()
            print("Sistema de procesamiento inicializado")
        except Exception as e:
            print(f"Error inicializando procesamiento: {e}")
    
    def _init_graphics_system(self):
        """Inicializa el sistema de gráficos"""
        try:
            if not self.graph_layout:
                raise Exception("Layout de gráficos no configurado")
            
            # Configuración optimizada para gráficos
            config = PlotConfigurations.get_ultra_minimal()
            
            self.plot_widget = TriplePlotWidget(
                parent=None,
                window_size=60,
                update_interval=50,
                plot_config=config
            )
            
            # Agregar al layout
            self.graph_layout.addWidget(self.plot_widget)
            
            print("Sistema de gráficos inicializado")
        except Exception as e:
            print(f"Error inicializando gráficos: {e}")
            self.plot_widget = None
    
    # === CONTROL DE GRABACIÓN ===
    
    def start_recording(self, test_name: str = None) -> bool:
        """
        Inicia la grabación de datos.
        
        Args:
            test_name: Nombre opcional para el test
            
        Returns:
            bool: True si se inició exitosamente
        """
        if self.is_recording:
            print("Advertencia: Grabación ya en progreso")
            return False
        
        if not self.data_storage:
            print("Error: Sistema de almacenamiento no disponible")
            return False
        
        try:
            # Generar filename
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            if test_name:
                filename = f"{test_name}_{timestamp}.csv"
            else:
                filename = f"vng_recording_{timestamp}.csv"
            
            # Iniciar grabación
            success = self.data_storage.start_recording(filename)
            
            if success:
                self.is_recording = True
                self.recording_start_time = time.time()
                self.current_filename = filename
                
                # Limpiar buffers
                self._clear_buffers()
                
                # Configurar gráficos para grabación
                if self.plot_widget:
                    self.plot_widget.clear_data()
                    self.plot_widget.set_recording_state(True)
                
                self.recording_started.emit(filename)
                print(f"Grabación iniciada: {filename}")
                return True
            else:
                print("Error iniciando grabación en DataStorage")
                return False
                
        except Exception as e:
            print(f"Error iniciando grabación: {e}")
            return False
    
    def stop_recording(self) -> Optional[str]:
        """
        Detiene la grabación de datos.
        
        Returns:
            str: Filename de la grabación o None si hubo error
        """
        if not self.is_recording:
            print("Advertencia: No hay grabación en progreso")
            return None
        
        try:
            # Detener grabación
            filename = self.data_storage.stop_recording()
            
            # Actualizar estado
            self.is_recording = False
            recording_filename = self.current_filename
            self.current_filename = None
            self.recording_start_time = None
            
            # Configurar gráficos
            if self.plot_widget:
                self.plot_widget.set_recording_state(False)
            
            # Procesar datos finales
            self._flush_graph_buffer()
            
            self.recording_stopped.emit(recording_filename or "unknown")
            print(f"Grabación detenida: {recording_filename}")
            
            return recording_filename
            
        except Exception as e:
            print(f"Error deteniendo grabación: {e}")
            self.is_recording = False
            return None
    
    # === PROCESAMIENTO DE DATOS ===
    
    def process_eye_data(self, left_eye: Optional[List[float]], 
                        right_eye: Optional[List[float]], 
                        timestamp: Optional[float] = None) -> Dict[str, Any]:
        """
        Procesa datos de posiciones oculares.
        
        Args:
            left_eye: Posición del ojo izquierdo [x, y] o None
            right_eye: Posición del ojo derecho [x, y] o None
            timestamp: Timestamp opcional
            
        Returns:
            Dict con datos procesados
        """
        if timestamp is None:
            timestamp = time.time()
        
        try:
            # Procesar con EyeDataProcessor si está disponible
            processed_left = left_eye
            processed_right = right_eye
            
            if self.eye_processor:
                # Aquí puedes agregar procesamiento específico
                pass
            
            # Crear punto de datos procesado
            data_point = {
                'timestamp': timestamp,
                'left_eye': processed_left,
                'right_eye': processed_right,
                'left_eye_valid': processed_left is not None,
                'right_eye_valid': processed_right is not None,
                'processing_time': time.time()
            }
            
            # Actualizar buffer en tiempo real
            self._update_realtime_buffer(data_point)
            
            # Enviar a almacenamiento si está grabando
            if self.is_recording and self.data_storage:
                self._store_eye_data(data_point)
            
            # Agregar a buffer de gráficos
            self._add_to_graph_buffer(data_point)
            
            self.total_points_processed += 1
            self.data_point_processed.emit(data_point)
            
            return data_point
            
        except Exception as e:
            print(f"Error procesando datos oculares: {e}")
            self.processing_errors += 1
            return {'error': str(e), 'timestamp': timestamp}
    
    def process_imu_data(self, imu_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesa datos del IMU.
        
        Args:
            imu_data: Datos del IMU
            
        Returns:
            Dict con datos procesados del IMU
        """
        try:
            # Extraer valores relevantes
            processed_data = {
                'timestamp': imu_data.get('timestamp', time.time()),
                'yaw': imu_data.get('yaw', 0.0),
                'pitch': imu_data.get('pitch', 0.0),
                'roll': imu_data.get('roll', 0.0),
                'is_valid': imu_data.get('is_valid', False)
            }
            
            # Actualizar buffer en tiempo real
            self.realtime_buffer['imu_data'].append(processed_data)
            self._trim_realtime_buffer()
            
            # Enviar a almacenamiento si está grabando
            if self.is_recording and self.data_storage:
                self._store_imu_data(processed_data)
            
            return processed_data
            
        except Exception as e:
            print(f"Error procesando datos IMU: {e}")
            return {'error': str(e)}
    
    def add_combined_data_point(self, left_eye: Optional[List[float]], 
                               right_eye: Optional[List[float]], 
                               imu_x: float, imu_y: float, 
                               timestamp: Optional[float] = None):
        """
        Añade un punto combinado de datos (ojos + IMU) para gráficos.
        
        Args:
            left_eye: Posición ojo izquierdo
            right_eye: Posición ojo derecho  
            imu_x: Valor IMU X
            imu_y: Valor IMU Y
            timestamp: Timestamp
        """
        if timestamp is None:
            timestamp = time.time()
        
        try:
            # Enviar a gráficos
            if self.plot_widget:
                self.plot_widget.add_data_point(left_eye, right_eye, imu_x, imu_y, timestamp)
            
            # Si está grabando, almacenar datos combinados
            if self.is_recording and self.data_storage:
                combined_data = {
                    'timestamp': timestamp,
                    'left_eye': left_eye,
                    'right_eye': right_eye,
                    'imu_x': imu_x,
                    'imu_y': imu_y
                }
                # Aquí puedes agregar lógica de almacenamiento específica
                
        except Exception as e:
            print(f"Error añadiendo punto combinado: {e}")
    
    # === MÉTODOS AUXILIARES ===
    
    def _clear_buffers(self):
        """Limpia todos los buffers de datos"""
        self.graph_data_buffer.clear()
        self.realtime_buffer = {
            'timestamps': [],
            'left_eye_positions': [],
            'right_eye_positions': [],
            'imu_data': [],
            'max_size': 1000
        }
    
    def _update_realtime_buffer(self, data_point: Dict):
        """Actualiza el buffer de datos en tiempo real"""
        self.realtime_buffer['timestamps'].append(data_point['timestamp'])
        self.realtime_buffer['left_eye_positions'].append(data_point['left_eye'])
        self.realtime_buffer['right_eye_positions'].append(data_point['right_eye'])
        
        self._trim_realtime_buffer()
    
    def _trim_realtime_buffer(self):
        """Recorta el buffer en tiempo real al tamaño máximo"""
        max_size = self.realtime_buffer['max_size']
        
        for key in ['timestamps', 'left_eye_positions', 'right_eye_positions', 'imu_data']:
            if len(self.realtime_buffer[key]) > max_size:
                self.realtime_buffer[key] = self.realtime_buffer[key][-max_size:]
    
    def _add_to_graph_buffer(self, data_point: Dict):
        """Añade datos al buffer de gráficos"""
        current_time = time.time()
        
        # Solo actualizar gráficos a intervalos regulares
        if current_time - self.last_graph_update < self.graph_update_interval:
            return
        
        self.graph_data_buffer.append(data_point)
        self.last_graph_update = current_time
        
        # Flush buffer si está muy lleno
        if len(self.graph_data_buffer) > 50:
            self._flush_graph_buffer()
    
    def _flush_graph_buffer(self):
        """Envía datos acumulados a los gráficos"""
        if not self.graph_data_buffer or not self.plot_widget:
            return
        
        try:
            for point in self.graph_data_buffer:
                # Extraer datos para gráficos
                left_eye = point.get('left_eye')
                right_eye = point.get('right_eye')
                timestamp = point.get('timestamp', time.time())
                
                # Datos IMU por defecto si no están disponibles
                imu_x = 0.0
                imu_y = 0.0
                
                # Enviar a gráficos
                if hasattr(self.plot_widget, 'add_data_point'):
                    self.plot_widget.add_data_point(left_eye, right_eye, imu_x, imu_y, timestamp)
            
            self.graph_data_buffer.clear()
            
        except Exception as e:
            print(f"Error enviando a gráficos: {e}")
            self.graph_data_buffer.clear()
    
    def _store_eye_data(self, data_point: Dict):
        """Almacena datos oculares en DataStorage"""
        if self.data_storage:
            # Aquí puedes formatear los datos según necesites
            self.data_storage.add_data_point(data_point)
    
    def _store_imu_data(self, imu_data: Dict):
        """Almacena datos IMU en DataStorage"""
        if self.data_storage:
            # Aquí puedes formatear los datos IMU según necesites
            pass
    
    # === ANÁLISIS DE DATOS ===
    
    def analyze_current_session(self) -> Dict[str, Any]:
        """Analiza la sesión actual de datos"""
        try:
            analysis = {
                'total_points': self.total_points_processed,
                'processing_errors': self.processing_errors,
                'session_duration': 0,
                'eye_tracking_quality': 'unknown'
            }
            
            if self.recording_start_time:
                analysis['session_duration'] = time.time() - self.recording_start_time
            
            # Aquí puedes agregar más análisis específicos
            
            return analysis
            
        except Exception as e:
            print(f"Error en análisis: {e}")
            return {'error': str(e)}
    
    # === INFORMACIÓN DE ESTADO ===
    
    def get_recording_status(self) -> Dict[str, Any]:
        """Obtiene estado de grabación"""
        return {
            'is_recording': self.is_recording,
            'current_filename': self.current_filename,
            'recording_duration': time.time() - self.recording_start_time if self.recording_start_time else 0,
            'total_points': self.total_points_processed
        }
    
    def get_realtime_data(self) -> Dict[str, Any]:
        """Obtiene datos en tiempo real"""
        return self.realtime_buffer.copy()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas del sistema"""
        return {
            'total_points_processed': self.total_points_processed,
            'processing_errors': self.processing_errors,
            'buffer_size': len(self.graph_data_buffer),
            'realtime_buffer_size': len(self.realtime_buffer['timestamps'])
        }
    
    # === CLEANUP ===
    
    def cleanup(self):
        """Limpia recursos del sistema de datos"""
        try:
            # Detener grabación si está activa
            if self.is_recording:
                self.stop_recording()
            
            # Limpiar buffers
            self._clear_buffers()
            
            # Cleanup de componentes
            if self.plot_widget:
                self.plot_widget.clear_data()
            
            print("DataManager limpiado")
            
        except Exception as e:
            print(f"Error durante cleanup de datos: {e}")