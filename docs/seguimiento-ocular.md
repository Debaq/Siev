# Seguimiento ocular (pupil tracking)

Detalle tecnico del pipeline de video-oculografia: desde el frame crudo de la camara
hasta la posicion angular de cada pupila en grados.

Todo el pipeline corre en Rust, en un hilo dedicado, desacoplado del render de la UI.

**Archivos clave**

| Archivo | Responsabilidad |
|---------|-----------------|
| `src-tauri/src/vng/native_video.rs` | Captura, ROI, YOLO, deteccion de pupila, preview |
| `src-tauri/src/math/processor.rs` | Centrado, calibracion pixel->grados, orquestacion Kalman |
| `src-tauri/src/math/kalman.rs` | Filtro de Kalman de 6 estados |
| `src-tauri/src/vng/nystagmus.rs` | Analisis posterior (batidas, SPV) |

---

## Vision general

```
camara MJPEG
   |
   v
[1] captura + fallback + reconexion        native_video.rs:475
   |
   v
[2] decode Luma (zune-jpeg) + ROI dual + frame combinado
   |
   v
[3] YOLO26 ONNX cada N frames -> cajas de busqueda (opcional)
   |
   v
[4] detector matematico refinado por ojo   native_video.rs:1503
   |
   v
[5] estado inter-frame: velocidad, radio, perdidas, parpadeo
   |
   v
[6] EyeProcessor: centrado + Kalman + escala a grados   processor.rs:117
   |
   v
[7] WebSocket EyeData + SessionRecorder    (full rate)
    preview JPEG con overlays              (throttled a 30 FPS)
```

---

## 1. Captura

`NativeVideoManager::start_capture` — `native_video.rs:475`

- `nokhwa` (backend V4L2) solicita **MJPEG** a la resolucion/fps pedidos.
- Si falla, cascada de formatos fallback (`native_video.rs:544-559`):
  `(w,h,fps)` solicitado, luego 240/120/60 fps al mismo tamano, luego
  640x480, 640x400, 640x360, 800x600, 1280x720.
- Si `nokhwa` falla con todos, se abre `v4l` directo. Necesario porque `nokhwa`
  no maneja framerates fraccionarios que reportan algunas camaras.
- Si no hay camara, se entra en **modo polling**: reintento cada 500 ms,
  broadcast `CameraStatus { status: "disconnected" }`.

**Watchdog de desconexion.** 10 errores consecutivos de captura
(`MAX_CONSECUTIVE_ERRORS`) sueltan la camara, notifican desconexion y entran al
loop de reconexion (`native_video.rs:770-830` para nokhwa, `~838-905` para v4l).
La reconexion prueba primero nokhwa y despues v4l, en ambos sentidos.

**Decodificacion.** `zune-jpeg` con
`DecoderOptions::default().jpeg_set_out_colorspace(ColorSpace::Luma)`: la salida
es escala de grises directa, sin pasar por RGB. Ahorra la conversion de color
completa por frame.

---

## 2. ROI dual y frame combinado

`native_video.rs:940-1000`

La camara ve ambos ojos en un mismo frame. Se descarta la franja de la nariz y se
recortan dos ROI:

```
roi_nose   = w * nose_width        (default 0.25)
roi_y      = h * 0.1
roi_height = h * eye_height * 2    (default 0.25 -> 50% del alto)

ojo derecho  = x [0, roi_eye_width]                 (lado izquierdo de la imagen)
ojo izquierdo = x [roi_eye_width + roi_nose, w]     (lado derecho de la imagen)
roi_eye_width = (w - roi_nose) / 2
```

Ambos ROI se copian a una unica imagen `combined` fila por fila con
`copy_from_slice` (memcpy), no pixel a pixel. Las dimensiones resultantes se
publican en `combined_w` / `combined_h` (atomicos) para el grabador de video.

Despues se aplica brillo y contraste sobre Luma
(`apply_brightness_contrast_luma`, `native_video.rs:1877`).

El frame limpio (sin marcas de UI) se envia al `VideoRecorder` si hay grabacion
activa — se graba lo que ve el algoritmo, no lo que ve el operador.

---

## 3. YOLO26 ONNX — solo pistas, no posicion final

`run_yolo_inference` — `native_video.rs:1340`

Se ejecuta cada `yolo_frequency` frames (default 10) y es **opcional**
(`use_yolo`, default `false`). Su unico trabajo es entregar la caja de busqueda.

**Preproceso**
- Letterbox a 640x640: escala manteniendo proporcion + padding gris (114,114,114).
- El canal Luma se replica en los 3 canales RGB, normalizado a [0,1].
- Tensor `Array4<f32>` de forma `[1, 3, 640, 640]`.

