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
from typing import Optional, Dict, Any

from tcp_client import ReconnectingTcpClient
from protocol import Message, Command, MessageType
import dependencies
from managers.video_manager_api import VideoManagerAPI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("SIEV-Worker")

class SievWorker:
    def __init__(self, host: str = "127.0.0.1", port: int = 9999):
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

    async def _on_connect(self):
        logger.info("Connected to Rust orchestrator")
        # Start the data transmitter task if capture is already running
        if self.video_manager.is_capturing and not self._data_transmitter_task:
            self._data_transmitter_task = asyncio.create_task(self._data_transmitter_loop())

    async def _on_disconnect(self):
        logger.warning("Disconnected from Rust orchestrator")
        # We don't stop the transmitter task here, it will wait for reconnection

    async def start(self):
        """Start the worker and connect to Rust"""
        logger.info(f"Starting SIEV Worker, connecting to {self.host}:{self.port}...")
        
        # Initialize video manager with defaults
        self.video_manager.initialize()
        
        # Start connection loop in background
        connection_task = asyncio.create_task(self.client.start())
        
        # Main message processing loop
        try:
            while not self._stop_event.is_set():
                if self.client.connected:
                    msg = await self.client.recv()
                    if msg:
                        await self._handle_message(msg)
                    else:
                        await asyncio.sleep(0.1)
                else:
                    await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            logger.info("Worker task cancelled")
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
        await self.client.stop()
        logger.info("SIEV Worker stopped")

    async def _handle_message(self, msg: Message):
        """Handle incoming messages from Rust"""
        if msg.msg_type == MessageType.HEARTBEAT:
            # Protocol handles heartbeat? Usually it's bidirectional.
            # For now, we just ignore it or could reply.
            pass
        elif msg.msg_type == MessageType.CMD:
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
                
                # If already capturing, stop first to re-initialize cleanly
                if self.video_manager.is_capturing:
                    logger.info("Stopping existing capture before re-starting")
                    self.video_manager.stop_capture()
                
                # (Re)Initialize with params provided
                logger.info(f"Initializing video manager with camera_id: {params.get('camera_id')}")
                init_success = self.video_manager.initialize(
                    camera_id=params.get("camera_id", self.video_manager.camera_id),
                    width=params.get("width", self.video_manager.cap_width),
                    height=params.get("height", self.video_manager.cap_height),
                    fps=params.get("fps", self.video_manager.cap_fps)
                )
                
                if not init_success:
                    error = "Failed to initialize video manager"
                    logger.error(error)
                else:
                    success = self.video_manager.start_capture()
                    if success:
                        # Start transmission task if not running
                        if not self._data_transmitter_task or self._data_transmitter_task.done():
                            self._data_transmitter_task = asyncio.create_task(self._data_transmitter_loop())
                        logger.info("Capture task started and transmitter active")
                    else:
                        error = "Failed to start capture processes"
                        logger.error(error)

            elif cmd.cmd == "stop_capture":
                self.video_manager.stop_capture()
                if self._data_transmitter_task:
                    self._data_transmitter_task.cancel()
                    self._data_transmitter_task = None
                success = True

            elif cmd.cmd == "set_config":
                params = cmd.params
                self.video_manager.update_config(
                    brightness=params.get("brightness"),
                    contrast=params.get("contrast"),
                    threshold=params.get("threshold"),
                    erode=params.get("erode"),
                    nose_width=params.get("nose_width"),
                    eye_height=params.get("eye_height"),
                    use_yolo=params.get("use_yolo"),
                    show_debug=params.get("show_debug")
                )
                success = True

            elif cmd.cmd == "set_pupil_config":
                self.video_manager.set_pupil_config(**cmd.params)
                success = True

            elif cmd.cmd == "set_pupil_mode":
                mode = cmd.params.get("mode", "hybrid")
                self.video_manager.set_pupil_mode(mode)
                success = True

            elif cmd.cmd == "list_cameras":
                cameras = self.video_manager.get_available_cameras()
                data = {"cameras": cameras}
                success = True

            elif cmd.cmd == "get_resolutions":
                cam_id = cmd.params.get("camera_id", self.video_manager.camera_id)
                resolutions = self.video_manager.get_available_resolutions(cam_id)
                data = {"resolutions": resolutions}
                success = True
            
            elif cmd.cmd == "start_recording":
                success = self.video_manager.start_recording()
                if not success:
                    error = "Failed to start recording"
            
            elif cmd.cmd == "stop_recording":
                path = self.video_manager.stop_recording()
                if path:
                    data = {"path": path}
                    success = True
                else:
                    error = "Failed to stop recording or no file saved"

            else:
                logger.warning(f"Unknown command: {cmd.cmd}")
                error = f"Unknown command: {cmd.cmd}"

        except Exception as e:
            logger.error(f"Error executing command {cmd.cmd}: {e}", exc_info=True)
            error = str(e)

        # Send ACK
        await self.client.send_ack(success, data, error)

    async def _data_transmitter_loop(self):
        """Loop that sends frames and eye data to Rust when capturing"""
        logger.info("Starting data transmitter loop")
        
        last_frame_sent = 0
        frame_interval = 1.0 / 30.0  # Limit video stream to 30 FPS via TCP to save bandwidth
        
        try:
            while self.video_manager.is_capturing:
                if not self.client.connected:
                    await asyncio.sleep(0.1)
                    continue

                now = time.time()
                
                # 1. Send Eye Data (as fast as it comes, but limit buffer read)
                eye_data_batch = self.video_manager.get_latest_eye_data_batch()
                for data in eye_data_batch:
                    # Map VideoManagerAPI data to Protocol EyeData
                    # VideoManagerAPI.latest_eye_data format:
                    # { 'timestamp': float, 'left_eye': [x, y], 'right_eye': [x, y], ... }
                    
                    left = None
                    if data.get('left_eye'):
                        left = {"x": data['left_eye'][0], "y": data['left_eye'][1], "radius": 5.0, "confidence": 1.0}
                    
                    right = None
                    if data.get('right_eye'):
                        right = {"x": data['right_eye'][0], "y": data['right_eye'][1], "radius": 5.0, "confidence": 1.0}

                    # timestamp in ms for the protocol
                    ts_ms = int(data['timestamp'] * 1000)
                    await self.client.send_eye_data(ts_ms, left, right)

                # 2. Send Video Frame (rate limited)
                if now - last_frame_sent >= frame_interval:
                    with self.video_manager.frame_lock:
                        frame = self.video_manager.latest_frame
                    
                    if frame is not None:
                        try:
                            # Convert RGB (internal) to BGR for OpenCV encoding
                            bgr_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                            _, jpeg = cv2.imencode('.jpg', bgr_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                            await self.client.send_frame(jpeg.tobytes())
                            last_frame_sent = now
                        except Exception as e:
                            logger.error(f"Error encoding/sending frame: {e}")

                # Small sleep to prevent busy waiting
                await asyncio.sleep(0.001)
                
        except asyncio.CancelledError:
            logger.info("Data transmitter loop cancelled")
        except Exception as e:
            logger.error(f"Error in data transmitter loop: {e}", exc_info=True)
        finally:
            logger.info("Data transmitter loop finished")

if __name__ == "__main__":
    # Get port from env or args if needed
    port = 9999
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
            
    worker = SievWorker(port=port)
    try:
        asyncio.run(worker.start())
    except KeyboardInterrupt:
        pass
