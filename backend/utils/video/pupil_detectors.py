"""
Módulo de detectores de pupila simplificado.
Solo mantiene el detector Legacy para migración progresiva a Rust.
"""

import cv2
import numpy as np
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

# Intentar importar la extensión de Rust para aceleración
try:
    import siev_vision_py
    RUST_ENABLED = True
    print("[SIEV] Aceleración Full-Stack Rust activada.")
except ImportError:
    RUST_ENABLED = False
    print("[SIEV] Aceleración de Rust no disponible. Usando fallback de OpenCV.")

@dataclass
class PupilResult:
    """Resultado de detección de pupila."""
    center_x: int
    center_y: int
    radius: int
    confidence: float  # 0.0 - 1.0
    mask: Optional[np.ndarray] = None  # Para visualización debug
    found: bool = True

@dataclass
class DetectorConfig:
    """Configuración para los detectores de pupila."""
    threshold_value: int = 0
    erode_value: int = 0
    debug_mode: bool = False
    legacy_blur_enabled: bool = True
    legacy_blur_kernel: int = 5
    legacy_morph_enabled: bool = True
    legacy_morph_close_iterations: int = 1
    legacy_morph_dilate_iterations: int = 1

class BasePupilDetector(ABC):
    """Clase base abstracta para detectores de pupila."""

    @abstractmethod
    def detect(self, eye_gray: np.ndarray, config: DetectorConfig) -> Optional[PupilResult]:
        pass

    @abstractmethod
    def reset(self):
        pass

class LegacyPupilDetector(BasePupilDetector):
    """
    Detector optimizado que delega el procesamiento y la detección a Rust.
    """

    def __init__(self):
        pass

    def reset(self):
        pass

    def detect(self, eye_bgr: np.ndarray, config: DetectorConfig) -> Optional[PupilResult]:
        try:
            eh, ew = eye_bgr.shape[:2]

            if RUST_ENABLED:
                # ACELERACIÓN FULL RUST BGR
                sigma = (config.legacy_blur_kernel - 1) / 6.0 if config.legacy_blur_enabled else 0.0
                
                # Rust devuelve la máscara SOLO SI se solicita (ahorro masivo de CPU)
                thresh, data_json = siev_vision_py.process_and_detect_bgr(
                    eye_bgr,
                    sigma,
                    config.threshold_value if config.threshold_value > 0 else 40,
                    config.erode_value,
                    config.legacy_morph_dilate_iterations if config.legacy_morph_enabled else 0,
                    20.0,
                    float(ew * eh),
                    config.debug_mode # return_mask
                )
                
                res_data = json.loads(data_json)
                mask = None
                if thresh is not None:
                    mask = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)

                if res_data['found']:
                    return PupilResult(
                        center_x=int(res_data['center_x']),
                        center_y=int(res_data['center_y']),
                        radius=int(res_data['radius']),
                        confidence=res_data['confidence'],
                        mask=mask,
                        found=True
                    )
                else:
                    return PupilResult(0, 0, 0, 0.0, mask, found=False)

            else:
                # FALLBACK OPENCV (Solo si Rust falla)
                eye_gray = cv2.cvtColor(eye_bgr, cv2.COLOR_BGR2GRAY)
                processed = eye_gray.copy()
                if config.legacy_blur_enabled:
                    k = max(3, config.legacy_blur_kernel | 1)
                    processed = cv2.GaussianBlur(processed, (k, k), 0)
                
                _, thresh = cv2.threshold(processed, config.threshold_value or 40, 255, cv2.THRESH_BINARY_INV)
                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if not contours: return PupilResult(0, 0, 0, 0.0, None, found=False)
                largest = max(contours, key=cv2.contourArea)
                M = cv2.moments(largest)
                if M["m00"] == 0: return PupilResult(0, 0, 0, 0.0, None, found=False)
                return PupilResult(int(M["m10"]/M["m00"]), int(M["m01"]/M["m00"]), 10, 0.8)

        except Exception as e:
            print(f"Error en Detector: {e}")
            return PupilResult(0, 0, 0, 0.0, None, found=False)

def create_pupil_detector(mode: str) -> BasePupilDetector:
    """Crea el detector de pupila Legacy (único disponible por ahora)."""
    return LegacyPupilDetector()