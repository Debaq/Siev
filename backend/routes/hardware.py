import asyncio
import json
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse

from models.api_schemas import HardwareConfig, CommandRequest
from dependencies import get_hardware_manager

router = APIRouter(tags=["Hardware"])

@router.post("/hardware/connect")
async def connect_hardware(config: Optional[HardwareConfig] = None, hardware_manager=Depends(get_hardware_manager)):
    """Connect to IMU hardware"""
    port = config.port if config else "/dev/ttyUSB0"
    baudrate = config.baudrate if config else 115200
    success = hardware_manager.initialize(port=port, baudrate=baudrate)
    if success:
        return {"status": "connected", "port": port}
    else:
        raise HTTPException(status_code=500, detail="Failed to connect to hardware")

@router.post("/hardware/disconnect")
async def disconnect_hardware(hardware_manager=Depends(get_hardware_manager)):
    """Disconnect from IMU hardware"""
    hardware_manager.cleanup()
    return {"status": "disconnected"}

@router.get("/hardware/status")
async def get_hardware_status(hardware_manager=Depends(get_hardware_manager)):
    """Get hardware status"""
    return hardware_manager.get_hardware_info()

@router.post("/hardware/command")
async def send_hardware_command(request: CommandRequest, hardware_manager=Depends(get_hardware_manager)):
    """Send command to hardware"""
    success = hardware_manager.send_command(request.command)
    if success:
        return {"status": "sent", "command": request.command}
    else:
        raise HTTPException(status_code=500, detail="Failed to send command")

@router.get("/stream/imu_data")
async def stream_imu_data(hardware_manager=Depends(get_hardware_manager)):
    """Stream IMU data via SSE"""
    async def event_generator():
        while True:
            data = hardware_manager.get_latest_imu_data()
            if data:
                yield f"data: {json.dumps(data)}\\n\n"
            await asyncio.sleep(0.01)
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.post("/hardware/led/{led_id}/on")
async def turn_on_led(led_id: str, hardware_manager=Depends(get_hardware_manager)):
    """Turn on specific LED"""
    if led_id == "left": success = hardware_manager.turn_on_left_led()
    elif led_id == "right": success = hardware_manager.turn_on_right_led()
    else: raise HTTPException(status_code=400, detail="Invalid LED ID")
    
    if success: return {"status": "on", "led": led_id}
    else: raise HTTPException(status_code=500, detail="Failed to turn on LED")

@router.post("/hardware/led/{led_id}/off")
async def turn_off_led(led_id: str, hardware_manager=Depends(get_hardware_manager)):
    """Turn off specific LED"""
    if led_id == "left": success = hardware_manager.turn_off_left_led()
    elif led_id == "right": success = hardware_manager.turn_off_right_led()
    elif led_id == "all": success = hardware_manager.turn_off_all_leds()
    else: raise HTTPException(status_code=400, detail="Invalid LED ID")
    
    if success: return {"status": "off", "led": led_id}
    else: raise HTTPException(status_code=500, detail="Failed to turn off LED")

@router.post("/calibrate")
async def start_calibration(hardware_manager=Depends(get_hardware_manager)):
    """Start eye calibration"""
    success = hardware_manager.start_calibration()
    if success:
        return {"status": "calibrating", "message": "Calibration started"}
    else:
        raise HTTPException(status_code=500, detail="Failed to start calibration")
