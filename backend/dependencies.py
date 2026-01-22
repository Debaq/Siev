from typing import Optional
from managers.video_manager_api import VideoManagerAPI
from managers.hardware_manager_api import HardwareManagerAPI

# Global instances to be shared across routers
video_manager: Optional[VideoManagerAPI] = None
hardware_manager: Optional[HardwareManagerAPI] = None

def get_video_manager() -> VideoManagerAPI:
    global video_manager
    if video_manager is None:
        video_manager = VideoManagerAPI()
    return video_manager

def get_hardware_manager() -> HardwareManagerAPI:
    global hardware_manager
    if hardware_manager is None:
        hardware_manager = HardwareManagerAPI()
    return hardware_manager
