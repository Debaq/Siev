#!/usr/bin/env python3
"""
Simple Video Processor
Programa simple para abrir videos SIEV, reprocesarlos y graficar resultados.
Solo procesa datos del ojo derecho.
"""

import sys
import os
import json
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import time

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QLabel, QSlider, QFileDialog, QComboBox, QMessageBox,
    QSplitter, QGroupBox, QGridLayout
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtGui import QPixmap, QImage

import pyqtgraph as pg

try:
    from numba import jit, prange
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False
    print("Numba no disponible, usando implementación estándar")

# Importar clases existentes del proyecto
try:
    from src.utils.graphing.caloric_graph import CaloricGraph
    from src.utils.video.video_player_thread import VideoPlayerThread
    from src.utils.graphing.data_processor import DataProcessor
except ImportError as e:
    print(f"Error importing project modules: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)


# Funciones aceleradas con Numba si está disponible
if NUMBA_AVAILABLE:
    @jit(nopython=True, cache=True)
    def find_largest_contour_fast(contours_array):
        """Encontrar el contorno más grande usando Numba"""
        max_area = 0
        max_idx = -1
        
        for i in range(len(contours_array)):
            contour = contours_array[i]
            area = 0.0
            
            # Calcular área usando shoelace formula
            n = len(contour)
            for j in range(n):
                k = (j + 1) % n
                area += contour[j][0] * contour[k][1]
                area -= contour[k][0] * contour[j][1]
            area = abs(area) / 2.0
            
            if area > max_area:
                max_area = area
                max_idx = i
                
        return max_idx, max_area
    
    @jit(nopython=True, cache=True)
    def calculate_centroid_fast(contour):
        """Calcular centroide rápido con Numba"""
        cx = 0.0
        cy = 0.0
        n = len(contour)
        
        for i in range(n):
            cx += contour[i][0]
            cy += contour[i][1]
            
        return cx / n, cy / n
    
    @jit(nopython=True, cache=True)
    def apply_threshold_fast(gray_region, threshold):
        """Aplicar umbral rápido con Numba"""
        h, w = gray_region.shape
        result = np.zeros((h, w), dtype=np.uint8)
        
        for i in prange(h):
            for j in prange(w):
                if gray_region[i, j] < threshold:
                    result[i, j] = 255
                else:
                    result[i, j] = 0
                    
        return result
else:
    # Versiones estándar sin Numba
    def find_largest_contour_fast(contours):
        """Versión estándar sin Numba"""
        if not contours:
            return -1, 0
        areas = [cv2.contourArea(c) for c in contours]
        max_idx = np.argmax(areas)
        return max_idx, areas[max_idx]
    
    def calculate_centroid_fast(contour):
        """Versión estándar sin Numba"""
        M = cv2.moments(contour)
        if M['m00'] == 0:
            return 0, 0
        cx = M['m10'] / M['m00']
        cy = M['m01'] / M['m00']
        return cx, cy
    
    def apply_threshold_fast(gray_region, threshold):
        """Versión estándar sin Numba"""
        return cv2.threshold(gray_region, threshold, 255, cv2.THRESH_BINARY_INV)[1]


class FastVideoProcessor:
    """
    Procesador de video optimizado específico para detección de pupila del ojo derecho
    """
    
    def __init__(self, thresholds: Dict):
        self.thresholds = thresholds
        self.face_detector = None
        self.eye_detector = None
        self.setup_detectors()
        
        # Cache para optimización
        self.last_face_region = None
        self.last_eye_region = None
        self.frame_skip_counter = 0
        
    def setup_detectors(self):
        """Configurar detectores OpenCV"""
        try:
            # Usar detectores Haar más rápidos
            face_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            eye_cascade_path = cv2.data.haarcascades + 'haarcascade_eye.xml'
            
            self.face_detector = cv2.CascadeClassifier(face_cascade_path)
            self.eye_detector = cv2.CascadeClassifier(eye_cascade_path)
            
        except Exception as e:
            print(f"Error configurando detectores: {e}")
            
    def process_frame(self, frame: np.ndarray) -> Tuple[float, float, bool]:
        """
        Procesar frame y retornar posición de pupila del ojo derecho
        
        Returns:
            Tuple[x, y, detected]: Posición x, y y si se detectó
        """
        if frame is None:
            return 0.0, 0.0, False
            
        try:
            # Convertir a escala de grises
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detectar cara (con cache cada 5 frames para acelerar)
            face_region = self._detect_face_region(gray)
            if face_region is None:
                return 0.0, 0.0, False
                
            # Detectar ojo derecho
            right_eye_region = self._detect_right_eye(face_region)
            if right_eye_region is None:
                return 0.0, 0.0, False
                
            # Detectar pupila en ojo derecho
            pupil_x, pupil_y = self._detect_pupil_in_eye(right_eye_region)
            
            return pupil_x, pupil_y, True
            
        except Exception as e:
            print(f"Error procesando frame: {e}")
            return 0.0, 0.0, False
            
    def _detect_face_region(self, gray: np.ndarray) -> Optional[np.ndarray]:
        """Detectar región de la cara con cache"""
        self.frame_skip_counter += 1
        
        # Solo detectar cara cada 5 frames para acelerar
        if self.frame_skip_counter % 5 == 0 or self.last_face_region is None:
            faces = self.face_detector.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100)
            )
            
            if len(faces) > 0:
                # Tomar la cara más grande
                face = max(faces, key=lambda r: r[2] * r[3])
                x, y, w, h = face
                
                # Expandir región ligeramente
                margin = 20
                x = max(0, x - margin)
                y = max(0, y - margin)
                w = min(gray.shape[1] - x, w + 2 * margin)
                h = min(gray.shape[0] - y, h + 2 * margin)
                
                self.last_face_region = (x, y, w, h)
                
        if self.last_face_region:
            x, y, w, h = self.last_face_region
            return gray[y:y+h, x:x+w]
            
        return None
        
    def _detect_right_eye(self, face_region: np.ndarray) -> Optional[np.ndarray]:
        """Detectar ojo derecho en la cara"""
        if face_region is None:
            return None
            
        # Detectar ojos
        eyes = self.eye_detector.detectMultiScale(
            face_region, scaleFactor=1.1, minNeighbors=3, minSize=(30, 30)
        )
        
        if len(eyes) < 1:
            return None
            
        # Si hay 2 ojos, tomar el de la derecha (menor x desde perspectiva del sujeto)
        if len(eyes) >= 2:
            # Ordenar por posición x
            eyes = sorted(eyes, key=lambda e: e[0])
            # Ojo derecho es el primero (menor x)
            eye = eyes[0]
        else:
            # Solo un ojo detectado, asumir que es el derecho
            eye = eyes[0]
            
        ex, ey, ew, eh = eye
        return face_region[ey:ey+eh, ex:ex+ew]
        
    def _detect_pupil_in_eye(self, eye_region: np.ndarray) -> Tuple[float, float]:
        """Detectar pupila en región del ojo"""
        if eye_region is None or eye_region.size == 0:
            return 0.0, 0.0
            
        try:
            # Aplicar umbral
            threshold = self.thresholds.get('threshold_right', 50)
            
            if NUMBA_AVAILABLE:
                binary = apply_threshold_fast(eye_region, threshold)
            else:
                binary = apply_threshold_fast(eye_region, threshold)
                
            # Aplicar erosión
            erode_size = self.thresholds.get('erode_right', 2)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (erode_size, erode_size))
            binary = cv2.erode(binary, kernel, iterations=1)
            
            # Encontrar contornos
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return 0.0, 0.0
                
            # Encontrar contorno más grande
            if NUMBA_AVAILABLE and len(contours) > 1:
                # Convertir contornos para Numba
                contours_array = [c.reshape(-1, 2) for c in contours if len(c) > 5]
                if contours_array:
                    max_idx, max_area = find_largest_contour_fast(contours_array)
                    if max_idx >= 0:
                        largest_contour = contours_array[max_idx]
                        cx, cy = calculate_centroid_fast(largest_contour)
                        return float(cx), float(cy)
            else:
                # Usar método estándar
                largest_contour = max(contours, key=cv2.contourArea)
                if cv2.contourArea(largest_contour) > 10:  # Área mínima
                    cx, cy = calculate_centroid_fast(largest_contour)
                    return float(cx), float(cy)
                    
            return 0.0, 0.0
            
        except Exception as e:
            print(f"Error detectando pupila: {e}")
            return 0.0, 0.0


