def select_max_resolution(lista_resoluciones):
    if not lista_resoluciones:
        return None
    
    # Parsear formato "1920x1080@60" a tuplas (width, height, fps)
    resoluciones_parseadas = []
    for res in lista_resoluciones:
        partes = res.split('@')
        width, height = map(int, partes[0].split('x'))
        fps = int(partes[1])
        area = width * height
        resoluciones_parseadas.append((width, height, fps, area, res))
    
    # Filtrar las que tienen FPS > 100
    fps_altos = [r for r in resoluciones_parseadas if r[2] > 100]
    
    if fps_altos:
        # Encontrar el área máxima
        area_maxima = max(fps_altos, key=lambda x: x[3])[3]
        # Filtrar por área máxima
        mejores_area = [r for r in fps_altos if r[3] == area_maxima]
        # Si hay empate en área, tomar el de mayor FPS
        mejor = max(mejores_area, key=lambda x: x[2])
        return mejor[4]
    
    # Si no hay ninguna con FPS > 100, tomar la de mayor área
    mejor = max(resoluciones_parseadas, key=lambda x: x[3])
    return mejor[4]