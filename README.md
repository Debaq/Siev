# SIEV

Video-oculography system for vestibular and audiological diagnostics.

Desktop application (Tauri + React + Rust) that integrates dual-camera eye tracking, nystagmus analysis, caloric / positional / oculomotor testing, audiometry, and posturography into a single clinical workstation.

## Features

- **VNG (video-oculography):** dual-camera capture, pupil detection via a refined mathematical algorithm seeded with hints from a YOLO26 ONNX model, real-time nystagmus metrics.
- **Clinical tests:**
  - Caloric (bithermal / monothermal, OFI, selectable method)
  - Positional (Dix-Hallpike, rotations)
  - Oculomotor (saccades, smooth pursuit, optokinetic)
  - Postural (stabilometry, custom tests, phase editor)
  - Audiometry (pure-tone, speech, suprathreshold, high-frequency, acumetry)
- **Per-patient persistent calibration** (auto save / load).
- **PDF report generation** (jsPDF + html2canvas).
- **External stimulus display** (secondary window for the patient).
- **ESP8266 firmware** for physical stimulus hardware.

## Stack

| Layer    | Tech |
|----------|------|
| Frontend | React 19, TypeScript, Vite, TailwindCSS v4, Three.js, ECharts, Recharts, uPlot |
| Backend  | Rust, Tauri 2, tokio, sqlx (SQLite), nokhwa (v4l), ort (ONNX Runtime), nalgebra, ndarray, openh264 |
| Hardware | ESP8266 (stimulus), Arduino (thesis prototype), serial port |
| IPC      | Tauri commands + WebSocket (tokio-tungstenite) |

## Layout

```
siev/
├── frontend/          React + Vite (UI)
│   └── src/
│       ├── components/   (audiometry, postural, charts, reports, review, stimulus, settings)
│       ├── pages/        (Calibration, ExternalDisplay, StimulusPlayer)
│       ├── contexts/     (WebSocket)
│       └── hooks/
├── src-tauri/         Rust + Tauri backend
│   └── src/
│       ├── vng/          (metrics, nystagmus, native_video, report, tests/)
│       ├── hardware/     (manager, serial)
│       ├── database/     (SQLite schema)
│       ├── websocket/
│       ├── storage/
│       └── math/
├── firmware/          ESP8266 + Arduino code
├── backend/models/    ONNX models
└── docs/
```

## Requirements

- Node.js 20+ and npm (or pnpm)
- Rust stable (cargo)
- `cargo-tauri` CLI: `cargo install tauri-cli --version "^2"`
- Linux: v4l, libappindicator, libwebkit2gtk-4.1, fuse2 (for AppImage)
- Windows: WebView2 (bundled in Win10+)
- V4L2-compatible camera

## Quick start

All-in-one script:

```bash
./siev.sh            # interactive menu
./siev.sh install    # install deps
./siev.sh dev        # dev debug
./siev.sh dev-fast   # dev release (high FPS)
./siev.sh dev-clean  # clean and dev
./siev.sh build      # production build + bundle
./siev.sh clean      # full cleanup
```

Windows: `siev.ps1`.

## Manual

```bash
cd frontend && npm install
cd ../src-tauri && cargo fetch
cargo tauri dev           # debug
cargo tauri dev --release # release
cargo tauri build         # final bundle
```

Build artifacts: `out/v<version>_<timestamp>/` (binary + tarball + AppImage/MSI/NSIS when available).

## Development

- Frontend dev server: `http://localhost:5173`
- Tauri window: 1400x900, min 1280x720
- Internal WebSocket for frame streaming and hardware events
- Embedded SQLite (patients, sessions, calibration)

## Documentation

- [Eye tracking pipeline](docs/seguimiento-ocular.md) — capture, ROI, YOLO hints, pupil detector, Kalman, calibration

## License

MIT
