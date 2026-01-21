# src/managers/__init__.py

# API managers (FastAPI - no PyQt dependencies)
from .video_manager_api import VideoManagerAPI
from .hardware_manager_api import HardwareManagerAPI

__all__ = ['VideoManagerAPI', 'HardwareManagerAPI']
