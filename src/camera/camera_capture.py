#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Camera Capture Module - Manejo exclusivo de captura y configuración de cámara
"""

import cv2
import numpy as np
from typing import Optional, Tuple, Dict, Any
from PySide6.QtCore import QObject, Signal


class CameraCapture(QObject):
    """
    Módulo de captura de cámara con configuración optimizada.
    Solo se encarga de abrir, configurar, capturar y liberar la cámara.
    """
    
    # Señales
    camera_connected = Signal(bool)  # True=conectada, False=desconectada
    frame_captured = Signal(np.ndarray)  # Frame capturado exitosamente
    capture_failed = Signal(str)  # Error en captura con mensaje
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Estado de cámara
        self.camera = None
        self.is_connected = False
        self.camera_index = None
        
        # Configuración por defecto
        self.default_config = {
            'width': 800,
            'height': 600,
            'fps': 120,
            'buffer_size': 1,
            'fourcc': 'MJPG'
        }
        
        # Control de errores
        self.consecutive_failures = 0
        self.max_failures = 5
    
    def init_camera(self, camera_index: int, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Inicializar cámara con índice específico.
        
        Args:
            camera_index: Índice de cámara OpenCV
            config: Configuración opcional (width, height, fps, etc.)
            
        Returns:
            bool: True si la inicialización fue exitosa
        """
        try:
            print(f"🔌 Inicializando cámara en índice {camera_index}")
            
            # Liberar cámara anterior si existe
            self._release_camera()
            
            # Usar configuración proporcionada o por defecto
            cam_config = {**self.default_config, **(config or {})}
            
            # Crear nueva captura
            self.camera = cv2.VideoCapture(camera_index)
            
            if not self.camera.isOpened():
                print(f"❌ No se pudo abrir cámara en índice {camera_index}")
                return False
            
            # Aplicar configuración
            self._apply_camera_config(cam_config)
            
            # Test de captura inicial
            if not self._test_initial_capture():
                print(f"❌ Cámara {camera_index} no puede capturar frames")
                self._release_camera()
                return False
            
            # Éxito
            self.camera_index = camera_index
            self.is_connected = True
            self.consecutive_failures = 0
            
            print(f"✅ Cámara {camera_index} inicializada correctamente")
            self.camera_connected.emit(True)
            return True
            
        except Exception as e:
            print(f"❌ Error inicializando cámara {camera_index}: {e}")
            self._release_camera()
            return False
    
    def _apply_camera_config(self, config: Dict[str, Any]) -> None:
        """Aplicar configuración a la cámara."""
        if not self.camera:
            return
        
        try:
            # Resolución
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, config['width'])
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, config['height'])
            
            # FPS
            self.camera.set(cv2.CAP_PROP_FPS, config['fps'])
            
            # Buffer size (importante para latencia)
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, config['buffer_size'])
            
            # Codec si está especificado
            if config.get('fourcc'):
                fourcc_code = cv2.VideoWriter_fourcc(*config['fourcc'])
                self.camera.set(cv2.CAP_PROP_FOURCC, fourcc_code)
            
            print(f"📐 Configuración aplicada: {config['width']}x{config['height']} @ {config['fps']}fps")
            
        except Exception as e:
            print(f"⚠️ Error aplicando configuración: {e}")
    
    def _test_initial_capture(self) -> bool:
        """Probar captura inicial para verificar funcionamiento."""
        if not self.camera:
            return False
        
        try:
            ret, frame = self.camera.read()
            return ret and frame is not None and frame.size > 0
        except Exception:
            return False
    
    def capture_frame(self) -> Optional[np.ndarray]:
        """
        Capturar un frame de la cámara.
        
        Returns:
            np.ndarray: Frame capturado o None si hay error
        """
        if not self.is_connected or not self.camera:
            return None
        
        try:
            ret, frame = self.camera.read()
            
            if not ret or frame is None:
                self._handle_capture_failure("No se pudo capturar frame")
                return None
            
            # Frame capturado exitosamente
            self.consecutive_failures = 0
            self.frame_captured.emit(frame)
            return frame
            
        except Exception as e:
            self._handle_capture_failure(f"Error en captura: {e}")
            return None
    
    def _handle_capture_failure(self, error_msg: str) -> None:
        """Manejar fallos de captura y detectar desconexión."""
        self.consecutive_failures += 1
        
        if self.consecutive_failures >= self.max_failures:
            print(f"❌ Cámara desconectada: {error_msg} (fallos: {self.consecutive_failures})")
            
            # Marcar como desconectada
            self.is_connected = False
            self.camera_connected.emit(False)
            self.capture_failed.emit(error_msg)
        else:
            print(f"⚠️ Fallo de captura {self.consecutive_failures}/{self.max_failures}: {error_msg}")
    
    def _release_camera(self) -> None:
        """Liberar recursos de cámara interna."""
        if self.camera:
            try:
                self.camera.release()
            except Exception as e:
                print(f"⚠️ Error liberando cámara: {e}")
            finally:
                self.camera = None
    
    def release_camera(self) -> None:
        """
        Liberar cámara completamente y limpiar estado.
        """
        print("🔌 Liberando cámara...")
        
        self._release_camera()
        
        # Limpiar estado
        self.is_connected = False
        self.camera_index = None
        self.consecutive_failures = 0
        
        self.camera_connected.emit(False)
        print("✅ Cámara liberada")
    
    def is_camera_available(self) -> bool:
        """Verificar si la cámara está disponible."""
        return self.is_connected and self.camera is not None
    
    def get_camera_info(self) -> Dict[str, Any]:
        """
        Obtener información actual de la cámara.
        
        Returns:
            Dict con información de la cámara
        """
        if not self.camera:
            return {'connected': False}
        
        try:
            return {
                'connected': self.is_connected,
                'index': self.camera_index,
                'width': int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)),
                'height': int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                'fps': self.camera.get(cv2.CAP_PROP_FPS),
                'buffer_size': int(self.camera.get(cv2.CAP_PROP_BUFFERSIZE)),
                'consecutive_failures': self.consecutive_failures
            }
        except Exception as e:
            print(f"Error obteniendo info de cámara: {e}")
            return {'connected': False, 'error': str(e)}
    
    def update_camera_config(self, new_config: Dict[str, Any]) -> bool:
        """
        Actualizar configuración de cámara en tiempo real.
        
        Args:
            new_config: Nueva configuración a aplicar
            
        Returns:
            bool: True si se aplicó correctamente
        """
        if not self.is_connected or not self.camera:
            return False
        
        try:
            self._apply_camera_config(new_config)
            return True
        except Exception as e:
            print(f"Error actualizando configuración: {e}")
            return False
    
    def get_frame_dimensions(self) -> Tuple[int, int]:
        """
        Obtener dimensiones del frame actual.
        
        Returns:
            Tuple (width, height) o (0, 0) si no hay cámara
        """
        if not self.camera:
            return (0, 0)
        
        try:
            width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            return (width, height)
        except Exception:
            return (0, 0)