# Conexiones WebSocket eliminadas de Configuracion VNG

Campos y mensajes WebSocket removidos del frontend de Settings/Configuracion.
El backend (Rust) puede seguir esperando estos mensajes. Revisar para limpiar o reconectar segun necesidad.

---

## CameraTab - Conexiones eliminadas

### Campos eliminados de la UI
| Campo | WS Key | Mensaje |
|-------|--------|---------|
| `exposure` | `exposure` | `{ type: 'set_config', key: 'exposure', value: number }` |
| `contrast` | `contrast` | `{ type: 'set_config', key: 'contrast', value: number }` |
| `video_quality` | `video_quality` | `{ type: 'set_config', key: 'video_quality', value: number }` |
| `video_scale` | `video_scale` | `{ type: 'set_config', key: 'video_scale', value: number }` |
| `flip_horizontal` | `flip_h` | `{ type: 'set_config', key: 'flip_h', value: boolean }` |
| `flip_vertical` | `flip_v` | `{ type: 'set_config', key: 'flip_v', value: boolean }` |

### syncWithWebSocket - campos eliminados de camera_setup
Anteriormente el mensaje `camera_setup` incluia `video_quality` y `video_scale`:
```json
{
  "type": "set_config",
  "key": "camera_setup",
  "value": {
    "camera_id": 0,
    "width": 960,
    "height": 540,
    "fps": 60,
    "video_quality": 80,
    "video_scale": 0.75
  }
}
```
Ahora solo envia: `camera_id`, `width`, `height`, `fps`.

---

## AlgorithmTab - Conexiones eliminadas

| Campo | WS Key | Mensaje |
|-------|--------|---------|
| `threshold` (umbral binarizacion) | `bin_threshold` | `{ type: 'set_config', key: 'bin_threshold', value: number }` |
| `min_pupil_size` | `min_size` | `{ type: 'set_config', key: 'min_size', value: number }` |
| `show_debug` (toggle) | `show_debug` | `{ type: 'set_config', key: 'show_debug', value: boolean }` |
| `pupil_detection.mode` | `pupil_mode` | `{ type: 'set_config', key: 'pupil_mode', value: string }` |

**Nota:** `show_debug` y otros campos de algoritmo aun se envian desde el ControlPanel (ajustes avanzados en runtime via `useSessionConfig`). Solo se elimino el duplicado en Settings.

---

## syncWithWebSocket - Bloque eliminado: set_pupil_config

Se elimino completamente el envio de configuracion de deteccion de pupila al guardar settings:
```json
{
  "type": "set_pupil_config",
  "params": {
    "mode": "legacy",
    "search_window_multiplier": 3.0,
    "dark_threshold_percent": 20,
    "starburst_rays": 16,
    "starburst_min_gradient": 30,
    "fallback_threshold": 5,
    "min_confidence_for_lock": 0.5,
    "revalidation_interval": 30,
    "legacy_blur_enabled": true,
    "legacy_blur_kernel": 5,
    "legacy_clahe_enabled": true,
    "legacy_clahe_clip_limit": 2.0,
    "legacy_clahe_grid_size": 8,
    "legacy_morph_enabled": true,
    "legacy_morph_close_iterations": 1,
    "legacy_morph_dilate_iterations": 1
  }
}
```

---

## VisualStimuliTab - Seccion eliminada

Se elimino la seccion de **Calibracion** del tab de estimulos visuales.
Anteriormente enviaba via Tauri emit:
```json
{
  "test": "calibration",
  "params": {
    "type": "points_9",
    "horizontal_fov": 20,
    "vertical_fov": 10,
    "duration_per_point": 1.5,
    "auto_advance": true
  }
}
```

---

## HardwareConfig - Campos eliminados (solo tipo/defaults, no habia UI)

| Campo | Descripcion |
|-------|-------------|
| `fixation_led_enabled` | LED de fijacion habilitado (no tenia controles en Settings) |
| `fixation_led_auto_off` | Tiempo auto-apagado LED (no tenia controles en Settings) |

---

## Tipos TypeScript eliminados

| Tipo | Archivo original |
|------|-----------------|
| `VNGLegacyParams` | `config.ts` |
| `VNGPupilDetectionConfig` | `config.ts` |
| `ManualEyeRoi` | `config.ts` (se mantiene en `useSessionConfig.ts`) |

---

## Campos eliminados de interfaces existentes

### VNGCameraConfig
`exposure`, `contrast`, `brightness`, `flip_horizontal`, `flip_vertical`, `video_quality`, `video_scale`

### VNGAlgorithmConfig
`threshold`, `threshold_left`, `threshold_right`, `erode_left`, `erode_right`, `min_pupil_size`, `roi_enabled`, `nose_width`, `eye_height`, `smooth`, `use_yolo`, `show_debug`, `manual_roi_right`, `manual_roi_left`

### VNGHardwareConfig
`fixation_led_enabled`, `fixation_led_auto_off`

### VNGConfig
`pupil_detection` (seccion completa eliminada)

### StimulusDefaultParams
`calibration` (sub-objeto eliminado)
