import cv2
import os
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QImage, QPixmap


class CameraController(QThread):
    """Controls camera access and emits ready-to-display frames."""

    frame_ready = Signal(QPixmap)

    def __init__(self):
        super().__init__()
        self.camera = None
        self.recording = False
        self.video_writer = None
        self.running = False
        self.camera_index = 2

    def get_available_cameras(self):
        """Detect available cameras."""
        available_cameras = []
        for i in range(10):
            try:
                if i > 0:
                    cap = cv2.VideoCapture(i, cv2.CAP_V4L2)
                    if cap.isOpened():
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            available_cameras.append(i)
                    cap.release()
            except Exception:
                continue
        if not available_cameras:
            for i in range(5):
                try:
                    if i > 0:
                        cap = cv2.VideoCapture(i)
                        if cap.isOpened():
                            ret, frame = cap.read()
                            if ret and frame is not None:
                                available_cameras.append(i)
                        cap.release()
                except Exception:
                    continue
        return available_cameras

    def start_camera(self, camera_index=2):
        """Start the camera feed."""
        self.camera_index = camera_index
        if self.camera:
            self.camera.release()
        self.camera = cv2.VideoCapture(self.camera_index)
        if self.camera.isOpened():
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
            self.camera.set(cv2.CAP_PROP_FPS, 120)
            self.camera.set(cv2.CAP_PROP_AUTOFOCUS, 0)
            self.camera.set(cv2.CAP_PROP_AUTO_EXPOSURE, 3)
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.running = True
            if not self.isRunning():
                self.start()
            return True
        return False

    def change_camera(self, camera_index):
        """Change the active camera."""
        was_recording = self.recording
        current_filename = getattr(self, 'current_filename', None)
        if was_recording:
            self.stop_recording()
        if self.camera:
            self.camera.release()
        success = self.start_camera(camera_index)
        if was_recording and success and current_filename:
            self.start_recording(current_filename)
        return success

    def stop_camera(self):
        """Stop the camera thread and release resources."""
        self.running = False
        if self.recording:
            self.stop_recording()
        if self.camera:
            try:
                self.camera.release()
            finally:
                self.camera = None
        if self.isRunning():
            self.quit()
            self.wait(3000)
        cv2.destroyAllWindows()

    def start_recording(self, filename):
        """Start video recording to the given filename."""
        if self.camera and self.camera.isOpened():
            directory = os.path.dirname(filename)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            fps = 30.0
            frame_size = (640, 480)
            self.video_writer = cv2.VideoWriter(filename, fourcc, fps, frame_size)
            self.recording = True
            self.current_filename = filename
            return True
        return False

    def stop_recording(self):
        """Stop video recording."""
        self.recording = False
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None

    def run(self):
        """Thread loop that captures frames and emits them."""
        while self.running:
            if self.camera and self.camera.isOpened():
                ret, frame = self.camera.read()
                if ret:
                    if self.recording and self.video_writer:
                        self.video_writer.write(frame)
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w, ch = rgb_frame.shape
                    bytes_per_line = ch * w
                    qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                    pixmap = QPixmap.fromImage(qt_image).scaled(640, 480, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    self.frame_ready.emit(pixmap)
                else:
                    self.camera.release()
                    self.camera = cv2.VideoCapture(self.camera_index)
            self.msleep(33)

