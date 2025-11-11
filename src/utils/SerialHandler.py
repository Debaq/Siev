import serial
import threading

class SerialHandler:
    def __init__(self, port, baudrate):
        self.serial_port = serial.Serial(port, baudrate, timeout=1)
        self.lock = threading.Lock()  # Añadir un lock para evitar condiciones de carrera

    def send_data(self, data_string):
        with self.lock:
            self.serial_port.write((data_string + "\n").encode())

    def read_data(self):
        with self.lock:
            if self.serial_port.in_waiting > 0:
                return self.serial_port.readline().decode().strip()
            return None