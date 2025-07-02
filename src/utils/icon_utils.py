#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Icon utilities - Sistema simplificado con PySide6 y SVG con control de colores
"""

import os
import requests
import threading
import time
from typing import Optional, Dict, Any
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtWidgets import QApplication


class IconManager:
    """Gestor de iconos SVG con PySide6 y control de colores"""
    
    def __init__(self, cache_dir="assets/icons"):
        self.cache_dir = cache_dir
        self.icons_cache = {}  # Cache en memoria
        self.downloading = set()
        self.failed_icons = set()
        
        # Crear directorio de cache si no existe
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Iconos de la aplicación
        self.app_icons = {
            "file-text": "Archivos",
            "search": "Buscar",
            "camera": "Cámara", 
            "settings": "Configuración",
            "save": "Guardar",
            "folder-open": "Abrir",
            "eye": "Vista previa",
            "download": "Descargar",
            "upload": "Cargar",
            "circle-check": "Completado",
            "circle-x": "Error",
            "triangle-alert": "Advertencia",
            "info": "Información",
            "rotate-cw": "Rotar",
            "play": "Reproducir",
            "pause": "Pausar",
            "stop": "Detener"
        }
    
    def get_svg_path(self, name: str) -> str:
        """Obtener ruta del archivo SVG"""
        return os.path.join(self.cache_dir, f"{name}.svg")
    
    def svg_exists(self, name: str) -> bool:
        """Verificar si el SVG existe localmente"""
        return os.path.exists(self.get_svg_path(name))
    
    def download_svg_from_lucide(self, name: str) -> bool:
        """Descargar SVG desde GitHub de Lucide"""
        try:
            url = f"https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/{name}.svg"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            svg_content = response.text
            
            # Verificar que es un SVG válido
            if not svg_content.strip().startswith('<svg'):
                raise Exception(f"No se encontró el icono '{name}' en Lucide")
            
            # Guardar SVG
            svg_path = self.get_svg_path(name)
            with open(svg_path, 'w', encoding='utf-8') as f:
                f.write(svg_content)
            
            print(f"✓ Icono SVG {name} descargado")
            return True
            
        except requests.exceptions.RequestException as e:
            if "404" in str(e):
                print(f"✗ Icono '{name}' no encontrado en Lucide")
            else:
                print(f"Error de conexión descargando {name}: {e}")
            return False
        except Exception as e:
            print(f"Error descargando {name}: {e}")
            return False
    
    def modify_svg_color(self, svg_content: str, color: str) -> str:
        """Modificar color del SVG"""
        # Reemplazar atributos de color comunes
        svg_content = svg_content.replace('stroke="currentColor"', f'stroke="{color}"')
        svg_content = svg_content.replace('fill="currentColor"', f'fill="{color}"')
        svg_content = svg_content.replace('stroke="none"', f'stroke="{color}"')
        
        # Si no tiene color definido, agregar stroke
        if 'stroke=' not in svg_content and '<path' in svg_content:
            svg_content = svg_content.replace('<path', f'<path stroke="{color}"')
        
        return svg_content
    
    def create_qicon_from_svg(self, svg_content: str, size: int = 24) -> QIcon:
        """Crear QIcon desde contenido SVG"""
        try:
            # Crear renderer SVG
            svg_bytes = QByteArray(svg_content.encode('utf-8'))
            renderer = QSvgRenderer(svg_bytes)
            
            if not renderer.isValid():
                return self.create_fallback_icon(size)
            
            # Crear pixmap
            pixmap = QPixmap(QSize(size, size))
            pixmap.fill(Qt.transparent)  
            
            # Renderizar SVG en pixmap
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            
            return QIcon(pixmap)
            
        except Exception as e:
            print(f"Error creando QIcon desde SVG: {e}")
            return self.create_fallback_icon(size)
    
    def create_fallback_icon(self, size: int = 24) -> QIcon:
        """Crear icono fallback simple"""
        try:
            pixmap = QPixmap(QSize(size, size))
            pixmap.fill()  # Transparente
            
            painter = QPainter(pixmap)
            painter.fillRect(pixmap.rect(), "#cccccc")
            painter.end()
            
            return QIcon(pixmap)
        except:
            return QIcon()  # Icono vacío
    
    def get_icon(self, name: str, size: int = 24, color: str = "#000000") -> QIcon:
        """Obtener icono con color específico"""
        cache_key = f"{name}_{size}_{color}"
        
        # Verificar cache en memoria
        if cache_key in self.icons_cache:
            return self.icons_cache[cache_key]
        
        # Si ya falló antes, usar fallback
        if name in self.failed_icons:
            icon = self.create_fallback_icon(size)
            self.icons_cache[cache_key] = icon
            return icon
        
        svg_path = self.get_svg_path(name)
        
        # Si existe el SVG, cargarlo
        if self.svg_exists(name):
            try:
                with open(svg_path, 'r', encoding='utf-8') as f:
                    svg_content = f.read()
                
                # Modificar color
                colored_svg = self.modify_svg_color(svg_content, color)
                
                # Crear icono
                icon = self.create_qicon_from_svg(colored_svg, size)
                self.icons_cache[cache_key] = icon
                return icon
                
            except Exception as e:
                print(f"Error cargando SVG {name}: {e}")
                # Si falla cargar, intentar re-descargar
                try:
                    os.remove(svg_path)
                except:
                    pass
        
        # Si no existe, descargarlo en hilo separado
        if name not in self.downloading:
            self.downloading.add(name)
            
            def download_thread():
                success = self.download_svg_from_lucide(name)
                self.downloading.discard(name)
                
                if not success:
                    self.failed_icons.add(name)
            
            thread = threading.Thread(target=download_thread, daemon=True)
            thread.start()
        
        # Mientras tanto, devolver fallback
        icon = self.create_fallback_icon(size)
        self.icons_cache[cache_key] = icon
        return icon
    
    def preload_app_icons(self, sizes=[16, 24, 32]):
        """Pre-cargar iconos comunes de la aplicación"""
        def preload_thread():
            for icon_name in self.app_icons.keys():
                if not self.svg_exists(icon_name):
                    self.download_svg_from_lucide(icon_name)
                    time.sleep(0.1)  # Pausa para no saturar
        
        thread = threading.Thread(target=preload_thread, daemon=True)
        thread.start()
    
    def clear_cache(self):
        """Limpiar cache de iconos"""
        try:
            # Limpiar archivos SVG
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.svg'):
                    os.remove(os.path.join(self.cache_dir, filename))
            
            # Limpiar cache en memoria
            self.icons_cache.clear()
            self.failed_icons.clear()
            
            print("Cache de iconos limpiado")
        except Exception as e:
            print(f"Error limpiando cache: {e}")

# Instancia global del gestor
icon_manager = IconManager()

# Funciones de conveniencia
def get_icon(name: str, size: int = 24, color: str = "#000000") -> QIcon:
    """Función conveniente para obtener iconos con color"""
    return icon_manager.get_icon(name, size, color)

def preload_icons():
    """Pre-cargar iconos comunes"""
    icon_manager.preload_app_icons()

def clear_icon_cache():
    """Limpiar cache de iconos"""
    icon_manager.clear_cache()

# Colores predefinidos útiles
class IconColors:
    BLACK = "#000000"
    WHITE = "#ffffff"
    BLUE = "#3498db"
    GREEN = "#27ae60"
    RED = "#e74c3c"
    ORANGE = "#f39c12"
    GRAY = "#95a5a6"
    DARK_GRAY = "#7f8c8d"

# Para testing
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton
    
    app = QApplication(sys.argv)
    
    window = QMainWindow()
    window.setWindowTitle("Test de Iconos SVG")
    
    central_widget = QWidget()
    layout = QVBoxLayout(central_widget)
    
    # Probar algunos iconos con diferentes colores
    test_icons = [
        ("search", IconColors.BLUE),
        ("camera", IconColors.GREEN), 
        ("settings", IconColors.GRAY),
        ("save", IconColors.ORANGE)
    ]
    
    for icon_name, color in test_icons:
        btn = QPushButton(f"{icon_name} ({color})")
        btn.setIcon(get_icon(icon_name, 24, color))
        layout.addWidget(btn)
    
    window.setCentralWidget(central_widget)
    window.show()
    
    sys.exit(app.exec())