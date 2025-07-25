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
            self.main_window.reset_button_for_new_test()

            # Mensaje de confirmación
            protocol_name = self.protocol_names.get(protocol_type, protocol_type)
            QMessageBox.information(
                self.main_window,
                "Prueba Creada",
                f"Prueba '{protocol_name}' creada exitosamente.\n\n"
                f"Evaluador: {self.current_evaluator}\n"
                f"Estado: Pendiente\n\n"
                f"Presione 'Iniciar' para comenzar la grabación."
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
    
    # Agregar estos métodos al protocol_manager.py existente:

    def start_test(self, test_id):
        """
        Iniciar una prueba (llamar cuando se presiona Iniciar)
        
        Args:
            test_id: ID de la prueba a iniciar
        """
        try:
            # Actualizar estado a "ejecutando"
            self.update_test_status(test_id, "ejecutando")
            
            # Actualizar hora de inicio en .siev
            self.update_test_in_siev(test_id, hora_inicio=time.time())
            
            print(f"Prueba {test_id} iniciada")
            return True
            
        except Exception as e:
            print(f"Error iniciando prueba {test_id}: {e}")
            return False

    def finalize_test(self, test_id, stopped_manually=False):
        """
        Finalizar prueba y empaquetar datos
        
        Args:
            test_id: ID de la prueba
            stopped_manually: Si fue detenida manualmente o por tiempo
        """
        try:
            print(f"=== FINALIZANDO PRUEBA {test_id} ===")
            
            # Obtener datos de data_storage
            test_data = self.main_window.data_storage.get_test_data()
            
            if not test_data:
                print("No hay datos para empaquetar")
                self.update_test_status(test_id, "error")
                return False
            
            # Actualizar estado a "completado"
            self.update_test_status(test_id, "completado")
            
            # Actualizar metadatos finales en .siev
            self.update_test_in_siev(
                test_id, 
                hora_fin=time.time(),
                test_data=test_data,
                stopped_manually=stopped_manually
            )
            
            # Limpiar datos de memoria
            self.main_window.data_storage.clear_data()
            
            print(f"Prueba {test_id} finalizada y empaquetada exitosamente")
            
            # Mostrar estadísticas
            stats = test_data.get('statistics', {})
            print(f"  - Duración: {stats.get('duration_seconds', 0):.1f}s")
            print(f"  - Muestras: {stats.get('total_samples', 0)}")
            print(f"  - Tasa de muestreo: {stats.get('sample_rate', 0):.1f} Hz")
            
            return True
            
        except Exception as e:
            print(f"Error finalizando prueba {test_id}: {e}")
            self.update_test_status(test_id, "error")
            return False

    def update_test_in_siev(self, test_id, hora_inicio=None, hora_fin=None, test_data=None, stopped_manually=False):
        """
        Actualizar prueba en el archivo .siev con datos completos
        
        Args:
            test_id: ID de la prueba
            hora_inicio: Timestamp de inicio (opcional)
            hora_fin: Timestamp de finalización (opcional)  
            test_data: Datos completos de la prueba (opcional)
            stopped_manually: Si fue detenida manualmente
        """
        try:
            siev_manager = self.main_window.siev_manager
            siev_path = self.main_window.current_user_siev
            
            if not siev_manager or not siev_path:
                raise Exception("Sistema de usuarios no disponible")
            
            # Si es solo actualización de timestamps
            if not test_data:
                # Actualizar solo metadatos básicos
                metadata_updates = {}
                if hora_inicio:
                    metadata_updates['hora_inicio'] = hora_inicio
                if hora_fin:
                    metadata_updates['hora_fin'] = hora_fin
                
                # TODO: Implementar actualización simple de metadatos en SievManager
                print(f"Actualizando timestamps para {test_id}")
                return True
            
            # Si es finalización completa con datos
            if test_data:
                # Preparar datos CSV en formato compatible
                csv_data = self._prepare_csv_data(test_data)
                
                # Obtener metadatos actuales de la prueba
                current_test_data = self._get_test_metadata(test_id)
                if current_test_data:
                    current_test_data['hora_fin'] = hora_fin
                    current_test_data['estado'] = 'completado'
                    current_test_data['detenido_manualmente'] = stopped_manually
                    
                    # Usar SievManager para agregar datos completos
                    success = siev_manager.add_test_to_siev(
                        siev_path,
                        current_test_data,
                        csv_data=csv_data,
                        video_path=None  # TODO: Implementar video si es necesario
                    )
                    
                    if success:
                        print(f"Datos de prueba {test_id} empaquetados en .siev")
                        return True
                    else:
                        raise Exception("Error empaquetando datos en .siev")
            
            return True
            
        except Exception as e:
            print(f"Error actualizando prueba {test_id} en .siev: {e}")
            return False

    def _prepare_csv_data(self, test_data):
        """
        Convertir datos de prueba al formato CSV para SievManager
        
        Args:
            test_data: Datos de la prueba desde data_storage
            
        Returns:
            List[Dict]: Lista de diccionarios con los datos (formato esperado por SievManager)
        """
        try:
            # Preparar lista de diccionarios en lugar de cadena CSV
            csv_data = []
            
            # Procesar cada muestra - usar estructura real de data_storage
            for sample in test_data.get('data', []):
                # Los datos vienen directamente del data_storage sin anidamiento
                row_dict = {
                    'timestamp': sample.get('timestamp', 0),
                    'recording_time': sample.get('timestamp', 0),  # usar timestamp como recording_time
                    'left_eye_x': sample.get('left_eye_x', 0),
                    'left_eye_y': sample.get('left_eye_y', 0),
                    'left_eye_detected': sample.get('left_eye_detected', False),
                    'right_eye_x': sample.get('right_eye_x', 0),
                    'right_eye_y': sample.get('right_eye_y', 0),
                    'right_eye_detected': sample.get('right_eye_detected', False),
                    'imu_x': sample.get('imu_x', 0),
                    'imu_y': sample.get('imu_y', 0),
                    'imu_z': 0  # No hay imu_z en data_storage, usar 0
                }
                
                csv_data.append(row_dict)
            
            print(f"Datos CSV preparados: {len(csv_data)} muestras")
            return csv_data
            
        except Exception as e:
            print(f"Error preparando datos CSV: {e}")
            return []

    def _get_test_metadata(self, test_id):
        """
        Obtener metadatos actuales de una prueba desde el tree widget
        
        Args:
            test_id: ID de la prueba
            
        Returns:
            dict: Metadatos de la prueba o None
        """
        try:
            tree_widget = self.main_window.ui.listTestWidget
            
            # Buscar el item de la prueba
            for i in range(tree_widget.topLevelItemCount()):
                date_item = tree_widget.topLevelItem(i)
                
                for j in range(date_item.childCount()):
                    test_item = date_item.child(j)
                    item_data = test_item.data(0, Qt.UserRole)
                    
                    if item_data and item_data.get('test_id') == test_id:
                        return item_data.get('test_data', {})
            
            return None
            
        except Exception as e:
            print(f"Error obteniendo metadatos de prueba {test_id}: {e}")
            return None

    def get_current_test_id(self):
        """
        Obtener ID de la prueba actualmente seleccionada o más reciente
        
        Returns:
            str: ID de la prueba actual o None
        """
        try:
            tree_widget = self.main_window.ui.listTestWidget
            
            # Intentar obtener item seleccionado
            current_item = tree_widget.currentItem()
            if current_item and current_item.parent():  # Es un item de prueba
                item_data = current_item.data(0, Qt.UserRole)
                if item_data:
                    return item_data.get('test_id')
            
            # Si no hay selección, buscar la prueba más reciente con estado "pendiente" o "ejecutando"
            latest_test_id = None
            latest_timestamp = 0
            
            for i in range(tree_widget.topLevelItemCount()):
                date_item = tree_widget.topLevelItem(i)
                
                for j in range(date_item.childCount()):
                    test_item = date_item.child(j)
                    item_data = test_item.data(0, Qt.UserRole)
                    
                    if item_data:
                        test_data = item_data.get('test_data', {})
                        estado = test_data.get('estado', '')
                        fecha = test_data.get('fecha', 0)
                        
                        if estado in ['pendiente', 'ejecutando'] and fecha > latest_timestamp:
                            latest_timestamp = fecha
                            latest_test_id = item_data.get('test_id')
            
            return latest_test_id
            
        except Exception as e:
            print(f"Error obteniendo test_id actual: {e}")
            return None
    
    
    def get_current_evaluator(self):
        """Obtener evaluador actual"""
        return self.current_evaluator
    
    def clear_session_data(self):
        """Limpiar datos de sesión (al cerrar usuario)"""
        self.current_evaluator = None
        print("Datos de sesión de protocolo limpiados")