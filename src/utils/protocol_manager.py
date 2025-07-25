import time
from datetime import datetime
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, 
                            QPushButton, QLabel, QMessageBox, QTreeWidgetItem)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class EvaluatorDialog(QDialog):
    """Diálogo simple para ingresar/cambiar evaluador"""
    
    def __init__(self, current_evaluator=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Evaluador/a")
        self.setModal(True)
        self.resize(350, 150)
        
        self.evaluator_name = None
        self.setup_ui(current_evaluator)
    
    def setup_ui(self, current_evaluator):
        """Configurar interfaz del diálogo"""
        layout = QVBoxLayout(self)
        
        # Título
        title_label = QLabel("Nombre del Evaluador/a:")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Input del evaluador
        self.evaluator_input = QLineEdit()
        self.evaluator_input.setPlaceholderText("Ingrese nombre completo del evaluador/a")
        if current_evaluator:
            self.evaluator_input.setText(current_evaluator)
        layout.addWidget(self.evaluator_input)
        
        # Botones
        button_layout = QHBoxLayout()
        
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_accept = QPushButton("Aceptar")
        self.btn_accept.setDefault(True)
        
        # Estilo para el botón principal
        self.btn_accept.setStyleSheet("""
            QPushButton {
                background-color: #007ACC;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #005A9B;
            }
        """)
        
        button_layout.addStretch()
        button_layout.addWidget(self.btn_cancel)
        button_layout.addWidget(self.btn_accept)
        
        layout.addLayout(button_layout)
        
        # Conectar señales
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_accept.clicked.connect(self.accept_evaluator)
        self.evaluator_input.textChanged.connect(self.validate_input)
        self.evaluator_input.returnPressed.connect(self.accept_evaluator)
        
        # Validación inicial
        self.validate_input()
    
    def validate_input(self):
        """Validar entrada en tiempo real"""
        text = self.evaluator_input.text().strip()
        self.btn_accept.setEnabled(len(text) >= 2)
    
    def accept_evaluator(self):
        """Aceptar evaluador"""
        evaluator = self.evaluator_input.text().strip()
        if len(evaluator) >= 2:
            self.evaluator_name = evaluator
            self.accept()
        else:
            QMessageBox.warning(self, "Nombre inválido", "El nombre debe tener al menos 2 caracteres")
    
    def get_evaluator_name(self):
        """Obtener nombre del evaluador"""
        return self.evaluator_name


class ProtocolManager:
    """
    Gestor de protocolos y pruebas del sistema VNG.
    Maneja la creación, seguimiento y persistencia de pruebas.
    """
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.current_evaluator = None
        
        # Mapeo de protocolos
        self.protocol_names = {
            "OD_44": "OD 44°C",
            "OI_44": "OI 44°C", 
            "OD_37": "OD 37°C",
            "OI_37": "OI 37°C",
            "seguimiento_lento": "Seguimiento Lento",
            "optoquinetico": "Optoquinético",
            "sacadas": "Sacadas",
            "espontaneo": "Espontáneo"
        }
    
    def open_protocol_dialog(self, protocol_type):
        """
        Abrir diálogo de protocolo - punto de entrada principal
        
        Args:
            protocol_type: Tipo de protocolo (ej: "OD_44", "seguimiento_lento")
        """
        try:
            # Verificar que hay usuario actual
            if not self.main_window.current_user_siev:
                QMessageBox.warning(
                    self.main_window,
                    "Sin Usuario",
                    "Debe crear o abrir un usuario antes de iniciar una prueba."
                )
                return
            
            # Verificar evaluador
            if not self.current_evaluator:
                if not self.ask_for_evaluator():
                    return  # Usuario canceló
            
            # Crear nueva prueba
            self.create_new_test(protocol_type)
            
        except Exception as e:
            QMessageBox.critical(
                self.main_window, 
                "Error", 
                f"Error abriendo protocolo: {e}"
            )
            print(f"Error en open_protocol_dialog: {e}")
    
    def ask_for_evaluator(self):
        """
        Pedir nombre del evaluador
        
        Returns:
            bool: True si se ingresó evaluador, False si se canceló
        """
        try:
            dialog = EvaluatorDialog(self.current_evaluator, self.main_window)
            
            if dialog.exec() == QDialog.Accepted:
                self.current_evaluator = dialog.get_evaluator_name()
                print(f"Evaluador establecido: {self.current_evaluator}")
                return True
            else:
                return False
                
        except Exception as e:
            print(f"Error pidiendo evaluador: {e}")
            return False
    
    def change_evaluator(self):
        """Cambiar evaluador actual"""
        try:
            dialog = EvaluatorDialog(self.current_evaluator, self.main_window)
            
            if dialog.exec() == QDialog.Accepted:
                old_evaluator = self.current_evaluator
                self.current_evaluator = dialog.get_evaluator_name()
                
                QMessageBox.information(
                    self.main_window,
                    "Evaluador Cambiado",
                    f"Evaluador cambiado de:\n'{old_evaluator}'\na:\n'{self.current_evaluator}'"
                )
                
                print(f"Evaluador cambiado: {old_evaluator} → {self.current_evaluator}")
                
        except Exception as e:
            QMessageBox.critical(
                self.main_window,
                "Error",
                f"Error cambiando evaluador: {e}"
            )
    
    def create_new_test(self, protocol_type):
        """
        Crear nueva prueba y agregarla al tree y al .siev
        
        Args:
            protocol_type: Tipo de protocolo
        """
        try:
            # Generar datos de la prueba
            test_data = {
                "tipo": self.protocol_names.get(protocol_type, protocol_type),
                "protocolo_id": protocol_type,
                "fecha": time.time(),
                "hora_inicio": None,  # Se establecerá cuando inicie
                "hora_fin": None,     # Se establecerá cuando termine
                "evaluador": self.current_evaluator,
                "comentarios": None,  # Se establecerá al final
                "estado": "pendiente"
            }
            
            # Agregar al .siev
            test_id = self.add_test_to_siev(test_data)
            if not test_id:
                return
            
            # Agregar al tree widget
            self.add_test_to_tree(test_data, test_id)
            
            # Mensaje de confirmación
            protocol_name = self.protocol_names.get(protocol_type, protocol_type)
            QMessageBox.information(
                self.main_window,
                "Prueba Creada",
                f"Prueba '{protocol_name}' creada exitosamente.\n\n"
                f"Evaluador: {self.current_evaluator}\n"
                f"Estado: Pendiente"
            )
            
            print(f"Prueba creada: {protocol_name} por {self.current_evaluator}")
            
        except Exception as e:
            QMessageBox.critical(
                self.main_window,
                "Error",
                f"Error creando prueba: {e}"
            )
            print(f"Error en create_new_test: {e}")
    
    def add_test_to_siev(self, test_data):
        """
        Agregar prueba al archivo .siev del usuario
        
        Args:
            test_data: Datos de la prueba
            
        Returns:
            str: ID de la prueba o None si falló
        """
        try:
            siev_manager = self.main_window.siev_manager
            siev_path = self.main_window.current_user_siev
            
            if not siev_manager or not siev_path:
                raise Exception("Sistema de usuarios no disponible")
            
            # Agregar prueba al .siev (sin datos CSV/video por ahora)
            success = siev_manager.add_test_to_siev(siev_path, test_data)
            
            if success:
                # Generar ID único basado en timestamp
                test_id = f"test_{int(test_data['fecha'])}"
                return test_id
            else:
                raise Exception("Error agregando prueba al archivo .siev")
                
        except Exception as e:
            print(f"Error agregando prueba al .siev: {e}")
            return None
    
    def add_test_to_tree(self, test_data, test_id):
        """
        Agregar prueba al QTreeWidget organizando por fechas
        
        Args:
            test_data: Datos de la prueba
            test_id: ID único de la prueba
        """
        try:
            tree_widget = self.main_window.ui.listTestWidget
            
            # Obtener fecha de la prueba
            test_date = datetime.fromtimestamp(test_data['fecha'])
            date_str = test_date.strftime("%d/%m/%Y")
            time_str = test_date.strftime("%H:%M")
            
            # Buscar o crear item de fecha
            date_item = self.find_or_create_date_item(tree_widget, date_str)
            
            # Crear item de la prueba
            test_name = test_data['tipo']
            evaluator = test_data['evaluador']
            estado = test_data['estado'].upper()
            
            test_text = f"{test_name} - {time_str} ({evaluator}) [{estado}]"
            test_item = QTreeWidgetItem(date_item)
            test_item.setText(0, test_text)
            
            # Guardar datos en el item para referencia
            test_item.setData(0, Qt.UserRole, {
                'test_id': test_id,
                'test_data': test_data
            })
            
            # Expandir fecha para mostrar la nueva prueba
            date_item.setExpanded(True)
            
            # Scroll hacia el nuevo item
            tree_widget.scrollToItem(test_item)
            
            print(f"Prueba agregada al tree: {test_text}")
            
        except Exception as e:
            print(f"Error agregando prueba al tree: {e}")
    
    def find_or_create_date_item(self, tree_widget, date_str):
        """
        Buscar o crear item de fecha en el tree
        
        Args:
            tree_widget: QTreeWidget
            date_str: Fecha en formato "DD/MM/YYYY"
            
        Returns:
            QTreeWidgetItem: Item de la fecha
        """
        try:
            # Buscar item existente
            for i in range(tree_widget.topLevelItemCount()):
                item = tree_widget.topLevelItem(i)
                if item.text(0) == date_str:
                    return item
            
            # Crear nuevo item de fecha
            date_item = QTreeWidgetItem(tree_widget)
            date_item.setText(0, date_str)
            
            # Estilo para el item de fecha
            font = date_item.font(0)
            font.setBold(True)
            date_item.setFont(0, font)
            
            # Ordenar fechas (más reciente primero)
            #self.sort_date_items(tree_widget)
            
            return date_item
            
        except Exception as e:
            print(f"Error creando item de fecha: {e}")
            # Retornar item básico en caso de error
            date_item = QTreeWidgetItem(tree_widget)
            date_item.setText(0, date_str)
            return date_item
    

    
    def update_test_status(self, test_id, new_status):
        """
        Actualizar estado de una prueba
        
        Args:
            test_id: ID de la prueba
            new_status: Nuevo estado ("pendiente", "en_progreso", "completada")
        """
        try:
            # Actualizar en el tree widget
            self.update_test_in_tree(test_id, new_status)
            
            # Actualizar en el .siev
            self.update_test_in_siev(test_id, new_status)
            
            print(f"Estado de prueba {test_id} actualizado a: {new_status}")
            
        except Exception as e:
            print(f"Error actualizando estado de prueba: {e}")
    
    def update_test_in_tree(self, test_id, new_status):
        """Actualizar estado de prueba en el tree widget"""
        try:
            tree_widget = self.main_window.ui.listTestWidget
            
            # Buscar el item de la prueba
            for i in range(tree_widget.topLevelItemCount()):
                date_item = tree_widget.topLevelItem(i)
                
                for j in range(date_item.childCount()):
                    test_item = date_item.child(j)
                    item_data = test_item.data(0, Qt.UserRole)
                    
                    if item_data and item_data.get('test_id') == test_id:
                        # Actualizar texto del item
                        test_data = item_data['test_data']
                        test_data['estado'] = new_status
                        
                        test_date = datetime.fromtimestamp(test_data['fecha'])
                        time_str = test_date.strftime("%H:%M")
                        test_name = test_data['tipo']
                        evaluator = test_data['evaluador']
                        estado = new_status.upper()
                        
                        new_text = f"{test_name} - {time_str} ({evaluator}) [{estado}]"
                        test_item.setText(0, new_text)
                        
                        # Actualizar datos guardados
                        item_data['test_data'] = test_data
                        test_item.setData(0, Qt.UserRole, item_data)
                        
                        return
                        
        except Exception as e:
            print(f"Error actualizando prueba en tree: {e}")
    
    def update_test_in_siev(self, test_id, new_status):
        """Actualizar estado de prueba en el .siev"""
        try:
            # Esta función se implementará cuando se integre con la lógica de grabación
            # Por ahora solo logging
            print(f"TODO: Actualizar prueba {test_id} en .siev con estado {new_status}")
            
        except Exception as e:
            print(f"Error actualizando prueba en .siev: {e}")
    
    def get_current_evaluator(self):
        """Obtener evaluador actual"""
        return self.current_evaluator
    
    def clear_session_data(self):
        """Limpiar datos de sesión (al cerrar usuario)"""
        self.current_evaluator = None
        print("Datos de sesión de protocolo limpiados")