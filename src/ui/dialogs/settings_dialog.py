"""
Diálogo de configuración de la aplicación SIEV

Permite cambiar idioma y tema
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QComboBox, QPushButton, QGroupBox, QMessageBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from utils.i18n import get_translation_manager
from utils.style_manager import get_style_manager


class SettingsDialog(QDialog):
    """
    Diálogo de configuración para idioma y tema.
    Emite señales cuando se aplican cambios.
    """

    settings_changed = Signal(dict)  # Emite diccionario con cambios aplicados

    def __init__(self, parent=None):
        super().__init__(parent)

        self.translation_manager = get_translation_manager()
        self.style_manager = get_style_manager()
        self.t = self.translation_manager.t

        # Guardar configuración inicial
        self.initial_language = self.translation_manager.get_current_language()
        self.initial_style = self.style_manager.get_current_style()

        self.setup_ui()
        self.load_current_settings()

    def setup_ui(self):
        """Configurar interfaz del diálogo"""
        self.setWindowTitle("Configuración")
        self.setModal(True)
        self.setMinimumWidth(450)
        self.resize(450, 300)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Título
        title_label = QLabel("Configuración de la Aplicación")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # === GRUPO DE IDIOMA ===
        language_group = QGroupBox("Idioma / Language")
        language_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        language_layout = QVBoxLayout()
        language_layout.setSpacing(10)

        # Etiqueta de idioma
        lang_label = QLabel("Seleccionar idioma:")
        language_layout.addWidget(lang_label)

        # Combo de idiomas
        self.language_combo = QComboBox()
        self.language_combo.setMinimumHeight(35)

        # Obtener idiomas disponibles
        available_languages = self.translation_manager.get_available_languages()
        language_names = {
            'es': '🇪🇸 Español',
            'en': '🇬🇧 English',
            'pt': '🇵🇹 Português',
            'fr': '🇫🇷 Français'
        }

        for lang_code in available_languages:
            display_name = language_names.get(lang_code, lang_code.upper())
            self.language_combo.addItem(display_name, lang_code)

        language_layout.addWidget(self.language_combo)

        # Nota sobre el idioma
        lang_note = QLabel("* Los cambios de idioma requieren reiniciar la aplicación")
        lang_note.setStyleSheet("color: #757575; font-size: 8pt;")
        language_layout.addWidget(lang_note)

        language_group.setLayout(language_layout)
        layout.addWidget(language_group)

        # === GRUPO DE TEMA ===
        theme_group = QGroupBox("Tema / Theme")
        theme_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        theme_layout = QVBoxLayout()
        theme_layout.setSpacing(10)

        # Etiqueta de tema
        theme_label = QLabel("Seleccionar tema:")
        theme_layout.addWidget(theme_label)

        # Combo de temas
        self.theme_combo = QComboBox()
        self.theme_combo.setMinimumHeight(35)

        # Obtener temas disponibles
        available_styles = self.style_manager.get_available_styles()
        theme_names = {
            'professional': '💼 Profesional',
            'dark': '🌙 Oscuro',
            'light': '☀️ Claro',
            'high_contrast': '🔆 Alto Contraste'
        }

        for style_name in available_styles:
            display_name = theme_names.get(style_name, style_name.capitalize())
            self.theme_combo.addItem(display_name, style_name)

        theme_layout.addWidget(self.theme_combo)

        # Nota sobre el tema
        theme_note = QLabel("* Los cambios de tema se aplican inmediatamente")
        theme_note.setStyleSheet("color: #757575; font-size: 8pt;")
        theme_layout.addWidget(theme_note)

        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)

        # Espaciador
        layout.addStretch()

        # === BOTONES ===
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        # Botón Vista Previa
        self.preview_button = QPushButton("Vista Previa del Tema")
        self.preview_button.setMinimumHeight(35)
        self.preview_button.clicked.connect(self.preview_theme)
        button_layout.addWidget(self.preview_button)

        button_layout.addStretch()

        # Botón Cancelar
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.setMinimumHeight(35)
        self.cancel_button.setMinimumWidth(100)
        self.cancel_button.clicked.connect(self.reject_changes)
        button_layout.addWidget(self.cancel_button)

        # Botón Aplicar
        self.apply_button = QPushButton("Aplicar")
        self.apply_button.setMinimumHeight(35)
        self.apply_button.setMinimumWidth(100)
        self.apply_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.apply_button.clicked.connect(self.apply_settings)
        button_layout.addWidget(self.apply_button)

        layout.addLayout(button_layout)

        # Conectar señales
        self.theme_combo.currentIndexChanged.connect(self.on_theme_changed)

    def load_current_settings(self):
        """Cargar configuración actual en los combos"""
        # Cargar idioma actual
        current_language = self.translation_manager.get_current_language()
        for i in range(self.language_combo.count()):
            if self.language_combo.itemData(i) == current_language:
                self.language_combo.setCurrentIndex(i)
                break

        # Cargar tema actual
        current_style = self.style_manager.get_current_style()
        for i in range(self.theme_combo.count()):
            if self.theme_combo.itemData(i) == current_style:
                self.theme_combo.setCurrentIndex(i)
                break

    def on_theme_changed(self, index):
        """Se llama cuando cambia la selección de tema"""
        # Habilitar botón de vista previa
        self.preview_button.setEnabled(True)

    def preview_theme(self):
        """Vista previa del tema seleccionado"""
        selected_style = self.theme_combo.currentData()

        if selected_style:
            app = QApplication.instance()
            if self.style_manager.apply_style(app, selected_style):
                QMessageBox.information(
                    self,
                    "Vista Previa",
                    f"Vista previa del tema '{self.theme_combo.currentText()}' aplicada.\n\n"
                    "Si no te gusta, puedes cancelar para volver al tema anterior."
                )
            else:
                QMessageBox.warning(
                    self,
                    "Error",
                    "No se pudo aplicar el tema seleccionado."
                )

    def apply_settings(self):
        """Aplicar configuración y cerrar diálogo"""
        changes = {}

        # Verificar cambio de idioma
        selected_language = self.language_combo.currentData()
        if selected_language != self.initial_language:
            if self.translation_manager.switch_language(selected_language):
                changes['language'] = selected_language

                # Informar que requiere reinicio
                QMessageBox.information(
                    self,
                    "Cambio de Idioma",
                    "El idioma se cambiará completamente al reiniciar la aplicación.\n\n"
                    "Algunos textos ya están actualizados, pero para una experiencia completa, "
                    "por favor reinicia la aplicación."
                )

        # Verificar cambio de tema
        selected_style = self.theme_combo.currentData()
        if selected_style != self.initial_style:
            app = QApplication.instance()
            if self.style_manager.apply_style(app, selected_style):
                changes['theme'] = selected_style

        # Emitir señal con cambios
        if changes:
            self.settings_changed.emit(changes)

        self.accept()

    def reject_changes(self):
        """Cancelar cambios y restaurar configuración inicial"""
        # Restaurar tema inicial si se cambió en vista previa
        current_style = self.style_manager.get_current_style()
        if current_style != self.initial_style:
            app = QApplication.instance()
            self.style_manager.apply_style(app, self.initial_style)

        self.reject()


# Función helper para abrir el diálogo
def open_settings_dialog(parent=None):
    """
    Abre el diálogo de configuración.

    Args:
        parent: Widget padre

    Returns:
        dict: Diccionario con cambios aplicados o None si se canceló
    """
    dialog = SettingsDialog(parent)

    changes = {}

    def on_settings_changed(changed_settings):
        nonlocal changes
        changes = changed_settings

    dialog.settings_changed.connect(on_settings_changed)

    result = dialog.exec()

    if result == QDialog.Accepted and changes:
        return changes

    return None
