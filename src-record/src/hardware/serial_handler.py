import time
import serial
import serial.tools.list_ports

class SerialHandler:
    """Maneja la comunicación serial para el LED"""
    def __init__(self):
        self.serial_connection = None
        self.connect_to_arduino()
    
    def connect_to_arduino(self):
        """Busca y conecta al Arduino automáticamente"""
        try:
            ports = serial.tools.list_ports.comports()
            for port in ports:
                try:
                    # Intentar conectar a cada puerto
                    self.serial_connection = serial.Serial(port.device, 115200, timeout=1)
                    time.sleep(2)  # Esperar conexión
                    print(f"Conectado a {port.device}")
                    return True
                except:
                    continue
            print("No se encontró Arduino conectado")
            return False
        except Exception as e:
            print(f"Error al conectar serial: {e}")
            return False
    
    def send_data(self, command):
        """Envía comando al Arduino"""
        if self.serial_connection and self.serial_connection.is_open:
            try:
                self.serial_connection.write(f"{command}\n".encode())
                print(f"Comando enviado: {command}")
                return True
            except Exception as e:
                print(f"Error enviando comando: {e}")
                return False
        else:
            print(f"Serial no disponible - Comando: {command}")
            return False
    
    def disconnect(self):
        """Desconecta el puerto serial"""
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
    
    def is_connected(self):
        """Verifica si está conectado"""
        return self.serial_connection is not None and self.serial_connection.is_open