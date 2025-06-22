#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIEV - Sistema Integrado de Evaluación Vestibular
Main Application Entry Point

Arquitectura: PySide6 + Plugin System
Fase 1: Foundation Sólida
"""
import sys
import os
from pathlib import Path

# Agregar src/ al Python path
src_dir = Path(__file__).parent
sys.path.insert(0, str(src_dir))

import traceback
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt, QDir
from PySide6.QtGui import QIcon


# Importar componentes core
from utils.path_manager import paths  # ← AGREGAR ESTA LÍNEA
from core.window_handler import WindowHandler
from utils.theme_manager import ThemeManager


class SIEVApplication:
    """
    Clase principal de la aplicación SIEV
    Maneja inicialización, configuración y ciclo de vida
    """
    
    def __init__(self):
        """Inicializar aplicación"""
        self.app = None
        self.window_handler = None
        self.theme_manager = None
        
    def setup_directories(self):
        """Crear directorios necesarios si no existen"""
        paths.ensure_directory('data')
        paths.ensure_directory('patients')
        paths.ensure_directory('evaluations') 
        paths.ensure_directory('reports')
        paths.ensure_directory('config')
        paths.ensure_directory('backups')
        paths.ensure_directory('logs')
                
    def setup_application(self):
        """Configurar QApplication con propiedades básicas"""
        # Configurar atributos de aplicación
        QApplication.setApplicationName("SIEV")
        QApplication.setApplicationVersion("1.0.0")
        QApplication.setOrganizationName("Medical Systems")
        QApplication.setOrganizationDomain("siev.medical")
        
        # Crear aplicación
        self.app = QApplication(sys.argv)
        
        # Configurar icono de aplicación si existe
        icon_path = paths.get_path('icons', 'app_icon.png')
        if os.path.exists(icon_path):
            self.app.setWindowIcon(QIcon(icon_path))
            
        # Configurar estilo base
        self.app.setStyle("Fusion")  # Estilo moderno base
        
    def setup_theme(self):
        """Inicializar sistema de temas"""
        try:
            self.theme_manager = ThemeManager()
            # Cargar tema por defecto (medical_theme)
            self.theme_manager.load_theme("medical")
            self.theme_manager.apply_theme(self.app)
            print("✅ Tema médico cargado correctamente")
        except Exception as e:
            print(f"⚠️  Error cargando tema: {e}")
            print("📄 Continuando con tema por defecto")
            
    def setup_window(self):
        """Inicializar ventana principal"""
        try:
            self.window_handler = WindowHandler()
            self.window_handler.setup_main_window()
            print("✅ Ventana principal inicializada")
        except Exception as e:
            print(f"❌ Error inicializando ventana: {e}")
            raise
            
    def show_error_dialog(self, title, message, details=None):
        """Mostrar diálogo de error profesional"""
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle(f"SIEV - {title}")
        msg_box.setText(message)
        
        if details:
            msg_box.setDetailedText(details)
            
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec()
        
    def run(self):
        """Ejecutar aplicación principal"""
        try:
            print("🏥 Iniciando SIEV - Sistema Integrado de Evaluación Vestibular")
            print("=" * 60)
            
            # Paso 1: Crear directorios
            print("📁 Configurando directorios...")
            self.setup_directories()
            
            # Paso 2: Configurar QApplication
            print("⚙️  Configurando aplicación...")
            self.setup_application()
            
            # Paso 3: Cargar tema
            print("🎨 Cargando tema médico...")
            self.setup_theme()
            
            # Paso 4: Inicializar ventana
            print("🏠 Inicializando ventana principal...")
            self.setup_window()
            
            # Paso 5: Mostrar ventana
            print("🚀 Mostrando interfaz...")
            self.window_handler.show_window()
            
            print("=" * 60)
            print("✅ SIEV iniciado correctamente")
            print("💡 Presiona Ctrl+C para cerrar")
            
            # Ejecutar loop principal
            return self.app.exec()
            
        except ImportError as e:
            error_msg = f"Error importando módulos requeridos:\n{str(e)}"
            print(f"❌ {error_msg}")
            
            if self.app:
                self.show_error_dialog(
                    "Error de Importación",
                    "No se pudieron cargar los módulos necesarios.",
                    error_msg
                )
            return 1
            
        except FileNotFoundError as e:
            error_msg = f"Archivo requerido no encontrado:\n{str(e)}"
            print(f"❌ {error_msg}")
            
            if self.app:
                self.show_error_dialog(
                    "Archivo No Encontrado", 
                    "No se pudo encontrar un archivo requerido.",
                    error_msg
                )
            return 1
            
        except Exception as e:
            error_msg = f"Error inesperado:\n{str(e)}\n\n{traceback.format_exc()}"
            print(f"❌ {error_msg}")
            
            if self.app:
                self.show_error_dialog(
                    "Error Crítico",
                    "Ha ocurrido un error inesperado.",
                    error_msg
                )
            return 1
            
    def cleanup(self):
        """Limpiar recursos al cerrar"""
        try:
            if self.window_handler:
                self.window_handler.cleanup()
            print("🧹 Recursos limpiados correctamente")
        except Exception as e:
            print(f"⚠️  Error en cleanup: {e}")


def main():
    """
    Punto de entrada principal
    """
    # Configurar encoding para Windows
    if sys.platform.startswith('win'):
        os.environ['PYTHONIOENCODING'] = 'utf-8'
    
    # Crear y ejecutar aplicación
    siev_app = SIEVApplication()
    
    try:
        exit_code = siev_app.run()
    except KeyboardInterrupt:
        print("\n🛑 Aplicación interrumpida por usuario")
        exit_code = 0
    finally:
        siev_app.cleanup()
    
    return exit_code


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)