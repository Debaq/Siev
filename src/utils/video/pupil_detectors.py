"""
Módulo de detectores de pupila con 3 modos:
- Legacy: Threshold + CLAHE + Contornos (método original)
- Fast: Ventana local + Punto más oscuro + Star-burst
- Hybrid: Fast con fallback automático a Legacy
"""

import cv2
import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class PupilResult:
    """Resultado de detección de pupila."""
    center_x: int
    center_y: int
    radius: int
    confidence: float  # 0.0 - 1.0
    mask: Optional[np.ndarray] = None  # Para visualización debug


@dataclass
class DetectorConfig:
    """Configuración para los detectores de pupila."""
    # Parámetros compartidos
    threshold_value: int = 0
    erode_value: int = 0

    # Parámetros Fast detector
    search_window_multiplier: float = 3.0
    dark_threshold_percent: int = 20
    starburst_rays: int = 16
    starburst_min_gradient: int = 30

    # Parámetros Hybrid
    fallback_threshold: int = 5

    # Parámetros Legacy - Toggles de etapas
    legacy_blur_enabled: bool = True
    legacy_blur_kernel: int = 5  # Debe ser impar: 3, 5, 7, 9
    legacy_clahe_enabled: bool = True
    legacy_clahe_clip_limit: float = 2.0
    legacy_clahe_grid_size: int = 8
    legacy_morph_enabled: bool = True
    legacy_morph_close_iterations: int = 1
    legacy_morph_dilate_iterations: int = 1


class BasePupilDetector(ABC):
    """Clase base abstracta para detectores de pupila."""

    @abstractmethod
    def detect(self, eye_gray: np.ndarray, config: DetectorConfig) -> Optional[PupilResult]:
        """
        Detecta la pupila en una región del ojo.

        Args:
            eye_gray: Imagen en escala de grises de la región del ojo
            config: Configuración del detector

        Returns:
            PupilResult con la posición de la pupila o None si no se detectó
        """
        pass

    @abstractmethod
    def reset(self):
        """Resetea el estado interno del detector."""
        pass


class LegacyPupilDetector(BasePupilDetector):
    """
    Detector legacy basado en threshold + CLAHE + contornos.
    Procesa toda la ROI en cada frame.
    Cada etapa puede ser activada/desactivada y configurada.
    """

    def __init__(self):
        self._clahe = None
        self._clahe_params = (2.0, 8)  # (clip_limit, grid_size)

    def _get_clahe(self, clip_limit: float, grid_size: int):
        """Obtiene CLAHE con caché para evitar recrearlo cada frame."""
        if self._clahe is None or self._clahe_params != (clip_limit, grid_size):
            self._clahe = cv2.createCLAHE(
                clipLimit=clip_limit,
                tileGridSize=(grid_size, grid_size)
            )
            self._clahe_params = (clip_limit, grid_size)
        return self._clahe

    def reset(self):
        pass  # Sin estado persistente

    def detect(self, eye_gray: np.ndarray, config: DetectorConfig) -> Optional[PupilResult]:
        try:
            eh, ew = eye_gray.shape[:2]

            # 1. Preprocesamiento - Blur (opcional)
            if config.legacy_blur_enabled:
                kernel_size = config.legacy_blur_kernel
                # Asegurar que sea impar
                if kernel_size % 2 == 0:
                    kernel_size += 1
                kernel_size = max(3, min(kernel_size, 15))  # Limitar entre 3 y 15
                processed = cv2.GaussianBlur(eye_gray, (kernel_size, kernel_size), 0)
            else:
                processed = eye_gray.copy()

            # 2. CLAHE - Mejora de contraste (opcional)
            if config.legacy_clahe_enabled:
                clahe = self._get_clahe(
                    config.legacy_clahe_clip_limit,
                    config.legacy_clahe_grid_size
                )
                processed = clahe.apply(processed)

            # 3. Umbralización
            threshold_value = config.threshold_value
            if threshold_value == 0:
                otsu_thresh, _ = cv2.threshold(processed, 0, 255,
                                                cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                adjusted_thresh = max(0, min(255, otsu_thresh))
                _, thresh = cv2.threshold(processed, adjusted_thresh, 255, cv2.THRESH_BINARY_INV)
            else:
                _, thresh = cv2.threshold(processed, threshold_value, 255, cv2.THRESH_BINARY_INV)

            # 4. Operaciones morfológicas (opcional)
            kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))

            # Erosión (siempre controlada por erode_value)
            if config.erode_value > 0:
                thresh = cv2.erode(thresh, kernel_small, iterations=config.erode_value)

            # Close y Dilate (opcionales)
            if config.legacy_morph_enabled:
                if config.legacy_morph_close_iterations > 0:
                    thresh = cv2.morphologyEx(
                        thresh, cv2.MORPH_CLOSE, kernel_small,
                        iterations=config.legacy_morph_close_iterations
                    )
                if config.legacy_morph_dilate_iterations > 0:
                    thresh = cv2.dilate(
                        thresh, kernel_small,
                        iterations=config.legacy_morph_dilate_iterations
                    )

            # 4. Encontrar contornos
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # Crear máscara para visualización
            mask = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)

            if not contours:
                return None

            # 5. Filtrar contornos válidos
            valid_contours = []
            for c in contours:
                area = cv2.contourArea(c)
                if area > 20 and area < (ew * eh * 0.5):
                    valid_contours.append(c)

            if not valid_contours:
                return None

            # 6. Tomar el contorno más grande
            largest_contour = max(valid_contours, key=cv2.contourArea)

            # 7. Calcular centro
            M = cv2.moments(largest_contour)
            if M["m00"] != 0:
                center_x = int(M["m10"] / M["m00"])
                center_y = int(M["m01"] / M["m00"])
            else:
                x, y, w, h = cv2.boundingRect(largest_contour)
                center_x = x + w // 2
                center_y = y + h // 2

            # 8. Calcular radio usando mediana de distancias
            points = largest_contour.reshape(-1, 2)
            dx = points[:, 0] - center_x
            dy = points[:, 1] - center_y
            distances = np.sqrt(dx * dx + dy * dy)
            radius = int(np.median(distances)) if len(distances) > 0 else 10

            # Limitar radio
            min_radius = 5
            max_radius = min(ew, eh) // 3
            radius = max(min_radius, min(radius, max_radius))

            # Calcular confianza basada en circularidad del contorno
            area = cv2.contourArea(largest_contour)
            perimeter = cv2.arcLength(largest_contour, True)
            circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
            confidence = min(1.0, circularity)

            # Dibujar en máscara para debug
            cv2.drawContours(mask, [largest_contour], 0, (0, 0, 255), 1)
            cv2.circle(mask, (center_x, center_y), radius, (0, 255, 0), 1)
            cv2.circle(mask, (center_x, center_y), 2, (255, 0, 0), -1)

            return PupilResult(
                center_x=center_x,
                center_y=center_y,
                radius=radius,
                confidence=confidence,
                mask=mask
            )

        except Exception as e:
            print(f"Error en LegacyPupilDetector: {e}")
            return None


