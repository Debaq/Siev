#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIEV - Theme Manager
Manejo básico de temas y estilos QSS
"""

import os
from .path_manager import paths, get_style_file


class ThemeManager:
    """
    Maneja la carga y aplicación de temas QSS
    Funcionalidad básica para estilos de la aplicación
    """
    
    def __init__(self):
        """Inicializar manager de temas"""
        self.current_theme = None
        self.themes_path = paths.get_path('styles')  # ← CAMBIAR ESTA LÍNEA
        self.loaded_style = ""


    def load_theme(self, theme_name):
        """
        Cargar tema específico desde archivo QSS
        
        Args:
            theme_name (str): Nombre del tema ('medical', 'dark', 'light')
        """
        try:
            # Construir ruta del archivo de tema usando PathManager
            theme_file = f"{theme_name}_theme.qss"
            theme_path = get_style_file(theme_file)
            
            # Verificar que el archivo existe
            if not theme_path.exists():
                print(f"⚠️  Archivo de tema no encontrado: {theme_path}")
                self._load_fallback_style()
                return
                
            # Leer archivo QSS
            with open(theme_path, 'r', encoding='utf-8') as file:
                self.loaded_style = file.read()
                
            self.current_theme = theme_name
            print(f"✅ Tema '{theme_name}' cargado desde {theme_path}")
            
        except Exception as e:
            print(f"❌ Error cargando tema '{theme_name}': {e}")
            self._load_fallback_style()

            
    def _load_fallback_style(self):
        """Cargar estilo básico como fallback"""
        self.loaded_style = """
        /* SIEV - Estilo Fallback Básico */
        QMainWindow {
            background-color: #f8f9fb;
            color: #374151;
        }
        
        QPushButton {
            background-color: #6B46C1;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: 500;
        }
        
        QPushButton:hover {
            background-color: #553C9A;
        }
        
        QPushButton:pressed {
            background-color: #4C1D95;
        }
        
        QLineEdit, QTextEdit {
            background-color: white;
            border: 1px solid #D1D5DB;
            border-radius: 6px;
            padding: 8px;
        }
        
        QLineEdit:focus, QTextEdit:focus {
            border-color: #6B46C1;
        }
        """
        self.current_theme = "fallback"
        print("📄 Estilo fallback básico cargado")
        
    def apply_theme(self, app):
        """
        Aplicar tema cargado a la aplicación
        
        Args:
            app (QApplication): Instancia de la aplicación
        """
        try:
            if self.loaded_style:
                app.setStyleSheet(self.loaded_style)
                print(f"🎨 Tema aplicado: {self.current_theme}")
            else:
                print("⚠️  No hay estilo cargado para aplicar")
                
        except Exception as e:
            print(f"❌ Error aplicando tema: {e}")
            
    def get_current_theme(self):
        """Obtener nombre del tema actual"""
        return self.current_theme
        
    def get_available_themes(self):
        """Obtener lista de temas disponibles"""
        themes = []
        
        themes_dir = paths.get_path('styles')
        if themes_dir.exists():
            for file in themes_dir.iterdir():
                if file.name.endswith('_theme.qss'):
                    theme_name = file.name.replace('_theme.qss', '')
                    themes.append(theme_name)
                    
        return themes if themes else ['fallback']