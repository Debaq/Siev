import win32com.client

class WindowsCamera:
    def __init__(self):
        self.device = None
        self.capture_filter = None
        self.graph = None
        self.control = None

    @staticmethod
    def get_connected_cameras():
        """Obtiene una lista de todas las cámaras conectadas."""
        system_device_enum = win32com.client.Dispatch("SystemDeviceEnum")
        moniker_enum = system_device_enum.CreateClassEnumerator(
            "{860BB310-5D01-11D0-BD3B-00A0C911CE86}", 0)
        
        moniker_list = []
        if moniker_enum:
            moniker_enum.Reset()
            while True:
                moniker = moniker_enum.Next(1)
                if not moniker:
                    break
                moniker_list.append(moniker[0])
        
        cameras = []
        for moniker in moniker_list:
            name = moniker.GetDisplayName()
            cameras.append(name)
        return cameras

    def set_camera(self, device_index):
        """Configura la cámara activa."""
        self.device = self.get_connected_cameras()[device_index]

        # Create the filter graph manager
        self.graph = win32com.client.Dispatch("FilterGraph")
        # Add the capture filter for the selected camera
        capture_filter = self._create_capture_filter(self.device)
        self.graph.AddFilter(capture_filter, "Capture Filter")
        self.capture_filter = capture_filter

        # Get the control interface
        self.control = self.graph.QueryInterface("IAMVideoProcAmp")

    def _create_capture_filter(self, device_name):
        """Crea el filtro de captura para la cámara."""
        capture_filter = win32com.client.Dispatch("CaptureFilter")
        capture_filter.SetDevice(device_name)
        return capture_filter

    def set_control(self, control, value):
        """Ajusta un parámetro específico de la cámara."""
        if not self.control:
            raise ValueError("No camera device set. Use set_camera() first.")

        control_dict = {
            'brightness': 0,
            'contrast': 1,
            'hue': 2,
            'saturation': 3,
            'sharpness': 4,
            'gamma': 5,
            'color_enable': 6,
            'white_balance': 7,
            'backlight_compensation': 8,
            'gain': 9,
            'focus': 10,  # Focus control
            'white_balance_automatic': 11,
            'focus_automatic_continuous': 12,
        }

        if control in control_dict:
            self.control.Set(control_dict[control], value, 2)  # 2 means `VideoProcAmp_Flags_Manual`
        else:
            raise ValueError(f"Control {control} no soportado.")

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
        self.set_control('focus', value)

    def set_autofocus(self, value):
        """Ajusta el enfoque automático de la cámara."""
        self.set_control('focus_automatic_continuous', value)

    def set_white_balance_automatic(self, value):
        """Ajusta el balance de blancos automático de la cámara."""
        self.set_control('white_balance_automatic', value)
