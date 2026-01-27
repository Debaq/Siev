#!/usr/bin/env python3
"""
Script para convertir modelo YOLO de PyTorch (.pt) a ONNX (.onnx)

Uso:
    python convert_to_onnx.py [--model MODEL_NAME] [--imgsz SIZE] [--opset OPSET]

Ejemplo:
    python convert_to_onnx.py --model siev_vng_r01.pt --imgsz 640 --opset 14
"""

import argparse
import os
import sys

# Agregar el directorio padre al path para importar módulos del backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ultralytics import YOLO
from utils.path_utils import get_models_path, get_model_file_path


def convert_to_onnx(
    model_name: str = "siev_vng_r01.pt",
    imgsz: int = 640,
    opset: int = 12,
    simplify: bool = True,
    half: bool = False,
):
    """
    Convierte un modelo YOLO de PyTorch a ONNX.

    Args:
        model_name: Nombre del archivo del modelo .pt
        imgsz: Tamaño de imagen para la exportación
        opset: Versión de ONNX opset (12-17 recomendado)
        simplify: Simplificar el modelo ONNX
        half: Usar FP16 (requiere GPU compatible)
    """
    # Obtener ruta del modelo
    model_path = get_model_file_path(model_name)

    if not os.path.exists(model_path):
        print(f"Error: No se encontró el modelo en {model_path}")
        sys.exit(1)

    print(f"Cargando modelo: {model_path}")
    model = YOLO(model_path)

    # Mostrar información del modelo
    print("\nInformación del modelo:")
    model.info()

    print(f"\nExportando a ONNX con:")
    print(f"  - imgsz: {imgsz}")
    print(f"  - opset: {opset}")
    print(f"  - simplify: {simplify}")
    print(f"  - half (FP16): {half}")

    # Exportar a ONNX
    output_path = model.export(
        format="onnx",
        imgsz=imgsz,
        opset=opset,
        simplify=simplify,
        half=half,
        dynamic=False,  # Tamaño fijo para mejor rendimiento
    )

    print(f"\nModelo exportado exitosamente a: {output_path}")

    # Verificar tamaño del archivo
    if os.path.exists(output_path):
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"Tamaño del archivo ONNX: {size_mb:.2f} MB")

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Convertir modelo YOLO de PyTorch a ONNX"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="siev_vng_r01.pt",
        help="Nombre del archivo del modelo .pt (default: siev_vng_r01.pt)",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=640,
        help="Tamaño de imagen para exportación (default: 640)",
    )
    parser.add_argument(
        "--opset",
        type=int,
        default=12,
        help="Versión de ONNX opset (default: 12)",
    )
    parser.add_argument(
        "--simplify",
        action="store_true",
        default=True,
        help="Simplificar modelo ONNX (default: True)",
    )
    parser.add_argument(
        "--half",
        action="store_true",
        default=False,
        help="Usar FP16 - requiere GPU compatible (default: False)",
    )

    args = parser.parse_args()

    convert_to_onnx(
        model_name=args.model,
        imgsz=args.imgsz,
        opset=args.opset,
        simplify=args.simplify,
        half=args.half,
    )


if __name__ == "__main__":
    main()
