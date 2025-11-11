import subprocess

class V4L2Camera:
    def __init__(self):
        self.device = None

    @staticmethod
    def get_connected_cameras():
        """Obtiene una lista de todas las cámaras conectadas."""
        result = subprocess.run(['v4l2-ctl', '--list-devices'], stdout=subprocess.PIPE, text=True)
        devices = result.stdout.split('\n\n')
        cameras = []
        for device in devices:
            if device.strip():
                lines = device.split('\n')
                camera_name = lines[0]
                device_path = lines[1].strip()
                cameras.append((camera_name, device_path))
                print(cameras)
        return cameras

    def set_camera(self, device_path, width, height):
        """Configura la cámara activa y ajusta el tamaño del fotograma."""
        self.device = device_path
        self.set_frame_size(width, height)

    def set_frame_size(self, width, height):
        """Ajusta el tamaño del fotograma."""
        if not self.device:
            raise ValueError("No camera device set. Use set_camera() first.")
        command = ["v4l2-ctl", "--device={}".format(self.device), "--set-fmt-video=width={},height={}".format(width, height)]
        result = subprocess.run(command, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            print(f"Error setting frame size: {result.stderr}")

    def set_control(self, control, value):
        """Ajusta un parámetro específico de la cámara."""
        if not self.device:
            raise ValueError("No camera device set. Use set_camera() first.")
        command = ["v4l2-ctl", "--device={}".format(self.device), "--set-ctrl={}={}".format(control, value)]
        result = subprocess.run(command, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            print(f"Error setting control {control}: {result.stderr}")

    def set_brightness(self, value):
        """Ajusta el brillo de la cámara."""
        self.set_control('brightness', value)

    def set_contrast(self, value):
        """Ajusta el contraste de la cámara."""
        self.set_control('contrast', value)

    def set_saturation(self, value):
        """Ajusta la saturación de la cámara."""
        self.set_control('saturation', value)

    def set_hue(self, value):
        """Ajusta el tono de la cámara."""
        self.set_control('hue', value)

    def set_gamma(self, value):
        """Ajusta el gamma de la cámara."""
        self.set_control('gamma', value)

    def set_sharpness(self, value):
        """Ajusta la nitidez de la cámara."""
        self.set_control('sharpness', value)

    def set_backlight_compensation(self, value):
        """Ajusta la compensación de contraluz de la cámara."""
        self.set_control('backlight_compensation', value)

    def set_exposure_time_absolute(self, value):
        """Ajusta el tiempo de exposición absoluto de la cámara."""
        self.set_control('exposure_time_absolute', value)

    def set_focus(self, value):
        """Ajusta el enfoque de la cámara."""
        self.set_control('focus_absolute', value)

    def set_autofocus(self, value):
        """Ajusta el enfoque automático de la cámara."""
        
        #self.set_control('focus_automatic_continuous', value)

    def set_white_balance_automatic(self, value):
        """Ajusta el balance de blancos automático de la cámara."""
        self.set_control('white_balance_automatic', value)
