import asyncio
import os
import signal
import subprocess
import sys
import time
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import Dependencies (Only Video)
import dependencies
from models.api_schemas import HealthResponse
from utils.exceptions import SievError

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
from routes import video

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
    logger.info("SIEV Video Server starting...")

    # Initialize managers via dependencies
    video_manager = dependencies.get_video_manager()
    
    # Init video with default config (Rust will update it later via API if needed)
    try:
        video_manager.initialize()
    except Exception as e:
        logger.error(f"Error initializing video manager: {e}")

    yield

    # Cleanup on shutdown
    logger.info("SIEV Video Server shutting down...")
    video_manager.cleanup()

# ============================================================================ 
# FastAPI Application
# ============================================================================ 

app = FastAPI(
    title="SIEV Video API",
    description="Video processing engine for SIEV",
    version="2.0.0",
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

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "An unexpected error occurred", "detail": str(exc)},
    )

# Include Routers
app.include_router(video.router)

# ============================================================================ 
# Health Check
# ============================================================================ 

@app.get("/health", response_model=HealthResponse)
async def health_check():
    v_manager = dependencies.get_video_manager()
    return HealthResponse(
        status="ok",
        video_status=v_manager.get_status(),
        hardware_status="managed_by_rust", # Legacy compatibility
        uptime=time.time() - startup_time
    )

# ============================================================================ 
# Main Entry Point
# ============================================================================ 

async def serve_safe():

    import uvicorn

    

    # Use default logging config but ensure basicConfig is set for our app

    logging.basicConfig(

        level=logging.INFO,

        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',

        force=True # Force reconfiguration to override any previous settings

    )



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
