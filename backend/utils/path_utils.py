import os
import sys


def get_src_path():
    """Obtener el directorio src de la aplicación"""
    if getattr(sys, "frozen", False):
        # Si es un ejecutable empaquetado
        base_path = os.path.dirname(sys.executable)
        return os.path.join(base_path, "src")
    else:
        # Si es desarrollo, obtener el directorio src
        current_file = os.path.abspath(__file__)
        utils_dir = os.path.dirname(current_file)
        return os.path.dirname(utils_dir)


def get_models_path():
    """Obtener el directorio models dentro de src"""
    src_path = get_src_path()
    return os.path.join(src_path, "models")


def get_model_file_path(model_filename):
    """
    Obtener la ruta completa de un archivo de modelo
    
    Args:
        model_filename: Nombre del archivo del modelo (ej: 'best_color.pt')
    
    Returns:
        Ruta completa al archivo del modelo
    """
    models_path = get_models_path()
    return os.path.join(models_path, model_filename)