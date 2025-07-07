#!/usr/bin/env python3
"""
Script para limpiar archivos obsoletos del proyecto VNG
"""

import os
import shutil

def cleanup_project():
    """Elimina archivos obsoletos del proyecto"""
    
    # Lista de archivos a eliminar
    files_to_remove = [
        # Versiones obsoletas de VideoWidget
        'src/utils/VideoWidget.py',
        'src/utils/VideoWidget2.py',
        'src/utils/VideoWidget3.py',
        'src/utils/VideoWidget4.py',
        'src/utils/VideoWidget5.py',
        'src/utils/VideoWidget6.py',
        'src/utils/VideoWidget7.py',
        'src/utils/VideoWidget8.py',
        'src/utils/VideoWidget9.py',
        'src/utils/VideoWidget10.py',
        
        # Archivos experimentales
        'src/utils/SimpleTracker.py',
        'src/utils/VideoHandler.py',
        'src/utils/helpers.py',
        'src/utils/camera_config.py',
        
        # Sistemas de cámara específicos (eliminar según tu OS)
        # 'src/utils/V4L2Camera.py',      # Descomenta si no usas Linux
        # 'src/utils/WindowsCamera.py',   # Descomenta si no usas Windows
        
        # Módulos avanzados no utilizados (opcional)
        # 'src/utils/DetectorNistagmo.py',   # Descomenta si no lo usas
        # 'src/utils/EyeDataProcessor.py',   # Descomenta si no lo usas
        
        # Sistema de gráficos legacy (solo si usas el nuevo sistema modular)
        # 'src/utils/GraphHandler.py',       # Descomenta si usas graphing/
    ]
    
    removed_files = []
    not_found_files = []
    
    print("🧹 Iniciando limpieza del proyecto...")
    print("=" * 50)
    
    for file_path in files_to_remove:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                removed_files.append(file_path)
                print(f"✅ Eliminado: {file_path}")
            except Exception as e:
                print(f"❌ Error eliminando {file_path}: {e}")
        else:
            not_found_files.append(file_path)
            print(f"⚠️  No encontrado: {file_path}")
    
    print("=" * 50)
    print(f"✅ Archivos eliminados: {len(removed_files)}")
    print(f"⚠️  Archivos no encontrados: {len(not_found_files)}")
    
    # Mostrar estructura final recomendada
    print("\n📁 Estructura final recomendada:")
    print("""
src/
├── config/
│   ├── __init__.py
│   └── config.json
├── models/
│   ├── __init__.py
│   └── data_models.py
├── ui/
│   ├── main_ui.py
│   └── main_window.py
├── utils/
│   ├── __init__.py
│   ├── VideoWidget11.py        ← PRINCIPAL
│   ├── SerialHandler.py
│   ├── RecordHandler.py
│   ├── V4L2Camera.py          ← Solo Linux
│   ├── WindowsCamera.py       ← Solo Windows
│   └── graphing/              ← Sistema modular
│       ├── __init__.py
│       ├── base_plot.py
│       ├── blink_detector.py
│       ├── data_processor.py
│       ├── triple_plot_widget.py
│       └── visual_manager.py
    """)
    
    print("\n🔧 Después de la limpieza, actualiza las importaciones:")
    print("   - En main_window.py: from utils.VideoWidget11 import VideoWidget")
    print("   - En main_window.py: from utils.graphing import TriplePlotWidget")
    
    print("\n✨ ¡Limpieza completada!")

def verify_essential_files():
    """Verifica que los archivos esenciales estén presentes"""
    essential_files = [
        'src/config/config.json',
        'src/ui/main_ui.py',
        'src/ui/main_window.py',
        'src/utils/VideoWidget11.py',
        'src/utils/SerialHandler.py',
        'src/utils/RecordHandler.py',
        'src/utils/graphing/triple_plot_widget.py',
    ]
    
    print("\n🔍 Verificando archivos esenciales...")
    missing_files = []
    
    for file_path in essential_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
            print(f"❌ FALTA: {file_path}")
        else:
            print(f"✅ OK: {file_path}")
    
    if missing_files:
        print(f"\n⚠️  ADVERTENCIA: Faltan {len(missing_files)} archivos esenciales!")
        return False
    else:
        print("\n✅ Todos los archivos esenciales están presentes")
        return True

if __name__ == "__main__":
    # Verificar que estamos en el directorio correcto
    if not os.path.exists('src'):
        print("❌ Error: No se encontró el directorio 'src'")
        print("   Ejecuta este script desde la raíz del proyecto")
        exit(1)
    
    # Verificar archivos esenciales antes de limpiar
    print("🔍 Verificación previa...")
    if not verify_essential_files():
        response = input("\n⚠️  ¿Continuar con la limpieza? (y/N): ")
        if response.lower() != 'y':
            print("Limpieza cancelada")
            exit(0)
    
    # Ejecutar limpieza
    cleanup_project()
    
    # Verificar nuevamente después de la limpieza
    verify_essential_files()
