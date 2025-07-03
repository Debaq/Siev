#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Protocol Manager - Gestor independiente de protocolos vestibulares
Manejo completo de carga, guardado, validación y manipulación de protocolos
"""

import os
import json
import copy
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from PySide6.QtCore import QObject, Signal


class ProtocolValidationError(Exception):
    """Excepción para errores de validación de protocolos"""
    pass


class ProtocolManager(QObject):
    """
    Gestor completo de protocolos vestibulares independiente.
    Maneja carga, guardado, validación, copia y eliminación de protocolos.
    """
    
    # Señales
    protocols_loaded = Signal(int)  # número de protocolos cargados
    protocols_saved = Signal(bool)  # éxito del guardado
    protocol_added = Signal(str)   # protocol_key añadido
    protocol_removed = Signal(str) # protocol_key eliminado
    protocol_modified = Signal(str) # protocol_key modificado
    validation_error = Signal(str) # mensaje de error
    
    def __init__(self, protocols_path: str = "src/assets/protocols/protocolos_evaluacion_vestibular.json"):
        super().__init__()
        
        self.protocols_path = protocols_path
        self.protocols_data = None
        self.is_loaded = False
        
        # Esquemas de validación
        self.validation_schema = self._load_validation_schema()
        
        print(f"✅ ProtocolManager inicializado para: {protocols_path}")
    
    def _load_validation_schema(self) -> Dict[str, Any]:
        """Cargar esquema de validación para protocolos"""
        return {
            "required_fields": ["name", "category", "behavior_type"],
            "behavior_types": ["recording", "window", "caloric"],
            "categories": ["observacion", "oculomotoras", "calorica", "posicional", "equilibrio"],
            "field_types": {
                "duration_max": int,
                "temperature": (int, float),
                "amplitude": (int, float),
                "frequency": (int, float),
                "time": (int, float)
            },
            "validation_rules": {
                "duration_max": {"min": 10, "max": 600},
                "temperature": {"min": 20, "max": 50},
                "amplitude": {"min": 1, "max": 90},
                "frequency": {"min": 0.1, "max": 10.0},
                "time": {"min": 0, "max": 600}
            },
            "led_targets": ["LEFT", "RIGHT"],
            "event_actions": ["activate_torok_tool", "led_on", "led_off", "deactivate_torok_tool"]
        }
    
    def load_protocols(self) -> bool:
        """
        Cargar protocolos desde archivo JSON.
        
        Returns:
            bool: True si la carga fue exitosa
        """
        try:
            if not os.path.exists(self.protocols_path):
                print(f"❌ Archivo no encontrado: {self.protocols_path}")
                self.protocols_data = self._create_default_structure()
                self._create_default_file()
                return False
            
            with open(self.protocols_path, 'r', encoding='utf-8') as f:
                self.protocols_data = json.load(f)
            
            # Validar estructura básica
            if not self._validate_file_structure():
                print("⚠️ Estructura de archivo inválida, creando estructura por defecto")
                self.protocols_data = self._create_default_structure()
                return False
            
            total_protocols = len(self.get_all_protocols())
            self.is_loaded = True
            
            print(f"✅ {total_protocols} protocolos cargados desde {self.protocols_path}")
            self.protocols_loaded.emit(total_protocols)
            return True
            
        except json.JSONDecodeError as e:
            print(f"❌ Error de JSON: {e}")
            self.protocols_data = self._create_default_structure()
            self.validation_error.emit(f"Archivo JSON inválido: {e}")
            return False
        except Exception as e:
            print(f"❌ Error cargando protocolos: {e}")
            self.protocols_data = self._create_default_structure()
            self.validation_error.emit(f"Error de carga: {e}")
            return False
    
    def save_protocols(self) -> bool:
        """
        Guardar protocolos al archivo JSON.
        
        Returns:
            bool: True si el guardado fue exitoso
        """
        try:
            if not self.protocols_data:
                print("❌ No hay datos para guardar")
                return False
            
            # Crear directorio si no existe
            os.makedirs(os.path.dirname(self.protocols_path), exist_ok=True)
            
            # Agregar metadata de guardado
            self.protocols_data["last_saved"] = datetime.now().isoformat()
            
            # Guardar con formato bonito
            with open(self.protocols_path, 'w', encoding='utf-8') as f:
                json.dump(self.protocols_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Protocolos guardados en {self.protocols_path}")
            self.protocols_saved.emit(True)
            return True
            
        except Exception as e:
            print(f"❌ Error guardando protocolos: {e}")
            self.protocols_saved.emit(False)
            self.validation_error.emit(f"Error de guardado: {e}")
            return False
    
    def _create_default_structure(self) -> Dict[str, Any]:
        """Crear estructura por defecto de protocolos"""
        return {
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "description": "Protocolos de evaluación vestibular SIEV",
            "default": {
                "nistagmo_espontaneo": {
                    "name": "Nistagmo Espontáneo",
                    "category": "observacion",
                    "behavior_type": "recording",
                    "duration_max": None,
                    "description": "Observación de nistagmo espontáneo sin estimulación",
                    "protocol": {
                        "recording_mode": "manual",
                        "auto_stop": False
                    },
                    "ui_settings": {
                        "show_crosshair": True,
                        "show_tracking_circles": True,
                        "show_eye_detection": True,
                        "show_pupil_detection": True
                    },
                    "hardware_control": {
                        "led_control": False,
                        "esp8266_commands": []
                    },
                    "graph_tools": {
                        "torok_tool": False,
                        "peak_editing": True,
                        "tiempo_fijacion": False,
                        "zoom": True,
                        "crosshair": True
                    }
                }
            },
            "presets": {},
            "ui_tree_structure": {
                "observacion": {
                    "parent": None,
                    "display_name": "Pruebas de Observación",
                    "icon": "eye",
                    "expandable": True,
                    "children": [
                        {
                            "key": "nistagmo_espontaneo",
                            "display_name": "Nistagmo Espontáneo",
                            "icon": "circle"
                        }
                    ]
                }
            },
            "configuration_schema": self.validation_schema
        }
    
    def _create_default_file(self):
        """Crear archivo por defecto si no existe"""
        try:
            if self.save_protocols():
                print(f"✅ Archivo por defecto creado: {self.protocols_path}")
        except Exception as e:
            print(f"❌ Error creando archivo por defecto: {e}")
    
    def _validate_file_structure(self) -> bool:
        """Validar estructura básica del archivo"""
        if not isinstance(self.protocols_data, dict):
            return False
        
        required_sections = ["version", "default", "presets", "ui_tree_structure"]
        for section in required_sections:
            if section not in self.protocols_data:
                print(f"⚠️ Sección faltante: {section}")
                return False
        
        return True
    
    def get_protocol(self, protocol_key: str) -> Optional[Dict[str, Any]]:
        """
        Obtener protocolo por clave.
        
        Args:
            protocol_key: Clave del protocolo
            
        Returns:
            Datos del protocolo o None si no existe
        """
        if not self.protocols_data:
            return None
        
        # Buscar en defaults
        if protocol_key in self.protocols_data.get("default", {}):
            return self.protocols_data["default"][protocol_key]
        
        # Buscar en presets
        if protocol_key in self.protocols_data.get("presets", {}):
            return self.protocols_data["presets"][protocol_key]
        
        return None
    
    def get_all_protocols(self) -> Dict[str, Dict[str, Any]]:
        """
        Obtener todos los protocolos (defaults + presets).
        
        Returns:
            Diccionario con todos los protocolos
        """
        if not self.protocols_data:
            return {}
        
        protocols = {}
        protocols.update(self.protocols_data.get("default", {}))
        protocols.update(self.protocols_data.get("presets", {}))
        return protocols
    
    def get_default_protocols(self) -> Dict[str, Dict[str, Any]]:
        """Obtener solo protocolos por defecto"""
        if not self.protocols_data:
            return {}
        return self.protocols_data.get("default", {})
    
    def get_preset_protocols(self) -> Dict[str, Dict[str, Any]]:
        """Obtener solo protocolos personalizados"""
        if not self.protocols_data:
            return {}
        return self.protocols_data.get("presets", {})
    
    def get_protocols_by_category(self, category: str) -> Dict[str, Dict[str, Any]]:
        """
        Obtener protocolos por categoría.
        
        Args:
            category: Categoría a filtrar
            
        Returns:
            Protocolos de la categoría especificada
        """
        all_protocols = self.get_all_protocols()
        return {
            key: protocol for key, protocol in all_protocols.items()
            if protocol.get("category") == category
        }
    
    def is_default_protocol(self, protocol_key: str) -> bool:
        """
        Verificar si es un protocolo por defecto.
        
        Args:
            protocol_key: Clave del protocolo
            
        Returns:
            True si es protocolo por defecto
        """
        if not self.protocols_data:
            return False
        return protocol_key in self.protocols_data.get("default", {})
    
    def validate_protocol(self, protocol_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validar datos de protocolo.
        
        Args:
            protocol_data: Datos del protocolo a validar
            
        Returns:
            Tuple (es_válido, lista_de_errores)
        """
        errors = []
        
        # Validar campos requeridos
        for field in self.validation_schema["required_fields"]:
            if field not in protocol_data:
                errors.append(f"Campo requerido faltante: {field}")
        
        # Validar behavior_type
        behavior_type = protocol_data.get("behavior_type")
        if behavior_type not in self.validation_schema["behavior_types"]:
            errors.append(f"Behavior type inválido: {behavior_type}")
        
        # Validar categoría
        category = protocol_data.get("category")
        if category not in self.validation_schema["categories"]:
            errors.append(f"Categoría inválida: {category}")
        
        # Validar tipos de datos
        for field, expected_type in self.validation_schema["field_types"].items():
            if field in protocol_data:
                value = protocol_data[field]
                if not isinstance(value, expected_type):
                    errors.append(f"Tipo incorrecto para {field}: esperado {expected_type}")
        
        # Validar rangos
        for field, rules in self.validation_schema["validation_rules"].items():
            if field in protocol_data:
                value = protocol_data[field]
                if isinstance(value, (int, float)):
                    if "min" in rules and value < rules["min"]:
                        errors.append(f"{field} menor que mínimo: {value} < {rules['min']}")
                    if "max" in rules and value > rules["max"]:
                        errors.append(f"{field} mayor que máximo: {value} > {rules['max']}")
        
        # Validar eventos para protocolos calóricos
        if behavior_type == "caloric":
            events = protocol_data.get("protocol", {}).get("events", [])
            for i, event in enumerate(events):
                if "action" in event and event["action"] not in self.validation_schema["event_actions"]:
                    errors.append(f"Acción inválida en evento {i}: {event['action']}")
                
                if "led_target" in event and event["led_target"] not in self.validation_schema["led_targets"]:
                    errors.append(f"LED target inválido en evento {i}: {event['led_target']}")
        
        return len(errors) == 0, errors
    
    def add_protocol(self, protocol_key: str, protocol_data: Dict[str, Any], 
                    is_preset: bool = True) -> bool:
        """
        Agregar nuevo protocolo.
        
        Args:
            protocol_key: Clave única del protocolo
            protocol_data: Datos del protocolo
            is_preset: True para preset, False para default
            
        Returns:
            True si se agregó correctamente
        """
        try:
            # Validar protocolo
            is_valid, errors = self.validate_protocol(protocol_data)
            if not is_valid:
                error_msg = f"Protocolo inválido: {', '.join(errors)}"
                print(f"❌ {error_msg}")
                self.validation_error.emit(error_msg)
                return False
            
            # Verificar que no exista
            if self.get_protocol(protocol_key):
                error_msg = f"Ya existe un protocolo con clave: {protocol_key}"
                print(f"❌ {error_msg}")
                self.validation_error.emit(error_msg)
                return False
            
            # Agregar metadata
            protocol_data = protocol_data.copy()
            protocol_data["created_date"] = datetime.now().isoformat()
            protocol_data["created_by"] = "Usuario"
            
            # Agregar al lugar correspondiente
            if is_preset:
                if "presets" not in self.protocols_data:
                    self.protocols_data["presets"] = {}
                self.protocols_data["presets"][protocol_key] = protocol_data
            else:
                if "default" not in self.protocols_data:
                    self.protocols_data["default"] = {}
                self.protocols_data["default"][protocol_key] = protocol_data
            
            print(f"✅ Protocolo agregado: {protocol_key}")
            self.protocol_added.emit(protocol_key)
            return True
            
        except Exception as e:
            error_msg = f"Error agregando protocolo: {e}"
            print(f"❌ {error_msg}")
            self.validation_error.emit(error_msg)
            return False
    
    def copy_protocol(self, source_key: str, new_name: str, 
                     description: str = "") -> Optional[str]:
        """
        Copiar protocolo existente con nuevo nombre.
        
        Args:
            source_key: Clave del protocolo origen
            new_name: Nombre para la copia
            description: Descripción opcional
            
        Returns:
            Clave del nuevo protocolo o None si falló
        """
        try:
            source_protocol = self.get_protocol(source_key)
            if not source_protocol:
                error_msg = f"Protocolo origen no encontrado: {source_key}"
                print(f"❌ {error_msg}")
                self.validation_error.emit(error_msg)
                return None
            
            # Crear copia profunda
            new_protocol = copy.deepcopy(source_protocol)
            
            # Actualizar metadatos
            new_protocol["name"] = new_name
            new_protocol["base"] = source_key
            new_protocol["created_by"] = "Usuario"
            new_protocol["created_date"] = datetime.now().isoformat()
            new_protocol["copied_from"] = source_key
            
            if description:
                new_protocol["description"] = description
            
            # Generar clave única
            new_key = self._generate_unique_key(new_name)
            
            # Agregar como preset
            if self.add_protocol(new_key, new_protocol, is_preset=True):
                print(f"✅ Protocolo copiado: {source_key} → {new_key}")
                return new_key
            else:
                return None
                
        except Exception as e:
            error_msg = f"Error copiando protocolo: {e}"
            print(f"❌ {error_msg}")
            self.validation_error.emit(error_msg)
            return None
    
    def update_protocol(self, protocol_key: str, updates: Dict[str, Any]) -> bool:
        """
        Actualizar protocolo existente.
        
        Args:
            protocol_key: Clave del protocolo
            updates: Diccionario con campos a actualizar
            
        Returns:
            True si se actualizó correctamente
        """
        try:
            # Verificar que existe
            protocol = self.get_protocol(protocol_key)
            if not protocol:
                error_msg = f"Protocolo no encontrado: {protocol_key}"
                print(f"❌ {error_msg}")
                self.validation_error.emit(error_msg)
                return False
            
            # No permitir modificar defaults (solo metadata)
            if self.is_default_protocol(protocol_key):
                allowed_fields = ["description", "last_modified"]
                invalid_fields = [f for f in updates.keys() if f not in allowed_fields]
                if invalid_fields:
                    error_msg = f"No se pueden modificar campos en protocolos default: {invalid_fields}"
                    print(f"❌ {error_msg}")
                    self.validation_error.emit(error_msg)
                    return False
            
            # Crear protocolo actualizado
            updated_protocol = protocol.copy()
            updated_protocol.update(updates)
            updated_protocol["last_modified"] = datetime.now().isoformat()
            
            # Validar protocolo actualizado
            is_valid, errors = self.validate_protocol(updated_protocol)
            if not is_valid:
                error_msg = f"Protocolo actualizado inválido: {', '.join(errors)}"
                print(f"❌ {error_msg}")
                self.validation_error.emit(error_msg)
                return False
            
            # Aplicar actualización
            if self.is_default_protocol(protocol_key):
                self.protocols_data["default"][protocol_key] = updated_protocol
            else:
                self.protocols_data["presets"][protocol_key] = updated_protocol
            
            print(f"✅ Protocolo actualizado: {protocol_key}")
            self.protocol_modified.emit(protocol_key)
            return True
            
        except Exception as e:
            error_msg = f"Error actualizando protocolo: {e}"
            print(f"❌ {error_msg}")
            self.validation_error.emit(error_msg)
            return False
    
    def delete_protocol(self, protocol_key: str) -> bool:
        """
        Eliminar protocolo (solo presets).
        
        Args:
            protocol_key: Clave del protocolo
            
        Returns:
            True si se eliminó correctamente
        """
        try:
            # Verificar que no es default
            if self.is_default_protocol(protocol_key):
                error_msg = f"No se pueden eliminar protocolos default: {protocol_key}"
                print(f"❌ {error_msg}")
                self.validation_error.emit(error_msg)
                return False
            
            # Verificar que existe en presets
            if protocol_key not in self.protocols_data.get("presets", {}):
                error_msg = f"Protocolo preset no encontrado: {protocol_key}"
                print(f"❌ {error_msg}")
                self.validation_error.emit(error_msg)
                return False
            
            # Eliminar
            del self.protocols_data["presets"][protocol_key]
            
            print(f"✅ Protocolo eliminado: {protocol_key}")
            self.protocol_removed.emit(protocol_key)
            return True
            
        except Exception as e:
            error_msg = f"Error eliminando protocolo: {e}"
            print(f"❌ {error_msg}")
            self.validation_error.emit(error_msg)
            return False
    
    def _generate_unique_key(self, name: str) -> str:
        """
        Generar clave única para protocolo.
        
        Args:
            name: Nombre base
            
        Returns:
            Clave única
        """
        # Normalizar nombre
        base_key = name.lower().replace(" ", "_").replace("-", "_")
        base_key = "".join(c for c in base_key if c.isalnum() or c == "_")
        
        # Asegurar unicidad
        counter = 1
        current_key = base_key
        
        while (current_key in self.protocols_data.get("default", {}) or 
               current_key in self.protocols_data.get("presets", {})):
            current_key = f"{base_key}_{counter}"
            counter += 1
        
        return current_key
    
    def get_ui_tree_structure(self) -> Dict[str, Any]:
        """Obtener estructura del árbol UI"""
        if not self.protocols_data:
            return {}
        return self.protocols_data.get("ui_tree_structure", {})
    
    def get_validation_schema(self) -> Dict[str, Any]:
        """Obtener esquema de validación"""
        return self.validation_schema
    
    def export_protocols(self, export_path: str, include_defaults: bool = True,
                        include_presets: bool = True) -> bool:
        """
        Exportar protocolos a archivo.
        
        Args:
            export_path: Ruta de exportación
            include_defaults: Incluir protocolos default
            include_presets: Incluir protocolos preset
            
        Returns:
            True si se exportó correctamente
        """
        try:
            export_data = {
                "version": self.protocols_data.get("version", "1.0"),
                "exported": datetime.now().isoformat(),
                "source": self.protocols_path
            }
            
            if include_defaults:
                export_data["default"] = self.protocols_data.get("default", {})
            
            if include_presets:
                export_data["presets"] = self.protocols_data.get("presets", {})
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Protocolos exportados a: {export_path}")
            return True
            
        except Exception as e:
            error_msg = f"Error exportando protocolos: {e}"
            print(f"❌ {error_msg}")
            self.validation_error.emit(error_msg)
            return False
    
    def import_protocols(self, import_path: str, overwrite_existing: bool = False) -> Tuple[bool, int]:
        """
        Importar protocolos desde archivo.
        
        Args:
            import_path: Ruta del archivo a importar
            overwrite_existing: Sobrescribir protocolos existentes
            
        Returns:
            Tuple (éxito, número_importados)
        """
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            imported_count = 0
            
            # Importar presets
            for key, protocol in import_data.get("presets", {}).items():
                if not overwrite_existing and self.get_protocol(key):
                    continue
                
                if self.add_protocol(key, protocol, is_preset=True):
                    imported_count += 1
            
            print(f"✅ {imported_count} protocolos importados desde: {import_path}")
            return True, imported_count
            
        except Exception as e:
            error_msg = f"Error importando protocolos: {e}"
            print(f"❌ {error_msg}")
            self.validation_error.emit(error_msg)
            return False, 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas de protocolos"""
        all_protocols = self.get_all_protocols()
        
        stats = {
            "total_protocols": len(all_protocols),
            "default_protocols": len(self.get_default_protocols()),
            "preset_protocols": len(self.get_preset_protocols()),
            "categories": {},
            "behavior_types": {},
            "file_path": self.protocols_path,
            "is_loaded": self.is_loaded
        }
        
        # Estadísticas por categoría
        for protocol in all_protocols.values():
            category = protocol.get("category", "unknown")
            stats["categories"][category] = stats["categories"].get(category, 0) + 1
            
            behavior_type = protocol.get("behavior_type", "unknown")
            stats["behavior_types"][behavior_type] = stats["behavior_types"].get(behavior_type, 0) + 1
        
        return stats