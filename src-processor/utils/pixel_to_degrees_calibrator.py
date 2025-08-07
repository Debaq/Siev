#!/usr/bin/env python3
"""
Pixel to Degrees Calibrator
Calibra pixeles de posición de pupila a grados de movimiento ocular.
Usa los primeros frames para establecer la posición central.
"""

from typing import Optional


class PixelToDegreesCalibrator:
    """
    Calibrador que convierte posición de pupila en pixeles a grados de movimiento ocular.
    
    Rango esperado: -30° (nasal) a +30° (temporal)
    Usa calibración automática basada en los primeros frames.
    """
    
    def __init__(self, calibration_frames: int = 10):
        """
        Inicializar calibrador
        
        Args:
            calibration_frames: Número de frames para calibrar posición central
        """
        self.calibration_frames = calibration_frames
        
        # Valores de referencia por defecto
        self.default_center = 56.0      # Posición central en pixeles
        self.default_temporal = 41.0    # Posición temporal (+30°)
        self.default_nasal = 61.0       # Posición nasal (-30°)
        
        # Calibración dinámica
        self.calibration_samples = []   # Muestras de los primeros frames
        self.is_calibrated = False
        self.frame_count = 0
        
        # Parámetros de calibración actual
        self.center_pixel = self.default_center
        self.temporal_pixel = self.default_temporal
        self.nasal_pixel = self.default_nasal
        
        # Rangos de grados
        self.max_degrees = 30.0         # +30° temporal
        self.min_degrees = -30.0        # -30° nasal
        
    def calibrate_pixel_to_degrees(self, pixel_x: float) -> float:
        """
        Convertir posición en pixeles a grados
        
        Args:
            pixel_x: Posición horizontal de pupila en pixeles
            
        Returns:
            float: Posición en grados (-30 a +30)
        """
        if pixel_x <= 0:
            return 0.0
            
        # Fase de calibración (primeros N frames)
        if not self.is_calibrated and self.frame_count < self.calibration_frames:
            self._collect_calibration_sample(pixel_x)
            
            if self.frame_count >= self.calibration_frames:
                self._finalize_calibration()
        
        self.frame_count += 1
        
        # Convertir pixel a grados usando interpolación lineal
        return self._convert_to_degrees(pixel_x)
    
    def _collect_calibration_sample(self, pixel_x: float):
        """Recopilar muestra para calibración"""
        if pixel_x > 0:  # Solo muestras válidas
            self.calibration_samples.append(pixel_x)
    
    def _finalize_calibration(self):
        """Finalizar calibración usando las muestras recopiladas"""
        if not self.calibration_samples:
            # Sin muestras válidas, usar valores por defecto
            print("PixelCalibrator: Sin muestras válidas, usando valores por defecto")
            self.is_calibrated = True
            return
        
        # Calcular posición central promedio de las muestras
        calibrated_center = sum(self.calibration_samples) / len(self.calibration_samples)
        
        # Calcular diferencia con el centro por defecto
        center_offset = calibrated_center - self.default_center
        
        # Ajustar todos los valores de referencia
        self.center_pixel = calibrated_center
        self.temporal_pixel = self.default_temporal + center_offset
        self.nasal_pixel = self.default_nasal + center_offset
        
        self.is_calibrated = True
        
        print(f"PixelCalibrator: Calibración completada")
        print(f"  Centro: {self.center_pixel:.1f} px (0°)")
        print(f"  Temporal: {self.temporal_pixel:.1f} px (+30°)")
        print(f"  Nasal: {self.nasal_pixel:.1f} px (-30°)")
    
    def _convert_to_degrees(self, pixel_x: float) -> float:
        """
        Convertir pixel a grados usando interpolación lineal
        
        Args:
            pixel_x: Posición en pixeles
            
        Returns:
            float: Posición en grados
        """
        if pixel_x <= 0:
            return 0.0
        
        if pixel_x <= self.center_pixel:
            # Lado temporal (centro a temporal = 0° a +30°)
            if self.center_pixel != self.temporal_pixel:
                # Interpolación lineal
                ratio = (self.center_pixel - pixel_x) / (self.center_pixel - self.temporal_pixel)
                degrees = ratio * self.max_degrees
                return min(self.max_degrees, max(0, degrees))
            else:
                return 0.0
        else:
            # Lado nasal (centro a nasal = 0° a -30°)
            if self.nasal_pixel != self.center_pixel:
                # Interpolación lineal
                ratio = (pixel_x - self.center_pixel) / (self.nasal_pixel - self.center_pixel)
                degrees = ratio * self.min_degrees
                return max(self.min_degrees, min(0, degrees))
            else:
                return 0.0
    
    def reset_calibration(self):
        """Reiniciar calibración para nuevo video"""
        self.calibration_samples.clear()
        self.is_calibrated = False
        self.frame_count = 0
        
        # Restaurar valores por defecto
        self.center_pixel = self.default_center
        self.temporal_pixel = self.default_temporal
        self.nasal_pixel = self.default_nasal
        
        print("PixelCalibrator: Calibración reiniciada")
    
    def get_calibration_info(self) -> dict:
        """Obtener información de calibración actual"""
        return {
            'is_calibrated': self.is_calibrated,
            'frame_count': self.frame_count,
            'samples_collected': len(self.calibration_samples),
            'center_pixel': self.center_pixel,
            'temporal_pixel': self.temporal_pixel,
            'nasal_pixel': self.nasal_pixel,
            'degrees_range': (self.min_degrees, self.max_degrees)
        }
    
    def set_manual_calibration(self, center: float, temporal: float, nasal: float):
        """
        Establecer calibración manual
        
        Args:
            center: Posición central en pixeles (0°)
            temporal: Posición temporal en pixeles (+30°)
            nasal: Posición nasal en pixeles (-30°)
        """
        self.center_pixel = center
        self.temporal_pixel = temporal
        self.nasal_pixel = nasal
        self.is_calibrated = True
        
        print(f"PixelCalibrator: Calibración manual establecida")
        print(f"  Centro: {center} px, Temporal: {temporal} px, Nasal: {nasal} px")