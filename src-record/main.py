"""Aplicación principal del sistema de registro."""

import sys
from pathlib import Path


def main() -> int:
    """Inicializa la aplicación de registro."""

    current_dir = Path(__file__).resolve().parent
    src_dir = current_dir / "src"

    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    try:
        from PySide6.QtWidgets import QApplication
        from ui.main_window import PatientRecordSystem
    except ImportError as exc:  # pragma: no cover - ruta sin dependencia
        print(f"No se pudo iniciar la aplicación: {exc}")
        print("Asegúrate de tener instaladas las dependencias necesarias (p. ej. PySide6).")
        return 1

    app = QApplication(sys.argv)
    app.setApplicationName("Sistema de Registro con Cámara")

    window = PatientRecordSystem()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

