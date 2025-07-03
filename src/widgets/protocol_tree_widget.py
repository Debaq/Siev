#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Protocol Tree Widget - Widget completo para manejo de protocolos vestibulares
Incluye TreeWidget + Toolbar + Botón de iniciar + toda la lógica de protocolos
"""

import os
import json
import copy
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                              QTreeWidget, QTreeWidgetItem, QMessageBox, 
                              QInputDialog, QFrame)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QIcon
from utils.icon_utils import get_icon, IconColors


class ProtocolManager:
    """Gestor de protocolos vestibulares con carga y manejo de presets"""
    
    def __init__(self, protocols_path="src/assets/protocols/protocolos_evaluacion_vestibular.json"):
        self.protocols_path = protocols_path
        self.protocols_data = None
        self.load_protocols()
    
    def load_protocols(self):
        """Cargar protocolos desde archivo JSON"""
        try:
            with open(self.protocols_path, 'r', encoding='utf-8') as f:
                self.protocols_data = json.load(f)
            print(f"✅ Protocolos cargados desde {self.protocols_path}")
            return True
        except FileNotFoundError:
            print(f"❌ No se encontró el archivo de protocolos: {self.protocols_path}")
            self.protocols_data = self._create_minimal_fallback()
            return False
        except Exception as e:
            print(f"❌ Error cargando protocolos: {e}")
            self.protocols_data = self._create_minimal_fallback()
            return False
    
    def save_protocols(self):
        """Guardar protocolos al archivo JSON"""
        try:
            with open(self.protocols_path, 'w', encoding='utf-8') as f:
                json.dump(self.protocols_data, f, indent=2, ensure_ascii=False)
            print("✅ Protocolos guardados correctamente")
            return True
        except Exception as e:
            print(f"❌ Error guardando protocolos: {e}")
            return False
    
    def _create_minimal_fallback(self):
        """Crear estructura mínima de fallback"""
        return {
            "version": "1.0",
            "default": {
                "nistagmo_espontaneo": {
                    "name": "Nistagmo Espontáneo",
                    "category": "observacion",
                    "behavior_type": "recording",
                    "description": "Protocolo básico de fallback"
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
            }
        }
    
    def get_protocol(self, protocol_key):
        """Obtener protocolo por clave"""
        # Primero buscar en defaults
        if protocol_key in self.protocols_data.get("default", {}):
            return self.protocols_data["default"][protocol_key]
        
        # Luego buscar en presets
        if protocol_key in self.protocols_data.get("presets", {}):
            return self.protocols_data["presets"][protocol_key]
        
        return None
    
    def get_all_protocols(self):
        """Obtener todos los protocolos (defaults + presets)"""
        protocols = {}
        protocols.update(self.protocols_data.get("default", {}))
        protocols.update(self.protocols_data.get("presets", {}))
        return protocols
    
    def is_default_protocol(self, protocol_key):
        """Verificar si es un protocolo por defecto"""
        return protocol_key in self.protocols_data.get("default", {})
    
    def copy_protocol(self, protocol_key, new_name):
        """Copiar protocolo existente con nuevo nombre"""
        protocol = self.get_protocol(protocol_key)
        if not protocol:
            return False
        
        # Crear copia
        new_protocol = copy.deepcopy(protocol)
        new_protocol["name"] = new_name
        new_protocol["base"] = protocol_key
        new_protocol["created_by"] = "Usuario"
        new_protocol["created_date"] = "2025-07-03"
        
        # Generar clave única
        new_key = self._generate_unique_key(new_name)
        
        # Guardar en presets
        if "presets" not in self.protocols_data:
            self.protocols_data["presets"] = {}
        
        self.protocols_data["presets"][new_key] = new_protocol
        
        return new_key
    
    def delete_protocol(self, protocol_key):
        """Eliminar protocolo (solo presets)"""
        if self.is_default_protocol(protocol_key):
            return False  # No se pueden eliminar defaults
        
        if protocol_key in self.protocols_data.get("presets", {}):
            del self.protocols_data["presets"][protocol_key]
            return True
        
        return False
    
    def _generate_unique_key(self, name):
        """Generar clave única para protocolo"""
        base_key = name.lower().replace(" ", "_").replace("-", "_")
        counter = 1
        
        while (base_key in self.protocols_data.get("default", {}) or 
               base_key in self.protocols_data.get("presets", {})):
            base_key = f"{name.lower().replace(' ', '_')}_{counter}"
            counter += 1
        
        return base_key


class ProtocolTreeWidget(QWidget):
    """
    Widget completo para manejo de protocolos vestibulares.
    Incluye TreeWidget, toolbar de acciones y botón de iniciar.
    """
    
    # Señales
    protocol_selected = Signal(str)  # protocol_key
    protocol_execution_requested = Signal(dict)  # protocol_data
    protocol_changed = Signal(str)  # mensaje de estado
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Estado interno
        self.protocol_manager = ProtocolManager()
        self.selected_protocol_key = None
        self.current_protocol_name = "Ninguno"
        
        # Configurar UI
        self.setup_ui()
        
        # Cargar protocolos
        self.load_protocols_to_tree()
        
        # Configurar conexiones
        self.setup_connections()
        
        # Cargar iconos
        self.load_icons()
        
        # Estado inicial
        self.update_buttons_state()
        
        print("✅ ProtocolTreeWidget inicializado")
    
    def setup_ui(self):
        """Configurar interfaz de usuario"""
        
        # Layout principal vertical
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(8)
        
        # === TOOLBAR SUPERIOR ===
        self.create_toolbar(main_layout)
        
        # === TREE WIDGET ===
        self.create_tree_widget(main_layout)
        
        # === BOTÓN INICIAR ===
        self.create_action_button(main_layout)
    
    def create_toolbar(self, parent_layout):
        """Crear toolbar superior con botones de acción"""
        
        # Frame contenedor
        toolbar_frame = QFrame()
        toolbar_frame.setFrameStyle(QFrame.Box)
        toolbar_frame.setLineWidth(1)
        
        # Layout horizontal para botones
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setSpacing(5)
        toolbar_layout.setContentsMargins(5, 5, 5, 5)
        
        # Botón Copiar
        self.btn_copy = QPushButton("Copiar")
        self.btn_copy.setToolTip("Crear copia del protocolo seleccionado")
        self.btn_copy.setFixedHeight(30)
        toolbar_layout.addWidget(self.btn_copy)
        
        # Botón Editar
        self.btn_edit = QPushButton("Editar")
        self.btn_edit.setToolTip("Editar protocolo seleccionado")
        self.btn_edit.setFixedHeight(30)
        toolbar_layout.addWidget(self.btn_edit)
        
        # Botón Borrar
        self.btn_delete = QPushButton("Borrar")
        self.btn_delete.setToolTip("Eliminar protocolo personalizado")
        self.btn_delete.setFixedHeight(30)
        toolbar_layout.addWidget(self.btn_delete)
        
        # Spacer para empujar botones a la izquierda
        toolbar_layout.addStretch()
        
        parent_layout.addWidget(toolbar_frame)
    
    def create_tree_widget(self, parent_layout):
        """Crear TreeWidget para protocolos"""
        
        # TreeWidget
        self.tree_protocols = QTreeWidget()
        self.tree_protocols.setHeaderLabel("Protocolos Vestibulares")
        self.tree_protocols.setSelectionMode(QTreeWidget.SingleSelection)
        self.tree_protocols.setExpandsOnDoubleClick(False)
        self.tree_protocols.setAlternatingRowColors(True)
        
        # Configurar tamaño
        self.tree_protocols.setMinimumHeight(200)
        
        parent_layout.addWidget(self.tree_protocols)
    
    def create_action_button(self, parent_layout):
        """Crear botón de acción principal"""
        
        # Botón Iniciar Prueba
        self.btn_start_protocol = QPushButton("Iniciar Prueba")
        self.btn_start_protocol.setFixedHeight(40)
        self.btn_start_protocol.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
            QPushButton:pressed {
                background-color: #229954;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
                color: #7f8c8d;
            }
        """)
        
        parent_layout.addWidget(self.btn_start_protocol)
    
    def setup_connections(self):
        """Configurar conexiones de señales"""
        
        # TreeWidget
        self.tree_protocols.itemSelectionChanged.connect(self.on_selection_changed)
        self.tree_protocols.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        # Botones de toolbar
        self.btn_copy.clicked.connect(self.copy_protocol)
        self.btn_edit.clicked.connect(self.edit_protocol)
        self.btn_delete.clicked.connect(self.delete_protocol)
        
        # Botón de acción
        self.btn_start_protocol.clicked.connect(self.start_protocol)
    
    def load_icons(self):
        """Cargar iconos en botones"""
        try:
            # Iconos de toolbar
            self.btn_copy.setIcon(get_icon("copy", 16, IconColors.BLUE))
            self.btn_edit.setIcon(get_icon("file-pen-line", 16, IconColors.GREEN))
            self.btn_delete.setIcon(get_icon("trash-2", 16, IconColors.RED))
            
            # Icono de iniciar
            self.btn_start_protocol.setIcon(get_icon("play", 16, IconColors.WHITE))
            
            print("✅ Iconos del ProtocolTreeWidget cargados")
        except Exception as e:
            print(f"⚠️ Error cargando iconos del ProtocolTreeWidget: {e}")
    
    def load_protocols_to_tree(self):
        """Cargar protocolos desde JSON al TreeWidget"""
        
        # Limpiar tree
        self.tree_protocols.clear()
        
        if not self.protocol_manager.protocols_data:
            print("❌ No hay datos de protocolos para cargar")
            return
        
        ui_structure = self.protocol_manager.protocols_data.get("ui_tree_structure", {})
        all_protocols = self.protocol_manager.get_all_protocols()
        
        # Crear items padre basados en estructura UI
        parent_items = {}
        
        for key, structure in ui_structure.items():
            if structure.get("parent") is None:  # Es un item padre
                parent_item = QTreeWidgetItem(self.tree_protocols)
                parent_item.setText(0, structure["display_name"])
                parent_item.setData(0, Qt.UserRole, key)
                
                # Agregar icono si está disponible
                if "icon" in structure:
                    try:
                        icon = get_icon(structure["icon"], 16, IconColors.BLUE)
                        parent_item.setIcon(0, icon)
                    except:
                        pass
                
                parent_items[key] = parent_item
                
                # Agregar hijos si los tiene
                if "children" in structure:
                    for child in structure["children"]:
                        child_key = child["key"]
                        if child_key in all_protocols:
                            child_item = QTreeWidgetItem(parent_item)
                            child_item.setText(0, child["display_name"])
                            child_item.setData(0, Qt.UserRole, child_key)
                            
                            # Icono del hijo
                            if "icon" in child:
                                try:
                                    child_icon = get_icon(child["icon"], 16, IconColors.GREEN)
                                    child_item.setIcon(0, child_icon)
                                except:
                                    pass
                            
                            # Marcar si es preset personalizado
                            if not self.protocol_manager.is_default_protocol(child_key):
                                child_item.setText(0, f"{child['display_name']} *")
        
        # Agregar protocolos personalizados que no están en la estructura
        presets = self.protocol_manager.protocols_data.get("presets", {})
        for preset_key, preset in presets.items():
            # Verificar si ya está agregado
            if not self._find_item_by_key(preset_key):
                # Crear categoría "Personalizados" si no existe
                if "personalizados" not in parent_items:
                    custom_parent = QTreeWidgetItem(self.tree_protocols)
                    custom_parent.setText(0, "Protocolos Personalizados")
                    try:
                        custom_icon = get_icon("user", 16, IconColors.ORANGE)
                        custom_parent.setIcon(0, custom_icon)
                    except:
                        pass
                    parent_items["personalizados"] = custom_parent
                
                # Agregar preset
                preset_item = QTreeWidgetItem(parent_items["personalizados"])
                preset_item.setText(0, f"{preset['name']} *")
                preset_item.setData(0, Qt.UserRole, preset_key)
                try:
                    preset_icon = get_icon("file-pen-line", 16, IconColors.ORANGE)
                    preset_item.setIcon(0, preset_icon)
                except:
                    pass
        
        # Expandir todos los items
        self.tree_protocols.expandAll()
        
        print(f"✅ {len(all_protocols)} protocolos cargados en TreeWidget")
    
    def _find_item_by_key(self, protocol_key):
        """Buscar item en el tree por protocol_key"""
        for i in range(self.tree_protocols.topLevelItemCount()):
            parent = self.tree_protocols.topLevelItem(i)
            
            # Buscar en hijos
            for j in range(parent.childCount()):
                child = parent.child(j)
                if child.data(0, Qt.UserRole) == protocol_key:
                    return child
        return None
    
    def on_selection_changed(self):
        """Manejar cambio de selección"""
        selected_items = self.tree_protocols.selectedItems()
        
        if selected_items:
            item = selected_items[0]
            protocol_key = item.data(0, Qt.UserRole)
            
            if protocol_key:  # Es un protocolo, no una categoría
                self.selected_protocol_key = protocol_key
                protocol = self.protocol_manager.get_protocol(protocol_key)
                if protocol:
                    self.current_protocol_name = protocol["name"]
                    self.protocol_selected.emit(protocol_key)
                    self.protocol_changed.emit(f"Protocolo seleccionado: {self.current_protocol_name}")
                else:
                    self._clear_selection()
            else:
                self._clear_selection()
        else:
            self._clear_selection()
        
        self.update_buttons_state()
    
    def _clear_selection(self):
        """Limpiar selección interna"""
        self.selected_protocol_key = None
        self.current_protocol_name = "Ninguno"
    
    def on_item_double_clicked(self, item, column):
        """Manejar doble click en item"""
        protocol_key = item.data(0, Qt.UserRole)
        if protocol_key and self.selected_protocol_key:
            # Doble click actúa como "iniciar protocolo"
            self.start_protocol()
    
    def update_buttons_state(self):
        """Actualizar estado de botones según selección"""
        has_selection = self.selected_protocol_key is not None
        is_default = False
        
        if has_selection:
            is_default = self.protocol_manager.is_default_protocol(self.selected_protocol_key)
        
        # Botones de toolbar
        self.btn_copy.setEnabled(has_selection)
        self.btn_edit.setEnabled(has_selection)
        self.btn_delete.setEnabled(has_selection and not is_default)
        
        # Botón de acción
        self.btn_start_protocol.setEnabled(has_selection)
        
        # Actualizar tooltips
        if not has_selection:
            self.btn_copy.setToolTip("Seleccione un protocolo para copiar")
            self.btn_edit.setToolTip("Seleccione un protocolo para editar")
            self.btn_delete.setToolTip("Seleccione un protocolo personalizado para eliminar")
            self.btn_start_protocol.setToolTip("Seleccione un protocolo para iniciar")
        elif is_default:
            self.btn_delete.setToolTip("No se pueden eliminar protocolos estándar")
            self.btn_start_protocol.setToolTip(f"Iniciar: {self.current_protocol_name}")
        else:
            self.btn_copy.setToolTip("Crear copia del protocolo seleccionado")
            self.btn_edit.setToolTip("Editar protocolo seleccionado")
            self.btn_delete.setToolTip("Eliminar protocolo personalizado")
            self.btn_start_protocol.setToolTip(f"Iniciar: {self.current_protocol_name}")
    
    def copy_protocol(self):
        """Copiar protocolo seleccionado"""
        if not self.selected_protocol_key:
            return
        
        # Pedir nombre para la copia
        name, ok = QInputDialog.getText(
            self, 
            "Copiar Protocolo",
            f"Nombre para la copia de '{self.current_protocol_name}':",
            text=f"{self.current_protocol_name} - Copia"
        )
        
        if ok and name.strip():
            new_key = self.protocol_manager.copy_protocol(self.selected_protocol_key, name.strip())
            if new_key:
                # Guardar protocolos
                self.protocol_manager.save_protocols()
                
                # Recargar TreeWidget
                self.load_protocols_to_tree()
                
                # Seleccionar el nuevo protocolo
                self.select_protocol_by_key(new_key)
                
                self.protocol_changed.emit(f"Protocolo copiado: {name.strip()}")
            else:
                QMessageBox.warning(self, "Error", "No se pudo copiar el protocolo")
    
    def edit_protocol(self):
        """Editar protocolo seleccionado"""
        if not self.selected_protocol_key:
            return
        
        protocol = self.protocol_manager.get_protocol(self.selected_protocol_key)
        if not protocol:
            return
        
        # TODO: Abrir ventana de configuración específica
        # Por ahora, mostrar información del protocolo
        QMessageBox.information(
            self,
            "Editar Protocolo",
            f"Protocolo: {protocol['name']}\n"
            f"Tipo: {protocol.get('behavior_type', 'N/A')}\n"
            f"Categoría: {protocol.get('category', 'N/A')}\n"
            f"Duración máx: {protocol.get('duration_max', 'N/A')} seg\n\n"
            f"[Ventana de configuración en desarrollo]"
        )
    
    def delete_protocol(self):
        """Eliminar protocolo seleccionado"""
        if not self.selected_protocol_key:
            return
        
        if self.protocol_manager.is_default_protocol(self.selected_protocol_key):
            QMessageBox.warning(
                self,
                "No Permitido", 
                "No se pueden eliminar protocolos estándar."
            )
            return
        
        # Confirmar eliminación
        reply = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Está seguro de que desea eliminar el protocolo '{self.current_protocol_name}'?\n\n"
            f"Esta acción no se puede deshacer.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.protocol_manager.delete_protocol(self.selected_protocol_key):
                # Guardar cambios
                self.protocol_manager.save_protocols()
                
                # Recargar TreeWidget
                self.load_protocols_to_tree()
                
                # Limpiar selección
                self._clear_selection()
                self.update_buttons_state()
                
                self.protocol_changed.emit("Protocolo eliminado correctamente")
            else:
                QMessageBox.critical(self, "Error", "No se pudo eliminar el protocolo")
    
    def start_protocol(self):
        """Iniciar protocolo seleccionado"""
        if not self.selected_protocol_key:
            QMessageBox.warning(
                self,
                "Protocolo No Seleccionado",
                "Debe seleccionar un protocolo antes de iniciar la prueba.\n\n"
                "Seleccione un protocolo de la lista o haga doble click sobre él."
            )
            return
        
        protocol = self.protocol_manager.get_protocol(self.selected_protocol_key)
        if not protocol:
            QMessageBox.critical(
                self,
                "Error",
                "No se pudo cargar el protocolo seleccionado."
            )
            return
        
        # Emitir señal para que el main ejecute el protocolo
        self.protocol_execution_requested.emit(protocol)
        self.protocol_changed.emit(f"Iniciando: {protocol['name']}")
    
    def select_protocol_by_key(self, protocol_key):
        """Seleccionar protocolo específico por clave"""
        item = self._find_item_by_key(protocol_key)
        if item:
            self.tree_protocols.setCurrentItem(item)
            return True
        return False
    
    def get_selected_protocol(self):
        """Obtener protocolo actualmente seleccionado"""
        if self.selected_protocol_key:
            return self.protocol_manager.get_protocol(self.selected_protocol_key)
        return None
    
    def get_selected_protocol_key(self):
        """Obtener clave del protocolo seleccionado"""
        return self.selected_protocol_key
    
    def refresh_protocols(self):
        """Recargar protocolos desde archivo"""
        self.protocol_manager.load_protocols()
        self.load_protocols_to_tree()
        self.protocol_changed.emit("Protocolos recargados")
    
    def get_protocols_count(self):
        """Obtener número total de protocolos"""
        return len(self.protocol_manager.get_all_protocols())