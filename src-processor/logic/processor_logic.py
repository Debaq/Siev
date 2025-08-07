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

from utils.pupil_filter import PupilSignalFilter
from utils.pixel_to_degrees_calibrator import PixelToDegreesCalibrator


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
    slider_frame_config = Signal(int)  # Emite total de frames para configurar slider
    frame_info_updated = Signal(int, int)  # Emite (current_frame, total_frames)
    torok_data_updated = Signal(list, list)  # timestamps, values para gráfico Torok - NUEVA SEÑAL


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
        #elf.visualization_timer = QTimer()
        #self.visualization_timer.timeout.connect(self.update_current_frame_visualization)
        
        # Datos de gráfico (un solo punto por timestamp)
        self.graph_data_timestamps = []
        self.graph_data_values = []
        
        # Frame actual para procesamiento
        self.current_raw_frame = None
        self.current_graph_type = "Espontáneo (Simple)"
        
        self.pupil_filter = PupilSignalFilter(
            window_size=50,           # Ventana más grande = más suavizado
            filter_type="savgol"      # Mantener Savitzky-Golay
            )
        self.pixel_calibrator = PixelToDegreesCalibrator(calibration_frames=10)

        self.last_point = None
        self.last_frame = 0
        self.torok_region_start = 40.0
        self.torok_region_end = 90.0
        
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
        self.cleanup_video_resources()

        # Inicializar procesador rápido
        self.fast_processor = FastVideoProcessor(self.thresholds)
        if hasattr(self, 'pixel_calibrator'):
            self.pixel_calibrator.reset_calibration()
        
        try:
            with open(file_path, 'rb') as f:
                video_data = f.read()
                
            self.video_player = SimpleVideoPlayer(video_data)
            self.video_player.frame_ready.connect(self._on_frame_ready)
            self.video_player.video_loaded.connect(self._on_video_loaded)
            self.video_player.duration_changed.connect(self._on_duration_changed)
            
            # Iniciar thread
            self.video_player.start()
            self.clear_graph_data()
            
        except Exception as e:
            print(f"Error cargando video: {e}")
            self.status_updated.emit(f"Error cargando video: {str(e)}")
    
    # === AGREGAR MÉTODO PARA OBTENER INFO DE CALIBRACIÓN ===
    def get_calibration_info(self) -> dict:
        """Obtener información de calibración actual"""
        if hasattr(self, 'pixel_calibrator'):
            return self.pixel_calibrator.get_calibration_info()
        return {}


    def cleanup_video_resources(self):
        """
        Limpiar correctamente todos los recursos de video y threads antes de cargar nuevo video
        """
        try:
            # 1. Detener y limpiar video_player existente
            if hasattr(self, 'video_player') and self.video_player is not None:
                print("Limpiando video_player anterior...")
                
                # Detener el thread
                self.video_player.stop()
                
                # Desconectar señales para evitar callbacks
                try:
                    self.video_player.frame_ready.disconnect()
                    self.video_player.video_loaded.disconnect() 
                    self.video_player.duration_changed.disconnect()
                except:
                    pass  # Ignorar si ya están desconectadas
                
                # Esperar a que termine el thread (máximo 3 segundos)
                if self.video_player.isRunning():
                    self.video_player.quit()
                    if not self.video_player.wait(3000):  # 3 segundos timeout
                        print("Warning: Thread no terminó en tiempo esperado")
                        # Forzar terminación si es necesario
                        self.video_player.terminate()
                        self.video_player.wait(1000)  # Esperar 1 segundo más
                
                print("Video_player limpiado correctamente")
                self.video_player = None
            
            # 2. Limpiar fast_processor si existe
            if hasattr(self, 'fast_processor') and self.fast_processor is not None:
                print("Limpiando fast_processor...")
                # El fast_processor no es thread, pero limpiar referencias
                self.fast_processor = None
            
            # 3. Limpiar timer de visualización si existe
            if hasattr(self, 'visualization_timer') and self.visualization_timer is not None:
                if self.visualization_timer.isActive():
                    self.visualization_timer.stop()
                print("Timer de visualización detenido")
            
            # 4. Limpiar datos de gráfico para liberar memoria
            if hasattr(self, 'graph_data_timestamps'):
                self.graph_data_timestamps.clear()
            if hasattr(self, 'graph_data_values'):
                self.graph_data_values.clear()
            
            # 5. Limpiar frame actual
            self.current_raw_frame = None
            
            print("Recursos de video limpiados exitosamente")
            
        except Exception as e:
            print(f"Error durante limpieza de recursos: {e}")
            # Asegurar que las referencias se limpien aunque haya error
            self.video_player = None
            self.fast_processor = None
            self.current_raw_frame = None
        
    
    # ========== MÉTODOS DE EVENTOS DE VIDEO ==========
    
    def _on_video_loaded(self, success: bool):
        """Manejar evento de video cargado"""
        if success:
            self.status_updated.emit("Video cargado correctamente")
            
            # Obtener información del video
            total_frames = self.video_player.get_total_frames()
            max_duration = self.video_player.get_duration()
            
            # NUEVO: Configurar slider para usar frames directamente
            self.total_frames = total_frames
            self.fps = self.video_player.get_fps()
            
            # Emitir señal especial para configurar slider con frames
            self.slider_frame_config.emit(total_frames)  # Nueva señal
            
            self.graph_duration_adjusted.emit(max_duration)
            
            # Iniciar timer para visualización en tiempo real
            #self.visualization_timer.start(100)
            
            # Buscar frame inicial
            self.video_player.seek_to_frame(0)
            
            self.video_loaded.emit(True, max_duration)
        else:
            self.status_updated.emit("Error cargando video")
            self.video_loaded.emit(False, 0.0)
            
    def set_frame_position(self, frame_number: int):
        """
        NUEVO: Establecer posición por número de frame exacto
        """
        if not self.video_player:
            return
        
        # Asegurar que el frame está en rango válido
        frame_number = max(0, min(frame_number, self.total_frames - 1))
        self.current_frame = frame_number
        # Obtener configuración específica para este frame
        frame_config = self.get_frame_config(frame_number)
        
        # Actualizar FastVideoProcessor con configuración específica del frame
        if self.fast_processor:
            self.fast_processor.update_thresholds(frame_config)
        
        # Buscar frame exacto
        self.video_player.seek_to_frame(frame_number)
        
        # Calcular tiempo para mostrar
        current_time = frame_number / self.fps if self.fps > 0 else 0
        max_time = self.video_player.get_duration()
        
        # Emitir señales de actualización
        self.time_info_updated.emit(current_time, max_time)
        self.time_line_position_updated.emit(current_time)
        self.frame_info_updated.emit(frame_number, self.total_frames)  # Nueva señal
        #self.update_config_labels()
        
        
                            
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
                    print(f"{self.last_frame} - {self.current_frame}")
                    pupil_x, pupil_y, detected, vis_frame = self.fast_processor.process_frame(frame)
                    # Emitir frame procesado para mostrar
                    self.frame_ready.emit(vis_frame)
                    if self.last_point is None:
                    # Primer valor siempre aceptado (o con validación mínima)
                        self.last_point = pupil_x
                        
                    if self.last_point != 0:  # Evitar división por cero
                        relative_change = abs((pupil_x - self.last_point) / self.last_point)
                    else:
                        # Si last_point es 0, cualquier valor no cero es un cambio infinito
                        relative_change = float('inf') if pupil_x != 0 else 0

                    # Si el cambio es mayor al 50%, NO pasamos la prueba (ignoramos el punto)
                    if relative_change <= 0.50:  # Cambio aceptable (≤ 50%)
                        current_time = self.video_player.get_current_time() if self.video_player else 0
                        
                        # === NUEVA LÍNEA: CALIBRAR PIXELES A GRADOS ===
                        pupil_degrees = self.pixel_calibrator.calibrate_pixel_to_degrees(pupil_x)
                        
                        # === MODIFICAR: USAR GRADOS EN LUGAR DE PIXELES ===
                        filtered_pupil_degrees = self.pupil_filter.process_pupil_x(current_time, pupil_degrees, detected)
                        
                        if self.last_frame < self.current_frame:
                            # === MODIFICAR: AGREGAR GRADOS AL GRÁFICO ===
                            self.add_point_to_graph(current_time, filtered_pupil_degrees)
                        self.last_point = pupil_x  # Actualizamos solo si fue aceptado
                        

                    else:
                        # Opcional: emitir advertencia o usar último valor válido
                        pass
                        #print(f"Cambio excesivo en pupil_x: {self.last_point} -> {pupil_x} (>{20}%) - ignorado")
                        # No actualizamos last_point, y no agregamos el punto
                    self.last_frame = self.current_frame

                except Exception as e:
                    print(f"Error procesando frame: {e}")
                    self.frame_ready.emit(frame)
            else:
                self.frame_ready.emit(frame)

    # === AGREGAR MÉTODO PARA REINICIAR CALIBRACIÓN ===
    def reset_pixel_calibration(self):
        """Reiniciar calibración de pixeles (útil para nuevo video)"""
        if hasattr(self, 'pixel_calibrator'):
            self.pixel_calibrator.reset_calibration()
            self.status_updated.emit("Calibración de pixeles reiniciada")
        
                
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
        
        # ✅ ACTUALIZAR VISUALIZACIÓN SOLO CUANDO CAMBIAS THRESHOLD
        self.update_current_frame_visualization()  # Una sola vez, no cada 100ms
        
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
        #self.update_config_labels()
        
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
        """
        DEPRECATED: Usar set_frame_position en su lugar
        Este método se mantiene por compatibilidad pero redirige a frames
        """
        # Si el slider está configurado para frames (0 a total_frames)
        if hasattr(self, 'total_frames'):
            self.set_frame_position(slider_value)
        else:
            # Comportamiento antiguo por compatibilidad
            if not self.video_player:
                return
            
            max_time = self.video_player.get_duration()
            current_time = (slider_value / 1000.0) * max_time
            current_frame = int(current_time * self.video_player.get_fps())
            self.set_frame_position(current_frame)
                
    def update_current_frame_visualization(self):
        """Actualizar visualización del frame actual"""
        if self.current_raw_frame is None or not self.fast_processor:
            return
            
        try:
            # Procesar frame actual con parámetros actualizados
            _, _, _, vis_frame = self.fast_processor.process_frame(self.current_raw_frame, False)
            
            # Emitir frame procesado
            if vis_frame is not None:
                self.frame_ready.emit(vis_frame)
                
        except Exception as e:
            print(f"Error actualizando visualización: {e}")
            
    # ========== MÉTODOS DE GRÁFICO ==========
    
    def add_point_to_graph(self, timestamp: float, value: float):
        #print(f"🟦 DEBUG: Agregando punto {timestamp:.2f}, {value:.2f}")

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
                if len(self.graph_data_timestamps) > 5000:
                    self.graph_data_timestamps = self.graph_data_timestamps[-500:]
                    self.graph_data_values = self.graph_data_values[-500:]
            
            # Emitir datos actualizados
            #print(f"🟦 DEBUG: Emitiendo {len(self.graph_data_timestamps)} puntos")

            self.graph_data_updated.emit(self.graph_data_timestamps, self.graph_data_values)
            if self.torok_region_start <= timestamp <= self.torok_region_end:
                self.update_torok_data()
            
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
        
    #======= TOROK =====
    
    def set_torok_region(self, start_time: float, end_time: float):
        """Establecer nueva región Torok y actualizar datos"""
        self.torok_region_start = start_time
        self.torok_region_end = end_time
        
        # Re-emitir datos filtrados para Torok
        if self.graph_data_timestamps and self.graph_data_values:
            self.update_torok_data()

    def update_torok_data(self):
        """Actualizar datos del gráfico Torok basado en región actual"""
        if not self.graph_data_timestamps or not self.graph_data_values:
            self.torok_data_updated.emit([], [])
            return
        
        # Filtrar datos en el rango Torok
        filtered_timestamps = []
        filtered_values = []
        
        for t, v in zip(self.graph_data_timestamps, self.graph_data_values):
            if self.torok_region_start <= t <= self.torok_region_end:
                filtered_timestamps.append(t)
                filtered_values.append(v)
        
        self.torok_data_updated.emit(filtered_timestamps, filtered_values)
