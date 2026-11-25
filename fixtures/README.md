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
