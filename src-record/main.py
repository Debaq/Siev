import sys
import os

# Obtener el directorio actual del script
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')

# Agregar src al path de Python
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Ahora importar
try:
    from ui.main_window import PatientRecordSystem
    from PySide6.QtWidgets import QApplication
    
    def main():
        app = QApplication(sys.argv)
        app.setApplicationName("Sistema de Registro con Cámara")
        
        window = PatientRecordSystem()
        window.show()
        
        sys.exit(app.exec())

    if __name__ == "__main__":
        main()
        
except ImportError as e:
    print(f"Error de importación: {e}")
    print(f"Directorio actual: {current_dir}")
    print(f"Directorio src: {src_dir}")
    print(f"¿Existe src?: {os.path.exists(src_dir)}")
    
    if os.path.exists(src_dir):
        print("Contenido de src:")
        for item in os.listdir(src_dir):
            print(f"  - {item}")
    
    sys.exit(1)