class SimpleVideoProcessor(QThread):
    """Hilo para procesar video completo de forma simple"""
    
    progress_updated = Signal(int)  # Progreso en porcentaje
    frame_processed = Signal(object, float, float)  # frame, timestamp, angular_velocity
    processing_finished = Signal()
    
    def __init__(self, video_path: str, thresholds: Dict):
        super().__init__()
        self.video_path = video_path
        self.thresholds = thresholds
        self.running = True
        
    def stop(self):
        """Detener procesamiento"""
        self.running = False
        
    def run(self):
        """Procesar video completo"""
        try:
            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                return
                
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            frame_count = 0
            last_angle = 0.0
            
            while self.running and cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                    
                timestamp = frame_count / fps
                
                # Procesar solo ojo derecho (implementación simplificada)
                angular_velocity = self._process_right_eye(frame, last_angle)
                
                # Emitir frame procesado
                self.frame_processed.emit(frame, timestamp, angular_velocity)
                
                # Actualizar progreso
                progress = int((frame_count / total_frames) * 100)
                self.progress_updated.emit(progress)
                
                frame_count += 1
                last_angle = angular_velocity
                
            cap.release()
            self.processing_finished.emit()
            
        except Exception as e:
            print(f"Error en procesamiento: {e}")
            sys.exit(1)
            
    def _process_right_eye(self, frame: np.ndarray, last_angle: float) -> float:
        """
        Procesamiento simplificado del ojo derecho
        TODO: Implementar detección real usando las clases existentes
        """
        # Por ahora retorna valor simulado
        # En implementación real usar PupilAnalyzer y detectores existentes
        return np.random.uniform(-10, 10)  # Placeholder


