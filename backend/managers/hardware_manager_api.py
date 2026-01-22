# src/managers/hardware_manager_api.py
"""
Hardware Manager API - Refactored without PyQt dependencies
Manages serial communication with IMU and calibration system.
"""

import time
import threading
import logging
from typing import Optional, Dict, Any, Callable
from queue import Queue, Empty

from utils.serial_handler import SerialHandler
from utils.exceptions import HardwareError, SerialError

logger = logging.getLogger(__name__)


class SerialReaderThread(threading.Thread):
    """Thread for reading serial data without PyQt dependency"""

    def __init__(self, serial_handler: SerialHandler, callback: Callable[[str], None]):
        super().__init__(daemon=True)
        self.serial_handler = serial_handler
        self.callback = callback
        self._running = True

    def run(self):
        while self._running:
            try:
                data = self.serial_handler.read_data()
                if data:
                    self.callback(data)
                time.sleep(0.01)  # 100 Hz polling
            except SerialError as e:
                logger.error(f"Serial communication error: {e}")
                time.sleep(1.0) # Wait longer if there's a serial error
            except Exception as e:
                logger.error(f"Unexpected error in serial reader thread: {e}")
                time.sleep(0.1)

    def stop(self):
        self._running = False


class HardwareManagerAPI:
    """
    Manages hardware communication for the API server.
    Replaces PyQt signals with callbacks and queues for data flow.
    """

    def __init__(self):
        # Serial components
        self.serial_handler: Optional[SerialHandler] = None
        self.serial_thread: Optional[SerialReaderThread] = None

        # State
        self.is_connected = False
        self.is_calibrating = False
        self.connection_status = "disconnected"

        # Configuration
        self.default_port = '/dev/ttyUSB0'
        self.default_baudrate = 115200

        # IMU data buffer
        self.imu_data_queue: Queue = Queue(maxsize=100)
        self.last_imu_data: Dict[str, Any] = {
            'timestamp': 0,
            'yaw': 0.0,
            'pitch': 0.0,
            'roll': 0.0,
            'is_valid': False
        }
        self.imu_data_lock = threading.Lock()

        # Callbacks for events (can be set by external code)
        self.on_imu_data: Optional[Callable[[Dict], None]] = None
        self.on_calibration_progress: Optional[Callable[[str], None]] = None
        self.on_calibration_completed: Optional[Callable[[bool], None]] = None
        self.on_status_changed: Optional[Callable[[str], None]] = None

        # Calibration state
        self._calibration_samples: list = []
        self._calibration_target_samples = 30
        self._is_calibrated = False
        self._calibration_data: Optional[Dict] = None

        logger.info("HardwareManagerAPI initialized")

    def initialize(self, port: str = None, baudrate: int = None) -> bool:
        """
        Initialize hardware communication.

        Args:
            port: Serial port (uses default if None)
            baudrate: Baud rate (uses default if None)

        Returns:
            bool: True if initialization was successful
        """
        port = port or self.default_port
        baudrate = baudrate or self.default_baudrate

        try:
            success = self._init_serial_communication(port, baudrate)
            if success:
                logger.info("Hardware system initialized successfully")
                return True
            else:
                logger.error("Error initializing serial communication")
                return False

        except Exception as e:
            logger.error(f"Error initializing hardware: {e}")
            self._emit_status_changed(f"Error: {e}")
            return False

    def _init_serial_communication(self, port: str, baudrate: int) -> bool:
        """Initialize serial communication"""
        try:
            # Create serial handler
            self.serial_handler = SerialHandler(port, baudrate)

            # Create and start reader thread
            self.serial_thread = SerialReaderThread(
                self.serial_handler,
                self._handle_serial_data
            )
            self.serial_thread.start()

            # Update state
            self.is_connected = True
            self.connection_status = "connected"
            self._emit_status_changed("Connected")

            logger.info(f"Serial communication established: {port}@{baudrate}")
            return True

        except SerialError as e:
            logger.error(f"Serial error during initialization: {e}")
            self.serial_handler = None
            self.serial_thread = None
            self.is_connected = False
            self.connection_status = "error"
            self._emit_status_changed(f"Connection error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error initializing serial communication: {e}")
            self.serial_handler = None
            self.serial_thread = None
            self.is_connected = False
            self.connection_status = "error"
            self._emit_status_changed(f"Connection error: {e}")
            return False

    def _handle_serial_data(self, raw_data: str):
        """
        Process incoming serial data from the IMU.
        
        Parses the raw data, updates the internal state, and notifies listeners.
        Also handles data collection during calibration.

        Args:
            raw_data: The raw string received from the serial port.
        """
        try:
            imu_data = self._parse_imu_data(raw_data)

            if imu_data['is_valid']:
                with self.imu_data_lock:
                    self.last_imu_data = imu_data

                # Add to queue for streaming
                try:
                    self.imu_data_queue.put_nowait(imu_data)
                except:
                    pass  # Queue full, skip

                # Callback
                if self.on_imu_data:
                    self.on_imu_data(imu_data)

                # Handle calibration sample collection
                if self.is_calibrating:
                    self._collect_calibration_sample(imu_data)

        except Exception as e:
            logger.error(f"Error processing serial data: {e}")

    def _parse_imu_data(self, raw_data: str) -> Dict[str, Any]:
        """
        Parse a raw IMU data string into a structured dictionary.

        Expected format: "yaw,pitch,roll" (comma-separated floats).

        Args:
            raw_data: Raw string from serial port.

        Returns:
            Dict containing parsed 'yaw', 'pitch', 'roll', 'timestamp', 
            and 'is_valid' flag.
        """
        try:
            data = raw_data.strip()

            if not data:
                return {'is_valid': False}

            # Parse comma-separated format
            if ',' in data:
                parts = data.split(',')

                if len(parts) >= 3:
                    try:
                        yaw = float(parts[0])
                        pitch = float(parts[1])
                        roll = float(parts[2])

                        return {
                            'timestamp': self._get_current_timestamp(),
                            'yaw': yaw,
                            'pitch': pitch,
                            'roll': roll,
                            'is_valid': True,
                            'raw_data': raw_data
                        }
                    except ValueError:
                        pass

            # If parsing failed, return invalid
            return {
                'timestamp': self._get_current_timestamp(),
                'raw_data': raw_data,
                'is_valid': False
            }

        except Exception as e:
            logger.error(f"Error parsing IMU data: {e}")
            return {'is_valid': False, 'error': str(e)}

    def _get_current_timestamp(self) -> float:
        """Get current timestamp in milliseconds"""
        return time.time() * 1000

    # =========================================================================
    # Hardware Control
    # =========================================================================

    def send_command(self, command: str) -> bool:
        """
        Send a control command to the hardware via serial.

        Args:
            command: The command string to send (e.g., "ZERO", "PAUSE").

        Returns:
            bool: True if the command was sent successfully, False otherwise.
        """
        if not self.is_connected or not self.serial_handler:
            logger.warning("Attempted to send command while hardware not connected")
            return False

        try:
            self.serial_handler.send_data(command)
            logger.debug(f"Command sent: {command}")
            return True

        except SerialError as e:
            logger.error(f"Error sending command: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending command: {e}")
            return False


    def pause_imu(self) -> bool:
        """Pause IMU reading"""
        return self.send_command("PAUSE")

    def set_euler_mode(self) -> bool:
        """Set IMU to Euler mode"""
        return self.send_command("MODE_EULER")

    def set_vhit_mode(self) -> bool:
        """Set IMU to VHIT mode"""
        return self.send_command("MODE_VHIT")

    def zero_position(self) -> bool:
        """Set current position as zero"""
        return self.send_command("ZERO")

    # =========================================================================
    # LED Control
    # =========================================================================

    def turn_on_left_led(self) -> bool:
        """Turn on left LED"""
        return self.send_command("L_12_ON")

    def turn_off_left_led(self) -> bool:
        """Turn off left LED"""
        return self.send_command("L_12_OFF")

    def turn_on_right_led(self) -> bool:
        """Turn on right LED"""
        return self.send_command("L_14_ON")

    def turn_off_right_led(self) -> bool:
        """Turn off right LED"""
        return self.send_command("L_14_OFF")

    def turn_off_all_leds(self) -> bool:
        """Turn off all LEDs"""
        success1 = self.turn_off_left_led()
        success2 = self.turn_off_right_led()
        return success1 and success2

    # =========================================================================
    # Calibration System
    # =========================================================================

    def start_calibration(self) -> bool:
        """
        Start eye calibration process.

        Returns:
            bool: True if started successfully
        """
        if self.is_calibrating:
            logger.warning("Calibration already in progress")
            return False

        self.is_calibrating = True
        self._calibration_samples = []
        self._emit_calibration_progress("Calibration started")
        logger.info("Calibration started")
        return True

    def _collect_calibration_sample(self, imu_data: Dict):
        """Collect calibration sample"""
        self._calibration_samples.append({
            'yaw': imu_data['yaw'],
            'pitch': imu_data['pitch'],
            'roll': imu_data['roll'],
            'timestamp': imu_data['timestamp']
        })

        progress = len(self._calibration_samples) / self._calibration_target_samples * 100
        self._emit_calibration_progress(f"Collecting samples: {progress:.0f}%")

        if len(self._calibration_samples) >= self._calibration_target_samples:
            self._complete_calibration()

    def _complete_calibration(self):
        """Complete calibration and calculate offsets"""
        if not self._calibration_samples:
            self._emit_calibration_completed(False)
            return

        # Calculate average offsets
        yaw_avg = sum(s['yaw'] for s in self._calibration_samples) / len(self._calibration_samples)
        pitch_avg = sum(s['pitch'] for s in self._calibration_samples) / len(self._calibration_samples)
        roll_avg = sum(s['roll'] for s in self._calibration_samples) / len(self._calibration_samples)

        self._calibration_data = {
            'yaw_offset': yaw_avg,
            'pitch_offset': pitch_avg,
            'roll_offset': roll_avg,
            'sample_count': len(self._calibration_samples),
            'timestamp': self._get_current_timestamp()
        }

        self._is_calibrated = True
        self.is_calibrating = False
        self._calibration_samples = []

        self._emit_calibration_progress("Calibration completed")
        self._emit_calibration_completed(True)
        logger.info(f"Calibration completed: {self._calibration_data}")

    def finish_calibration(self) -> bool:
        """Manually finish calibration"""
        self.is_calibrating = False
        return True

    def is_calibrated(self) -> bool:
        """Check if system is calibrated"""
        return self._is_calibrated

    def get_calibration_data(self) -> Optional[Dict]:
        """Get calibration data"""
        return self._calibration_data

    # =========================================================================
    # Status Information
    # =========================================================================

    def get_connection_status(self) -> str:
        """Get connection status string"""
        return self.connection_status

    def get_latest_imu_data(self) -> Dict[str, Any]:
        """Get latest IMU data"""
        with self.imu_data_lock:
            return self.last_imu_data.copy()

    def get_hardware_info(self) -> Dict[str, Any]:
        """Get complete hardware information"""
        return {
            'is_connected': self.is_connected,
            'connection_status': self.connection_status,
            'is_calibrating': self.is_calibrating,
            'is_calibrated': self._is_calibrated,
            'port': self.default_port,
            'baudrate': self.default_baudrate,
            'last_data_timestamp': self.last_imu_data.get('timestamp', 0)
        }

    # =========================================================================
    # Configuration
    # =========================================================================

    def set_default_port(self, port: str):
        """Set default serial port"""
        self.default_port = port
        logger.info(f"Default port set: {port}")

    def set_default_baudrate(self, baudrate: int):
        """Set default baud rate"""
        self.default_baudrate = baudrate
        logger.info(f"Default baudrate set: {baudrate}")

    # =========================================================================
    # Event Emitters (replace PyQt signals)
    # =========================================================================

    def _emit_status_changed(self, status: str):
        """Emit status changed event"""
        if self.on_status_changed:
            self.on_status_changed(status)

    def _emit_calibration_progress(self, progress: str):
        """Emit calibration progress event"""
        if self.on_calibration_progress:
            self.on_calibration_progress(progress)

    def _emit_calibration_completed(self, success: bool):
        """Emit calibration completed event"""
        if self.on_calibration_completed:
            self.on_calibration_completed(success)

    # =========================================================================
    # Cleanup
    # =========================================================================

    def cleanup(self):
        """Clean up hardware resources"""
        try:
            # Turn off LEDs
            if self.is_connected:
                self.turn_off_all_leds()

            # Stop serial thread
            if self.serial_thread:
                self.serial_thread.stop()
                self.serial_thread.join(timeout=3.0)

            # Close serial connection
            if self.serial_handler:
                self.serial_handler.close()

            # Reset state
            self.is_connected = False
            self.is_calibrating = False
            self.connection_status = "disconnected"

            logger.info("HardwareManagerAPI cleaned up")

        except Exception as e:
            logger.error(f"Error during hardware cleanup: {e}")

