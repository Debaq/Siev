import sys
import os
import subprocess
import json
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QProgressBar, QPushButton, QTextEdit, QDialog)
from PySide6.QtCore import QThread, Signal, QTimer, Qt
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtCore import QTranslator, QLocale


class GitUpdateWorker(QThread):
    """Worker thread para operaciones Git y pip sin bloquear la UI"""
    
    progress_changed = Signal(int)  # 0-100
    status_changed = Signal(str)
    finished = Signal(bool, str)  # success, message
    
    def __init__(self, project_path, conda_env="vng"):
        super().__init__()
        self.project_path = Path(project_path)
        self.conda_env = conda_env
        self.should_update = False
        
    def run(self):
        """Ejecuta el proceso completo de verificación y actualización"""
        try:
            self.status_changed.emit("Verificando repositorio Git...")
            self.progress_changed.emit(10)
            
            # Verificar si es repositorio Git
            if not self._is_git_repo():
                self.finished.emit(False, "No es un repositorio Git válido")
                return
            
            self.status_changed.emit("Consultando actualizaciones remotas...")
            self.progress_changed.emit(20)
            
            # Verificar conexión y actualizaciones
            if not self._check_remote_updates():
                self.finished.emit(True, "No hay actualizaciones disponibles")
                return
            
            self.status_changed.emit("Descargando actualizaciones...")
            self.progress_changed.emit(40)
            
            # Realizar git pull
            if not self._git_pull():
                self.finished.emit(False, "Error al descargar actualizaciones")
                return
            
            self.status_changed.emit("Verificando dependencias...")
            self.progress_changed.emit(60)
            
            # Verificar e instalar dependencias
            if not self._update_dependencies():
                self.finished.emit(False, "Error al actualizar dependencias")
                return
            
            self.status_changed.emit("Actualización completada exitosamente")
            self.progress_changed.emit(100)
            
            self.finished.emit(True, "Proyecto actualizado correctamente")
            
        except Exception as e:
            self.finished.emit(False, f"Error inesperado: {str(e)}")
    
    def _is_git_repo(self):
        """Verifica si el directorio es un repositorio Git"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            return result.returncode == 0
        except:
            return False
    
    def _check_remote_updates(self):
        """Verifica si hay actualizaciones en el repositorio remoto"""
        try:
            # Fetch para obtener últimos cambios remotos
            subprocess.run(
                ["git", "fetch"],
                cwd=self.project_path,
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                timeout=30
            )
            
            # Comparar HEAD local vs remoto
            local_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            
            remote_result = subprocess.run(
                ["git", "rev-parse", "@{u}"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            
            if local_result.returncode == 0 and remote_result.returncode == 0:
                local_hash = local_result.stdout.strip()
                remote_hash = remote_result.stdout.strip()
                return local_hash != remote_hash
            
            return False
            
        except subprocess.TimeoutExpired:
            return False
        except:
            return False
    
    def _git_pull(self):
        """Realiza git pull para actualizar el repositorio"""
        try:
            result = subprocess.run(
                ["git", "pull"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                timeout=60
            )
            return result.returncode == 0
        except:
            return False
    
    def _update_dependencies(self):
        """Verifica e instala nuevas dependencias"""
        try:
            requirements_file = self.project_path / "requirements.txt"
            if not requirements_file.exists():
                return True  # No hay requirements.txt, continuar
            
            # Construir comando para micromamba
            if sys.platform == "win32":
                conda_cmd = ["micromamba", "run", "-n", self.conda_env, "pip", "install", "-r", str(requirements_file)]
            else:
                conda_cmd = ["micromamba", "run", "-n", self.conda_env, "pip", "install", "-r", str(requirements_file)]
            
            result = subprocess.run(
                conda_cmd,
                cwd=self.project_path,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                timeout=300  # 5 minutos para instalar dependencias
            )
            
            return result.returncode == 0
            
        except subprocess.TimeoutExpired:
            return False
        except:
            return True  # Si falla, continuar sin error crítico


class UpdateDialog(QDialog):
    """Ventana para mostrar el proceso de actualización"""
    
    update_completed = Signal(bool)  # True si se actualizó, False si se canceló
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.worker = None
        
    def setup_ui(self):
        """Configura la interfaz de usuario"""
        self.setWindowTitle("Actualizador VNG")
        self.setFixedSize(400, 250)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Título
        title = QLabel("Actualización Disponible")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Mensaje
        self.message_label = QLabel("Se encontraron actualizaciones disponibles en GitHub.\n¿Desea actualizar ahora?")
        self.message_label.setWordWrap(True)
        self.message_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.message_label)
        
        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)
        
        # Botones
        button_layout = QHBoxLayout()
        
        self.cancel_button = QPushButton("Más Tarde")
        self.cancel_button.clicked.connect(self.reject_update)
        button_layout.addWidget(self.cancel_button)
        
        self.update_button = QPushButton("Actualizar Ahora")
        self.update_button.setDefault(True)
        self.update_button.clicked.connect(self.start_update)
        self.update_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        button_layout.addWidget(self.update_button)
        
        layout.addLayout(button_layout)
    
    def start_update(self):
        """Inicia el proceso de actualización"""
        # Cambiar UI para mostrar progreso
        self.message_label.setText("Actualizando proyecto desde GitHub...")
        self.progress_bar.setVisible(True)
        self.status_label.setVisible(True)
        self.update_button.setEnabled(False)
        self.cancel_button.setText("Cancelar")
        
        # Obtener ruta del proyecto
        if getattr(sys, "frozen", False):
            project_path = os.path.dirname(sys.executable)
        else:
            project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Crear worker thread
        self.worker = GitUpdateWorker(project_path)
        self.worker.progress_changed.connect(self.progress_bar.setValue)
        self.worker.status_changed.connect(self.status_label.setText)
        self.worker.finished.connect(self.on_update_finished)
        
        # Iniciar actualización
        self.worker.start()
    
    def on_update_finished(self, success, message):
        """Maneja la finalización del proceso de actualización"""
        if success:
            self.message_label.setText("¡Actualización completada!")
            self.status_label.setText(message)
            self.update_button.setText("Reiniciar Aplicación")
            self.update_button.setEnabled(True)
            self.update_button.clicked.disconnect()
            self.update_button.clicked.connect(self.finish_update)
            self.cancel_button.setVisible(False)
        else:
            self.message_label.setText("Error en la actualización")
            self.status_label.setText(message)
            self.status_label.setStyleSheet("color: red;")
            self.update_button.setText("Continuar sin Actualizar")
            self.update_button.setEnabled(True)
            self.update_button.clicked.disconnect()
            self.update_button.clicked.connect(self.reject_update)
            self.cancel_button.setVisible(False)
    
    def finish_update(self):
        """Finaliza la actualización y señala reinicio"""
        self.update_completed.emit(True)
        self.accept()
    
    def reject_update(self):
        """Rechaza la actualización y continúa"""
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait(3000)
        
        self.update_completed.emit(False)
        self.reject()


class UpdateChecker(QThread):
    """Thread para verificar actualizaciones sin bloquear el inicio"""
    
    update_available = Signal(bool)
    
    def __init__(self, project_path):
        super().__init__()
        self.project_path = Path(project_path)
    
    def run(self):
        """Verifica si hay actualizaciones disponibles"""
        try:
            # Verificar si es repositorio Git
            if not self._is_git_repo():
                self.update_available.emit(False)
                return
            
            # Verificar actualizaciones remotas
            has_updates = self._check_remote_updates()
            self.update_available.emit(has_updates)
            
        except:
            self.update_available.emit(False)
    
    def _is_git_repo(self):
        """Verifica si el directorio es un repositorio Git"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False
    
    def _check_remote_updates(self):
        """Verifica si hay actualizaciones en el repositorio remoto"""
        try:
            # Fetch rápido
            subprocess.run(
                ["git", "fetch"],
                cwd=self.project_path,
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                timeout=10
            )
            
            # Comparar commits
            local_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            
            remote_result = subprocess.run(
                ["git", "rev-parse", "@{u}"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            
            if local_result.returncode == 0 and remote_result.returncode == 0:
                return local_result.stdout.strip() != remote_result.stdout.strip()
            
            return False
            
        except:
            return False


def check_for_updates_and_run():
    """Función principal que verifica actualizaciones y ejecuta la aplicación"""
    app = QApplication(sys.argv)
    
    # Configurar traductor
    translator = QTranslator()
    locale = QLocale.system().name().split("_")[0]
    
    # Obtener rutas
    if getattr(sys, "frozen", False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Cargar traducción
    translations_path = os.path.join(base_path, "resources", "translations")
    translation_file = os.path.join(translations_path, f"{locale}.qm")
    
    if translator.load(translation_file):
        print(f"Loaded translations for {locale}")
        app.installTranslator(translator)
    else:
        print(f"Using default language (en)")
    
    # Verificar actualizaciones
    print("Verificando actualizaciones...")
    
    checker = UpdateChecker(base_path)
    update_dialog = None
    main_window = None
    update_check_completed = False  # Flag para evitar doble ejecución
    
    def on_update_check_finished(has_updates):
        nonlocal update_dialog, main_window, update_check_completed
        
        # Evitar doble ejecución
        if update_check_completed:
            return
        update_check_completed = True
        
        if has_updates:
            print("Actualizaciones disponibles - Mostrando diálogo")
            update_dialog = UpdateDialog()
            update_dialog.update_completed.connect(on_update_completed)
            update_dialog.show()
        else:
            print("No hay actualizaciones - Iniciando aplicación")
            start_main_application()
    
    def on_update_completed(updated):
        nonlocal main_window
        
        if updated:
            print("Aplicación actualizada - Cerrando...")
            # Mostrar mensaje de cierre y cerrar aplicación
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(
                None,
                "Actualización Completada",
                "La aplicación se ha actualizado correctamente.\n\n"
                "La aplicación se cerrará ahora.\n"
                "Vuelva a abrirla para usar la versión actualizada."
            )
            app.quit()
        else:
            print("Continuando sin actualizar")
            start_main_application()
    
    def start_main_application():
        nonlocal main_window
        try:
            from ui.main_window import MainWindow
            main_window = MainWindow()
            main_window.show()
        except ImportError as e:
            print(f"Error importando MainWindow: {e}")
            app.quit()
            return 1
    
    # Conectar señales y iniciar verificación
    checker.update_available.connect(on_update_check_finished)
    checker.start()
    
    # Timeout para evitar espera infinita (solo si no se ha completado)
    def timeout_handler():
        if not update_check_completed:
            print("Timeout en verificación - Iniciando sin actualizar")
            on_update_check_finished(False)
    
    QTimer.singleShot(15000, timeout_handler)
    
    return app.exec()


def main():
    """Punto de entrada principal"""
    return check_for_updates_and_run()


if __name__ == "__main__":
    sys.exit(main())