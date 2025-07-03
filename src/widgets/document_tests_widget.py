#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Document Tests Widget - TreeWidget para mostrar pruebas realizadas del documento actual
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, 
                              QTreeWidgetItem, QPushButton, QLabel, QFrame,
                              QMessageBox, QMenu)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QAction
from utils.icon_utils import get_icon, IconColors
from utils.dialog_utils import ask_delete_confirmation


class DocumentTestsWidget(QWidget):
    """
    Widget para mostrar y gestionar las pruebas realizadas en el documento actual.
    Se muestra debajo del ProtocolTreeWidget cuando hay un documento abierto.
    """
    
    # Señales
    test_selected = Signal(str, dict)  # test_id, test_data
    test_view_requested = Signal(str, dict)  # test_id, test_data
    test_delete_requested = Signal(str)  # test_id
    test_export_requested = Signal(str, dict)  # test_id, test_data
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Estado
        self.tests_data = {}
        self.selected_test_id = None
        self.document_manager = None
        
        # Setup UI
        self.setup_ui()
        self.setup_connections()
        
        # Estado inicial
        self.update_buttons_state()
        
        print("✅ DocumentTestsWidget inicializado")
    
    def setup_ui(self):
        """Configurar interfaz de usuario"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(8)
        
        # === HEADER ===
        self.create_header(main_layout)
        
        # === TREE WIDGET ===
        self.create_tree_widget(main_layout)
        
        # === TOOLBAR ===
        self.create_toolbar(main_layout)
        
        # Aplicar estilos
        self.apply_styles()
    
    def create_header(self, parent_layout):
        """Crear header del widget"""
        header_layout = QHBoxLayout()
        
        # Icono y título
        icon_label = QLabel()
        icon_label.setFixedSize(20, 20)
        icon = get_icon("file-text", 20, IconColors.GREEN)
        icon_label.setPixmap(icon.pixmap(20, 20))
        header_layout.addWidget(icon_label)
        
        self.title_label = QLabel("Pruebas Realizadas")
        self.title_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.title_label.setStyleSheet("color: #2c3e50;")
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        # Contador de pruebas
        self.count_label = QLabel("0 pruebas")
        self.count_label.setStyleSheet("color: #7f8c8d; font-size: 9px;")
        header_layout.addWidget(self.count_label)
        
        parent_layout.addLayout(header_layout)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("color: #bdc3c7;")
        parent_layout.addWidget(separator)
    
    def create_tree_widget(self, parent_layout):
        """Crear TreeWidget para mostrar pruebas"""
        self.tree_tests = QTreeWidget()
        self.tree_tests.setHeaderLabel("Pruebas del Documento")
        self.tree_tests.setSelectionMode(QTreeWidget.SingleSelection)
        self.tree_tests.setAlternatingRowColors(True)
        self.tree_tests.setRootIsDecorated(False)
        self.tree_tests.setIndentation(10)
        
        # Configurar tamaño
        self.tree_tests.setMinimumHeight(150)
        self.tree_tests.setMaximumHeight(300)
        
        # Menú contextual
        self.tree_tests.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_tests.customContextMenuRequested.connect(self.show_context_menu)
        
        parent_layout.addWidget(self.tree_tests)
    
    def create_toolbar(self, parent_layout):
        """Crear toolbar con botones de acción"""
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(5)
        
        # Botón Ver
        self.btn_view = QPushButton("Ver")
        self.btn_view.setToolTip("Ver resultados de la prueba seleccionada")
        self.btn_view.setIcon(get_icon("eye", 14, IconColors.WHITE))
        self.btn_view.setFixedHeight(28)
        toolbar_layout.addWidget(self.btn_view)
        
        # Botón Exportar
        self.btn_export = QPushButton("Exportar")
        self.btn_export.setToolTip("Exportar datos de la prueba")
        self.btn_export.setIcon(get_icon("download", 14, IconColors.WHITE))
        self.btn_export.setFixedHeight(28)
        toolbar_layout.addWidget(self.btn_export)
        
        # Spacer
        toolbar_layout.addStretch()
        
        # Botón Eliminar
        self.btn_delete = QPushButton("Eliminar")
        self.btn_delete.setToolTip("Eliminar prueba seleccionada")
        self.btn_delete.setIcon(get_icon("trash-2", 14, IconColors.WHITE))
        self.btn_delete.setFixedHeight(28)
        toolbar_layout.addWidget(self.btn_delete)
        
        parent_layout.addLayout(toolbar_layout)
    
    def setup_connections(self):
        """Configurar conexiones de señales"""
        # TreeWidget
        self.tree_tests.itemSelectionChanged.connect(self.on_selection_changed)
        self.tree_tests.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        # Botones
        self.btn_view.clicked.connect(self.view_selected_test)
        self.btn_export.clicked.connect(self.export_selected_test)
        self.btn_delete.clicked.connect(self.delete_selected_test)
    
    def apply_styles(self):
        """Aplicar estilos CSS"""
        self.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background-color: white;
                selection-background-color: #3498db;
                alternate-background-color: #f8f9fa;
            }
            QTreeWidget::item {
                padding: 4px;
                border-bottom: 1px solid #ecf0f1;
            }
            QTreeWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
            QTreeWidget::item:hover {
                background-color: #ebf3fd;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 3px;
                font-weight: bold;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
                color: #7f8c8d;
            }
        """)
        
        # Estilo específico para botón eliminar
        self.btn_delete.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
                color: #7f8c8d;
            }
        """)
    
    def set_document_manager(self, document_manager):
        """Establecer referencia al DocumentManager"""
        self.document_manager = document_manager
        
        if document_manager:
            # Conectar señales del DocumentManager
            document_manager.test_added.connect(self.on_test_added)
            document_manager.test_removed.connect(self.on_test_removed)
            document_manager.document_loaded.connect(self.on_document_loaded)
    
    def load_tests(self, tests_data: Dict[str, Dict[str, Any]]):
        """
        Cargar pruebas en el TreeWidget.
        
        Args:
            tests_data: Diccionario con datos de las pruebas
        """
        self.tests_data = tests_data.copy()
        self.refresh_tree()
    
    def refresh_tree(self):
        """Refrescar el TreeWidget con los datos actuales"""
        self.tree_tests.clear()
        
        if not self.tests_data:
            # Mostrar mensaje cuando no hay pruebas
            no_tests_item = QTreeWidgetItem(self.tree_tests)
            no_tests_item.setText(0, "No hay pruebas realizadas")
            no_tests_item.setIcon(0, get_icon("info", 16, IconColors.GRAY))
            no_tests_item.setDisabled(True)
            no_tests_item.setData(0, Qt.UserRole, None)
        else:
            # Ordenar pruebas por timestamp (más reciente primero)
            sorted_tests = sorted(
                self.tests_data.items(),
                key=lambda x: x[1].get("timestamp", ""),
                reverse=True
            )
            
            for test_id, test_data in sorted_tests:
                self.add_test_item(test_id, test_data)
        
        # Actualizar contador
        self.update_count_label()
        
        # Actualizar estado de botones
        self.update_buttons_state()
    
    def add_test_item(self, test_id: str, test_data: Dict[str, Any]):
        """Agregar item de prueba al tree"""
        item = QTreeWidgetItem(self.tree_tests)
        
        # Datos de la prueba
        protocol_name = test_data.get("protocol_name", "Protocolo desconocido")
        timestamp = test_data.get("timestamp", "")
        status = test_data.get("status", "unknown")
        
        # Formatear timestamp
        formatted_time = self.format_timestamp(timestamp)
        
        # Texto del item
        item_text = f"{protocol_name} - {formatted_time}"
        item.setText(0, item_text)
        
        # Icono según tipo de protocolo
        icon_name = self.get_protocol_icon(test_data)
        item.setIcon(0, get_icon(icon_name, 16, IconColors.GREEN))
        
        # Tooltip con información adicional
        tooltip = self.build_test_tooltip(test_data)
        item.setToolTip(0, tooltip)
        
        # Guardar datos en el item
        item.setData(0, Qt.UserRole, test_id)
        
        # Estilo según estado
        if status != "completed":
            item.setForeground(0, "#e74c3c")  # Rojo para pruebas incompletas
    
    def format_timestamp(self, timestamp: str) -> str:
        """Formatear timestamp para mostrar"""
        try:
            dt = datetime.fromisoformat(timestamp)
            return dt.strftime("%d/%m/%Y %H:%M")
        except:
            return "Fecha desconocida"
    
    def get_protocol_icon(self, test_data: Dict[str, Any]) -> str:
        """Obtener icono según tipo de protocolo"""
        protocol_name = test_data.get("protocol_name", "").lower()
        
        if "calorica" in protocol_name or "calórica" in protocol_name:
            return "thermometer"
        elif "sacada" in protocol_name:
            return "zap"
        elif "seguimiento" in protocol_name:
            return "move"
        elif "optoq" in protocol_name:
            return "repeat"
        elif "romberg" in protocol_name or "equilibrio" in protocol_name:
            return "footprints"
        elif "dix" in protocol_name or "posicional" in protocol_name:
            return "rotate-3d"
        else:
            return "circle-check"
    
    def build_test_tooltip(self, test_data: Dict[str, Any]) -> str:
        """Construir tooltip con información de la prueba"""
        protocol_name = test_data.get("protocol_name", "Desconocido")
        timestamp = test_data.get("timestamp", "")
        status = test_data.get("status", "unknown")
        
        formatted_time = self.format_timestamp(timestamp)
        
        tooltip = f"""Protocolo: {protocol_name}
