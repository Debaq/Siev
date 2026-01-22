from typing import Optional
from managers.video_manager_api import VideoManagerAPI

# Global instances to be shared across routers
video_manager: Optional[VideoManagerAPI] = None

def get_video_manager() -> VideoManagerAPI:
    global video_manager
    if video_manager is None:
        video_manager = VideoManagerAPI()
    return video_manager