"""
Configuraciones de estilo profesionales para gráficos

Proporciona múltiples opciones de estilo para los gráficos de pyqtgraph
"""

# ====== ESTILOS PROFESIONALES ======

PROFESSIONAL_LIGHT = {
    'name': 'Profesional Claro',
    'background': '#FAFAFA',
    'grid_alpha': 0.3,
    'grid_color': 150,
    'axis_color': '#424242',
    'axis_width': 1.5,
    'text_color': '#212121',
    'label_size': '11pt',
    'label_weight': 'bold',
    'line_width': 2.5,
    'colors': {
        'left_eye': (33, 150, 243),    # Azul Material #2196F3
        'right_eye': (244, 67, 54),    # Rojo Material #F44336
        'vline': '#F44336',
        'caloric': '#F44336'
    }
}

PROFESSIONAL_DARK = {
    'name': 'Profesional Oscuro',
    'background': '#1E1E1E',
    'grid_alpha': 0.2,
    'grid_color': 80,
    'axis_color': '#E0E0E0',
    'axis_width': 1.5,
    'text_color': '#FFFFFF',
    'label_size': '11pt',
    'label_weight': 'bold',
    'line_width': 2.5,
    'colors': {
        'left_eye': (66, 165, 245),    # Azul claro #42A5F5
        'right_eye': (239, 83, 80),    # Rojo claro #EF5350
        'vline': '#EF5350',
        'caloric': '#EF5350'
    }
}

HIGH_CONTRAST = {
    'name': 'Alto Contraste',
    'background': '#FFFFFF',
    'grid_alpha': 0.5,
    'grid_color': 200,
    'axis_color': '#000000',
    'axis_width': 2,
    'text_color': '#000000',
    'label_size': '12pt',
    'label_weight': 'bold',
    'line_width': 3,
    'colors': {
        'left_eye': (0, 0, 255),       # Azul puro
        'right_eye': (255, 0, 0),      # Rojo puro
        'vline': '#FF0000',
        'caloric': '#FF0000'
    }
}

MEDICAL_BLUE = {
    'name': 'Médico Azul',
    'background': '#F0F4F8',
    'grid_alpha': 0.25,
    'grid_color': 160,
    'axis_color': '#1565C0',
    'axis_width': 1.5,
    'text_color': '#0D47A1',
    'label_size': '11pt',
    'label_weight': 'bold',
    'line_width': 2,
    'colors': {
        'left_eye': (21, 101, 192),    # Azul médico #1565C0
        'right_eye': (244, 67, 54),    # Rojo contraste #F44336
        'vline': '#F44336',
        'caloric': '#1565C0'
    }
}

COLORBLIND_FRIENDLY = {
    'name': 'Amigable Daltónicos',
    'background': '#FAFAFA',
    'grid_alpha': 0.3,
    'grid_color': 150,
    'axis_color': '#424242',
    'axis_width': 1.5,
    'text_color': '#212121',
    'label_size': '11pt',
    'label_weight': 'bold',
    'line_width': 2.5,
    'colors': {
        'left_eye': (0, 114, 178),     # Azul #0072B2
        'right_eye': (230, 159, 0),    # Naranja #E69F00
        'vline': '#E69F00',
        'caloric': '#0072B2'
    }
}

MINIMALIST = {
    'name': 'Minimalista',
    'background': '#FFFFFF',
    'grid_alpha': 0.15,
    'grid_color': 120,
    'axis_color': '#CCCCCC',
    'axis_width': 1,
    'text_color': '#666666',
    'label_size': '10pt',
    'label_weight': 'normal',
    'line_width': 2,
    'colors': {
        'left_eye': (100, 100, 100),   # Gris
        'right_eye': (50, 50, 50),     # Gris oscuro
        'vline': '#999999',
        'caloric': '#666666'
    }
}

# Diccionario de estilos disponibles
AVAILABLE_STYLES = {
    'professional_light': PROFESSIONAL_LIGHT,
    'professional_dark': PROFESSIONAL_DARK,
    'high_contrast': HIGH_CONTRAST,
    'medical_blue': MEDICAL_BLUE,
    'colorblind_friendly': COLORBLIND_FRIENDLY,
    'minimalist': MINIMALIST
}

# Estilo por defecto
DEFAULT_STYLE = 'professional_light'


def get_style(style_name: str = None):
    """
    Obtiene una configuración de estilo.

    Args:
        style_name: Nombre del estilo. Si es None, retorna el estilo por defecto.

    Returns:
        dict: Configuración de estilo
    """
    if style_name is None:
        style_name = DEFAULT_STYLE

    return AVAILABLE_STYLES.get(style_name, PROFESSIONAL_LIGHT).copy()


def get_available_style_names():
    """
    Retorna lista de nombres de estilos disponibles.

    Returns:
        list: Lista de nombres de estilos
    """
    return list(AVAILABLE_STYLES.keys())


def get_style_display_names():
    """
    Retorna diccionario de nombres internos a nombres para mostrar.

    Returns:
        dict: Mapeo de nombre interno -> nombre visible
    """
    return {
        key: style['name']
        for key, style in AVAILABLE_STYLES.items()
    }


# ====== COLORES PREDEFINIDOS PARA FASES CALÓRICAS ======

CALORIC_PHASES_COLORS = {
    'professional': {
        'irrigation': (33, 150, 243, 60),    # Azul
        'torok': (255, 152, 0, 60),          # Naranja
        'fixation': (76, 175, 80, 60)        # Verde
    },
    'high_contrast': {
        'irrigation': (0, 0, 255, 80),       # Azul puro
        'torok': (255, 165, 0, 80),          # Naranja puro
        'fixation': (0, 255, 0, 80)          # Verde puro
    },
    'medical': {
        'irrigation': (21, 101, 192, 50),    # Azul médico
        'torok': (251, 192, 45, 50),         # Amarillo médico
        'fixation': (67, 160, 71, 50)        # Verde médico
    }
}


def get_caloric_phase_colors(style='professional'):
    """
    Obtiene colores para fases calóricas según estilo.

    Args:
        style: Estilo de colores ('professional', 'high_contrast', 'medical')

    Returns:
        dict: Colores para cada fase
    """
    return CALORIC_PHASES_COLORS.get(style, CALORIC_PHASES_COLORS['professional']).copy()
