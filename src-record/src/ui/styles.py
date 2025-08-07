def get_dark_theme():
    """Retorna el estilo del tema oscuro principal"""
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
    """

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
    """

def get_button_style(color):
    """Estilo para QPushButton con color específico"""
    return f"""
        QPushButton {{
            background-color: {color};
            border: none;
            border-radius: 8px;
            color: white;
            font-weight: bold;
            font-size: 14px;
            padding: 15px;
        }}
        QPushButton:hover {{
            background-color: {color}cc;
        }}
        QPushButton:pressed {{
            background-color: {color}88;
        }}
    """

def get_status_style(color):
    """Estilo para etiquetas de estado"""
    return f"""
        QLabel {{
            color: {color}; 
            font-weight: bold; 
            font-size: 14px;
            padding: 10px;
            border: 1px solid {color};
            border-radius: 6px;
            background-color: rgba({color[1:3]}, {color[3:5]}, {color[5:7]}, 0.1);
        }}
    """

def get_camera_label_style():
    """Estilo para el label de la cámara"""
    return """
        QLabel {
            border: 2px solid #555;
            border-radius: 8px;
            background-color: #2d2d2d;
            color: white;
        }
    """