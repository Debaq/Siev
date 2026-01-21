# src/server.py
"""
SIEV FastAPI Server
Provides REST API and streaming endpoints for the video-oculography system.
"""

import asyncio
import time
import threading
import sys
import signal
import os
import subprocess
from typing import Optional, Dict, Any, List

def kill_port_owner(port):
    """Try to kill all processes currently using the specified port."""
    try:
        # Use lsof to find all PIDs
        cmd = ["lsof", "-t", f"-i:{port}"]
        output = subprocess.check_output(cmd).decode().strip()
        if output:
            pids = output.split('\n')
            print(f"⚠️ Port {port} is busy (PIDs: {', '.join(pids)}). Cleaning up...")
            for pid in pids:
                try:
                    os.kill(int(pid), signal.SIGKILL)
                except (ValueError, ProcessLookupError):
                    continue
            time.sleep(1.5) # Wait for OS to release the port
    except (subprocess.CalledProcessError):
        # No process found, ignore
        pass

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

# Import managers (refactored without PyQt)
from managers.video_manager_api import VideoManagerAPI
from managers.hardware_manager_api import HardwareManagerAPI

# Import Database Service
from database.service import db_service
from database.models import Patient, Session

# Import Config Store
from utils.config_store import config_store

# Global instances
video_manager: Optional[VideoManagerAPI] = None
hardware_manager: Optional[HardwareManagerAPI] = None


# ============================================================================ 
# Pydantic Models for Request/Response
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
    show_debug: bool = False  # Show threshold mask and ROI overlay


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


class CommandRequest(BaseModel):
    command: str


class CalibrationConfig(BaseModel):
    samples: int = 30


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

# --- Patient Models ---

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
    created_at: str
    session_count: int

class SessionResponse(BaseModel):
    id: int
    patient_id: int
    date: str
    description: Optional[str]
    duration_seconds: int
    video_path: Optional[str]
    data_path: Optional[str]

# ============================================================================ 
# Application Lifecycle
# ============================================================================ 

startup_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global video_manager, hardware_manager

    print("SIEV Server starting...")

    # Initialize managers
    video_manager = VideoManagerAPI()
    hardware_manager = HardwareManagerAPI()
    
    # Load initial config
    cfg = config_store.get() 
    
    # Init video with saved config if possible, otherwise defaults
    try:
        video_manager.initialize(
            camera_id=cfg['video'].get('camera_id', 2),
            width=cfg['video'].get('resolution_width', 960),
            height=cfg['video'].get('resolution_height', 540),
            fps=cfg['video'].get('fps', 120),
            brightness=cfg['video'].get('brightness', -21),
            contrast=cfg['video'].get('contrast', 50),
            threshold=cfg['video'].get('threshold', [0, 0]),
            erode=cfg['video'].get('erode', [0, 0]),
            nose_width=cfg['video'].get('nose_width', 0.25),
            eye_height=cfg['video'].get('eye_height', 0.25),
            use_yolo=cfg['video'].get('use_yolo', True)
        )
    except Exception as e:
        print(f"Error applying saved video config: {e}")
        video_manager.initialize() # Fallback

    yield

    # Cleanup on shutdown
    print("SIEV Server shutting down...")
    if video_manager:
        video_manager.cleanup()
    if hardware_manager:
        hardware_manager.cleanup()


# ============================================================================ 
# FastAPI Application
# ============================================================================ 

