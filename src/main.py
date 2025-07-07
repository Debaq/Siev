import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTranslator, QLocale
from ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    
    # Configurar el traductor
    translator = QTranslator()
    
    # Obtener el idioma base del sistema (ej: "es" de "es_CL")
    locale = QLocale.system().name().split("_")[0]
    
    # Intentar cargar la traducción del idioma base
    translations_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                   "resources", "translations")
    translation_file = os.path.join(translations_path, f"{locale}.qm")
    
    if translator.load(translation_file):
        print(f"Loaded translations for {locale}")
        app.installTranslator(translator)
    else:
        print(f"Using default language (en)")
    
    window = MainWindow()
    window.show()
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
