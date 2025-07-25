"""
Sistema de almacenamiento de datos VNG - Versión actualizada
Mantiene funcionalidad original pero elimina escritura CSV individual
Los datos se almacenan en memoria para posterior empaquetado con SievManager
"""

import time
import threading
from collections import deque
from typing import List, Dict, Optional, Any
import json
import os


class DataStorage:
    """
    Sistema de almacenamiento que mantiene TODOS los datos sin pérdida.
    Versión actualizada: datos en memoria para empaquetado posterior con SievManager
    """
    
    def __init__(self, auto_save_interval=5.0, buffer_size=1000, data_path=None):
        # Almacenamiento completo de todos los datos
        self.complete_dataset = []
        
        # Buffer para procesamiento
        self.write_buffer = deque()
        self.buffer_size = buffer_size
        
        # Configurar rutas - usar data_path si se proporciona, sino usar por defecto
        #if data_path is None:
        #    data_path = os.path.expanduser("~/siev_data")  # Expandir ~ al home
        #else:
        #    data_path = os.path.expanduser(data_path)  # Expandir ~ si está presente
        
        #self.data_path = data_path
        #self.data_dir = os.path.join(data_path, "data")
        #self.logs_dir = os.path.join(data_path, "logs")
        
        # Crear directorios si no existen
        #self._ensure_directories()
        
        # Control de grabación
        self.recording_filename = None
        self.auto_save_interval = auto_save_interval
        self.is_recording = False
        
        # Metadatos de la grabación
        self.recording_metadata = {
            'start_time': None,
            'end_time': None,
            'total_samples': 0,
            'sample_rate': 0,
            'version': '1.0'
        }
        
        # Lock para thread safety
        self.data_lock = threading.Lock()
        
        print("DataStorage inicializado - Almacenamiento en memoria")

    def _ensure_directories(self):
        """Crear directorios necesarios si no existen"""
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            os.makedirs(self.logs_dir, exist_ok=True)
            print(f"Directorios de datos asegurados en: {self.data_path}")
        except Exception as e:
            print(f"Error creando directorios de datos: {e}")
    
    def get_full_data_path(self, filename):
        """Obtener ruta completa para archivo de datos"""
        return os.path.join(self.data_dir, filename)
    
    def get_full_logs_path(self, filename):
        """Obtener ruta completa para archivo de logs"""
        return os.path.join(self.logs_dir, filename)
    
    def start_recording(self, filename: str = None):
        """
        Inicia una nueva grabación en memoria.
        
        Args:
            filename: Nombre del archivo (para referencia, no se crea archivo físico)
        """
        if self.is_recording:
            self.stop_recording()
        
        # Generar nombre de archivo si no se proporciona
        if filename is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"vng_recording_{timestamp}.csv"
        
        self.recording_filename = filename
        self.is_recording = True
        
        # Limpiar datos anteriores
        with self.data_lock:
            self.complete_dataset.clear()
            self.write_buffer.clear()
        
        # Configurar metadatos
        self.recording_metadata = {
            'start_time': time.time(),
            'end_time': None,
            'total_samples': 0,
            'sample_rate': 0,
            'version': '1.0',
            'filename': filename
        }
        
        print(f"Grabación iniciada en memoria: {filename}")
    
    def stop_recording(self):
        """Detiene la grabación actual."""
        if not self.is_recording:
            return
        
        self.is_recording = False
        
        # Actualizar metadatos finales
        self.recording_metadata['end_time'] = time.time()
        self.recording_metadata['total_samples'] = len(self.complete_dataset)
        
        # Calcular sample rate promedio
        if len(self.complete_dataset) > 1:
            duration = self.recording_metadata['end_time'] - self.recording_metadata['start_time']
            self.recording_metadata['sample_rate'] = len(self.complete_dataset) / duration
        
        print(f"Grabación detenida. {len(self.complete_dataset)} muestras almacenadas en memoria.")
    
    def add_data_point(self, left_eye: Optional[List[float]], right_eye: Optional[List[float]], 
                      imu_x: float, imu_y: float, timestamp: float):
        """
        Añade un punto de datos al almacenamiento en memoria.
        
        Args:
            left_eye: Posición del ojo izquierdo [x, y] o None
            right_eye: Posición del ojo derecho [x, y] o None
            imu_x: Valor del acelerómetro eje X
            imu_y: Valor del acelerómetro eje Y
            timestamp: Marca de tiempo
        """
        if not self.is_recording:
            return
        
        # Crear punto de datos
        data_point = {
            'timestamp': timestamp,
            'left_eye_x': left_eye[0] if left_eye else None,
            'left_eye_y': left_eye[1] if left_eye else None,
            'right_eye_x': right_eye[0] if right_eye else None,
            'right_eye_y': right_eye[1] if right_eye else None,
            'imu_x': imu_x,
            'imu_y': imu_y,
            'left_eye_detected': left_eye is not None,
            'right_eye_detected': right_eye is not None
        }
        
        # Almacenar en dataset completo (thread-safe)
        with self.data_lock:
            self.complete_dataset.append(data_point)
    
    def get_test_data(self):
        """
        Obtener todos los datos de la prueba para envío a SievManager
        
        Returns:
            dict: Datos completos de la prueba o None si no hay datos
        """
        with self.data_lock:
            if not self.complete_dataset:
                return None
            
            # Calcular estadísticas
            total_samples = len(self.complete_dataset)
            start_time = self.complete_dataset[0]['timestamp']
            end_time = self.complete_dataset[-1]['timestamp']
            duration = end_time - start_time
            sample_rate = total_samples / duration if duration > 0 else 0
            
            # Contar detecciones
            left_detections = sum(1 for p in self.complete_dataset if p['left_eye_detected'])
            right_detections = sum(1 for p in self.complete_dataset if p['right_eye_detected'])
            
            left_detection_rate = (left_detections / total_samples * 100) if total_samples > 0 else 0
            right_detection_rate = (right_detections / total_samples * 100) if total_samples > 0 else 0
            
            return {
                'filename': self.recording_filename,
                'start_time': self.recording_metadata['start_time'],
                'end_time': self.recording_metadata['end_time'],
                'duration_seconds': duration,
                'total_samples': total_samples,
                'sample_rate': sample_rate,
                'left_eye_detection_rate': left_detection_rate,
                'right_eye_detection_rate': right_detection_rate,
                'data': self.complete_dataset.copy(),  # Copia para seguridad
                'metadata': self.recording_metadata.copy(),
                'statistics': {
                    'duration_seconds': duration,
                    'total_samples': total_samples,
                    'sample_rate': sample_rate,
                    'left_eye_detection_rate': left_detection_rate,
                    'right_eye_detection_rate': right_detection_rate,
                    'start_time': start_time,
                    'end_time': end_time
                }
            }
    
    def get_data_by_time_range(self, start_time: float, end_time: float) -> List[Dict]:
        """
        Obtiene datos en un rango de tiempo específico.
        
        Args:
            start_time: Tiempo de inicio
            end_time: Tiempo de fin
            
        Returns:
            Lista de puntos de datos en el rango especificado
        """
        with self.data_lock:
            return [
                point for point in self.complete_dataset
                if start_time <= point['timestamp'] <= end_time
            ]
    
    def get_recent_data(self, seconds: float = 60.0) -> List[Dict]:
        """
        Obtiene los datos más recientes.
        
        Args:
            seconds: Número de segundos hacia atrás desde el último dato
            
        Returns:
            Lista de puntos de datos recientes
        """
        if not self.complete_dataset:
            return []
        
        with self.data_lock:
            latest_time = self.complete_dataset[-1]['timestamp']
            start_time = latest_time - seconds
            
            return [
                point for point in self.complete_dataset
                if point['timestamp'] >= start_time
            ]
    
    def get_all_data(self) -> List[Dict]:
        """Obtiene una copia de todos los datos almacenados."""
        with self.data_lock:
            return self.complete_dataset.copy()
    
    def get_statistics(self) -> Dict:
        """Obtiene estadísticas de la grabación actual."""
        with self.data_lock:
            if not self.complete_dataset:
                return {
                    'total_samples': 0,
                    'duration_seconds': 0,
                    'sample_rate': 0,
                    'left_eye_detection_rate': 0,
                    'right_eye_detection_rate': 0
                }
            
            total_points = len(self.complete_dataset)
            first_time = self.complete_dataset[0]['timestamp']
            last_time = self.complete_dataset[-1]['timestamp']
            duration = last_time - first_time
            
            # Contar detecciones
            left_detections = sum(1 for p in self.complete_dataset if p['left_eye_detected'])
            right_detections = sum(1 for p in self.complete_dataset if p['right_eye_detected'])
            
            return {
                'total_samples': total_points,
                'duration_seconds': duration,
                'sample_rate': total_points / duration if duration > 0 else 0,
                'left_eye_detection_rate': (left_detections / total_points * 100) if total_points > 0 else 0,
                'right_eye_detection_rate': (right_detections / total_points * 100) if total_points > 0 else 0,
                'start_time': first_time,
                'end_time': last_time
            }
    
    def clear_data(self):
        """Limpiar todos los datos almacenados."""
        with self.data_lock:
            self.complete_dataset.clear()
            self.write_buffer.clear()
            print("Datos limpiados de memoria")
    
    def is_recording_active(self):
        """Verificar si hay grabación activa."""
        return self.is_recording
    
    def get_sample_count(self):
        """Obtener número de muestras almacenadas."""
        with self.data_lock:
            return len(self.complete_dataset)
    
    def export_to_csv(self, filename: str = None) -> bool:
        """
        LEGACY: Exportar a CSV (mantenido para compatibilidad)
        Nota: En el nuevo sistema, los datos se empaquetan directamente en .siev
        """
        print("AVISO: export_to_csv es legacy. Los datos se empaquetan automáticamente en .siev")
        return True
    
    def load_from_csv(self, filename: str) -> bool:
        """
        LEGACY: Cargar desde CSV (mantenido para compatibilidad)
        """
        print("AVISO: load_from_csv es legacy. Los datos se cargan desde archivos .siev")
        return False