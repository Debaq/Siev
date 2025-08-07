def validate_patient_name(name):
    """Valida nombre del paciente"""
    if not name or not name.strip():
        return False, "El nombre del paciente es obligatorio"
    
    if len(name.strip()) < 2:
        return False, "El nombre debe tener al menos 2 caracteres"
    
    return True, ""

def validate_ear_selection(ear_index):
    """Valida selección de oído"""
    if ear_index == 0:  # "Seleccionar..."
        return False, "Debe seleccionar el oído irrigado"
    
    return True, ""

def validate_temperature(temp_str):
    """Valida temperatura"""
    if not temp_str or not temp_str.strip():
        return False, "La temperatura es obligatoria"
    
    try:
        temp = float(temp_str)
        if temp < 30 or temp > 44:
            return False, "La temperatura parece estar fuera del rango normal (30-44°C)"
        return True, ""
    except ValueError:
        return False, "La temperatura debe ser un número válido"

def validate_all_fields(name, ear_index, temp_str):
    """Valida todos los campos"""
    # Validar nombre
    valid, message = validate_patient_name(name)
    if not valid:
        return False, message
    
    # Validar oído
    valid, message = validate_ear_selection(ear_index)
    if not valid:
        return False, message
    
    # Validar temperatura
    valid, message = validate_temperature(temp_str)
    if not valid:
        return False, message
    
    return True, ""