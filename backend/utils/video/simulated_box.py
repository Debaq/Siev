import numpy as np

class SimulatedBox:
    """Clase para simular las detecciones de YOLO cuando se usa ROI fija"""
    def __init__(self, x1, y1, x2, y2):
        self.xyxy = np.array([[x1, y1, x2, y2]])
