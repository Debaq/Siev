# Análisis de Rendimiento: Sistema de Detección de Pupilas

## Resumen Ejecutivo

| Etapa | FPS Medidos | Pérdida |
|-------|-------------|---------|
| Cámara (entrada) | 124 | - |
| Pipeline Python | 86-210 | Variable |
| Frontend | 4-12 | **90-97%** |

**Diagnóstico:** El cuello de botella principal está en la transmisión Python → TCP → Rust → WebSocket → Frontend, no en el procesamiento de pupilas.

---

## ESTADO ACTUAL: Optimizaciones Implementadas

### Implementado el 2025-01-26

| Fase | Cambio | Archivo | Resultado |
|------|--------|---------|-----------|
| 1.1 | Eliminar conversión color duplicada | `worker.py:316` | ✅ Aplicado |
| 1.2 | Broadcast channel 100→500 | `server.rs:28` | ✅ Aplicado |
| 1.3 | Lazy mask creation (debug_mode) | `pupil_detectors.py` | ✅ Aplicado |
| 2.1 | JPEG en ThreadPoolExecutor | `worker.py` | ✅ Aplicado |
| 2.2 | Rate limiting 60fps | `worker.py` | ✅ Aplicado |
| 3.1 | Frame skipping en Rust | `lib.rs` | ✅ Aplicado |
| 3.3 | Reducir resolución 50% | `worker.py` | ✅ Aplicado |
| 4.1 | Starburst vectorizado | `pupil_detectors.py` | ✅ Aplicado |
| 5.1 | Diagnóstico de drops | `worker.py`, `lib.rs`, `useWebSocket.ts` | ✅ Aplicado |
| 5.2 | Throttle gráficos 10fps | `EyeDataPanel.tsx` | ✅ Aplicado |
| 5.3 | Reducir puntos 500→150 | `EyeDataPanel.tsx` | ✅ Aplicado |

### Resultado

**Backend Python:** Excelente rendimiento
- Con YOLO: 210 fps (configuración 120/90)
- Sin YOLO: 120/120 fps

**Frontend:** NO MEJORÓ SIGNIFICATIVAMENTE
- Subió momentáneamente a ~12 fps
- Cae a 4 fps de forma persistente
- El video se ve más pequeño (por resize 50%) pero igual de lento

### Conclusión

Las optimizaciones de backend y encoding funcionaron, pero el cuello de botella real está en el **pipeline de transmisión TCP → Rust → WebSocket**. Los frames se pierden en algún punto del camino.

---

## PARTE 1: Problemas del Backend Python (RESUELTO)

### 1.1 Arquitectura Actual

```
capture_worker (124 fps)
    ↓ frame_queue
detection_worker (YOLO cada 4 frames)
    ↓ result_queue
processing_worker (210 fps) → detección pupilas ✅ OPTIMIZADO
    ↓ ui_queue
video_manager_api → latest_frame
    ↓
worker.py → TCP → Rust → WebSocket → Frontend (4-12 fps) ❌ CUELLO DE BOTELLA
```

### 1.2 Optimizaciones Aplicadas al Backend

#### ✅ Starburst Vectorizado (pupil_detectors.py)
```python
# ANTES: 3200 iteraciones por pupila (16 rayos × 200 píxeles)
for angle in angles:
    for step in range(1, max_length):
        # ... iteración pixel por pixel

# DESPUÉS: Operaciones matriciales NumPy
rays_x = center_x + np.outer(cos_angles, steps)
rays_y = center_y + np.outer(sin_angles, steps)
values = image[rays_y_safe, rays_x_safe]
gradients = np.diff(values_with_center, axis=1)
```

#### ✅ Lazy Mask Creation (pupil_detectors.py)
```python
# Solo crear mask si debug_mode está activo
mask = cv2.cvtColor(eye_gray.copy(), cv2.COLOR_GRAY2BGR) if config.debug_mode else None
```

---

## PARTE 2: Problema de Transmisión (NO RESUELTO)

### 2.1 Flujo de Datos Actual

```
Python worker.py:
  1. Obtiene frame de video_manager.latest_frame
  2. cv2.resize(frame, 50%)                    # ✅ Reducido
  3. cv2.imencode('.jpg', quality=40)          # ✅ En ThreadPool
  4. await client.send_frame()                 # ❌ PROBLEMA AQUÍ?
  5. await asyncio.sleep(0.001)

Rust:
  1. TCP server recibe → broadcast channel (256)
  2. PythonBridge procesa → broadcast channel (512)
  3. lib.rs recibe → frame skipping 16ms       # ✅ Aplicado
  4. ws_broadcast.broadcast_binary()
  5. WebSocket → broadcast channel (500)       # ✅ Aumentado
  6. Frontend recibe                           # ❌ SOLO 4 FPS
```

### 2.2 Hipótesis del Problema

El problema persiste porque:

