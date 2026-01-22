import json
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Get the project root directory (parent of src/)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_PATH = os.path.join(_PROJECT_ROOT, "data", "siev_config.json")

DEFAULT_CONFIG = {
    "clinic": {
        "name": "Centro de Diagnóstico VNG",
        "doctor_name": "",
        "logo_path": ""
    },
    "video": {
        "camera_id": 2,
        "resolution_width": 640,
        "resolution_height": 480,
        "fps": 60,
        "exposure": -5,
        "gain": 0,
        "contrast": 50,
        "brightness": -21,
        "flip_horizontal": False,
        "flip_vertical": False,
        "display_size": "640x480"
    },
    "processing": {
        "algorithm": "yolo", # yolo, hough, threshold
        "threshold": 40,
        "min_pupil_size": 10,
        "max_pupil_size": 100,
        "roi_enabled": True
    },
    "pupil_detection": {
        "mode": "hybrid",  # legacy, fast, hybrid
        # Fast detector params
        "search_window_multiplier": 3.0,
        "dark_threshold_percent": 20,
        "starburst_rays": 16,
        "starburst_min_gradient": 30,
        "fallback_threshold": 5,
        # Legacy detector params
        "legacy_blur_enabled": True,
        "legacy_blur_kernel": 5,
        "legacy_clahe_enabled": True,
        "legacy_clahe_clip_limit": 2.0,
        "legacy_clahe_grid_size": 8,
        "legacy_morph_enabled": True,
        "legacy_morph_close_iterations": 1,
        "legacy_morph_dilate_iterations": 1
    },
    "calibration": {
        "pattern_type": "5_points", # 3_points, 5_points, 9_points
        "horizontal_angle": 30, # degrees
        "vertical_angle": 20, # degrees
        "point_duration": 2.0 # seconds per point
    },
    "hardware": {
        "serial_port": "/dev/ttyUSB0",
        "baudrate": 115200,
        "stimulus_screen": 1 # Screen ID for visual stimulus
    },
    "reference_values": {
        "saccade_latency_max": 250, # ms
        "saccade_velocity_min": 200, # deg/s
        "smooth_pursuit_gain_min": 0.8
    }
}

class ConfigStore:
    def __init__(self):
        self.config = DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, 'r') as f:
                    saved = json.load(f)
                    self._merge_config(self.config, saved)
            except Exception as e:
                print(f"Error loading config: {e}")

    def _merge_config(self, default: Dict, saved: Dict):
        """Recursively update config without losing default keys"""
        for key, value in saved.items():
            if key in default and isinstance(default[key], dict) and isinstance(value, dict):
                self._merge_config(default[key], value)
            else:
                default[key] = value

    def save(self):
        try:
            os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
            with open(CONFIG_PATH, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving config: {e}")

    def get(self) -> Dict[str, Any]:
        return self.config

    def update(self, new_config: Dict[str, Any]):
        self._merge_config(self.config, new_config)
        self.save()
        return self.config

    def get_section(self, section: str) -> Dict[str, Any]:
        return self.config.get(section, {})

config_store = ConfigStore()
