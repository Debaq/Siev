import platform
import cv2
import os

if platform.system() == "Linux":
    from utils.V4L2Camera import V4L2Camera as Camera
elif platform.system() == "Windows":
    from utils.WindowsCamera import WindowsCamera as Camera
else:
    raise EnvironmentError("Sistema operativo no soportado")

class CameraConfig:
    def __init__(self):
        self.camera = Camera()
        self.device_path = None
        self.writer = None
        self.is_recording = False

    def get_connected_camera(self, camera_name="DH Camera"):
        cameras = self.camera.get_connected_cameras()
        for cam_name, cam_path in cameras:
            if camera_name in cam_name:
                self.device_path = cam_path
                break
        if not self.device_path:
            raise ValueError(f"No se encontró la cámara {camera_name}")
        return self.device_path

    def setup_camera(self):
        if platform.system() == "Linux":
            self.camera.set_camera(self.device_path, 420, 240)
        elif platform.system() == "Windows":
            self.camera.set_camera(self.device_path)
            self.camera.set_control('frame_size', (420, 240))
        cap = cv2.VideoCapture(self.device_path if platform.system() == "Linux" else 0)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 420)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
        cap.set(cv2.CAP_PROP_FPS, 210)
        cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 3)
        return cap

    def set_focus(self, value):
        self.camera.set_focus(value)
    
    def set_hue(self, value):
        self.camera.set_hue(value)

    def set_brightness(self, value):
        self.camera.set_brightness(value)

    def set_contrast(self, value):
        self.camera.set_contrast(value)

    def set_autofocus(self, value):
        pass
        #self.camera.set_autofocus(value)

    def set_white_balance_automatic(self, value):
        self.camera.set_white_balance_automatic(value)

    def start_recording(self, filename="output.avi"):
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        folder = "record"
        self.writer = cv2.VideoWriter(f"{folder}/{filename}", fourcc, 20.0, (960, 540))

        self.is_recording = True

    def stop_recording(self):
        if self.writer is not None:
            self.writer.release()
            self.writer = None
        self.is_recording = False

    def write_frame(self, frame):
        if self.is_recording and self.writer is not None:
            self.writer.write(frame)

if __name__ == "__main__":

    camera_config = CameraConfig()
    device_path = camera_config.get_connected_camera(camera_name="Camera: Integrated C")
    cap = camera_config.setup_camera()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        cv2.imshow("frame", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()