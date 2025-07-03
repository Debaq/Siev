#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Document Manager - Gestor de documentos .siev (archivos comprimidos con datos de paciente)
"""

import os
import json
import zipfile
import tempfile
import shutil
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from PySide6.QtCore import QObject, Signal


class DocumentManager(QObject):
    """
    Gestor de documentos .siev para manejo de datos de paciente.
    Los archivos .siev son ZIP comprimidos con estructura interna definida.
    """
    
    # Señales
    document_loaded = Signal(dict)  # metadata del documento
    document_saved = Signal(str)    # ruta del archivo guardado
    test_added = Signal(dict)       # datos de la prueba agregada
    test_removed = Signal(str)      # ID de la prueba eliminada
    error_occurred = Signal(str)    # mensaje de error
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Estado del documento actual
        self.current_document_path = None
        self.document_metadata = None
        self.tests_data = {}  # {test_id: test_data}
        self.temp_dir = None
        self.is_modified = False
        
        # Estructura interna del documento
        self.internal_structure = {
            "metadata.json": "Datos básicos del paciente",
            "config.json": "Configuración del documento", 
            "tests/": "Carpeta con datos de pruebas",
            "videos/": "Carpeta con videos grabados",
            "reports/": "Carpeta con informes generados"
        }
        
        print("✅ DocumentManager inicializado")
    
    def create_new_document(self, patient_data: Dict[str, Any]) -> bool:
        """
        Crear nuevo documento con datos del paciente.
        
        Args:
            patient_data: Datos del paciente desde PatientDataDialog
            
        Returns:
            bool: True si se creó correctamente
        """
        try:
            print("📄 Creando nuevo documento...")
            
            # Limpiar documento anterior
            self._cleanup_current_document()
            
            # Crear directorio temporal
            self.temp_dir = tempfile.mkdtemp(prefix="siev_doc_")
            
            # Preparar metadata
            self.document_metadata = {
                "version": "1.0",
                "document_type": "siev_patient",
                "created_date": datetime.now().isoformat(),
                "last_modified": datetime.now().isoformat(),
                "patient": patient_data,
                "tests_count": 0,
                "last_test_id": 0
            }
            
            # Crear estructura de carpetas
            self._create_internal_structure()
            
            # Guardar metadata inicial
            self._save_metadata()
            
            # Crear configuración inicial
            self._create_initial_config()
            
            # Marcar como modificado
            self.is_modified = True
            
            print(f"✅ Documento creado para: {patient_data.get('name', 'Sin nombre')}")
            self.document_loaded.emit(self.document_metadata)
            
            return True
            
        except Exception as e:
            error_msg = f"Error creando documento: {e}"
            print(f"❌ {error_msg}")
            self.error_occurred.emit(error_msg)
            return False
    
    def open_document(self, file_path: str) -> bool:
        """
        Abrir documento .siev existente.
        
        Args:
            file_path: Ruta del archivo .siev
            
        Returns:
            bool: True si se abrió correctamente
        """
        try:
            print(f"📂 Abriendo documento: {file_path}")
            
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
            
            # Limpiar documento anterior
            self._cleanup_current_document()
            
            # Crear directorio temporal
            self.temp_dir = tempfile.mkdtemp(prefix="siev_doc_")
            
            # Extraer archivo .siev
            with zipfile.ZipFile(file_path, 'r') as zip_file:
                zip_file.extractall(self.temp_dir)
            
            # Cargar metadata
            metadata_path = os.path.join(self.temp_dir, "metadata.json")
            if not os.path.exists(metadata_path):
                raise ValueError("Archivo .siev inválido: falta metadata.json")
            
            with open(metadata_path, 'r', encoding='utf-8') as f:
                self.document_metadata = json.load(f)
            
            # Cargar pruebas existentes
            self._load_existing_tests()
            
            # Establecer ruta actual
            self.current_document_path = file_path
            self.is_modified = False
            
            patient_name = self.document_metadata.get("patient", {}).get("name", "Sin nombre")
            print(f"✅ Documento abierto: {patient_name}")
            self.document_loaded.emit(self.document_metadata)
            
            return True
            
        except Exception as e:
            error_msg = f"Error abriendo documento: {e}"
            print(f"❌ {error_msg}")
            self.error_occurred.emit(error_msg)
            return False
    
    def save_document(self, file_path: Optional[str] = None) -> bool:
        """
        Guardar documento actual como .siev.
        
        Args:
            file_path: Ruta donde guardar (None para usar la actual)
            
        Returns:
            bool: True si se guardó correctamente
        """
        try:
            if not self.temp_dir or not self.document_metadata:
                raise ValueError("No hay documento activo para guardar")
            
            # Usar ruta proporcionada o la actual
            target_path = file_path or self.current_document_path
            
            if not target_path:
                raise ValueError("No se especificó ruta para guardar")
            
            print(f"💾 Guardando documento: {target_path}")
            
            # Actualizar metadata antes de guardar
            self.document_metadata["last_modified"] = datetime.now().isoformat()
            self.document_metadata["tests_count"] = len(self.tests_data)
            self._save_metadata()
            
            # Crear archivo .siev (ZIP)
            with zipfile.ZipFile(target_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Agregar todos los archivos del directorio temporal
                for root, dirs, files in os.walk(self.temp_dir):
                    for file in files:
                        file_path_abs = os.path.join(root, file)
                        file_path_rel = os.path.relpath(file_path_abs, self.temp_dir)
                        zip_file.write(file_path_abs, file_path_rel)
            
            # Actualizar estado
            self.current_document_path = target_path
            self.is_modified = False
            
            print("✅ Documento guardado correctamente")
            self.document_saved.emit(target_path)
            
            return True
            
        except Exception as e:
            error_msg = f"Error guardando documento: {e}"
            print(f"❌ {error_msg}")
            self.error_occurred.emit(error_msg)
            return False
    
    def add_test_data(self, protocol_name: str, test_data: Dict[str, Any]) -> str:
        """
        Agregar datos de una prueba realizada.
        
        Args:
            protocol_name: Nombre del protocolo ejecutado
            test_data: Datos de la prueba (gráficos, resultados, etc.)
            
        Returns:
            str: ID de la prueba creada
        """
        try:
            if not self.document_metadata:
                raise ValueError("No hay documento activo")
            
            # Generar ID único para la prueba
            self.document_metadata["last_test_id"] += 1
            test_id = f"test_{self.document_metadata['last_test_id']:03d}"
            
            # Preparar datos de la prueba
            test_entry = {
                "test_id": test_id,
                "protocol_name": protocol_name,
                "timestamp": datetime.now().isoformat(),
                "data": test_data,
                "status": "completed"
            }
            
            # Guardar en memoria
            self.tests_data[test_id] = test_entry
            
            # Guardar en archivo
            test_file_path = os.path.join(self.temp_dir, "tests", f"{test_id}.json")
            with open(test_file_path, 'w', encoding='utf-8') as f:
                json.dump(test_entry, f, indent=2, ensure_ascii=False)
            
            # Marcar como modificado
            self.is_modified = True
            
            print(f"✅ Prueba agregada: {test_id} ({protocol_name})")
            self.test_added.emit(test_entry)
            
            return test_id
            
        except Exception as e:
            error_msg = f"Error agregando prueba: {e}"
            print(f"❌ {error_msg}")
            self.error_occurred.emit(error_msg)
            return ""
    
    def remove_test(self, test_id: str) -> bool:
        """
        Eliminar una prueba del documento.
        
        Args:
            test_id: ID de la prueba a eliminar
            
        Returns:
            bool: True si se eliminó correctamente
        """
        try:
            if test_id not in self.tests_data:
                raise ValueError(f"Prueba no encontrada: {test_id}")
            
            # Eliminar de memoria
            del self.tests_data[test_id]
            
            # Eliminar archivo
            test_file_path = os.path.join(self.temp_dir, "tests", f"{test_id}.json")
            if os.path.exists(test_file_path):
                os.remove(test_file_path)
            
            # Marcar como modificado
            self.is_modified = True
            
            print(f"✅ Prueba eliminada: {test_id}")
            self.test_removed.emit(test_id)
            
            return True
            
        except Exception as e:
            error_msg = f"Error eliminando prueba: {e}"
            print(f"❌ {error_msg}")
            self.error_occurred.emit(error_msg)
            return False
    
    def get_test_data(self, test_id: str) -> Optional[Dict[str, Any]]:
        """Obtener datos de una prueba específica"""
        return self.tests_data.get(test_id)
    
    def get_all_tests(self) -> Dict[str, Dict[str, Any]]:
        """Obtener todas las pruebas del documento"""
        return self.tests_data.copy()
    
    def get_patient_data(self) -> Optional[Dict[str, Any]]:
        """Obtener datos del paciente"""
        if self.document_metadata:
            return self.document_metadata.get("patient")
        return None
    
    def update_patient_data(self, new_patient_data: Dict[str, Any]) -> bool:
        """
        Actualizar datos del paciente.
        
        Args:
            new_patient_data: Nuevos datos del paciente
            
        Returns:
            bool: True si se actualizó correctamente
        """
        try:
            if not self.document_metadata:
                raise ValueError("No hay documento activo")
            
            self.document_metadata["patient"] = new_patient_data
            self.document_metadata["last_modified"] = datetime.now().isoformat()
            
            self._save_metadata()
            self.is_modified = True
            
            print("✅ Datos del paciente actualizados")
            return True
            
        except Exception as e:
            error_msg = f"Error actualizando datos del paciente: {e}"
            print(f"❌ {error_msg}")
            self.error_occurred.emit(error_msg)
            return False
    
    def close_document(self) -> bool:
        """
        Cerrar documento actual.
        
        Returns:
            bool: True si hay cambios sin guardar
        """
        has_unsaved_changes = self.is_modified
        self._cleanup_current_document()
        return has_unsaved_changes
    
    def is_document_open(self) -> bool:
        """Verificar si hay un documento abierto"""
        return self.document_metadata is not None
    
    def get_document_info(self) -> Dict[str, Any]:
        """Obtener información del documento actual"""
        if not self.document_metadata:
            return {"open": False}
        
        patient = self.document_metadata.get("patient", {})
        
        return {
            "open": True,
            "path": self.current_document_path,
            "patient_name": patient.get("name", "Sin nombre"),
            "patient_id": patient.get("patient_id", "Sin ID"),
            "created_date": self.document_metadata.get("created_date"),
            "last_modified": self.document_metadata.get("last_modified"),
            "tests_count": len(self.tests_data),
            "is_modified": self.is_modified
        }
    
    # === MÉTODOS PRIVADOS ===
    
    def _cleanup_current_document(self):
        """Limpiar documento actual"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                print(f"⚠️ Error limpiando directorio temporal: {e}")
        
        self.temp_dir = None
        self.current_document_path = None
        self.document_metadata = None
        self.tests_data = {}
        self.is_modified = False
    
    def _create_internal_structure(self):
        """Crear estructura interna de carpetas"""
        if not self.temp_dir:
            return
        
        # Crear carpetas principales
        folders = ["tests", "videos", "reports"]
        for folder in folders:
            os.makedirs(os.path.join(self.temp_dir, folder), exist_ok=True)
    
    def _save_metadata(self):
        """Guardar metadata en archivo"""
        if not self.temp_dir or not self.document_metadata:
            return
        
        metadata_path = os.path.join(self.temp_dir, "metadata.json")
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(self.document_metadata, f, indent=2, ensure_ascii=False)
    
    def _create_initial_config(self):
        """Crear configuración inicial del documento"""
        if not self.temp_dir:
            return
        
        config = {
            "version": "1.0",
            "settings": {
                "auto_save": True,
                "backup_enabled": False,
                "compression_level": 6
            },
            "preferences": {
                "default_graph_settings": {},
                "default_export_format": "pdf"
            }
        }
        
        config_path = os.path.join(self.temp_dir, "config.json")
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    def _load_existing_tests(self):
        """Cargar pruebas existentes desde archivos"""
        self.tests_data = {}
        
        tests_dir = os.path.join(self.temp_dir, "tests")
        if not os.path.exists(tests_dir):
            return
        
        for filename in os.listdir(tests_dir):
            if filename.endswith('.json'):
                test_file_path = os.path.join(tests_dir, filename)
                try:
                    with open(test_file_path, 'r', encoding='utf-8') as f:
                        test_data = json.load(f)
                    
                    test_id = test_data.get("test_id")
                    if test_id:
                        self.tests_data[test_id] = test_data
                        
                except Exception as e:
                    print(f"⚠️ Error cargando prueba {filename}: {e}")
        
        print(f"✅ {len(self.tests_data)} pruebas cargadas")
    
    def __del__(self):
        """Destructor para limpiar recursos"""
        self._cleanup_current_document()


