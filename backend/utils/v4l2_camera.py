"""
V4L2 Camera Utility
Provides a wrapper for v4l2-ctl to control camera parameters on Linux.
"""

import subprocess
import logging

logger = logging.getLogger(__name__)

class V4L2Camera:
    """Wrapper class for v4l2-ctl commands to manage camera hardware settings."""
    
    def __init__(self, device_path: str = None):
        """
        Initialize the camera utility.
        
        Args:
            device_path: Path to the video device (e.g., '/dev/video0')
        """
        self.device = device_path

    @staticmethod
    def get_connected_cameras():
        """
        Lists all connected V4L2 devices.
        
        Returns:
            list: List of tuples (camera_name, device_path)
        """
        try:
            result = subprocess.run(['v4l2-ctl', '--list-devices'], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE,
                                   text=True)
            if result.returncode != 0:
                return []
                
            devices = result.stdout.split('\n\n')
            cameras = []
            for device in devices:
                if device.strip():
                    lines = device.split('\n')
                    camera_name = lines[0].strip()
                    # Device path is usually the second line, indented
                    if len(lines) > 1:
                        device_path = lines[1].strip()
                        cameras.append((camera_name, device_path))
            return cameras
        except FileNotFoundError:
            logger.error("v4l2-ctl not found. Please install v4l-utils.")
            return []

    def set_camera(self, device_path: str, width: int = None, height: int = None):
        """
        Configures the active camera device.
        
        Args:
            device_path: Path to the video device
            width: Optional width to set
            height: Optional height to set
        """
        self.device = device_path
        if width and height:
            self.set_frame_size(width, height)

    def _run_v4l2_ctl(self, args: list) -> bool:
        """
        Internal helper to run v4l2-ctl with a set of arguments.
        """
        if not self.device:
            logger.error("No camera device set. Use set_camera() first.")
            return False
            
        command = ["v4l2-ctl", "--device={}".format(self.device)] + args
        try:
            result = subprocess.run(command, 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE, 
                                   text=True)
            if result.returncode != 0:
                logger.error(f"v4l2-ctl error: {result.stderr.strip()}")
                return False
            return True
        except Exception as e:
            logger.error(f"Failed to execute v4l2-ctl: {e}")
            return False

    def set_frame_size(self, width: int, height: int) -> bool:
        """Sets the camera capture resolution."""
        return self._run_v4l2_ctl(["--set-fmt-video=width={},height={}".format(width, height)])

    def set_control(self, control: str, value: int) -> bool:
        """Sets a specific camera control value."""
        return self._run_v4l2_ctl(["--set-ctrl={}={}".format(control, value)])

    # --- Convenience methods for common controls ---

    def set_brightness(self, value: int):
        self.set_control('brightness', value)

    def set_contrast(self, value: int):
        self.set_control('contrast', value)

    def set_saturation(self, value: int):
        self.set_control('saturation', value)

    def set_hue(self, value: int):
        self.set_control('hue', value)

    def set_gamma(self, value: int):
        self.set_control('gamma', value)

    def set_sharpness(self, value: int):
        self.set_control('sharpness', value)

    def set_backlight_compensation(self, value: int):
        self.set_control('backlight_compensation', value)

    def set_exposure_time_absolute(self, value: int):
        self.set_control('exposure_time_absolute', value)

    def set_focus(self, value: int):
        self.set_control('focus_absolute', value)

    def set_autofocus(self, value: bool):
        # Value should be 0 (off) or 1 (on)
        self.set_control('focus_automatic_continuous', 1 if value else 0)

    def set_white_balance_automatic(self, value: bool):
        self.set_control('white_balance_automatic', 1 if value else 0)