class SimpleProcessorWindow(QMainWindow):
    """Ventana principal del procesador simple"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple Video Processor")
        self.setGeometry(100, 100, 1400, 900)
        
        # Datos
        self.siev_data = None
        self.current_test = None
        self.video_path = None
        self.is_processing = False
        
        # Configuración de umbrales
        self.thresholds = {
            'threshold_left': 50,
            'threshold_right': 50,
            'erode_left': 2,
            'erode_right': 2,
            'nose_width': 0.25,
            'eye_height': 0.5
        }
        
        # Componentes
        self.processor_thread = None
        self.video_player = None
        self.current_frame = None
        
        self.setup_ui()
        
    def setup_ui(self):
        """Configurar interfaz de usuario"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        
        # Panel de control superior
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel)
        
        # Splitter principal
        main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(main_splitter)
        
        # Panel izquierdo - Video y controles
        left_panel = self.create_left_panel()
        main_splitter.addWidget(left_panel)
        
        # Panel derecho - Gráficos
        right_panel = self.create_right_panel()
        main_splitter.addWidget(right_panel)
        
        # Establecer proporciones
        main_splitter.setSizes([600, 800])
        
    def create_control_panel(self) -> QWidget:
        """Crear panel de control superior"""
        panel = QGroupBox("Control Principal")
        layout = QHBoxLayout(panel)
        
        # Cargar SIEV
        self.btn_load_siev = QPushButton("Cargar SIEV")
        self.btn_load_siev.clicked.connect(self.load_siev_file)
        layout.addWidget(self.btn_load_siev)
        
        # Selector de prueba
        self.combo_tests = QComboBox()
        self.combo_tests.currentTextChanged.connect(self.test_selected)
        layout.addWidget(QLabel("Prueba:"))
        layout.addWidget(self.combo_tests)
        
        # Cargar video
        self.btn_load_video = QPushButton("Cargar Video")
        self.btn_load_video.clicked.connect(self.load_video_file)
        self.btn_load_video.setEnabled(False)
        layout.addWidget(self.btn_load_video)
        
        # Reprocesar
        self.btn_reprocess = QPushButton("Reprocesar")
        self.btn_reprocess.clicked.connect(self.start_reprocessing)
        self.btn_reprocess.setEnabled(False)
        layout.addWidget(self.btn_reprocess)
        
        # Estado
        self.lbl_status = QLabel("Cargar archivo SIEV para comenzar")
        layout.addWidget(self.lbl_status)
        
        layout.addStretch()
        
        return panel
        
    def create_left_panel(self) -> QWidget:
        """Crear panel izquierdo con video y controles"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Video display
        video_group = QGroupBox("Video")
        video_layout = QVBoxLayout(video_group)
        
        self.video_label = QLabel("No hay video cargado")
        self.video_label.setMinimumSize(400, 300)
        self.video_label.setStyleSheet("border: 1px solid gray;")
        self.video_label.setAlignment(Qt.AlignCenter)
        video_layout.addWidget(self.video_label)
        
        layout.addWidget(video_group)
        
        # Controles de tiempo
        time_group = QGroupBox("Control de Tiempo")
        time_layout = QVBoxLayout(time_group)
        
        self.time_slider = QSlider(Qt.Horizontal)
        self.time_slider.setMinimum(0)
        self.time_slider.setMaximum(1000)
        self.time_slider.setValue(0)
        self.time_slider.valueChanged.connect(self.time_slider_changed)
        time_layout.addWidget(self.time_slider)
        
        self.time_label = QLabel("Tiempo: 0.00s / 0.00s")
        time_layout.addWidget(self.time_label)
        
        layout.addWidget(time_group)
        
        # Controles de umbrales
        threshold_group = self.create_threshold_controls()
        layout.addWidget(threshold_group)
        
        return widget
        
    def create_threshold_controls(self) -> QWidget:
        """Crear controles de umbrales"""
        group = QGroupBox("Umbrales de Procesamiento")
        layout = QGridLayout(group)
        
        # Threshold Right (solo ojo derecho)
        layout.addWidget(QLabel("Threshold Right:"), 0, 0)
        self.slider_threshold_right = QSlider(Qt.Horizontal)
        self.slider_threshold_right.setMinimum(1)
        self.slider_threshold_right.setMaximum(255)
        self.slider_threshold_right.setValue(50)
        self.slider_threshold_right.valueChanged.connect(
            lambda v: self.threshold_changed('threshold_right', v)
        )
        layout.addWidget(self.slider_threshold_right, 0, 1)
        self.lbl_threshold_right = QLabel("50")
        layout.addWidget(self.lbl_threshold_right, 0, 2)
        
        # Erode Right
        layout.addWidget(QLabel("Erode Right:"), 1, 0)
        self.slider_erode_right = QSlider(Qt.Horizontal)
        self.slider_erode_right.setMinimum(1)
        self.slider_erode_right.setMaximum(10)
        self.slider_erode_right.setValue(2)
        self.slider_erode_right.valueChanged.connect(
            lambda v: self.threshold_changed('erode_right', v)
        )
        layout.addWidget(self.slider_erode_right, 1, 1)
        self.lbl_erode_right = QLabel("2")
        layout.addWidget(self.lbl_erode_right, 1, 2)
        
        # Nose Width
        layout.addWidget(QLabel("Nose Width:"), 2, 0)
        self.slider_nose_width = QSlider(Qt.Horizontal)
        self.slider_nose_width.setMinimum(10)
        self.slider_nose_width.setMaximum(50)
        self.slider_nose_width.setValue(25)
        self.slider_nose_width.valueChanged.connect(
            lambda v: self.threshold_changed('nose_width', v/100.0)
        )
        layout.addWidget(self.slider_nose_width, 2, 1)
        self.lbl_nose_width = QLabel("0.25")
        layout.addWidget(self.lbl_nose_width, 2, 2)
        
        # Eye Height
        layout.addWidget(QLabel("Eye Height:"), 3, 0)
        self.slider_eye_height = QSlider(Qt.Horizontal)
        self.slider_eye_height.setMinimum(20)
        self.slider_eye_height.setMaximum(80)
        self.slider_eye_height.setValue(50)
        self.slider_eye_height.valueChanged.connect(
            lambda v: self.threshold_changed('eye_height', v/100.0)
        )
        layout.addWidget(self.slider_eye_height, 3, 1)
        self.lbl_eye_height = QLabel("0.50")
        layout.addWidget(self.lbl_eye_height, 3, 2)
        
        return group
        
    def create_right_panel(self) -> QWidget:
        """Crear panel derecho con gráficos"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Selector de tipo de gráfico
        graph_control = QHBoxLayout()
        graph_control.addWidget(QLabel("Tipo de gráfico:"))
        
        self.combo_graph_type = QComboBox()
        self.combo_graph_type.addItems(["Espontáneo (Simple)", "Calórico (Avanzado)"])
        self.combo_graph_type.currentTextChanged.connect(self.graph_type_changed)
        graph_control.addWidget(self.combo_graph_type)
        graph_control.addStretch()
        
        layout.addLayout(graph_control)
        
        # Container para gráficos
        self.graph_container = QWidget()
        self.graph_layout = QVBoxLayout(self.graph_container)
        layout.addWidget(self.graph_container)
        
        # Inicializar con gráfico simple
        self.setup_simple_graph()
        
        return widget
        
    def setup_simple_graph(self):
        """Configurar gráfico simple para espontáneo"""
        self.clear_graph_container()
        
        # Gráfico PyQtGraph simple
        self.simple_plot = pg.PlotWidget(title="Posición Pupila - Ojo Derecho")
        self.simple_plot.setLabel('left', 'Posición X Pupila', units='px')
        self.simple_plot.setLabel('bottom', 'Tiempo', units='s')
        self.simple_plot.showGrid(x=True, y=True)
        
        # Curva de datos
        self.simple_curve = self.simple_plot.plot([], [], pen='b', name='Ojo Derecho')
        
        # Línea de tiempo
        self.simple_time_line = pg.InfiniteLine(
            pos=0, angle=90, pen=pg.mkPen(color='r', width=2),
            movable=True, label="Tiempo"
        )
        self.simple_plot.addItem(self.simple_time_line)
        
        self.graph_layout.addWidget(self.simple_plot)
        
    def setup_caloric_graph(self):
        """Configurar gráfico tipo calórico"""
        self.clear_graph_container()
        
        # Usar CaloricGraph existente
        try:
            self.caloric_graph = CaloricGraph(
                total_duration=60.0,  # Se actualizará con duración real
                parent=self.graph_container
            )
            self.graph_layout.addWidget(self.caloric_graph)
        except Exception as e:
            print(f"Error creando CaloricGraph: {e}")
            # Fallback a gráfico simple
            self.setup_simple_graph()
            
    def clear_graph_container(self):
        """Limpiar container de gráficos"""
        while self.graph_layout.count():
            child = self.graph_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
    def load_siev_file(self):
        """Cargar archivo SIEV"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Cargar archivo SIEV", "", "Archivos SIEV (*.siev);;Todos los archivos (*)"
        )
        
        if not file_path:
            return
            
        try:
            # Los archivos SIEV son tar.gz que contienen metadata.json
            import tarfile
            
            with tarfile.open(file_path, 'r:gz') as tar:
                # Buscar metadata.json específicamente
                try:
                    metadata_file = tar.extractfile('metadata.json')
                    if metadata_file:
                        content = metadata_file.read().decode('utf-8')
                        self.siev_data = json.loads(content)
                    else:
                        print("No se encontró metadata.json en el archivo SIEV")
                        return
                except KeyError:
                    # Si no existe metadata.json, intentar backup
                    try:
                        backup_file = tar.extractfile('metadata_backup.json')
                        if backup_file:
                            content = backup_file.read().decode('utf-8')
                            self.siev_data = json.loads(content)
                            print("Usando metadata_backup.json")
                        else:
                            print("No se encontró metadata.json ni metadata_backup.json")
                            return
                    except KeyError:
                        print("Archivo SIEV no contiene los archivos de metadata esperados")
                        return
                
            # Cargar pruebas en combo
            self.combo_tests.clear()
            test_names = []
            
            if 'pruebas' in self.siev_data:
                # La estructura correcta es 'pruebas' (no 'tests')
                for prueba in self.siev_data['pruebas']:
                    test_id = prueba.get('id', 'sin_id')
                    test_type = prueba.get('tipo', 'desconocido')
                    test_name = f"{test_id} ({test_type})"
                    test_names.append(test_name)
                    
                self.combo_tests.addItems(test_names)
            
            self.btn_load_video.setEnabled(len(test_names) > 0)
            self.lbl_status.setText(f"SIEV cargado: {len(test_names)} pruebas encontradas")
            
        except Exception as e:
            print(f"Error cargando archivo SIEV: {e}")
            return
            
    def test_selected(self, test_name: str):
        """Prueba seleccionada"""
        if not test_name or not self.siev_data:
            return
            
        # Extraer el ID de la prueba del texto del combo (formato: "id (tipo)")
        test_id = test_name.split(' (')[0] if ' (' in test_name else test_name
        
        # Buscar la prueba en los datos SIEV
        for prueba in self.siev_data.get('pruebas', []):
            if prueba.get('id') == test_id:
                self.current_test = prueba
                self.lbl_status.setText(f"Prueba seleccionada: {test_name}")
                break
            
    def load_video_file(self):
        """Cargar archivo de video"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Cargar video", "", "Videos (*.mp4 *.avi *.mov *.mkv);;Todos los archivos (*)"
        )
        
        if not file_path:
            return
            
        self.video_path = file_path
        
        # Inicializar video player
        try:
            with open(file_path, 'rb') as f:
                video_data = f.read()
                
            self.video_player = VideoPlayerThread(video_data)
            self.video_player.frame_ready.connect(self.update_video_display)
            self.video_player.duration_changed.connect(self.video_duration_changed)
            
            # Cargar video
            if self.video_player.load_video_from_data():
                self.btn_reprocess.setEnabled(True)
                self.lbl_status.setText("Video cargado correctamente")
            else:
                self.lbl_status.setText("Error cargando video")
                
        except Exception as e:
            print(f"Error cargando video: {e}")
            return
            
    def start_reprocessing(self):
        """Iniciar reprocesamiento del video"""
        if self.is_processing or not self.video_path:
            return
            
        # Limpiar datos existentes del gráfico
        self.clear_graph_data()
        
        # Iniciar procesamiento
        self.is_processing = True
        self.btn_reprocess.setEnabled(False)
        self.lbl_status.setText("Reprocesando video...")
        
        self.processor_thread = SimpleVideoProcessor(self.video_path, self.thresholds)
        self.processor_thread.progress_updated.connect(self.update_progress)
        self.processor_thread.frame_processed.connect(self.process_frame_data)
        self.processor_thread.processing_finished.connect(self.processing_completed)
        self.processor_thread.start()
        
    def clear_graph_data(self):
        """Limpiar datos del gráfico actual"""
        current_type = self.combo_graph_type.currentText()
        
        if "Simple" in current_type and hasattr(self, 'simple_curve'):
            self.simple_curve.setData([], [])
            # Limpiar arrays de datos
            if hasattr(self, 'simple_data_x'):
                self.simple_data_x.clear()
            if hasattr(self, 'simple_data_y_x'):
                self.simple_data_y_x.clear()
            if hasattr(self, 'simple_data_y_y'):
                self.simple_data_y_y.clear()
        elif "Avanzado" in current_type and hasattr(self, 'caloric_graph'):
            # Limpiar datos del CaloricGraph
            try:
                self.caloric_graph.clear_all_data()
            except:
                pass
                
    def process_frame_data(self, frame, timestamp: float, pupil_x: float, pupil_y: float):
        """Procesar datos de frame"""
        # Almacenar frame actual
        self.current_frame = frame
        
        # Agregar datos al gráfico actual
        current_type = self.combo_graph_type.currentText()
        
        if "Simple" in current_type and hasattr(self, 'simple_curve'):
            # Actualizar gráfico simple con posiciones de pupila
            if not hasattr(self, 'simple_data_x'):
                self.simple_data_x = []
                self.simple_data_y_x = []  # Posición X de pupila
                self.simple_data_y_y = []  # Posición Y de pupila
                
            self.simple_data_x.append(timestamp)
            self.simple_data_y_x.append(pupil_x)
            self.simple_data_y_y.append(pupil_y)
            
            # Mostrar solo posición X por ahora (se puede cambiar)
            self.simple_curve.setData(self.simple_data_x, self.simple_data_y_x)
            
        elif "Avanzado" in current_type and hasattr(self, 'caloric_graph'):
            # Para gráfico calórico, usar posición X como velocidad angular
            try:
                self.caloric_graph.add_data_point(timestamp, pupil_x)
            except:
                pass
                
    def processing_completed(self):
        """Procesamiento completado"""
        self.is_processing = False
        self.btn_reprocess.setEnabled(True)
        self.lbl_status.setText("Procesamiento completado")
        
        if self.processor_thread:
            self.processor_thread.quit()
            self.processor_thread.wait()
            self.processor_thread = None
            
    def update_progress(self, progress: int):
        """Actualizar progreso"""
        self.lbl_status.setText(f"Procesando... {progress}%")
        
    def threshold_changed(self, param: str, value):
        """Cambio en umbrales"""
        self.thresholds[param] = value
        
        # Actualizar labels
        if param == 'threshold_right':
            self.lbl_threshold_right.setText(str(value))
        elif param == 'erode_right':
            self.lbl_erode_right.setText(str(value))
        elif param == 'nose_width':
            self.lbl_nose_width.setText(f"{value:.2f}")
        elif param == 'eye_height':
            self.lbl_eye_height.setText(f"{value:.2f}")
            
    def time_slider_changed(self, value: int):
        """Cambio en slider de tiempo"""
        if not self.video_player:
            return
            
        # Convertir valor del slider a tiempo
        max_time = self.video_player.duration
        current_time = (value / 1000.0) * max_time
        
        # Actualizar video player
        if self.video_player:
            try:
                self.video_player.seek_to_time(current_time)
            except:
                pass
            
        # Actualizar líneas de tiempo en gráficos
        if hasattr(self, 'simple_time_line'):
            self.simple_time_line.setPos(current_time)
        if hasattr(self, 'caloric_graph'):
            try:
                self.caloric_graph.set_pos_time_video(current_time)
            except:
                pass
                
        # Actualizar label de tiempo
        self.time_label.setText(f"Tiempo: {current_time:.2f}s / {max_time:.2f}s")
        
    def video_duration_changed(self, duration: float):
        """Duración de video cambiada"""
        # Actualizar gráfico calórico si existe
        if hasattr(self, 'caloric_graph'):
            try:
                self.caloric_graph.total_duration = duration
                self.caloric_graph.rebuild_phases()
            except:
                pass
                
    def graph_type_changed(self, graph_type: str):
        """Cambio de tipo de gráfico"""
        if "Simple" in graph_type:
            self.setup_simple_graph()
        else:
            self.setup_caloric_graph()
            
    def update_video_display(self, frame, pupil_positions, gray_frame):
        """Actualizar display de video"""
        if frame is not None:
            # Convertir frame a QImage y mostrar
            height, width, channel = frame.shape
            bytes_per_line = 3 * width
            q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
            
            # Escalar para mostrar
            pixmap = QPixmap.fromImage(q_image)
            scaled_pixmap = pixmap.scaled(
                self.video_label.size(), 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            self.video_label.setPixmap(scaled_pixmap)


def main():
    """Función principal"""
    app = QApplication(sys.argv)
    
    # Configurar estilo de gráficos
    pg.setConfigOption('background', 'w')
    pg.setConfigOption('foreground', 'k')
    
    window = SimpleProcessorWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()