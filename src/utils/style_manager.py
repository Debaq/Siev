"""

Gestor de estilos para la aplicación SIEV

Permite cargar y aplicar temas QSS dinámicamente

"""

 

from pathlib import Path

from typing import Optional

from PySide6.QtWidgets import QApplication

 

 

class StyleManager:

    """

    Gestor de estilos que carga y aplica hojas de estilo QSS.

    """

 

    def __init__(self, default_style: str = 'professional'):

        """

        Inicializa el gestor de estilos.

 

        Args:

            default_style: Nombre del estilo por defecto (sin extensión .qss)

        """

        self.current_style = default_style

        self.styles_dir = self._get_styles_dir()

        self.available_styles = self._load_available_styles()

 

    def _get_styles_dir(self) -> Path:

        """Detecta el directorio de estilos."""

        current_file = Path(__file__)

 

        # Buscar directorio de recursos

        possible_paths = [

            current_file.parent.parent / "resources" / "styles",

            current_file.parent / "resources" / "styles",

            Path.cwd() / "src" / "resources" / "styles",

        ]

 

        for path in possible_paths:

            if path.exists():

                return path

 

        # Si no existe, crear en la ubicación esperada

        default_path = current_file.parent.parent / "resources" / "styles"

        default_path.mkdir(parents=True, exist_ok=True)

        return default_path

 

    def _load_available_styles(self) -> list:

        """Carga la lista de estilos disponibles."""

        if not self.styles_dir.exists():

            print(f"Directorio de estilos no encontrado: {self.styles_dir}")

            return []

 

        # Buscar archivos .qss en el directorio

        styles = []

        for file_path in self.styles_dir.glob("*.qss"):

            styles.append(file_path.stem)

 

        print(f"Estilos disponibles: {', '.join(styles)}")

        return styles

 

    def load_stylesheet(self, style_name: str) -> Optional[str]:

        """

        Carga una hoja de estilos QSS.

 

        Args:

            style_name: Nombre del estilo (sin extensión)

 

        Returns:

            Contenido de la hoja de estilos o None si falla

        """

        if style_name not in self.available_styles:

            print(f"Estilo no disponible: {style_name}")

            return None

 

        stylesheet_file = self.styles_dir / f"{style_name}.qss"

 

        try:

            with open(stylesheet_file, 'r', encoding='utf-8') as f:

                stylesheet = f.read()

 

            self.current_style = style_name

            print(f"Hoja de estilos cargada: {style_name}")

            return stylesheet

 

        except Exception as e:

            print(f"Error cargando estilo {style_name}: {e}")

            return None

 

    def apply_style(self, app: QApplication, style_name: str = None) -> bool:

        """

        Aplica una hoja de estilos a la aplicación.

 

        Args:

            app: Instancia de QApplication

            style_name: Nombre del estilo (usa el actual si no se especifica)

 

        Returns:

            True si se aplicó correctamente

        """

        if style_name is None:

            style_name = self.current_style

 

        stylesheet = self.load_stylesheet(style_name)

        if stylesheet:

            app.setStyleSheet(stylesheet)

            return True

 

        return False

 

    def get_current_style(self) -> str:

        """Retorna el estilo actual."""

        return self.current_style

 

    def get_available_styles(self) -> list:

        """Retorna lista de estilos disponibles."""

        return self.available_styles.copy()

 

    def reload_current_style(self, app: QApplication) -> bool:

        """

        Recarga el estilo actual (útil durante desarrollo).

 

        Args:

            app: Instancia de QApplication

 

        Returns:

            True si se recargó correctamente

        """

        return self.apply_style(app, self.current_style)

 

 

# Instancia global del gestor de estilos

_style_manager: Optional[StyleManager] = None

 

 

def get_style_manager() -> StyleManager:

    """Obtiene la instancia global del gestor de estilos."""

    global _style_manager

 

    if _style_manager is None:

        _style_manager = StyleManager()

 

    return _style_manager

 

 

# Ejemplo de uso

if __name__ == "__main__":

    import sys

    from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget

 

    app = QApplication(sys.argv)

 

    # Crear gestor de estilos

    sm = StyleManager()

 

    # Aplicar estilo profesional

    sm.apply_style(app, 'professional')

 

    # Crear ventana de prueba

    window = QMainWindow()

    window.setWindowTitle("Test de Estilos SIEV")

    window.resize(800, 600)

 

    central_widget = QWidget()

    layout = QVBoxLayout()

 

    # Botones de prueba

    btn1 = QPushButton("Botón Principal")

    btn2 = QPushButton("Botón Secundario")

    btn2.setProperty("class", "secondary")

    btn3 = QPushButton("Botón Peligro")

    btn3.setProperty("class", "danger")

    btn4 = QPushButton("Botón Éxito")

    btn4.setProperty("class", "success")

 

    layout.addWidget(btn1)

    layout.addWidget(btn2)

    layout.addWidget(btn3)

    layout.addWidget(btn4)

 

    central_widget.setLayout(layout)

    window.setCentralWidget(central_widget)

 

    window.show()

    sys.exit(app.exec())