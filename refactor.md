# GEMINI.md - Contexto del Proyecto SIEV (Migración a Tauri)

## 1. Visión del Proyecto
**SIEV** es un sistema de video-oculografía de alto rendimiento diseñado para correr en hardware de gama baja (sin GPU dedicada).
* **Objetivo Actual:** Migrar de una aplicación monolítica `PyQt6` a una arquitectura moderna **Tauri (Frontend) + Python Sidecar (Backend)**.
* **Meta Crítica:** Mantener el procesamiento de visión a **>110 FPS** en el backend (input de cámara a 210 FPS), mientras se ofrece una interfaz fluida y moderna en el frontend sin consumir recursos excesivos.
* **Distribución:** Generar ejecutables "Siguiente, Siguiente" (`.exe`) para clientes finales en Windows, sin requerir instalación manual de Python ni Linux.

## 2. Stack Tecnológico (La "Arquitectura Híbrida")

### Frontend (La Cáscara Ligera)
* **Framework:** Tauri v2 (Rust) - *Gestión de ventanas y ciclo de vida (Bajo consumo de RAM).*
* **UI:** React + Vite + TypeScript.
* **Estilos:** Tailwind CSS - *Para una UI moderna estilo Dashboard médico.*
* **Gráficos:** Recharts / Chart.js - *Visualización de datos de pupilas (Nistagmo) en tiempo real.*
* **Comunicación:** `fetch` HTTP para comandos y `<img src>` para stream de video MJPEG.

### Backend (El Motor Pesado)
* **Lenguaje:** Python 3.10+ (Empaquetado como ejecutable independiente "Sidecar").
* **Visión:** OpenCV (Headless) + **YOLO26-Nano** (NMS-Free para CPU).
* **API Local:** **FastAPI** + Uvicorn.
    * Reemplaza las señales de PyQt.
    * Expone endpoints: `/video_feed` (MJPEG), `/start`, `/stop`, `/calibrate`.
* **Hardware:** `pyserial` para comunicación con Arduino/ESP32 (Protocolo existente).

### DevOps & Build
* **Empaquetado Python:** PyInstaller (`--onefile` y `--noconsole`).
* **Empaquetado App:** Tauri Builder (incluye el binario de Python como `externalBin`).
* **CI/CD:** GitHub Actions (Compilación cruzada automática para generar `.exe` de Windows desde el repo).

## 3. Estado de los Archivos (Plan de Migración)

### ❌ A eliminar (Legacy PyQt)
Todo lo relacionado con la interfaz antigua será deprecado:
* `src/ui/*` (Todos los archivos .ui y clases de widgets Qt).
* `src/utils/graphing/triple_plot_widget.py` (Reemplazado por React).
* `src/utils/video/video_widget.py`.
* `requirements.txt` -> Eliminar `PyQt6`, `pyqtgraph`.

### ✅ A conservar (Core Logic)
Esta lógica es sagrada. Solo se refactoriza para desacoplarse de la GUI:
* `src/managers/*`: `hardware_manager.py`, `video_manager.py`.
* `src/utils/SimpleTracker.py`: Algoritmo de seguimiento de pupilas.
* `src/utils/SerialHandler.py`: Comunicación Serial.
* `src/utils/EyeDataProcessor.py`: Matemáticas.

### 🆕 A crear (Roadmap)
* `src/server.py`: Nuevo punto de entrada. Inicia FastAPI y orquesta los Managers.
* `src-tauri/`: Configuración de Rust/Tauri.
* `src-frontend/`: Código React.

## 4. Reglas de Desarrollo (Directrices para la IA)

1.  **Rendimiento Primero:** El backend de Python tiene prioridad de CPU absoluta. El frontend solo visualiza a 30 FPS para el humano. Nunca procesar imágenes en JavaScript.
2.  **Desacople Total:** Python no debe saber que existe una ventana. Python solo responde a peticiones HTTP y escribe en el puerto Serial.
3.  **Cero Bloqueos:** El servidor FastAPI debe correr en hilos separados (`async`) para no detener el bucle crítico de captura (`cv2.read`).
4.  **Sidecar Pattern:** Asumir siempre que Python correrá como un ejecutable compilado dentro de Tauri. Usar rutas relativas dinámicas (`sys._MEIPASS` en PyInstaller).
5.  **Estética:** La interfaz debe ser oscura, clínica y moderna.

## 5. Tareas Inmediatas

- [ ] **Fase 1: Backend API**
    - Crear `src/server.py` con FastAPI.
    - Adaptar `VideoManager` para que genere un stream MJPEG (yield bytes).
    - Probar endpoints sin interfaz gráfica.

- [ ] **Fase 2: Frontend Básico**
    - Inicializar proyecto Tauri + React.
    - Conectar `<img src="http://localhost:PUERTO/video_feed">`.
    - Botones de control simples.

- [ ] **Fase 3: Migración de Gráficas**
    - Convertir `GraphHandler.py` para emitir datos JSON.
    - Implementar gráficas de alto rendimiento en React.

- [ ] **Fase 4: Empaquetado**
    - Script de PyInstaller para Windows.
    - Configuración de Tauri Sidecar.