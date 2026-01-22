# Plan de Migración: Arquitectura Unificada TCP

## Objetivo

Eliminar la doble fuente de verdad centralizando toda la comunicación en Rust (Tauri) como orquestador único, usando TCP localhost para comunicación multiplataforma.

## Arquitectura Actual vs Nueva

```
ACTUAL (Problemática)                    NUEVA (Unificada)
=====================                    =================

┌──────────┐                            ┌──────────┐
│ Frontend │                            │ Frontend │
└────┬─────┘                            └────┬─────┘
     │                                       │
     ├─── HTTP/SSE ───→ Python               │ WebSocket único
     │                                       │
     └─── Tauri IPC ──→ Rust            ┌────▼─────┐
                                        │   Rust   │ (Orquestador)
                                        └────┬─────┘
                                             │
                                             │ TCP localhost
                                             │
                                        ┌────▼─────┐
                                        │  Python  │ (Worker)
                                        └──────────┘
```

## Protocolo TCP

### Formato de Mensajes

Todos los mensajes usan un formato simple con header de longitud:

```
┌─────────────┬─────────────┬─────────────────────┐
│ Length (4B) │ Type (1B)   │ Payload (JSON/Bin)  │
└─────────────┴─────────────┴─────────────────────┘
```

### Tipos de Mensaje

| Type | Nombre | Dirección | Payload |
|------|--------|-----------|---------|
| 0x01 | CMD | Rust → Python | JSON comando |
| 0x02 | CMD_ACK | Python → Rust | JSON respuesta |
| 0x03 | EYE_DATA | Python → Rust | JSON datos ojos |
| 0x04 | VIDEO_FRAME | Python → Rust | JPEG binario |
| 0x05 | ERROR | Bidireccional | JSON error |
| 0x06 | HEARTBEAT | Bidireccional | Empty |

### Comandos (0x01)

```json
{"cmd": "start_capture", "params": {"camera_id": 0, "width": 640, "height": 480}}
{"cmd": "stop_capture", "params": {}}
{"cmd": "set_config", "params": {"brightness": 50, "contrast": 30}}
{"cmd": "list_cameras", "params": {}}
{"cmd": "set_pupil_config", "params": {"threshold": 30, "mode": "fast"}}
```

### Eye Data (0x03)

```json
{
  "timestamp": 1234567890,
  "left": {"x": 320.5, "y": 240.2, "radius": 15.3, "confidence": 0.95},
  "right": {"x": 318.2, "y": 241.1, "radius": 14.8, "confidence": 0.93}
}
```

---

## Fases de Implementación

### Fase 1: Infraestructura TCP en Rust

**Objetivo**: Crear el servidor TCP en Rust que será el punto de contacto con Python.

**Archivos a crear**:
```
src-tauri/src/
├── bridge/
│   ├── mod.rs
│   ├── tcp_server.rs      # Servidor TCP async
│   ├── protocol.rs        # Parseo de mensajes
│   └── python_bridge.rs   # API de alto nivel
```

**Tareas**:

- [X] Crear módulo `bridge/protocol.rs`
  - Definir enums para tipos de mensaje
  - Implementar serialización/deserialización
  - Manejar frames con length-prefix

- [X] Crear módulo `bridge/tcp_server.rs`
  - Servidor TCP async con tokio
  - Escuchar en `127.0.0.1:9999`
  - Manejar reconexiones automáticas
  - Buffer de mensajes entrantes

- [X] Crear módulo `bridge/python_bridge.rs`
  - API de alto nivel: `send_command()`, `on_eye_data()`, `on_frame()`
  - Gestión de estado de conexión
  - Cola de comandos pendientes

- [X] Integrar en `lib.rs`
  - Añadir PythonBridge al AppState
  - Exponer estado de conexión

**Dependencias Rust a añadir**:
```toml
[dependencies]
tokio = { version = "1", features = ["net", "io-util", "sync"] }
bytes = "1"
```

---

### Fase 2: Adaptar Python como Worker TCP

**Objetivo**: Convertir el backend Python de servidor HTTP a cliente TCP.

**Archivos a modificar/crear**:
```
backend/
├── tcp_client.py          # NUEVO: Cliente TCP
├── protocol.py            # NUEVO: Protocolo compartido
├── worker.py              # NUEVO: Loop principal
├── main.py                # MODIFICAR: Punto de entrada
└── utils/video/
    └── video_processes.py # MODIFICAR: Adaptar salida
```

**Tareas**:

- [X] Crear `backend/protocol.py`
  - Misma lógica de mensajes que Rust
  - Funciones: `pack_message()`, `unpack_message()`
  - Constantes de tipos de mensaje

- [X] Crear `backend/tcp_client.py`
  - Conexión TCP a `127.0.0.1:9999`
  - Reconexión automática con backoff
  - Async con asyncio
  - Métodos: `connect()`, `send()`, `recv()`, `close()`