**Postproceso**
- Salida `output0` con forma `[1, 300, 6]` = `[x1, y1, x2, y2, conf, class_id]`.
  Shape distinto -> se descarta la inferencia.
- `conf < 0.25` se descarta. Clases: `0 = ojo`, `1 = pupila`.
- Coordenadas revertidas del letterbox: `(v - pad) * (1/scale)`, clampeadas.
- **Ojos:** top-2 por confianza, luego reordenados por `x1` (izq -> der).
  Si hay menos de 2, la inferencia se descarta entera.
- Padding de la caja del ojo: -20/+20 px horizontal, -40/+40 px vertical.
- **Pupilas:** cada deteccion se asigna al ojo cuyo centro de bbox este mas cerca
  (distancia euclidiana al cuadrado). Por ojo se guarda la de mayor confianza.

Si YOLO esta desactivado o no detecta, se usa el **ROI manual** (`ManualEyeRoi`:
`top`, `bottom`, `nasal`, `temporal`, todos relativos 0.0-1.0 respecto al area de
cada ojo). Nota: en el ojo derecho `temporal` mapea a x1 y `nasal` a x2; en el
izquierdo es al reves, porque el eje temporal-nasal se invierte entre ojos.

---

## 4. Detector matematico refinado

`detect_pupil_math_refined` — `native_video.rs:1503`

Es el corazon del tracking. Se ejecuta por ojo, en cada frame, sobre la imagen
combinada.

### a) ROI dinamico con prediccion de velocidad

```
speed  = |velocity|
margin = max(prev.radius * 2.5,
             prev.radius * 2 + speed * velocity_margin_factor)   (factor def 2.0)
centro_busqueda = prev.center + velocity
```

Si no hay pupila previa (o la ventana resultante mide menos de 10x10), se busca
en el ROI completo. Este recorte reduce el area de busqueda entre 10x y 50x y es
lo que sostiene los FPS altos.

Los buffers `scratch_gray` / `scratch_thresh` se reusan entre frames y solo se
reasignan si cambia el tamano de la ventana (zero-allocation en regimen).

### b) Umbral adaptativo con histeresis

Blur gaussiano (`smooth_sigma`, default 2.5), luego:

1. Histograma de 256 bins. Si el ancho de busqueda supera 100 px, se submuestrea
   uno de cada 2 pixeles.
2. Se acumula hasta el **percentil 15%** mas oscuro -> `raw_val`.
3. Suavizado temporal:

```
thresh = 0.8 * thresh_anterior + 0.2 * raw_val
```

La histeresis evita que el umbral oscile frame a frame con cambios minimos de
iluminacion. Si `manual_threshold != 0` (default 40) se salta todo el calculo y
se usa el valor fijo.

Binarizacion: `pixel <= thresh -> 255`, si no `0` (la pupila es lo oscuro).

### c) Deteccion de parpadeo

Activa por defecto (`blink_detection`). Se evalua **antes** de la morfologia:

```
white_ratio = pixeles_blancos / pixeles_totales
si white_ratio > blink_white_ratio (def 0.60) o white_ratio < 0.01:
    -> RustPupilResult { found: false, confidence: -1.0 }
```

`confidence == -1.0` es un marcador especial, distinto de "no encontrado": el
estado de tracking se **congela** (no decae la velocidad, no incrementa el
contador de perdidas). Ver seccion 5.

### d) Morfologia

`close` con norma LInf radio 2, luego `erode` LInf radio 1 repetido
`erode_iter` veces (default 1).

### e) Contornos y filtros en cascada

`find_contours::<i32>`. Por cada candidato, en orden:

| Filtro | Criterio | Default |
|--------|----------|---------|
| Aspect ratio del bbox | `bb_w / bb_h` fuera de rango | 0.4 – 2.5 |
| Area | fuera de `[min_area, max_area]` | 30 px – 60% del ROI |
| Intensidad media | `mean > thresh * 1.5` | — |
| Extent | `area / (bb_w * bb_h) < 0.4` | 0.4 |
| Circularidad | `4*pi*A / P^2 < min_circularity` | 0.55 |
| Margen del borde | centroide a menos de 3 px del borde del ROI | 3 px |

El filtro de borde existe porque la pupila fisicamente nunca queda pegada al
limite del ROI; lo que aparece ahi suele ser pestana o sombra del parpado.

### f) Centroide sub-pixel ponderado

No se usa el centro del bounding box ni el centroide binario. Se usan momentos
ponderados por oscuridad:

```
w(x,y) = (255 - I(x,y))^2

cx = sum(x * w) / sum(w)
cy = sum(y * w) / sum(w)
```

