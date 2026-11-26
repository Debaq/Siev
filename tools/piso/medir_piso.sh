#!/usr/bin/env bash
# Mide el piso de hardware del VNG en este PC (ver README.md de esta carpeta).
#
#   tools/piso/medir_piso.sh [modelo.bin]
#
# Variables:
#   PISO_BIN=<ruta a piso_vng>   binario ya compilado (PC sin Rust). Si no, se compila.
#   PISO_FIXTURE=<carpeta>       grabacion con crudo.mkv (defecto fixtures/mascara_20261125_2min)
#   PISO_VUELTAS=<n>             repeticiones de cada configuracion (defecto 2)
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/../.." && pwd)"
MODELO="${1:-$RAIZ/../siev_vng_models/siev_ojo_r03.bin}"
FIX="${PISO_FIXTURE:-$RAIZ/fixtures/mascara_20261125_2min}"
VUELTAS="${PISO_VUELTAS:-2}"
SALIDA_DIR="$RAIZ/tools/piso/resultados"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

[ -f "$MODELO" ] || { echo "falta el modelo: $MODELO" >&2; exit 1; }
[ -f "$FIX/crudo.mkv" ] || { echo "falta $FIX/crudo.mkv" >&2; exit 1; }
command -v ffmpeg >/dev/null || { echo "falta ffmpeg" >&2; exit 1; }

# 1) material de entrada: verificar la grabacion y reconstruir los PGM si faltan
if [ -f "$FIX/crudo.mkv.sha256" ]; then
    (cd "$FIX" && sha256sum -c --quiet crudo.mkv.sha256) || { echo "crudo.mkv no coincide con su sha256" >&2; exit 1; }
fi
if [ ! -d "$FIX/pgm" ] || [ -z "$(ls -A "$FIX/pgm" 2>/dev/null)" ]; then
    echo "reconstruyendo PGM desde crudo.mkv (una vez, ~3 GB)..."
    mkdir -p "$FIX/pgm"
    ffmpeg -v error -i "$FIX/crudo.mkv" -fps_mode passthrough -pix_fmt gray -f image2 "$FIX/pgm/%06d.pgm"
fi
mkdir -p "$TMP/jpg"
ffmpeg -v error -i "$FIX/crudo.mkv" -c:v copy -frames:v 500 "$TMP/jpg/%06d.jpg"

# 2) binario
if [ -n "${PISO_BIN:-}" ]; then
    BIN="$PISO_BIN"
else
    (cd "$RAIZ" && cargo build -q --release -p siev-tracking --example piso_vng)
    BIN="${CARGO_TARGET_DIR:-$RAIZ/target}/release/examples/piso_vng"
fi
[ -x "$BIN" ] || { echo "no encuentro el binario piso_vng: $BIN" >&2; exit 1; }

# 3) datos del equipo
CPU="$(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2 | sed 's/^ *//')"
AVX2="$(grep -qw avx2 /proc/cpuinfo && echo si || echo no)"
NUCLEOS="$(nproc)"
RAM="$(awk '/MemTotal/ {printf "%.1f GB", $2/1048576}' /proc/meminfo)"
GOV="$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo ?)"
AC="$(cat /sys/class/power_supply/A*/online 2>/dev/null | head -1 || echo ?)"
CARGA="$(cut -d' ' -f1 /proc/loadavg)"
mkdir -p "$SALIDA_DIR"
SLUG="$(echo "$CPU" | tr -cs 'A-Za-z0-9' '_' | sed 's/_*$//')"
OUT="$SALIDA_DIR/$(date +%Y%m%d_%H%M)_${SLUG}.txt"

{
    echo "# piso_vng $(date -Iseconds)"
    echo "CPU: $CPU | nucleos: $NUCLEOS | AVX2: $AVX2 | RAM: $RAM"
    echo "SO: $(uname -sr) | governor: $GOV | enchufado: $AC | carga al inicio: $CARGA"
    echo "modelo: $(basename "$MODELO") | grabacion: $(basename "$FIX")"
    echo
} | tee "$OUT"
if awk "BEGIN {exit !($CARGA > 1.5)}"; then
    echo "AVISO: carga del sistema $CARGA; cerrar otros programas o los numeros saldran inflados." | tee -a "$OUT"
fi

corre() {
    local nombre="$1"; shift
    local r
    r="$(env "$@" "$BIN" "$FIX/pgm" "$TMP/jpg" 2>/dev/null | sed -n '/=== piso/,$p')"
    {
        echo "## $nombre"
        echo "$r" | tail -n +2
        echo
    } | tee -a "$OUT"
}

for v in $(seq 1 "$VUELTAS"); do
    echo "=== vuelta $v ===" | tee -a "$OUT"
    corre "sin IA" X=1
    corre "IA recorte 64x64" SIEV_YOLO="$MODELO" SIEV_IA_CADA=1 SIEV_OJO_UMBRAL=0.5
    if [ "$AVX2" = si ]; then
        corre "IA recorte 64x64, forzando ruta sin AVX2" SIEV_YOLO="$MODELO" SIEV_IA_CADA=1 SIEV_OJO_UMBRAL=0.5 SIEV_OJO_SIN_AVX=1
    fi
    corre "IA recorte cada 3 cuadros" SIEV_YOLO="$MODELO" SIEV_IA_CADA=3 SIEV_OJO_UMBRAL=0.5
done

# 4) resumen: mejor total de cada configuracion entre vueltas (el ruido solo suma)
{
    echo "=== resumen (mejor de $VUELTAS vueltas) ==="
    awk '
        /^## / { conf = substr($0, 4) }
        /^total/ { t = $3 + 0; if (!(conf in mejor) || t < mejor[conf]) mejor[conf] = t; if (!(conf in orden)) orden[conf] = ++n }
        END {
            for (c in orden) lista[orden[c]] = c
            for (i = 1; i <= n; i++) {
                c = lista[i]; t = mejor[c]
                printf "%-42s %6.3f ms  ~%4.0f fps |", c, t, 700 / t
                split("60 90 120 220", f, " ")
                for (j = 1; j <= 4; j++) { u = t / (1000 / f[j]); printf " %s:%s", f[j], (u <= 0.7 ? "OK" : (u <= 1 ? "justo" : "NO")) }
                printf "\n"
            }
        }' "$OUT"
} | tee -a "$OUT"

echo "resultado guardado en $OUT"
