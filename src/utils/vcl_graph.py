import sys
import numpy as np
from typing import List, Tuple, Dict, Any
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QMainWindow, QPushButton, QHBoxLayout, QCheckBox
from PySide6.QtCore import Signal, QTimer
import pyqtgraph as pg


class VCLGraphWidget(QWidget):

    # Señales
    point_added = Signal(float, float, str)
    point_removed = Signal(float, float, str) 
    torok_region_changed = Signal(float, float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_data()
        self.setup_tools()
        
    def setup_ui(self):
        """Configurar interfaz de usuario"""
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(5)
        
        # Crear gráficos con configuración robusta
        self.graph_horizontal = pg.PlotWidget()
        self.graph_vertical = pg.PlotWidget()
        
        # Configurar títulos y etiquetas después de crear los widgets
        self.graph_horizontal.setTitle("Movimientos Horizontales")
        self.graph_vertical.setTitle("Movimientos Verticales")
        
        self.graph_horizontal.setLabel('left', 'Amplitud (°)')
        self.graph_horizontal.setLabel('bottom', 'Tiempo (s)')
        self.graph_vertical.setLabel('left', 'Amplitud (°)')
        self.graph_vertical.setLabel('bottom', 'Tiempo (s)')
        
        # Configurar rangos iniciales
        self.graph_horizontal.setXRange(0, 100)
        self.graph_horizontal.setYRange(-30, 30)
        self.graph_vertical.setXRange(0, 100)
        self.graph_vertical.setYRange(-15, 15)
        
        # Habilitar interacción
        self.graph_horizontal.setMouseEnabled(x=True, y=True)
        self.graph_vertical.setMouseEnabled(x=True, y=True)
        
        # Agregar gráficos al layout
        self.layout.addWidget(self.graph_horizontal)
        self.layout.addWidget(self.graph_vertical)
        
    def setup_data(self):
        """Inicializar variables de datos"""
        self.data = {
            'tiempo': [],
            'horizontal_ojo_izq': [],
            'horizontal_ojo_der': [],
            'vertical_ojo_izq': [],
            'vertical_ojo_der': [],
            'ojo_izq_visible': True,  # UN SOLO BOOLEAN por ojo
            'ojo_der_visible': True,
            'puntos_interes': []
        }
        
        # Curvas de datos
        self.curves = {
            'horizontal_izq': self.graph_horizontal.plot(pen=pg.mkPen('b', width=2), name='Ojo Izquierdo'),
            'horizontal_der': self.graph_horizontal.plot(pen=pg.mkPen('r', width=2), name='Ojo Derecho'),
            'vertical_izq': self.graph_vertical.plot(pen=pg.mkPen('b', width=2), name='Ojo Izquierdo'),
            'vertical_der': self.graph_vertical.plot(pen=pg.mkPen('r', width=2), name='Ojo Derecho')
        }
        
        # Puntos de interés
        self.interest_points = {'horizontal': [], 'vertical': []}
        
    def setup_tools(self):
        """Configurar herramientas"""
        # Estado de herramientas
        self.tools_active = {
            'torok': False,
            'peak_editing': False,
            'tiempo_fijacion': False,
            'zoom': False,
            'crosshair': False,
            'peak_detection': False
        }
        
        # ROI Torok
        self.torok_roi_h = None
        self.torok_roi_v = None
        
        # ROIs tiempo de fijación
        self.tiempo_fijacion_rois = []
        
        # Conectar eventos de mouse de forma más segura
        QTimer.singleShot(100, self.connect_mouse_events)
        
    def connect_mouse_events(self):
        """Conectar eventos de mouse después de que los widgets estén completamente inicializados"""
        try:
            if hasattr(self.graph_horizontal, 'scene') and self.graph_horizontal.scene():
                self.graph_horizontal.scene().sigMouseClicked.connect(self.on_mouse_click_horizontal)
            if hasattr(self.graph_vertical, 'scene') and self.graph_vertical.scene():
                self.graph_vertical.scene().sigMouseClicked.connect(self.on_mouse_click_vertical)
        except Exception as e:
            print(f"Error conectando eventos de mouse: {e}")
        
    def set_data(self, data: dict):
        """Cargar datos y actualizar gráficos"""
        # Validar límite de 5 minutos
        if len(data.get('tiempo', [])) > 0:
            max_time = max(data['tiempo'])
            if max_time > 300:  # 5 minutos = 300 segundos
                print("Advertencia: Datos exceden 5 minutos, se truncarán")
                # Truncar datos
                valid_indices = [i for i, t in enumerate(data['tiempo']) if t <= 300]
                for key in data:
                    if isinstance(data[key], list) and key != 'puntos_interes':
                        data[key] = [data[key][i] for i in valid_indices]
                # Filtrar puntos de interés
                data['puntos_interes'] = [(t, a, tipo) for t, a, tipo in data['puntos_interes'] if t <= 300]
        
        self.data = data.copy()
        self.update_plots()
        
    def set_eye_visibility(self, ojo_izq_visible: bool, ojo_der_visible: bool):
        """Establecer visibilidad de ojos y actualizar gráficos"""
        self.data['ojo_izq_visible'] = ojo_izq_visible
        self.data['ojo_der_visible'] = ojo_der_visible
        self.update_plots()
        
    def update_plots(self):
        """Actualizar gráficos con datos actuales"""
        if not self.data['tiempo']:
            return
            
        try:
            tiempo = np.array(self.data['tiempo'])
            
            # Preparar datos
            h_izq = np.array(self.data['horizontal_ojo_izq'], dtype=float)
            h_der = np.array(self.data['horizontal_ojo_der'], dtype=float)
            v_izq = np.array(self.data['vertical_ojo_izq'], dtype=float)
            v_der = np.array(self.data['vertical_ojo_der'], dtype=float)
            
            # Aplicar visibilidad: si ojo_visible es False, ocultar TODOS los datos de ese ojo
            if not self.data.get('ojo_izq_visible', True):
                # Ojo izquierdo no visible: ocultar en ambos gráficos
                self.curves['horizontal_izq'].setData([], [])
                self.curves['vertical_izq'].setData([], [])
            else:
                # Ojo izquierdo visible: mostrar datos
                self.curves['horizontal_izq'].setData(tiempo, h_izq)
                self.curves['vertical_izq'].setData(tiempo, v_izq)
            
            if not self.data.get('ojo_der_visible', True):
                # Ojo derecho no visible: ocultar en ambos gráficos
                self.curves['horizontal_der'].setData([], [])
                self.curves['vertical_der'].setData([], [])
            else:
                # Ojo derecho visible: mostrar datos
                self.curves['horizontal_der'].setData(tiempo, h_der)
                self.curves['vertical_der'].setData(tiempo, v_der)
            
            # Actualizar rangos automáticamente
            if len(tiempo) > 0:
                self.graph_horizontal.setXRange(tiempo[0], tiempo[-1], padding=0.02)
                self.graph_vertical.setXRange(tiempo[0], tiempo[-1], padding=0.02)
            
            # Actualizar puntos de interés
            QTimer.singleShot(50, self.update_interest_points)
            
        except Exception as e:
            print(f"Error actualizando gráficos: {e}")
        
    def update_interest_points(self):
        """Actualizar puntos de interés en los gráficos"""
        try:
            # Limpiar puntos existentes
            for points in self.interest_points['horizontal']:
                if points is not None:
                    self.graph_horizontal.removeItem(points)
            for points in self.interest_points['vertical']:
                if points is not None:
                    self.graph_vertical.removeItem(points)
                
            self.interest_points = {'horizontal': [], 'vertical': []}
            
            # Agregar nuevos puntos
            for tiempo, amplitud, tipo in self.data['puntos_interes']:
                if tipo == 'horizontal':
                    point = pg.ScatterPlotItem([tiempo], [amplitud], 
                                             pen=pg.mkPen('orange', width=2),
                                             brush=pg.mkBrush('orange'),
                                             size=8, symbol='o')
                    self.graph_horizontal.addItem(point)
                    self.interest_points['horizontal'].append(point)
                elif tipo == 'vertical':
                    point = pg.ScatterPlotItem([tiempo], [amplitud],
                                             pen=pg.mkPen('orange', width=2), 
                                             brush=pg.mkBrush('orange'),
                                             size=8, symbol='o')
                    self.graph_vertical.addItem(point)
                    self.interest_points['vertical'].append(point)
            
        except Exception as e:
            print(f"Error actualizando puntos de interés: {e}")
    
    def get_data(self) -> dict:
        """Obtener datos actuales"""
        return self.data.copy()
    
    def get_torok(self) -> dict:
        """Obtener datos del ROI Torok seleccionado"""
        if not self.tools_active['torok'] or self.torok_roi_h is None:
            return {}
            
        # Obtener región del ROI
        region = self.torok_roi_h.getRegion()
        inicio, fin = region[0], region[1]
        
        # Filtrar datos por región
        tiempo = np.array(self.data['tiempo'])
        mask = (tiempo >= inicio) & (tiempo <= fin)
        
        if not np.any(mask):
            return {}
            
        indices = np.where(mask)[0]
        
        filtered_data = {}
        for key in self.data:
            if key == 'puntos_interes':
                filtered_data[key] = [(t, a, tipo) for t, a, tipo in self.data[key] 
                                    if inicio <= t <= fin]
            elif isinstance(self.data[key], list) and len(self.data[key]) == len(tiempo):
                filtered_data[key] = [self.data[key][i] for i in indices]
            else:
                filtered_data[key] = self.data[key]
                
        return filtered_data
    
    def activate_torok_tool(self):
        """ROI amarillo móvil (10-20s por defecto para datos de prueba)"""
        if self.tools_active['torok']:
            return
            
        self.tools_active['torok'] = True
        
        # Crear ROI en gráfico horizontal (ajustado para datos de 60s)
        self.torok_roi_h = pg.LinearRegionItem(values=(10, 20), 
                                             brush=pg.mkBrush(255, 255, 0, 80),
                                             pen=pg.mkPen('orange', width=2))
        self.graph_horizontal.addItem(self.torok_roi_h)
        
        # Crear ROI en gráfico vertical
        self.torok_roi_v = pg.LinearRegionItem(values=(10, 20),
                                             brush=pg.mkBrush(255, 255, 0, 80), 
                                             pen=pg.mkPen('orange', width=2))
        self.graph_vertical.addItem(self.torok_roi_v)
        
        # Sincronizar ROIs
        self.torok_roi_h.sigRegionChanged.connect(self.sync_torok_roi_h_to_v)
        self.torok_roi_v.sigRegionChanged.connect(self.sync_torok_roi_v_to_h)
        self.torok_roi_h.sigRegionChanged.connect(self.emit_torok_change)
        
    def sync_torok_roi_h_to_v(self):
        """Sincronizar ROI horizontal a vertical"""
        if self.torok_roi_v is not None:
            self.torok_roi_v.sigRegionChanged.disconnect()
            self.torok_roi_v.setRegion(self.torok_roi_h.getRegion())
            self.torok_roi_v.sigRegionChanged.connect(self.sync_torok_roi_v_to_h)
            
    def sync_torok_roi_v_to_h(self):
        """Sincronizar ROI vertical a horizontal"""
        if self.torok_roi_h is not None:
            self.torok_roi_h.sigRegionChanged.disconnect()
            self.torok_roi_h.setRegion(self.torok_roi_v.getRegion())
            self.torok_roi_h.sigRegionChanged.connect(self.sync_torok_roi_h_to_v)
            self.torok_roi_h.sigRegionChanged.connect(self.emit_torok_change)
            
    def emit_torok_change(self):
        """Emitir señal de cambio de región Torok"""
        if self.torok_roi_h is not None:
            region = self.torok_roi_h.getRegion()
            self.torok_region_changed.emit(region[0], region[1])
    
    def deactivate_torok_tool(self):
        """Desactivar ROI Torok"""
        if not self.tools_active['torok']:
            return
            
        self.tools_active['torok'] = False
        
        if self.torok_roi_h is not None:
            self.graph_horizontal.removeItem(self.torok_roi_h)
            self.torok_roi_h = None
            
        if self.torok_roi_v is not None:
            self.graph_vertical.removeItem(self.torok_roi_v)
            self.torok_roi_v = None
    
    def activate_peak_editing(self):
        """Click para crear puntos, click en existente para borrar"""
        self.tools_active['peak_editing'] = True
        
    def deactivate_peak_editing(self):
        """Desactivar edición de puntos"""
        self.tools_active['peak_editing'] = False
        
    def on_mouse_click_horizontal(self, event):
        """Manejar click en gráfico horizontal"""
        if not self.tools_active['peak_editing']:
            return
            
        if event.double():
            return
            
        pos = event.scenePos()
        if self.graph_horizontal.plotItem.vb.sceneBoundingRect().contains(pos):
            mouse_point = self.graph_horizontal.plotItem.vb.mapSceneToView(pos)
            self.handle_point_click(mouse_point.x(), mouse_point.y(), 'horizontal')
            
    def on_mouse_click_vertical(self, event):
        """Manejar click en gráfico vertical"""
        if not self.tools_active['peak_editing']:
            return
            
        if event.double():
            return
            
        pos = event.scenePos()
        if self.graph_vertical.plotItem.vb.sceneBoundingRect().contains(pos):
            mouse_point = self.graph_vertical.plotItem.vb.mapSceneToView(pos)
            self.handle_point_click(mouse_point.x(), mouse_point.y(), 'vertical')
            
    def handle_point_click(self, tiempo, amplitud, tipo):
        """Manejar click para crear/eliminar puntos"""
        # Buscar punto existente cerca del click
        tolerance = 0.5  # Tolerancia para detectar puntos existentes
        point_to_remove = None
        
        for i, (t, a, tipo_punto) in enumerate(self.data['puntos_interes']):
            if (tipo_punto == tipo and 
                abs(t - tiempo) < tolerance and 
                abs(a - amplitud) < tolerance):
                point_to_remove = i
                break
                
        if point_to_remove is not None:
            # Eliminar punto existente
            removed_point = self.data['puntos_interes'].pop(point_to_remove)
            self.point_removed.emit(removed_point[0], removed_point[1], removed_point[2])
        else:
            # Crear nuevo punto
            self.data['puntos_interes'].append((tiempo, amplitud, tipo))
            self.point_added.emit(tiempo, amplitud, tipo)
            
        self.update_interest_points()
    
    def activate_tiempo_fijacion(self):
        """Herramienta para crear ROIs verdes inmóviles"""
        self.tools_active['tiempo_fijacion'] = True
        
    def deactivate_tiempo_fijacion(self):
        """Desactivar herramienta tiempo fijación"""
        self.tools_active['tiempo_fijacion'] = False
        
    def create_tiempo_fijacion(self, inicio: float, fin: float):
        """Crear ROI verde inmóvil en tiempo real"""
        # ROI en gráfico horizontal
        roi_h = pg.LinearRegionItem(values=(inicio, fin),
                                   brush=pg.mkBrush(0, 255, 0, 60),
                                   pen=pg.mkPen('green', width=1),
                                   movable=False)
        self.graph_horizontal.addItem(roi_h)
        
        # ROI en gráfico vertical  
        roi_v = pg.LinearRegionItem(values=(inicio, fin),
                                   brush=pg.mkBrush(0, 255, 0, 60),
                                   pen=pg.mkPen('green', width=1), 
                                   movable=False)
        self.graph_vertical.addItem(roi_v)
        
        self.tiempo_fijacion_rois.append((roi_h, roi_v, inicio, fin))
        
    def get_tiempos_fijacion(self) -> List[Tuple[float, float]]:
        """Obtener intervalos de fijación"""
        return [(inicio, fin) for _, _, inicio, fin in self.tiempo_fijacion_rois]
    
    # Herramientas adicionales (implementación básica)
    def activate_zoom(self):
        """Activar zoom en gráficos"""
        self.tools_active['zoom'] = True
        
    def deactivate_zoom(self):
        """Desactivar zoom"""
        self.tools_active['zoom'] = False
        
    def activate_crosshair(self):
        """Activar cursor cruzado"""
        self.tools_active['crosshair'] = True
        
    def deactivate_crosshair(self):
        """Desactivar cursor cruzado"""
        self.tools_active['crosshair'] = False
        
    def activate_peak_detection(self):
        """Activar detección automática de peaks"""
        self.tools_active['peak_detection'] = True
        
    def deactivate_peak_detection(self):
        """Desactivar detección automática"""
        self.tools_active['peak_detection'] = False


# EJEMPLO DE TESTING CON CONTROLES DE VISIBILIDAD
class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VCL Graph Widget - Con Control de Visibilidad")
        self.setGeometry(100, 100, 1200, 900)
        
        # Widget principal
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Layout principal
        layout = QVBoxLayout(self.central_widget)
        
        # CONTROLES DE VISIBILIDAD DE OJOS
        visibility_layout = QHBoxLayout()
        
        self.chk_ojo_izq = QCheckBox("Mostrar Ojo Izquierdo (Azul)")
        self.chk_ojo_izq.setChecked(True)
        self.chk_ojo_izq.toggled.connect(self.update_eye_visibility)
        visibility_layout.addWidget(self.chk_ojo_izq)
        
        self.chk_ojo_der = QCheckBox("Mostrar Ojo Derecho (Rojo)")
        self.chk_ojo_der.setChecked(True)
        self.chk_ojo_der.toggled.connect(self.update_eye_visibility)
        visibility_layout.addWidget(self.chk_ojo_der)
        
        visibility_layout.addStretch()
        layout.addLayout(visibility_layout)
        
        # CONTROLES DE HERRAMIENTAS
        tools_layout = QHBoxLayout()
        
        self.btn_torok = QPushButton("Toggle Torok")
        self.btn_torok.clicked.connect(self.toggle_torok)
        tools_layout.addWidget(self.btn_torok)
        
        self.btn_peak_edit = QPushButton("Toggle Peak Edit")
        self.btn_peak_edit.clicked.connect(self.toggle_peak_edit)
        tools_layout.addWidget(self.btn_peak_edit)
        
        self.btn_tiempo_fij = QPushButton("Add Tiempo Fijación")
        self.btn_tiempo_fij.clicked.connect(self.add_tiempo_fijacion)
        tools_layout.addWidget(self.btn_tiempo_fij)
        
        layout.addLayout(tools_layout)
        
        # Widget de gráficos
        self.graph_widget = VCLGraphWidget()
        layout.addWidget(self.graph_widget)
        
        # Conectar señales
        self.graph_widget.point_added.connect(self.on_point_added)
        self.graph_widget.point_removed.connect(self.on_point_removed)
        self.graph_widget.torok_region_changed.connect(self.on_torok_changed)
        
        # Cargar datos de prueba
        self.load_test_data()
        
    def update_eye_visibility(self):
        """Actualizar visibilidad de ojos basado en checkboxes"""
        ojo_izq_visible = self.chk_ojo_izq.isChecked()
        ojo_der_visible = self.chk_ojo_der.isChecked()
        
        self.graph_widget.set_eye_visibility(ojo_izq_visible, ojo_der_visible)
        print(f"Visibilidad actualizada: Izq={ojo_izq_visible}, Der={ojo_der_visible}")
        
    def load_test_data(self):
        """Cargar datos de prueba simples y claros"""
        # Generar 60 segundos de datos (1 minuto)
        tiempo = np.linspace(0, 60, 600)  # 10 Hz, 600 puntos
        
        print(f"Tiempo generado: {tiempo[:5]} ... {tiempo[-5:]}")
        print(f"Rango de tiempo: {tiempo[0]} a {tiempo[-1]} segundos")
        
        # Movimientos horizontales simples
        h_izq = 10 * np.sin(2 * np.pi * 0.2 * tiempo) + np.random.randn(len(tiempo)) * 0.5
        h_der = 8 * np.sin(2 * np.pi * 0.15 * tiempo + 0.5) + np.random.randn(len(tiempo)) * 0.5
        
        # Movimientos verticales simples  
        v_izq = 5 * np.sin(2 * np.pi * 0.1 * tiempo) + np.random.randn(len(tiempo)) * 0.3
        v_der = 4 * np.sin(2 * np.pi * 0.12 * tiempo + 0.3) + np.random.randn(len(tiempo)) * 0.3
        
        print(f"h_izq: {h_izq[:3]}")
        print(f"h_der: {h_der[:3]}")
        
        # Visibilidad: UN SOLO BOOLEAN POR OJO
        ojo_izq_visible = True
        ojo_der_visible = True
        
        # Puntos de interés claros y visibles
        puntos_interes = [
            (15.0, 10.0, 'horizontal'),   # Pico horizontal claro
            (30.0, -8.0, 'horizontal'),   # Valle horizontal claro
            (20.0, 5.0, 'vertical'),      # Pico vertical claro
            (40.0, -4.0, 'vertical'),     # Valle vertical claro
        ]
        
        datos = {
            'tiempo': tiempo.tolist(),
            'horizontal_ojo_izq': h_izq.tolist(),
            'horizontal_ojo_der': h_der.tolist(),
            'vertical_ojo_izq': v_izq.tolist(),
            'vertical_ojo_der': v_der.tolist(),
            'ojo_izq_visible': ojo_izq_visible,
            'ojo_der_visible': ojo_der_visible,
            'puntos_interes': puntos_interes
        }
        
        print(f"Datos preparados:")
        print(f"  Tiempo: {len(datos['tiempo'])} puntos")
        print(f"  Primer tiempo: {datos['tiempo'][0]}")
        print(f"  Último tiempo: {datos['tiempo'][-1]}")
        print(f"  h_izq primer valor: {datos['horizontal_ojo_izq'][0]}")
        
        self.graph_widget.set_data(datos)
        
    def toggle_torok(self):
        """Alternar herramienta Torok"""
        if self.graph_widget.tools_active['torok']:
            self.graph_widget.deactivate_torok_tool()
            self.btn_torok.setText("Activate Torok")
        else:
            self.graph_widget.activate_torok_tool()
            self.btn_torok.setText("Deactivate Torok")
            
    def toggle_peak_edit(self):
        """Alternar edición de picos"""
        if self.graph_widget.tools_active['peak_editing']:
            self.graph_widget.deactivate_peak_editing()
            self.btn_peak_edit.setText("Activate Peak Edit")
        else:
            self.graph_widget.activate_peak_editing()
            self.btn_peak_edit.setText("Deactivate Peak Edit")
            
    def add_tiempo_fijacion(self):
        """Agregar tiempo de fijación"""
        import random
        inicio = random.uniform(5, 45)
        fin = inicio + random.uniform(3, 10)
        self.graph_widget.create_tiempo_fijacion(inicio, fin)
        print(f"Tiempo de fijación creado: {inicio:.1f} - {fin:.1f}s")
        
    def on_point_added(self, tiempo, amplitud, tipo):
        """Manejar punto agregado"""
        print(f"Punto agregado: t={tiempo:.2f}s, amp={amplitud:.2f}°, tipo={tipo}")
        
    def on_point_removed(self, tiempo, amplitud, tipo):
        """Manejar punto eliminado"""
        print(f"Punto eliminado: t={tiempo:.2f}s, amp={amplitud:.2f}°, tipo={tipo}")
        
    def on_torok_changed(self, inicio, fin):
        """Manejar cambio de región Torok"""
        print(f"Región Torok: {inicio:.1f} - {fin:.1f}s")
        datos_torok = self.graph_widget.get_torok()
        if datos_torok:
            print(f"  Datos en región: {len(datos_torok.get('tiempo', []))} puntos")


def main():
    """Función principal para testing"""
    app = QApplication(sys.argv)
    
    # Configurar PyQtGraph para mayor estabilidad
    pg.setConfigOptions(antialias=True, useOpenGL=False)
    
    try:
        # Crear ventana de prueba
        window = TestWindow()
        window.show()
        
        print("=== VCL Graph Widget Test - Con Control de Visibilidad ===")
        print("Datos: 60 segundos de movimientos oculares simulados")
        print("- Gráfico superior: Movimientos horizontales (azul=izq, rojo=der)")
        print("- Gráfico inferior: Movimientos verticales (azul=izq, rojo=der)")
        print("- Puntos naranjas: Puntos de interés en 15s, 30s, 20s, 40s")
        print("")
        print("NUEVOS CONTROLES DE VISIBILIDAD:")
        print("- Checkboxes para mostrar/ocultar cada ojo independientemente")
        print("- Un checkbox afecta AMBOS gráficos del mismo ojo")
        print("")
        print("Controles de herramientas:")
        print("- Toggle Torok: ROI amarillo móvil (10-20s)")
        print("- Toggle Peak Edit: Click para crear/eliminar puntos")
        print("- Add Tiempo Fijación: ROI verde inmóvil aleatorio")
        
        sys.exit(app.exec())
        
    except Exception as e:
        print(f"Error iniciando aplicación: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()