`I` es la intensidad del frame **suavizado**, no del binarizado. Los pixeles mas
oscuros pesan cuadraticamente mas, lo que da precision sub-pixel y hace el
centroide robusto frente a los bordes difusos del iris.

### g) Score de seleccion

```
proximity = exp(-d^2 / (2*sigma^2)),  sigma = max(prev.radius * 2.5, 15)
d = distancia del candidato a la posicion predicha

score = area * circularity * darkness_factor * (0.3 + 0.7 * proximity)

darkness_factor = 1 - (mean_intensity / 255)
```

El termino de proximidad prefiere el candidato cercano a la prediccion pero no
elimina a los lejanos: el piso de 0.3 permite recuperar el tracking tras un salto
real (sacada rapida) sin quedarse pegado a un falso positivo.

Gana el score mas alto. `radius = sqrt(area / pi)`, `confidence = circularity`
(limitada a 1.0).

### h) Gate de salto imposible

```
si distancia(mejor_candidato, posicion_predicha) > max(prev.radius * 5, 40) px:
    -> se descarta el frame como perdida
```

Descarta saltos fisicamente imposibles para un ojo entre dos frames consecutivos.

---

## 5. Estado inter-frame

`native_video.rs:1099-1200` (ojo derecho; el izquierdo es simetrico)

Mantenido en el hilo de captura, independiente por ojo:

```
// deteccion exitosa
velocity = 0.5 * velocity + 0.5 * (pos - pos_anterior)   // EMA
radius   = 0.7 * radius_anterior + 0.3 * radius_nuevo    // suavizado temporal

// perdida
velocity *= 0.8          // decaimiento
lost_count += 1
si lost_count > lost_tolerance (def 5):
    reset del tracker -> proxima busqueda es global

// parpadeo (confidence == -1.0)
se congela todo el estado
si el parpadeo dura > 500 ms -> reset completo
```

La distincion entre "perdida" y "parpadeo" es importante: durante un parpadeo la
pupila sigue donde estaba, asi que conservar velocidad y posicion permite
retomar el tracking al abrir el ojo sin volver a la busqueda global.

---

## 6. Conversion de coordenadas y procesado

`native_video.rs:1204-1215` y `processor.rs:117`

El eje Y se invierte (`* -1.0`) al salir del detector, para pasar de convencion
de imagen (Y crece hacia abajo) a convencion matematica (Y crece hacia arriba).
El timestamp es UTC en milisegundos convertido a segundos (`f64`).

`EyeProcessor::process`:

1. **`dt` dinamico real** entre frames, con minimo de 1 ms. No se asume el fps
   nominal de la camara: el pipeline entrega frames a ritmo variable.
2. **Centrado:** `punto -= center`, donde `center` viene de la calibracion.
3. **Kalman** por ojo (seccion 7).
4. **Escala a grados:** `[x * scale_x, y * scale_y]`.

Si `filtering_enabled == false`, se devuelven los datos crudos sin Kalman ni
centrado.

---

## 7. Filtro de Kalman (6 estados)

`math/kalman.rs`

Estado: `[x, y, vx, vy, ax, ay]`. Modelo cinematico de aceleracion constante
amortiguada:

```
x = x + v*dt + 0.5*a*dt^2
v = v + a*dt
a = a * stability_factor        (default 0.01)
```

El `stability_factor` de 0.01 hace que la aceleracion practicamente no persista
entre pasos: el modelo tolera aceleraciones bruscas (sacadas) sin extrapolarlas.

**Matriz de medicion `H`:** solo se mide posicion (2x6).

**Ruido de proceso `Q`:** identidad * `process_noise` (0.01), con ajuste fino:

```
Q[0,0] y Q[1,1] *= 0.1     // menos ruido en posicion -> ancla la posicion
Q[4,4] y Q[5,5] *= 10.0    // mas ruido en aceleracion -> la deja moverse rapido
```

**Ruido de medicion `R`:** identidad * 0.1. Con `Q = 0.01` y `R = 0.1` el filtro
confia mas en el modelo que en la medicion, lo que suaviza el jitter del
centroide a costa de un retardo minimo.

**Detalles de implementacion**
- `predict()` se ejecuta **siempre**, incluso sin medicion disponible. Esto
  mantiene la inercia durante parpadeos y hace crecer la incertidumbre.
- Primera medicion: inicializa posicion, deja velocidad y aceleracion en 0 y la
  devuelve tal cual.
- Si `S` no es invertible (raro), se devuelve la prediccion actual en vez de
  fallar.

---

## 8. Calibracion

`processor.rs:239` (`apply_manual_calibration`)

