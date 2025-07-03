#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI Loader - Gestor genérico para carga y acceso a elementos UI
Proporciona interfaz limpia para cargar archivos .ui y acceder a widgets
"""

import os
from typing import Optional, Dict, Any, List, Type
from PySide6.QtWidgets import QWidget, QLayout, QPushButton, QLabel, QCheckBox, QGroupBox, QFrame
from PySide6.QtCore import QFile
from PySide6.QtUiTools import QUiLoader


def inspect_ui_widgets(widget, level=0):
    """Función para inspeccionar estructura de widgets"""
    indent = "  " * level
    print(f"{indent}{widget.__class__.__name__}: {widget.objectName()}")
    
    for child in widget.findChildren(QWidget):
        if child.parent() == widget:  # Solo hijos directos
            inspect_ui_widgets(child, level + 1)


class UILoader:
    """
    Gestor genérico para carga y acceso a elementos UI.
    Carga automáticamente el archivo .ui y proporciona acceso limpio a widgets.
    """
    
    def __init__(self, ui_file_path: str, search_paths: List[str] = None, auto_inspect: bool = False):
        """
        Inicializar y cargar UI automáticamente
        
        Args:
            ui_file_path: Ruta al archivo .ui
            search_paths: Rutas adicionales de búsqueda
            auto_inspect: Si mostrar automáticamente la estructura del UI
        """
        self.ui = None
        self.ui_path = None
        self.auto_inspect = auto_inspect
        
        # Cache de widgets encontrados
        self._widget_cache = {}
        self._layout_cache = {}
        
        # Cargar UI automáticamente
        self._load_ui(ui_file_path, search_paths)
    
    def _load_ui(self, ui_file_path: str, search_paths: List[str] = None) -> bool:
        """
        Cargar archivo .ui con búsqueda en múltiples rutas
        
        Args:
            ui_file_path: Ruta al archivo .ui
            search_paths: Rutas adicionales de búsqueda
        
        Returns:
            bool: True si se cargó exitosamente
        """
        try:
            # Rutas por defecto
            default_paths = [
                ui_file_path,
                os.path.join("src", ui_file_path),
                os.path.join("src", "ui", ui_file_path),
                os.path.join("ui", ui_file_path),
                os.path.join(".", ui_file_path)
            ]
            
            # Agregar rutas personalizadas
            if search_paths:
                default_paths.extend(search_paths)
            
            # Buscar archivo existente
            self.ui_path = None
            for path in default_paths:
                if os.path.exists(path):
                    self.ui_path = path
                    break
            
            if not self.ui_path:
                print("❌ No se encontró archivo UI en ninguna ruta")
                print(f"   Rutas buscadas: {default_paths}")
                raise FileNotFoundError(f"No se encontró {ui_file_path}")
            
            # Cargar UI
            ui_file = QFile(self.ui_path)
            if not ui_file.open(QFile.ReadOnly):
                raise IOError(f"No se puede abrir el archivo: {self.ui_path}")
            
            loader = QUiLoader()
            self.ui = loader.load(ui_file)
            ui_file.close()
            
            if not self.ui:
                raise ValueError(f"Error cargando UI desde: {self.ui_path}")
            
            # Inspeccionar estructura si está habilitado
            if self.auto_inspect:
                print(f"📋 Estructura UI cargado desde: {self.ui_path}")
                inspect_ui_widgets(self.ui)
            
            print(f"✅ UI cargado desde: {self.ui_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error cargando UI: {e}")
            self.ui = None
            self.ui_path = None
            raise
    
    # ===== MÉTODOS DE ACCESO A WIDGETS =====
    
    def widget(self, name: str) -> Optional[QWidget]:
        """
        Acceso directo a widget por nombre
        
        Args:
            name: Nombre del widget (objectName)
        
        Returns:
            Widget encontrado o None
        """
        if not self.ui:
            return None
        
        # Acceso directo a propiedades principales de QMainWindow
        if hasattr(self.ui, name):
            return getattr(self.ui, name)
        
        # Buscar por findChild
        return self.find_widget(name)
    
    def find_widget(self, name: str, widget_type: Type = QWidget) -> Optional[QWidget]:
        """
        Buscar widget por nombre y tipo (con cache)
        
        Args:
            name: Nombre del objeto (objectName)
            widget_type: Tipo de widget a buscar
        
        Returns:
            Widget encontrado o None
        """
        if not self.ui:
            return None
        
        # Usar cache si existe
        cache_key = f"{name}_{widget_type.__name__}"
        if cache_key in self._widget_cache:
            return self._widget_cache[cache_key]
        
        # Buscar widget
        widget = self.ui.findChild(widget_type, name)
        
        # Cachear resultado (incluso si es None)
        self._widget_cache[cache_key] = widget
        
        return widget
    
    def find_layout(self, name: str, layout_type: Type = QLayout) -> Optional[QLayout]:
        """
        Buscar layout por nombre y tipo (con cache)
        
        Args:
            name: Nombre del objeto (objectName)
            layout_type: Tipo de layout a buscar
        
        Returns:
            Layout encontrado o None
        """
        if not self.ui:
            return None
        
        # Usar cache si existe
        cache_key = f"{name}_{layout_type.__name__}"
        if cache_key in self._layout_cache:
            return self._layout_cache[cache_key]
        
        # Buscar layout
        layout = self.ui.findChild(layout_type, name)
        
        # Cachear resultado
        self._layout_cache[cache_key] = layout
        
        return layout
    
    def find_all_widgets(self, widget_type: Type = QWidget) -> List[QWidget]:
        """
        Encontrar todos los widgets de un tipo específico
        
        Args:
            widget_type: Tipo de widget a buscar
        
        Returns:
            Lista de widgets encontrados
        """
        if not self.ui:
            return []
        
        return self.ui.findChildren(widget_type)
    
    # ===== MÉTODOS DE CONVENIENCIA =====
    
    def button(self, name: str) -> Optional[QPushButton]:
        """Buscar botón específicamente"""
        return self.find_widget(name, QPushButton)
    
    def label(self, name: str) -> Optional[QLabel]:
        """Buscar label específicamente"""
        return self.find_widget(name, QLabel)
    
    def checkbox(self, name: str) -> Optional[QCheckBox]:
        """Buscar checkbox específicamente"""
        return self.find_widget(name, QCheckBox)
    
    def groupbox(self, name: str) -> Optional[QGroupBox]:
        """Buscar groupbox específicamente"""
        return self.find_widget(name, QGroupBox)
    
    def frame(self, name: str) -> Optional[QFrame]:
        """Buscar frame específicamente"""
        return self.find_widget(name, QFrame)
    
    # ===== MÉTODOS DE INFORMACIÓN =====
    
    def has_widget(self, name: str, widget_type: Type = QWidget) -> bool:
        """Verificar si existe un widget"""
        return self.find_widget(name, widget_type) is not None
    
    def has_layout(self, name: str, layout_type: Type = QLayout) -> bool:
        """Verificar si existe un layout"""
        return self.find_layout(name, layout_type) is not None
    
    def get_widget_info(self, name: str) -> Dict[str, Any]:
        """
        Obtener información completa de un widget
        
        Args:
            name: Nombre del widget
        
        Returns:
            Diccionario con información del widget
        """
        widget = self.find_widget(name)
        
        if not widget:
            return {'exists': False, 'name': name}
        
        return {
            'exists': True,
            'name': name,
            'type': widget.__class__.__name__,
            'object_name': widget.objectName(),
            'enabled': widget.isEnabled(),
            'visible': widget.isVisible(),
            'parent': widget.parent().__class__.__name__ if widget.parent() else None
        }
    
    def list_all_widgets(self) -> Dict[str, List[str]]:
        """
        Listar todos los widgets por tipo
        
        Returns:
            Diccionario con tipos de widget y sus nombres
        """
        if not self.ui:
            return {}
        
        widget_types = {}
        all_widgets = self.ui.findChildren(QWidget)
        
        for widget in all_widgets:
            widget_type = widget.__class__.__name__
            if widget_type not in widget_types:
                widget_types[widget_type] = []
            
            object_name = widget.objectName()
            if object_name:  # Solo widgets con nombre
                widget_types[widget_type].append(object_name)
        
        return widget_types
    
    def inspect_structure(self):
        """Mostrar estructura completa del UI"""
        if not self.ui:
            print("❌ No hay UI cargado")
            return
        
        print("=== ESTRUCTURA UI ===")
        inspect_ui_widgets(self.ui)
    
    def debug_info(self):
        """Mostrar información completa del UI para debug"""
        if not self.ui:
            print("❌ No hay UI cargado")
            return
        
        print("=== DEBUG UI INFO ===")
        print(f"UI Path: {self.ui_path}")
        print(f"UI Type: {self.ui.__class__.__name__}")
        print(f"UI Object Name: {self.ui.objectName()}")
        
        print(f"\n--- Elementos principales ---")
        main_elements = ['centralwidget', 'menubar', 'statusbar']
        for element in main_elements:
            exists = self.widget(element) is not None
            print(f"{element}: {'✅' if exists else '❌'}")
        
        print(f"\n--- TEST DIRECTO FINDCHILD vs FINDCHILDREN ---")
        # Test directo para frame_left_panel
        test_names = ['frame_left_panel', 'frame_central_panel', 'frame_right_panel']
        
        for name in test_names:
            # Test con findChild
            child_result = self.ui.findChild(QFrame, name)
            children_result = [w for w in self.ui.findChildren(QFrame) if w.objectName() == name]
            
            print(f"{name}:")
            print(f"  findChild(QFrame): {child_result}")
            print(f"  findChildren(QFrame) filtrado: {children_result}")
            
            # Test también como QWidget
            child_widget = self.ui.findChild(QWidget, name)
            print(f"  findChild(QWidget): {child_widget}")
        
        print(f"\n--- Todos los widgets por tipo ---")
        widget_types = self.list_all_widgets()
        for widget_type, names in widget_types.items():
            print(f"{widget_type}: {names}")
    
    def is_loaded(self) -> bool:
        """Verificar si el UI está cargado correctamente"""
        return self.ui is not None and self.ui_path is not None
    
    def clear_cache(self):
        """Limpiar cache de widgets y layouts"""
        self._widget_cache.clear()
        self._layout_cache.clear()
        print("🧹 Cache de UI limpiado")
    
    # ===== PROPIEDADES =====
    
    @property
    def root(self) -> Optional[QWidget]:
        """Obtener widget raíz del UI"""
        return self.ui
    
    @property
    def path(self) -> Optional[str]:
        """Obtener ruta del archivo UI cargado"""
        return self.ui_path
