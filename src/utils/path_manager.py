#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIEV - Path Manager
Gestor centralizado de rutas para toda la aplicación
Resuelve automáticamente las rutas según el contexto de ejecución
"""

import os
import sys
from pathlib import Path
from typing import Union, Optional


class PathManager:
    """
    Gestor centralizado de rutas para la aplicación SIEV
    Detecta automáticamente el directorio base y resuelve todas las rutas
    """
    
    _instance: Optional['PathManager'] = None
    
    def __new__(cls):
        """Singleton pattern - una sola instancia del PathManager"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Inicializar el gestor de rutas"""
        if hasattr(self, '_initialized'):
            return
            
        self._initialized = True
        self.base_dir = self._detect_base_directory()
        self.src_dir = self.base_dir / "src"
        
        # Cache de rutas calculadas para mejor performance
        self._path_cache = {}
        
        print(f"📁 PathManager inicializado - Base: {self.base_dir}")
        
    def _detect_base_directory(self) -> Path:
        """
        Detectar el directorio base del proyecto automáticamente
        Funciona tanto desde src/ como desde el directorio raíz
        """
        # Obtener directorio del archivo actual (main.py)
        current_file = Path(__file__).resolve()
        current_dir = current_file.parent
        
        # Buscar hacia arriba hasta encontrar el directorio que contenga 'src'
        search_dir = current_dir
        max_levels = 5  # Evitar búsqueda infinita
        
        for _ in range(max_levels):
            # Si encontramos 'src' como subdirectorio, este es el base
            src_candidate = search_dir / "src"
            if src_candidate.exists() and src_candidate.is_dir():
                return search_dir
                
            # Si estamos dentro de 'src', el padre es el base
            if search_dir.name == "src":
                return search_dir.parent
                
            # Subir un nivel
            parent = search_dir.parent
            if parent == search_dir:  # Llegamos a la raíz del sistema
                break
            search_dir = parent
        
        # Fallback: usar el directorio del archivo actual
        print(f"⚠️  No se encontró estructura estándar, usando: {current_dir}")
        return current_dir
        
    def get_path(self, path_type: str, filename: str = None) -> Path:
        """
        Obtener ruta de archivo o directorio específico
        
        Args:
            path_type: Tipo de ruta ('ui', 'styles', 'icons', 'data', 'plugins', etc.)
            filename: Nombre del archivo (opcional)
            
        Returns:
            Path: Ruta completa al archivo o directorio
        """
        cache_key = f"{path_type}:{filename}"
        
        if cache_key in self._path_cache:
            return self._path_cache[cache_key]
        
        # Mapeo de tipos de ruta
        path_map = {
            # UI Files
            'ui': self.src_dir / "ui",
            'ui_components': self.src_dir / "ui" / "components",
            
            # Resources
            'resources': self.src_dir / "resources",
            'styles': self.src_dir / "resources" / "styles", 
            'icons': self.src_dir / "resources" / "icons",
            'fonts': self.src_dir / "resources" / "fonts",
            'translations': self.src_dir / "resources" / "translations",
            
            # Data directories
            'data': self.base_dir / "data",
            'patients': self.base_dir / "data" / "patients",
            'evaluations': self.base_dir / "data" / "evaluations",
            'reports': self.base_dir / "data" / "reports",
            'config': self.base_dir / "data" / "config",
            'backups': self.base_dir / "data" / "backups",
            'logs': self.base_dir / "logs",
            
            # Source directories
            'src': self.src_dir,
            'core': self.src_dir / "core",
            'utils': self.src_dir / "utils",
            'plugins': self.src_dir / "plugins",
            
            # Plugin specific directories
            'plugin_dashboard': self.src_dir / "plugins" / "dashboard",
            'plugin_patients': self.src_dir / "plugins" / "patients",
            'plugin_vng': self.src_dir / "plugins" / "vng", 
            'plugin_reports': self.src_dir / "plugins" / "reports",
            'plugin_settings': self.src_dir / "plugins" / "settings",
        }
        
        # Obtener directorio base
        base_path = path_map.get(path_type)
        if base_path is None:
            raise ValueError(f"Tipo de ruta no reconocido: {path_type}")
        
        # Si no se especifica filename, retornar directorio
        if filename is None:
            result = base_path
        else:
            result = base_path / filename
            
        # Cache del resultado
        self._path_cache[cache_key] = result
        return result
        
    def exists(self, path_type: str, filename: str = None) -> bool:
        """
        Verificar si existe un archivo o directorio
        
        Args:
            path_type: Tipo de ruta
            filename: Nombre del archivo (opcional)
            
        Returns:
            bool: True si existe
        """
        try:
            path = self.get_path(path_type, filename)
            return path.exists()
        except ValueError:
            return False
            
    def ensure_directory(self, path_type: str) -> Path:
        """
        Asegurar que un directorio existe, crearlo si no existe
        
        Args:
            path_type: Tipo de directorio
            
        Returns:
            Path: Ruta del directorio
        """
        dir_path = self.get_path(path_type)
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path
        
    def get_relative_to_base(self, path_type: str, filename: str = None) -> str:
        """
        Obtener ruta relativa al directorio base del proyecto
        
        Args:
            path_type: Tipo de ruta
            filename: Nombre del archivo (opcional)
            
        Returns:
            str: Ruta relativa como string
        """
        full_path = self.get_path(path_type, filename)
        try:
            relative = full_path.relative_to(self.base_dir)
            return str(relative)
        except ValueError:
            # Si no se puede hacer relativa, retornar ruta absoluta
            return str(full_path)
            
    def list_files(self, path_type: str, pattern: str = "*") -> list[Path]:
        """
        Listar archivos en un directorio
        
        Args:
            path_type: Tipo de directorio
            pattern: Patrón de archivos (ej: "*.ui", "*.qss")
            
        Returns:
            list[Path]: Lista de archivos encontrados
        """
        dir_path = self.get_path(path_type)
        if not dir_path.exists():
            return []
            
        return list(dir_path.glob(pattern))
        
    def get_safe_path(self, path_type: str, filename: str = None, 
                      fallback: str = None) -> Optional[Path]:
        """
        Obtener ruta de forma segura, retornando None si no existe
        
        Args:
            path_type: Tipo de ruta
            filename: Nombre del archivo (opcional)
            fallback: Ruta de fallback si no existe la principal
            
        Returns:
            Path: Ruta si existe, None si no existe
        """
        try:
            path = self.get_path(path_type, filename)
            if path.exists():
                return path
            elif fallback:
                fallback_path = Path(fallback)
                if fallback_path.exists():
                    return fallback_path
            return None
        except (ValueError, OSError):
            return None
            
    def debug_paths(self) -> dict:
        """
        Obtener información de debug de todas las rutas
        Útil para troubleshooting
        
        Returns:
            dict: Información de rutas y existencia
        """
        debug_info = {
            'base_directory': str(self.base_dir),
            'src_directory': str(self.src_dir),
            'current_working_directory': str(Path.cwd()),
            'main_file_location': str(Path(__file__).parent),
            'paths_status': {}
        }
        
        # Verificar rutas principales
        key_paths = [
            ('ui', 'main_window.ui'),
            ('styles', 'medical_theme.qss'),
            ('plugins', None),
            ('data', None),
            ('config', None)
        ]
        
        for path_type, filename in key_paths:
            try:
                path = self.get_path(path_type, filename)
                debug_info['paths_status'][f"{path_type}:{filename}"] = {
                    'path': str(path),
                    'exists': path.exists(),
                    'is_file': path.is_file() if path.exists() else False,
                    'is_dir': path.is_dir() if path.exists() else False
                }
            except Exception as e:
                debug_info['paths_status'][f"{path_type}:{filename}"] = {
                    'error': str(e)
                }
                
        return debug_info
        

# Instancia global del PathManager (Singleton)
paths = PathManager()


# Funciones de conveniencia para uso común
def get_ui_file(filename: str) -> Path:
    """Shortcut para obtener archivos .ui"""
    return paths.get_path('ui', filename)

def get_style_file(filename: str) -> Path:
    """Shortcut para obtener archivos .qss"""
    return paths.get_path('styles', filename)

def get_plugin_dir(plugin_name: str) -> Path:
    """Shortcut para obtener directorio de plugin"""
    return paths.get_path(f'plugin_{plugin_name}')

def ensure_data_dir(dir_name: str) -> Path:
    """Shortcut para asegurar directorio de datos"""
    return paths.ensure_directory(dir_name)
    
def file_exists(path_type: str, filename: str) -> bool:
    """Shortcut para verificar existencia de archivo"""
    return paths.exists(path_type, filename)