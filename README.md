# SIEV

Sistema de Video-Oculografía para diagnóstico vestibular y auditivo.

Aplicación de escritorio (Tauri + React + Rust) que integra captura de video ocular, análisis de nistagmo, pruebas calóricas, posicionales, oculomotoras, audiometría y posturografía.

## Características

- **VNG (Video-oculografía):** captura dual-cámara, detección de pupila por algoritmo matemático refinado con *hints* de un modelo YOLO26 (ONNX) para seed del tracker, métricas de nistagmo.
- **Pruebas clínicas:**
  - Calórica (bitermal / monotermal, OFI, método seleccionable)
  - Posicional (Dix-Hallpike, rotaciones)
  - Oculomotora (sacadas, seguimiento, optokinético)
  - Postural (estabilometría, tests custom, editor de fases)
  - Audiometría (tonal, vocal, supraliminar, alta frecuencia, acumetría)
- **Calibración persistente por paciente** (auto guardar/cargar).
- **Generación de reportes PDF** (jsPDF + html2canvas).
- **Pantalla externa de estímulo** (ventana secundaria para paciente).
- **Firmware ESP8266** para hardware de estímulo físico.

## Stack

| Capa | Tech |
|------|------|
| Frontend | React 19, TypeScript, Vite, TailwindCSS v4, Three.js, ECharts, Recharts, uPlot |
| Backend | Rust, Tauri 2, tokio, sqlx (SQLite), nokhwa (v4l), ort (ONNX Runtime), nalgebra, ndarray, openh264 |
| Hardware | ESP8266 (estímulo), Arduino (prototipo tesis), puerto serial |
| IPC | Tauri commands + WebSocket (tokio-tungstenite) |

## Estructura

```
siev/
├── frontend/          React + Vite (UI)
│   └── src/
│       ├── components/   (audiometry, postural, charts, reports, review, stimulus, settings)
│       ├── pages/        (Calibration, ExternalDisplay, StimulusPlayer)
│       ├── contexts/     (WebSocket)
│       └── hooks/
├── src-tauri/         Backend Rust + Tauri
│   └── src/
│       ├── vng/          (metrics, nystagmus, native_video, report, tests/)
│       ├── hardware/     (manager, serial)
│       ├── database/     (SQLite schema)
│       ├── websocket/
│       ├── storage/
│       └── math/
├── firmware/          Código ESP8266 + Arduino
├── backend/models/    Modelos ONNX
└── docs/
```

## Requisitos

- Node.js 20+ y npm (o pnpm)
- Rust stable (cargo)
- `cargo-tauri` CLI: `cargo install tauri-cli --version "^2"`
- Linux: v4l, libappindicator, libwebkit2gtk-4.1, fuse2 (para AppImage)
- Windows: WebView2 (nativo en Win10+)
- Cámara V4L2 compatible

## Uso rápido

Script todo-en-uno:

```bash
./siev.sh            # menú interactivo
./siev.sh install    # instalar deps
./siev.sh dev        # dev debug
./siev.sh dev-fast   # dev release (alto FPS)
./siev.sh dev-clean  # limpiar y dev
./siev.sh build      # build producción + bundle
./siev.sh clean      # limpieza total
```

Windows: `siev.ps1`.

## Manual

```bash
cd frontend && npm install
cd ../src-tauri && cargo fetch
cargo tauri dev           # debug
cargo tauri dev --release # release
cargo tauri build         # bundle final
```

Artefactos de build: `out/v<version>_<timestamp>/` (binario + tarball + AppImage/MSI/NSIS si disponible).

## Desarrollo

- Frontend dev server: `http://localhost:5173`
- Ventana Tauri: 1400x900 mín. 1280x720
- WebSocket interno para streaming de frames y eventos de hardware
- SQLite embebido (pacientes, sesiones, calibración)

## Licencia

MIT
