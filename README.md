# SIEV — VNG en Rust puro

Videonistagmografia (VNG) de escritorio, sin Tauri ni frontend web: un solo
binario Rust con GUI nativa (`eframe`/`egui`) y graficos en tiempo real
(`egui_plot`).

El pipeline de seguimiento pupilar se copio tal cual de la rama `rust-rust`
(mismo equipo: camara USB MJPEG + iluminacion IR). La prueba de regresion de
traza de tolerancia cero pasa bit a bit sobre el codigo copiado.

## Estructura

```
crates/
  siev-tracking/        pipeline (lib, sin GUI)
    src/bus.rs          bus de eventos en proceso (reemplaza al WebSocket)
    src/math/           EyeProcessor (centrado, calibracion) + Kalman 6 estados
    src/vng/            captura, ROI, YOLO, detector, nistagmo, traza
    src/storage/        grabador JSONL y H.264
    tests/              regresion de traza (tolerancia cero)
  siev-vng/             app GUI: preview, parametros, graficos H/V OD/OI
docs/seguimiento-ocular.md   detalle del pipeline
fixtures/README.md           como reconstruir las secuencias PGM
NOTAS_HALLAZGOS.md           hallazgos [H-xx] citados en el codigo
```

## Uso

```bash
cargo run --release -p siev-vng            # app
cargo test -p siev-tracking                # unitarios + regresion de traza
```

La regresion necesita `fixtures/seq_eyes_800/` (no versionada, ver
`fixtures/README.md`); si falta, la prueba se salta. Tambien acepta
`SIEV_SEQ_DIR=<carpeta>`.

Dependencias de sistema (Linux): `v4l` (camara), y para la GUI las de
`winit`/`wgpu` (Wayland o X11). `ort` descarga ONNX Runtime al compilar.