Fecha: {formatted_time}
Estado: {status}
ID: {test_data.get('test_id', 'N/A')}"""
        
        # Agregar información adicional si está disponible
        data = test_data.get("data", {})
        if "duration" in data:
            tooltip += f"\nDuración: {data['duration']:.1f}s"
        
        return tooltip
    
    def update_count_label(self):
        """Actualizar etiqueta de contador"""
        count = len(self.tests_data)
        if count == 0:
            self.count_label.setText("Sin pruebas")
        elif count == 1:
            self.count_label.setText("1 prueba")
        else:
            self.count_label.setText(f"{count} pruebas")
    
    def update_buttons_state(self):
        """Actualizar estado de botones según selección"""
        has_selection = self.selected_test_id is not None
        has_valid_selection = has_selection and self.selected_test_id in self.tests_data
        
        self.btn_view.setEnabled(has_valid_selection)
        self.btn_export.setEnabled(has_valid_selection)
        self.btn_delete.setEnabled(has_valid_selection)
        
        # Actualizar tooltips
        if not has_valid_selection:
            self.btn_view.setToolTip("Seleccione una prueba para ver")
            self.btn_export.setToolTip("Seleccione una prueba para exportar")
            self.btn_delete.setToolTip("Seleccione una prueba para eliminar")
        else:
            test_data = self.tests_data.get(self.selected_test_id, {})
            protocol_name = test_data.get("protocol_name", "Prueba")
            
            self.btn_view.setToolTip(f"Ver resultados: {protocol_name}")
            self.btn_export.setToolTip(f"Exportar: {protocol_name}")
            self.btn_delete.setToolTip(f"Eliminar: {protocol_name}")
    
    def on_selection_changed(self):
        """Manejar cambio de selección"""
        selected_items = self.tree_tests.selectedItems()
        
        if selected_items:
            item = selected_items[0]
            test_id = item.data(0, Qt.UserRole)
            
            if test_id and test_id in self.tests_data:
                self.selected_test_id = test_id
                test_data = self.tests_data[test_id]
                self.test_selected.emit(test_id, test_data)
            else:
                self.selected_test_id = None
        else:
            self.selected_test_id = None
        
        self.update_buttons_state()
    
    def on_item_double_clicked(self, item, column):
        """Manejar doble click en item"""
        test_id = item.data(0, Qt.UserRole)
        if test_id and test_id in self.tests_data:
            self.view_selected_test()
    
    def view_selected_test(self):
        """Ver prueba seleccionada"""
        if self.selected_test_id and self.selected_test_id in self.tests_data:
            test_data = self.tests_data[self.selected_test_id]
            self.test_view_requested.emit(self.selected_test_id, test_data)
    
    def export_selected_test(self):
        """Exportar prueba seleccionada"""
        if self.selected_test_id and self.selected_test_id in self.tests_data:
            test_data = self.tests_data[self.selected_test_id]
            self.test_export_requested.emit(self.selected_test_id, test_data)
    
    def delete_selected_test(self):
        """Eliminar prueba seleccionada"""
        if not self.selected_test_id or self.selected_test_id not in self.tests_data:
            return
        
        test_data = self.tests_data[self.selected_test_id]
        protocol_name = test_data.get("protocol_name", "Prueba")
        timestamp = self.format_timestamp(test_data.get("timestamp", ""))
        
        # Confirmar eliminación
        if ask_delete_confirmation(f"{protocol_name} - {timestamp}", self):
            self.test_delete_requested.emit(self.selected_test_id)
    
    def show_context_menu(self, position):
        """Mostrar menú contextual"""
        item = self.tree_tests.itemAt(position)
        if not item:
            return
        
        test_id = item.data(0, Qt.UserRole)
        if not test_id or test_id not in self.tests_data:
            return
        
        menu = QMenu(self)
        
        # Acción Ver
        view_action = QAction("Ver Resultados", self)
        view_action.setIcon(get_icon("eye", 16, IconColors.BLUE))
        view_action.triggered.connect(self.view_selected_test)
        menu.addAction(view_action)
        
        # Acción Exportar
        export_action = QAction("Exportar Datos", self)
        export_action.setIcon(get_icon("download", 16, IconColors.GREEN))
        export_action.triggered.connect(self.export_selected_test)
        menu.addAction(export_action)
        
        menu.addSeparator()
        
        # Acción Eliminar
        delete_action = QAction("Eliminar Prueba", self)
        delete_action.setIcon(get_icon("trash-2", 16, IconColors.RED))
        delete_action.triggered.connect(self.delete_selected_test)
        menu.addAction(delete_action)
        
        menu.exec(self.tree_tests.mapToGlobal(position))
    
    # === MANEJADORES DE SEÑALES DEL DOCUMENTMANAGER ===
    
    def on_test_added(self, test_data: Dict[str, Any]):
        """Manejar prueba agregada al documento"""
        test_id = test_data.get("test_id")
        if test_id:
            self.tests_data[test_id] = test_data
            self.refresh_tree()
    
    def on_test_removed(self, test_id: str):
        """Manejar prueba eliminada del documento"""
        if test_id in self.tests_data:
            del self.tests_data[test_id]
            
            # Si era la seleccionada, limpiar selección
            if self.selected_test_id == test_id:
                self.selected_test_id = None
            
            self.refresh_tree()
    
    def on_document_loaded(self, metadata: Dict[str, Any]):
        """Manejar documento cargado"""
        if self.document_manager:
            # Cargar todas las pruebas del documento
            all_tests = self.document_manager.get_all_tests()
            self.load_tests(all_tests)
    
    def clear(self):
        """Limpiar widget (cuando se cierra documento)"""
        self.tests_data = {}
        self.selected_test_id = None
        self.refresh_tree()
    
    def get_selected_test_id(self) -> Optional[str]:
        """Obtener ID de la prueba seleccionada"""
        return self.selected_test_id
    
    def get_selected_test_data(self) -> Optional[Dict[str, Any]]:
        """Obtener datos de la prueba seleccionada"""
        if self.selected_test_id:
            return self.tests_data.get(self.selected_test_id)
        return None