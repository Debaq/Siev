#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Icon utilities - Descarga automática de iconos Lucide con carga controlada
"""

import os
import requests
import tkinter as tk
from PIL import Image, ImageTk
from io import BytesIO
import threading
import time

class IconManager:
    """Gestor de iconos con descarga automática desde Lucide"""
    
    def __init__(self, cache_dir="assets/icons"):
        self.cache_dir = cache_dir
        self.icons = {}
        self.downloading = set()
        self.failed_icons = set()
        self.qt_ready = False  # NUEVO: Flag para saber si Qt está listo
        
        # Crear directorio de cache si no existe
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Iconos por defecto para la aplicación
        self.app_icons = {
            "file-text": "Archivos GIFT",
            "file-pen-line": "Crear evaluaciones",
            "search": "Revisar evaluaciones", 
            "settings": "Configuración",
            "circle-plus": "Agregar pregunta",
            "trash-2": "Eliminar",
            "arrow-up": "Subir pregunta",
            "arrow-down": "Bajar pregunta",
            "save": "Guardar",
            "folder-open": "Abrir carpeta",
            "eye": "Vista previa",
            "download": "Descargar",
            "upload": "Cargar",
            "circle-check": "Completado",
            "circle-x": "Error",
            "triangle-alert": "Advertencia",
            "info": "Información",
            "camera": "Cámara",
            "rotate-cw": "Rotar"
        }
    
    def set_qt_ready(self, ready=True):
        """Marcar que Qt está listo para crear imágenes"""
        self.qt_ready = ready
        print(f"🖼️ Qt ready for images: {ready}")
    
    def get_icon_path(self, name, size=24):
        """Obtener ruta del archivo de icono"""
        return os.path.join(self.cache_dir, f"{name}_{size}.png")
    
    def icon_exists(self, name, size=24):
        """Verificar si el icono existe localmente"""
        return os.path.exists(self.get_icon_path(name, size))
    
    def download_icon_from_lucide(self, name, size=24, color="000000"):
        """Descargar icono desde GitHub de Lucide"""
        try:
            # URL correcta de GitHub raw para Lucide
            url = f"https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/{name}.svg"
            
            # Timeout para evitar bloqueos
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            svg_content = response.text
            
            # Verificar que es un SVG válido
            if not svg_content.strip().startswith('<svg'):
                raise Exception(f"No se encontró el icono '{name}' en Lucide")
            
            # Modificar color del stroke
            svg_content = svg_content.replace('stroke="currentColor"', f'stroke="#{color}"')
            
            # Convertir SVG a PNG usando cairosvg si está disponible
            try:
                import cairosvg
                png_data = cairosvg.svg2png(
                    bytestring=svg_content.encode('utf-8'),
                    output_width=size,
                    output_height=size
                )
                
                # Guardar archivo
                icon_path = self.get_icon_path(name, size)
                with open(icon_path, "wb") as f:
                    f.write(png_data)
                
                print(f"✓ Icono {name} descargado desde GitHub")
                return True
                
            except ImportError:
                print("cairosvg no está instalado. Usando fallback...")
                # Fallback: crear icono simple
                return self.create_fallback_icon_file(name, size)
                
        except requests.exceptions.RequestException as e:
            if "404" in str(e):
                print(f"✗ Icono '{name}' no encontrado en Lucide")
            else:
                print(f"Error de conexión descargando icono {name}: {e}")
            return False
        except Exception as e:
            print(f"Error descargando icono {name}: {e}")
            return False
    
    def create_fallback_icon_file(self, name, size):
        """Crear icono fallback simple y guardarlo"""
        try:
            # Crear imagen simple con letra inicial
            img = Image.new('RGBA', (size, size), (70, 130, 180, 255))  # SteelBlue
            
            # Guardar como PNG
            icon_path = self.get_icon_path(name, size)
            img.save(icon_path, "PNG")
            return True
            
        except Exception as e:
            print(f"Error creando fallback para {name}: {e}")
            return False
    
    def load_icon(self, name, size=24, color="000000"):
        """Cargar icono, descargándolo si no existe"""
        # SI QT NO ESTÁ LISTO, NO INTENTAR CREAR IMÁGENES
        if not self.qt_ready:
            print(f"⚠️ Qt no está listo, no se puede cargar icono {name}")
            return self.create_text_fallback(name)
        
        key = f"{name}_{size}_{color}"
        
        # Si ya está en memoria, devolverlo
        if key in self.icons:
            return self.icons[key]
        
        # Si ya falló anteriormente, usar fallback en memoria
        if name in self.failed_icons:
            return self.create_memory_fallback(name, size)
        
        icon_path = self.get_icon_path(name, size)
        
        # Si el archivo existe, cargarlo
        if self.icon_exists(name, size):
            try:
                img = Image.open(icon_path)
                self.icons[key] = ImageTk.PhotoImage(img)
                return self.icons[key]
            except Exception as e:
                print(f"Error cargando icono {name}: {e}")
                # Si falla cargar, intentar re-descargar
                try:
                    os.remove(icon_path)
                except:
                    pass
        
        # Si no existe, descargarlo SOLO SI Qt está listo
        if name not in self.downloading and self.qt_ready:
            self.downloading.add(name)
            
            # Descargar en hilo separado para no bloquear UI
            def download_thread():
                success = self.download_icon_from_lucide(name, size, color)
                self.downloading.discard(name)
                
                if not success:
                    self.failed_icons.add(name)
            
            thread = threading.Thread(target=download_thread, daemon=True)
            thread.start()
        
        # Mientras tanto, devolver fallback en memoria
        return self.create_memory_fallback(name, size)
    
    def create_text_fallback(self, name):
        """Crear fallback de texto cuando Qt no está listo"""
        # Devolver None para que se use texto en lugar de icono
        return None
    
    def create_memory_fallback(self, name, size):
        """Crear icono fallback en memoria"""
        if not self.qt_ready:
            return None
        
        key = f"fallback_{name}_{size}"
        
        if key not in self.icons:
            try:
                # Crear imagen simple con texto
                img = Image.new('RGBA', (size, size), (128, 128, 128, 255))
                
                # Intentar agregar texto si PIL lo soporta
                try:
                    from PIL import ImageDraw, ImageFont
                    draw = ImageDraw.Draw(img)
                    
                    # Usar primera letra del nombre del icono
                    text = name[0].upper() if name else "?"
                    
                    # Intentar cargar fuente, o usar default
                    try:
                        font_size = max(8, size // 3)
                        font = ImageFont.load_default()
                    except:
                        font = None
                    
                    # Centrar texto
                    if font:
                        bbox = draw.textbbox((0, 0), text, font=font)
                        text_width = bbox[2] - bbox[0]
                        text_height = bbox[3] - bbox[1]
                        x = (size - text_width) // 2
                        y = (size - text_height) // 2
                        draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)
                    
                except ImportError:
                    pass  # PIL sin ImageDraw
                
                self.icons[key] = ImageTk.PhotoImage(img)
            except Exception as e:
                print(f"Error creando fallback en memoria: {e}")
                return None
        
        return self.icons.get(key)
    
    def preload_app_icons(self, sizes=[16, 24, 32]):
        """Pre-cargar iconos comunes de la aplicación"""
        if not self.qt_ready:
            print("⚠️ Qt no está listo, saltando precarga de iconos")
            return
        
        def preload_thread():
            for icon_name in self.app_icons.keys():
                for size in sizes:
                    if not self.icon_exists(icon_name, size):
                        self.download_icon_from_lucide(icon_name, size)
                        time.sleep(0.1)  # Pequeña pausa para no saturar la API
        
        thread = threading.Thread(target=preload_thread, daemon=True)
        thread.start()
    
    def clear_cache(self):
        """Limpiar cache de iconos"""
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.png'):
                    os.remove(os.path.join(self.cache_dir, filename))
            self.icons.clear()
            self.failed_icons.clear()
            print("Cache de iconos limpiado")
        except Exception as e:
            print(f"Error limpiando cache: {e}")

# Instancia global del gestor de iconos
icon_manager = IconManager()

# Funciones de conveniencia
def set_qt_ready(ready=True):
    """Marcar que Qt está listo para crear imágenes"""
    icon_manager.set_qt_ready(ready)

def get_icon(name, size=24, color="000000"):
    """Función conveniente para obtener iconos"""
    return icon_manager.load_icon(name, size, color)

def preload_icons():
    """Pre-cargar iconos comunes"""
    icon_manager.preload_app_icons()

def clear_icon_cache():
    """Limpiar cache de iconos"""
    icon_manager.clear_cache()

# NO inicializar automáticamente hasta que Qt esté listo
# La aplicación debe llamar set_qt_ready(True) cuando esté lista

# Para testing
if __name__ == "__main__":
    # Test básico
    root = tk.Tk()
    root.title("Test de Iconos")
    
    frame = tk.Frame(root, padding=20)
    frame.pack()
    
    # Marcar Qt como listo para testing
    set_qt_ready(True)
    
    # Probar algunos iconos
    test_icons = ["file-pen-line", "search", "save", "settings"]
    
    for i, icon_name in enumerate(test_icons):
        icon = get_icon(icon_name, 32)
        btn = tk.Button(frame, text=icon_name, image=icon, compound="top")
        btn.grid(row=0, column=i, padx=10, pady=10)
    
    root.mainloop()