- [X] Crear `backend/worker.py`
  - Loop principal que:
    1. Conecta al servidor Rust
    2. Espera comandos
    3. Procesa video cuando está activo
    4. Envía eye_data y frames

- [X] Modificar `video_processes.py`
  - Cambiar output de queue interna a callback
  - Callback envía datos vía TCP

- [X] Eliminar dependencias HTTP
  - Quitar FastAPI, uvicorn
  - Simplificar `requirements.txt`

**Nuevo flujo Python**:
```python
async def main():
    client = TcpClient("127.0.0.1", 9999)
    await client.connect()

    video_processor = None

    async for message in client.messages():
        if message.type == CMD:
            if message.cmd == "start_capture":
                video_processor = VideoProcessor(
                    on_frame=lambda f: client.send_frame(f),
                    on_eye_data=lambda d: client.send_eye_data(d)
                )
                video_processor.start()
            elif message.cmd == "stop_capture":
                video_processor.stop()
            # ...
```

---

### Fase 3: WebSocket en Rust para Frontend

**Objetivo**: Reemplazar HTTP+SSE+Tauri IPC con un WebSocket único.

**Archivos a crear/modificar**:
```
src-tauri/src/
├── websocket/
│   ├── mod.rs
│   ├── server.rs          # WebSocket server
│   └── messages.rs        # Mensajes Frontend<->Rust
```

**Tareas**:

- [X] Crear módulo `websocket/messages.rs`
  - Definir mensajes JSON para frontend
  - Tipos: Command, EyeData, VideoFrame, ImuData, Status

- [X] Crear módulo `websocket/server.rs`
  - WebSocket server en puerto dinámico
  - Broadcast de datos a todos los clientes
  - Recepción de comandos del frontend

- [X] Integrar flujos de datos
  - PythonBridge.on_eye_data → WebSocket broadcast
  - PythonBridge.on_frame → WebSocket broadcast (base64)
  - HardwareManager.on_imu → WebSocket broadcast
  - WebSocket.on_command → PythonBridge / HardwareManager

- [X] Exponer puerto WebSocket al frontend
  - Comando Tauri: `get_websocket_port()`

**Dependencias Rust a añadir**:
```toml
[dependencies]
tokio-tungstenite = "0.21"
futures-util = "0.3"
base64 = "0.21"
```

**Mensajes WebSocket (Frontend ↔ Rust)**:

```typescript
// Frontend → Rust
{type: "start_capture", camera_id: 0}
{type: "stop_capture"}
{type: "set_config", key: "brightness", value: 50}
{type: "connect_hardware", port: "/dev/ttyUSB0"}
{type: "send_led_command", cmd: "L_12_ON"}

// Rust → Frontend
{type: "eye_data", timestamp: 123, left: {...}, right: {...}}
{type: "video_frame", data: "base64..."}
{type: "imu_data", yaw: 1.2, pitch: 0.5, roll: 0.1}
{type: "status", python_connected: true, hardware_connected: true}
{type: "error", source: "python", message: "Camera not found"}
```

---

### Fase 4: Migrar Frontend

**Objetivo**: Simplificar el frontend para usar solo WebSocket.

**Archivos a modificar/eliminar**:
```
frontend/src/
├── hooks/
│   ├── useWebSocket.ts       # NUEVO: Hook único de conexión
│   ├── useBackend.ts         # ELIMINAR
│   ├── useSSE.ts             # ELIMINAR
│   └── useTauriHardware.ts   # SIMPLIFICAR (solo get_websocket_port)
├── components/
│   ├── VideoFeed.tsx         # MODIFICAR: Recibir frames por WS
│   └── EyeDataPanel.tsx      # MODIFICAR: Recibir datos por WS
```

**Tareas**:

- [X] Crear `hooks/useWebSocket.ts`
- [X] Modificar `VideoFeed.tsx`
  - Quitar fetch MJPEG
  - Usar videoFrame de useWebSocket
  - Renderizar con `<img src={`data:image/jpeg;base64,${frame}`} />`

- [X] Modificar `EyeDataPanel.tsx`
  - Quitar SSE
  - Usar eyeData de useWebSocket
  - Quitar llamada a `process_eye_data_batch` (Rust lo hace internamente)

- [X] Modificar `ControlPanel.tsx`
  - Cambiar fetch a websocket.send()

- [X] Eliminar código obsoleto
  - `useBackend.ts`
  - `useSSE.ts`
  - Referencias a `http://localhost:8000`

---

### Fase 5: Gestión de Proceso Python

**Objetivo**: Rust inicia y supervisa el proceso Python automáticamente.

**Tareas**:

