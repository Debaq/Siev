import cv2
import os
import time
import threading
from queue import Queue, Empty
from typing import Optional

class VideoRecorder:
    """
    Grabador de video simple que funciona como tu ejemplo
    """
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.is_recording = False
        self.video_writer = None
        self.current_test_id = None
        
        # Configuración simple como tu ejemplo
        self.fourcc = cv2.VideoWriter_fourcc(*'XVID')
        self.fps = 20.0
        
        # Cola para frames
        self.frame_queue = Queue(maxsize=100)
        self.recording_thread = None
        self.stop_thread = False
        
        # Agregar variables para el nombre del archivo
        self.current_filename = None
        
        # Estadísticas
        self.frames_written = 0
        
    def start_recording(self, test_id: str):
        """Iniciar grabación simple"""
        if self.is_recording:
            print("Ya hay una grabación en curso")
            return False
            
        try:
            # Crear archivo en raíz con timestamp
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"video_{timestamp}.avi"
            self.current_filename = filename  # Guardar nombre para stop_recording
            
            # VideoWriter simple como tu ejemplo
            self.video_writer = cv2.VideoWriter(filename, self.fourcc, self.fps, (640, 480))
            
            if not self.video_writer.isOpened():
                print("Error: No se pudo crear VideoWriter")
                return False
            
            # Configurar estado
            self.current_test_id = test_id
            self.is_recording = True
            self.frames_written = 0
            self.stop_thread = False
            
            # Iniciar hilo de escritura
            self.recording_thread = threading.Thread(target=self._recording_worker, daemon=True)
            self.recording_thread.start()
            
            print(f"Grabación iniciada: {filename}")
            return True
            
        except Exception as e:
            print(f"Error iniciando grabación: {e}")
            return False
    
    def add_frame(self, gray_frame):
        """Agregar frame a la grabación"""
        if not self.is_recording:
            return
            
        try:
            # Agregar a la cola sin bloquear
            self.frame_queue.put(gray_frame, block=False)
        except:
            # Cola llena, descartar frame
            pass
    
    def stop_recording(self):
        """Detener grabación"""
        if not self.is_recording:
            return None
            
        print("Deteniendo grabación de video...")
        
        # Señalizar parada
        self.stop_thread = True
        
        # Esperar que termine el hilo
        if self.recording_thread and self.recording_thread.is_alive():
            self.recording_thread.join(timeout=3.0)
        
        # Cerrar VideoWriter
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
        
        print(f"Video grabado: {self.frames_written} frames")
        
        # Obtener path del archivo creado
        video_path = self.current_filename
        
        # Resetear estado
        self.is_recording = False
        self.current_test_id = None
        self.current_filename = None
        self.frames_written = 0
        
        return video_path  # Retornar path real del video
    
    def _add_padding(self, frame):
        """Agregar padding negro para ajustar frame a 640x480 sin deformar"""
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
        """Hilo worker simple"""
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
                        
                        # Agregar padding en lugar de redimensionar
                        frame_padded = self._add_padding(frame_bgr)
                        
                        # Escribir al video
                        self.video_writer.write(frame_padded)
                        self.frames_written += 1
                        
                        # Debug cada 50 frames
                        if self.frames_written % 50 == 0:
                            print(f"Frames escritos: {self.frames_written}")
                
                except Empty:
                    continue
                except Exception as e:
                    print(f"Error en worker: {e}")
                    break
        
        except Exception as e:
            print(f"Error crítico en worker: {e}")
        
        print(f"Worker terminado. Total frames: {self.frames_written}")
    
    def save_to_siev(self, video_path: str) -> bool:
        """Guardar video en el archivo .siev del usuario actual"""
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
            test_data = {
                'id': self.current_test_id,
                'tipo': getattr(self.main_window, 'current_protocol', 'desconocido'),
                'fecha': time.time(),
                'evaluador': getattr(self.main_window, 'current_evaluator', 'Sin evaluador'),
                'estado': 'completado'
            }
            
            # Agregar video al .siev
            success = siev_manager.add_test_to_siev(
                siev_path, 
                test_data, 
                csv_data=None,  # Solo video por ahora
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
        """Dummy para compatibilidad"""
        return (640, 480)
    
    def get_status(self) -> dict:
        """Estado actual"""
        return {
            'is_recording': self.is_recording,
            'test_id': self.current_test_id,
            'frames_written': self.frames_written
        }