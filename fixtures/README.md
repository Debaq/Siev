# Secuencias de referencia

Material de entrada para la prueba de regresion de traza (Fase 1) y, mas
adelante, para `vng-bench`.

**Las secuencias PGM no se versionan** (238 MB para 800 cuadros). Se versiona su
receta de extraccion y su checksum. Cualquiera puede reconstruir bit a bit la
misma secuencia con lo que hay aqui.

---

## seq_vng2_f4000 — secuencia provisional de regresion

**Estado: PROVISIONAL.** Sirve como fixture de regresion —- misma entrada, misma
traza, que es lo unico que la prueba comprueba -— pero **no** es material de
captura fiel. Ver [H-07] en NOTAS_HALLAZGOS.md: el video de origen es un cuadro
**combinado** (post recorte de ROI, post brillo/contraste, ajustado a lienzo
estandar), no la salida cruda de la camara. Reemplazar por una grabacion de
camara cruda antes de publicar resultados.

| | |
|---|---|
| Origen | `out/v1.0.0_20260129_112833/20260129_195001_VNG_2.siev/video/raw_capture.mp4` |
| Paciente | registro de depuracion, datos ficticios (`fvdsfdsf dsfdsfsd`) |
| Fecha de captura | 2026-01-29 |
| Cuadros del origen | 21214 |
| Ventana extraida | n = 4000..4799 (800 cuadros) |
| Resolucion | 640x480, 8 bits, gris |
| Formato | PGM binario P5 |

**Comando de extraccion exacto** (va al manifiesto de corrida, es material, no
andamiaje):

```bash
ffmpeg -y -v error \
  -i out/v1.0.0_20260129_112833/20260129_195001_VNG_2.siev/video/raw_capture.mp4 \
  -vf "select='between(n\,4000\,4799)'" \
  -fps_mode passthrough \
  -pix_fmt gray -f image2 \
  fixtures/seq_vng2_f4000/%06d.pgm
```

**Version de ffmpeg:** `ffmpeg version n9.0.1 Copyright (c) 2000-2026 the FFmpeg developers`

`-pix_fmt gray` es obligatorio y se extrae directo a gris a proposito: si se
extrajera en color y se convirtiera despues, el coeficiente de luminancia podria
no coincidir con la ruta `zune-jpeg -> ColorSpace::Luma` de produccion, y esa
diferencia de **entrada** se confundiria con una diferencia de **algoritmo**.

El mismo criterio aplica a ExCuSe y ElSe cuando se incorporen: si vienen en PNG,
convertir a PGM gris con `-pix_fmt gray` y documentar el comando aqui.

**Verificar integridad:**

```bash
cd fixtures && sha256sum -c seq_vng2_f4000.sha256
```

---

## Que hace falta para la secuencia definitiva

Grabacion propia de depuracion, **desde la camara**, no desde un bundle:

- entre 500 y 1000 cuadros
- al menos un parpadeo completo
- al menos un evento de perdida seguido de recuperacion
- guardada como cuadros crudos de camara, antes de cualquier recorte de ROI o
  ajuste de brillo/contraste

Sin esos dos eventos la traza de referencia no ejercita la parte del estado
inter-cuadro que mas se movera en la Fase 3 (congelado por parpadeo, decaimiento
de velocidad, `lost_count`, reset del tracker).

---

## mascara_20261125 — grabacion cruda de la mascara (definitiva candidata)

Captura directa de la camara, **antes** de cualquier recorte o ajuste: es el
material que pedia la seccion anterior. No se versiona (gitignore `fixtures/*/`).

| | |
|---|---|
| Camara | USB GS CAM (`/dev/video2`), MJPEG sin recomprimir |
| Formato | 640x360 @ 210 fps nominal, 1348 cuadros en 6 s (~225 fps reales) |
| Sensor | exposicion automatica (aperture priority), gamma 300, brillo 16, contraste 35 |
| Contenido | mirada al frente, a los lados y parpadeos; voluntario del equipo |
| Fecha | 2026-11-25 |
| SHA-256 `crudo.mkv` | `5439d689fdbb98d097db2f69a9dccaad5a5ab5fc860c067d6e5e667646df44ba` |

Grabacion:

```bash
ffmpeg -f v4l2 -input_format mjpeg -video_size 640x360 -framerate 210 \
  -i /dev/video2 -t 6 -c:v copy fixtures/mascara_20261125/crudo.mkv
```

Cuadros PGM (misma regla de gris que arriba):

```bash
ffmpeg -i fixtures/mascara_20261125/crudo.mkv -fps_mode passthrough \
  -pix_fmt gray -f image2 fixtures/mascara_20261125/pgm/%06d.pgm
```

Analisis con la geometria de la app:

```bash
SIEV_GEOM_APP=1 SIEV_MEJORAS=reflejos,semilla SIEV_YOLO=<siev_iris_r01.onnx> \
  cargo run --release -p siev-tracking --example nistagmo_pgm -- fixtures/mascara_20261125/pgm 0 0
```

---

## mascara_20261125_2min — movimientos rapidos y apertura variable

Misma camara y formato que `mascara_20261125`. Exposicion automatica, gamma
265, brillo 22, contraste 31, nitidez 26. Mirada en todas las direcciones, a
distintas velocidades, con ojos entrecerrados, muy abiertos y parpadeos. Se
pidieron 2 min; la grabacion se detuvo a los 63,5 s.

| | |
|---|---|
| Cuadros | 14273 en 63,5 s (~225 fps) |
| SHA-256 `crudo.mkv` | `eee546680964ebb13fdc044123fef77844b96e863a1e635f3d3ef9bf60bbd05e` |

Mismos comandos de grabacion, extraccion y analisis que la seccion anterior
(`-t 120`, carpeta `mascara_20261125_2min`).
