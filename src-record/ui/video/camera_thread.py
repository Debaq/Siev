import cv2
import os
from threading import Thread

class CameraThread(Thread):
    def __init__(self, output_path):
        super().__init__()
        self.output_path = output_path
        self.running = True
        
        # Crear directorio si no existe
        directory = os.path.dirname(output_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)

    def run(self):
        cap = None
        out = None
        try:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                print("Error: No se pudo abrir la cámara")
                return
                
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            out = cv2.VideoWriter(self.output_path, fourcc, 20.0, (640, 480))

            while self.running and cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    out.write(frame)
                else:
                    break
        except Exception as e:
            print(f"Error en grabación: {e}")
        finally:
            if cap is not None:
                cap.release()
            if out is not None:
                out.release()
            print(f"Grabación guardada en: {self.output_path}")

    def stop(self):
        self.running = False