"""
Estilos Qt6 Dark Theme - Sistema Médico
Estilos reutilizables para aplicaciones Qt6 con tema oscuro profesional
"""

class Qt6DarkStyles:
    """Clase con todos los estilos del tema oscuro para Qt6"""
    
    # COLORES PRINCIPALES
    COLORS = {
        'primary_bg': '#1a1a1a',           # Fondo principal
        'secondary_bg': '#2d2d2d',         # Fondo secundario
        'accent_blue': '#4a9eff',          # Azul principal
        'success_green': '#4aff6b',        # Verde éxito
        'warning_orange': '#ff8c00',       # Naranja advertencia
        'danger_red': '#ff4444',           # Rojo peligro
        'text_white': 'white',             # Texto principal
        'border_gray': '#555',             # Bordes
        'hover_gray': '#666',              # Hover estados
    }
    
    @staticmethod
    def get_main_window_style():
        """Estilo principal para QMainWindow"""
        return """
            QMainWindow {
                background-color: #1a1a1a;
                color: white;
            }
            QWidget {
                background-color: #1a1a1a;
                color: white;
            }
        """
    
    @staticmethod
    def get_group_style():
        """Estilo para QGroupBox"""
        return """
            QGroupBox {
                font-size: 12px;
                font-weight: bold;
                color: #4a9eff;
                border: 2px solid #555;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: rgba(45, 45, 45, 0.3);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """
    
    @staticmethod
    def get_input_style():
        """Estilo para QLineEdit"""
        return """
            QLineEdit {
                background-color: #2d2d2d;
                border: 2px solid #555;
                border-radius: 6px;
                padding: 10px;
                color: white;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #4a9eff;
            }
            QLineEdit:disabled {
                background-color: #1a1a1a;
                color: #888;
                border-color: #333;
            }
        """
    
    @staticmethod
    def get_combo_style():
        """Estilo para QComboBox"""
        return """
            QComboBox {
                background-color: #2d2d2d;
                border: 2px solid #555;
                border-radius: 6px;
                padding: 10px;
                color: white;
                font-size: 12px;
                min-width: 6em;
            }
            QComboBox:focus {
                border-color: #4a9eff;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 8px solid white;
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                border: 1px solid #555;
                selection-background-color: #4a9eff;
                color: white;
                padding: 5px;
            }
            QComboBox:disabled {
                background-color: #1a1a1a;
                color: #888;
                border-color: #333;
            }
        """
    
    @staticmethod
    def get_button_style(color="#4a9eff", hover_alpha="cc", pressed_alpha="88"):
        """
        Estilo para QPushButton
        Args:
            color: Color principal del botón (hex)
            hover_alpha: Transparencia para hover (hex)
            pressed_alpha: Transparencia para pressed (hex)
        """
        return f"""
            QPushButton {{
                background-color: {color};
                border: none;
                border-radius: 8px;
                color: white;
                font-weight: bold;
                font-size: 14px;
                padding: 15px;
                min-height: 25px;
            }}
            QPushButton:hover {{
                background-color: {color}{hover_alpha};
            }}
            QPushButton:pressed {{
                background-color: {color}{pressed_alpha};
            }}
            QPushButton:disabled {{
                background-color: #333;
                color: #888;
            }}
        """
    
    @staticmethod
    def get_small_button_style():
        """Estilo para botones pequeños"""
        return """
            QPushButton {
                background-color: #555;
                border: 1px solid #777;
                border-radius: 4px;
                color: white;
                font-size: 11px;
                padding: 8px 12px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #666;
            }
            QPushButton:pressed {
                background-color: #444;
            }
            QPushButton:disabled {
                background-color: #333;
                color: #888;
                border-color: #444;
            }
        """
    
    @staticmethod
    def get_status_label_style(color="#4aff6b"):
        """Estilo para labels de estado"""
        return f"""
            QLabel {{
                color: {color}; 
                font-weight: bold; 
                font-size: 14px;
                padding: 10px;
                border: 1px solid {color};
                border-radius: 6px;
                background-color: rgba({Qt6DarkStyles._hex_to_rgba(color)}, 0.1);
            }}
        """
    
    @staticmethod
    def get_table_style():
        """Estilo para QTableWidget"""
        return """
            QTableWidget {
                background-color: #2d2d2d;
                border: 1px solid #555;
                gridline-color: #555;
                color: white;
                selection-background-color: #4a9eff;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #555;
            }
            QTableWidget::item:selected {
                background-color: #4a9eff;
                color: white;
            }
            QTableWidget::item:hover {
                background-color: rgba(74, 158, 255, 0.3);
            }
            QHeaderView::section {
                background-color: #1a1a1a;
                color: white;
                font-weight: bold;
                border: 1px solid #555;
                padding: 8px;
            }
            QHeaderView::section:hover {
                background-color: #333;
            }
        """
    
    @staticmethod
    def get_text_edit_style():
        """Estilo para QTextEdit"""
        return """
            QTextEdit {
                background-color: #2d2d2d;
                border: 2px solid #555;
                border-radius: 6px;
                padding: 10px;
                color: white;
                font-size: 12px;
            }
            QTextEdit:focus {
                border-color: #4a9eff;
            }
        """
    
    @staticmethod
    def get_scroll_bar_style():
        """Estilo para barras de desplazamiento"""
        return """
            QScrollBar:vertical {
                border: none;
                background: #2d2d2d;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #555;
                min-height: 20px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover {
                background: #666;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
            QScrollBar:horizontal {
                border: none;
                background: #2d2d2d;
                height: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background: #555;
                min-width: 20px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #666;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                border: none;
                background: none;
            }
        """
    
    @staticmethod
    def get_checkbox_style():
        """Estilo para QCheckBox"""
        return """
            QCheckBox {
                color: white;
                font-size: 12px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #555;
                border-radius: 3px;
                background-color: #2d2d2d;
            }
            QCheckBox::indicator:hover {
                border-color: #4a9eff;
            }
            QCheckBox::indicator:checked {
                background-color: #4a9eff;
                border-color: #4a9eff;
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iMTIiIHZpZXdCb3g9IjAgMCAxMiAxMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEwIDNMNC41IDguNUwyIDYiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+Cjwvc3ZnPgo=);
            }
        """
    
    @staticmethod
    def get_radio_button_style():
        """Estilo para QRadioButton"""
        return """
            QRadioButton {
                color: white;
                font-size: 12px;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #555;
                border-radius: 9px;
                background-color: #2d2d2d;
            }
            QRadioButton::indicator:hover {
                border-color: #4a9eff;
            }
            QRadioButton::indicator:checked {
                background-color: #4a9eff;
                border-color: #4a9eff;
            }
            QRadioButton::indicator:checked::after {
                content: '';
                width: 6px;
                height: 6px;
                border-radius: 3px;
                background-color: white;
                position: absolute;
                top: 6px;
                left: 6px;
            }
        """
    
    @staticmethod
    def get_slider_style():
        """Estilo para QSlider"""
        return """
            QSlider::groove:horizontal {
                border: 1px solid #555;
                height: 6px;
                background: #2d2d2d;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #4a9eff;
                border: 1px solid #4a9eff;
                width: 18px;
                height: 18px;
                margin: -7px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: #6bb3ff;
                border-color: #6bb3ff;
            }
            QSlider::sub-page:horizontal {
                background: #4a9eff;
                border-radius: 3px;
            }
        """
    
    @staticmethod
    def get_progress_bar_style():
        """Estilo para QProgressBar"""
        return """
            QProgressBar {
                border: 2px solid #555;
                border-radius: 8px;
                text-align: center;
                font-weight: bold;
                font-size: 12px;
                color: white;
                background-color: #2d2d2d;
            }
            QProgressBar::chunk {
                background-color: #4a9eff;
                border-radius: 6px;
            }
        """
    
    @staticmethod
    def get_menu_style():
        """Estilo para menús"""
        return """
            QMenuBar {
                background-color: #2d2d2d;
                color: white;
                border-bottom: 1px solid #555;
            }
            QMenuBar::item {
                padding: 8px 12px;
                background: transparent;
            }
            QMenuBar::item:selected {
                background-color: #4a9eff;
            }
            QMenu {
                background-color: #2d2d2d;
                border: 1px solid #555;
                color: white;
            }
            QMenu::item {
                padding: 8px 25px;
            }
            QMenu::item:selected {
                background-color: #4a9eff;
            }
        """
    
    @staticmethod
    def get_tab_widget_style():
        """Estilo para QTabWidget"""
        return """
            QTabWidget::pane {
                border: 1px solid #555;
                background-color: #1a1a1a;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: white;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QTabBar::tab:selected {
                background-color: #4a9eff;
            }
            QTabBar::tab:hover {
                background-color: #555;
            }
        """
    
    @staticmethod
    def _hex_to_rgba(hex_color):
        """Convierte color hex a valores RGB para rgba()"""
        hex_color = hex_color.lstrip('#')
        return f"{int(hex_color[0:2], 16)}, {int(hex_color[2:4], 16)}, {int(hex_color[4:6], 16)}"
    
    # ESTILOS PREDEFINIDOS PARA COMPONENTES ESPECÍFICOS
    
    @staticmethod
    def get_success_button():
        """Botón verde de éxito"""
        return Qt6DarkStyles.get_button_style("#4aff6b")
    
    @staticmethod
    def get_danger_button():
        """Botón rojo de peligro"""
        return Qt6DarkStyles.get_button_style("#ff4444")
    
    @staticmethod
    def get_warning_button():
        """Botón naranja de advertencia"""
        return Qt6DarkStyles.get_button_style("#ff8c00")
    
    @staticmethod
    def get_info_button():
        """Botón azul informativo"""
        return Qt6DarkStyles.get_button_style("#4a9eff")
    
    @staticmethod
    def get_camera_frame_style():
        """Estilo específico para marcos de cámara"""
        return """
            QLabel {
                border: 2px solid #555;
                border-radius: 8px;
                background-color: #2d2d2d;
                color: white;
                font-size: 14px;
                text-align: center;
            }
        """

