#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hilo para detección de hardware SIEV en segundo plano
"""

from PySide6.QtCore import QThread, Signal
from utils.siev_finder import SievFinder

class SievDetectionThread(QThread):
    """Hilo para detectar hardware SIEV sin bloquear la UI."""
    
    detection_finished = Signal(dict)  # Emite el resultado de la detección
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.finder = None
        self._stop_requested = False
    
    def run(self):
        """Ejecutar detección en hilo separado."""
        if self._stop_requested:
            return
            
        try:
            print("🔍 Iniciando detección SIEV en hilo separado...")
            
            # Crear finder y buscar setup
            self.finder = SievFinder()
            siev_setup = self.finder.find_siev_setup()
            
            # Verificar si se solicitó parar
            if self._stop_requested:
                return
            
            if siev_setup:
                result = {
                    'success': True,
                    'setup': siev_setup,
                    'error': None
                }
                print("✅ Detección SIEV exitosa en hilo")
            else:
                result = {
                    'success': False,
                    'setup': None,
                    'error': 'Hardware SIEV no encontrado'
                }
                print("❌ SIEV no encontrado en hilo")
            
        except Exception as e:
            result = {
                'success': False, 
                'setup': None,
                'error': str(e)
            }
            print(f"❌ Error en detección SIEV: {e}")
        
        # Solo emitir si no se solicitó parar
        if not self._stop_requested:
            self.detection_finished.emit(result)
        
        print("🔚 Hilo de detección SIEV terminado")
    
    def stop_detection(self):
        """Detener detección de forma segura."""
        print("🛑 Solicitando parada del hilo de detección...")
        self._stop_requested = True
        
        if self.isRunning():
            # Esperar máximo 2 segundos
            if not self.wait(2000):
                print("⚠️ Terminando hilo por timeout...")
                self.terminate()
                self.wait()