1. **await drain() bloqueante**: Python espera a que TCP vacíe su buffer antes de continuar
2. **Backpressure inexistente**: Python envía sin saber si el frontend puede procesar
3. **Múltiples capas de buffering**: Cada capa (TCP, Rust channels, WebSocket) acumula y dropea
4. **Sin feedback del frontend**: No hay ACK para saber qué frames llegaron

---

## PARTE 3: Nuevas Fases Propuestas

### Fase 5: Diagnóstico de Drops (RECOMENDADO PRIMERO)

**Objetivo:** Identificar exactamente dónde se pierden los frames

#### 5.1 Agregar Logging de Diagnóstico

**Archivo:** `backend/worker.py`
```python
async def _data_transmitter_loop(self):
    frames_sent = 0
    last_log_time = time.time()

    while self.video_manager.is_capturing:
        # ... código existente ...

        if pending_encode is not None and pending_encode.done():
            jpeg_bytes = pending_encode.result()
            await self.client.send_frame(jpeg_bytes)
            frames_sent += 1

            # Log cada segundo
            now = time.time()
            if now - last_log_time >= 1.0:
                logger.info(f"[DIAG] Frames enviados: {frames_sent}/s")
                frames_sent = 0
                last_log_time = now
```

**Archivo:** `src-tauri/src/python_bridge.rs`
```rust
// Agregar contador de frames recibidos/enviados
static FRAMES_RECEIVED: AtomicU64 = AtomicU64::new(0);
static FRAMES_FORWARDED: AtomicU64 = AtomicU64::new(0);

// En el handler de VideoFrame:
BridgeEvent::VideoFrame(jpeg) => {
    FRAMES_RECEIVED.fetch_add(1, Ordering::Relaxed);
    // ... enviar ...
    FRAMES_FORWARDED.fetch_add(1, Ordering::Relaxed);
}

// Log periódico
if now.duration_since(last_diag) >= Duration::from_secs(1) {
    let recv = FRAMES_RECEIVED.swap(0, Ordering::Relaxed);
    let fwd = FRAMES_FORWARDED.swap(0, Ordering::Relaxed);
    eprintln!("[DIAG] Bridge: recv={}/s fwd={}/s dropped={}/s", recv, fwd, recv - fwd);
}
```

**Archivo:** `src/hooks/useWebSocket.ts` (o equivalente en frontend)
```typescript
// Contador de frames recibidos en frontend
let framesReceived = 0;
setInterval(() => {
    console.log(`[DIAG] Frontend: ${framesReceived} frames/s`);
    framesReceived = 0;
}, 1000);

// En el handler de mensaje binario:
if (message instanceof ArrayBuffer) {
    framesReceived++;
    // ... procesar frame ...
}
```

---

### Fase 6: Fire-and-Forget TCP

**Objetivo:** Eliminar el bloqueo de `await drain()`

**Archivo:** `backend/tcp_client.py`

```python
# ANTES:
async def send_frame(self, jpeg_bytes: bytes):
    # ... preparar mensaje ...
    self._writer.write(data)
    await self._writer.drain()  # ❌ BLOQUEANTE

# DESPUÉS:
async def send_frame(self, jpeg_bytes: bytes):
    if not self.connected or self._writer is None:
        return False

    try:
        # ... preparar mensaje ...
        self._writer.write(data)
        # NO await drain() - fire and forget
        # El OS maneja el buffering TCP
        return True
    except Exception as e:
        logger.warning(f"Send failed (non-blocking): {e}")
        return False
```

**Consideraciones:**
- Puede causar uso de memoria si el buffer TCP crece mucho
- Agregar límite de buffer pendiente:

```python
class ReconnectingTcpClient:
    def __init__(self, ...):
        self._max_pending_bytes = 1024 * 1024  # 1MB máximo

    async def send_frame(self, jpeg_bytes: bytes):
        # Verificar si hay demasiado pendiente
        if self._writer and self._writer.transport:
            pending = self._writer.transport.get_write_buffer_size()
            if pending > self._max_pending_bytes:
                logger.warning(f"Buffer TCP lleno ({pending} bytes), dropeando frame")
                return False

        # Enviar sin esperar
        self._writer.write(data)
        return True
```

---

### Fase 7: Reducir FPS de Preview

**Objetivo:** Enviar menos frames pero más estables

**Archivo:** `backend/worker.py`

```python
async def _data_transmitter_loop(self):
    # Reducir drásticamente el target
    target_fps = 30  # En vez de 60
    frame_interval = 1.0 / target_fps

    # El eye tracking sigue a máxima velocidad
    # Solo el video preview se reduce
```

**Variante más agresiva - 15fps:**
```python
target_fps = 15  # Suficiente para preview, muy bajo overhead
```

---

### Fase 8: WebSocket Directo desde Python

**Objetivo:** Eliminar el paso por TCP y Rust para video frames

**Arquitectura propuesta:**
```
Python worker.py ──TCP──> Rust (solo comandos y eye data)
                 ──WS───> Frontend (video frames directo)
```