# Funciones de conveniencia
def create_document_with_patient_dialog(parent=None) -> Tuple[Optional[DocumentManager], bool]:
    """
    Crear nuevo documento mostrando diálogo de paciente.
    
    Args:
        parent: Widget padre
        
    Returns:
        Tuple (DocumentManager, success)
    """
    from dialogs.patient_data_dialog import show_patient_data_dialog
    
    # Mostrar diálogo de datos del paciente
    patient_data = show_patient_data_dialog(parent=parent)
    
    if patient_data:
        # Crear documento
        doc_manager = DocumentManager()
        success = doc_manager.create_new_document(patient_data)
        return doc_manager, success
    
    return None, False

def open_document_dialog(parent=None) -> Tuple[Optional[DocumentManager], bool]:
    """
    Abrir documento mostrando diálogo de selección.
    
    Args:
        parent: Widget padre
        
    Returns:
        Tuple (DocumentManager, success)
    """
    from PySide6.QtWidgets import QFileDialog
    
    file_path, _ = QFileDialog.getOpenFileName(
        parent,
        "Abrir Documento SIEV",
        "",
        "Documentos SIEV (*.siev);;Todos los archivos (*)"
    )
    
    if file_path:
        doc_manager = DocumentManager()
        success = doc_manager.open_document(file_path)
        return doc_manager, success
    
    return None, False