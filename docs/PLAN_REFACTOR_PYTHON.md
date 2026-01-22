# Plan de Refactorización SIEV (Python)

Este documento detalla la estrategia de limpieza y profesionalización del código Python para el sistema de video-oculografía SIEV.

## ✅ Fase 1: Estandarización y Limpieza (Completada)
*   **Renombrado de archivos**: Se normalizaron las utilidades de `src/utils/` a `snake_case` (PEP 8).
    *   `camera_resolution_detector.py`
    *   `eye_data_processor.py`
    *   `serial_handler.py`
    *   `simple_tracker.py`
    *   `v4l2_camera.py`
*   **Limpieza de `v4l2_camera.py`**: Se eliminó ruido de consola y se centralizó el control de hardware en un método privado robusto.
*   **Organización de Imports**: Se reestructuraron las importaciones siguiendo el estándar PEP 8 en los archivos principales.

## ✅ Fase 2: Descomposición Arquitectónica (Completada)
*   **Modularización de Rutas**: Se eliminó el "God Object" de `src/server.py`, dividiendo los endpoints en `src/routes/`:
    *   `patients.py`: Gestión de base de datos.
    *   `video.py`: Control de captura y streaming.
    *   `hardware.py`: Comunicación con IMU y LEDs.
*   **Extracción de Modelos**: Los esquemas de Pydantic se centralizaron en `src/models/api_schemas.py`.
*   **Inyección de Dependencias**: Se creó `src/dependencies.py` para gestionar las instancias globales de los Managers de forma segura y evitar importaciones circulares.
*   **Servidor Minimalista**: `src/server.py` ahora solo actúa como orquestador y punto de entrada.

## ✅ Fase 3: Robustez y Manejo de Errores (Completada)
*   **Exception Handlers**: Se implementaron decoradores de FastAPI y excepciones personalizadas (`SievError`, `HardwareError`) para capturar errores de hardware y devolver JSON claros.
*   **Validación de Hardware**: Se mejoró el manejo de errores en `SerialHandler` y `HardwareManagerAPI`, incluyendo reintentos de conexión de cámara en `VideoProcesses`.
*   **Logging Profesional**: Se reemplazaron los `print()` por el módulo `logging` de Python en todo el proyecto, con una configuración centralizada en `server.py`.

## ✅ Fase 4: Consolidación de Modelos y Deuda Técnica (Completada)
*   **Unificación de Datos**: Sincronizados los modelos de base de datos (SQLAlchemy) con los de la API (Pydantic) usando `from_attributes=True` y eliminando métodos `to_dict` manuales.
*   **Eliminación de Legacy**: Se eliminaron los archivos obsoletos en `legacy/` (SievManager, DetectorNistagmo, WindowsCamera, etc.), conservando `vng_pdf_generator.py` para futura migración.
*   **Documentación Inline**: Se añadieron y mejoraron los Docstrings en `src/managers/` siguiendo el estilo Google.

---
*Última actualización: 21 de enero de 2026*