**Archivo:** `backend/worker.py`
```python
import websockets

class SievWorker:
    def __init__(self, ...):
        self._ws_server = None
        self._ws_clients = set()

    async def start(self):
        # Iniciar servidor WebSocket para video
        self._ws_server = await websockets.serve(
            self._ws_handler,
            "127.0.0.1",
            8766  # Puerto diferente al de Rust
        )
        logger.info("WebSocket video server en puerto 8766")

    async def _ws_handler(self, websocket, path):
        self._ws_clients.add(websocket)
        try:
            async for message in websocket:
                pass  # Solo recibe, no procesa
        finally:
            self._ws_clients.discard(websocket)

    async def _broadcast_frame(self, jpeg_bytes: bytes):
        if self._ws_clients:
            await asyncio.gather(
                *[client.send(jpeg_bytes) for client in self._ws_clients],
                return_exceptions=True
            )
```

**Archivo:** Frontend - conectar a ambos WebSockets:
```typescript
// WebSocket principal (Rust) - comandos y eye data
const mainWs = new WebSocket(`ws://127.0.0.1:${rustPort}`);

// WebSocket video (Python directo) - solo frames
const videoWs = new WebSocket('ws://127.0.0.1:8766');
videoWs.binaryType = 'arraybuffer';
videoWs.onmessage = (event) => {
    // Procesar frame de video
    const blob = new Blob([event.data], { type: 'image/jpeg' });
    videoUrl = URL.createObjectURL(blob);
};
```

**Ventajas:**
- Elimina 2 capas de buffering (TCP Python→Rust, channels internos)
- Control directo del flujo
- Más fácil implementar backpressure

**Desventajas:**
- Requiere que frontend conecte a 2 WebSockets
- Más complejidad en el frontend

---

### Fase 9: Shared Memory (Avanzado)

**Objetivo:** Eliminar serialización/deserialización de frames

**Concepto:**
```
Python: Escribe JPEG a memoria compartida
        Notifica a Rust vía TCP (solo "frame listo")
Rust:   Lee de memoria compartida
        Envía por WebSocket
```

**Implementación básica con mmap:**

**Archivo:** `backend/shared_frame.py`
```python
import mmap
import struct

class SharedFrameBuffer:
    def __init__(self, name: str, max_size: int = 1024 * 1024):
        self.name = f"/dev/shm/siev_{name}"
        self.max_size = max_size
        self._fd = open(self.name, "w+b")
        self._fd.truncate(max_size + 8)  # 8 bytes header (size + sequence)
        self._mmap = mmap.mmap(self._fd.fileno(), max_size + 8)

    def write_frame(self, data: bytes, sequence: int):
        size = len(data)
        if size > self.max_size:
            raise ValueError("Frame too large")

        # Header: [size:4bytes][sequence:4bytes]
        header = struct.pack('<II', size, sequence)
        self._mmap.seek(0)
        self._mmap.write(header)
        self._mmap.write(data)

    def close(self):
        self._mmap.close()
        self._fd.close()
```

**Archivo:** `src-tauri/src/shared_frame.rs`
```rust
use memmap2::MmapMut;

pub struct SharedFrameBuffer {
    mmap: MmapMut,
}

impl SharedFrameBuffer {
    pub fn open(name: &str) -> Result<Self, std::io::Error> {
        let path = format!("/dev/shm/siev_{}", name);
        let file = std::fs::OpenOptions::new()
            .read(true)
            .open(&path)?;
        let mmap = unsafe { MmapMut::map_mut(&file)? };
        Ok(Self { mmap })
    }

    pub fn read_frame(&self) -> Option<(Vec<u8>, u32)> {
        let size = u32::from_le_bytes(self.mmap[0..4].try_into().ok()?);
        let seq = u32::from_le_bytes(self.mmap[4..8].try_into().ok()?);
        let data = self.mmap[8..8 + size as usize].to_vec();
        Some((data, seq))
    }
}
```

---

## Orden de Implementación Recomendado

| Prioridad | Fase | Descripción | Esfuerzo | Impacto Esperado |
|-----------|------|-------------|----------|------------------|
| 1 | **5** | Diagnóstico de drops | Bajo | Identificar problema |
| 2 | **6** | Fire-and-forget TCP | Bajo | Medio |
| 3 | **7** | Reducir a 30fps preview | Muy bajo | Medio |
| 4 | **8** | WebSocket directo | Alto | Alto |
| 5 | **9** | Shared memory | Muy alto | Muy alto |

**Recomendación:** Empezar con Fase 5 + 6 + 7 (todas de bajo esfuerzo) y medir resultados antes de invertir en Fase 8 o 9.

---

## Archivos a Modificar

| Archivo | Fases |
|---------|-------|
| `backend/worker.py` | 5, 7, 8 |
| `backend/tcp_client.py` | 6 |
| `src-tauri/src/python_bridge.rs` | 5 |
| `src-tauri/src/lib.rs` | 5, 9 |
| `src/hooks/useWebSocket.ts` | 5, 8 |

---

*Documento actualizado: 2025-01-26*
*Estado: Fases 1-5 implementadas*
*Próximo paso: Ejecutar la aplicación y analizar los logs de diagnóstico para identificar dónde se pierden frames*
