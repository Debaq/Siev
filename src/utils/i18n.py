"""

Sistema de internacionalización (i18n) para SIEV

Soporta múltiples idiomas mediante archivos JSON de traducción

"""

 

import json

import os

from typing import Dict, Optional

from pathlib import Path

 

 

class TranslationManager:

    """

    Gestor de traducciones que carga y maneja múltiples idiomas.

    """

 

    def __init__(self, default_language: str = 'es'):

        """

        Inicializa el gestor de traducciones.

 

        Args:

            default_language: Idioma por defecto ('es' o 'en')

        """

        self.current_language = default_language

        self.translations: Dict[str, Dict] = {}

        self.available_languages = []

 

        # Detectar directorio de recursos

        self.translations_dir = self._get_translations_dir()

 

        # Cargar idiomas disponibles

        self._load_available_languages()

 

        # Cargar idioma por defecto

        if default_language in self.available_languages:

            self.load_language(default_language)

 

    def _get_translations_dir(self) -> Path:

        """Detecta el directorio de traducciones."""

        # Obtener directorio del módulo actual

        current_file = Path(__file__)

 

        # Buscar directorio de recursos

        # Puede estar en: src/resources/translations o ../resources/translations

        possible_paths = [

            current_file.parent.parent / "resources" / "translations",

            current_file.parent / "resources" / "translations",

            Path(os.getcwd()) / "src" / "resources" / "translations",

        ]

 

        for path in possible_paths:

            if path.exists():

                return path

 

        # Si no existe, crear en la ubicación esperada

        default_path = current_file.parent.parent / "resources" / "translations"

        default_path.mkdir(parents=True, exist_ok=True)

        return default_path

 

    def _load_available_languages(self):

        """Carga la lista de idiomas disponibles."""

        if not self.translations_dir.exists():

            print(f"Directorio de traducciones no encontrado: {self.translations_dir}")

            return

 

        # Buscar archivos .json en el directorio

        for file_path in self.translations_dir.glob("*.json"):

            lang_code = file_path.stem

            self.available_languages.append(lang_code)

 

        print(f"Idiomas disponibles: {', '.join(self.available_languages)}")

 

    def load_language(self, language_code: str) -> bool:

        """

        Carga un archivo de traducción.

 

        Args:

            language_code: Código del idioma ('es', 'en', etc.)

 

        Returns:

            True si se cargó correctamente

        """

        if language_code not in self.available_languages:

            print(f"Idioma no disponible: {language_code}")

            return False

 

        translation_file = self.translations_dir / f"{language_code}.json"

 

        try:

            with open(translation_file, 'r', encoding='utf-8') as f:

                self.translations[language_code] = json.load(f)

 

            self.current_language = language_code

            print(f"Idioma cargado: {language_code}")

            return True

 

        except Exception as e:

            print(f"Error cargando idioma {language_code}: {e}")

            return False

 

    def get(self, key_path: str, **kwargs) -> str:

        """

        Obtiene una traducción usando una ruta de clave (ej: 'menu.archivo').

 

        Args:

            key_path: Ruta de la clave separada por puntos

            **kwargs: Variables para formatear la cadena (ej: time=5)

 

        Returns:

            Texto traducido o la clave si no se encuentra

        """

        if self.current_language not in self.translations:

            return key_path

 

        # Navegar por el diccionario anidado

        keys = key_path.split('.')

        value = self.translations[self.current_language]

 

        try:

            for key in keys:

                value = value[key]

 

            # Si hay variables para formatear

            if kwargs:

                return value.format(**kwargs)

 

            return value

 

        except (KeyError, TypeError):

            print(f"Traducción no encontrada: {key_path}")

            return key_path

 

    def t(self, key_path: str, **kwargs) -> str:

        """Alias corto para get()."""

        return self.get(key_path, **kwargs)

 

    def get_current_language(self) -> str:

        """Retorna el idioma actual."""

        return self.current_language

 

    def get_available_languages(self) -> list:

        """Retorna lista de idiomas disponibles."""

        return self.available_languages.copy()

 

    def switch_language(self, language_code: str) -> bool:

        """

        Cambia el idioma actual.

 

        Args:

            language_code: Código del nuevo idioma

 

        Returns:

            True si el cambio fue exitoso

        """

        return self.load_language(language_code)

 

 

# Instancia global del gestor de traducciones

_translation_manager: Optional[TranslationManager] = None

 

 

def get_translation_manager() -> TranslationManager:

    """Obtiene la instancia global del gestor de traducciones."""

    global _translation_manager

 

    if _translation_manager is None:

        _translation_manager = TranslationManager()

 

    return _translation_manager

 

 

def t(key_path: str, **kwargs) -> str:

    """

    Función global para obtener traducciones.

 

    Args:

        key_path: Ruta de la clave (ej: 'menu.archivo')

        **kwargs: Variables para formatear

 

    Returns:

        Texto traducido

    """

    return get_translation_manager().get(key_path, **kwargs)

 

 

# Ejemplo de uso:

if __name__ == "__main__":

    # Crear gestor con español por defecto

    tm = TranslationManager('es')

 

    print(f"Idioma actual: {tm.get_current_language()}")

    print(f"Idiomas disponibles: {tm.get_available_languages()}")

    print()

 

    # Pruebas en español

    print("=== Español ===")

    print(f"Título: {tm.t('app.title')}")

    print(f"Menú Archivo: {tm.t('menu.archivo')}")

    print(f"Iniciar: {tm.t('controls.iniciar')}")

    print(f"Calibrando: {tm.t('time.calibrando', time=5)}")

    print()

 

    # Cambiar a inglés

    tm.switch_language('en')

 

    print("=== English ===")

    print(f"Title: {tm.t('app.title')}")

    print(f"File Menu: {tm.t('menu.archivo')}")

    print(f"Start: {tm.t('controls.iniciar')}")

    print(f"Calibrating: {tm.t('time.calibrando', time=5)}")