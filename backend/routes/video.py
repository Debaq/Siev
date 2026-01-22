import asyncio
import json
import time
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse

from models.api_schemas import VideoConfig, StatusResponse, PupilDetectionConfig
from dependencies import get_video_manager

router = APIRouter(tags=["Video"])

@router.get("/status", response_model=StatusResponse)
async def get_status(video_manager=Depends(get_video_manager)):
    """Get current system status"""
    status = video_manager.get_full_status()
    return StatusResponse(**status)

@router.post("/start")
async def start_capture(config: Optional[VideoConfig] = None, video_manager=Depends(get_video_manager)):
    """Start video capture"""
    if config:
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
        # Initialize with defaults if no config provided
        # Rust backend should eventually provide this via API call or CLI args
        success = video_manager.initialize()

    if success:
        video_manager.start_capture()
        return {"status": "started", "message": "Video capture started"}
    else:
        raise HTTPException(status_code=500, detail="Failed to initialize video capture")

@router.post("/stop")
async def stop_capture(video_manager=Depends(get_video_manager)):
    """Stop video capture"""
    video_manager.stop_capture()
    return {"status": "stopped", "message": "Video capture stopped"}

@router.post("/recording/start")
async def start_recording(video_manager=Depends(get_video_manager)):
    """Start video recording"""
    success = video_manager.start_recording()
    if success:
        return {"status": "recording", "message": "Recording started"}
    else:
        raise HTTPException(status_code=500, detail="Failed to start recording")

@router.post("/recording/stop")
async def stop_recording(video_manager=Depends(get_video_manager)):
    """Stop video recording"""
    video_manager.stop_recording()
    return {"status": "stopped", "message": "Recording stopped"}

@router.get("/video_feed")
async def video_feed(video_manager=Depends(get_video_manager)):
    """Stream video as MJPEG"""
    if not video_manager.is_capturing:
        raise HTTPException(status_code=400, detail="Video capture not started")

    return StreamingResponse(
        video_manager.generate_mjpeg_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@router.get("/stream/eye_data")
async def stream_eye_data(video_manager=Depends(get_video_manager)):
    """Stream eye tracking data via Server-Sent Events"""
    async def event_generator():
        while True:
            batch = video_manager.get_latest_eye_data_batch()
            if batch:
                yield f"data: {json.dumps(batch)}\n\n"
            await asyncio.sleep(0.02)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

@router.post("/video/reset_stream")
async def reset_stream(video_manager=Depends(get_video_manager)):
    """Force reset video stream - clears frame buffer to force fresh frames"""
    with video_manager.frame_lock:
        video_manager.latest_frame = None
    # Clear the frame buffer queue as well
    while not video_manager.frame_buffer.empty():
        try:
            video_manager.frame_buffer.get_nowait()
        except:
            break
    return {"status": "reset", "message": "Video stream reset"}


@router.post("/video/config")
async def update_video_config(config: VideoConfig, video_manager=Depends(get_video_manager)):
    """Update video configuration"""
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

@router.get("/video/resolutions")
async def get_available_resolutions(camera_id: Optional[int] = None, video_manager=Depends(get_video_manager)):
    """Get available camera resolutions"""
    resolutions = video_manager.get_available_resolutions(camera_id)
    return {"resolutions": resolutions}

@router.get("/video/cameras")
async def get_available_cameras(video_manager=Depends(get_video_manager)):
    """Get available cameras"""
    cameras = video_manager.get_available_cameras()
    return {"cameras": cameras}

@router.post("/video/pupil/mode")
async def set_pupil_mode(mode: str, video_manager=Depends(get_video_manager)):
    """Set pupil detection mode"""
    valid_modes = ["legacy", "fast", "hybrid"]
    if mode not in valid_modes:
        raise HTTPException(status_code=400, detail=f"Invalid mode. Must be one of: {valid_modes}")

    video_manager.set_pupil_mode(mode)
    return {"status": "updated", "pupil_mode": mode}


@router.post("/video/pupil/config")
async def set_pupil_config(config: PupilDetectionConfig, video_manager=Depends(get_video_manager)):
    """Update pupil detection configuration"""
    # Set mode if provided
    if config.mode:
        valid_modes = ["legacy", "fast", "hybrid"]
        if config.mode in valid_modes:
            video_manager.set_pupil_mode(config.mode)

    # Set all other parameters
    video_manager.set_pupil_config(
        search_window_multiplier=config.search_window_multiplier,
        dark_threshold_percent=config.dark_threshold_percent,
        starburst_rays=config.starburst_rays,
        starburst_min_gradient=config.starburst_min_gradient,
        fallback_threshold=config.fallback_threshold,
        legacy_blur_enabled=config.legacy_blur_enabled,
        legacy_blur_kernel=config.legacy_blur_kernel,
        legacy_clahe_enabled=config.legacy_clahe_enabled,
        legacy_clahe_clip_limit=config.legacy_clahe_clip_limit,
        legacy_clahe_grid_size=config.legacy_clahe_grid_size,
        legacy_morph_enabled=config.legacy_morph_enabled,
        legacy_morph_close_iterations=config.legacy_morph_close_iterations,
        legacy_morph_dilate_iterations=config.legacy_morph_dilate_iterations
    )

    return {"status": "updated", "config": config.model_dump(exclude_none=True)}