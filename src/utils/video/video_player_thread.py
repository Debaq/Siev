"""
VideoPlayerThread.py
Thread para reproducir videos grabados frame por frame con análisis de pupila
"""

import cv2
import numpy as np
import time
import tempfile
import os
from PySide6.QtCore import QThread, Signal
from PySide6.QtCore import QTimer


class VideoPlayerThread(QThread):
    frame_ready = Signal(object, list, object)  # frame, pupil_positions, gray_frame
    video_loaded = Signal(bool)  # Señal cuando el video se carga
    duration_changed = Signal(float)  # Duración total del video
    
    def __init__(self, video_data, analysis_config=None):
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
        
        # === CONFIGURACIÓN DE ANÁLISIS ===
        self.analysis_config = analysis_config or {
            'threslhold': [50, 50],
            'erode': [2, 2], 
            'nose_width': 0.25,
            'eye_height': 0.5
        }
        
        # === CONTROL DE HILO ===
        self.running = True
        
        # === PROCESAMIENTO DE PUPILA ===
        # No usar PupilAnalyzer específico, usar análisis básico integrado
        self.pupil_analyzer = None
        self.auto_crop_enabled = True  # Activado por defecto
        self.crop_area = None  # (x, y, width, height)
        
    def load_video_from_data(self):
        """Cargar video desde datos binarios"""
        try:
            print("Cargando video desde datos...")
            
            # Crear archivo temporal
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
                temp_file.write(self.video_data)
                self.temp_video_path = temp_file.name
            
            # Abrir con OpenCV
            self.cap = cv2.VideoCapture(self.temp_video_path)
            
            if not self.cap.isOpened():
                print("Error: No se pudo abrir el video")
                self.video_loaded.emit(False)
                return False
            
            # Obtener propiedades del video
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
            self.duration = self.total_frames / self.fps
            
            print(f"Video cargado: {self.total_frames} frames, {self.fps} FPS, {self.duration:.2f}s")
            
            # Inicializar auto-crop ANTES de procesar primer frame
            if self.auto_crop_enabled:
                self.initialize_auto_crop()
            
            # === MOSTRAR PRIMER FRAME INMEDIATAMENTE ===
            # Ir al primer frame
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.current_frame_index = 0
            self.current_time = 0.0
            
            # Leer y procesar primer frame
            self._read_and_process_current_frame()
            
            # Emitir señales
            self.video_loaded.emit(True)
            self.duration_changed.emit(self.duration)
            
            return True
            
        except Exception as e:
            print(f"Error cargando video: {e}")
            self.video_loaded.emit(False)
            return False
    
    
    
    def seek_to_time(self, time_seconds):
        """Buscar a un tiempo específico"""
        if not self.cap:
            return
            
        # Calcular frame correspondiente
        target_frame = int(time_seconds * self.fps)
        target_frame = max(0, min(target_frame, self.total_frames - 1))
        
        # Establecer posición
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        self.current_frame_index = target_frame
        self.current_time = target_frame / self.fps
        
        # Leer y procesar frame inmediatamente
        self._read_and_process_current_frame()
    
    def seek_to_frame(self, frame_index):
        """Buscar a un frame específico"""
        if not self.cap:
            return
            
        frame_index = max(0, min(frame_index, self.total_frames - 1))
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        self.current_frame_index = frame_index
        self.current_time = frame_index / self.fps
        
        # Leer y procesar frame inmediatamente
        self._read_and_process_current_frame()
    
    def play(self):
        """Iniciar reproducción"""
        self.is_playing = True
        print(f"Reproduciendo desde frame {self.current_frame_index}")
    
    def pause(self):
        """Pausar reproducción"""
        self.is_playing = False
        print("Reproducción pausada")
    
    def stop(self):
        """Detener completamente"""
        print("Deteniendo VideoPlayerThread...")
        self.running = False
        self.is_playing = False
        
        # Limpiar recursos
        if self.cap:
            self.cap.release()
            self.cap = None
        
        if self.temp_video_path and os.path.exists(self.temp_video_path):
            try:
                os.remove(self.temp_video_path)
                print("Archivo temporal eliminado")
            except:
                pass
    
    def _read_and_process_current_frame(self):
        """Leer y procesar el frame actual"""
        if not self.cap:
            return
            
        ret, frame = self.cap.read()
        if not ret:
            return
        
        # Procesar frame
        processed_frame, pupil_positions, gray_frame = self._process_frame(frame)
        
        # Emitir resultado
        self.frame_ready.emit(processed_frame, pupil_positions, gray_frame)
    
  
    def _process_frame(self, frame):
        """Procesar frame para análisis de pupila"""
        try:
            # === APLICAR AUTO-CROP PRIMERO ===
            if self.auto_crop_enabled and hasattr(self, 'crop_area') and self.crop_area:
                frame = self.apply_auto_crop(frame)
                print(f"Auto-crop aplicado - Nueva resolución: {frame.shape[1]}x{frame.shape[0]}")
            
            # Convertir a gray
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Copia para dibujar
            display_frame = frame.copy()
            
            # Análisis de pupila básico
            pupil_positions = [None, None]
            
            if self.pupil_analyzer:
                # Usar analizador avanzado si está disponible
                pupil_positions = self.pupil_analyzer.analyze_frame(gray, self.analysis_config)
            else:
                # Análisis básico de fallback
                pupil_positions = self._basic_pupil_analysis(gray)
            
            # Dibujar resultados en el frame
            self._draw_pupil_detection(display_frame, pupil_positions)
            
            # Convertir a RGB para Qt
            display_frame_rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            
            return display_frame_rgb, pupil_positions, gray
            
        except Exception as e:
            print(f"Error procesando frame: {e}")
            # Retornar frame sin procesar
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            return frame_rgb, [None, None], None

    
    def _basic_pupil_analysis(self, gray_frame):
        """Análisis básico de pupila como fallback"""
        try:
            # Implementación básica - encontrar contornos circulares oscuros
            height, width = gray_frame.shape
            
            # Dividir en mitades (izquierda y derecha)
            left_half = gray_frame[:, :width//2]
            right_half = gray_frame[:, width//2:]
            
            pupil_positions = [None, None]
            
            # Procesar cada mitad
            for i, (region, x_offset) in enumerate([(right_half, 0), (left_half, width//2)]):
                # Aplicar umbralización
                threshold = self.analysis_config['threslhold'][i]
                _, binary = cv2.threshold(region, threshold, 255, cv2.THRESH_BINARY_INV)
                
                # Erosión
                erode_size = self.analysis_config['erode'][i]
                if erode_size > 0:
                    kernel = np.ones((erode_size, erode_size), np.uint8)
                    binary = cv2.erode(binary, kernel, iterations=1)
                
                # Encontrar contornos
                contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                if contours:
                    # Encontrar el contorno más circular y de tamaño apropiado
                    best_contour = None
                    best_score = 0
                    
                    for contour in contours:
                        area = cv2.contourArea(contour)
                        if 100 < area < 2000:  # Tamaño razonable para pupila
                            # Calcular circularidad
                            perimeter = cv2.arcLength(contour, True)
                            if perimeter > 0:
                                circularity = 4 * np.pi * area / (perimeter * perimeter)
                                if circularity > best_score:
                                    best_score = circularity
                                    best_contour = contour
                    
                    if best_contour is not None and best_score > 0.3:
                        # Calcular centro
                        M = cv2.moments(best_contour)
                        if M["m00"] != 0:
                            cx = int(M["m10"] / M["m00"]) + x_offset
                            cy = int(M["m01"] / M["m00"])
                            pupil_positions[i] = [cx, -cy]  # Y negativo como en el original
            
            return pupil_positions
            
        except Exception as e:
            print(f"Error en análisis básico: {e}")
            return [None, None]
    
    def _draw_pupil_detection(self, frame, pupil_positions):
        """Dibujar detección de pupila en el frame"""
        for i, pos in enumerate(pupil_positions):
            if pos:
                x, y = int(pos[0]), int(-pos[1])  # Y negativo de vuelta a positivo
                
                # Color según ojo
                color = (0, 255, 0) if i == 0 else (255, 0, 0)  # Verde=derecho, Rojo=izquierdo
                
                # Dibujar círculo y cruz
                cv2.circle(frame, (x, y), 5, color, 2)
                cv2.line(frame, (x-10, y), (x+10, y), color, 1)
                cv2.line(frame, (x, y-10), (x, y+10), color, 1)
    
    def update_analysis_config(self, config):
        """Actualizar configuración de análisis"""
        self.analysis_config.update(config)
    
    def get_current_time(self):
        """Obtener tiempo actual"""
        return self.current_time
    
    def get_duration(self):
        """Obtener duración total"""
        return self.duration
    
    def get_current_frame_index(self):
        """Obtener índice de frame actual"""
        return self.current_frame_index
    
    def run(self):
        """Loop principal del thread"""
        print("VideoPlayerThread iniciado")
        
        # Cargar video
        if not self.load_video_from_data():
            return
        
        # Loop principal
        last_time = time.time()
        
        while self.running:
            current_time = time.time()
            
            if self.is_playing:
                # Calcular si es momento de avanzar frame
                elapsed = current_time - last_time
                frame_duration = 1.0 / self.fps
                
                if elapsed >= frame_duration:
                    # Avanzar al siguiente frame
                    self.current_frame_index += 1
                    
                    if self.current_frame_index >= self.total_frames:
                        # Fin del video
                        self.current_frame_index = self.total_frames - 1
                        self.is_playing = False
                        print("Fin del video")
                    
                    # Actualizar tiempo
                    self.current_time = self.current_frame_index / self.fps
                    
                    # Leer y procesar frame
                    self.seek_to_frame(self.current_frame_index)
                    
                    last_time = current_time
            
            # Pequeña pausa para no sobrecargar CPU
            time.sleep(0.001)
        
        print("VideoPlayerThread finalizado")
        
        
    def detect_crop_area(self, frame, threshold=30):
        """
        Detecta automáticamente el área de recorte para eliminar espacios negros
        
        Args:
            frame: Frame de OpenCV (BGR)
            threshold: Umbral para considerar un píxel como "negro" (0-255)
            
        Returns:
            tuple: (x, y, width, height) del área útil
        """
        try:
            # Convertir a escala de grises
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Crear máscara de píxeles que NO son negros
            mask = gray > threshold
            
            # Encontrar coordenadas de píxeles no negros
            coords = np.where(mask)
            
            if len(coords[0]) == 0:
                # Si no hay píxeles útiles, devolver frame completo
                print("No se encontraron píxeles útiles para auto-crop")
                return 0, 0, frame.shape[1], frame.shape[0]
            
            # Calcular bounding box
            y_min, y_max = coords[0].min(), coords[0].max()
            x_min, x_max = coords[1].min(), coords[1].max()
            
            # Añadir pequeño margen de seguridad
            margin = 10
            y_min = max(0, y_min - margin)
            x_min = max(0, x_min - margin)
            y_max = min(frame.shape[0], y_max + margin)
            x_max = min(frame.shape[1], x_max + margin)
            
            width = x_max - x_min
            height = y_max - y_min
            
            # Validar que el área detectada sea significativa
            original_area = frame.shape[0] * frame.shape[1]
            detected_area = width * height
            area_ratio = detected_area / original_area
            
            if area_ratio > 0.95:
                # Si el área detectada es >95% del original, no hay recorte significativo
                print(f"Área detectada muy similar al original ({area_ratio*100:.1f}%), no aplicando crop")
                return 0, 0, frame.shape[1], frame.shape[0]
            
            print(f"Área de recorte detectada: x={x_min}, y={y_min}, w={width}, h={height}")
            print(f"Reducción de área: {(1-area_ratio)*100:.1f}%")
            
            return x_min, y_min, width, height
            
        except Exception as e:
            print(f"Error detectando área de recorte: {e}")
            return 0, 0, frame.shape[1], frame.shape[0]
    
    def apply_auto_crop(self, frame):
        """
        Aplica el recorte automático al frame
        
        Args:
            frame: Frame de OpenCV (BGR)
            
        Returns:
            Frame recortado
        """
        if not hasattr(self, 'crop_area') or self.crop_area is None:
            return frame
            
        try:
            x, y, w, h = self.crop_area
            
            # Validar coordenadas
            if (x + w <= frame.shape[1] and y + h <= frame.shape[0] and 
                x >= 0 and y >= 0 and w > 0 and h > 0):
                
                cropped = frame[y:y+h, x:x+w]
                return cropped
            else:
                print(f"Coordenadas de recorte inválidas: x={x}, y={y}, w={w}, h={h}")
                print(f"Frame shape: {frame.shape}")
                return frame
                
        except Exception as e:
            print(f"Error aplicando recorte: {e}")
            return frame

    def toggle_auto_crop(self, enabled=None):
        """
        Activa/desactiva el auto-crop
        
        Args:
            enabled: True/False para forzar estado, None para alternar
        """
        if enabled is None:
            self.auto_crop_enabled = not getattr(self, 'auto_crop_enabled', False)
        else:
            self.auto_crop_enabled = enabled
            
        if self.auto_crop_enabled and not hasattr(self, 'crop_area'):
            # Inicializar auto-crop si no se ha hecho
            self.initialize_auto_crop()
        
        status = "activado" if self.auto_crop_enabled else "desactivado"
        print(f"Auto-crop {status}")
        
        return self.auto_crop_enabled
    
    def initialize_auto_crop(self):
        """
        Inicializa el auto-crop analizando el primer frame del video
        """
        try:
            if not self.cap:
                print("Error: No hay captura de video disponible para auto-crop")
                return
                
            # Guardar posición actual
            current_pos = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
            
            # Ir al primer frame
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            
            # Leer primer frame
            ret, frame = self.cap.read()
            
            if ret and frame is not None:
                # Detectar área de recorte
                self.crop_area = self.detect_crop_area(frame)
                
                if self.crop_area and self.crop_area != (0, 0, frame.shape[1], frame.shape[0]):
                    # Calcular factor de escalado para mostrar información
                    original_area = frame.shape[0] * frame.shape[1]
                    crop_area_size = self.crop_area[2] * self.crop_area[3]
                    reduction_percent = ((original_area - crop_area_size) / original_area) * 100
                    
                    print(f"Auto-crop inicializado:")
                    print(f"  Resolución original: {frame.shape[1]}x{frame.shape[0]}")
                    print(f"  Resolución recortada: {self.crop_area[2]}x{self.crop_area[3]}")
                    print(f"  Reducción de área: {reduction_percent:.1f}%")
                    print(f"  Área de recorte: x={self.crop_area[0]}, y={self.crop_area[1]}")
                else:
                    print("No se detectó área de recorte significativa, usando frame completo")
                    self.auto_crop_enabled = False
                
            else:
                print("No se pudo leer el primer frame para auto-crop")
                self.crop_area = None
                self.auto_crop_enabled = False
            
            # Restaurar posición original
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, current_pos)
            
        except Exception as e:
            print(f"Error inicializando auto-crop: {e}")
            self.crop_area = None
        self.auto_crop_enabled = False
    
  