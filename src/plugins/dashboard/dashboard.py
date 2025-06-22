#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIEV - Dashboard Plugin
Plugin principal del dashboard con estadísticas y accesos rápidos
"""

import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QFrame, QPushButton, QGridLayout, QScrollArea)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtUiTools import QUiLoader
from core.base_plugin import BasePlugin, PluginMetadata


class DashboardPlugin(BasePlugin):
    """
    Plugin del dashboard principal
    Muestra estadísticas del sistema y accesos rápidos
    """
    
    def __init__(self, parent=None):
        """Inicializar dashboard plugin"""
        super().__init__(parent)
        self.ui_loader = QUiLoader()
        self.main_widget = None
        
        # Datos de ejemplo para el dashboard
        self.stats_data = {
            'patients_count': 142,
            'evaluations_today': 8,
            'pending_reports': 3,
            'success_rate': 94.5
        }
        
    def get_metadata(self) -> PluginMetadata:
        """Retorna metadatos del plugin"""
        return PluginMetadata(
            name="dashboard",
            display_name="Dashboard Principal",
            version="1.0.0",
            description="Panel principal con estadísticas y accesos rápidos",
            author="SIEV Team",
            category="core"
        )
        
    def initialize_plugin(self) -> bool:
        """Inicializar el plugin"""
        try:
            print("🏠 Inicializando Dashboard Plugin...")
            
            # Configurar timer para actualizaciones (opcional)
            self.start_periodic_updates(30000)  # 30 segundos
            
            self._is_initialized = True
            return True
            
        except Exception as e:
            print(f"❌ Error inicializando Dashboard Plugin: {e}")
            return False
            
    def create_main_widget(self) -> QWidget:
        """Crear widget principal del dashboard"""
        try:
            # Intentar cargar desde .ui file
            ui_file_path = "ui/dashboard_widget.ui"
            
            if os.path.exists(ui_file_path):
                return self._load_from_ui_file(ui_file_path)
            else:
                print("📄 Archivo .ui no encontrado, creando dashboard programáticamente")
                return self._create_programmatic_dashboard()
                
        except Exception as e:
            print(f"❌ Error creando widget principal: {e}")
            return self._create_fallback_widget()
            
    def _load_from_ui_file(self, ui_file_path: str) -> QWidget:
        """Cargar dashboard desde archivo .ui"""
        try:
            widget = self.ui_loader.load(ui_file_path)
            
            # Conectar funcionalidades específicas si es necesario
            self._setup_ui_connections(widget)
            
            return widget
            
        except Exception as e:
            print(f"⚠️  Error cargando .ui, usando fallback: {e}")
            return self._create_programmatic_dashboard()
            
    def _create_programmatic_dashboard(self) -> QWidget:
        """Crear dashboard programáticamente"""
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(24)
        
        # Header del dashboard
        header = self._create_header()
        main_layout.addWidget(header)
        
        # Stats cards
        stats_section = self._create_stats_section()
        main_layout.addWidget(stats_section)
        
        # Quick actions
        actions_section = self._create_actions_section()
        main_layout.addWidget(actions_section)
        
        # Recent activity
        recent_section = self._create_recent_section()
        main_layout.addWidget(recent_section)
        
        # Espaciador
        main_layout.addStretch()
        
        return main_widget
        
    def _create_header(self) -> QWidget:
        """Crear header del dashboard"""
        header = QFrame()
        header.setFrameStyle(QFrame.NoFrame)
        layout = QVBoxLayout(header)
        
        # Título principal
        title = QLabel("Dashboard Principal")
        title.setProperty("labelStyle", "title")
        title.setStyleSheet("""
            QLabel {
                font-size: 28px;
                font-weight: 700;
                color: #111827;
                margin-bottom: 8px;
            }
        """)
        
        # Subtítulo
        subtitle = QLabel("Bienvenido al Sistema Integrado de Evaluación Vestibular")
        subtitle.setProperty("labelStyle", "subtitle")
        subtitle.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #6B7280;
                margin-bottom: 16px;
            }
        """)
        
        layout.addWidget(title)
        layout.addWidget(subtitle)
        
        return header
        
    def _create_stats_section(self) -> QWidget:
        """Crear sección de estadísticas"""
        stats_frame = QFrame()
        stats_frame.setFrameStyle(QFrame.NoFrame)
        
        # Grid layout para las stats cards
        grid_layout = QGridLayout(stats_frame)
        grid_layout.setSpacing(16)
        
        # Stats cards data
        stats = [
            ("Pacientes Totales", self.stats_data['patients_count'], "#6B46C1", "👥"),
            ("Evaluaciones Hoy", self.stats_data['evaluations_today'], "#059669", "📊"),
            ("Reportes Pendientes", self.stats_data['pending_reports'], "#F59E0B", "📋"),
            ("Tasa de Éxito", f"{self.stats_data['success_rate']}%", "#EF4444", "✅")
        ]
        
        for i, (label, value, color, icon) in enumerate(stats):
            card = self._create_stat_card(label, value, color, icon)
            grid_layout.addWidget(card, 0, i)
            
        return stats_frame
        
    def _create_stat_card(self, label: str, value, color: str, icon: str) -> QWidget:
        """Crear tarjeta de estadística individual"""
        card = QFrame()
        card.setProperty("statsCard", "true")
        card.setStyleSheet(f"""
            QFrame[statsCard="true"] {{
                background-color: white;
                border: 1px solid #E5E7EB;
                border-radius: 12px;
                padding: 20px;
                min-height: 100px;
            }}
            QFrame[statsCard="true"]:hover {{
                border-color: {color};
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(8)
        
        # Icon y valor en la parte superior
        top_layout = QHBoxLayout()
        
        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"""
            QLabel {{
                font-size: 24px;
                color: {color};
            }}
        """)
        
        value_label = QLabel(str(value))
        value_label.setProperty("labelStyle", "value")
        value_label.setAlignment(Qt.AlignRight)
        value_label.setStyleSheet(f"""
            QLabel {{
                font-size: 24px;
                font-weight: 700;
                color: {color};
            }}
        """)
        
        top_layout.addWidget(icon_label)
        top_layout.addStretch()
        top_layout.addWidget(value_label)
        
        # Label en la parte inferior
        label_widget = QLabel(label)
        label_widget.setProperty("labelStyle", "caption")
        label_widget.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: 500;
                color: #6B7280;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
        """)
        
        layout.addLayout(top_layout)
        layout.addWidget(label_widget)
        
        return card
        
    def _create_actions_section(self) -> QWidget:
        """Crear sección de acciones rápidas"""
        actions_frame = QFrame()
        actions_frame.setFrameStyle(QFrame.NoFrame)
        
        layout = QVBoxLayout(actions_frame)
        
        # Título de sección
        title = QLabel("Acciones Rápidas")
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: 600;
                color: #374151;
                margin-bottom: 16px;
            }
        """)
        
        # Botones de acción
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(12)
        
        actions = [
            ("🆕 Nuevo Paciente", "patients"),
            ("👁️ Iniciar VNG", "vng"),
            ("📊 Ver Reportes", "reports"),
            ("⚙️ Configuración", "settings")
        ]
        
        for text, plugin in actions:
            button = QPushButton(text)
            button.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                               stop:0 #6B46C1, stop:1 #A78BFA);
                    border: none;
                    border-radius: 8px;
                    color: white;
                    font-weight: 500;
                    padding: 12px 24px;
                    min-width: 140px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                               stop:0 #553C9A, stop:1 #9F7AEA);
                }
            """)
            
            # Conectar acción (emitir señal para cargar plugin)
            button.clicked.connect(lambda checked=False, p=plugin: self._load_plugin(p))
            
            actions_layout.addWidget(button)
            
        actions_layout.addStretch()
        
        layout.addWidget(title)
        layout.addLayout(actions_layout)
        
        return actions_frame
        
    def _create_recent_section(self) -> QWidget:
        """Crear sección de actividad reciente"""
        recent_frame = QFrame()
        recent_frame.setProperty("cardStyle", "true")
        recent_frame.setStyleSheet("""
            QFrame[cardStyle="true"] {
                background-color: white;
                border: 1px solid #E5E7EB;
                border-radius: 12px;
                padding: 20px;
            }
        """)
        
        layout = QVBoxLayout(recent_frame)
        
        # Título
        title = QLabel("Estado del Sistema")
        title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: 600;
                color: #374151;
                margin-bottom: 16px;
            }
        """)
        
        # Indicadores de estado
        status_layout = QVBoxLayout()
        status_layout.setSpacing(8)
        
        statuses = [
            ("💚 Cámara", "Conectada y funcionando", "success"),
            ("💚 Base de Datos", "Conectada - Sin errores", "success"),  
            ("💛 Backup", "Último backup hace 2 horas", "warning"),
            ("💚 Sistema", "Todos los servicios operativos", "success")
        ]
        
        for icon, text, status_type in statuses:
            status_item = self._create_status_item(icon, text, status_type)
            status_layout.addWidget(status_item)
            
        layout.addWidget(title)
        layout.addLayout(status_layout)
        
        return recent_frame
        
    def _create_status_item(self, icon: str, text: str, status_type: str) -> QWidget:
        """Crear item de estado individual"""
        item = QFrame()
        layout = QHBoxLayout(item)
        layout.setContentsMargins(0, 4, 0, 4)
        
        icon_label = QLabel(icon)
        text_label = QLabel(text)
        text_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #374151;
            }
        """)
        
        layout.addWidget(icon_label)
        layout.addWidget(text_label)
        layout.addStretch()
        
        return item
        
    def _create_fallback_widget(self) -> QWidget:
        """Crear widget de fallback simple"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)
        
        label = QLabel("Dashboard Plugin Cargado")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: 600;
                color: #6B46C1;
                padding: 40px;
            }
        """)
        
        layout.addWidget(label)
        return widget
        
    def _setup_ui_connections(self, widget: QWidget):
        """Configurar conexiones de UI cargada desde archivo"""
        # Aquí conectarías botones y otros elementos del .ui file
        pass
        
    def _load_plugin(self, plugin_name: str):
        """Señalar que se debe cargar otro plugin"""
        # Esta funcionalidad la manejará el plugin loader desde el WindowHandler
        print(f"🔄 Solicitando carga de plugin: {plugin_name}")
        
    def on_activate(self):
        """Llamado cuando el plugin se activa"""
        print("🏠 Dashboard activado")
        # Aquí podrías actualizar datos, refrescar estadísticas, etc.
        
    def on_deactivate(self):
        """Llamado cuando el plugin se desactiva"""
        print("🏠 Dashboard desactivado")
        
    def on_periodic_update(self):
        """Actualización periódica del dashboard"""
        # Aquí podrías actualizar estadísticas en tiempo real
        pass
        
    def cleanup(self):
        """Limpiar recursos del plugin"""
        super().cleanup()
        print("🧹 Dashboard plugin limpiado")