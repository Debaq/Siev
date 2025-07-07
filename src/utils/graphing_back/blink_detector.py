import numpy as np
import pyqtgraph as pg


class BlinkDetector:
    """Clase para detectar y gestionar los parpadeos en los datos oculares."""
    
    def __init__(self):
        # Para seguimiento de parpadeos
        self.left_blink_regions = []  # Lista de tuplas (inicio_x, fin_x) para ojo izquierdo
        self.right_blink_regions = []  # Lista de tuplas (inicio_x, fin_x) para ojo derecho
        self.left_blinking = False     # Indicador de parpadeo en progreso
        self.right_blinking = False    # Indicador de parpadeo en progreso
        self.blink_start_time = {"left": None, "right": None}  # Tiempo de inicio del parpadeo
        
    def process_blink_left_eye(self, left_eye, current_time):
        """
        Procesa el estado de parpadeo para el ojo izquierdo.
        
        Args:
            left_eye: Datos del ojo izquierdo [x, y] o None si no se detecta
            current_time: Tiempo actual
            
        Returns:
            bool: True si cambió el estado de parpadeo, False en caso contrario
        """
        state_changed = False
        
        if left_eye is None:
            # Ojo no detectado (parpadeo)
            if not self.left_blinking:
                # Inicio de parpadeo
                self.left_blinking = True
                self.blink_start_time["left"] = current_time
                state_changed = True
        else:
            # Ojo detectado
            if self.left_blinking:
                # Fin de parpadeo
                self.left_blinking = False
                self.left_blink_regions.append((self.blink_start_time["left"], current_time))
                self.blink_start_time["left"] = None
                state_changed = True
                
        return state_changed
    
    def process_blink_right_eye(self, right_eye, current_time):
        """
        Procesa el estado de parpadeo para el ojo derecho.
        
        Args:
            right_eye: Datos del ojo derecho [x, y] o None si no se detecta
            current_time: Tiempo actual
            
        Returns:
            bool: True si cambió el estado de parpadeo, False en caso contrario
        """
        state_changed = False
        
        if right_eye is None:
            # Ojo no detectado (parpadeo)
            if not self.right_blinking:
                # Inicio de parpadeo
                self.right_blinking = True
                self.blink_start_time["right"] = current_time
                state_changed = True
        else:
            # Ojo detectado
            if self.right_blinking:
                # Fin de parpadeo
                self.right_blinking = False
                self.right_blink_regions.append((self.blink_start_time["right"], current_time))
                self.blink_start_time["right"] = None
                state_changed = True
                
        return state_changed
    
    def get_visible_blink_regions(self, view_start, view_end, max_regions=50):
        """
        Obtiene las regiones de parpadeo visibles en la ventana de tiempo actual.
        
        Args:
            view_start: Tiempo de inicio de la ventana
            view_end: Tiempo de fin de la ventana
            max_regions: Máximo número de regiones a mostrar
            
        Returns:
            tuple: (regiones_ojo_izquierdo, regiones_ojo_derecho)
        """
        # Filtrar regiones de parpadeo por visibilidad
        visible_left_blinks = [
            (start, end) for start, end in self.left_blink_regions
            if end >= view_start and start <= view_end
        ]
        
        visible_right_blinks = [
            (start, end) for start, end in self.right_blink_regions
            if end >= view_start and start <= view_end
        ]
        
        # Limitar número de regiones para rendimiento
        if len(visible_left_blinks) > max_regions:
            visible_left_blinks = visible_left_blinks[-max_regions:]
        
        if len(visible_right_blinks) > max_regions:
            visible_right_blinks = visible_right_blinks[-max_regions:]
            
        return visible_left_blinks, visible_right_blinks
    
    def create_blink_region_items(self, visible_left_blinks, visible_right_blinks, current_time=None):
        """
        Crea elementos LinearRegionItem para representar los parpadeos en los gráficos.
        
        Args:
            visible_left_blinks: Lista de regiones para el ojo izquierdo
            visible_right_blinks: Lista de regiones para el ojo derecho
            current_time: Tiempo actual para parpadeos en curso
            
        Returns:
            list: Lista de objetos LinearRegionItem
        """
        regions = []
        
        # Regiones para ojo izquierdo
        for start, end in visible_left_blinks:
            if end > start:  # Asegurarse de que la región es válida
                region = pg.LinearRegionItem(
                    values=[start, end],
                    brush=pg.mkBrush(0, 0, 255, 50),  # Azul semi-transparente
                    movable=False
                )
                regions.append(region)
        
        # Regiones para ojo derecho
        for start, end in visible_right_blinks:
            if end > start:  # Asegurarse de que la región es válida
                region = pg.LinearRegionItem(
                    values=[start, end],
                    brush=pg.mkBrush(255, 0, 0, 50),  # Rojo semi-transparente
                    movable=False
                )
                regions.append(region)
        
        # Añadir parpadeos en curso si está disponible el tiempo actual
        if current_time is not None:
            # Parpadeo en curso ojo izquierdo
            if self.left_blinking and self.blink_start_time["left"] is not None:
                region = pg.LinearRegionItem(
                    values=[self.blink_start_time["left"], current_time],
                    brush=pg.mkBrush(0, 0, 255, 50),  # Azul semi-transparente
                    movable=False
                )
                regions.append(region)
                
            # Parpadeo en curso ojo derecho
            if self.right_blinking and self.blink_start_time["right"] is not None:
                region = pg.LinearRegionItem(
                    values=[self.blink_start_time["right"], current_time],
                    brush=pg.mkBrush(255, 0, 0, 50),  # Rojo semi-transparente
                    movable=False
                )
                regions.append(region)
        
        return regions
    
    def clear(self):
        """Limpia todos los datos de parpadeos."""
        self.left_blink_regions.clear()
        self.right_blink_regions.clear()
        self.left_blinking = False
        self.right_blinking = False
        self.blink_start_time = {"left": None, "right": None}
    
    def get_blink_data(self):
        """
        Obtiene una copia de los datos de parpadeos.
        
        Returns:
            dict: Datos de regiones de parpadeo
        """
        return {
            'left_blink_regions': self.left_blink_regions.copy(),
            'right_blink_regions': self.right_blink_regions.copy(),
            'left_blinking': self.left_blinking,
            'right_blinking': self.right_blinking,
            'blink_start_time': self.blink_start_time.copy()
        }