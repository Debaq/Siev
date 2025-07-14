import csv
import time
import threading
from collections import deque
from typing import List, Dict, Optional, Any
import json
import os


class DataStorage:
    """
    Sistema de almacenamiento que mantiene TODOS los datos sin pérdida.
    Separa completamente el almacenamiento de la visualización.
    """
    
    def __init__(self, auto_save_interval=5.0, buffer_size=1000, data_path=None):
        # Almacenamiento completo de todos los datos
        self.complete_dataset = []
        
        # Buffer para escritura asíncrona
        self.write_buffer = deque()
        self.buffer_size = buffer_size
        
        # Configurar rutas - usar data_path si se proporciona, sino usar por defecto
        if data_path is None:
            data_path = "./siev"
        
        self.data_path = data_path
        self.data_dir = os.path.join(data_path, "data")
        self.logs_dir = os.path.join(data_path, "logs")
        
        # Crear directorios si no existen
        self._ensure_directories()
        
        # Control de archivos
        self.recording_filename = None
        self.auto_save_interval = auto_save_interval
        self.is_recording = False
        
        # Threading para escritura asíncrona
        self.write_thread = None
        self.stop_writing = threading.Event()
        
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
        Inicia una nueva grabación.
        
        Args:
            filename: Nombre del archivo. Si es None, se genera automáticamente.
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
        
        # Crear archivo con encabezados
        self._create_csv_file()
        
        # Iniciar hilo de escritura asíncrona
        self.stop_writing.clear()
        self.write_thread = threading.Thread(target=self._async_writer, daemon=True)
        self.write_thread.start()
        
        print(f"Grabación iniciada: {filename}")
    
    def stop_recording(self):
        """Detiene la grabación actual y guarda todos los datos pendientes."""
        if not self.is_recording:
            return
        
        self.is_recording = False
        
        # Detener hilo de escritura
        if self.write_thread and self.write_thread.is_alive():
            self.stop_writing.set()
            self.write_thread.join(timeout=5.0)
        
        # Escribir datos pendientes
        self._flush_remaining_data()
        
        # Actualizar metadatos finales
        self.recording_metadata['end_time'] = time.time()
        self.recording_metadata['total_samples'] = len(self.complete_dataset)
        
        # Calcular sample rate promedio
        if len(self.complete_dataset) > 1:
            duration = self.recording_metadata['end_time'] - self.recording_metadata['start_time']
            self.recording_metadata['sample_rate'] = len(self.complete_dataset) / duration
        
        # Guardar metadatos
        self._save_metadata()
        
        print(f"Grabación detenida. {len(self.complete_dataset)} muestras guardadas.")
    
    def add_data_point(self, left_eye: Optional[List[float]], right_eye: Optional[List[float]], 
                      imu_x: float, imu_y: float, timestamp: float):
        """
        Añade un punto de datos al almacenamiento completo.
        
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
            self.write_buffer.append(data_point)
    
    def get_data_range(self, start_time: float, end_time: float) -> List[Dict]:
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
                return {'total_samples': 0}
            
            # Calcular estadísticas básicas
            total_samples = len(self.complete_dataset)
            start_time = self.complete_dataset[0]['timestamp']
            end_time = self.complete_dataset[-1]['timestamp']
            duration = end_time - start_time
            
            # Contar detecciones válidas
            left_detections = sum(1 for p in self.complete_dataset if p['left_eye_detected'])
            right_detections = sum(1 for p in self.complete_dataset if p['right_eye_detected'])
            
            return {
                'total_samples': total_samples,
                'duration_seconds': duration,
                'sample_rate': total_samples / duration if duration > 0 else 0,
                'left_eye_detection_rate': left_detections / total_samples * 100,
                'right_eye_detection_rate': right_detections / total_samples * 100,
                'start_time': start_time,
                'end_time': end_time
            }
    
    def export_to_csv(self, filename: str = None) -> bool:
        """
        Exporta todos los datos a un archivo CSV.
        
        Args:
            filename: Nombre del archivo de destino
            
        Returns:
            True si la exportación fue exitosa
        """
        if filename is None:
            filename = self.recording_filename or "vng_export.csv"
        
        try:
            with self.data_lock:
                with open(filename, 'w', newline='') as csvfile:
                    if not self.complete_dataset:
                        return False
                    
                    fieldnames = ['timestamp', 'left_eye_x', 'left_eye_y', 'right_eye_x', 
                                'right_eye_y', 'imu_x', 'imu_y', 'left_eye_detected', 'right_eye_detected']
                    
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(self.complete_dataset)
            
            print(f"Datos exportados exitosamente a {filename}")
            return True
            
        except Exception as e:
            print(f"Error al exportar datos: {e}")
            return False
    
    def _create_csv_file(self):
        """Crea el archivo CSV con encabezados."""
        try:
            with open(self.recording_filename, 'w', newline='') as csvfile:
                fieldnames = ['timestamp', 'left_eye_x', 'left_eye_y', 'right_eye_x', 
                            'right_eye_y', 'imu_x', 'imu_y', 'left_eye_detected', 'right_eye_detected']
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
        except Exception as e:
            print(f"Error al crear archivo CSV: {e}")
    
    def _async_writer(self):
        """Hilo de escritura asíncrona para mantener performance."""
        while not self.stop_writing.is_set():
            try:
                # Recopilar datos para escribir
                data_to_write = []
                with self.data_lock:
                    if len(self.write_buffer) >= self.buffer_size:
                        data_to_write = list(self.write_buffer)
                        self.write_buffer.clear()
                
                # Escribir datos si hay suficientes
                if data_to_write:
                    self._write_data_batch(data_to_write)
                
                # Esperar antes del siguiente ciclo
                self.stop_writing.wait(self.auto_save_interval)
                
            except Exception as e:
                print(f"Error en escritura asíncrona: {e}")
    
    def _write_data_batch(self, data_batch: List[Dict]):
        """Escribe un lote de datos al archivo."""
        try:
            with open(self.recording_filename, 'a', newline='') as csvfile:
                fieldnames = ['timestamp', 'left_eye_x', 'left_eye_y', 'right_eye_x', 
                            'right_eye_y', 'imu_x', 'imu_y', 'left_eye_detected', 'right_eye_detected']
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writerows(data_batch)
        except Exception as e:
            print(f"Error al escribir lote de datos: {e}")
    
    def _flush_remaining_data(self):
        """Escribe todos los datos pendientes al archivo."""
        with self.data_lock:
            if self.write_buffer:
                self._write_data_batch(list(self.write_buffer))
                self.write_buffer.clear()
    
    def _save_metadata(self):
        """Guarda metadatos de la grabación."""
        if not self.recording_filename:
            return
        
        metadata_filename = self.recording_filename.replace('.csv', '_metadata.json')
        try:
            with open(metadata_filename, 'w') as f:
                json.dump(self.recording_metadata, f, indent=2)
        except Exception as e:
            print(f"Error al guardar metadatos: {e}")
    
    def load_from_csv(self, filename: str) -> bool:
        """
        Carga datos desde un archivo CSV.
        
        Args:
            filename: Nombre del archivo a cargar
            
        Returns:
            True si la carga fue exitosa
        """
        try:
            with open(filename, 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                loaded_data = []
                
                for row in reader:
                    # Convertir tipos de datos
                    data_point = {
                        'timestamp': float(row['timestamp']),
                        'left_eye_x': float(row['left_eye_x']) if row['left_eye_x'] != '' else None,
                        'left_eye_y': float(row['left_eye_y']) if row['left_eye_y'] != '' else None,
                        'right_eye_x': float(row['right_eye_x']) if row['right_eye_x'] != '' else None,
                        'right_eye_y': float(row['right_eye_y']) if row['right_eye_y'] != '' else None,
                        'imu_x': float(row['imu_x']),
                        'imu_y': float(row['imu_y']),
                        'left_eye_detected': row['left_eye_detected'].lower() == 'true',
                        'right_eye_detected': row['right_eye_detected'].lower() == 'true'
                    }
                    loaded_data.append(data_point)
            
            with self.data_lock:
                self.complete_dataset = loaded_data
            
            print(f"Cargados {len(loaded_data)} puntos de datos desde {filename}")
            return True
            
        except Exception as e:
            print(f"Error al cargar datos: {e}")
            return False