import sys
import subprocess
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout, 
                            QLabel, QPushButton, QProgressBar, QMessageBox)
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QFont


class DeploymentWorker(QThread):
    """Worker thread para deployment sin bloquear la UI"""
    
    progress_changed = Signal(int)  # 0-100
    status_changed = Signal(str)
    finished = Signal(bool, str)  # success, message
    
    def __init__(self, project_path):
        super().__init__()
        self.project_path = Path(project_path)
        
    def run(self):
        """Ejecuta el deployment de development -> alpha_version"""
        try:
            self.status_changed.emit("Verificando repositorio...")
            self.progress_changed.emit(10)
            
            # Verificar si es repositorio Git
            if not self._is_git_repo():
                self.finished.emit(False, "No es un repositorio Git válido")
                return
            
            self.status_changed.emit("Verificando rama development...")
            self.progress_changed.emit(20)
            
            # Verificar que existe rama development
            if not self._branch_exists("development"):
                self.finished.emit(False, "La rama 'development' no existe")
                return
            
            self.status_changed.emit("Cambiando a rama development...")
            self.progress_changed.emit(30)
            
            # Checkout a development
            if not self._checkout_branch("development"):
                self.finished.emit(False, "Error al cambiar a rama development")
                return
            
            self.status_changed.emit("Descartando cambios locales...")
            self.progress_changed.emit(40)
            
            # Descartar cambios locales
            if not self._reset_hard():
                self.finished.emit(False, "Error al descartar cambios locales")
                return
            
            self.status_changed.emit("Creando/actualizando rama alpha_version...")
            self.progress_changed.emit(60)
            
            # Crear o resetear rama alpha_version
            if not self._create_or_reset_alpha():
                self.finished.emit(False, "Error al crear/actualizar rama alpha_version")
                return
            
            self.status_changed.emit("Subiendo cambios al repositorio remoto...")
            self.progress_changed.emit(80)
            
            # Push alpha_version al remoto
            if not self._push_alpha():
                self.finished.emit(False, "Error al subir rama alpha_version")
                return
            
            self.status_changed.emit("Deployment completado exitosamente")
            self.progress_changed.emit(100)
            
            self.finished.emit(True, "Deployment realizado correctamente:\ndevelopment → alpha_version")
            
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
    
    def _branch_exists(self, branch_name):
        """Verifica si una rama existe"""
        try:
            result = subprocess.run(
                ["git", "show-ref", "--verify", f"refs/heads/{branch_name}"],
                cwd=self.project_path,
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            return result.returncode == 0
        except:
            return False
    
    def _checkout_branch(self, branch_name):
        """Hace checkout a una rama específica"""
        try:
            result = subprocess.run(
                ["git", "checkout", branch_name],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                timeout=30
            )
            return result.returncode == 0
        except:
            return False
    
    def _reset_hard(self):
        """Descarta todos los cambios locales"""
        try:
            result = subprocess.run(
                ["git", "reset", "--hard", "HEAD"],
                cwd=self.project_path,
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                timeout=30
            )
            return result.returncode == 0
        except:
            return False
    
    def _create_or_reset_alpha(self):
        """Crea o resetea la rama alpha_version con el contenido de development"""
        try:
            # Si alpha_version existe, la eliminamos
            subprocess.run(
                ["git", "branch", "-D", "alpha_version"],
                cwd=self.project_path,
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            
            # Crear nueva rama alpha_version desde development actual
            result = subprocess.run(
                ["git", "checkout", "-b", "alpha_version"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                timeout=30
            )
            return result.returncode == 0
        except:
            return False
    
    def _push_alpha(self):
        """Push de la rama alpha_version al remoto"""
        try:
            result = subprocess.run(
                ["git", "push", "origin", "alpha_version", "--force"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                timeout=60
            )
            return result.returncode == 0
        except:
            return False


class DeploymentDialog(QDialog):
    """Ventana para el proceso de deployment"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.worker = None
        
    def setup_ui(self):
        """Configura la interfaz de usuario"""
        self.setWindowTitle("Deployment - development → alpha_version")
        self.setFixedSize(450, 250)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Título
        title = QLabel("Deployment de Rama")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Mensaje
        self.message_label = QLabel("¿Desea hacer deployment de development → alpha_version?\n\n"
                                  "⚠️ ADVERTENCIA: Se perderá todo el contenido actual de alpha_version")
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
        
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        self.deploy_button = QPushButton("Hacer Deployment")
        self.deploy_button.setDefault(True)
        self.deploy_button.clicked.connect(self.start_deployment)
        self.deploy_button.setStyleSheet("""
            QPushButton {
                background-color: #FF5722;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #E64A19;
            }
        """)
        button_layout.addWidget(self.deploy_button)
        
        layout.addLayout(button_layout)
    
    def start_deployment(self):
        """Inicia el proceso de deployment"""
        # Cambiar UI para mostrar progreso
        self.message_label.setText("Ejecutando deployment...")
        self.progress_bar.setVisible(True)
        self.status_label.setVisible(True)
        self.deploy_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        
        # Obtener ruta del proyecto
        import os
        if getattr(sys, "frozen", False):
            project_path = os.path.dirname(sys.executable)
        else:
            project_path = os.path.dirname(os.path.abspath(__file__))
        
        # Crear worker thread
        self.worker = DeploymentWorker(project_path)
        self.worker.progress_changed.connect(self.progress_bar.setValue)
        self.worker.status_changed.connect(self.status_label.setText)
        self.worker.finished.connect(self.on_deployment_finished)
        
        # Iniciar deployment
        self.worker.start()
    
    def on_deployment_finished(self, success, message):
        """Maneja la finalización del deployment"""
        if success:
            self.message_label.setText("¡Deployment Completado!")
            self.status_label.setText(message)
            self.status_label.setStyleSheet("color: green;")
            QMessageBox.information(self, "Éxito", message)
        else:
            self.message_label.setText("Error en el Deployment")
            self.status_label.setText(message)
            self.status_label.setStyleSheet("color: red;")
            QMessageBox.critical(self, "Error", message)
        
        self.deploy_button.setText("Cerrar")
        self.deploy_button.setEnabled(True)
        self.deploy_button.clicked.disconnect()
        self.deploy_button.clicked.connect(self.accept)
        self.cancel_button.setVisible(False)


def main():
    """Punto de entrada principal"""
    app = QApplication(sys.argv)
    
    dialog = DeploymentDialog()
    dialog.exec()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())