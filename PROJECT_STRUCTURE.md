# 📂 Estructura Detallada del Proyecto SIEV

Este documento proporciona una visión exhaustiva de la arquitectura del Sistema Integrado de Evaluación Vestibular (SIEV), detallando sus componentes, flujos de datos y responsabilidades.

---

## 🏗️ Arquitectura General
El sistema utiliza una arquitectura de tres capas para separar la interfaz de usuario, la orquestación lógica y el procesamiento intensivo de datos.

1.  **Frontend (React + TypeScript)**: Interfaz de usuario de alta fidelidad y visualización en tiempo real.
2.  **Orquestador (Rust + Tauri)**: Núcleo del sistema, gestión de estado, base de datos, control de hardware y puente de comunicación.
3.  **Trabajador de Visión (Python Sidecar)**: Procesamiento de video de alto rendimiento y detección de pupila mediante IA.

---

## 1. 🖥️ Frontend (Interfaz de Usuario)
Ubicación: `frontend/src/`

La UI se comunica con el orquestador a través de comandos de Tauri e intercambia datos de tiempo real mediante WebSockets.

*   **`App.tsx`**: Orquestador principal de la UI, gestiona la navegación entre vistas (Niveles de usuario, Pacientes, Pruebas).
*   **`contexts/`**:
    *   `WebSocketContext.tsx`: Mantiene la conexión de datos de baja latencia para el streaming de video y datos de ojos.
    *   `SessionConfigContext.tsx`: Gestiona la configuración de la sesión de prueba actual.
*   **`hooks/`**:
    *   `useSettingsConfig.ts`: Hook para persistencia de ajustes globales en la base de datos.
    *   `useTauriHardware.ts`: Abstracción para interactuar con los comandos de hardware de Rust.
*   **`components/`**:
    *   `VideoFeed.tsx`: Renderiza el stream de video (JPEG sobre WS) y superpone las detecciones.
    *   `EyeDataPanel.tsx`: Visualización gráfica (nistagmus) utilizando los datos procesados.
    *   `ControlPanel.tsx`: Ajustes de cámara, iluminación y algoritmos de detección.
    *   `settings/`: Desglose modular de la configuración del sistema.

---

## 2. 🦀 Orquestador (Rust / Tauri Core)
Ubicación: `src-tauri/src/`

Actúa como el cerebro del sistema, coordinando el ciclo de vida del proceso Python y la persistencia de datos.

*   **`main.rs` & `lib.rs`**: Punto de entrada, definición del `AppState` y registro de comandos `invoke`.
*   **`bridge/`**: Comunicación con el trabajador Python.
    *   `tcp_server.rs`: Servidor de alto rendimiento para recibir video y datos de ojos.
    *   `python_bridge.rs`: Abstracción para enviar comandos (start/stop capture, set config) a Python.
    *   `protocol.rs`: Definición del protocolo binario de mensajería (framing).
*   **`database/`**: Capa de persistencia (SQLite + SQLx).
    *   `service.rs`: Gestión de pacientes, especialistas, sesiones y configuración.
    *   `models.rs`: Definiciones de esquemas y DTOs.
*   **`math/`**: Procesamiento de señales.
    *   `processor.rs`: Convierte coordenadas de pupila en grados y detecta nistagmus.
    *   `kalman.rs`: Filtros de suavizado para las señales oculares.
*   **`hardware/`**: Control de periféricos.
    *   `manager.rs`: Comunicación serial con las gafas (LEDs, sensores IMU) mediante el firmware.
*   **`storage/`**: Gestión de archivos de sesión.
    *   `bundle.rs`: Crea y gestiona la estructura de carpetas `.siev` para cada sesión.
    *   `recorder.rs`: Grabador asíncrono que persiste los datos procesados en archivos `.csv` o binarios.
*   **`websocket/`**: Servidor interno para comunicación UI <-> Backend.

---

## 3. 🐍 Trabajador de Visión (Python Sidecar)
Ubicación: `backend/`

Un proceso independiente que se ejecuta como un "sidecar" de Tauri para aprovechar las librerías de Computer Vision y Deep Learning.

*   **`worker.py`**: Bucle principal que gestiona la captura de cámara y la ejecución de detectores.
*   **`tcp_client.py`**: Cliente que envía los resultados al orquestador Rust.
*   **`protocol.py`**: Implementación Python del protocolo de mensajería (debe coincidir con `bridge/protocol.rs`).
*   **`utils/video/`**:
    *   `pupil_detectors.py`: Implementa múltiples algoritmos:
        *   `YoloDetector`: Inferencia con `siev_vng_r01.pt` para robustez ante párpados/pestañas.
        *   `HybridDetector`: Algoritmo tradicional optimizado para baja latencia.
    *   `video_processes.py`: Gestión de hilos de captura y pre-procesamiento de frames.
*   **`models/`**: Contiene los pesos de las redes neuronales (`.pt`).

---

## 🔌 Firmware y Hardware
Ubicación: `firmware/`

Código que reside en el hardware físico de las gafas de evaluación.

*   **`esp8266_siev/`**: Implementación principal en ESP8266.
    *   `esp8266_siev_protocol.md`: Definición de comandos seriales (ej: `L1` encender LED IR izquierdo).

---

## 🔄 Flujo de Datos Típico (Telemetría de Ojo)
1.  **Python**: Captura frame -> Detecta pupila -> Empaqueta en frame TCP.
2.  **Rust (Bridge)**: Recibe frame TCP -> Desempaqueta.
3.  **Rust (Math)**: Pasa coordenadas por Filtro de Kalman -> Calcula grados.
4.  **Rust (Recorder)**: Si se está grabando, guarda el dato en disco.
5.  **Rust (WS)**: Envía datos procesados y frame JPEG a la UI.
6.  **Frontend**: Actualiza gráficas y canvas de video.

---

## 🛠️ Herramientas y Scripts
*   **`dev.sh`**: Script para iniciar el entorno de desarrollo (frontend + tauri).
*   **`scripts/build_sidecar.py`**: Compila el proceso Python en un ejecutable para distribución.
*   **`sidecar.spec`**: Configuración de PyInstaller para el empaquetado del trabajador.