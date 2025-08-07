import serial
import threading

class SerialHandler:
    def __init__(self, port='COM3', baudrate=9600):
        self.ser = None
        try:
            self.ser = serial.Serial(port, baudrate, timeout=1)
            self.thread = threading.Thread(target=self.read_data)
            self.thread.daemon = True
            self.thread.start()
            print(f"Puerto serial {port} conectado correctamente")
        except Exception as e:
            print(f"No se pudo abrir el puerto serial: {e}")

    def read_data(self):
        if self.ser is None:
            return
        while True:
            try:
                if self.ser.in_waiting:
                    data = self.ser.readline().decode('utf-8').strip()
                    print("Datos recibidos:", data)
            except Exception as e:
                print(f"Error leyendo datos seriales: {e}")
                break

    def send_data(self, data):
        if self.ser is not None:
            try:
                self.ser.write(data.encode())
            except Exception as e:
                print(f"Error enviando datos: {e}")
        else:
            print("Puerto serial no disponible")

    def close(self):
        if self.ser is not None:
            self.ser.close()