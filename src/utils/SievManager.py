import tarfile
import json
import os
import time
import shutil
from io import BytesIO
from typing import Dict, List, Optional, Any
import tempfile


class SievManager:
    """
    Gestor de archivos .siev (tar.gz) que contienen datos completos de usuarios VNG.
    Maneja creación, actualización y extracción de expedientes de usuarios.
    """
    
    def __init__(self, base_path: str = None):
        """
        Inicializa el gestor de archivos .siev
        
        Args:
            base_path: Directorio base donde se guardan los archivos .siev
        """
        if base_path is None:
            base_path = os.path.expanduser("~/siev_data/users")
        
        self.base_path = base_path
        os.makedirs(self.base_path, exist_ok=True)
    
    def create_user_siev(self, user_data: Dict, siev_path: str = None) -> str:
        """
        Crea un nuevo archivo .siev para un usuario
        
        Args:
            user_data: Datos del usuario (nombre, edad, etc.)
            siev_path: Ruta específica del archivo, si no se genera automáticamente
            
        Returns:
            Ruta del archivo .siev creado
        """
        # Generar nombre de archivo si no se proporciona
        if siev_path is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            user_name = user_data.get('nombre', 'usuario')
            if user_name and user_name != 'None':
                filename = f"{user_name}_{timestamp}.siev"
            else:
                filename = f"usuario_{timestamp}.siev"
            siev_path = os.path.join(self.base_path, filename)
        
        # Crear estructura JSON inicial
        initial_data = {
            "usuario": user_data or {
                "nombre": None,
                "edad": None,
                "genero": None,
                "id_paciente": None,
                "fecha_creacion": time.time(),
                "notas": None
            },
            "pruebas": [],
            "metadata": {
                "version": "1.0",
                "creado": time.time(),
                "ultima_actualizacion": time.time(),
                "total_pruebas": 0
            }
        }
        
        # Crear archivo .siev usando archivo temporal
        temp_path = siev_path + "_temp"
        
        try:
            with tarfile.open(temp_path, 'w:gz') as tar:
                # Crear estructura de directorios
                self._create_directory_structure(tar)
                
                # Agregar JSON inicial
                self._add_json_to_tar(tar, initial_data, "metadata.json")
                self._add_json_to_tar(tar, initial_data, "metadata_backup.json")
            
            # Renombrar archivo temporal a definitivo
            shutil.move(temp_path, siev_path)
            print(f"Archivo .siev creado: {siev_path}")
            return siev_path
            
        except Exception as e:
            # Limpiar archivo temporal si hay error
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise Exception(f"Error creando archivo .siev: {e}")
    
    def add_test_to_siev(self, siev_path: str, test_data: Dict, 
                        csv_data: List[Dict] = None, video_path: str = None) -> bool:
        """
        Agrega una nueva prueba al archivo .siev existente
        
        Args:
            siev_path: Ruta del archivo .siev
            test_data: Datos de la prueba (tipo, fecha, etc.)
            csv_data: Datos CSV de la prueba
            video_path: Ruta del archivo de video (si existe)
            
        Returns:
            True si se agregó exitosamente
        """
        if not os.path.exists(siev_path):
            raise FileNotFoundError(f"Archivo .siev no encontrado: {siev_path}")
        
        temp_path = siev_path + "_temp"
        
        try:
            # Leer datos actuales
            current_data = self._read_metadata_from_siev(siev_path)
            
            # Generar ID único para la prueba
            test_id = test_data.get('id') or f"test_{int(time.time())}"
            
            # Preparar datos de la nueva prueba
            new_test = {
                "id": test_id,
                "tipo": test_data.get('tipo', 'desconocido'),
                "fecha": test_data.get('fecha', time.time()),
                "hora_inicio": test_data.get('hora_inicio', time.time()),
                "hora_fin": test_data.get('hora_fin', None),
                "evaluador": test_data.get('evaluador', None),
                "comentarios": test_data.get('comentarios', None),
                "archivos": {
                    "csv": f"data/{test_id}.csv" if csv_data else None,
                    "video": f"videos/{test_id}.mp4" if video_path else None
                },
                "metadata_prueba": test_data.get('metadata_prueba', {})
            }
            
            # Agregar nueva prueba
            current_data["pruebas"].append(new_test)
            current_data["metadata"]["total_pruebas"] += 1
            current_data["metadata"]["ultima_actualizacion"] = time.time()
            
            # Crear nuevo archivo .siev
            with tarfile.open(temp_path, 'w:gz') as new_tar:
                # Copiar contenido existente (excepto metadata)
                self._copy_existing_content(siev_path, new_tar, exclude=['metadata.json'])
                
                # Agregar nuevos archivos
                if csv_data:
                    self._add_csv_to_tar(new_tar, csv_data, f"data/{test_id}.csv")
                
                if video_path and os.path.exists(video_path):
                    self._add_file_to_tar(new_tar, video_path, f"videos/{test_id}.mp4")
                
                # Actualizar metadata con backup
                self._add_json_to_tar(new_tar, current_data, "metadata_backup.json")
                self._add_json_to_tar(new_tar, current_data, "metadata.json")
            
            # Reemplazar archivo original
            shutil.move(temp_path, siev_path)
            print(f"Prueba agregada al archivo .siev: {test_id}")
            return True
            
        except Exception as e:
            # Limpiar archivo temporal si hay error
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise Exception(f"Error agregando prueba: {e}")
    
    def update_test_metadata(self, siev_path: str, test_id: str, 
                           evaluator: str = None, comments: str = None) -> bool:
        """
        Actualiza metadatos de una prueba específica
        
        Args:
            siev_path: Ruta del archivo .siev
            test_id: ID de la prueba a actualizar
            evaluator: Nombre del evaluador
            comments: Comentarios de la prueba
            
        Returns:
            True si se actualizó exitosamente
        """
        if not os.path.exists(siev_path):
            raise FileNotFoundError(f"Archivo .siev no encontrado: {siev_path}")
        
        temp_path = siev_path + "_temp"
        
        try:
            # Leer datos actuales
            current_data = self._read_metadata_from_siev(siev_path)
            
            # Buscar y actualizar la prueba
            test_found = False
            for test in current_data["pruebas"]:
                if test["id"] == test_id:
                    if evaluator is not None:
                        test["evaluador"] = evaluator
                    if comments is not None:
                        test["comentarios"] = comments
                    test["hora_fin"] = time.time()
                    test_found = True
                    break
            
            if not test_found:
                raise ValueError(f"Prueba con ID {test_id} no encontrada")
            
            current_data["metadata"]["ultima_actualizacion"] = time.time()
            
            # Crear nuevo archivo .siev
            with tarfile.open(temp_path, 'w:gz') as new_tar:
                # Copiar todo el contenido existente excepto metadata
                self._copy_existing_content(siev_path, new_tar, exclude=['metadata.json'])
                
                # Actualizar metadata
                self._add_json_to_tar(new_tar, current_data, "metadata_backup.json")
                self._add_json_to_tar(new_tar, current_data, "metadata.json")
            
            # Reemplazar archivo original
            shutil.move(temp_path, siev_path)
            print(f"Metadatos de prueba actualizados: {test_id}")
            return True
            
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise Exception(f"Error actualizando metadatos: {e}")
    
    def extract_siev_data(self, siev_path: str, output_dir: str) -> bool:
        """
        Extrae todo el contenido de un archivo .siev
        
        Args:
            siev_path: Ruta del archivo .siev
            output_dir: Directorio donde extraer
            
        Returns:
            True si se extrajo exitosamente
        """
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            with tarfile.open(siev_path, 'r:gz') as tar:
                tar.extractall(output_dir)
            
            print(f"Archivo .siev extraído en: {output_dir}")
            return True
            
        except Exception as e:
            raise Exception(f"Error extrayendo archivo .siev: {e}")
    
    def validate_siev(self, siev_path: str) -> Dict[str, Any]:
        """
        Valida la integridad de un archivo .siev
        
        Args:
            siev_path: Ruta del archivo .siev
            
        Returns:
            Diccionario con resultado de validación
        """
        try:
            result = {
                "valid": False,
                "errors": [],
                "warnings": [],
                "metadata": None
            }
            
            if not os.path.exists(siev_path):
                result["errors"].append("Archivo no existe")
                return result
            
            # Validar que es un tar válido
            try:
                with tarfile.open(siev_path, 'r:gz') as tar:
                    members = tar.getnames()
            except Exception as e:
                result["errors"].append(f"No es un archivo tar válido: {e}")
                return result
            
            # Validar estructura
            required_files = ["metadata.json"]
            for req_file in required_files:
                if req_file not in members:
                    result["errors"].append(f"Archivo requerido faltante: {req_file}")
            
            # Validar metadata JSON
            try:
                metadata = self._read_metadata_from_siev(siev_path)
                result["metadata"] = metadata
                
                # Validar estructura del JSON
                required_keys = ["usuario", "pruebas", "metadata"]
                for key in required_keys:
                    if key not in metadata:
                        result["errors"].append(f"Clave faltante en metadata: {key}")
                
            except Exception as e:
                result["errors"].append(f"Error leyendo metadata: {e}")
            
            # Verificar backup
            if "metadata_backup.json" not in members:
                result["warnings"].append("Archivo de backup faltante")
            
            result["valid"] = len(result["errors"]) == 0
            return result
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Error durante validación: {e}"],
                "warnings": [],
                "metadata": None
            }
    
    def get_user_tests(self, siev_path: str) -> List[Dict]:
        """
        Obtiene la lista de pruebas de un usuario
        
        Args:
            siev_path: Ruta del archivo .siev
            
        Returns:
            Lista de pruebas con metadatos
        """
        try:
            metadata = self._read_metadata_from_siev(siev_path)
            return metadata.get("pruebas", [])
        except Exception as e:
            raise Exception(f"Error obteniendo lista de pruebas: {e}")
    
    def get_user_info(self, siev_path: str) -> Dict:
        """
        Obtiene información del usuario
        
        Args:
            siev_path: Ruta del archivo .siev
            
        Returns:
            Datos del usuario
        """
        try:
            metadata = self._read_metadata_from_siev(siev_path)
            return metadata.get("usuario", {})
        except Exception as e:
            raise Exception(f"Error obteniendo información de usuario: {e}")
    
    # Métodos auxiliares privados
    
    def _create_directory_structure(self, tar: tarfile.TarFile):
        """Crea la estructura de directorios dentro del tar"""
        dirs = ["data/", "videos/"]
        for dir_name in dirs:
            tarinfo = tarfile.TarInfo(name=dir_name)
            tarinfo.type = tarfile.DIRTYPE
            tarinfo.mode = 0o755
            tarinfo.mtime = int(time.time())
            tar.addfile(tarinfo)
    
    def _add_json_to_tar(self, tar: tarfile.TarFile, data: Dict, filename: str):
        """Agrega un archivo JSON al tar"""
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        json_bytes = json_str.encode('utf-8')
        
        tarinfo = tarfile.TarInfo(name=filename)
        tarinfo.size = len(json_bytes)
        tarinfo.mtime = int(time.time())
        
        tar.addfile(tarinfo, BytesIO(json_bytes))
    
    def _add_csv_to_tar(self, tar: tarfile.TarFile, csv_data: List[Dict], filename: str):
        """Agrega datos CSV al tar"""
        import csv
        import io
        
        if not csv_data:
            return
        
        try:
            # Convertir numpy types a tipos nativos de Python si es necesario
            processed_data = []
            for row in csv_data:
                processed_row = {}
                for key, value in row.items():
                    # Convertir numpy types a tipos nativos
                    if hasattr(value, 'item'):  # numpy types tienen el método .item()
                        processed_row[key] = value.item()
                    else:
                        processed_row[key] = value
                processed_data.append(processed_row)
            
            # Usar StringIO para escribir texto CSV
            csv_text_buffer = io.StringIO()
            
            # Escribir CSV como texto
            fieldnames = processed_data[0].keys() if processed_data else []
            writer = csv.DictWriter(csv_text_buffer, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(processed_data)
            
            # Obtener el texto CSV y convertir a bytes
            csv_text = csv_text_buffer.getvalue()
            csv_bytes = csv_text.encode('utf-8')
            
            # Crear TarInfo y agregar al tar
            tarinfo = tarfile.TarInfo(name=filename)
            tarinfo.size = len(csv_bytes)
            tarinfo.mtime = int(time.time())
            
            tar.addfile(tarinfo, BytesIO(csv_bytes))
            
            print(f"CSV agregado al tar: {filename} ({len(processed_data)} filas)")
            
        except Exception as e:
            print(f"Error agregando CSV al tar: {e}")
            raise
    
    def _add_file_to_tar(self, tar: tarfile.TarFile, file_path: str, archive_name: str):
        """Agrega un archivo existente al tar"""
        tar.add(file_path, arcname=archive_name)
    
    def _copy_existing_content(self, source_siev: str, target_tar: tarfile.TarFile, 
                             exclude: List[str] = None):
        """Copia contenido existente de un .siev a otro, excluyendo archivos específicos"""
        exclude = exclude or []
        
        with tarfile.open(source_siev, 'r:gz') as source_tar:
            for member in source_tar.getmembers():
                if member.name not in exclude:
                    if member.isfile():
                        file_data = source_tar.extractfile(member)
                        target_tar.addfile(member, file_data)
                    else:
                        target_tar.addfile(member)
    
    def _read_metadata_from_siev(self, siev_path: str) -> Dict:
        """Lee el metadata JSON de un archivo .siev"""
        try:
            with tarfile.open(siev_path, 'r:gz') as tar:
                try:
                    # Intentar leer metadata principal
                    metadata_file = tar.extractfile('metadata.json')
                    metadata = json.load(metadata_file)
                    return metadata
                except:
                    # Si falla, intentar backup
                    backup_file = tar.extractfile('metadata_backup.json')
                    metadata = json.load(backup_file)
                    print("ADVERTENCIA: Usando archivo de backup de metadata")
                    return metadata
        except Exception as e:
            raise Exception(f"Error leyendo metadata: {e}")
    
    def list_user_sievs(self) -> List[str]:
        """
        Lista todos los archivos .siev en el directorio base
        
        Returns:
            Lista de nombres de archivos .siev
        """
        try:
            siev_files = []
            if os.path.exists(self.base_path):
                for file in os.listdir(self.base_path):
                    if file.endswith('.siev'):
                        siev_files.append(os.path.join(self.base_path, file))
            
            # Ordenar por fecha de modificación
            siev_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            return siev_files
        except Exception as e:
            print(f"Error listando archivos .siev: {e}")
            return []