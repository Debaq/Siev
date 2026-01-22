from typing import Optional, List, Dict, Any
from pydantic import BaseModel

# ============================================================================ 
# Configuration Models
# ============================================================================ 

class VideoConfig(BaseModel):
    camera_id: int = 2
    width: int = 960
    height: int = 540
    fps: int = 120
    brightness: int = -21
    contrast: int = 50
    threshold: List[int] = [0, 0]
    erode: List[int] = [0, 0]
    nose_width: float = 0.25
    eye_height: float = 0.25
    use_yolo: bool = True
    show_debug: bool = False
    storage_path: Optional[str] = None


class PupilDetectionConfig(BaseModel):
    mode: Optional[str] = None  # "legacy", "fast", "hybrid"
    # Fast detector params
    search_window_multiplier: Optional[float] = None
    dark_threshold_percent: Optional[int] = None
    starburst_rays: Optional[int] = None
    starburst_min_gradient: Optional[int] = None
    fallback_threshold: Optional[int] = None
    # Legacy detector params
    legacy_blur_enabled: Optional[bool] = None
    legacy_blur_kernel: Optional[int] = None
    legacy_clahe_enabled: Optional[bool] = None
    legacy_clahe_clip_limit: Optional[float] = None
    legacy_clahe_grid_size: Optional[int] = None
    legacy_morph_enabled: Optional[bool] = None
    legacy_morph_close_iterations: Optional[int] = None
    legacy_morph_dilate_iterations: Optional[int] = None


class HardwareConfig(BaseModel):
    port: str = "/dev/ttyUSB0"
    baudrate: int = 115200


class CalibrationConfig(BaseModel):
    samples: int = 30


# ============================================================================ 
# Response Models
# ============================================================================ 

class HealthResponse(BaseModel):
    status: str
    video_status: str
    hardware_status: str
    uptime: float


class StatusResponse(BaseModel):
    is_capturing: bool
    is_recording: bool
    video_mode: str
    fps: float
    resolution: Optional[str]


class CommandRequest(BaseModel):
    command: str


# ============================================================================ 
# Patient & Session Models
# ============================================================================ 

class PatientBase(BaseModel):
    first_name: str
    last_name: str
    dni: Optional[str] = None
    birth_date: Optional[str] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None


class PatientCreate(PatientBase):
    pass


class PatientUpdate(PatientBase):
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class PatientResponse(PatientBase):
    id: int
    created_at: Any
    session_count: int

    class Config:
        from_attributes = True


class SessionResponse(BaseModel):
    id: int
    patient_id: int
    date: Any
    description: Optional[str]
    duration_seconds: int
    video_path: Optional[str]
    data_path: Optional[str]

    class Config:
        from_attributes = True
