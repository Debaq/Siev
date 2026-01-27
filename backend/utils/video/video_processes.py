import os
# LÍMITES ESTRICTOS DE HILOS - NIVEL KERNEL
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["ORT_TBB_NUM_THREADS"] = "1"

from ultralytics import YOLO
import cv2
import numpy as np
import torch
import multiprocessing as mp
from multiprocessing import Value, Array
import time
import ctypes
import logging
from queue import Empty
from utils.path_utils import get_model_file_path_prefer_onnx
from utils.video.simulated_box import SimulatedBox
from utils.video.pupil_detectors import (
    create_pupil_detector, DetectorConfig, PupilResult
)
from utils.v4l2_camera import V4L2Camera

logger = logging.getLogger(__name__)

class VideoProcesses:
    def __init__(self, camera_id=0, cap_width=960,
                 cap_height=540, cap_fps=120,
                 brightness=-21, contrast=50):
        self.camera_id = camera_id
        self.cap_width = cap_width
        self.cap_height = cap_height
        self.cap_fps = cap_fps
        
        self.running = Value(ctypes.c_bool, True)
        self.frame_queue = mp.Queue(maxsize=2)
        self.result_queue = mp.Queue(maxsize=20)
        self.ui_queue = mp.Queue(maxsize=2)
        
        self.nose_width = Value(ctypes.c_float, 0.25)
        self.eye_height = Value(ctypes.c_float, 0.25)
        self.changed_nose = Value(ctypes.c_bool, False)
        self.changed_eye_height = Value(ctypes.c_bool, False)

        self.threslhold = Array('i', [0, 0])
        self.erode = Array('i', [0, 0])
        self.cap_error = Value(ctypes.c_bool, False)
        self.slider_th_pressed = Value(ctypes.c_bool, False)
        
        self.brightness = Value(ctypes.c_int, brightness) 
        self.contrast = Value(ctypes.c_int, contrast)    
        self.color_changed = Value(ctypes.c_bool, False)  
        
        self.use_yolo = Value(ctypes.c_bool, True)
        self.yolo_frequency = Value(ctypes.c_int, 40) # YOLO cada 40 frames (~5 veces por seg)
        self.yolo_confidence = Value(ctypes.c_float, 0.4)

        self.pupil_mode = Value(ctypes.c_int, 0)  
        self.legacy_blur_enabled = Value(ctypes.c_bool, True)
        self.legacy_blur_kernel = Value(ctypes.c_int, 5)
        self.legacy_morph_enabled = Value(ctypes.c_bool, True)
        self.legacy_morph_close_iterations = Value(ctypes.c_int, 1)
        self.legacy_morph_dilate_iterations = Value(ctypes.c_int, 1)  
    
        self.capture_process = None
        self.detection_process = None

    def setup_camera(self):
        cap = cv2.VideoCapture(self.camera_id, cv2.CAP_V4L2)
        if not cap.isOpened(): return None
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.cap_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.cap_height)
        cap.set(cv2.CAP_PROP_FPS, self.cap_fps)
        return cap

    def capture_worker(self):
        cap = self.setup_camera()
        if cap is None:
            self.cap_error.value = True
            return
        fps_avg = 0
        frame_count = 0
        last_time = time.time()
        while self.running.value:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.01)
                continue
            frame_count += 1
            if time.time() - last_time >= 1.0:
                fps_avg = frame_count / (time.time() - last_time)
                frame_count = 0
                last_time = time.time()
            if self.frame_queue.full():
                try: self.frame_queue.get_nowait()
                except: pass
            self.frame_queue.put((frame, fps_avg))
        cap.release()

    def detection_worker(self):
        logger.info("Starting ECO-Hybrid Pipeline (YOLO-ONNX + Rust)")
        # Forzar 1 hilo en Torch y ONNX
        torch.set_num_threads(1)
        
        # Intentar cargar ONNX para bajar consumo, si no, usar PT pero capado
        model_path, _ = get_model_file_path_prefer_onnx('siev_vng_r01.pt')
        model = YOLO(model_path, task='detect')

        detector_right = create_pupil_detector("legacy")
        detector_left = create_pupil_detector("legacy")

        ui_last_time = 0
        ui_interval = 1.0 / 25.0 
        detection_counter = 0
        
        # ROI inicial amplia para empezar
        roi_r = [0, 50, 450, 300]
        roi_l = [500, 50, 950, 300]

        while self.running.value:
            try:
                frame, fps = self.frame_queue.get(timeout=0.5)
            except Empty: continue

            h, w = frame.shape[:2]
            now = time.time()

            # 1. IA: Solo si está activada y cada N frames
            if self.use_yolo.value and (detection_counter % self.yolo_frequency.value == 0):
                # Análisis en miniatura (muy rápido)
                small = cv2.resize(frame, (320, 180))
                with torch.no_grad():
                    # Usamos half=False porque en CPU es más lento half
                    results = model.predict(small, conf=self.yolo_confidence.value, verbose=False)
                
                for r in results:
                    boxes = r.boxes.xyxy.cpu().numpy()
                    if len(boxes) >= 2:
                        sorted_boxes = sorted(boxes, key=lambda b: b[0])
                        sx, sy = w / 320, h / 180
                        
                        # Expandir un poco el ROI para que Rust tenga contexto
                        def expand(b, m=15):
                            return [int(max(0, b[0]*sx-m)), int(max(0, b[1]*sy-m)), 
                                    int(min(w, b[2]*sx+m)), int(min(h, b[3]*sy+m))]
                        
                        roi_r = expand(sorted_boxes[0])
                        roi_l = expand(sorted_boxes[1])

            # 2. PROCESADO RUST (210 FPS)
            # Extraer ROIs exactas de YOLO
            img_r = frame[roi_r[1]:roi_r[3], roi_r[0]:roi_r[2]]
            img_l = frame[roi_l[1]:roi_l[3], roi_l[0]:roi_l[2]]

            if img_r.size == 0 or img_l.size == 0: 
                detection_counter += 1
                continue

            d_config = DetectorConfig(
                debug_mode=self.slider_th_pressed.value,
                legacy_blur_enabled=self.legacy_blur_enabled.value,
                legacy_blur_kernel=self.legacy_blur_kernel.value,
                legacy_morph_enabled=self.legacy_morph_enabled.value,
                legacy_morph_dilate_iterations=self.legacy_morph_dilate_iterations.value
            )

            pupil_positions = [None, None]
            
            # Ojo Izquierdo
            d_config.threshold_value = self.threslhold[1]
            d_config.erode_value = self.erode[1]
            res_l = detector_left.detect(img_l, d_config)
            if res_l and res_l.found:
                pupil_positions[0] = [roi_l[0] + res_l.center_x, (roi_l[1] + res_l.center_y) * -1]

            # Ojo Derecho
            d_config.threshold_value = self.threslhold[0]
            d_config.erode_value = self.erode[0]
            res_r = detector_right.detect(img_r, d_config)
            if res_r and res_r.found:
                pupil_positions[1] = [roi_r[0] + res_r.center_x, (roi_r[1] + res_r.center_y) * -1]

            # 3. Telemetría
            if not self.result_queue.full():
                self.result_queue.put({'pupil_positions': pupil_positions, 'fps': fps})

            # 4. UI (Unión Normalizada)
            if now - ui_last_time >= ui_interval:
                th = 200
                ir = cv2.resize(img_r, (int(img_r.shape[1] * th / img_r.shape[0]), th))
                il = cv2.resize(img_l, (int(img_l.shape[1] * th / img_l.shape[0]), th))
                combined = np.hstack((ir, il))
                
                # Marcas
                if res_r and res_r.found:
                    cv2.circle(combined, (int(res_r.center_x * (th / img_r.shape[0])), 
                                         int(res_r.center_y * (th / img_r.shape[0]))), 5, (0, 0, 255), 2)
                if res_l and res_l.found:
                    cv2.circle(combined, (ir.shape[1] + int(res_l.center_x * (th / img_l.shape[0])), 
                                         int(res_l.center_y * (th / img_l.shape[0]))), 5, (255, 191, 0), 2)

                ui_frame = cv2.resize(combined, (w, 400))
                if not self.ui_queue.full():
                    self.ui_queue.put({'frame': ui_frame, 'pupil_positions': pupil_positions})
                ui_last_time = now

            detection_counter += 1

    def start(self, frame_info=None):
        self.running.value = True
        self.capture_process = mp.Process(target=self.capture_worker)
        self.detection_process = mp.Process(target=self.detection_worker)
        self.capture_process.daemon = True
        self.detection_process.daemon = True
        self.capture_process.start()
        self.detection_process.start()

    def set_pupil_mode(self, mode: str): pass
    def set_pupil_config(self, **kwargs):
        if 'legacy_blur_enabled' in kwargs: self.legacy_blur_enabled.value = bool(kwargs['legacy_blur_enabled'])
        if 'legacy_blur_kernel' in kwargs: self.legacy_blur_kernel.value = int(kwargs['legacy_blur_kernel'])
        if 'legacy_morph_enabled' in kwargs: self.legacy_morph_enabled.value = bool(kwargs['legacy_morph_enabled'])
        if 'legacy_morph_close_iterations' in kwargs: self.legacy_morph_close_iterations.value = int(kwargs['legacy_morph_close_iterations'])
        if 'legacy_morph_dilate_iterations' in kwargs: self.legacy_morph_dilate_iterations.value = int(kwargs['legacy_morph_dilate_iterations'])

    def stop(self):
        self.running.value = False
        time.sleep(0.1)
        if self.capture_process: self.capture_process.terminate()
        if self.detection_process: self.detection_process.terminate()