class FastPupilDetector(BasePupilDetector):
    """
    Detector rápido con 3 capas:
    1. Búsqueda en ventana local (si hay posición previa)
    2. Umbralización automática por punto más oscuro
    3. Star-burst para precisión de bordes
    """

    def __init__(self):
        self.last_position: Optional[Tuple[int, int]] = None
        self.last_radius: int = 20
        self.frames_without_detection: int = 0

    def reset(self):
        """Resetea el estado para forzar búsqueda completa."""
        self.last_position = None
        self.last_radius = 20
        self.frames_without_detection = 0

    def detect(self, eye_gray: np.ndarray, config: DetectorConfig) -> Optional[PupilResult]:
        try:
            eh, ew = eye_gray.shape[:2]

            # Determinar región de búsqueda
            if self.last_position is not None:
                # Búsqueda en ventana local
                search_region, offset_x, offset_y = self._get_search_window(
                    eye_gray, config.search_window_multiplier
                )
            else:
                # Búsqueda en toda la imagen
                search_region = eye_gray
                offset_x, offset_y = 0, 0

            # Capa 1: Encontrar punto más oscuro (centro aproximado)
            dark_center = self._find_darkest_region(search_region)
            if dark_center is None:
                self.frames_without_detection += 1
                return None

            dark_x, dark_y = dark_center

            # Capa 2: Umbral adaptativo basado en punto más oscuro
            local_threshold = self._calculate_adaptive_threshold(
                search_region, dark_x, dark_y, config.dark_threshold_percent
            )

            # Capa 3: Star-burst para encontrar bordes precisos
            border_points = self._starburst(
                search_region, dark_x, dark_y,
                config.starburst_rays,
                local_threshold,
                config.starburst_min_gradient
            )

            if len(border_points) < 4:
                # No suficientes puntos, usar fallback con threshold
                result = self._fallback_threshold_detection(
                    search_region, local_threshold
                )
                if result is None:
                    self.frames_without_detection += 1
                    return None
                center_x, center_y, radius = result
            else:
                # Calcular centro y radio desde puntos del starburst
                center_x, center_y, radius = self._fit_circle_from_points(border_points)

            # Ajustar coordenadas al sistema global
            final_x = center_x + offset_x
            final_y = center_y + offset_y

            # Validar que esté dentro de la imagen
            if not (0 <= final_x < ew and 0 <= final_y < eh):
                self.frames_without_detection += 1
                return None

            # Limitar radio
            min_radius = 5
            max_radius = min(ew, eh) // 3
            radius = max(min_radius, min(radius, max_radius))

            # Calcular confianza basada en número de puntos válidos del starburst
            confidence = min(1.0, len(border_points) / config.starburst_rays)

            # Actualizar estado
            self.last_position = (final_x, final_y)
            self.last_radius = radius
            self.frames_without_detection = 0

            # Crear máscara para debug
            mask = cv2.cvtColor(eye_gray.copy(), cv2.COLOR_GRAY2BGR)

            # Dibujar ventana de búsqueda
            if offset_x > 0 or offset_y > 0:
                window_size = int(self.last_radius * config.search_window_multiplier)
                cv2.rectangle(mask,
                             (offset_x, offset_y),
                             (offset_x + search_region.shape[1], offset_y + search_region.shape[0]),
                             (255, 255, 0), 1)

            # Dibujar puntos del starburst
            for px, py in border_points:
                abs_px = int(px + offset_x)
                abs_py = int(py + offset_y)
                cv2.circle(mask, (abs_px, abs_py), 1, (0, 255, 255), -1)

            # Dibujar círculo final
            cv2.circle(mask, (final_x, final_y), radius, (0, 255, 0), 1)
            cv2.circle(mask, (final_x, final_y), 2, (255, 0, 0), -1)

            return PupilResult(
                center_x=final_x,
                center_y=final_y,
                radius=radius,
                confidence=confidence,
                mask=mask
            )

        except Exception as e:
            print(f"Error en FastPupilDetector: {e}")
            self.frames_without_detection += 1
            return None

    def _get_search_window(self, image: np.ndarray, multiplier: float) -> Tuple[np.ndarray, int, int]:
        """Extrae ventana de búsqueda alrededor de la última posición conocida."""
        h, w = image.shape[:2]

        window_size = int(self.last_radius * multiplier)
        half_window = window_size // 2

        cx, cy = self.last_position

        # Calcular límites con clipping
        x1 = max(0, cx - half_window)
        y1 = max(0, cy - half_window)
        x2 = min(w, cx + half_window)
        y2 = min(h, cy + half_window)

        return image[y1:y2, x1:x2], x1, y1

    def _find_darkest_region(self, image: np.ndarray) -> Optional[Tuple[int, int]]:
        """Encuentra el centro de la región más oscura (candidato a pupila)."""
        if image.size == 0:
            return None

        # Suavizar para reducir ruido
        blurred = cv2.GaussianBlur(image, (5, 5), 0)

        # Encontrar el mínimo (punto más oscuro)
        min_val, _, min_loc, _ = cv2.minMaxLoc(blurred)

        # Buscar región alrededor del mínimo usando percentil bajo
        # para ser más robusto a outliers
        threshold_dark = np.percentile(blurred, 5)
        dark_mask = blurred <= threshold_dark

        # Encontrar centroide de la región oscura
        coords = np.where(dark_mask)
        if len(coords[0]) == 0:
            return min_loc  # Fallback al punto mínimo

        center_y = int(np.mean(coords[0]))
        center_x = int(np.mean(coords[1]))

        return (center_x, center_y)

    def _calculate_adaptive_threshold(self, image: np.ndarray,
                                       center_x: int, center_y: int,
                                       percent_offset: int) -> int:
        """Calcula umbral adaptativo basado en el valor del punto más oscuro."""
        h, w = image.shape[:2]

        # Tomar valor en una pequeña región alrededor del centro
        radius = 3
        x1 = max(0, center_x - radius)
        y1 = max(0, center_y - radius)
        x2 = min(w, center_x + radius)
        y2 = min(h, center_y + radius)

        region = image[y1:y2, x1:x2]
        if region.size == 0:
            return 50  # Valor por defecto

        darkest_value = np.min(region)

        # Umbral = valor más oscuro + porcentaje de offset
        threshold = int(darkest_value + (255 - darkest_value) * percent_offset / 100)

        return max(10, min(threshold, 200))

    def _starburst(self, image: np.ndarray, center_x: int, center_y: int,
                   num_rays: int, threshold: int, min_gradient: int) -> list:
        """
        Algoritmo Star-burst: lanza rayos desde el centro para encontrar bordes.
        """
        h, w = image.shape[:2]
        border_points = []

        # Ángulos equidistantes
        angles = np.linspace(0, 2 * np.pi, num_rays, endpoint=False)

        # Longitud máxima del rayo
        max_length = min(w, h) // 2

        for angle in angles:
            dx = np.cos(angle)
            dy = np.sin(angle)

            prev_value = image[center_y, center_x] if 0 <= center_y < h and 0 <= center_x < w else 0

            # Recorrer el rayo desde el centro hacia afuera
            for step in range(1, max_length):
                x = int(center_x + dx * step)
                y = int(center_y + dy * step)

                # Verificar límites
                if not (0 <= x < w and 0 <= y < h):
                    break

                current_value = image[y, x]
                gradient = current_value - prev_value

                # Detectar borde: cambio significativo de oscuro a claro
                if gradient > min_gradient and current_value > threshold:
                    # Retroceder un paso para quedarnos en el borde de la pupila
                    border_x = int(center_x + dx * (step - 1))
                    border_y = int(center_y + dy * (step - 1))
                    border_points.append((border_x, border_y))
                    break

                prev_value = current_value

        return border_points

    def _fit_circle_from_points(self, points: list) -> Tuple[int, int, int]:
        """Ajusta un círculo a los puntos del borde usando mínimos cuadrados."""
        if len(points) < 3:
            return (0, 0, 10)

        points_array = np.array(points, dtype=np.float32)

        # Método simple: centro = promedio, radio = distancia promedio al centro
        center_x = np.mean(points_array[:, 0])
        center_y = np.mean(points_array[:, 1])

        distances = np.sqrt((points_array[:, 0] - center_x) ** 2 +
                           (points_array[:, 1] - center_y) ** 2)
        radius = np.median(distances)  # Mediana es más robusta a outliers

        return (int(center_x), int(center_y), int(radius))

    def _fallback_threshold_detection(self, image: np.ndarray,
                                       threshold: int) -> Optional[Tuple[int, int, int]]:
        """Fallback: detección por threshold cuando starburst falla."""
        _, thresh = cv2.threshold(image, threshold, 255, cv2.THRESH_BINARY_INV)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return None

        largest = max(contours, key=cv2.contourArea)

        M = cv2.moments(largest)
        if M["m00"] == 0:
            return None

        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])

        points = largest.reshape(-1, 2)
        distances = np.sqrt((points[:, 0] - cx) ** 2 + (points[:, 1] - cy) ** 2)
        radius = int(np.median(distances)) if len(distances) > 0 else 10

        return (cx, cy, radius)


