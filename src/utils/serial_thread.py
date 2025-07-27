from PySide6.QtCore import QThread, Signal



class SerialReadThread(QThread):
    """Thread para lectura de datos seriales del IMU"""
    data_received = Signal(str)

    def __init__(self, serial_handler):
        super().__init__()
        self.serial_handler = serial_handler
        self._running = True

    def run(self):
        while self._running:
            try:
                data = self.serial_handler.read_data()
                if data:
                    self.data_received.emit(data)
                self.msleep(10)
            except Exception as e:
                print(f"Error en serial thread: {e}")

    def stop(self):
        self._running = False
        self.wait()