# EJEMPLO DE USO EN UNA APLICACIÓN
class ExampleApp:
    """Ejemplo de cómo usar los estilos"""
    
    def setup_styles(self, main_window):
        """Aplicar estilos a la aplicación"""
        styles = Qt6DarkStyles()
        
        # Estilo principal
        main_window.setStyleSheet(styles.get_main_window_style())
        
        # Aplicar estilos a componentes específicos
        # self.button.setStyleSheet(styles.get_success_button())
        # self.input_field.setStyleSheet(styles.get_input_style())
        # self.combo_box.setStyleSheet(styles.get_combo_style())
        # self.group_box.setStyleSheet(styles.get_group_style())
        
    def apply_all_styles(self, app):
        """Aplica todos los estilos globalmente"""
        styles = Qt6DarkStyles()
        
        global_style = f"""
            {styles.get_main_window_style()}
            {styles.get_scroll_bar_style()}
            {styles.get_menu_style()}
        """
        
        app.setStyleSheet(global_style)

"""
CÓMO USAR:

1. Importa la clase:
   from qt6_styles import Qt6DarkStyles

2. Aplica estilos individuales:
   styles = Qt6DarkStyles()
   button.setStyleSheet(styles.get_success_button())
   input_field.setStyleSheet(styles.get_input_style())

3. Aplica estilo completo a la ventana:
   main_window.setStyleSheet(styles.get_main_window_style())

4. Colores personalizados:
   custom_button = styles.get_button_style("#ff6b4a")
   
5. Estado específico:
   status_label.setStyleSheet(styles.get_status_label_style("#4aff6b"))
"""
