"""
Wizard para generación de informes
Compatible con la estructura del proyecto VNG
"""

from PySide6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout, QTreeWidget, 
    QTreeWidgetItem, QPushButton, QLabel, QTextEdit, QTableWidget,
    QTableWidgetItem, QMessageBox, QFrame, QSplitter, QGroupBox,
    QGridLayout, QHeaderView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from datetime import datetime


class TestSelectionPage(QWizardPage):
    """Primera página: Selección de pruebas"""
    
    def __init__(self, user_tests, user_data):
        super().__init__()
        self.user_tests = user_tests
        self.user_data = user_data
        self.selected_tests = []
        
        self.setTitle("Selección de Pruebas")
        self.setSubTitle("Seleccione las pruebas que desea incluir en el informe")
        
        self.setup_ui()
        self.load_available_tests()
        
    def setup_ui(self):
        """Configurar interfaz de usuario"""
        layout = QVBoxLayout()
        
        # Crear splitter horizontal
        splitter = QSplitter(Qt.Horizontal)
        
        # Panel izquierdo - Pruebas disponibles
        left_group = QGroupBox("Pruebas Disponibles")
        left_layout = QVBoxLayout()
        
        self.available_tree = QTreeWidget()
        self.available_tree.setHeaderLabel("Todas las pruebas del paciente")
        self.available_tree.setSelectionMode(QTreeWidget.SingleSelection)
        left_layout.addWidget(self.available_tree)
        
        left_group.setLayout(left_layout)
        splitter.addWidget(left_group)
        
        # Panel central - Botones
        buttons_layout = QVBoxLayout()
        buttons_layout.addStretch()
        
        self.btn_add = QPushButton("→ Agregar")
        self.btn_add.setFixedSize(100, 30)
        self.btn_add.clicked.connect(self.add_test)
        buttons_layout.addWidget(self.btn_add)
        
        buttons_layout.addSpacing(10)
        
        self.btn_remove = QPushButton("← Quitar")
        self.btn_remove.setFixedSize(100, 30)
        self.btn_remove.clicked.connect(self.remove_test)
        buttons_layout.addWidget(self.btn_remove)
        
        buttons_layout.addStretch()
        
        buttons_frame = QFrame()
        buttons_frame.setLayout(buttons_layout)
        buttons_frame.setMaximumWidth(120)
        splitter.addWidget(buttons_frame)
        
        # Panel derecho - Pruebas seleccionadas
        right_group = QGroupBox("Pruebas Seleccionadas para el Informe")
        right_layout = QVBoxLayout()
        
        self.selected_tree = QTreeWidget()
        self.selected_tree.setHeaderLabel("Pruebas incluidas en el informe")
        self.selected_tree.setSelectionMode(QTreeWidget.SingleSelection)
        right_layout.addWidget(self.selected_tree)
        
        right_group.setLayout(right_layout)
        splitter.addWidget(right_group)
        
        # Configurar proporciones del splitter
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 0)
        splitter.setStretchFactor(2, 2)
        
        layout.addWidget(splitter)
        
        # Etiqueta informativa
        info_label = QLabel("⚠️ Solo se puede seleccionar una prueba por tipo (ej: un AOD 44°C, un OI 44°C, etc.)")
        info_label.setStyleSheet("color: #666; font-style: italic; padding: 10px;")
        layout.addWidget(info_label)
        
        self.setLayout(layout)
        
    def load_available_tests(self):
        """Cargar pruebas disponibles del paciente"""
        try:
            if not self.user_tests:
                return
                
            # Organizar pruebas por fecha (como en main_window)
            tests_by_date = {}
            for test in self.user_tests:
                try:
                    test_date = datetime.fromtimestamp(test.get('fecha', 0))
                    date_str = test_date.strftime("%d/%m/%Y")
                    
                    if date_str not in tests_by_date:
                        tests_by_date[date_str] = []
                    
                    tests_by_date[date_str].append(test)
                    
                except Exception as e:
                    print(f"Error procesando prueba: {e}")
                    continue
            
            # Crear estructura en el tree (más reciente primero)
            for date_str in sorted(tests_by_date.keys(), reverse=True):
                # Crear item de fecha
                date_item = QTreeWidgetItem(self.available_tree)
                date_item.setText(0, date_str)
                
                # Estilo para fecha
                font = date_item.font(0)
                font.setBold(True)
                date_item.setFont(0, font)
                
                # Agregar pruebas de esta fecha
                for test in tests_by_date[date_str]:
                    try:
                        test_date = datetime.fromtimestamp(test.get('fecha', 0))
                        time_str = test_date.strftime("%H:%M")
                        
                        test_name = test.get('tipo', 'Desconocido')
                        evaluator = test.get('evaluador', 'Sin evaluador')
                        estado = test.get('estado', 'completada').upper()
                        
                        test_text = f"{test_name} - {time_str} ({evaluator}) [{estado}]"
                        test_item = QTreeWidgetItem(date_item)
                        test_item.setText(0, test_text)
                        
                        # Guardar datos para referencia
                        test_item.setData(0, Qt.UserRole, {
                            'test_id': test.get('id'),
                            'test_data': test
                        })
                        
                    except Exception as e:
                        print(f"Error creando item de prueba: {e}")
                        continue
                
                # Expandir fecha si tiene pocas pruebas
                if len(tests_by_date[date_str]) <= 3:
                    date_item.setExpanded(True)
                    
        except Exception as e:
            print(f"Error cargando pruebas disponibles: {e}")
    
    def add_test(self):
        """Agregar prueba seleccionada al informe"""
        try:
            current_item = self.available_tree.currentItem()
            
            if not current_item or not current_item.parent():
                QMessageBox.warning(self, "Selección Inválida", 
                                  "Debe seleccionar una prueba específica, no una fecha.")
                return
            
            # Obtener datos de la prueba
            item_data = current_item.data(0, Qt.UserRole)
            if not item_data:
                return
                
            test_data = item_data['test_data']
            test_type = test_data.get('tipo', '')
            
            # Verificar si ya existe una prueba del mismo tipo
            if self.has_test_type(test_type):
                QMessageBox.warning(
                    self, 
                    "Tipo Duplicado", 
                    f"Ya existe una prueba del tipo '{test_type}' en el informe.\n\n"
                    f"Solo se permite una prueba por tipo."
                )
                return
            
            # Agregar a pruebas seleccionadas
            self.selected_tests.append(item_data)
            
            # Crear item en el tree de seleccionados
            selected_item = QTreeWidgetItem(self.selected_tree)
            selected_item.setText(0, current_item.text(0))
            selected_item.setData(0, Qt.UserRole, item_data)
            
            # Remover de disponibles
            parent = current_item.parent()
            parent.removeChild(current_item)
            
            # Si la fecha quedó vacía, remover también
            if parent.childCount() == 0:
                self.available_tree.takeTopLevelItem(
                    self.available_tree.indexOfTopLevelItem(parent)
                )
            
            print(f"Prueba agregada al informe: {test_type}")
            
            # IMPORTANTE: Notificar al wizard que la página cambió
            self.completeChanged.emit()
            
        except Exception as e:
            print(f"Error agregando prueba: {e}")
            QMessageBox.critical(self, "Error", f"Error agregando prueba: {e}")
    
    def remove_test(self):
        """Quitar prueba del informe"""
        try:
            current_item = self.selected_tree.currentItem()
            
            if not current_item:
                QMessageBox.warning(self, "Selección Inválida", 
                                  "Debe seleccionar una prueba para quitar.")
                return
            
            # Obtener datos de la prueba
            item_data = current_item.data(0, Qt.UserRole)
            if not item_data:
                return
            
            # Remover de lista de seleccionadas
            self.selected_tests = [test for test in self.selected_tests 
                                 if test['test_id'] != item_data['test_id']]
            
            # Devolver a pruebas disponibles
            self.add_back_to_available(item_data)
            
            # Remover del tree de seleccionadas
            self.selected_tree.takeTopLevelItem(
                self.selected_tree.indexOfTopLevelItem(current_item)
            )
            
            print(f"Prueba removida del informe")
            
            # IMPORTANTE: Notificar al wizard que la página cambió
            self.completeChanged.emit()
            
        except Exception as e:
            print(f"Error removiendo prueba: {e}")
    
    def add_back_to_available(self, item_data):
        """Devolver prueba a la lista de disponibles"""
        try:
            test_data = item_data['test_data']
            test_date = datetime.fromtimestamp(test_data.get('fecha', 0))
            date_str = test_date.strftime("%d/%m/%Y")
            time_str = test_date.strftime("%H:%M")
            
            # Buscar o crear item de fecha
            date_item = None
            for i in range(self.available_tree.topLevelItemCount()):
                item = self.available_tree.topLevelItem(i)
                if item.text(0) == date_str:
                    date_item = item
                    break
            
            if not date_item:
                # Crear nuevo item de fecha
                date_item = QTreeWidgetItem(self.available_tree)
                date_item.setText(0, date_str)
                
                font = date_item.font(0)
                font.setBold(True)
                date_item.setFont(0, font)
                
                # Reordenar fechas
                self.sort_dates_in_tree()
            
            # Crear item de prueba
            test_name = test_data.get('tipo', 'Desconocido')
            evaluator = test_data.get('evaluador', 'Sin evaluador')
            estado = test_data.get('estado', 'completada').upper()
            
            test_text = f"{test_name} - {time_str} ({evaluator}) [{estado}]"
            test_item = QTreeWidgetItem(date_item)
            test_item.setText(0, test_text)
            test_item.setData(0, Qt.UserRole, item_data)
            
            date_item.setExpanded(True)
            
        except Exception as e:
            print(f"Error devolviendo prueba: {e}")
    
    def sort_dates_in_tree(self):
        """Ordenar fechas en el tree (más reciente primero)"""
        try:
            # Obtener todos los items de fecha
            date_items = []
            for i in range(self.available_tree.topLevelItemCount()):
                date_items.append(self.available_tree.takeTopLevelItem(0))
            
            # Ordenar por fecha (más reciente primero)
            date_items.sort(key=lambda item: datetime.strptime(item.text(0), "%d/%m/%Y"), 
                          reverse=True)
            
            # Volver a agregar en orden
            for item in date_items:
                self.available_tree.addTopLevelItem(item)
                
        except Exception as e:
            print(f"Error ordenando fechas: {e}")
    
    def has_test_type(self, test_type):
        """Verificar si ya existe una prueba del tipo especificado"""
        for test_item in self.selected_tests:
            if test_item['test_data'].get('tipo') == test_type:
                return True
        return False
    
    def get_selected_tests(self):
        """Obtener lista de pruebas seleccionadas"""
        return self.selected_tests
    
    def isComplete(self):
        """Validar que la página está completa"""
        return len(self.selected_tests) > 0


