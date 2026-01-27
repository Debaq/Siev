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


def get_model_file_path_prefer_onnx(model_filename):
    """
    Obtener la ruta completa de un archivo de modelo, priorizando ONNX si existe.

    Si el modelo solicitado es .pt, busca primero la versión .onnx.
    Si existe el .onnx, lo retorna. Si no, retorna el .pt original.

    Args:
        model_filename: Nombre del archivo del modelo (ej: 'model.pt')

    Returns:
        tuple: (ruta_completa, formato) donde formato es 'onnx' o 'pt'
    """
    models_path = get_models_path()

    # Si el archivo es .pt, buscar versión .onnx primero
    if model_filename.endswith('.pt'):
        onnx_filename = model_filename.replace('.pt', '.onnx')
        onnx_path = os.path.join(models_path, onnx_filename)

        if os.path.exists(onnx_path):
            return onnx_path, 'onnx'

    # Retornar el archivo original
    return os.path.join(models_path, model_filename), 'pt'