import asyncio
import os
import signal
import subprocess
import sys
import threading
import time
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import Config Store & Dependencies
from utils.config_store import config_store
import dependencies
from models.api_schemas import HealthResponse
from utils.exceptions import SievError, HardwareError

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("SIEV-Server")

# Import Routers
from routes import patients, video, hardware

def kill_port_owner(port):
    """Try to kill all processes currently using the specified port."""
    try:
        cmd = ["lsof", "-t", f"-i:{port}"]
        output = subprocess.check_output(cmd).decode().strip()
        if output:
            pids = output.split('\n')
            logger.warning(f"Port {port} is busy (PIDs: {', '.join(pids)}). Cleaning up...")
            for pid in pids:
                try:
                    os.kill(int(pid), signal.SIGKILL)
                except (ValueError, ProcessLookupError):
                    continue
            time.sleep(1.5)
    except (subprocess.CalledProcessError):
        pass

startup_time = time.time()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("SIEV Server starting...")

    # Initialize managers via dependencies
    video_manager = dependencies.get_video_manager()
    hardware_manager = dependencies.get_hardware_manager()
    
    # Load initial config
    cfg = config_store.get() 
    
    # Init video with saved config
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
        logger.error(f"Error applying saved video config: {e}")
        video_manager.initialize()

    yield

    # Cleanup on shutdown
    logger.info("SIEV Server shutting down...")
    video_manager.cleanup()
    hardware_manager.cleanup()

# ============================================================================ 
# FastAPI Application
# ============================================================================ 

app = FastAPI(
    title="SIEV API",
    description="Video-oculography system API",
    version="1.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception Handlers
@app.exception_handler(SievError)
async def siev_exception_handler(request: Request, exc: SievError):
    logger.error(f"SIEV Error: {exc}")
    return JSONResponse(
        status_code=400,
        content={"message": str(exc), "type": exc.__class__.__name__},
    )

@app.exception_handler(HardwareError)
async def hardware_exception_handler(request: Request, exc: HardwareError):
    logger.error(f"Hardware Error: {exc} - Detail: {exc.detail}")
    return JSONResponse(
        status_code=503, # Service Unavailable for hardware issues
        content={
            "message": str(exc),
            "detail": exc.detail,
            "type": exc.__class__.__name__
        },
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "An unexpected error occurred", "detail": str(exc)},
    )

# Include Routers
app.include_router(patients.router)
app.include_router(video.router)
app.include_router(hardware.router)

# ============================================================================ 
# Global Configuration & Health
# ============================================================================ 

@app.get("/config")
async def get_config():
    return config_store.get()

@app.post("/config")
async def update_config(config: Dict[str, Any]):
    new_config = config_store.update(config)
    if 'video' in config:
        dependencies.get_video_manager().update_config(
            brightness=config['video'].get('brightness'),
            contrast=config['video'].get('contrast')
        )
    return new_config

@app.get("/health", response_model=HealthResponse)
async def health_check():
    v_manager = dependencies.get_video_manager()
    h_manager = dependencies.get_hardware_manager()
    return HealthResponse(
        status="ok",
        video_status=v_manager.get_status(),
        hardware_status=h_manager.get_connection_status(),
        uptime=time.time() - startup_time
    )

# ============================================================================ 
# Main Entry Point
# ============================================================================ 

async def serve_safe():
    import uvicorn
    # Set uvicorn logging to match ours or be quiet
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["access"]["fmt"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_config["formatters"]["default"]["fmt"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    config = uvicorn.Config(
        "server:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=False, 
        workers=1,
        log_level="info"
    )
    server = uvicorn.Server(config)
    config.install_signal_handlers = False
    loop = asyncio.get_running_loop()
    
    def handle_signal():
        logger.info("Signal received. Initiating graceful shutdown...")
        server.should_exit = True
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, handle_signal)
        except NotImplementedError:
             signal.signal(sig, lambda s, f: handle_signal())

    await server.serve()

if __name__ == "__main__":
    kill_port_owner(8000)
    try:
        asyncio.run(serve_safe())
    except KeyboardInterrupt:
        sys.exit(0)