class ReportSummaryPage(QWizardPage):
    """Segunda página: Resumen y comentarios"""
    
    def __init__(self, user_data):
        super().__init__()
        self.user_data = user_data
        self.selected_tests = []
        
        self.setTitle("Resumen del Informe")
        self.setSubTitle("Revise la información y agregue comentarios")
        
        self.setup_ui()
        self.load_patient_info()
    
    def setup_ui(self):
        """Configurar interfaz de usuario"""
        layout = QVBoxLayout()
        
        # Sección superior - Resumen
        summary_group = QGroupBox("Resumen")
        summary_layout = QVBoxLayout()
        
        # Información del paciente
        patient_layout = QGridLayout()
        
        # Datos del paciente
        patient_layout.addWidget(QLabel("Nombre del Paciente:"), 0, 0)
        self.patient_name_label = QLabel()
        self.patient_name_label.setStyleSheet("font-weight: bold;")
        patient_layout.addWidget(self.patient_name_label, 0, 1)
        
        patient_layout.addWidget(QLabel("RUT/ID:"), 0, 2)
        self.patient_id_label = QLabel()
        patient_layout.addWidget(self.patient_id_label, 0, 3)
        
        patient_layout.addWidget(QLabel("Edad:"), 1, 0)
        self.patient_age_label = QLabel()
        patient_layout.addWidget(self.patient_age_label, 1, 1)
        
        patient_layout.addWidget(QLabel("Fecha de Nacimiento:"), 1, 2)
        self.patient_birth_label = QLabel()
        patient_layout.addWidget(self.patient_birth_label, 1, 3)
        
        summary_layout.addLayout(patient_layout)
        
        # Tabla de pruebas seleccionadas
        summary_layout.addWidget(QLabel("Pruebas incluidas en el informe:"))
        
        self.tests_table = QTableWidget()
        self.tests_table.setColumnCount(3)
        self.tests_table.setHorizontalHeaderLabels(["Tipo de Prueba", "Fecha de Evaluación", "Evaluador"])
        
        # Configurar tabla
        header = self.tests_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        
        self.tests_table.setMaximumHeight(150)
        summary_layout.addWidget(self.tests_table)
        
        # Espacio para resumen de resultados (futuro)
        summary_layout.addWidget(QLabel("Resumen de Resultados:"))
        results_label = QLabel("(Esta funcionalidad se implementará posteriormente)")
        results_label.setStyleSheet("color: #666; font-style: italic; padding: 10px;")
        summary_layout.addWidget(results_label)
        
        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)
        
        # Sección inferior - Comentarios
        comments_group = QGroupBox("Comentarios del Informe")
        comments_layout = QVBoxLayout()
        
        self.comments_text = QTextEdit()
        self.comments_text.setPlaceholderText("Ingrese aquí sus comentarios adicionales para el informe...")
        self.comments_text.setMaximumHeight(120)
        comments_layout.addWidget(self.comments_text)
        
        comments_group.setLayout(comments_layout)
        layout.addWidget(comments_group)
        
        self.setLayout(layout)
    
    def load_patient_info(self):
        """Cargar información del paciente"""
        try:
            if not self.user_data:
                return
            
            # Nombre
            nombre = self.user_data.get('nombre', 'No especificado')
            self.patient_name_label.setText(nombre)
            
            # RUT/ID
            rut_id = self.user_data.get('rut_id', 'No especificado')
            self.patient_id_label.setText(rut_id)
            
            # Calcular edad y fecha de nacimiento
            fecha_nacimiento = self.user_data.get('fecha_nacimiento')
            if fecha_nacimiento:
                try:
                    birth_date = datetime.strptime(fecha_nacimiento, "%Y-%m-%d")
                    today = datetime.now()
                    edad = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                    
                    self.patient_age_label.setText(f"{edad} años")
                    self.patient_birth_label.setText(birth_date.strftime("%d/%m/%Y"))
                except:
                    self.patient_age_label.setText("No calculable")
                    self.patient_birth_label.setText("Formato inválido")
            else:
                self.patient_age_label.setText("No especificada")
                self.patient_birth_label.setText("No especificada")
                
        except Exception as e:
            print(f"Error cargando información del paciente: {e}")
    
    def update_selected_tests(self, selected_tests):
        """Actualizar tabla con las pruebas seleccionadas"""
        try:
            self.selected_tests = selected_tests
            
            # Configurar tabla
            self.tests_table.setRowCount(len(selected_tests))
            
            for row, test_item in enumerate(selected_tests):
                test_data = test_item['test_data']
                
                # Tipo de prueba
                tipo_item = QTableWidgetItem(test_data.get('tipo', 'Desconocido'))
                self.tests_table.setItem(row, 0, tipo_item)
                
                # Fecha de evaluación
                fecha_timestamp = test_data.get('fecha', 0)
                fecha_str = datetime.fromtimestamp(fecha_timestamp).strftime("%d/%m/%Y %H:%M")
                fecha_item = QTableWidgetItem(fecha_str)
                self.tests_table.setItem(row, 1, fecha_item)
                
                # Evaluador
                evaluador_item = QTableWidgetItem(test_data.get('evaluador', 'Sin evaluador'))
                self.tests_table.setItem(row, 2, evaluador_item)
            
            # Ajustar altura de tabla
            self.tests_table.resizeRowsToContents()
            
        except Exception as e:
            print(f"Error actualizando tabla de pruebas: {e}")
    
    def get_comments(self):
        """Obtener comentarios ingresados"""
        return self.comments_text.toPlainText().strip()


