"""
Generador de PDF para informes VNG
Crea informes médicos en formato PDF con gráficos, datos del paciente y resultados
Compatible con PySide6 y pyqtgraph
"""

import os
import io
from datetime import datetime
import numpy as np

try:
    import pyqtgraph as pg
    from pyqtgraph.exporters import ImageExporter
    PYQTGRAPH_AVAILABLE = True
except ImportError:
    print("Warning: pyqtgraph no disponible")
    PYQTGRAPH_AVAILABLE = False

try:
    from PySide6.QtWidgets import QFileDialog, QMessageBox, QApplication
    from PySide6.QtCore import QStandardPaths
    from PySide6.QtGui import QPainter, QPagedPaintDevice, QFont, QColor, QPen
    from PySide6.QtPrintSupport import QPrinter
    PYSIDE6_AVAILABLE = True
except ImportError as e:
    print(f"Warning: PySide6 no disponible completamente: {e}")
    PYSIDE6_AVAILABLE = False

class VNGPDFGenerator:
    """Generador de informes PDF para el sistema VNG usando PySide6 y pyqtgraph"""
    
    def __init__(self):
        # Verificar dependencias
        if not PYSIDE6_AVAILABLE:
            raise ImportError("PySide6 no está disponible. Verifique la instalación.")
        
        if not PYQTGRAPH_AVAILABLE:
            print("Warning: pyqtgraph no disponible, los gráficos se omitirán")
        else:
            # Configurar pyqtgraph para usar Qt
            pg.setConfigOptions(antialias=True)
        
    def generate_report(self, patient_data, selected_tests, comments, nistagmo_results=None, evaluator_name="", parent_widget=None):
        """
        Genera el informe PDF completo
        
        Args:
            patient_data: Datos del paciente
            selected_tests: Lista de pruebas seleccionadas
            comments: Comentarios del wizard
            nistagmo_results: Resultados de conteo de nistagmo/VCL (opcional)
            evaluator_name: Nombre del evaluador
            parent_widget: Widget padre para diálogos
        """
        try:
            # Solicitar ubicación de guardado
            default_name = f"Informe_VNG_{patient_data.get('nombre', 'Paciente')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            default_path = os.path.join(
                QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation),
                default_name
            )
            
            file_path, _ = QFileDialog.getSaveFileName(
                parent_widget,
                "Guardar Informe PDF",
                default_path,
                "Archivos PDF (*.pdf);;Todos los archivos (*)"
            )
            
            if not file_path:
                return False  # Usuario canceló
            
            # Generar el PDF
            self._create_pdf_report(file_path, patient_data, selected_tests, comments, nistagmo_results, evaluator_name)
            
            # Confirmar éxito
            QMessageBox.information(
                parent_widget,
                "Informe Generado",
                f"El informe PDF se guardó exitosamente en:\n{file_path}"
            )
            
            return True
            
        except Exception as e:
            QMessageBox.critical(
                parent_widget,
                "Error",
                f"Error generando informe PDF:\n{str(e)}"
            )
            return False
    
    def _create_pdf_report(self, file_path, patient_data, selected_tests, comments, nistagmo_results, evaluator_name):
        """Crear el archivo PDF con todo el contenido usando QPrinter"""
        
        # Configurar impresora PDF
        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(file_path)
        printer.setPageSize(QPagedPaintDevice.A4)
        printer.setPageMargins(20, 20, 20, 20, QPrinter.Millimeter)
        
        # Crear painter
        painter = QPainter()
        painter.begin(printer)
        
        try:
            # Obtener dimensiones de la página
            page_rect = printer.pageRect()
            page_width = page_rect.width()
            page_height = page_rect.height()
            
            # Dibujar contenido del informe
            current_y = self._draw_title(painter, page_width)
            current_y = self._draw_patient_header(painter, patient_data, page_width, current_y)
            current_y = self._draw_test_graphs(painter, selected_tests, page_width, page_height, current_y)
            current_y = self._draw_comments_section(painter, comments, page_width, current_y)
            
            if nistagmo_results:
                current_y = self._draw_nistagmo_results(painter, nistagmo_results, page_width, current_y)
            
            self._draw_evaluator_signature(painter, evaluator_name, page_width, page_height)
            
        finally:
            painter.end()
    
    def _draw_title(self, painter, page_width):
        """Dibujar título del informe"""
        title_font = QFont("Arial", 16, QFont.Bold)
        painter.setFont(title_font)
        painter.setPen(QColor(0, 0, 0))
        
        title_rect = painter.boundingRect(0, 0, page_width, 100, 0, "INFORME DE VIDEONISTAGMOGRAFÍA (VNG)")
        painter.drawText(title_rect, 0x0004, "INFORME DE VIDEONISTAGMOGRAFÍA (VNG)")  # Qt.AlignCenter
        
        return title_rect.bottom() + 20
    
    def _draw_patient_header(self, painter, patient_data, page_width, y_pos):
        """Dibujar encabezado con datos del paciente"""
        header_font = QFont("Arial", 12, QFont.Bold)
        painter.setFont(header_font)
        
        # Datos del paciente
        nombre = patient_data.get('nombre', 'No especificado')
        rut = patient_data.get('rut_id', 'No especificado')
        edad = patient_data.get('edad', 'No especificada')
        fecha_informe = datetime.now().strftime("%d/%m/%Y")
        
        header_text = f"Paciente: {nombre}    RUT: {rut}    Edad: {edad} años    Fecha del Informe: {fecha_informe}"
        
        header_rect = painter.boundingRect(0, y_pos, page_width, 50, 0, header_text)
        
        # Dibujar fondo gris claro
        painter.fillRect(header_rect.adjusted(-10, -5, 10, 5), QColor(240, 240, 240))
        
        painter.drawText(header_rect, 0x0004, header_text)  # Qt.AlignCenter
        
        return header_rect.bottom() + 30
    
    def _draw_test_graphs(self, painter, selected_tests, page_width, page_height, y_pos):
        """Dibujar gráficos de las pruebas usando pyqtgraph"""
        if not selected_tests:
            return y_pos
        
        # Calcular disposición de gráficos
        num_tests = len(selected_tests)
        
        if num_tests <= 4:
            cols = 2
            rows = 2
        elif num_tests <= 6:
            cols = 3
            rows = 2
        else:
            cols = 3
            rows = 3
        
        # Dimensiones de cada gráfico
        graph_width = (page_width - 60) // cols  # Espaciado entre gráficos
        graph_height = min(200, (page_height - y_pos - 200) // rows)  # Altura limitada
        
        graphs_drawn = 0
        current_row = 0
        
        for i, test_item in enumerate(selected_tests[:9]):  # Máximo 9 gráficos
            if graphs_drawn >= rows * cols:
                break
            
            col = graphs_drawn % cols
            row = graphs_drawn // cols
            
            x_pos = col * (graph_width + 20) + 10
            graph_y_pos = y_pos + row * (graph_height + 30)
            
            # Crear gráfico con pyqtgraph
            graph_image = self._create_test_graph(test_item['test_data'], graph_width, graph_height)
            
            if graph_image:
                painter.drawImage(x_pos, graph_y_pos, graph_image)
            
            graphs_drawn += 1
            current_row = row
        
        return y_pos + (current_row + 1) * (graph_height + 30) + 20
    
    def _create_test_graph(self, test_data, width, height):
        """Crear gráfico individual usando pyqtgraph"""
        try:
            if not PYQTGRAPH_AVAILABLE:
                return None
                
            # Crear widget de gráfico
            plot_widget = pg.PlotWidget()
            plot_widget.resize(width, height)
            plot_widget.setBackground('w')  # Fondo blanco
            
            # Configurar el gráfico
            plot_widget.setLabel('left', 'Posición (°)')
            plot_widget.setLabel('bottom', 'Tiempo (s)')
            plot_widget.setTitle(test_data.get('tipo', 'Prueba'))
            
            # Obtener datos CSV
            csv_data = test_data.get('csv_data', [])
            
            if csv_data:
                # Verificar que tenemos las columnas necesarias
                if csv_data and 'tiempo' in csv_data[0] and 'pos_h' in csv_data[0] and 'pos_v' in csv_data[0]:
                    # Extraer arrays de datos
                    tiempo_data = [row.get('tiempo', 0) for row in csv_data]
                    pos_h_data = [row.get('pos_h', 0) for row in csv_data]
                    pos_v_data = [row.get('pos_v', 0) for row in csv_data]
                    
                    # Filtrar datos para 60-100 segundos
                    tiempo_max = min(max(tiempo_data), 100)
                    tiempo_min = max(0, tiempo_max - 80) if tiempo_max >= 60 else 0
                    
                    # Filtrar arrays
                    filtered_tiempo = []
                    filtered_pos_h = []
                    filtered_pos_v = []
                    
                    for i, t in enumerate(tiempo_data):
                        if tiempo_min <= t <= tiempo_max:
                            filtered_tiempo.append(t)
                            filtered_pos_h.append(pos_h_data[i])
                            filtered_pos_v.append(pos_v_data[i])
                    
                    if filtered_tiempo:
                        # Graficar datos
                        plot_widget.plot(filtered_tiempo, filtered_pos_h, 
                                       pen=pg.mkPen(color='b', width=2), name='Horizontal')
                        plot_widget.plot(filtered_tiempo, filtered_pos_v, 
                                       pen=pg.mkPen(color='r', width=2), name='Vertical')
                        
                        # Agregar leyenda
                        plot_widget.addLegend()
                        
                        # Configurar grilla
                        plot_widget.showGrid(x=True, y=True, alpha=0.3)
            
            # Exportar a imagen
            exporter = ImageExporter(plot_widget.plotItem)
            exporter.parameters()['width'] = width
            exporter.parameters()['height'] = height
            
            # Renderizar a QImage
            image = exporter.export(toBytes=True)
            
            # Limpiar widget
            plot_widget.close()
            
            return image
            
        except Exception as e:
            print(f"Error creando gráfico: {e}")
            return None
    
    def _draw_comments_section(self, painter, comments, page_width, y_pos):
        """Dibujar sección de comentarios"""
        comments_font = QFont("Arial", 10)
        title_font = QFont("Arial", 11, QFont.Bold)
        
        # Título
        painter.setFont(title_font)
        painter.setPen(QColor(0, 0, 0))
        title_rect = painter.boundingRect(0, y_pos, page_width, 30, 0, "COMENTARIOS:")
        painter.drawText(title_rect, 0, "COMENTARIOS:")
        
        # Contenido de comentarios
        painter.setFont(comments_font)
        comments_text = comments.strip() if comments and comments.strip() else "Sin comentarios adicionales."
        
        # Calcular área para comentarios
        text_rect = painter.boundingRect(10, title_rect.bottom() + 10, page_width - 20, 100, 
                                       0x1000, comments_text)  # Qt.TextWordWrap
        
        # Dibujar fondo
        painter.fillRect(text_rect.adjusted(-5, -5, 5, 5), QColor(250, 250, 250))
        painter.setPen(QColor(128, 128, 128))
        painter.drawRect(text_rect.adjusted(-5, -5, 5, 5))
        
        # Dibujar texto
        painter.setPen(QColor(0, 0, 0))
        painter.drawText(text_rect, 0x1000, comments_text)  # Qt.TextWordWrap
        
        return text_rect.bottom() + 20
    
    def _draw_nistagmo_results(self, painter, nistagmo_results, page_width, y_pos):
        """Dibujar sección de resultados de nistagmo/VCL"""
        results_font = QFont("Arial", 10)
        title_font = QFont("Arial", 11, QFont.Bold)
        
        # Título
        painter.setFont(title_font)
        painter.setPen(QColor(0, 0, 0))
        title_rect = painter.boundingRect(0, y_pos, page_width, 30, 0, "RESULTADOS DE ANÁLISIS:")
        painter.drawText(title_rect, 0, "RESULTADOS DE ANÁLISIS:")
        
        # Contenido de resultados
        painter.setFont(results_font)
        
        results_text = ""
        if isinstance(nistagmo_results, dict):
            for key, value in nistagmo_results.items():
                results_text += f"• {key}: {value}\n"
        elif isinstance(nistagmo_results, str):
            results_text = nistagmo_results
        else:
            results_text = str(nistagmo_results)
        
        # Calcular área para resultados
        text_rect = painter.boundingRect(10, title_rect.bottom() + 10, page_width - 20, 80,
                                       0x1000, results_text)  # Qt.TextWordWrap
        
        # Dibujar fondo
        painter.fillRect(text_rect.adjusted(-5, -5, 5, 5), QColor(240, 248, 255))
        painter.setPen(QColor(100, 149, 237))
        painter.drawRect(text_rect.adjusted(-5, -5, 5, 5))
        
        # Dibujar texto
        painter.setPen(QColor(0, 0, 0))
        painter.drawText(text_rect, 0x1000, results_text)  # Qt.TextWordWrap
        
        return text_rect.bottom() + 20
    
    def _draw_evaluator_signature(self, painter, evaluator_name, page_width, page_height):
        """Dibujar firma del evaluador al final"""
        signature_font = QFont("Arial", 10)
        painter.setFont(signature_font)
        
        fecha_actual = datetime.now().strftime("%d/%m/%Y")
        evaluator_text = f"Evaluador: {evaluator_name or 'No especificado'}\nFecha: {fecha_actual}"
        
        # Posicionar en la parte inferior derecha
        text_rect = painter.boundingRect(0, 0, page_width//2, 60, 0x1000, evaluator_text)
        x_pos = page_width - text_rect.width() - 20
        y_pos = page_height - text_rect.height() - 20
        
        # Dibujar fondo
        final_rect = text_rect.translated(x_pos, y_pos)
        painter.fillRect(final_rect.adjusted(-10, -5, 10, 5), QColor(255, 255, 240))
        painter.setPen(QColor(218, 165, 32))
        painter.drawRect(final_rect.adjusted(-10, -5, 10, 5))
        
        # Dibujar texto
        painter.setPen(QColor(0, 0, 0))
        painter.drawText(final_rect, 0x1000, evaluator_text)


# Ejemplo de uso e integración
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    
    # Crear aplicación si no existe
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    # Datos de ejemplo para pruebas
    sample_patient_data = {
        'nombre': 'Juan Pérez García',
        'rut_id': '12345678-9',
        'edad': 45
    }
    
    sample_tests = [
        {
            'test_data': {
                'tipo': 'Seguimiento Lento',
                'fecha': 1645123456,
                'csv_data': [
                    {'tiempo': i, 'pos_h': 5*np.sin(i*0.1), 'pos_v': 3*np.cos(i*0.15)}
                    for i in range(0, 80)
                ]
            }
        }
    ]
    
    sample_comments = "Paciente presenta ligero nistagmo espontáneo. Se recomienda seguimiento."
    
    # Crear y probar generador
    generator = VNGPDFGenerator()
    # generator.generate_report(sample_patient_data, sample_tests, sample_comments)