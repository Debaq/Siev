#!/usr/bin/env python3
"""
Simple Video Player
Reproductor de video simple que maneja carga, auto-crop y reproducción.
NO hace análisis de pupila - solo prepara frames limpios.
"""

import cv2
import numpy as np
import time
import tempfile
import os
from typing import Optional, Tuple
from PySide6.QtCore import QThread, Signal


class SimpleVideoPlayer(QThread):
    """
    Reproductor de video simple que maneja:
    - Carga de video desde datos binarios
    - Auto-crop (detección y recorte de espacios negros)
    - Reproducción/pausa/seek
    - Emisión de frames recortados y limpios
    """
    
    frame_ready = Signal(object)  # frame recortado limpio
    video_loaded = Signal(bool)   # Señal cuando el video se carga
    duration_changed = Signal(float)  # Duración total del video
    
    def __init__(self, video_data):
        super().__init__()
        
        # === DATOS DEL VIDEO ===
        self.video_data = video_data
        self.temp_video_path = None
        self.cap = None
        self.total_frames = 0
        self.fps = 30.0
        self.duration = 0.0
        
        # === ESTADO DE REPRODUCCIÓN ===
        self.is_playing = False
        self.current_frame_index = 0
        self.current_time = 0.0
        
        # === CONTROL DE HILO ===
        self.running = True
        
        # === AUTO-CROP ===
        self.auto_crop_enabled = True
        self.crop_area = None  # (x, y, width, height)
        self.crop_detected = False
        
    def load_video_from_data(self) -> bool:
        """Cargar video desde datos binarios"""
        try:
            print("SimpleVideoPlayer: Cargando video desde datos...")
            
            # Crear archivo temporal
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
                temp_file.write(self.video_data)
                self.temp_video_path = temp_file.name
            
            # Abrir con OpenCV
            self.cap = cv2.VideoCapture(self.temp_video_path)
            
            if not self.cap.isOpened():
                print("SimpleVideoPlayer: Error - No se pudo abrir el video")
                self.video_loaded.emit(False)
                return False
            
            # Obtener propiedades del video
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.duration = self.total_frames / self.fps if self.fps > 0 else 0
            
            print(f"SimpleVideoPlayer: Video cargado - {self.total_frames} frames, {self.fps} FPS, {self.duration:.2f}s")
            
            # Detectar área de recorte automáticamente
            if self.auto_crop_enabled:
                self._detect_crop_area()
            
            # Emitir señales
            self.video_loaded.emit(True)
            self.duration_changed.emit(self.duration)
            
            return True
            
        except Exception as e:
            print(f"SimpleVideoPlayer: Error cargando video: {e}")
            self.video_loaded.emit(False)
            return False
    
    def _detect_crop_area(self):
        """Detectar área de recorte para eliminar espacios negros"""
        try:
            print("SimpleVideoPlayer: Detectando área de auto-crop...")
            
            if not self.cap:
                return
                
            # Guardar posición actual
            original_pos = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
            
            # Buscar en varios frames para detectar crop area consistente
            sample_frames = [
                int(self.total_frames * 0.1),   # 10%
                int(self.total_frames * 0.3),   # 30%
                int(self.total_frames * 0.5),   # 50%
                int(self.total_frames * 0.7),   # 70%
                int(self.total_frames * 0.9),   # 90%
            ]
            
            crop_areas = []
            
            for frame_idx in sample_frames:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = self.cap.read()
                
                if ret:
                    crop_area = self._calculate_crop_area(frame)
                    if crop_area:
                        crop_areas.append(crop_area)
            
            # Restaurar posición original
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, original_pos)
            
            # Calcular área de crop consenso
            if crop_areas:
                # Usar el crop más conservador (más grande)
                min_x = min(area[0] for area in crop_areas)
                min_y = min(area[1] for area in crop_areas)
                max_x2 = max(area[0] + area[2] for area in crop_areas)
                max_y2 = max(area[1] + area[3] for area in crop_areas)
                
                self.crop_area = (min_x, min_y, max_x2 - min_x, max_y2 - min_y)
                self.crop_detected = True
                
                print(f"SimpleVideoPlayer: Auto-crop detectado: {self.crop_area}")
            else:
                print("SimpleVideoPlayer: No se pudo detectar área de auto-crop")
                self.crop_area = None
                self.crop_detected = False
                
        except Exception as e:
            print(f"SimpleVideoPlayer: Error detectando auto-crop: {e}")
            self.crop_area = None
            self.crop_detected = False
    
    def _calculate_crop_area(self, frame: np.ndarray, threshold: int = 30) -> Optional[Tuple]:
        """
        Calcular área de recorte para un frame específico
        
        Args:
            frame: Frame a analizar
            threshold: Umbral para detectar espacios negros
            
        Returns:
            Tupla (x, y, width, height) o None si no hay crop necesario
        """
        try:
            # Convertir a escala de grises
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape
            
            # Encontrar límites no negros
            # Buscar desde arriba
            top = 0
            for i in range(h):
                if np.max(gray[i, :]) > threshold:
                    top = i
                    break
            
            # Buscar desde abajo
            bottom = h - 1
            for i in range(h - 1, -1, -1):
                if np.max(gray[i, :]) > threshold:
                    bottom = i
                    break
            
            # Buscar desde izquierda
            left = 0
            for i in range(w):
                if np.max(gray[:, i]) > threshold:
                    left = i
                    break
            
            # Buscar desde derecha
            right = w - 1
            for i in range(w - 1, -1, -1):
                if np.max(gray[:, i]) > threshold:
                    right = i
                    break
            
            # Verificar si hay crop significativo
            crop_width = right - left + 1
            crop_height = bottom - top + 1
            
            # Solo aplicar crop si hay una reducción significativa (>5%)
            width_reduction = (w - crop_width) / w
            height_reduction = (h - crop_height) / h
            
            if width_reduction > 0.05 or height_reduction > 0.05:
                return (left, top, crop_width, crop_height)
            
            return None
            
        except Exception as e:
            print(f"SimpleVideoPlayer: Error calculando crop area: {e}")
            return None
    
    def seek_to_frame(self, frame_index: int):
        """Buscar frame específico"""
        try:
            if not self.cap:
                return
                
            frame_index = max(0, min(frame_index, self.total_frames - 1))
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            self.current_frame_index = frame_index
            self.current_time = frame_index / self.fps if self.fps > 0 else 0
            
            # Leer y emitir frame actual
            ret, frame = self.cap.read()
            if ret:
                processed_frame = self._process_frame(frame)
                self.frame_ready.emit(processed_frame)
                
        except Exception as e:
            print(f"SimpleVideoPlayer: Error en seek_to_frame: {e}")
    
    def seek_to_time(self, seconds: float):
        """Buscar tiempo específico"""
        if self.fps > 0:
            frame_index = int(seconds * self.fps)
            self.seek_to_frame(frame_index)
    
    def play(self):
        """Iniciar reproducción"""
        self.is_playing = True
        print("SimpleVideoPlayer: Reproducción iniciada")
    
    def pause(self):
        """Pausar reproducción"""
        self.is_playing = False
        print("SimpleVideoPlayer: Reproducción pausada")
    
    def stop(self):
        """Detener reproductor"""
        self.running = False
        self.is_playing = False
        print("SimpleVideoPlayer: Deteniendo...")
    
    def _process_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Procesar frame aplicando auto-crop
        
        Args:
            frame: Frame original
            
        Returns:
            Frame procesado (recortado si es necesario)
        """
        try:
            if not self.auto_crop_enabled or not self.crop_area:
                return frame
            
            # Aplicar crop
            x, y, w, h = self.crop_area
            h_frame, w_frame = frame.shape[:2]
            
            # Verificar límites
            x = max(0, min(x, w_frame))
            y = max(0, min(y, h_frame))
            w = max(1, min(w, w_frame - x))
            h = max(1, min(h, h_frame - y))
            
            cropped_frame = frame[y:y+h, x:x+w]
            
            return cropped_frame
            
        except Exception as e:
            print(f"SimpleVideoPlayer: Error procesando frame: {e}")
            return frame
    
    def get_current_time(self) -> float:
        """Obtener tiempo actual"""
        return self.current_time
    
    def get_duration(self) -> float:
        """Obtener duración total"""
        return self.duration
    
    def get_current_frame_index(self) -> int:
        """Obtener índice de frame actual"""
        return self.current_frame_index
    
    def get_total_frames(self) -> int:
        """Obtener total de frames"""
        return self.total_frames
    
    def get_fps(self) -> float:
        """Obtener FPS"""
        return self.fps
    
    def set_auto_crop_enabled(self, enabled: bool):
        """Habilitar/deshabilitar auto-crop"""
        self.auto_crop_enabled = enabled
        if enabled and not self.crop_detected:
            self._detect_crop_area()
    
    def get_crop_info(self) -> dict:
        """Obtener información de crop"""
        return {
            'enabled': self.auto_crop_enabled,
            'detected': self.crop_detected,
            'area': self.crop_area
        }
    
    def run(self):
        """Loop principal del thread"""
        print("SimpleVideoPlayer: Thread iniciado")
        
        # Cargar video
        if not self.load_video_from_data():
            return
        
        # Loop principal de reproducción
        last_time = time.time()
        
        while self.running:
            current_time = time.time()
            
            if self.is_playing and self.cap:
                # Calcular si es momento de avanzar frame
                elapsed = current_time - last_time
                frame_duration = 1.0 / self.fps if self.fps > 0 else 0.033
                
                if elapsed >= frame_duration:
                    # Avanzar al siguiente frame
                    self.current_frame_index += 1
                    
                    if self.current_frame_index >= self.total_frames:
                        # Fin del video
                        self.current_frame_index = self.total_frames - 1
                        self.is_playing = False
                        print("SimpleVideoPlayer: Fin del video")
                    else:
                        # Leer y procesar frame
                        ret, frame = self.cap.read()
                        if ret:
                            processed_frame = self._process_frame(frame)
                            self.frame_ready.emit(processed_frame)
                            
                            # Actualizar tiempo
                            self.current_time = self.current_frame_index / self.fps if self.fps > 0 else 0
                    
                    last_time = current_time
            
            # Pequeña pausa para no sobrecargar CPU
            time.sleep(0.001)
        
        # Cleanup
        if self.cap:
            self.cap.release()
        
        if self.temp_video_path and os.path.exists(self.temp_video_path):
            try:
                os.unlink(self.temp_video_path)
                print("SimpleVideoPlayer: Archivo temporal eliminado")
            except:
                pass
        
        print("SimpleVideoPlayer: Thread finalizado")