Calibracion manual multi-punto. El paciente fija una serie de targets con angulo
conocido y el frontend captura la posicion en pixeles de cada pupila.

El mapeo es lineal, por eje y por ojo, con **minimos cuadrados forzados por el
origen**:

```
angulo = scale * (pixel - pixel_centro)

scale = sum(angulo * delta_pixel) / sum(delta_pixel^2)     [grados / pixel]
```

- El punto con `id == "C"` (o `angle_x == 0 && angle_y == 0`) define el centro y
  se excluye de la regresion.
- Deltas menores a `1e-6` se ignoran.
- Un eje sin datos (por ejemplo calibracion de 3 puntos solo horizontal) cae al
  default `scale = 1.0`.
- Al aplicar, los filtros de Kalman se resetean para adaptarse al nuevo sistema
  de coordenadas.

**Persistencia.** `CalibrationSnapshot` guarda puntos, distancia del paciente,
centros y escalas de ambos ojos, mas un timestamp RFC3339. Se guarda y recarga
automaticamente por paciente (`export_calibration_snapshot` /
`restore_calibration`).

**Auto-calibracion de respaldo.** Si no hay calibracion manual, se promedian las
primeras 30 muestras validas de cada ojo para establecer el centro
(`finalize_calibration`). Da centrado pero **no** escala angular: la salida queda
en pixeles.

---

## 9. Salida

**Datos (full rate, cada frame)**
- `WsMessage::EyeData(ProcessedEyeData)` por WebSocket al frontend.
- `SessionRecorder::record()` si hay grabacion de sesion activa.

`ProcessedEyeData { left, right, timestamp, is_calibrated }`, posiciones en
grados si hay calibracion manual aplicada.

**Preview visual (throttled a 30 FPS)**

Solo si `last_ui_time.elapsed() > 33 ms`. Desacoplado del procesamiento, que
corre a 120-240 FPS. Se convierte a RGB **solo para visualizar**:

- Cajas de busqueda: verde si vienen de YOLO, amarillo si son ROI manual.
- Etiquetas `OD` (rojo) / `OI` (celeste).
- Cruces sobre las pupilas detectadas.
- Si `show_debug` esta activo, se superponen las mascaras binarizadas con
  alpha 0.5 (rojo OD, celeste OI), posicionadas segun la ventana de busqueda
  dinamica actual.

Se codifica JPEG calidad 70 y se envia por `broadcast_binary`.

---

## 10. Metricas de rendimiento

Cada 1 segundo de tiempo de pared se imprime `[PERF]`:

```
FPS reales    = frames entregados / tiempo de pared transcurrido
Latencia CPU  = tiempo total de procesamiento / frames     [ms por frame]
Carga pipeline = tiempo total de procesamiento / tiempo de pared   [%]
```

La latencia mide solo el procesamiento (decode + ROI + deteccion), sin el bloqueo
esperando el siguiente frame de la camara. La carga del pipeline indica cuanto
margen queda: si se acerca a 100%, el detector es el cuello de botella y no la
camara.

---

## Referencia de parametros

Defaults en `NativeVideoManager::new` — `native_video.rs:283`.
Todos configurables en caliente desde la UI (pestanas Camera / Algorithm).

| Parametro | Default | Efecto |
|-----------|---------|--------|
| `threshold` [der, izq] | `[40, 40]` | Umbral fijo. `0` activa el adaptativo |
| `erode` [der, izq] | `[1, 1]` | Iteraciones de erosion |
| `nose_width` | 0.25 | Fraccion del ancho descartada (nariz) |
| `eye_height` | 0.25 | Alto del ROI (se multiplica x2) |
| `use_yolo` | `false` | Activa las pistas del modelo ONNX |
| `yolo_frequency` | 10 | Inferencia cada N frames |
| `smooth_sigma` | 2.5 | Sigma del blur gaussiano |
| `brightness` | 0 | -100 a +100 |
| `contrast` | 1.0 | 0.0 a 3.0 |
| `min_circularity` | 0.55 | Circularidad minima del contorno |
| `min_area` | 30 | Area minima en px |
| `max_area_ratio` | 0.6 | Area maxima como fraccion del ROI |
| `blink_detection` | `true` | Deteccion de parpadeo por ratio de blancos |
| `blink_white_ratio` | 0.60 | Umbral de blancos que marca parpadeo |
| `lost_tolerance` | 5 | Frames perdidos antes de resetear el tracker |
| `velocity_margin_factor` | 2.0 | Expansion del ROI segun velocidad |
| `aspect_ratio_min` / `max` | 0.4 / 2.5 | Rango de aspect ratio del bbox |