- [X] Configurar Python como sidecar en Tauri
  ```json
  // tauri.conf.json
  {
    "bundle": {
      "externalBin": ["binaries/python-worker"]
    }
  }
  ```

- [X] Crear script de entrada Python
  - `backend/main.py` → ejecutable standalone
  - Empaquetado con PyInstaller para distribución

- [X] Implementar supervisión en Rust
  - Iniciar Python al arrancar la app
  - Reiniciar si el proceso muere
  - Matar proceso al cerrar la app

- [X] Manejar estado de conexión
  - Si Python no conecta en 5s → error
  - Si conexión se pierde → intentar reconectar
  - Notificar al frontend vía WebSocket

---

### Fase 6: Testing y Limpieza

**Tareas**:

- [X] Tests de integración
- [X] Tests de rendimiento
- [X] Limpieza
  - Eliminar código muerto
  - Eliminar dependencias no usadas
  - Actualizar documentación
- [X] Testing multiplataforma (Verificado en Linux)

---

## Estructura Final

```
src-tauri/src/
├── lib.rs
├── bridge/
│   ├── mod.rs
│   ├── tcp_server.rs
│   ├── protocol.rs
│   └── python_bridge.rs
├── websocket/
│   ├── mod.rs
│   ├── server.rs
│   └── messages.rs
├── hardware/
│   └── manager.rs          # Sin cambios
├── math/
│   └── processor.rs        # Sin cambios
└── database/
    └── service.rs          # Sin cambios

backend/
├── main.py                 # Entry point
├── tcp_client.py
├── protocol.py
├── worker.py
└── utils/video/
    ├── video_processes.py
    └── pupil_detectors.py

frontend/src/
├── hooks/
│   ├── useWebSocket.ts     # ÚNICO hook de conexión
│   └── useTauriDb.ts       # Para base de datos (sigue usando IPC)
└── components/
    └── ...                 # Simplificados
```

---

## Diagrama de Flujo Final

```
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND (React)                        │
│                                                             │
│  useWebSocket() ←──────── WebSocket ────────→ UI Components│
│       │                                                     │
│       └── Solo renderiza, no coordina                       │
└─────────────────────────┬───────────────────────────────────┘
                          │ ws://localhost:PORT
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                    RUST (Orquestador)                       │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   WebSocket  │  │    Python    │  │   Hardware   │      │
│  │    Server    │  │    Bridge    │  │   Manager    │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                 │               │
│         │    ┌────────────┴────────────┐    │               │
│         │    │      EyeProcessor       │    │               │
│         │    │   (Kalman + Calibrar)   │    │               │
│         │    └─────────────────────────┘    │               │
│         │                                   │               │
│  ┌──────▼───────────────────────────────────▼──────┐       │
│  │              Broadcast Hub                       │       │
│  │  (Fusiona eye_data + imu_data + status)         │       │
│  └──────────────────────────────────────────────────┘       │
└─────────────────────────┬───────────────────────────────────┘
                          │ TCP localhost:9999
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                    PYTHON (Worker)                          │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  TCP Client  │──│    Worker    │──│    Video     │      │
│  │              │  │    Loop      │  │   Process    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                             │               │
│                                      ┌──────▼──────┐       │
│                                      │  OpenCV +   │       │
│                                      │    YOLO     │       │
│                                      └─────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

---

## Estimación de Complejidad

| Fase | Archivos Nuevos | Archivos Modificados | Archivos Eliminados |
|------|-----------------|---------------------|---------------------|
| 1 | 4 | 1 | 0 |
| 2 | 4 | 2 | 3 |
| 3 | 3 | 1 | 0 |
| 4 | 1 | 4 | 2 |
| 5 | 1 | 2 | 0 |
| 6 | 0 | 0 | 0 |
| **Total** | **13** | **10** | **5** |

---

## Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Latencia TCP mayor a SSE | Baja | Medio | TCP localhost es ~0.1ms, menor que HTTP |
| Video frames grandes saturan | Media | Alto | Comprimir JPEG al 80%, limitar FPS |
| Python crash no detectado | Baja | Alto | Heartbeat cada 1s, timeout de 3s |
| Puerto 9999 ocupado | Baja | Bajo | Usar puerto dinámico, notificar |
| Base64 video consume RAM | Media | Medio | Pool de buffers, limitar queue size |

---

## Orden de Ejecución Recomendado

1. **Fase 1** → Infraestructura TCP (Rust puede recibir conexiones)
2. **Fase 2** → Python worker (Ya se comunican Rust ↔ Python)
3. **Fase 5** → Gestión proceso (Rust inicia Python automáticamente)
4. **Fase 3** → WebSocket server (Frontend puede conectar)
5. **Fase 4** → Migrar frontend (Sistema completo funcionando)
6. **Fase 6** → Testing y limpieza

Este orden permite testing incremental: cada fase deja el sistema en estado funcional.
