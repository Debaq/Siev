import re

class PatientController:
    def __init__(self, db):
        self.db = db

    def validate_patient_info(self, name, patient_id):
        if not name or not patient_id:
            return False
        
        # Validar que el nombre solo contenga letras y espacios
        if not re.match(r"^[a-zA-ZÀ-ÿ\s]+$", name.strip()):
            return False
        
        # Validar que el ID no esté vacío y tenga formato válido
        if not patient_id.strip():
            return False
            
        return True

    def save_patient_info(self, name, patient_id):
        if self.validate_patient_info(name, patient_id):
            try:
                self.db.insert_paciente(name.strip(), patient_id.strip())
                return True
            except Exception as e:
                print(f"Error guardando paciente: {e}")
                return False
        return False