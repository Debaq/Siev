#!/usr/bin/env python3
"""
Simple Processor Logic
Lógica de negocio para el procesador simple de videos.
Maneja datos, archivos, procesamiento y configuraciones sin elementos de UI.
"""

import json
import tarfile
import os
from typing import Dict, List, Optional, Tuple
from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtWidgets import QFileDialog

try:
    from video.simple_video_player import SimpleVideoPlayer
    from video.fast_video_processor import FastVideoProcessor
except ImportError as e:
    print(f"Error importing video modules: {e}")


class SimpleProcessorLogic(QObject):
    """
    Lógica de negocio para el procesador simple.
    Maneja todos los datos y operaciones sin elementos de UI.
    """
    
    # Señales para comunicación con UI
    status_updated = Signal(str)  # mensaje de estado
    siev_data_loaded = Signal(list)  # lista de nombres de pruebas
    test_selection_changed = Signal(bool)  # habilitar botón de video SIEV
    video_loaded = Signal(bool, float)  # success, duration
    frame_ready = Signal(object)  # frame procesado para mostrar
    time_info_updated = Signal(float, float)  # current_time, max_time
    config_labels_updated = Signal(int, int, str)  # current_frame, total_configs, config_text
    graph_data_updated = Signal(list, list)  # timestamps, values para gráfico simple
    caloric_point_added = Signal(float, float)  # timestamp, value para gráfico calórico
    time_line_position_updated = Signal(float)  # position para línea de tiempo
    graph_duration_adjusted = Signal(float)  # duration para ajustar gráfico
    
    def __init__(self):
        super().__init__()
        
        # Datos principales
        self.siev_data = None
        self.current_test = None
        self.video_path = None
        
        # Sistema de configuraciones dinámicas por frame
        self.saved_frame_configs = {}  # {frame_number: {'threshold_right': X, 'erode_right': Y}}
        self.save_config_mode = False
        
        # Configuración de umbrales
        self.thresholds = {
            'threshold_right': 50,
            'erode_right': 2,
            'nose_width': 0.25,
            'eye_height': 0.5
        }
        
        # Componentes de video
        self.video_player = None
        self.fast_processor = None
        
        # Timer para visualización en tiempo real
        self.visualization_timer = QTimer()
        self.visualization_timer.timeout.connect(self.update_current_frame_visualization)
        
        # Datos de gráfico (un solo punto por timestamp)
        self.graph_data_timestamps = []
        self.graph_data_values = []
        
        # Frame actual para procesamiento
        self.current_raw_frame = None
        self.current_graph_type = "Espontáneo (Simple)"
        
    # ========== MÉTODOS DE CARGA DE ARCHIVOS ==========
    
    def load_siev_file(self, parent_widget=None):
        """Cargar archivo SIEV"""
        file_path, _ = QFileDialog.getOpenFileName(
            parent_widget, "Cargar archivo SIEV", "", "Archivos SIEV (*.siev);;Todos los archivos (*)"
        )
        
        if not file_path:
            return
            
        try:
            with tarfile.open(file_path, 'r:gz') as tar:
                # Buscar metadata.json específicamente
                try:
                    metadata_file = tar.extractfile('metadata.json')
                    if metadata_file:
                        content = metadata_file.read().decode('utf-8')
                        self.siev_data = json.loads(content)
                    else:
                        self.status_updated.emit("No se encontró metadata.json en el archivo SIEV")
                        return
                except KeyError:
                    # Si no existe metadata.json, intentar backup
                    try:
                        backup_file = tar.extractfile('metadata_backup.json')
                        if backup_file:
                            content = backup_file.read().decode('utf-8')
                            self.siev_data = json.loads(content)
                            print("Usando metadata_backup.json")
                        else:
                            self.status_updated.emit("No se encontró metadata.json ni metadata_backup.json")
                            return
                    except KeyError:
                        self.status_updated.emit("Archivo SIEV no contiene archivos de metadata esperados")
                        return
                        
            # Procesar pruebas
            test_names = []
            if 'pruebas' in self.siev_data:
                for prueba in self.siev_data['pruebas']:
                    test_id = prueba.get('id', 'sin_id')
                    test_type = prueba.get('tipo', 'desconocido')
                    test_name = f"{test_id} ({test_type})"
                    test_names.append(test_name)
            
            # Emitir señales
            self.siev_data_loaded.emit(test_names)
            if test_names:
                self.status_updated.emit(f"SIEV cargado: {len(test_names)} pruebas encontradas")
            else:
                self.status_updated.emit("SIEV cargado pero sin pruebas válidas")
            
        except Exception as e:
            print(f"Error cargando archivo SIEV: {e}")
            self.status_updated.emit(f"Error cargando SIEV: {str(e)}")
            
    def load_video_direct(self, parent_widget=None):
        """Cargar video directamente"""
        file_path, _ = QFileDialog.getOpenFileName(
            parent_widget, "Cargar video directo", "", "Videos (*.mp4 *.avi *.mov *.mkv);;Todos los archivos (*)"
        )
        
        if not file_path:
            return
            
        self.video_path = file_path
        self.status_updated.emit("Cargando video directo...")
        self._load_video_file(file_path)
        
    def load_siev_video(self, parent_widget=None):
        """Cargar video para la prueba SIEV seleccionada"""
        if not self.current_test:
            self.status_updated.emit("Selecciona una prueba SIEV primero")
            return
            
        file_path, _ = QFileDialog.getOpenFileName(
            parent_widget, "Cargar video para prueba SIEV", "", "Videos (*.mp4 *.avi *.mov *.mkv);;Todos los archivos (*)"
        )
        
        if not file_path:
            return
            
        self.video_path = file_path
        test_id = self.current_test.get('id', 'desconocida')
        self.status_updated.emit(f"Cargando video para prueba {test_id}...")
        self._load_video_file(file_path)
        
    def _load_video_file(self, file_path: str):
        """Método común para cargar archivos de video"""
        # Inicializar procesador rápido
        self.fast_processor = FastVideoProcessor(self.thresholds)
        
        try:
            with open(file_path, 'rb') as f:
                video_data = f.read()
                
            self.video_player = SimpleVideoPlayer(video_data)
            self.video_player.frame_ready.connect(self._on_frame_ready)
            self.video_player.video_loaded.connect(self._on_video_loaded)
            self.video_player.duration_changed.connect(self._on_duration_changed)
            
            # Iniciar thread
            self.video_player.start()
            
        except Exception as e:
            print(f"Error cargando video: {e}")
            self.status_updated.emit(f"Error cargando video: {str(e)}")
            
    # ========== MÉTODOS DE EVENTOS DE VIDEO ==========
    
    def _on_video_loaded(self, success: bool):
        """Manejar evento de video cargado"""
        if success:
            self.status_updated.emit("Video cargado correctamente")
            
            # Obtener duración y ajustar gráfico
            max_duration = self.video_player.get_duration()
            self.graph_duration_adjusted.emit(max_duration)
            
            # Iniciar timer para visualización en tiempo real
            self.visualization_timer.start(100)
            
            # Buscar frame inicial
            self.video_player.seek_to_frame(0)
            
            self.video_loaded.emit(True, max_duration)
        else:
            self.status_updated.emit("Error cargando video")
            self.video_loaded.emit(False, 0.0)
            
    def _on_duration_changed(self, duration: float):
        """Manejar cambio de duración"""
        self.graph_duration_adjusted.emit(duration)
        
    def _on_frame_ready(self, frame):
        """Manejar frame listo del video player"""
        if frame is not None:
            # Guardar frame para procesamiento
            self.current_raw_frame = frame.copy()
            
            # Procesar con FastVideoProcessor si está disponible
            if self.fast_processor:
                try:
                    pupil_x, pupil_y, detected, vis_frame = self.fast_processor.process_frame(frame)
                    
                    # Emitir frame procesado para mostrar
                    self.frame_ready.emit(vis_frame)
                    
                    # Agregar punto al gráfico si se detectó pupila
                    if detected:
                        current_time = self.video_player.get_current_time() if self.video_player else 0
                        self.add_point_to_graph(current_time, pupil_x)
                        
                except Exception as e:
                    print(f"Error procesando frame: {e}")
                    self.frame_ready.emit(frame)
            else:
                self.frame_ready.emit(frame)
                
    # ========== MÉTODOS DE SELECCIÓN Y CONFIGURACIÓN ==========
    
    def set_test_selected(self, test_name: str):
        """Establecer prueba seleccionada"""
        if not test_name or not self.siev_data:
            self.current_test = None
            self.test_selection_changed.emit(False)
            return
            
        # Extraer ID de la prueba
        test_id = test_name.split(' (')[0] if ' (' in test_name else test_name
        
        # Buscar la prueba
        for prueba in self.siev_data.get('pruebas', []):
            if prueba.get('id') == test_id:
                self.current_test = prueba
                self.test_selection_changed.emit(True)
                self.status_updated.emit(f"Prueba seleccionada: {test_name}")
                return
                
        self.current_test = None
        self.test_selection_changed.emit(False)
        
    def set_save_config_mode(self, enabled: bool):
        """Establecer modo de guardar configuración"""
        self.save_config_mode = enabled
        status_msg = "Modo guardar config: ACTIVADO" if enabled else "Modo guardar config: DESACTIVADO"
        self.status_updated.emit(status_msg)
        print(f"Modo guardar configuración: {'ACTIVADO' if enabled else 'DESACTIVADO'}")
        
    def set_threshold_value(self, param: str, value):
        """Establecer valor de umbral"""
        self.thresholds[param] = value
        
        # Actualizar FastVideoProcessor si existe
        if self.fast_processor:
            self.fast_processor.thresholds[param] = value
        
        # Si está en modo guardar, guardar configuración automáticamente
        if self.save_config_mode and param in ['threshold_right', 'erode_right']:
            self.save_current_frame_config()
            
    def set_graph_type(self, graph_type: str):
        """Establecer tipo de gráfico"""
        self.current_graph_type = graph_type
        
    # ========== MÉTODOS DE CONFIGURACIÓN POR FRAME ==========
    
    def save_current_frame_config(self):
        """Guardar configuración actual del frame"""
        if not self.video_player or not self.save_config_mode:
            return
            
        current_frame = self.video_player.get_current_frame_index()
        
        # Guardar solo threshold_right y erode_right
        config = {
            'threshold_right': self.thresholds['threshold_right'],
            'erode_right': self.thresholds['erode_right']
        }
        
        self.saved_frame_configs[current_frame] = config
        
        print(f"Configuración guardada para frame {current_frame}: {config}")
        self.update_config_labels()
        
    def get_frame_config(self, frame_number: int) -> Dict:
        """Obtener configuración para un frame específico"""
        if frame_number in self.saved_frame_configs:
            # Usar configuración guardada para este frame
            saved_config = self.saved_frame_configs[frame_number].copy()
            # Completar con valores actuales para otros parámetros
            full_config = self.thresholds.copy()
            full_config.update(saved_config)
            return full_config
        else:
            # Usar configuración actual de sliders
            return self.thresholds.copy()
            
    def update_config_labels(self):
        """Actualizar información de configuración"""
        if not self.video_player:
            return
            
        current_frame = self.video_player.get_current_frame_index()
        total_configs = len(self.saved_frame_configs)
        
        if current_frame in self.saved_frame_configs:
            config = self.saved_frame_configs[current_frame]
            config_text = f"T:{config['threshold_right']} E:{config['erode_right']}"
        else:
            config_text = "Global"
            
        self.config_labels_updated.emit(current_frame, total_configs, config_text)
        
    # ========== MÉTODOS DE CONTROL DE TIEMPO ==========
    
    def set_time_position(self, slider_value: int):
        """Establecer posición de tiempo basada en slider"""
        if not self.video_player:
            return
            
        # Convertir valor del slider a tiempo
        max_time = self.video_player.get_duration()
        current_time = (slider_value / 1000.0) * max_time
        current_frame = int(current_time * self.video_player.get_fps()) if self.video_player.get_fps() > 0 else 0
        
        # Obtener configuración específica para este frame
        frame_config = self.get_frame_config(current_frame)
        
        # Actualizar FastVideoProcessor con configuración específica del frame
        if self.fast_processor:
            self.fast_processor.update_thresholds(frame_config)
        
        # Actualizar video player
        try:
            self.video_player.seek_to_time(current_time)
        except Exception as e:
            print(f"Error en seek_to_time: {e}")
            
        # Emitir señales de actualización
        self.time_info_updated.emit(current_time, max_time)
        self.time_line_position_updated.emit(current_time)
        self.update_config_labels()
        
        # Procesar frame actual para gráfico si hay detección
        if self.fast_processor and self.current_raw_frame is not None:
            try:
                pupil_x, pupil_y, detected, _ = self.fast_processor.process_frame(self.current_raw_frame)
                if detected:
                    self.add_point_to_graph(current_time, pupil_x)
            except Exception as e:
                print(f"Error procesando frame para gráfico: {e}")
                
    def update_current_frame_visualization(self):
        """Actualizar visualización del frame actual"""
        if not self.current_raw_frame or not self.fast_processor:
            return
            
        try:
            # Procesar frame actual con parámetros actualizados
            _, _, _, vis_frame = self.fast_processor.process_frame(self.current_raw_frame)
            
            # Emitir frame procesado
            if vis_frame is not None:
                self.frame_ready.emit(vis_frame)
                
        except Exception as e:
            print(f"Error actualizando visualización: {e}")
            
    # ========== MÉTODOS DE GRÁFICO ==========
    
    def add_point_to_graph(self, timestamp: float, value: float):
        """Agregar punto al gráfico actual (solo un punto por timestamp)"""
        if "Simple" in self.current_graph_type:
            # Buscar si ya existe un punto en este timestamp
            existing_index = None
            for i, existing_timestamp in enumerate(self.graph_data_timestamps):
                if abs(existing_timestamp - timestamp) < 0.01:  # Tolerancia de 10ms
                    existing_index = i
                    break
                    
            if existing_index is not None:
                # Actualizar punto existente
                self.graph_data_values[existing_index] = value
            else:
                # Agregar nuevo punto
                self.graph_data_timestamps.append(timestamp)
                self.graph_data_values.append(value)
                
                # Mantener ordenado por timestamp
                sorted_pairs = sorted(zip(self.graph_data_timestamps, self.graph_data_values))
                if sorted_pairs:
                    self.graph_data_timestamps, self.graph_data_values = zip(*sorted_pairs)
                    self.graph_data_timestamps = list(self.graph_data_timestamps)
                    self.graph_data_values = list(self.graph_data_values)
                else:
                    self.graph_data_timestamps = []
                    self.graph_data_values = []
                
                # Mantener solo últimos 1000 puntos para rendimiento
                if len(self.graph_data_timestamps) > 1000:
                    self.graph_data_timestamps = self.graph_data_timestamps[-500:]
                    self.graph_data_values = self.graph_data_values[-500:]
            
            # Emitir datos actualizados
            self.graph_data_updated.emit(self.graph_data_timestamps, self.graph_data_values)
            
        elif "Avanzado" in self.current_graph_type:
            # Para gráfico calórico
            self.caloric_point_added.emit(timestamp, value)
            
    def clear_graph_data(self):
        """Limpiar datos del gráfico"""
        self.graph_data_timestamps.clear()
        self.graph_data_values.clear()
        self.graph_data_updated.emit([], [])
        
    # ========== MÉTODOS DE INFORMACIÓN ==========
    
    def get_video_info(self) -> Dict:
        """Obtener información del video actual"""
        if not self.video_player:
            return {}
            
        return {
            'duration': self.video_player.get_duration(),
            'fps': self.video_player.get_fps(),
            'total_frames': self.video_player.get_total_frames(),
            'current_frame': self.video_player.get_current_frame_index(),
            'current_time': self.video_player.get_current_time(),
        }
        
    def get_config_info(self) -> Dict:
        """Obtener información de configuraciones"""
        return {
            'save_mode': self.save_config_mode,
            'saved_configs': len(self.saved_frame_configs),
            'thresholds': self.thresholds.copy(),
        }
        
    def get_graph_info(self) -> Dict:
        """Obtener información del gráfico"""
        return {
            'type': self.current_graph_type,
            'points_count': len(self.graph_data_timestamps),
            'timestamps': self.graph_data_timestamps.copy(),
            'values': self.graph_data_values.copy(),
        }