import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class BasePlotFactory:
    """Clase para crear y configurar gráficos base con estilos consistentes."""
    
    @staticmethod
    def create_plot():
        """Crea un gráfico básico con configuración estándar."""
        plot = pg.PlotWidget()
        
        # Configurar fondo y ejes
        plot.setBackground('w')
        plot.getAxis('bottom').setPen(pg.mkPen(color='black', width=1))
        plot.getAxis('left').setPen(pg.mkPen(color='black', width=1))

        # Configurar color del texto de los ejes
        plot.getAxis('bottom').setTextPen(pg.mkPen(color='black'))
        plot.getAxis('left').setTextPen(pg.mkPen(color='black'))

        # Configurar fuente
        font = QFont()
        font.setPointSize(10)
        plot.getAxis('bottom').setTickFont(font)
        plot.getAxis('left').setTickFont(font)

        # Estilo de fuente para las etiquetas
        labelStyle = {'color': '#000', 'font-size': '10pt'}
        plot.setLabel('left', '', **labelStyle)
        plot.setLabel('bottom', '', **labelStyle)

        # Configuración de rendimiento
        plot.showGrid(x=True, y=True)
        plot.setDownsampling(auto=True, mode='peak')
        plot.setClipToView(True)
        
        return plot
    
    @staticmethod
    def create_curve(plot, is_left_eye=True):
        """Crea una curva para el gráfico con el estilo correcto."""
        if is_left_eye:
            # Ojo izquierdo (azul)
            pen = pg.mkPen(color=(0, 0, 200), width=1)
            name = "Ojo Izquierdo"
        else:
            # Ojo derecho (rojo)
            pen = pg.mkPen(color=(200, 0, 0), width=1)
            name = "Ojo Derecho"
            
        curve = plot.plot(pen=pen, name=name)
        curve.setDownsampling(auto=True, method='peak')
        curve.setClipToView(True)
        
        return curve
    
    @staticmethod
    def create_infinite_line(plot, angle=90, movable=True):
        """Crea una línea infinita para el gráfico."""
        line = pg.InfiniteLine(angle=angle, movable=movable)
        plot.addItem(line)
        return line
    
    @staticmethod
    def create_blink_region(start, end, is_left_eye=True):
        """Crea una región para representar un parpadeo."""
        if is_left_eye:
            # Ojo izquierdo (azul semi-transparente)
            brush = pg.mkBrush(0, 0, 255, 50)
        else:
            # Ojo derecho (rojo semi-transparente)
            brush = pg.mkBrush(255, 0, 0, 50)
            
        region = pg.LinearRegionItem(
            values=[start, end],
            brush=brush,
            movable=False
        )
        
        return region