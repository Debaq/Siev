#!/bin/bash
# SIEV Production Build Script (Unix)
set -e

echo "═══════════════════════════════════════════════════════"
echo "  SIEV Production Build"
echo "═══════════════════════════════════════════════════════"

# 1. Build Frontend
echo -e "\n[1/2] Building Frontend..."
cd frontend
npm install
npm run build
cd ..

# 2. Build Tauri Bundle
echo -e "\n[2/2] Building Tauri Production Bundle..."
cd src-tauri
# Ensure production dependencies are available
cargo build --release

# Intentar generar el AppImage, pero no detener el script si falla el bundling
# (Ya tenemos el binario compilado en target/release/siev)
if ! cargo tauri build; then
    echo -e "\n${RED}⚠ Advertencia: El empaquetado (bundling) falló.${NC}"
    echo -e "${YELLOW}Esto es común en Arch si falta fuse2 o appimagetool.${NC}"
    echo -e "${GREEN}No te preocupes, el binario SIEV fue compilado con éxito.${NC}"
fi
cd ..

# ---------------------------------------------------------
# Step 3: Archiving & Versioning
# ---------------------------------------------------------
echo -e "\n[3/3] Archiving build artifacts..."

VERSION=$(grep '"version":' src-tauri/tauri.conf.json | head -n 1 | awk -F'"' '{print $4}')
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUT_DIR="out/v${VERSION}_${TIMESTAMP}"

mkdir -p "$OUT_DIR"

# 1. Salvar Binario Standalone (El que realmente importa en Arch)
if [ -f "src-tauri/target/release/siev" ]; then
    cp "src-tauri/target/release/siev" "$OUT_DIR/siev_v${VERSION}"
    echo -e "✓ Binario puro guardado en $OUT_DIR"
    
    # Crear un Tarball comprimido (Formato universal para Linux)
    tar -czf "$OUT_DIR/SIEV_v${VERSION}_linux_x64.tar.gz" -C src-tauri/target/release siev
    echo -e "✓ Tarball (.tar.gz) creado en $OUT_DIR"
fi

# 2. Copiar bundles si existen (AppImage, etc)
if [ -d "src-tauri/target/release/bundle" ]; then
    cp -r src-tauri/target/release/bundle/* "$OUT_DIR/" 2>/dev/null || true
    echo -e "✓ Instaladores oficiales guardados en $OUT_DIR"
fi

echo -e "\n✅ Proceso finalizado en: ${OUT_DIR}"


