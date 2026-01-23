# src/managers/video_manager_api.py
"""
Video Manager API - Refactored without PyQt dependencies
Provides video capture, processing, and streaming via TCP to Rust orchestrator.
"""

import os
import cv2
import numpy as np
import time
import threading
import json
import logging
from typing import Optional, List, Dict, Any, Generator
from queue import Queue, Empty
from collections import deque

from utils.video.video_processes import VideoProcesses
from utils.camera_resolution_detector import CameraResolutionDetector
from utils.v4l2_camera import V4L2Camera
from utils.simple_tracker import PrecisionTracker
from utils.eye_data_processor import EyeDataProcessor
from utils.exceptions import CameraError

logger = logging.getLogger(__name__)


class VideoManagerAPI:
    """
    Manages video capture and processing for the API server.
    Replaces PyQt signals with queues and callbacks for data flow.
    """

    def __init__(self):
        # Video processing
        self.video_processes: Optional[VideoProcesses] = None
        self.camera_id = 0

        # Configuration
        self.cap_width = 960
        self.cap_height = 540
        self.cap_fps = 120
        self.brightness = -21
        self.contrast = 50
        self.threshold = [0, 0] # [right, left]
        self.erode = [0, 0] # [right, left]
        self.nose_width = 0.25
        self.eye_height = 0.25
        self.use_yolo = True
        self.storage_path: Optional[str] = None

        # State
        self.is_capturing = False
        self.is_recording = False
        self.is_initialized = False

        # Frame buffer for MJPEG streaming
        self.frame_buffer: Queue = Queue(maxsize=3)
        self.latest_frame: Optional[np.ndarray] = None
        self.frame_lock = threading.Lock()

        # Eye data buffer
        self.eye_data_buffer: Queue = Queue(maxsize=100)
        self.latest_eye_data: Optional[Dict] = None
        self.eye_data_lock = threading.Lock()

        # Trackers
        self.tracker_left = PrecisionTracker()
        self.tracker_right = PrecisionTracker()

        # Data processor
        self.eye_processor = EyeDataProcessor()

        # Frame reader thread
        self.reader_thread: Optional[threading.Thread] = None
        self.reader_running = False

        # FPS tracking
        self.fps_values = deque(maxlen=30)
        self.current_fps = 0.0
        self.last_frame_time = time.time()

        # Recording
        self.video_recorder = None
        self.recording_frames: List = []

        logger.info("VideoManagerAPI initialized")

    def initialize(
        self,
        camera_id: int = 0,
        width: int = 960,
        height: int = 540,
        fps: int = 120,
        brightness: int = -21,
        contrast: int = 50,
        threshold: List[int] = [0, 0],
        erode: List[int] = [0, 0],
        nose_width: float = 0.25,
        eye_height: float = 0.25,
        use_yolo: bool = True,
        storage_path: Optional[str] = None
    ) -> bool:
        """
        Initialize the video capture system.

        Args:
            camera_id: Camera device index
            width: Capture width
            height: Capture height
            fps: Target frames per second
            brightness: Camera brightness setting
            contrast: Camera contrast setting
            threshold: Eye threshold values [right, left]
            erode: Eye erosion values [right, left]
            nose_width: Width of nose ROI separation
            eye_height: Height of eye ROI
            use_yolo: Whether to use YOLO detection
            storage_path: Base path for storing recorded videos

        Returns:
            bool: True if initialization was successful
        """
        try:
            self.camera_id = camera_id
            self.cap_width = width
            self.cap_height = height
            self.cap_fps = fps
            self.brightness = brightness
            self.contrast = contrast
            self.threshold = threshold
            self.erode = erode
            self.nose_width = nose_width
            self.eye_height = eye_height
            self.use_yolo = use_yolo
            self.storage_path = storage_path

            # Stop existing processes if they exist to release resources (camera)
            if self.video_processes:
                logger.info("Stopping existing video processes before re-initialization")
                try:
                    self.video_processes.stop()
                    self.video_processes = None
                    # Give the OS time to release the video device handle
                    time.sleep(1.0)
                except Exception as e:
                    logger.error(f"Error stopping existing video processes: {e}")
                    self.video_processes = None

            # Create video processes
            self.video_processes = VideoProcesses(
                camera_id=camera_id,
                cap_width=width,
                cap_height=height,
                cap_fps=fps,
                brightness=brightness,
                contrast=contrast
            )
            
            # Apply additional settings
            self.video_processes.threslhold[0] = threshold[0]
            self.video_processes.threslhold[1] = threshold[1]
            self.video_processes.erode[0] = erode[0]
            self.video_processes.erode[1] = erode[1]
            self.video_processes.nose_width.value = nose_width
            self.video_processes.eye_height.value = eye_height
            self.video_processes.use_yolo.value = use_yolo

            self.is_initialized = True
            logger.info(f"VideoManagerAPI initialized: {width}x{height}@{fps}fps")
            return True

        except Exception as e:
            logger.error(f"Error initializing video manager: {e}")
            self.is_initialized = False
            return False

    def start_capture(self) -> bool:
        """Start video capture"""
        if not self.is_initialized:
            logger.error("Error: Video manager not initialized before start_capture")
            return False

        if self.is_capturing:
            logger.warning("Warning: Already capturing")
            return True

        try:
            logger.info("Starting video processes...")
            # Start video processing
            self.video_processes.start()

            logger.info("Starting frame reader thread...")
            # Start frame reader thread
            self.reader_running = True
            self.reader_thread = threading.Thread(target=self._frame_reader_loop, daemon=True)
            self.reader_thread.start()

            self.is_capturing = True
            logger.info("Video capture started successfully")
            return True

        except Exception as e:
            logger.error(f"Error starting capture: {e}", exc_info=True)
            return False

    def stop_capture(self):
        """Stop video capture"""
        logger.info("Stopping video capture...")
        self.reader_running = False
        self.is_capturing = False

        if self.reader_thread and self.reader_thread.is_alive():
            self.reader_thread.join(timeout=1.0)
        self.reader_thread = None

        if self.video_processes:
            self.video_processes.stop()
            self.video_processes = None

        self.is_initialized = False
        logger.info("Video capture stopped")

    def _frame_reader_loop(self):
        """Thread loop that reads frames from video processes and updates buffers"""
        while self.reader_running:
            try:
                if self.video_processes and hasattr(self.video_processes, 'ui_queue'):
                    if not self.video_processes.ui_queue.empty():
                        output = self.video_processes.ui_queue.get(timeout=0.1)

                        frame = output['frame']
                        pupil_positions = output['pupil_positions']
                        timestamp = time.time()

                        # Update FPS
                        current_time = time.time()
                        if self.last_frame_time > 0:
                            fps = 1.0 / max(current_time - self.last_frame_time, 0.001)
                            self.fps_values.append(fps)
                            if len(self.fps_values) >= 10:
                                self.current_fps = sum(self.fps_values) / len(self.fps_values)
                        self.last_frame_time = current_time

                        # Update frame buffer
                        with self.frame_lock:
                            self.latest_frame = frame.copy()

                        # Process eye positions
                        self._process_eye_positions(pupil_positions, timestamp)

                        # Handle recording
                        if self.is_recording:
                            self.recording_frames.append(frame.copy())
                    else:
                        time.sleep(0.001)
                else:
                    time.sleep(0.01)

            except Empty:
                continue
            except Exception as e:
                logger.error(f"Error in frame reader: {e}")
                time.sleep(0.01)


    def _process_eye_positions(self, pupil_positions: List, timestamp: float):
        """
        Process raw eye position data, applying tracking and smoothing.

        Args:
            pupil_positions: List of [x, y] coordinates for left and right eyes.
                             Index 0 is left eye, Index 1 is right eye.
            timestamp: The timestamp of the frame capture.
        """
        left_eye = pupil_positions[0] if pupil_positions[0] is not None else None
        right_eye = pupil_positions[1] if pupil_positions[1] is not None else None

        # Apply tracking
        if left_eye:
            tracked = self.tracker_left.update(tuple(left_eye + [5]), timestamp)
            if tracked is not None:
                left_eye = [int(tracked[0]), int(tracked[1])]

        if right_eye:
            tracked = self.tracker_right.update(tuple(right_eye + [5]), timestamp)
            if tracked is not None:
                right_eye = [int(tracked[0]), int(tracked[1])]

        # Process through EyeDataProcessor
        processed_data = self.eye_processor.process_eye_data(
            left_eye=left_eye,
            right_eye=right_eye,
            imu_x=0.0,  # Will be updated when hardware manager provides data
            imu_y=0.0,
            timestamp=timestamp
        )

        # Store latest eye data
        eye_data = {
            'timestamp': timestamp,
            'left_eye': left_eye,
            'right_eye': right_eye,
            'processed': processed_data[-1] if processed_data else None,
            'is_calibrated': self.eye_processor.is_calibrated,
            'fps': self.current_fps
        }

        with self.eye_data_lock:
            self.latest_eye_data = eye_data

        # Add to buffer for streaming
        try:
            self.eye_data_buffer.put_nowait(eye_data)
        except:
            pass  # Buffer full, skip

    def generate_mjpeg_frames(self) -> Generator[bytes, None, None]:
        """
        Generator that yields MJPEG frames for streaming.

        Yields:
            bytes: JPEG encoded frame with MJPEG boundary
        """
        while self.is_capturing:
            with self.frame_lock:
                frame = self.latest_frame

            if frame is not None:
                try:
                    # Encode frame as JPEG
                    _, jpeg = cv2.imencode('.jpg', cv2.cvtColor(frame, cv2.COLOR_RGB2BGR),
                                          [cv2.IMWRITE_JPEG_QUALITY, 80])

                    # Yield with MJPEG boundary
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
                except Exception as e:
                    logger.error(f"Error encoding frame: {e}")

            # Control streaming rate (~30 FPS for streaming)
            time.sleep(0.033)

    def get_latest_eye_data_batch(self) -> List[Dict]:
        """Get all pending eye data points from the buffer"""
        batch = []
        try:
            while not self.eye_data_buffer.empty():
                batch.append(self.eye_data_buffer.get_nowait())
        except Empty:
            pass
        return batch

    def get_latest_eye_data(self) -> Optional[str]:
        """Get latest eye data as JSON string for SSE streaming (Legacy/Single)"""
        with self.eye_data_lock:
            if self.latest_eye_data:
                return json.dumps(self.latest_eye_data)
        return None

    def start_recording(self) -> bool:
        """Start recording video"""
        if not self.is_capturing:
            logger.error("Error: Cannot record without capture")
            return False

        self.recording_frames = []
        self.is_recording = True
        logger.info("Recording started")
        return True

    def stop_recording(self) -> Optional[str]:
        """Stop recording and save video"""
        if not self.is_recording:
            return None

        self.is_recording = False

        if self.recording_frames:
            # Save recording
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"recording_{timestamp}.avi"
            
            if self.storage_path:
                try:
                    os.makedirs(self.storage_path, exist_ok=True)
                    filename = os.path.join(self.storage_path, filename)
                except Exception as e:
                    logger.error(f"Error creating storage directory: {e}")

            try:
                height, width = self.recording_frames[0].shape[:2]
                fourcc = cv2.VideoWriter_fourcc(*'XVID')
                out = cv2.VideoWriter(filename, fourcc, 30.0, (width, height))

                for frame in self.recording_frames:
                    # Convert RGB to BGR for saving
                    bgr_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    out.write(bgr_frame)

                out.release()
                logger.info(f"Recording saved: {filename}")
                return filename
            except Exception as e:
                logger.error(f"Error saving recording: {e}")
                return None
            finally:
                self.recording_frames = []
        else:
            return None

    def update_config(
        self,
        brightness: Optional[int] = None,
        contrast: Optional[int] = None,
        threshold: Optional[List[int]] = None,
        erode: Optional[List[int]] = None,
        nose_width: Optional[float] = None,
        eye_height: Optional[float] = None,
        use_yolo: Optional[bool] = None,
        show_debug: Optional[bool] = None
    ):
        """
        Update video configuration dynamically during runtime.

        Args:
            brightness: Camera brightness level.
            contrast: Camera contrast level.
            threshold: List of threshold values [right_eye, left_eye].
            erode: List of erosion iterations [right_eye, left_eye].
            nose_width: Width of the nose region as a fraction of total width.
            eye_height: Height of the eye region as a fraction of total height.
            use_yolo: Enable or disable YOLO-based detection.
            show_debug: Enable or disable debug overlay on the video feed.
        """
        if self.video_processes:
            if brightness is not None:
                self.video_processes.brightness.value = brightness
                self.brightness = brightness
                self.video_processes.color_changed.value = True

            if contrast is not None:
                self.video_processes.contrast.value = contrast
                self.contrast = contrast
                self.video_processes.color_changed.value = True

            if threshold is not None:
                self.video_processes.threslhold[0] = threshold[0]
                self.video_processes.threslhold[1] = threshold[1]
                self.threshold = threshold

            if erode is not None:
                self.video_processes.erode[0] = erode[0]
                self.video_processes.erode[1] = erode[1]
                self.erode = erode

            if nose_width is not None:
                self.video_processes.nose_width.value = nose_width
                self.nose_width = nose_width
                self.video_processes.changed_nose.value = True

            if eye_height is not None:
                self.video_processes.eye_height.value = eye_height
                self.eye_height = eye_height
                self.video_processes.changed_eye_height.value = True

            if use_yolo is not None:
                self.video_processes.use_yolo.value = use_yolo
                self.use_yolo = use_yolo

            if show_debug is not None:
                self.video_processes.slider_th_pressed.value = show_debug

    def toggle_yolo(self, enabled: bool):
        """Toggle YOLO detection mode"""
        if self.video_processes:
            self.video_processes.use_yolo.value = enabled
            logger.info(f"YOLO detection: {'enabled' if enabled else 'disabled'}")

    def set_pupil_mode(self, mode: str):
        """
        Set pupil detection mode.

        Args:
            mode: "legacy", "fast", or "hybrid"
        """
        if self.video_processes:
            self.video_processes.set_pupil_mode(mode)

    def set_pupil_config(
        self,
        # Fast detector params
        search_window_multiplier: Optional[float] = None,
        dark_threshold_percent: Optional[int] = None,
        starburst_rays: Optional[int] = None,
        starburst_min_gradient: Optional[int] = None,
        fallback_threshold: Optional[int] = None,
        # Legacy detector params
        legacy_blur_enabled: Optional[bool] = None,
        legacy_blur_kernel: Optional[int] = None,
        legacy_clahe_enabled: Optional[bool] = None,
        legacy_clahe_clip_limit: Optional[float] = None,
        legacy_clahe_grid_size: Optional[int] = None,
        legacy_morph_enabled: Optional[bool] = None,
        legacy_morph_close_iterations: Optional[int] = None,
        legacy_morph_dilate_iterations: Optional[int] = None
    ):
        """
        Update pupil detection configuration.

        Args:
            # Fast detector
            search_window_multiplier: Window size = radius × N (default 3.0)
            dark_threshold_percent: % above darkest point (default 20)
            starburst_rays: Number of starburst rays (default 16)
            starburst_min_gradient: Min gradient for edge detection (default 30)
            fallback_threshold: Frames without detection before fallback (default 5)

            # Legacy detector
            legacy_blur_enabled: Enable GaussianBlur (default True)
            legacy_blur_kernel: Blur kernel size (default 5)
            legacy_clahe_enabled: Enable CLAHE (default True)
            legacy_clahe_clip_limit: CLAHE clip limit (default 2.0)
            legacy_clahe_grid_size: CLAHE grid size (default 8)
            legacy_morph_enabled: Enable morphological ops (default True)
            legacy_morph_close_iterations: Close iterations (default 1)
            legacy_morph_dilate_iterations: Dilate iterations (default 1)
        """
        if self.video_processes:
            kwargs = {}
            # Fast detector params
            if search_window_multiplier is not None:
                kwargs['search_window_multiplier'] = search_window_multiplier
            if dark_threshold_percent is not None:
                kwargs['dark_threshold_percent'] = dark_threshold_percent
            if starburst_rays is not None:
                kwargs['starburst_rays'] = starburst_rays
            if starburst_min_gradient is not None:
                kwargs['starburst_min_gradient'] = starburst_min_gradient
            if fallback_threshold is not None:
                kwargs['fallback_threshold'] = fallback_threshold

            # Legacy detector params
            if legacy_blur_enabled is not None:
                kwargs['legacy_blur_enabled'] = legacy_blur_enabled
            if legacy_blur_kernel is not None:
                kwargs['legacy_blur_kernel'] = legacy_blur_kernel
            if legacy_clahe_enabled is not None:
                kwargs['legacy_clahe_enabled'] = legacy_clahe_enabled
            if legacy_clahe_clip_limit is not None:
                kwargs['legacy_clahe_clip_limit'] = legacy_clahe_clip_limit
            if legacy_clahe_grid_size is not None:
                kwargs['legacy_clahe_grid_size'] = legacy_clahe_grid_size
            if legacy_morph_enabled is not None:
                kwargs['legacy_morph_enabled'] = legacy_morph_enabled
            if legacy_morph_close_iterations is not None:
                kwargs['legacy_morph_close_iterations'] = legacy_morph_close_iterations
            if legacy_morph_dilate_iterations is not None:
                kwargs['legacy_morph_dilate_iterations'] = legacy_morph_dilate_iterations

            if kwargs:
                self.video_processes.set_pupil_config(**kwargs)

    def get_available_resolutions(self, camera_id: Optional[int] = None) -> List[str]:
        """Get list of available camera resolutions for a specific camera"""
        try:
            detector = CameraResolutionDetector()
            cam_id = camera_id if camera_id is not None else self.camera_id
            resolutions = detector.listar_resoluciones(cam_id)
            return resolutions if resolutions else []
        except Exception as e:
            logger.error(f"Error detecting resolutions: {e}")
            return []

    def get_available_cameras(self) -> List[Dict[str, Any]]:
        """Get list of available cameras"""
        try:
            cameras = V4L2Camera.get_connected_cameras()
            result = []
            import re
            for name, path in cameras:
                # Extract ID from /dev/videoX
                try:
                    match = re.search(r'video(\d+)', path)
                    if match:
                        cam_id = int(match.group(1))
                        result.append({"name": name, "path": path, "id": cam_id})
                except:
                    continue
            return result
        except Exception as e:
            logger.error(f"Error detecting cameras: {e}")
            return []

    def get_status(self) -> str:
        """Get current video manager status"""
        if not self.is_initialized:
            return "not_initialized"
        if self.is_capturing:
            return "capturing"
        return "initialized"

    def get_full_status(self) -> Dict[str, Any]:
        """Get full status information"""
        return {
            'is_capturing': self.is_capturing,
            'is_recording': self.is_recording,
            'video_mode': 'live' if self.is_capturing else 'idle',
            'fps': self.current_fps,
            'resolution': f"{self.cap_width}x{self.cap_height}" if self.is_initialized else None
        }

    def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up VideoManagerAPI...")

        self.stop_capture()

        if self.is_recording:
            self.stop_recording()

        self.is_initialized = False
        logger.info("VideoManagerAPI cleaned up")

