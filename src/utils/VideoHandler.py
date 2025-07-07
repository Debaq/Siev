import cv2
import json


class VideoHandler:
    def __init__(self):
        self.blur_size = 0
        self.threshold_value = 0
        self.min_contour_area = 0
        self.frame_data = {}
        self.position_oclusor = None
        self.oclus = []
        self.frame_count = 0
        self.last_time = cv2.getTickCount()

    def set_params(self, blur_size, threshold_value, min_contour_area):
        self.blur_size = blur_size
        self.threshold_value = threshold_value
        self.min_contour_area = min_contour_area




    def process_frame(self, frame, frame_number):
        # Guardar el frame original antes de procesar
        original_frame = frame.copy()
        
       
        return original_frame


    def save_marks_to_json(self, video_file = "output.avi", json_file = "output.json"):
        data = {
            "video_file": video_file,
            "json_file": json_file,
            "marks": self.frame_data,
            "midline": 640  # Valor constante por ahora
        }

        folder = "record"
        json_file = f"{folder}/{json_file}"
        with open(json_file, 'w') as f:
            json.dump(data, f, indent=4)
