# src/managers/video_manager.py

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QSlider
from typing import List, Callable, Optional

from libs.video.video_widget import VideoWidget
from libs.hardware.camera_resolution_detector import CameraResolutionDetector
from libs.common.utils import select_max_resolution


class VideoManager(QObject):
    """
    Gestiona todo el sistema de video: captura, grabación, reproducción y configuración.
    Encapsula la lógica de video para desacoplarla de MainWindow.
    """
    
    # Señales para comunicarse con MainWindow
    eye_positions_updated = Signal(list)  # Nuevas posiciones de ojos
    video_frame_ready = Signal(object)    # Frame listo para grabación
    video_mode_changed = Signal(str)      # Cambio entre 'live' y 'player'
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Referencias a UI (se asignan desde MainWindow)
        self.camera_frame = None
        self.resolution_combo = None
        self.slider_list = None
        
        # Sistema de video
        self.video_widget = None
        self.camera_index = 2
        
        # Sistema de grabación
        self.video_recorder = None
        self.is_recording = False
        
        # Configuración
        self.current_resolution = None
        
        print("VideoManager inicializado")
    
    def set_ui_references(self, camera_frame, resolution_combo, slider_list):
        """
        Establece referencias a los elementos de UI necesarios.
        
        Args:
            camera_frame: Widget donde se muestra el video
            resolution_combo: ComboBox de resoluciones
            slider_list: Lista de sliders de configuración
        """
        self.camera_frame = camera_frame
        self.resolution_combo = resolution_combo
        self.slider_list = slider_list
        
        print("Referencias UI establecidas en VideoManager")
    
    def initialize_video_system(self):
        """Inicializa el sistema completo de video"""
        try:
            self._detect_and_setup_camera()
            self._create_video_widget()
            self._connect_slider_events()
            self._init_video_recorder()
            
            print("Sistema de video inicializado exitosamente")
            return True
            
        except Exception as e:
            print(f"Error inicializando sistema de video: {e}")
            return False
    
    def _detect_and_setup_camera(self):
        """Detecta resoluciones de cámara y configura combo"""
        if not self.resolution_combo:
            raise Exception("ComboBox de resoluciones no configurado")
        
        detector = CameraResolutionDetector()
        resolution_list = detector.listar_resoluciones(self.camera_index)
        
        if not resolution_list:
            raise Exception(f"No se encontraron resoluciones para cámara {self.camera_index}")
        
        # Seleccionar mejor resolución
        max_resolution = select_max_resolution(resolution_list, True)
        
        # Llenar combo
        self._fill_resolution_combo(resolution_list, max_resolution)
        
        print(f"Cámara {self.camera_index} configurada con {len(resolution_list)} resoluciones")
    
    def _fill_resolution_combo(self, resolution_list: List[str], selected_resolution: str):
        """Llena el combo de resoluciones"""
        self.resolution_combo.clear()
        
        for resolution in resolution_list:
            self.resolution_combo.addItem(resolution)
        
        # Seleccionar la resolución óptima
        if selected_resolution in resolution_list:
            index = resolution_list.index(selected_resolution)
            self.resolution_combo.setCurrentIndex(index)
            self.current_resolution = selected_resolution
    
    def _create_video_widget(self):
        """Crea y configura el widget de video"""
        if not all([self.camera_frame, self.slider_list, self.resolution_combo]):
            raise Exception("Referencias UI no configuradas")
        
        self.video_widget = VideoWidget(
            self.camera_frame,
            self.slider_list,
            self.resolution_combo,
            camera_id=self.camera_index,
            video_callback=self._handle_video_frame
        )
        
        # Conectar señales del video widget
        self.video_widget.sig_pos.connect(self._handle_eye_positions)
        
        print("VideoWidget creado y configurado")
    
    def _connect_slider_events(self):
        """Conecta eventos de los sliders de configuración"""
        if not self.slider_list:
            return
        
        for slider in self.slider_list:
            if isinstance(slider, QSlider):
                slider.valueChanged.connect(self._on_slider_changed)
        
        print(f"Conectados {len(self.slider_list)} sliders")
    
    def _init_video_recorder(self):
        """Inicializa el grabador de video"""
        try:
            from libs.video.video_recorder import VideoRecorder
            self.video_recorder = VideoRecorder(self)
            print("VideoRecorder inicializado")
        except Exception as e:
            print(f"Error inicializando VideoRecorder: {e}")
            self.video_recorder = None
    
    # === MÉTODOS DE CONTROL ===
    
    def start_recording(self):
        """Inicia la grabación de video"""
        if self.video_recorder and not self.is_recording:
            success = self.video_recorder.start_recording()
            if success:
                self.is_recording = True
                print("Grabación de video iniciada")
            return success
        return False
    
    def stop_recording(self):
        """Detiene la grabación de video"""
        if self.video_recorder and self.is_recording:
            self.video_recorder.stop_recording()
            self.is_recording = False
            print("Grabación de video detenida")
    
    def switch_to_live_mode(self):
        """Cambia a modo video en vivo"""
        if self.video_widget:
            self.video_widget.switch_to_live()
            self.video_mode_changed.emit('live')
            print("Cambiado a modo video en vivo")
    
    def switch_to_player_mode(self, video_data: bytes):
        """
        Cambia a modo reproductor con datos de video específicos
        
        Args:
            video_data: Datos binarios del video a reproducir
        """
        if self.video_widget:
            success = self.video_widget.switch_to_player(video_data)
            if success:
                self.video_mode_changed.emit('player')
                print("Cambiado a modo reproductor")
            return success
        return False
    
    def get_video_mode(self) -> str:
        """Retorna el modo actual del video ('live' o 'player')"""
        if self.video_widget and hasattr(self.video_widget, 'is_in_player_mode'):
            return 'player' if self.video_widget.is_in_player_mode else 'live'
        return 'live'
    
    def set_camera_index(self, camera_index: int):
        """Cambia el índice de cámara"""
        self.camera_index = camera_index
    
    # === CALLBACKS Y HANDLERS ===
    
    def _handle_eye_positions(self, positions: list):
        """Maneja nuevas posiciones de ojos del video widget"""
        self.eye_positions_updated.emit(positions)
    
    def _handle_video_frame(self, frame):
        """Maneja frames de video para grabación"""
        if self.is_recording and self.video_recorder:
            self.video_recorder.add_frame(frame)
        
        # Emitir señal para otros componentes que necesiten el frame
        self.video_frame_ready.emit(frame)
    
    def _on_slider_changed(self, value):
        """Maneja cambios en sliders de configuración"""
        sender = self.sender()
        if sender:
            pass
            # Aquí se pueden agregar acciones específicas por slider
    
    # === MÉTODOS DE CONFIGURACIÓN ===
    
    def save_slider_configuration(self):
        """Guarda la configuración actual de sliders"""
        # Implementar guardado de configuración
        pass
    
    def load_slider_configuration(self):
        """Carga configuración guardada de sliders"""
        # Implementar carga de configuración
        pass
    
    # === CLEANUP ===
    
    def cleanup(self):
        """Limpia recursos del sistema de video"""
        if self.is_recording:
            self.stop_recording()
        
        if self.video_widget:
            # Implementar cleanup del video widget si es necesario
            pass
        
        print("VideoManager limpiado")