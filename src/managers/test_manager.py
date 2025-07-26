# src/managers/test_manager.py

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QDialog, QMessageBox, QTreeWidgetItem
from typing import Dict, Optional, List, Any
import time

from libs.core.protocol_manager import ProtocolManager
from libs.core.siev_manager import SievManager
from libs.stimulus.stimulus_system import StimulusManager
from ui.dialogs.user_dialog import NewUserDialog


class TestManager(QObject):
    """
    Gestiona todo el sistema de tests: protocolos, usuarios, estímulos y sesiones.
    Encapsula la lógica de pruebas para desacoplarla de MainWindow.
    """
    
    # Señales para comunicarse con MainWindow
    user_loaded = Signal(dict)              # Usuario cargado con sus datos
    user_closed = Signal()                  # Usuario cerrado
    test_created = Signal(str, dict)        # Test creado (test_id, test_data)
    test_started = Signal(str)              # Test iniciado (test_id)
    test_completed = Signal(str, dict)      # Test completado (test_id, results)
    stimulus_window_opened = Signal(str)    # Ventana de estímulos abierta (protocol)
    stimulus_window_closed = Signal()      # Ventana de estímulos cerrada
    evaluator_changed = Signal(str)        # Evaluador cambiado
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Componentes de gestión de tests
        self.protocol_manager = None
        self.siev_manager = None
        self.stimulus_manager = None
        
        # Referencias de UI (se asignan desde MainWindow)
        self.main_window = None
        self.test_tree_widget = None
        
        # Estado del usuario actual
        self.current_user_siev = None
        self.current_user_data = None
        
        # Estado de tests
        self.current_test_id = None
        self.current_protocol = None
        self.current_evaluator = None
        
        # Estado de estímulos
        self.test_preparation_mode = False
        self.test_ready_to_start = False
        
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
        
        # Protocolos que necesitan estímulos
        self.stimulus_protocols = [
            'sacadas', 
            'seguimiento_lento', 
            'optoquinetico'
        ]
        
        print("TestManager inicializado")
    
    def set_references(self, main_window, test_tree_widget):
        """
        Establece referencias necesarias desde MainWindow.
        
        Args:
            main_window: Referencia a MainWindow
            test_tree_widget: Widget del árbol de tests
        """
        self.main_window = main_window
        self.test_tree_widget = test_tree_widget
        print("Referencias establecidas en TestManager")
    
    def initialize_test_system(self) -> bool:
        """Inicializa todo el sistema de tests"""
        try:
            self._init_protocol_manager()
            self._init_user_manager()
            self._init_stimulus_manager()
            
            print("Sistema de tests inicializado exitosamente")
            return True
            
        except Exception as e:
            print(f"Error inicializando sistema de tests: {e}")
            return False
    
    def _init_protocol_manager(self):
        """Inicializa el gestor de protocolos"""
        if not self.main_window:
            raise Exception("MainWindow no configurado")
        
        self.protocol_manager = ProtocolManager(self.main_window)
        print("Gestor de protocolos inicializado")
    
    def _init_user_manager(self):
        """Inicializa el gestor de usuarios"""
        self.siev_manager = SievManager()
        print("Gestor de usuarios inicializado")
    
    def _init_stimulus_manager(self):
        """Inicializa el gestor de estímulos"""
        if not self.main_window:
            raise Exception("MainWindow no configurado")
        
        self.stimulus_manager = StimulusManager(self.main_window)
        print("Gestor de estímulos inicializado")
    
    # === GESTIÓN DE USUARIOS ===
    
    def open_new_user_dialog(self) -> bool:
        """
        Abre diálogo para crear nuevo usuario.
        
        Returns:
            bool: True si se creó el usuario exitosamente
        """
        try:
            dialog = NewUserDialog(self.main_window)
            if dialog.exec() == QDialog.Accepted:
                user_data = dialog.get_user_data()
                if user_data:
                    return self.create_new_user(user_data)
            return False
            
        except Exception as e:
            QMessageBox.critical(self.main_window, "Error", f"Error abriendo diálogo de usuario: {e}")
            return False
    
    def create_new_user(self, user_data: Dict) -> bool:
        """
        Crea un nuevo usuario.
        
        Args:
            user_data: Datos del usuario
            
        Returns:
            bool: True si se creó exitosamente
        """
        try:
            if not self.siev_manager:
                raise Exception("Gestor de usuarios no disponible")
            
            # Crear archivo .siev
            siev_path = self.siev_manager.create_user_siev(user_data)
            
            if siev_path:
                # Cargar el usuario recién creado
                return self.load_user(siev_path)
            else:
                raise Exception("Error creando archivo .siev")
                
        except Exception as e:
            QMessageBox.critical(self.main_window, "Error", f"Error creando usuario: {e}")
            return False
    
    def open_protocol_dialog(self, protocol_type: str):
        """
        Abre el diálogo de protocolo delegando al ProtocolManager.
        
        Args:
            protocol_type: Tipo de protocolo (ej: "OD_44", "seguimiento_lento")
        """
        try:
            if not self.protocol_manager:
                raise Exception("Gestor de protocolos no disponible")
            
            # Sincronizar el estado del usuario con ProtocolManager
            # ProtocolManager espera estos atributos en main_window
            self.main_window.current_user_siev = self.current_user_siev
            
            # También sincronizar el evaluador
            if self.current_evaluator:
                self.protocol_manager.current_evaluator = self.current_evaluator
            
            # Delegar al ProtocolManager existente
            return self.protocol_manager.open_protocol_dialog(protocol_type)
            
        except Exception as e:
            print(f"Error abriendo protocolo desde TestManager: {e}")
            return False

    def open_user_file(self) -> bool:
        """
        Abre diálogo para seleccionar archivo de usuario.
        
        Returns:
            bool: True si se cargó el usuario exitosamente
        """
        try:
            from PySide6.QtWidgets import QFileDialog
            
            file_path, _ = QFileDialog.getOpenFileName(
                self.main_window,
                "Abrir Archivo de Usuario",
                "",
                "Archivos SIEV (*.siev);;Todos los archivos (*)"
            )
            
            if file_path:
                return self.load_user(file_path)
            return False
            
        except Exception as e:
            QMessageBox.critical(self.main_window, "Error", f"Error abriendo archivo: {e}")
            return False
    
    def load_user(self, file_path: str) -> bool:
        """
        Carga un usuario desde archivo .siev.
        
        Args:
            file_path: Ruta al archivo .siev
            
        Returns:
            bool: True si se cargó exitosamente
        """
        try:
            if not self.siev_manager:
                raise Exception("Gestor de usuarios no disponible")
            
            # Validar archivo
            validation = self.siev_manager.validate_siev(file_path)
            if not validation['valid']:
                errors = '\n'.join(validation['errors'])
                raise Exception(f"Archivo inválido:\n{errors}")
            
            # Cargar datos del usuario
            user_data = self.siev_manager.get_user_info(file_path)
            user_tests = self.siev_manager.get_user_tests(file_path)
            
            # Actualizar estado
            self.current_user_siev = file_path
            self.current_user_data = user_data
            
            # Actualizar UI
            self._update_user_ui(user_data, user_tests)
            
            # Emitir señal
            self.user_loaded.emit(user_data)
            
            print(f"Usuario cargado: {user_data.get('nombre', 'Desconocido')}")
            return True
            
        except Exception as e:
            QMessageBox.critical(self.main_window, "Error", f"Error cargando usuario: {e}")
            return False
    
    def close_current_user(self):
        """Cierra el usuario actual"""
        try:
            if self.current_user_siev:
                print(f"Cerrando usuario: {self.current_user_data.get('nombre', 'Desconocido')}")
            
            # Limpiar estado
            self.current_user_siev = None
            self.current_user_data = None
            self.current_test_id = None
            self.current_protocol = None
            
            # Limpiar UI
            if self.test_tree_widget:
                self.test_tree_widget.clear()
                self.test_tree_widget.setHeaderLabel("Sin usuario seleccionado")
            
            # Cerrar ventana de estímulos si está abierta
            if self.stimulus_manager:
                self.stimulus_manager.close_stimulus_window()
            
            # Limpiar datos de sesión del protocolo
            if self.protocol_manager:
                self.protocol_manager.clear_session_data()
            
            # Emitir señal
            self.user_closed.emit()
            
        except Exception as e:
            print(f"Error cerrando usuario: {e}")
    
    def _update_user_ui(self, user_data: Dict, user_tests: List[Dict]):
        """Actualiza la UI con información del usuario"""
        try:
            if not self.test_tree_widget:
                return
            
            # Actualizar header del tree
            user_name = user_data.get('nombre', 'Usuario')
            self.test_tree_widget.setHeaderLabel(f"Pruebas - {user_name}")
            
            # Cargar tests en el tree
            self._populate_test_tree(user_tests)
            
            # Actualizar título de ventana
            if self.main_window:
                user_info = self.get_current_user_info()
                self.main_window.setWindowTitle(f"SIEV - {user_info}")
            
        except Exception as e:
            print(f"Error actualizando UI de usuario: {e}")
    
    def _populate_test_tree(self, user_tests: List[Dict]):
        """Llena el árbol de tests con los datos del usuario"""
        try:
            if not self.test_tree_widget:
                return
            
            self.test_tree_widget.clear()
            
            for test in user_tests:
                item = QTreeWidgetItem()
                
                # Configurar datos del item
                test_name = test.get('tipo', 'Desconocido')
                test_id = test.get('id', '')
                estado = test.get('estado', 'pendiente')
                
                item.setText(0, f"{self.protocol_names.get(test_name, test_name)} - {estado}")
                item.setData(0, 0x0100, test_id)  # Qt.UserRole = 0x0100
                
                self.test_tree_widget.addTopLevelItem(item)
            
            print(f"Cargados {len(user_tests)} tests en el árbol")
            
        except Exception as e:
            print(f"Error poblando árbol de tests: {e}")
    
    
    
    def create_new_test(self, protocol_data: Dict) -> bool:
        """
        Crea una nueva prueba.
        
        Args:
            protocol_data: Datos del protocolo seleccionado
            
        Returns:
            bool: True si se creó exitosamente
        """
        try:
            if not self.protocol_manager:
                raise Exception("Gestor de protocolos no disponible")
            
            # Asegurar que hay evaluador
            if not self.current_evaluator:
                if not self.change_evaluator():
                    return False
            
            # Crear datos de la prueba
            test_data = {
                'id': f"test_{int(time.time())}",
                'tipo': protocol_data.get('protocol_type', 'desconocido'),
                'nombre': protocol_data.get('protocol_name', 'Prueba'),
                'fecha_creacion': time.strftime("%Y-%m-%d %H:%M:%S"),
                'evaluador': self.current_evaluator,
                'estado': 'pendiente',
                'comentarios': ''
            }
            
            # Agregar al archivo .siev
            test_id = self._add_test_to_siev(test_data)
            
            if test_id:
                # Agregar al tree widget
                self._add_test_to_tree(test_data, test_id)
                
                # Actualizar estado
                self.current_test_id = test_id
                self.current_protocol = test_data['tipo']
                
                # Emitir señal
                self.test_created.emit(test_id, test_data)
                
                print(f"Prueba creada: {test_data['nombre']} por {self.current_evaluator}")
                return True
            else:
                raise Exception("Error agregando prueba al archivo .siev")
                
        except Exception as e:
            QMessageBox.critical(self.main_window, "Error", f"Error creando prueba: {e}")
            return False
    
    def _add_test_to_siev(self, test_data: Dict) -> Optional[str]:
        """Agrega una prueba al archivo .siev"""
        try:
            if not self.siev_manager or not self.current_user_siev:
                raise Exception("Sistema de usuarios no disponible")
            
            success = self.siev_manager.add_test_to_siev(self.current_user_siev, test_data)
            
            if success:
                return test_data.get('id')
            else:
                raise Exception("Error agregando prueba al archivo .siev")
                
        except Exception as e:
            print(f"Error agregando prueba al .siev: {e}")
            return None
    
    def _add_test_to_tree(self, test_data: Dict, test_id: str):
        """Agrega una prueba al tree widget"""
        try:
            if not self.test_tree_widget:
                return
            
            item = QTreeWidgetItem()
            
            test_name = test_data.get('tipo', 'Desconocido')
            estado = test_data.get('estado', 'pendiente')
            
            item.setText(0, f"{self.protocol_names.get(test_name, test_name)} - {estado}")
            item.setData(0, 0x0100, test_id)  # Qt.UserRole
            
            self.test_tree_widget.addTopLevelItem(item)
            
            # Seleccionar el nuevo item
            self.test_tree_widget.setCurrentItem(item)
            
        except Exception as e:
            print(f"Error agregando prueba al árbol: {e}")
    
    def change_evaluator(self) -> bool:
        """
        Cambia el evaluador actual.
        
        Returns:
            bool: True si se cambió exitosamente
        """
        try:
            from libs.core.protocol_manager import EvaluatorDialog
            
            dialog = EvaluatorDialog(self.main_window)
            if dialog.exec() == QDialog.Accepted:
                evaluator = dialog.get_evaluator_name()
                if evaluator:
                    self.current_evaluator = evaluator
                    self.evaluator_changed.emit(evaluator)
                    return True
            
            return False
            
        except Exception as e:
            QMessageBox.critical(self.main_window, "Error", f"Error cambiando evaluador: {e}")
            return False
    
    # === GESTIÓN DE ESTÍMULOS ===
    
    def prepare_test_with_stimulus(self, protocol_type: str) -> bool:
        """
        Prepara una prueba que requiere estímulos.
        
        Args:
            protocol_type: Tipo de protocolo
            
        Returns:
            bool: True si se preparó exitosamente
        """
        try:
            if not self.stimulus_manager:
                raise Exception("Gestor de estímulos no disponible")
            
            # Abrir ventana de estímulos
            success = self.stimulus_manager.open_stimulus_window(protocol_type)
            
            if success:
                self.test_preparation_mode = True
                self.test_ready_to_start = True
                self.stimulus_window_opened.emit(protocol_type)
                print(f"Ventana de estímulos abierta para: {protocol_type}")
                return True
            else:
                raise Exception("Error abriendo ventana de estímulos")
                
        except Exception as e:
            print(f"Error preparando test con estímulos: {e}")
            return False
    
    def close_stimulus_window(self):
        """Cierra la ventana de estímulos"""
        try:
            if self.stimulus_manager:
                self.stimulus_manager.close_stimulus_window()
            
            self.test_preparation_mode = False
            self.test_ready_to_start = False
            self.stimulus_window_closed.emit()
            
        except Exception as e:
            print(f"Error cerrando ventana de estímulos: {e}")
    
    # === CONTROL DE TESTS ===
    
    def start_current_test(self) -> bool:
        """
        Inicia el test actual.
        
        Returns:
            bool: True si se inició exitosamente
        """
        try:
            if not self.current_test_id:
                raise Exception("No hay test seleccionado")
            
            if not self.protocol_manager:
                raise Exception("Gestor de protocolos no disponible")
            
            # Iniciar en protocol manager
            success = self.protocol_manager.start_test(self.current_test_id)
            
            if success:
                self.test_started.emit(self.current_test_id)
                return True
            else:
                raise Exception("Error iniciando test en ProtocolManager")
                
        except Exception as e:
            print(f"Error iniciando test: {e}")
            return False
    
    def finalize_current_test(self, test_results: Dict, stopped_manually: bool = False) -> bool:
        """
        Finaliza el test actual.
        
        Args:
            test_results: Resultados del test
            stopped_manually: Si fue detenido manualmente
            
        Returns:
            bool: True si se finalizó exitosamente
        """
        try:
            if not self.current_test_id:
                raise Exception("No hay test actual")
            
            if not self.protocol_manager:
                raise Exception("Gestor de protocolos no disponible")
            
            # Finalizar en protocol manager
            success = self.protocol_manager.finalize_test(
                self.current_test_id, 
                stopped_manually=stopped_manually
            )
            
            if success:
                # Cerrar estímulos si están abiertos
                self.close_stimulus_window()
                
                # Emitir señal
                self.test_completed.emit(self.current_test_id, test_results)
                
                return True
            else:
                raise Exception("Error finalizando test en ProtocolManager")
                
        except Exception as e:
            print(f"Error finalizando test: {e}")
            return False
    
    # === INFORMACIÓN DE ESTADO ===
    
    def get_current_user_info(self) -> str:
        """Obtiene información del usuario actual"""
        try:
            if not self.current_user_data:
                return "Sin usuario seleccionado"
            
            user_name = self.current_user_data.get('nombre', 'Desconocido')
            user_id = self.current_user_data.get('rut_id', '')
            
            if user_id:
                return f"{user_name} ({user_id})"
            else:
                return user_name
                
        except Exception as e:
            print(f"Error obteniendo info de usuario: {e}")
            return "Error obteniendo usuario"
    
    def get_current_test_info(self) -> Dict[str, Any]:
        """Obtiene información del test actual"""
        return {
            'test_id': self.current_test_id,
            'protocol': self.current_protocol,
            'evaluator': self.current_evaluator,
            'needs_stimulus': self.current_protocol in self.stimulus_protocols if self.current_protocol else False,
            'preparation_mode': self.test_preparation_mode,
            'ready_to_start': self.test_ready_to_start
        }
    
    def has_user_loaded(self) -> bool:
        """Verifica si hay un usuario cargado"""
        return self.current_user_siev is not None
    
    def has_test_selected(self) -> bool:
        """Verifica si hay un test seleccionado"""
        return self.current_test_id is not None
    
    def protocol_needs_stimulus(self, protocol_type: str) -> bool:
        """Verifica si un protocolo necesita estímulos"""
        return protocol_type in self.stimulus_protocols
    
    # === CLEANUP ===
    
    def cleanup(self):
        """Limpia recursos del sistema de tests"""
        try:
            # Cerrar usuario actual
            self.close_current_user()
            
            # Cerrar ventana de estímulos
            self.close_stimulus_window()
            
            print("TestManager limpiado")
            
        except Exception as e:
            print(f"Error durante cleanup de tests: {e}")