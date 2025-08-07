#!/usr/bin/env python3
"""
Simple Processor Controller
Controlador principal que conecta la UI con la lógica de negocio.
Maneja la comunicación entre componentes sin lógica ni UI propias.
"""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject
import pyqtgraph as pg

from ui.processor_ui import SimpleProcessorUI
from logic.processor_logic import SimpleProcessorLogic



class SimpleProcessorController(QObject):
    """
    Controlador principal que conecta UI y lógica.
    Maneja toda la comunicación entre componentes.
    """
    
    def __init__(self):
        super().__init__()
        
        # Crear componentes
        self.ui = SimpleProcessorUI()
        self.logic = SimpleProcessorLogic()
        
        # Conectar señales de UI → Logic
        self.connect_ui_to_logic()
        
        # Conectar señales de Logic → UI
        self.connect_logic_to_ui()
        
    def connect_ui_to_logic(self):
        """Conectar señales de UI hacia lógica"""
        
        # Carga de archivos
        self.ui.siev_file_requested.connect(
            lambda: self.logic.load_siev_file(self.ui)
        )
        self.ui.video_file_requested.connect(
            lambda: self.logic.load_video_direct(self.ui)
        )
        self.ui.siev_video_requested.connect(
            lambda: self.logic.load_siev_video(self.ui)
        )
        self.ui.frame_slider_changed.connect(
            self.logic.set_frame_position
        )

        
        # Selección de elementos
        self.ui.test_selected.connect(self.logic.set_test_selected)
        self.ui.graph_type_changed.connect(self.logic.set_graph_type)
        
        # Control de tiempo
        self.ui.time_slider_changed.connect(self.logic.set_time_position)
        
        # Configuración
        self.ui.save_config_toggled.connect(self.logic.set_save_config_mode)
        self.ui.threshold_changed.connect(self.logic.set_threshold_value)
        
        
        #Torok
        self.ui.torok_region_moved.connect(self.logic.set_torok_region)

    def connect_logic_to_ui(self):
        """Conectar señales de lógica hacia UI"""
        
        # Estado y mensajes
        self.logic.status_updated.connect(self.ui.update_status)
        
        # Datos SIEV
        self.logic.siev_data_loaded.connect(self.ui.update_siev_panel)
        self.logic.test_selection_changed.connect(self.ui.enable_siev_video_button)
        
        # Video
        self.logic.video_loaded.connect(self.on_video_loaded)
        self.logic.frame_ready.connect(self.ui.update_video_display)
        
        # Tiempo
        self.logic.time_info_updated.connect(self.ui.update_time_label)
        self.logic.time_line_position_updated.connect(self.ui.update_time_line_position)
        
        # Configuración
        #self.logic.config_labels_updated.connect(self.ui.update_config_labels)
        
        # Gráficos
        self.logic.graph_duration_adjusted.connect(self.ui.adjust_graph_to_duration)
        self.logic.graph_data_updated.connect(self.ui.update_graph_data)
        self.logic.caloric_point_added.connect(self.ui.add_point_to_caloric_graph)
        
        # Umbrales (para actualizar labels en UI)
        self.logic.status_updated.connect(self._on_status_for_thresholds)
        
        # NUEVO: Configurar slider cuando se carga video
        self.logic.slider_frame_config.connect(self.ui.configure_slider_for_frames)
        self.logic.frame_info_updated.connect(
            lambda cf, tf: self.ui.update_frame_info(
                cf, tf, 
                cf / self.logic.fps if hasattr(self.logic, 'fps') else 0,
                self.logic.video_player.get_duration() if self.logic.video_player else 0
            )
        )
                
        #Torok
        self.logic.torok_data_updated.connect(self.ui.update_torok_data)

        
    def on_video_loaded(self, success: bool, duration: float):
        """Manejar evento de video cargado"""
        if success:
            # La UI ya recibe la señal adjust_graph_to_duration directamente
            # Solo necesitamos manejar lógica adicional si es necesaria
            self.ui.set_video_duration(duration)

        else:
            # Manejar error de carga si es necesario
            pass
            
    def _on_status_for_thresholds(self, message: str):
        """Manejar actualizaciones de estado relacionadas con umbrales"""
        # Este método se usa para interceptar cambios en umbrales
        # y actualizar la UI si es necesario
        pass
        
    def on_threshold_changed_from_ui(self, param: str, value):
        """Manejar cambio de umbral desde UI"""
        # Enviar a lógica
        self.logic.set_threshold_value(param, value)
        
        # Actualizar label en UI
        self.ui.update_threshold_labels(param, value)
        
    def show(self):
        """Mostrar la aplicación"""
        self.ui.show()
        
    def close(self):
        """Cerrar la aplicación"""
        # Limpiar recursos si es necesario
        if hasattr(self.logic, 'visualization_timer'):
            self.logic.visualization_timer.stop()
            
        if hasattr(self.logic, 'video_player') and self.logic.video_player:
            self.logic.video_player.stop()
            
        if hasattr(self.logic, 'cleanup_video_resources'):
            self.logic.cleanup_video_resources()
            
        self.ui.close()


def main():
    """Función principal"""
    # Crear aplicación Qt
    app = QApplication(sys.argv)
    
    # Configurar PyQtGraph
    pg.setConfigOption('background', 'w')  # Fondo blanco
    pg.setConfigOption('foreground', 'k')  # Texto negro
    
    # Crear y mostrar controlador
    controller = SimpleProcessorController()
    
    # Conectar manualmente el threshold_changed para tener control total
    controller.ui.threshold_changed.disconnect()  # Desconectar conexión automática
    controller.ui.threshold_changed.connect(controller.on_threshold_changed_from_ui)
    
    # Mostrar aplicación
    controller.show()
    
    # Ejecutar aplicación
    exit_code = app.exec()
    
    # Limpiar al salir
    controller.close()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()