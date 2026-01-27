"""
Main Worker process for SIEV Python backend.
Connects to Rust orchestrator via TCP and handles video processing commands.
"""
import asyncio
import logging
import sys
import time
import cv2
import json
import traceback
import concurrent.futures
from typing import Optional, Dict, Any

from tcp_client import ReconnectingTcpClient, DEFAULT_PORT, DEFAULT_HOST
from protocol import Message, Command, MessageType
import dependencies
from managers.video_manager_api import VideoManagerAPI

# Configure logging with forced flush
class FlushingStreamHandler(logging.StreamHandler):
    def emit(self, record):
        super().emit(record)
        self.flush()

logging.basicConfig(
    level=logging.DEBUG,  # More verbose for debugging
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[FlushingStreamHandler(sys.stdout)]
)
logger = logging.getLogger("SIEV-Worker")

# Also capture warnings
logging.captureWarnings(True)

class SievWorker:
    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self.host = host
        self.port = port
        self.client = ReconnectingTcpClient(
            host=host, 
            port=port,
            on_connect=self._on_connect,
            on_disconnect=self._on_disconnect
        )
        self.video_manager: VideoManagerAPI = dependencies.get_video_manager()
        self._stop_event = asyncio.Event()
        self._data_transmitter_task: Optional[asyncio.Task] = None
        self._jpeg_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

    async def _on_connect(self):
        logger.info("Connected to Rust orchestrator")
        if self.video_manager.is_capturing and not self._data_transmitter_task:
            self._data_transmitter_task = asyncio.create_task(self._data_transmitter_loop())

    async def _on_disconnect(self):
        logger.warning("Disconnected from Rust orchestrator")

    async def start(self):
        """Start the worker and connect to Rust"""
        logger.info(f"Starting SIEV Worker, connecting to {self.host}:{self.port}...")
        
        try:
            self.video_manager.initialize()
        except Exception as e:
            logger.error(f"Early init failed: {e}")
        
        connection_task = asyncio.create_task(self.client.start())
        
        try:
            while not self._stop_event.is_set():
                if self.client.connected:
                    msg = await self.client.recv()
                    if msg:
                        await self._handle_message(msg)
                    else:
                        await asyncio.sleep(0.01)
                else:
                    await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            logger.info("Worker task cancelled")
        except Exception as e:
            logger.error(f"Fatal error in worker loop: {e}")
            traceback.print_exc()
        finally:
            await self.stop()
            connection_task.cancel()

    async def stop(self):
        """Stop the worker and cleanup resources"""
        logger.info("Stopping SIEV Worker...")
        self._stop_event.set()
        
        if self._data_transmitter_task:
            self._data_transmitter_task.cancel()
            try:
                await self._data_transmitter_task
            except asyncio.CancelledError:
                pass
        
        self.video_manager.cleanup()
        self._jpeg_executor.shutdown(wait=False)
        await self.client.stop()
        logger.info("SIEV Worker stopped")

    async def _handle_message(self, msg: Message):
        """Handle incoming messages from Rust"""
        if msg.msg_type == MessageType.CMD:
            cmd = Command.from_message(msg)
            if cmd:
                await self._process_command(cmd)
        elif msg.msg_type == MessageType.ERROR:
            logger.error(f"Error from Rust: {msg.payload.decode('utf-8')}")

    async def _process_command(self, cmd: Command):
        """Execute commands from Rust"""
        logger.info(f"Processing command: {cmd.cmd} with params: {cmd.params}")
        success = False
        data = None
        error = None

        try:
            if cmd.cmd == "start_capture":
                params = cmd.params
                
                if self.video_manager.is_capturing:
                    logger.info("Stopping existing capture before re-starting")
                    self.video_manager.stop_capture()
                
                # Use params if provided, else keep current
                cam_id = params.get("camera_id", self.video_manager.camera_id)
                logger.info(f"Initializing video manager with camera_id: {cam_id}")
                
                init_success = self.video_manager.initialize(
                    camera_id=cam_id,
                    width=params.get("width", 960),
                    height=params.get("height", 540),
                    fps=params.get("fps", 120)
                )
                
                if not init_success:
                    error = "Failed to initialize video manager"
                    logger.error(error)
                else:
                    success = self.video_manager.start_capture()
                    if success:
                        if not self._data_transmitter_task or self._data_transmitter_task.done():
                            self._data_transmitter_task = asyncio.create_task(self._data_transmitter_loop())
                        logger.info("Capture started and transmitter active")
                    else:
                        error = "Failed to start capture processes (check camera connection)"
                        logger.error(error)

            elif cmd.cmd == "stop_capture":
                self.video_manager.stop_capture()
                if self._data_transmitter_task:
                    self._data_transmitter_task.cancel()
                    self._data_transmitter_task = None
                success = True

            elif cmd.cmd == "set_config":
                params = cmd.params
                
                # Handle structured key/value pair from WsMessage::SetConfig
                if "key" in params and "value" in params:
                    key = params["key"]
                    value = params["value"]
                    
                    if key == "session_update" and isinstance(value, dict):
                        # Bulk update of multiple config parameters
                        # Filter to only pass valid arguments to update_config
                        valid_args = [
                            'brightness', 'contrast', 'threshold', 'erode', 
                            'nose_width', 'eye_height', 'use_yolo', 'show_debug'
                        ]
                        filtered_args = {k: v for k, v in value.items() if k in valid_args}
                        if filtered_args:
                            self.video_manager.update_config(**filtered_args)
                        success = True
                        
                    elif key == "pupil_mode":
                        # Specific method for pupil detection mode
                        self.video_manager.set_pupil_mode(value)
                        success = True
                        
                    elif key == "camera_setup" and isinstance(value, dict):
                        # Re-initialization parameters
                        valid_init_args = [
                            'camera_id', 'width', 'height', 'fps',
                            'brightness', 'contrast', 'threshold', 'erode',
                            'nose_width', 'eye_height', 'use_yolo', 'storage_path'
                        ]
                        filtered_init = {k: v for k, v in value.items() if k in valid_init_args}

                        if self.video_manager.is_capturing:
                            # Stop capture, reinitialize with new config, restart
                            logger.info("Stopping capture to apply new camera configuration...")
                            self.video_manager.stop_capture()
                            if self._data_transmitter_task:
                                self._data_transmitter_task.cancel()
                                self._data_transmitter_task = None

                            # Reinitialize with new config
                            self.video_manager.initialize(**filtered_init)

                            # Restart capture
                            if self.video_manager.start_capture():
                                if not self._data_transmitter_task or self._data_transmitter_task.done():
                                    self._data_transmitter_task = asyncio.create_task(self._data_transmitter_loop())
                                logger.info("Capture restarted with new configuration")
                            else:
                                logger.error("Failed to restart capture after config change")
                        else:
                            self.video_manager.initialize(**filtered_init)
                        success = True
                        
                    else:
                        # Standard configuration update
                        # Verify key is valid for update_config
                        valid_config_args = [
                            'brightness', 'contrast', 'threshold', 'erode', 
                            'nose_width', 'eye_height', 'use_yolo', 'show_debug'
                        ]
                        if key in valid_config_args:
                            self.video_manager.update_config(**{key: value})
                        else:
                            logger.warning(f"Ignored unknown config key in set_config: {key}")
                        success = True
                        
                else:
                    # Handle direct flat parameters (legacy or bulk)
                    config_to_update = params
                    valid_config_args = [
                        'brightness', 'contrast', 'threshold', 'erode', 
                        'nose_width', 'eye_height', 'use_yolo', 'show_debug'
                    ]
                    # Filter keys
                    filtered_config = {k: v for k, v in config_to_update.items() if k in valid_config_args}
                    
                    if filtered_config:
                        self.video_manager.update_config(**filtered_config)
                    
                    success = True

            elif cmd.cmd == "set_pupil_config":
                self.video_manager.set_pupil_config(**cmd.params)
                success = True

            elif cmd.cmd == "list_cameras":
                cameras = self.video_manager.get_available_cameras()
                data = {"cameras": cameras}
                success = True

            elif cmd.cmd == "list_resolutions":
                camera_id = cmd.params.get("camera_id", 0)
                logger.info(f"Listing resolutions for camera_id: {camera_id}")
                resolutions = self.video_manager.get_available_resolutions(camera_id)
                logger.info(f"Found {len(resolutions)} resolutions: {resolutions[:5]}...")
                data = {"resolutions": resolutions, "camera_id": camera_id}
                success = True

            elif cmd.cmd == "send_command":
                # Handle generic commands like 'calibrate'
                if cmd.params.get('cmd') == 'calibrate':
                    # Rust handles calibration now, but we ack it
                    success = True
            
            else:
                logger.warning(f"Unknown command: {cmd.cmd}")
                error = f"Unknown command: {cmd.cmd}"

        except Exception as e:
            logger.error(f"Error executing command {cmd.cmd}: {e}")
            traceback.print_exc()
            error = str(e)

        # Send ACK
        await self.client.send_ack(success, data, error)

    def _encode_frame_sync(self, frame):
        """Encode frame to JPEG synchronously (runs in thread pool)"""
        # Fase 3.3: Reducir resolución para preview (50% = 4x menos datos)
        small_frame = cv2.resize(frame, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
        _, jpeg = cv2.imencode('.jpg', small_frame, [cv2.IMWRITE_JPEG_QUALITY, 40])
        return jpeg.tobytes()

    async def _encode_frame(self, frame):
        """Encode frame to JPEG in thread pool to avoid blocking event loop"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._jpeg_executor, self._encode_frame_sync, frame)

    async def _data_transmitter_loop(self):
        """Loop that sends frames and eye data to Rust when capturing"""
        logger.info("Starting data transmitter loop")

        # Limitar a 60fps para el frontend (no necesita más)
        target_fps = 60
        frame_interval = 1.0 / target_fps
        last_frame_sent = 0
        pending_encode: Optional[asyncio.Task] = None

        logger.info(f"Target transmission rate: {target_fps} FPS")

        try:
            while self.video_manager.is_capturing:
                if not self.client.connected:
                    await asyncio.sleep(0.1)
                    continue

                now = time.time()

                # 1. Send Eye Data
                eye_data_batch = self.video_manager.get_latest_eye_data_batch()
                for data in eye_data_batch:
                    left = None
                    if data.get('left_eye'):
                        left = {"x": data['left_eye'][0], "y": data['left_eye'][1], "radius": 5.0, "confidence": 1.0}

                    right = None
                    if data.get('right_eye'):
                        right = {"x": data['right_eye'][0], "y": data['right_eye'][1], "radius": 5.0, "confidence": 1.0}

                    ts_ms = int(data['timestamp'] * 1000)
                    await self.client.send_eye_data(ts_ms, left, right)

                # 2. Send Video Frame con encoding asíncrono y rate limiting
                # Iniciar encode si pasó suficiente tiempo y no hay encode pendiente
                if now - last_frame_sent >= frame_interval and pending_encode is None:
                    with self.video_manager.frame_lock:
                        frame = self.video_manager.latest_frame

                    if frame is not None:
                        # Hacer copia para evitar race conditions
                        frame_copy = frame.copy()
                        pending_encode = asyncio.create_task(self._encode_frame(frame_copy))

                # Verificar si el encode terminó y enviar
                if pending_encode is not None and pending_encode.done():
                    try:
                        jpeg_bytes = pending_encode.result()
                        await self.client.send_frame(jpeg_bytes)
                        last_frame_sent = time.time()
                    except Exception as e:
                        logger.error(f"Error encoding/sending frame: {e}")
                    finally:
                        pending_encode = None

                await asyncio.sleep(0.001)

        except asyncio.CancelledError:
            logger.info("Data transmitter loop cancelled")
            if pending_encode:
                pending_encode.cancel()
        except Exception as e:
            logger.error(f"Error in data transmitter loop: {e}")
        finally:
            logger.info("Data transmitter loop finished")

if __name__ == "__main__":
    import multiprocessing
    import signal
    multiprocessing.freeze_support()

    port = DEFAULT_PORT
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
            
    worker = SievWorker(port=port)
    
    # Handle signals for graceful shutdown
    def handle_signal(sig, frame):
        logger.info(f"Received signal {sig}, initiating shutdown...")
        asyncio.create_task(worker.stop())
        
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Register signal handlers if supported (not on Windows usually, but this is Linux)
    if sys.platform != 'win32':
        loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(worker.stop()))
        loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.create_task(worker.stop()))

    try:
        loop.run_until_complete(worker.start())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
