import cv2
import os
import time
import threading
from queue import Queue, Empty
from typing import Optional
import tempfile
import shutil

class VideoRecorder:
    """
    Tu VideoRecorder original + FPS dinámicos reales
    """
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.is_recording = False
        self.video_writer = None
        self.current_test_id = None
        
        # Configuración simple como tu ejemplo
        self.fourcc = cv2.VideoWriter_fourcc(*'XVID')
        self.fps = 60.0  # Temporal para grabación inicial
        
        # Cola para frames
        self.frame_queue = Queue(maxsize=100)
        self.recording_thread = None
        self.stop_thread = False
        
        # Variables para el nombre del archivo
        self.current_filename = None
        self.temp_filename = None
        
        # Estadísticas y tracking para FPS dinámicos
        self.frames_written = 0
        self.recording_start_time = None
        self.recording_end_time = None
        
    def start_recording(self, test_id: str):
        """Iniciar grabación simple - TU LÓGICA ORIGINAL"""
        if self.is_recording:
            print("Ya hay una grabación en curso")
            return False
            
        try:
            # Crear nombres de archivo
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            self.current_filename = f"video_{timestamp}.avi"
            
            # Crear archivo temporal primero
            temp_fd, self.temp_filename = tempfile.mkstemp(suffix='.avi', prefix='video_temp_')
            os.close(temp_fd)
            
            # VideoWriter a archivo temporal - USANDO TU RESOLUCIÓN FIJA
            self.video_writer = cv2.VideoWriter(self.temp_filename, self.fourcc, self.fps, (640, 480))
            
            if not self.video_writer.isOpened():
                print("Error: No se pudo crear VideoWriter")
                return False
            
            # Configurar estado
            self.current_test_id = test_id
            self.is_recording = True
            self.frames_written = 0
            self.stop_thread = False
            self.recording_start_time = time.time()
            
            # Iniciar hilo de escritura
            self.recording_thread = threading.Thread(target=self._recording_worker, daemon=True)
            self.recording_thread.start()
            
            print(f"Grabación iniciada: {self.current_filename} (temporal: {self.temp_filename})")
            return True
            
        except Exception as e:
            print(f"Error iniciando grabación: {e}")
            return False
    
    def add_frame(self, gray_frame):
        """Agregar frame a la grabación - TU LÓGICA ORIGINAL"""
        if not self.is_recording:
            return
            
        try:
            # Agregar a la cola sin bloquear
            self.frame_queue.put(gray_frame, block=False)
        except:
            # Cola llena, descartar frame
            pass
    
    def stop_recording(self):
        """Detener grabación y recrear con FPS correctos"""
        if not self.is_recording:
            return None
            
        print("Deteniendo grabación de video...")
        
        # Marcar tiempo de fin
        self.recording_end_time = time.time()
        
        # Señalizar parada
        self.stop_thread = True
        
        # Esperar que termine el hilo
        if self.recording_thread and self.recording_thread.is_alive():
            self.recording_thread.join(timeout=3.0)
        
        # Cerrar VideoWriter temporal
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
        
        print(f"Video grabado: {self.frames_written} frames")
        
        # Recrear video con FPS correctos
        final_video_path = self._create_final_video_with_correct_fps()
        
        # Limpiar archivo temporal
        self._cleanup_temp_files()
        
        # Resetear estado
        self.is_recording = False
        self.current_test_id = None
        self.frames_written = 0
        
        return final_video_path
    
    def _create_final_video_with_correct_fps(self):
        """Recrear video con FPS calculados dinámicamente"""
        if not self.recording_start_time or not self.recording_end_time or self.frames_written == 0:
            print("No hay suficientes datos para calcular FPS")
            return None
            
        try:
            # Calcular FPS reales
            duration = self.recording_end_time - self.recording_start_time
            real_fps = self.frames_written / duration
            
            # Validar FPS (evitar valores extremos)
            if real_fps < 10:
                real_fps = 30.0
                print(f"FPS muy bajos, usando 30 FPS")
            elif real_fps > 200:
                real_fps = 120.0
                print(f"FPS muy altos, usando 120 FPS")
            
            print(f"FPS reales calculados: {real_fps:.1f} ({self.frames_written} frames en {duration:.1f}s)")
            
            # Abrir video temporal para leer frames
            temp_cap = cv2.VideoCapture(self.temp_filename)
            if not temp_cap.isOpened():
                print("Error: No se pudo abrir video temporal")
                return None
            
            # Crear video final con FPS correctos
            final_writer = cv2.VideoWriter(
                self.current_filename,
                self.fourcc,
                real_fps,  # FPS DINÁMICOS CALCULADOS
                (640, 480)
            )
            
            if not final_writer.isOpened():
                print("Error: No se pudo crear video final")
                temp_cap.release()
                return None
            
            # Copiar todos los frames del temporal al final
            frames_copied = 0
            while True:
                ret, frame = temp_cap.read()
                if not ret:
                    break
                final_writer.write(frame)
                frames_copied += 1
            
            # Limpiar recursos
            temp_cap.release()
            final_writer.release()
            
            print(f"Video final creado: {self.current_filename} ({frames_copied} frames @ {real_fps:.1f} FPS)")
            
            # Verificar que el archivo final existe
            if os.path.exists(self.current_filename):
                return self.current_filename
            else:
                print("Error: Archivo final no fue creado")
                return None
                
        except Exception as e:
            print(f"Error recreando video: {e}")
            return None
    
    def _cleanup_temp_files(self):
        """Limpiar archivo temporal"""
        if self.temp_filename and os.path.exists(self.temp_filename):
            try:
                os.remove(self.temp_filename)
                print(f"Archivo temporal eliminado: {self.temp_filename}")
            except Exception as e:
                print(f"Error eliminando temporal: {e}")
    
    def _add_padding(self, frame):
        """Agregar padding negro para ajustar frame a 640x480 sin deformar - TU FUNCIÓN ORIGINAL"""
        current_height, current_width = frame.shape[:2]
        target_width, target_height = 640, 480
        
        # Calcular padding necesario
        pad_width = target_width - current_width
        pad_height = target_height - current_height
        
        # Centrar la imagen
        pad_left = pad_width // 2
        pad_right = pad_width - pad_left
        pad_top = pad_height // 2
        pad_bottom = pad_height - pad_top
        
        # Aplicar padding negro
        padded_frame = cv2.copyMakeBorder(
            frame,
            pad_top, pad_bottom, pad_left, pad_right,
            cv2.BORDER_CONSTANT,
            value=[0, 0, 0]  # Negro
        )
        
        return padded_frame
    
    def _recording_worker(self):
        """Hilo worker simple - TU LÓGICA ORIGINAL"""
        print("Worker iniciado")
        
        try:
            while not self.stop_thread:
                try:
                    # Obtener frame
                    frame = self.frame_queue.get(timeout=0.1)
                    
                    if self.video_writer and frame is not None:
                        # Convertir gray a BGR
                        if len(frame.shape) == 2:
                            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                        else:
                            frame_bgr = frame
                        
                        # Agregar padding en lugar de redimensionar - TU FUNCIÓN
                        frame_padded = self._add_padding(frame_bgr)
                        
                        # Escribir al video
                        self.video_writer.write(frame_padded)
                        self.frames_written += 1
                        
                except Empty:
                    continue
                except Exception as e:
                    print(f"Error en worker: {e}")
                    break
        
        except Exception as e:
            print(f"Error crítico en worker: {e}")
        
        print(f"Worker terminado. Total frames: {self.frames_written}")
    
    def save_to_siev(self, video_path: str) -> bool:
        """Guardar video en el archivo .siev del usuario actual - TU FUNCIÓN ORIGINAL"""
        try:
            if not os.path.exists(video_path):
                print(f"Error: Archivo de video no encontrado: {video_path}")
                return False
            
            siev_manager = self.main_window.siev_manager
            siev_path = self.main_window.current_user_siev
            
            if not siev_manager or not siev_path:
                print("Error: Sistema de usuarios no disponible")
                return False
            
            # Obtener información de la prueba actual
            current_test_id = self.main_window.protocol_manager.get_current_test_id()
            test_data = {
                'id': current_test_id,
                'tipo': 'video_update',
            }            
            
            # Agregar video al .siev
            success = siev_manager.add_test_to_siev(
                siev_path, 
                test_data, 
                csv_data=None,
                video_path=video_path
            )
            
            if success:
                print(f"Video guardado en .siev: {self.current_test_id}")
                # Limpiar archivo temporal
                try:
                    os.remove(video_path)
                    print(f"Archivo temporal eliminado: {video_path}")
                except:
                    pass
                return True
            else:
                print("Error guardando video en .siev")
                return False
                
        except Exception as e:
            print(f"Error guardando en .siev: {e}")
            return False
    
    def _get_current_resolution(self) -> Optional[tuple]:
        """Dummy para compatibilidad - TU FUNCIÓN ORIGINAL"""
        return (640, 480)
    
    def get_status(self) -> dict:
        """Estado actual - TU FUNCIÓN ORIGINAL"""
        return {
            'is_recording': self.is_recording,
            'test_id': self.current_test_id,
            'frames_written': self.frames_written
        }