app = FastAPI(
    title="SIEV API",
    description="Video-oculography system API for eye tracking and analysis",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================ 
# Global Configuration Endpoints
# ============================================================================ 

@app.get("/config")
async def get_config():
    """Get full system configuration"""
    return config_store.get()

@app.post("/config")
async def update_config(config: Dict[str, Any]):
    """Update system configuration"""
    new_config = config_store.update(config)
    
    # Apply changes dynamically where possible
    if 'video' in config and video_manager:
        vcfg = config['video']
        # If camera ID changed, we might need full re-init (not implemented dynamically for safety)
        # But we can update brightness/contrast
        video_manager.update_config(
            brightness=vcfg.get('brightness'),
            contrast=vcfg.get('contrast')
        )
        
    return new_config

# ============================================================================ 
# Database Endpoints (Patients)
# ============================================================================ 

# Helper to get DB session
def get_db():
    db = next(db_service.get_db())
    try:
        yield db
    finally:
        db.close()

@app.post("/patients", response_model=PatientResponse)
async def create_patient(patient: PatientCreate, db: DBSession = Depends(get_db)):
    """Create a new patient"""
    new_patient = db_service.create_patient(db, patient.model_dump())
    return new_patient.to_dict()

@app.get("/patients", response_model=List[PatientResponse])
async def get_patients(skip: int = 0, limit: int = 100, search: Optional[str] = None, db: DBSession = Depends(get_db)):
    """Get list of patients with optional search"""
    patients = db_service.get_patients(db, skip, limit, search)
    return [p.to_dict() for p in patients]

@app.get("/patients/{patient_id}", response_model=PatientResponse)
async def get_patient(patient_id: int, db: DBSession = Depends(get_db)):
    """Get a specific patient"""
    patient = db_service.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient.to_dict()

@app.put("/patients/{patient_id}", response_model=PatientResponse)
async def update_patient(patient_id: int, patient: PatientUpdate, db: DBSession = Depends(get_db)):
    """Update a patient"""
    updated = db_service.update_patient(db, patient_id, patient.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Patient not found")
    return updated.to_dict()

@app.delete("/patients/{patient_id}")
async def delete_patient(patient_id: int, db: DBSession = Depends(get_db)):
    """Delete a patient"""
    success = db_service.delete_patient(db, patient_id)
    if not success:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {"status": "deleted", "id": patient_id}

@app.get("/patients/{patient_id}/sessions", response_model=List[SessionResponse])
async def get_patient_sessions(patient_id: int, db: DBSession = Depends(get_db)):
    """Get all sessions for a patient"""
    sessions = db_service.get_patient_sessions(db, patient_id)
    return [s.to_dict() for s in sessions]

# ============================================================================ 
# Health & Status Endpoints
# ============================================================================ 

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check server health status"""
    return HealthResponse(
        status="ok",
        video_status=video_manager.get_status() if video_manager else "not_initialized",
        hardware_status=hardware_manager.get_connection_status() if hardware_manager else "not_initialized",
        uptime=time.time() - startup_time
    )


@app.get("/status", response_model=StatusResponse)
async def get_status():
    """Get current system status"""
    if not video_manager:
        raise HTTPException(status_code=503, detail="Video manager not initialized")

    status = video_manager.get_full_status()
    return StatusResponse(**status)


# ============================================================================ 
# Video Control Endpoints
# ============================================================================ 

@app.post("/start")
async def start_capture(config: Optional[VideoConfig] = None):
    """Start video capture"""
    if not video_manager:
        raise HTTPException(status_code=503, detail="Video manager not initialized")

    # If config provided, use it, else use stored config + defaults
    if config:
        print(f"[/start] Usando config del request: camera_id={config.camera_id}")
        success = video_manager.initialize(
            camera_id=config.camera_id,
            width=config.width,
            height=config.height,
            fps=config.fps,
            brightness=config.brightness,
            contrast=config.contrast,
            threshold=config.threshold,
            erode=config.erode,
            nose_width=config.nose_width,
            eye_height=config.eye_height,
            use_yolo=config.use_yolo
        )
    else:
        cfg = config_store.get()
        saved_camera_id = cfg['video'].get('camera_id', 2)
        print(f"[/start] Usando config guardada: camera_id={saved_camera_id}")
        success = video_manager.initialize(
            camera_id=saved_camera_id,
            width=cfg['video'].get('resolution_width', 960),
            height=cfg['video'].get('resolution_height', 540),
            fps=cfg['video'].get('fps', 120),
            brightness=cfg['video'].get('brightness', -21),
            contrast=cfg['video'].get('contrast', 50),
            threshold=cfg['video'].get('threshold', [0, 0]),
            erode=cfg['video'].get('erode', [0, 0]),
            nose_width=cfg['video'].get('nose_width', 0.25),
            eye_height=cfg['video'].get('eye_height', 0.25),
            use_yolo=cfg['video'].get('use_yolo', True)
        )

    if success:
        video_manager.start_capture()
        return {"status": "started", "message": "Video capture started"}
    else:
        raise HTTPException(status_code=500, detail="Failed to initialize video capture")


@app.post("/stop")
async def stop_capture():
    """Stop video capture"""
    if not video_manager:
        raise HTTPException(status_code=503, detail="Video manager not initialized")

    video_manager.stop_capture()
    return {"status": "stopped", "message": "Video capture stopped"}


@app.post("/recording/start")
async def start_recording():
    """Start video recording"""
    if not video_manager:
        raise HTTPException(status_code=503, detail="Video manager not initialized")

    success = video_manager.start_recording()
    if success:
        return {"status": "recording", "message": "Recording started"}
    else:
        raise HTTPException(status_code=500, detail="Failed to start recording")


@app.post("/recording/stop")
async def stop_recording():
    """Stop video recording"""
    if not video_manager:
        raise HTTPException(status_code=503, detail="Video manager not initialized")

    video_manager.stop_recording()
    return {"status": "stopped", "message": "Recording stopped"}


# ============================================================================ 
# Video Streaming Endpoint (MJPEG)
# ============================================================================ 

@app.get("/video_feed")
async def video_feed():
    """Stream video as MJPEG"""
    if not video_manager:
        raise HTTPException(status_code=503, detail="Video manager not initialized")

    if not video_manager.is_capturing:
        raise HTTPException(status_code=400, detail="Video capture not started")

    return StreamingResponse(
        video_manager.generate_mjpeg_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


# ============================================================================ 
# Eye Tracking Data Endpoint (Server-Sent Events)
# ============================================================================ 

@app.get("/stream/eye_data")
async def stream_eye_data():
    """Stream eye tracking data via Server-Sent Events"""
    if not video_manager:
        raise HTTPException(status_code=503, detail="Video manager not initialized")

    async def event_generator():
        import json
        while True:
            # Get all pending points in a batch
            batch = video_manager.get_latest_eye_data_batch()
            if batch:
                # Send the entire batch as one SSE event
                yield f"data: {json.dumps(batch)}\n\n"
            
            # Sleep a bit to prevent tight loop, but keep it responsive
            await asyncio.sleep(0.02) # ~50Hz batching

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )


# ============================================================================ 
# Hardware Control Endpoints
# ============================================================================ 

@app.post("/hardware/connect")
async def connect_hardware(config: Optional[HardwareConfig] = None):
    """Connect to IMU hardware"""
    if not hardware_manager:
        raise HTTPException(status_code=503, detail="Hardware manager not initialized")

    port = config.port if config else "/dev/ttyUSB0"
    baudrate = config.baudrate if config else 115200

    success = hardware_manager.initialize(port=port, baudrate=baudrate)
    if success:
        return {"status": "connected", "port": port}
    else:
        raise HTTPException(status_code=500, detail="Failed to connect to hardware")


@app.post("/hardware/disconnect")
async def disconnect_hardware():
    """Disconnect from IMU hardware"""
    if not hardware_manager:
        raise HTTPException(status_code=503, detail="Hardware manager not initialized")

    hardware_manager.cleanup()
    return {"status": "disconnected"}


@app.get("/hardware/status")
async def get_hardware_status():
    """Get hardware status"""
    if not hardware_manager:
        raise HTTPException(status_code=503, detail="Hardware manager not initialized")

    return hardware_manager.get_hardware_info()


@app.post("/hardware/command")
async def send_hardware_command(request: CommandRequest):
    """Send command to hardware"""
    if not hardware_manager:
        raise HTTPException(status_code=503, detail="Hardware manager not initialized")

    success = hardware_manager.send_command(request.command)
    if success:
        return {"status": "sent", "command": request.command}
    else:
        raise HTTPException(status_code=500, detail="Failed to send command")


@app.post("/calibrate")
async def start_calibration():
    """Start eye calibration"""
    if not hardware_manager:
        raise HTTPException(status_code=503, detail="Hardware manager not initialized")

    success = hardware_manager.start_calibration()
    if success:
        return {"status": "calibrating", "message": "Calibration started"}
    else:
        raise HTTPException(status_code=500, detail="Failed to start calibration")


# ============================================================================ 
# IMU Data Stream (Server-Sent Events)
# ============================================================================ 

@app.get("/stream/imu_data")
async def stream_imu_data():
    """Stream IMU data via Server-Sent Events"""
    if not hardware_manager:
        raise HTTPException(status_code=503, detail="Hardware manager not initialized")

    async def event_generator():
        while True:
            data = hardware_manager.get_latest_imu_data()
            if data:
                import json
                yield f"data: {json.dumps(data)}\n\n"
            await asyncio.sleep(0.01)  # 100 Hz for IMU data

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )


# ============================================================================ 
# LED Control Endpoints
# ============================================================================ 

@app.post("/hardware/led/{led_id}/on")
async def turn_on_led(led_id: str):
    """Turn on specific LED"""
    if not hardware_manager:
        raise HTTPException(status_code=503, detail="Hardware manager not initialized")

    if led_id == "left":
        success = hardware_manager.turn_on_left_led()
    elif led_id == "right":
        success = hardware_manager.turn_on_right_led()
    else:
        raise HTTPException(status_code=400, detail="Invalid LED ID. Use 'left' or 'right'")

    if success:
        return {"status": "on", "led": led_id}
    else:
        raise HTTPException(status_code=500, detail="Failed to turn on LED")


@app.post("/hardware/led/{led_id}/off")
async def turn_off_led(led_id: str):
    """Turn off specific LED"""
    if not hardware_manager:
        raise HTTPException(status_code=503, detail="Hardware manager not initialized")

    if led_id == "left":
        success = hardware_manager.turn_off_left_led()
    elif led_id == "right":
        success = hardware_manager.turn_off_right_led()
    elif led_id == "all":
        success = hardware_manager.turn_off_all_leds()
    else:
        raise HTTPException(status_code=400, detail="Invalid LED ID. Use 'left', 'right', or 'all'")

    if success:
        return {"status": "off", "led": led_id}
    else:
        raise HTTPException(status_code=500, detail="Failed to turn off LED")


# ============================================================================ 
# Video Configuration Endpoints
# ============================================================================ 

@app.post("/video/config")
async def update_video_config(config: VideoConfig):
    """Update video configuration"""
    if not video_manager:
        raise HTTPException(status_code=503, detail="Video manager not initialized")

    video_manager.update_config(
        brightness=config.brightness,
        contrast=config.contrast,
        threshold=config.threshold,
        erode=config.erode,
        nose_width=config.nose_width,
        eye_height=config.eye_height,
        use_yolo=config.use_yolo,
        show_debug=config.show_debug
    )
    return {"status": "updated", "config": config.model_dump()}


@app.get("/video/resolutions")
async def get_available_resolutions(camera_id: Optional[int] = None):
    """Get available camera resolutions for a specific camera"""
    if not video_manager:
        raise HTTPException(status_code=503, detail="Video manager not initialized")

    resolutions = video_manager.get_available_resolutions(camera_id)
    return {"resolutions": resolutions}


@app.post("/video/resolution")
async def change_resolution(width: int, height: int, fps: int = 60):
    """Change camera resolution (requires restart of capture)"""
    if not video_manager:
        raise HTTPException(status_code=503, detail="Video manager not initialized")

    was_capturing = video_manager.is_capturing

    # Stop current capture if running
    if was_capturing:
        video_manager.stop_capture()

    # Get current config
    cfg = config_store.get()

    # Update resolution in config
    cfg['video']['resolution_width'] = width
    cfg['video']['resolution_height'] = height
    cfg['video']['fps'] = fps
    config_store.update(cfg)

    # Reinitialize with new resolution
    success = video_manager.initialize(
        camera_id=cfg['video'].get('camera_id', 2),
        width=width,
        height=height,
        fps=fps,
        brightness=cfg['video'].get('brightness', -21),
        contrast=cfg['video'].get('contrast', 50),
        threshold=cfg['video'].get('threshold', [0, 0]),
        erode=cfg['video'].get('erode', [0, 0]),
        nose_width=cfg['video'].get('nose_width', 0.25),
        eye_height=cfg['video'].get('eye_height', 0.25),
        use_yolo=cfg['video'].get('use_yolo', True)
    )

    # Restart capture if it was running
    if success and was_capturing:
        video_manager.start_capture()

    if success:
        return {"status": "updated", "resolution": f"{width}x{height}@{fps}"}
    else:
        raise HTTPException(status_code=500, detail="Failed to change resolution")


@app.get("/video/cameras")
async def get_available_cameras():
    """Get available cameras"""
    if not video_manager:
        raise HTTPException(status_code=503, detail="Video manager not initialized")

    cameras = video_manager.get_available_cameras()
    return {"cameras": cameras}


@app.post("/video/yolo")
async def toggle_yolo(enabled: bool = True):
    """Toggle YOLO eye detection"""
    if not video_manager:
        raise HTTPException(status_code=503, detail="Video manager not initialized")

    video_manager.toggle_yolo(enabled)
    return {"status": "updated", "yolo_enabled": enabled}


# ============================================================================
# Pupil Detection Configuration Endpoints
# ============================================================================

@app.post("/video/pupil/mode")
async def set_pupil_mode(mode: str):
    """
    Set pupil detection mode.

    Args:
        mode: "legacy", "fast", or "hybrid"
    """
    if not video_manager:
        raise HTTPException(status_code=503, detail="Video manager not initialized")

    valid_modes = ["legacy", "fast", "hybrid"]
    if mode not in valid_modes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode. Must be one of: {valid_modes}"
        )

    video_manager.set_pupil_mode(mode)

    # Also update config store
    cfg = config_store.get()
    if 'pupil_detection' not in cfg:
        cfg['pupil_detection'] = {}
    cfg['pupil_detection']['mode'] = mode
    config_store.update(cfg)

    return {"status": "updated", "pupil_mode": mode}


@app.post("/video/pupil/config")
async def update_pupil_config(config: PupilDetectionConfig):
    """Update pupil detection configuration"""
    if not video_manager:
        raise HTTPException(status_code=503, detail="Video manager not initialized")

    # Apply mode if provided
    if config.mode:
        valid_modes = ["legacy", "fast", "hybrid"]
        if config.mode not in valid_modes:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid mode. Must be one of: {valid_modes}"
            )
        video_manager.set_pupil_mode(config.mode)

    # Apply other config
    video_manager.set_pupil_config(
        # Fast detector params
        search_window_multiplier=config.search_window_multiplier,
        dark_threshold_percent=config.dark_threshold_percent,
        starburst_rays=config.starburst_rays,
        starburst_min_gradient=config.starburst_min_gradient,
        fallback_threshold=config.fallback_threshold,
        # Legacy detector params
        legacy_blur_enabled=config.legacy_blur_enabled,
        legacy_blur_kernel=config.legacy_blur_kernel,
        legacy_clahe_enabled=config.legacy_clahe_enabled,
        legacy_clahe_clip_limit=config.legacy_clahe_clip_limit,
        legacy_clahe_grid_size=config.legacy_clahe_grid_size,
        legacy_morph_enabled=config.legacy_morph_enabled,
        legacy_morph_close_iterations=config.legacy_morph_close_iterations,
        legacy_morph_dilate_iterations=config.legacy_morph_dilate_iterations
    )

    # Update config store
    cfg = config_store.get()
    if 'pupil_detection' not in cfg:
        cfg['pupil_detection'] = {}

    update_dict = config.model_dump(exclude_none=True)
    cfg['pupil_detection'].update(update_dict)
    config_store.update(cfg)

    return {"status": "updated", "config": update_dict}


@app.get("/video/pupil/config")
async def get_pupil_config():
    """Get current pupil detection configuration"""
    cfg = config_store.get()
    return cfg.get('pupil_detection', {
        "mode": "hybrid",
        "search_window_multiplier": 3.0,
        "dark_threshold_percent": 20,
        "starburst_rays": 16,
        "starburst_min_gradient": 30,
        "fallback_threshold": 5
    })


# ============================================================================
# Main Entry Point
# ============================================================================ 

async def serve_safe():
    import uvicorn
    
    # Configure server
    config = uvicorn.Config(
        "server:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=False, 
        workers=1
    )
    server = uvicorn.Server(config)
    
    # Disable uvicorn's default signal handlers so we can manage them
    config.install_signal_handlers = False
    
    loop = asyncio.get_running_loop()
    
    def handle_signal():
        print("\n🛑 Signal received. Initiating graceful shutdown...")
        server.should_exit = True
        
        # Setup force exit on next signal (double Ctrl+C)
        def force_exit():
            print("\n☠️  Force killing...")
            sys.exit(1)
            
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.remove_signal_handler(sig)
                loop.add_signal_handler(sig, force_exit)
            except NotImplementedError:
                # Windows fallback
                signal.signal(sig, lambda s, f: sys.exit(1))
    
    # Register initial handlers
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, handle_signal)
        except NotImplementedError:
             # Windows fallback
             signal.signal(sig, lambda s, f: handle_signal())

    await server.serve()

if __name__ == "__main__":
    # Clean up port 8000 before starting
    kill_port_owner(8000)
    
    try:
        asyncio.run(serve_safe())
    except KeyboardInterrupt:
        # Catch any interrupt that happens before/outside the loop
        sys.exit(0)
