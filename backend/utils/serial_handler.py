import serial
import threading
import logging
from .exceptions import SerialError

logger = logging.getLogger(__name__)

class SerialHandler:
    def __init__(self, port, baudrate):
        try:
            self.serial_port = serial.Serial(port, baudrate, timeout=1)
            self.lock = threading.Lock()  # Añadir un lock para evitar condiciones de carrera
            logger.info(f"Serial port {port} opened at {baudrate} baud")
        except serial.SerialException as e:
            logger.error(f"Failed to open serial port {port}: {e}")
            raise SerialError(f"Could not open serial port {port}", detail=str(e))

    def send_data(self, data_string):
        try:
            with self.lock:
                self.serial_port.write((data_string + "\n").encode())
        except Exception as e:
            logger.error(f"Error sending data to serial port: {e}")
            raise SerialError("Failed to send data to hardware", detail=str(e))

    def read_data(self):
        try:
            with self.lock:
                if self.serial_port.in_waiting > 0:
                    return self.serial_port.readline().decode().strip()
                return None
        except Exception as e:
            logger.error(f"Error reading data from serial port: {e}")
            raise SerialError("Failed to read data from hardware", detail=str(e))

    def close(self):
        try:
            if hasattr(self, 'serial_port') and self.serial_port.is_open:
                self.serial_port.close()
                logger.info("Serial port closed")
        except Exception as e:
            logger.error(f"Error closing serial port: {e}")