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

*   **`App.tsx`**: Orquestador principal de la UI, gestiona la navegación entre vistas principales.
*   **`pages/`**:
    *   `CalibrationPage.tsx`: Interfaz dedicada para la calibración geométrica del sistema.
    *   `StimulusPlayerPage.tsx`: Reproductor de estímulos visuales (sacadas, seguimiento, OPK).
    *   `ExternalDisplayPage.tsx`: Vista simplificada para proyectar estímulos en un segundo monitor.
*   **`contexts/`**:
    *   `WebSocketContext.tsx`: Mantiene la conexión de datos de baja latencia para el streaming de video y datos de ojos.
    *   `SessionConfigContext.tsx`: Gestiona la configuración de la sesión de prueba actual.
*   **`hooks/`**:
    *   `useSettingsConfig.ts`: Hook para persistencia de ajustes globales y sincronización con el backend.
    *   `useTauriHardware.ts`: Abstracción para interactuar con los comandos de hardware de Rust.
    *   `useTauriDb.ts`: Interfaz para acceder a la base de datos SQLite desde el frontend.
*   **`components/`**:
    *   `VideoFeed.tsx`: Renderiza el stream de video (JPEG sobre WS) y superpone las detecciones. Incluye lógica de renderizado desacoplada del flujo de red para suavidad máxima.
    *   `EyeDataPanel.tsx`: Visualización gráfica en tiempo real de los movimientos oculares.
    *   `StimulusController.tsx`: Panel de control para lanzar y configurar pruebas visuales.
    *   `settings/`: Configuración modular dividida en:
        *   `general/`: Datos de la institución y almacenamiento.
        *   `vng/`: Parámetros de cámara, algoritmos, hardware y reportes.
        *   `stimulus/`: Configuración de monitor secundario y parámetros por defecto de estímulos.
    *   `stimulus/`: Implementación de los diversos estímulos visuales:
        *   `SaccadeStimulus.tsx`: Estímulos de sacadas (puntos aleatorios o fijos).
        *   `PursuitStimulus.tsx`: Seguimiento lento (movimiento sinusoidal o circular).
        *   `OPKStimulus.tsx`: Estímulo optocinético (barras en movimiento).
        *   `GazeStimulus.tsx`: Pruebas de mirada fija en diferentes posiciones.
        *   `CalibrationStimulus.tsx`: Puntos de referencia para la calibración del sistema.
        *   `Target.tsx`: Componente base reutilizable para los objetivos visuales (puntos, cruces, etc.).
    *   `reports/`: Generación y previsualización de informes clínicos.

---

## 2. 🦀 Orquestador (Rust / Tauri Core)
Ubicación: `src-tauri/src/`

Actúa como el cerebro del sistema, coordinando el ciclo de vida del proceso Python y la persistencia de datos.

*   **`main.rs` & `lib.rs`**: Punto de entrada, definición del `AppState` y registro de comandos `invoke`.
*   **`bridge/`**: Comunicación con el trabajador Python.
    *   `tcp_server.rs`: Servidor de alto rendimiento para recibir video y datos de ojos.
    *   `python_bridge.rs`: Orquestador del proceso sidecar y envío de comandos.
    *   `protocol.rs`: Definición del protocolo binario de mensajería (framing).
*   **`database/`**: Capa de persistencia (SQLite + SQLx).
    *   `service.rs`: Gestión CRUD de pacientes, especialistas, sesiones y configuración.
*   **`vng/`**: Lógica de dominio específica para Video-Oculografía.
    *   `metrics.rs`: Cálculo de parámetros clínicos (velocidad de fase lenta, latencia, etc.).
    *   `report.rs`: Generación de estructuras de datos para informes.
*   **`math/`**: Procesamiento de señales.
    *   `processor.rs`: Transformación de coordenadas a grados y filtros de nistagmus.
    *   `kalman.rs`: Filtros de suavizado de alta precisión.
*   **`hardware/`**: Control de periféricos.
    *   `manager.rs`: Comunicación serial con las gafas (LEDs, sensores IMU).
*   **`storage/`**: Gestión de archivos de sesión y exportación.
*   **`websocket/`**: Puente de comunicación en tiempo real UI <-> Backend.

---

## 3. 🐍 Trabajador de Visión (Python Sidecar)
Ubicación: `backend/`

Un proceso independiente optimizado para procesamiento de imagen en tiempo real.

*   **`worker.py`**: Punto de entrada que gestiona el bucle de comandos y la transmisión asíncrona de datos.
*   **`managers/video_manager_api.py`**: Capa de abstracción que controla los hilos de captura, grabación y actualización de parámetros en caliente.
*   **`tcp_client.py`**: Cliente de baja latencia para envío de binarios JPEG y telemetría.
*   **`utils/video/`**:
    *   `pupil_detectors.py`: Algoritmos `YoloDetector` (IA), `FastPupilDetector` (Starburst) e `HybridDetector`.
    *   `video_processes.py`: Gestión de procesos paralelos para captura de frames a alta velocidad (hasta 120 FPS).
*   **`utils/`**:
    *   `v4l2_camera.py`: Control de bajo nivel para parámetros de hardware de cámara en Linux.
    *   `camera_resolution_detector.py`: Escaneo automático de capacidades del hardware.
    *   `eye_data_processor.py`: Limpieza inicial de coordenadas antes del envío.
*   **`models/`**: Pesos de redes neuronales en formato `.pt` y `.onnx`.

---

## 🔌 Firmware y Hardware
Ubicación: `firmware/`

*   **`esp8266_siev/`**: Firmware para el control de LEDs IR, LEDs de fijación y sensores inerciales.
*   **`tes_tesis_arduino/`**: Prototipos y pruebas de sensores.

---

## 🔄 Flujo de Datos y Calidad
1.  **Captura**: Python captura a la resolución nativa de la cámara (ej. 960x540@120fps).
2.  **Transmisión de Video**: Los frames se comprimen en JPEG y se reescalan según los ajustes de **Optimización de Transmisión** configurados en la UI para balancear fluidez y nitidez.
3.  **Procesamiento**: Las coordenadas detectadas viajan por TCP a Rust, donde se filtran y se convierten en datos clínicos.
4.  **Visualización**: El frontend recibe el stream y lo dibuja en un `Canvas` optimizado, manteniendo un contador de FPS para diagnóstico.

---

## 🛠️ Herramientas y Documentación
*   **`docs/`**:
    *   `OPTIMIZACION_DETECCION_PUPILAS.md`: Guía de ajuste de algoritmos.
    *   `PERFORMANCE_ANALYSIS.md`: Análisis de latencia y uso de CPU/GPU.
*   **`scripts/`**: Automatización para compilación de sidecars y conversión de modelos.
*   **`dev.sh`**: Entorno de desarrollo unificado.
