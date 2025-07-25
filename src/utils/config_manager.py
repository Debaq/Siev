import json
import os
import sys


class ConfigManager:
    """
    Gestor de configuración centralizado para la aplicación VNG.
    Maneja carga, guardado y validación de configuraciones.
    """
    
    def __init__(self, config_filename="config.json"):
        self.config_filename = config_filename
        self.config = {}
        self.base_path = self._get_base_path()
        data_path = self.get_data_path()

        self.config_path = os.path.join(data_path, "config", self.config_filename)
        
        # Configuración por defecto
        self.default_config = {
            "app_name": "vng",
            "window_title": "VNG Application",
            "version": "0.0.2",
            "author": {
                "name": "Nicolás Baier",
                "email": "david.avila@uach.cl",
                "company": "UACH"
            },
            "description": "VNG",
            "license": "MIT",
            "window_size": {
                "width": 800,
                "height": 600
            },
            "data_path": "~/siev_data",  # Cambiado para usar home del usuario
            "slider_settings": {
                "slider_th_right": 16,
                "slider_th_left": 19,
                "slider_erode_right": 0,
                "slider_erode_left": 1,
                "slider_nose_width": 25,
                "slider_height": 50,
                "slider_brightness": 50,
                "slider_contrast": 50
            }
        }
        
        self.load_config()
    
    def _get_base_path(self):
        """Obtener el directorio base de la aplicación"""
        if getattr(sys, "frozen", False):
            return os.path.dirname(sys.executable)
        else:
            return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    def load_config(self):
        """Cargar configuración desde archivo JSON"""
        try:
            with open(self.config_path, "r", encoding='utf-8') as f:
                self.config = json.load(f)
            
            # Validar y completar configuración con valores por defecto
            self._validate_and_complete_config()
            
            # Asegurar que existan los directorios de datos
            self._ensure_data_directories()
            
            print(f"Configuración cargada desde: {self.config_path}")
            print(f"Ruta de datos: {self.get_data_path()}")
            
        except FileNotFoundError:
            print(f"Archivo de configuración no encontrado: {self.config_path}")
            print("Creando configuración por defecto...")
            self.config = self.default_config.copy()
            self.save_config()
            self._ensure_data_directories()
            
        except json.JSONDecodeError as e:
            print(f"Error al leer JSON: {e}")
            print("Usando configuración por defecto...")
            self.config = self.default_config.copy()
            self._ensure_data_directories()
            
        except Exception as e:
            print(f"Error cargando configuración: {e}")
            self.config = self.default_config.copy()
            self._ensure_data_directories()
    
    def save_config(self):
        """Guardar configuración actual al archivo JSON"""
        try:
            # Crear directorio de configuración si no existe
            config_dir = os.path.dirname(self.config_path)
            os.makedirs(config_dir, exist_ok=True)
            
            with open(self.config_path, "w", encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            
            #print(f"Configuración guardada en: {self.config_path}")
            return True
            
        except Exception as e:
            print(f"Error guardando configuración: {e}")
            return False
    
    def _validate_and_complete_config(self):
        """Validar y completar configuración con valores por defecto"""
        def update_dict(original, default):
            for key, value in default.items():
                if key not in original:
                    original[key] = value
                elif isinstance(value, dict) and isinstance(original[key], dict):
                    update_dict(original[key], value)
        
        update_dict(self.config, self.default_config)
    
    def _ensure_data_directories(self):
        """Crear directorios de datos si no existen"""
        try:
            data_path = self.get_data_path()
            
            # Crear directorio base
            os.makedirs(data_path, exist_ok=True)
            
            # Crear subdirectorios
            data_dir = os.path.join(data_path, "data")
            logs_dir = os.path.join(data_path, "logs")
            
            os.makedirs(data_dir, exist_ok=True)
            os.makedirs(logs_dir, exist_ok=True)
            
            print(f"Directorios de datos asegurados en: {data_path}")
            
        except Exception as e:
            print(f"Error creando directorios de datos: {e}")
    
    def get_data_path(self):
        """Obtener la ruta de datos configurada expandiendo ~ si es necesario"""
        data_path = self.config.get("data_path", "~/siev_data")
        return os.path.expanduser(data_path)  # Expande ~ al home del usuario
    
    def get_data_dir(self):
        """Obtener el directorio de datos CSV"""
        return os.path.join(self.get_data_path(), "data")
    
    def get_logs_dir(self):
        """Obtener el directorio de logs"""
        return os.path.join(self.get_data_path(), "logs")
    
    def get_window_config(self):
        """Obtener configuración de ventana"""
        return {
            "title": self.config.get("window_title", "VNG Application"),
            "size": self.config.get("window_size", {"width": 800, "height": 600})
        }
    
    def get_slider_settings(self):
        """Obtener configuración de sliders"""
        return self.config.get("slider_settings", {})
    
    def update_slider_settings(self, slider_values):
        """Actualizar configuración de sliders"""
        if "slider_settings" not in self.config:
            self.config["slider_settings"] = {}
        
        self.config["slider_settings"].update(slider_values)
        return self.save_config()
    
    def get_slider_value(self, slider_name, default_value=0):
        """Obtener valor específico de un slider"""
        return self.config.get("slider_settings", {}).get(slider_name, default_value)
    
    def set_slider_value(self, slider_name, value):
        """Establecer valor específico de un slider"""
        if "slider_settings" not in self.config:
            self.config["slider_settings"] = {}
        
        self.config["slider_settings"][slider_name] = value
        return self.save_config()
    
    def get_app_info(self):
        """Obtener información de la aplicación"""
        return {
            "name": self.config.get("app_name", "vng"),
            "version": self.config.get("version", "0.0.2"),
            "author": self.config.get("author", {}),
            "description": self.config.get("description", "VNG"),
            "license": self.config.get("license", "MIT")
        }
    
    def get_config(self):
        """Obtener configuración completa"""
        return self.config.copy()
    
    def set_data_path(self, new_path):
        """Cambiar la ruta de datos"""
        self.config["data_path"] = new_path
        self._ensure_data_directories()
        return self.save_config()
    
    def reset_to_defaults(self):
        """Resetear configuración a valores por defecto"""
        self.config = self.default_config.copy()
        self._ensure_data_directories()
        return self.save_config()