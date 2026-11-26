# Piso de hardware del VNG

Experimento para saber **qué nivel clínico soporta un PC**. Pasa una grabación
real de la máscara por el pipeline de seguimiento (sin dibujar), mide cuánto
cuesta cada cuadro y lo compara con el presupuesto de cada nivel.

| Nivel | fps | Presupuesto por cuadro |
|---|---|---|
| Clínico | 60 | 16,7 ms |
| vHIT básico | 90 | 11,1 ms |
| vHIT avanzado | 120 | 8,3 ms |
| Lujo | 220 | 4,5 ms |

Un nivel se cumple (`OK`) si decodificar el JPEG de la cámara y procesar el
cuadro usa **como mucho el 70 %** del presupuesto; el resto queda para la GUI y
el sistema. `justo` = entre 70 y 100 %; `NO` = no alcanza.

## Cómo correrlo

En un PC con el repo y Rust:

```bash
tools/piso/medir_piso.sh [ruta/a/siev_ojo_r03.bin]
```

En un PC viejo **sin Rust**: compilar el binario en otro equipo y copiar
`piso_vng`, el script, el modelo `.bin` y `fixtures/mascara_20261125_2min/crudo.mkv`
(con su `.sha256`) manteniendo la estructura de carpetas:

```bash
cargo build --release -p siev-tracking --example piso_vng
# copiar <target>/release/examples/piso_vng al PC viejo, y alli:
PISO_BIN=./piso_vng tools/piso/medir_piso.sh siev_ojo_r03.bin
```

El binario se compila para x86-64 genérico: corre en CPUs sin AVX2 y, si la
CPU tiene AVX2+FMA, la red lo detecta y lo usa sola. Necesita `ffmpeg`.

El script:
1. verifica `crudo.mkv` con su SHA-256 y, si faltan, reconstruye los PGM (una vez, ~3 GB);
2. extrae 500 JPEG originales de la cámara para medir la decodificación;
3. corre cada configuración dos veces (`PISO_VUELTAS`): sin IA, IA en recorte
   64x64, IA forzando la ruta sin AVX2 (si la CPU tiene AVX2) e IA cada 3 cuadros;
4. guarda el resultado con los datos del equipo en `tools/piso/resultados/`.

**Medir con el equipo en reposo y enchufado.** Con otros programas pesados
abiertos (carga ~15) los tiempos salieron 4 veces más altos. El script avisa si
la carga al inicio es mayor que 1,5.

## Referencia: Ryzen 7 PRO 4750U (2026-11-26)

Portátil de 15 W, 16 hilos, AVX2, enchufado, governor `performance`, carga baja.
640x360 MJPEG, modelo `siev_ojo_r03`.

| Parte | ms por cuadro |
|---|---|
| Decodificar el JPEG de la cámara | 0,45 |
| Pipeline sin IA (detector clásico, tracking, lectura del PGM) | 0,7 - 1,0 |
| Pipeline con IA r03 en recorte | ~1,3 |
| Pipeline con IA, forzando la ruta sin AVX2 | 1,5 - 2,3 |
| **Total con IA** | **~1,8** (≈ 390 fps sostenibles) |

Los cuatro niveles `OK`. Los dos ojos en paralelo (`SIEV_IA_PARALELO=1`) no
mejoran con el recorte: crear el hilo cuesta lo que ahorra.

## Piso estimado (sin medir aún)

Escalando por el rendimiento mono-hilo respecto al 4750U, y usando la ruta sin
AVX2 para las CPUs que no la tienen:

| Nivel | CPU mínima estimada | Ejemplos |
|---|---|---|
| 60 fps clínico | ~40 % del 4750U, sin AVX2 sirve | Celeron N4020, Pentium Silver |
| 90 fps vHIT básico | ~40-50 % | Celeron N4020 (justo), Pentium Silver |
| 120 fps vHIT avanzado | ~60 % | Intel N100, i3 de 6.ª generación o posterior |
| 220 fps lujo | ~85 % o más | Ryzen 4000 / Intel de 10.ª generación o posterior |

**Pendiente:** confirmar esta tabla corriendo el script en equipos reales de
gama baja; medir el costo de la GUI (egui) en iGPU débiles, que este
experimento no incluye; y, para resoluciones mayores, adaptar la reducción de
la imagen antes de la IA para que el iris le llegue del mismo tamaño (el JPEG
y el detector clásico crecen con los píxeles; la IA en recorte no).