class HybridPupilDetector(BasePupilDetector):
    """
    Detector híbrido que usa Fast como principal y Legacy como fallback.
    Combina velocidad del Fast con robustez del Legacy.
    """

    def __init__(self):
        self.fast_detector = FastPupilDetector()
        self.legacy_detector = LegacyPupilDetector()
        self.use_legacy_next_frame = False
        self.consecutive_fallbacks = 0

    def reset(self):
        """Resetea ambos detectores."""
        self.fast_detector.reset()
        self.legacy_detector.reset()
        self.use_legacy_next_frame = False
        self.consecutive_fallbacks = 0

    def detect(self, eye_gray: np.ndarray, config: DetectorConfig) -> Optional[PupilResult]:
        # Caso 1: Forzar legacy para re-adquisición
        if self.use_legacy_next_frame or self.fast_detector.last_position is None:
            result = self.legacy_detector.detect(eye_gray, config)

            if result is not None:
                # Transferir posición al fast detector
                self.fast_detector.last_position = (result.center_x, result.center_y)
                self.fast_detector.last_radius = result.radius
                self.fast_detector.frames_without_detection = 0
                self.use_legacy_next_frame = False
                self.consecutive_fallbacks = 0

                # Marcar como resultado de legacy en mask
                if result.mask is not None:
                    cv2.putText(result.mask, "L", (5, 15),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
            else:
                self.consecutive_fallbacks += 1

            return result

        # Caso 2: Intentar con fast detector
        result = self.fast_detector.detect(eye_gray, config)

        if result is not None:
            self.consecutive_fallbacks = 0
            # Marcar como resultado de fast en mask
            if result.mask is not None:
                cv2.putText(result.mask, "F", (5, 15),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
            return result

        # Caso 3: Fast falló, verificar si necesitamos fallback
        if self.fast_detector.frames_without_detection >= config.fallback_threshold:
            self.use_legacy_next_frame = True
            self.fast_detector.reset()

        return None


# Factory para crear el detector según configuración
def create_pupil_detector(mode: str) -> BasePupilDetector:
    """
    Crea el detector de pupila según el modo especificado.

    Args:
        mode: "legacy", "fast", o "hybrid"

    Returns:
        Instancia del detector correspondiente
    """
    detectors = {
        "legacy": LegacyPupilDetector,
        "fast": FastPupilDetector,
        "hybrid": HybridPupilDetector
    }

    detector_class = detectors.get(mode, HybridPupilDetector)
    return detector_class()