class ReportWizard(QWizard):
    """Wizard principal para generación de informes"""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        
        self.setWindowTitle("Generar Informe")
        self.setFixedSize(800, 600)
        
        # Obtener datos del usuario y pruebas
        self.user_data = main_window.current_user_data
        self.user_tests = []
        
        if main_window.current_user_siev and main_window.siev_manager:
            try:
                self.user_tests = main_window.siev_manager.get_user_tests(main_window.current_user_siev)
            except Exception as e:
                print(f"Error obteniendo pruebas del usuario: {e}")
        
        self.setup_pages()
    
    def setup_pages(self):
        """Configurar páginas del wizard"""
        try:
            # Página 1: Selección de pruebas
            self.test_selection_page = TestSelectionPage(self.user_tests, self.user_data)
            self.addPage(self.test_selection_page)
            
            # Página 2: Resumen y comentarios
            self.summary_page = ReportSummaryPage(self.user_data)
            self.addPage(self.summary_page)
            
            # Conectar señales para transferir datos entre páginas
            self.currentIdChanged.connect(self.on_page_changed)
            
            # Personalizar botones
            self.setButtonText(QWizard.NextButton, "Siguiente")
            self.setButtonText(QWizard.BackButton, "Anterior")
            self.setButtonText(QWizard.FinishButton, "Generar Informe")
            self.setButtonText(QWizard.CancelButton, "Cancelar")
            
        except Exception as e:
            print(f"Error configurando páginas del wizard: {e}")
            QMessageBox.critical(self, "Error", f"Error inicializando wizard: {e}")
    
    def on_page_changed(self, page_id):
        """Manejar cambio de página"""
        try:
            if page_id == 1:  # Página de resumen
                # Transferir pruebas seleccionadas
                selected_tests = self.test_selection_page.get_selected_tests()
                self.summary_page.update_selected_tests(selected_tests)
                
        except Exception as e:
            print(f"Error en cambio de página: {e}")
    
    def accept(self):
        """Manejar finalización del wizard"""
        try:
            # Obtener datos finales
            selected_tests = self.test_selection_page.get_selected_tests()
            comments = self.summary_page.get_comments()
            
            print("=== DATOS DEL INFORME ===")
            print(f"Usuario: {self.user_data.get('nombre', 'Desconocido')}")
            print(f"Pruebas seleccionadas: {len(selected_tests)}")
            for test_item in selected_tests:
                test_data = test_item['test_data']
                print(f"  - {test_data.get('tipo')} ({datetime.fromtimestamp(test_data.get('fecha', 0)).strftime('%d/%m/%Y')})")
            print(f"Comentarios: {comments if comments else '(Sin comentarios)'}")
            print("========================")
            
            # TODO: Aquí se implementará la generación real del informe
            QMessageBox.information(
                self, 
                "Informe Generado", 
                f"Informe generado exitosamente.\n\n"
                f"Pruebas incluidas: {len(selected_tests)}\n"
                f"Comentarios: {'Sí' if comments else 'No'}"
            )
            
            # Cerrar wizard
            super().accept()
            
        except Exception as e:
            print(f"Error generando informe: {e}")
            QMessageBox.critical(self, "Error", f"Error generando informe: {e}")


def open_report_wizard(main_window):
    """Función helper para abrir el wizard desde main_window"""
    try:
        # Verificar que hay usuario actual
        if not main_window.current_user_siev or not main_window.current_user_data:
            QMessageBox.warning(
                main_window,
                "Sin Usuario",
                "Debe cargar un usuario antes de generar un informe."
            )
            return
        
        # Verificar que hay pruebas
        if main_window.siev_manager:
            tests = main_window.siev_manager.get_user_tests(main_window.current_user_siev)
            if not tests:
                QMessageBox.information(
                    main_window,
                    "Sin Pruebas",
                    "El usuario actual no tiene pruebas disponibles para generar un informe."
                )
                return
        
        # Crear y mostrar wizard
        wizard = ReportWizard(main_window)
        wizard.exec()
        
    except Exception as e:
        print(f"Error abriendo wizard de informe: {e}")
        QMessageBox.critical(main_window, "Error", f"Error abriendo wizard: {e}")