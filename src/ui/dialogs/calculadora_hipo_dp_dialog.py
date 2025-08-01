from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                              QLineEdit, QPushButton, QLabel, QFrame, QGridLayout)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

class CalculadoraHipoDpDialog(QDialog):
    """Diálogo calculadora de Hipo/DP"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.connect_signals()
        self.init_default_values()
        
    def init_default_values(self):
        """Inicializar valores por defecto"""
        self.corte_hipo_edit.setText('25')
        self.corte_dp_edit.setText('30')
        self.calculate_formulas()
        
    def setup_ui(self):
        """Configurar interfaz de usuario"""
        self.setWindowTitle("Calculadora Hipo/DP")
        self.setModal(True)
        self.resize(400, 350)
        
        # Layout principal
        main_layout = QVBoxLayout(self)
        
        # Título
        title = QLabel("Calculadora Hipo/DP")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)
        
        # Separador
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)
        
        # Grid de inputs
        grid_layout = QGridLayout()
        
        # Fila 1
        grid_layout.addWidget(QLabel("OD 44:"), 0, 0)
        self.od_44_edit = QLineEdit()
        self.od_44_edit.setPlaceholderText("0")
        grid_layout.addWidget(self.od_44_edit, 0, 1)
        
        grid_layout.addWidget(QLabel("OI 44:"), 0, 2)
        self.oi_44_edit = QLineEdit()
        self.oi_44_edit.setPlaceholderText("0")
        grid_layout.addWidget(self.oi_44_edit, 0, 3)
        
        # Fila 2
        grid_layout.addWidget(QLabel("OD 30:"), 1, 0)
        self.od_30_edit = QLineEdit()
        self.od_30_edit.setPlaceholderText("0")
        grid_layout.addWidget(self.od_30_edit, 1, 1)
        
        grid_layout.addWidget(QLabel("OI 30:"), 1, 2)
        self.oi_30_edit = QLineEdit()
        self.oi_30_edit.setPlaceholderText("0")
        grid_layout.addWidget(self.oi_30_edit, 1, 3)
        
        # Fila 3
        grid_layout.addWidget(QLabel("Corte Hipo:"), 2, 0)
        self.corte_hipo_edit = QLineEdit()
        self.corte_hipo_edit.setText("25")
        grid_layout.addWidget(self.corte_hipo_edit, 2, 1)
        
        grid_layout.addWidget(QLabel("Corte DP:"), 2, 2)
        self.corte_dp_edit = QLineEdit()
        self.corte_dp_edit.setText("30")
        grid_layout.addWidget(self.corte_dp_edit, 2, 3)
        
        main_layout.addLayout(grid_layout)
        
        # Línea horizontal
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line2)
        
        # Fórmulas matemáticas
        formulas_layout = QVBoxLayout()
        
        # Fórmula Hipo
        hipo_title = QLabel("Fórmula Hipo:")
        hipo_title.setStyleSheet("font-weight: bold; font-size: 12px;")
        formulas_layout.addWidget(hipo_title)
        
        self.formula_hipo_label = QLabel()
        self.formula_hipo_label.setStyleSheet("color: #333; padding: 10px; background-color: #f5f5f5; border: 1px solid #ddd; font-size: 14px;")
        self.formula_hipo_label.setWordWrap(True)
        self.formula_hipo_label.setTextFormat(Qt.RichText)
        formulas_layout.addWidget(self.formula_hipo_label)
        
        # Fórmula DP
        dp_title = QLabel("Fórmula DP:")
        dp_title.setStyleSheet("font-weight: bold; font-size: 12px; margin-top: 10px;")
        formulas_layout.addWidget(dp_title)
        
        self.formula_dp_label = QLabel()
        self.formula_dp_label.setStyleSheet("color: #333; padding: 10px; background-color: #f5f5f5; border: 1px solid #ddd; font-size: 14px;")
        self.formula_dp_label.setWordWrap(True)
        self.formula_dp_label.setTextFormat(Qt.RichText)
        formulas_layout.addWidget(self.formula_dp_label)
        
        main_layout.addLayout(formulas_layout)
        
        # Línea horizontal
        line3 = QFrame()
        line3.setFrameShape(QFrame.HLine)
        line3.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line3)
        
        # Resultados finales
        final_results_layout = QVBoxLayout()
        
        results_title = QLabel("Resultados:")
        results_title.setStyleSheet("font-weight: bold; font-size: 12px;")
        final_results_layout.addWidget(results_title)
        
        self.resultado_hipo_label = QLabel("Hipo = -% (>= 25%)")
        self.resultado_hipo_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #2E7D32; padding: 5px; background-color: #E8F5E8; border: 1px solid #4CAF50;")
        final_results_layout.addWidget(self.resultado_hipo_label)
        
        self.resultado_dp_label = QLabel("DP = -% (>= 30%)")
        self.resultado_dp_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #2E7D32; padding: 5px; background-color: #E8F5E8; border: 1px solid #4CAF50;")
        final_results_layout.addWidget(self.resultado_dp_label)
        
        main_layout.addLayout(final_results_layout)
        
        # Botones
        button_layout = QHBoxLayout()
        
        self.limpiar_button = QPushButton("Limpiar Todo")
        self.limpiar_button.setStyleSheet("background-color: #FF5722; color: white; font-weight: bold; padding: 8px 16px;")
        button_layout.addWidget(self.limpiar_button)
        
        button_layout.addStretch()
        
        self.aceptar_button = QPushButton("Aceptar")
        self.aceptar_button.setDefault(True)
        self.aceptar_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px 16px;")
        button_layout.addWidget(self.aceptar_button)
        
        main_layout.addLayout(button_layout)
        
    def connect_signals(self):
        """Conectar señales"""
        # Conectar cambios en inputs para actualizar cálculos
        self.od_44_edit.textChanged.connect(self.calculate_formulas)
        self.oi_44_edit.textChanged.connect(self.calculate_formulas)
        self.od_30_edit.textChanged.connect(self.calculate_formulas)
        self.oi_30_edit.textChanged.connect(self.calculate_formulas)
        self.corte_hipo_edit.textChanged.connect(self.calculate_formulas)
        self.corte_dp_edit.textChanged.connect(self.calculate_formulas)
        
        # Botones
        self.limpiar_button.clicked.connect(self.limpiar_todo)
        self.aceptar_button.clicked.connect(self.accept)
        
    def get_value_or_variable(self, line_edit, variable_name):
        """Obtener valor numérico o nombre de variable si está vacío"""
        text = line_edit.text().strip()
        if text:
            try:
                return float(text), text
            except ValueError:
                return 0.0, variable_name
        else:
            return 0.0, variable_name
            
    def calculate_formulas(self):
        """Calcular y mostrar las fórmulas con valores o variables"""
        # Obtener valores o variables
        od_44_val, od_44_str = self.get_value_or_variable(self.od_44_edit, "OD₄₄")
        oi_44_val, oi_44_str = self.get_value_or_variable(self.oi_44_edit, "OI₄₄")
        od_30_val, od_30_str = self.get_value_or_variable(self.od_30_edit, "OD₃₀")
        oi_30_val, oi_30_str = self.get_value_or_variable(self.oi_30_edit, "OI₃₀")
        
        # Crear fórmulas en notación matemática usando HTML mejorado
        hipo_formula = f"""
        <div style="text-align: center; font-size: 16px;">
            <table style="display: inline-table; border-collapse: collapse;">
                <tr>
                    <td style="text-align: center;">Hipo =</td>
                    <td style="text-align: center; border-bottom: 2px solid black; padding: 5px 10px;">
                        ({oi_30_str} + {oi_44_str}) - ({od_30_str} + {od_44_str})
                    </td>
                    <td style="text-align: center; vertical-align: middle; padding-left: 10px;">× 100</td>
                </tr>
                <tr>
                    <td></td>
                    <td style="text-align: center; padding: 5px 10px;">
                        {oi_30_str} + {oi_44_str} + {od_30_str} + {od_44_str}
                    </td>
                    <td></td>
                </tr>
            </table>
        </div>
        """
        
        dp_formula = f"""
        <div style="text-align: center; font-size: 16px;">
            <table style="display: inline-table; border-collapse: collapse;">
                <tr>
                    <td style="text-align: center;">DP =</td>
                    <td style="text-align: center; border-bottom: 2px solid black; padding: 5px 10px;">
                        ({oi_30_str} + {od_44_str}) - ({od_30_str} + {oi_44_str})
                    </td>
                    <td style="text-align: center; vertical-align: middle; padding-left: 10px;">× 100</td>
                </tr>
                <tr>
                    <td></td>
                    <td style="text-align: center; padding: 5px 10px;">
                        {oi_30_str} + {oi_44_str} + {od_30_str} + {od_44_str}
                    </td>
                    <td></td>
                </tr>
            </table>
        </div>
        """
        
        self.formula_hipo_label.setText(hipo_formula)
        self.formula_dp_label.setText(dp_formula)
        
        # Calcular resultados numéricos
        denominador = oi_30_val + oi_44_val + od_30_val + od_44_val
        
        if denominador == 0:
            self.resultado_hipo_label.setText("Hipo = -% (>= 25%)")
            self.resultado_dp_label.setText("DP = -% (>= 30%)")
        else:
            # Calcular Hipo: ((OI30 + OI44) - (OD30 + OD44)) / (OI30 + OI44 + OD30 + OD44) * 100
            numerador_hipo = (oi_30_val + oi_44_val) - (od_30_val + od_44_val)
            resultado_hipo = (numerador_hipo / denominador) * 100
            
            # Calcular DP: ((OI30 + OD44) - (OD30 + OI44)) / (OI30 + OI44 + OD30 + OD44) * 100
            numerador_dp = (oi_30_val + od_44_val) - (od_30_val + oi_44_val)
            resultado_dp = (numerador_dp / denominador) * 100
            
            # Obtener valores de corte
            corte_hipo = self.corte_hipo_edit.text().strip() or "25"
            corte_dp = self.corte_dp_edit.text().strip() or "30"
            
            # Determinar interpretación para Hipo
            if resultado_hipo < 0:
                interpretacion_hipo = " (en OI)"
            else:
                interpretacion_hipo = " (en OD)"
            
            # Determinar interpretación para DP
            if resultado_dp < 0:
                interpretacion_dp = " (hacia izquierda)"
            else:
                interpretacion_dp = " (hacia derecha)"
            
            self.resultado_hipo_label.setText(f"Hipo = {resultado_hipo:.2f}%{interpretacion_hipo} (>= {corte_hipo}%)")
            self.resultado_dp_label.setText(f"DP = {resultado_dp:.2f}%{interpretacion_dp} (>= {corte_dp}%)")
        
    def update_results(self):
        """Método mantenido por compatibilidad - ahora llama a calculate_formulas"""
        self.calculate_formulas()
        
    def limpiar_todo(self):
        """Limpiar todos los campos y restaurar valores predeterminados"""
        self.od_44_edit.clear()
        self.oi_44_edit.clear()
        self.od_30_edit.clear()
        self.oi_30_edit.clear()
        self.corte_hipo_edit.setText("25")
        self.corte_dp_edit.setText("30")
        self.calculate_formulas()
        
    def get(self):
        """Obtener todos los datos como diccionario"""
        # Obtener valores
        od_44_val = self.get_input_value(self.od_44_edit.text())
        oi_44_val = self.get_input_value(self.oi_44_edit.text())
        od_30_val = self.get_input_value(self.od_30_edit.text())
        oi_30_val = self.get_input_value(self.oi_30_edit.text())
        
        # Calcular resultados
        denominador = oi_30_val + oi_44_val + od_30_val + od_44_val
        
        resultado_hipo = None
        resultado_dp = None
        
        if denominador != 0:
            numerador_hipo = (oi_30_val + oi_44_val) - (od_30_val + od_44_val)
            resultado_hipo = (numerador_hipo / denominador) * 100
            
            numerador_dp = (oi_30_val + od_44_val) - (od_30_val + oi_44_val)
            resultado_dp = (numerador_dp / denominador) * 100
        
        return {
            'od_44': self.od_44_edit.text(),
            'oi_44': self.oi_44_edit.text(),
            'od_30': self.od_30_edit.text(),
            'oi_30': self.oi_30_edit.text(),
            'corte_hipo': self.corte_hipo_edit.text(),
            'corte_dp': self.corte_dp_edit.text(),
            'od_44_val': od_44_val,
            'oi_44_val': oi_44_val,
            'od_30_val': od_30_val,
            'oi_30_val': oi_30_val,
            'resultado_hipo': resultado_hipo,
            'resultado_dp': resultado_dp,
            'denominador': denominador
        }
        
    def set_values(self, data):
        """Establecer valores desde un diccionario"""
        self.od_44_edit.setText(data.get('od_44', ''))
        self.oi_44_edit.setText(data.get('oi_44', ''))
        self.od_30_edit.setText(data.get('od_30', ''))
        self.oi_30_edit.setText(data.get('oi_30', ''))
        self.corte_hipo_edit.setText(data.get('corte_hipo', '25'))
        self.corte_dp_edit.setText(data.get('corte_dp', '30'))
        self.calculate_formulas()
        
    def clear_all(self):
        """Limpiar todos los valores"""
        self.od_44_edit.clear()
        self.oi_44_edit.clear()
        self.od_30_edit.clear()
        self.oi_30_edit.clear()
        self.corte_hipo_edit.setText("25")
        self.corte_dp_edit.setText("30")
        self.calculate_formulas()
        
    def get_input_value(self, text):
        """Obtener valor numérico de un texto"""
        try:
            return float(text.strip()) if text.strip() else 0.0
        except ValueError:
            return 0.0
        
    def load_saved_data(self):
        """Cargar datos guardados del mainWindow"""
        if self.main_window and hasattr(self.main_window, 'calculadora_hipo_dp_data'):
            data = self.main_window.calculadora_hipo_dp_data
            
            self.od_44_edit.setText(data.get('od_44', ''))
            self.oi_44_edit.setText(data.get('oi_44', ''))
            self.od_30_edit.setText(data.get('od_30', ''))
            self.oi_30_edit.setText(data.get('oi_30', ''))
            self.corte_hipo_edit.setText(data.get('corte_hipo', '25'))
            self.corte_dp_edit.setText(data.get('corte_dp', '30'))
        else:
            # Valores por defecto
            self.corte_hipo_edit.setText('25')
            self.corte_dp_edit.setText('30')
            
        self.calculate_formulas()
        
    def accept_and_save(self):
        """Guardar datos y cerrar ventana"""
        self.save_data()
        self.accept()
        
    def closeEvent(self, event):
        """Guardar datos al cerrar ventana"""
        self.save_data()
        super().closeEvent(event)