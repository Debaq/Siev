#!/bin/bash
# SIEV - Script principal de desarrollo y build
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# ─────────────────────────────────────────────────────────
# Funciones auxiliares
# ─────────────────────────────────────────────────────────

cleanup_processes() {
    echo -e "${YELLOW}Limpiando procesos SIEV existentes...${NC}"
    # Matar procesos siev excluyendo este script y su shell
    local pids
    pids=$(pgrep -f "siev" | grep -v "^$$\$" | grep -v "^$PPID\$" || true)
    if [ -n "$pids" ]; then
        echo "$pids" | xargs kill 2>/dev/null || true
    fi
}

check_cameras() {
    echo -e "${YELLOW}Verificando dispositivos de video...${NC}"
    if ! command -v lsof >/dev/null 2>&1; then
        echo -e "${DIM}lsof no disponible, saltando verificación.${NC}"
        return
    fi

    local busy_cams=""
    if [ "$(uname -s)" = "Darwin" ]; then
        busy_cams=$(lsof | grep -E "AppleCamera|VDCAssistant" | grep -v "grep" || true)
    else
        busy_cams=$(lsof /dev/video* 2>/dev/null || true)
    fi

    if [ -z "$busy_cams" ]; then
        echo -e "${GREEN}  No hay dispositivos de video ocupados.${NC}"
        return
    fi

    echo -e "${RED}Procesos usando dispositivos de video:${NC}"
    echo "$busy_cams"
    local pids
    pids=$(echo "$busy_cams" | awk '{print $2}' | sort -u)

    if [ -n "$pids" ]; then
        echo -ne "${RED}¿Matar estos procesos para liberar cámaras? (S/n): ${NC}"
        read -r answer
        answer=${answer:-S}
        if [[ "$answer" =~ ^[SsYy] ]]; then
            echo "$pids" | xargs kill -9 2>/dev/null || true
            echo -e "${GREEN}  Cámaras liberadas.${NC}"
        else
            echo -e "${YELLOW}  Saltando. La app podría no acceder a la cámara.${NC}"
        fi
    fi
}

install_deps() {
    echo -e "\n${BLUE}── Instalando dependencias ──${NC}"

    echo -e "${CYAN}[npm]${NC} Instalando dependencias del frontend..."
    cd "$SCRIPT_DIR/frontend"
    npm install
    echo -e "${GREEN}  Frontend OK${NC}"
    cd "$SCRIPT_DIR"

    echo -e "${CYAN}[cargo]${NC} Verificando dependencias de Rust..."
    cd "$SCRIPT_DIR/src-tauri"
    if cargo fetch; then
        echo -e "${GREEN}  Rust OK${NC}"
    else
        echo -e "${RED}  Error al obtener crates de Rust.${NC}"
        exit 1
    fi
    cd "$SCRIPT_DIR"

    echo -e "${GREEN}  Todas las dependencias instaladas.${NC}"
}

build_frontend() {
    echo -e "${CYAN}[npm]${NC} Compilando frontend..."
    cd "$SCRIPT_DIR/frontend"
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}  node_modules no encontrado, instalando...${NC}"
        npm install
    fi
    npm run build
    echo -e "${GREEN}  Frontend compilado.${NC}"
    cd "$SCRIPT_DIR"
}

run_dev() {
    local release_flag="$1"
    echo -e "\n${GREEN}═══════════════════════════════════════════════════════${NC}"
    if [ "$release_flag" = "--release" ]; then
        echo -e "${GREEN}  Lanzando Tauri Dev (RELEASE - Alta Velocidad)${NC}"
    else
        echo -e "${GREEN}  Lanzando Tauri Dev (DEBUG)${NC}"
    fi
    echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}\n"
    cargo tauri dev $release_flag
}

clean_all() {
    echo -e "\n${YELLOW}── Limpieza completa ──${NC}"

    echo -e "${CYAN}[npm]${NC} Eliminando node_modules..."
    rm -rf "$SCRIPT_DIR/frontend/node_modules"
    rm -rf "$SCRIPT_DIR/frontend/dist"

    echo -e "${CYAN}[cargo]${NC} cargo clean..."
    cd "$SCRIPT_DIR/src-tauri"
    cargo clean
    cd "$SCRIPT_DIR"

    echo -e "${GREEN}  Limpieza completada.${NC}"
}

do_build() {
    echo -e "\n${BLUE}── Build de Producción ──${NC}"

    build_frontend

    echo -e "${CYAN}[cargo]${NC} Compilando binario release..."
    cd "$SCRIPT_DIR/src-tauri"
    cargo build --release

    if ! cargo tauri build; then
        echo -e "${YELLOW}  El bundling falló (común en Arch sin fuse2/appimagetool).${NC}"
        echo -e "${GREEN}  El binario fue compilado correctamente.${NC}"
    fi
    cd "$SCRIPT_DIR"

    # Archivado
    local version
    version=$(grep '"version":' "$SCRIPT_DIR/src-tauri/tauri.conf.json" | head -n 1 | awk -F'"' '{print $4}')
    local timestamp
    timestamp=$(date +"%Y%m%d_%H%M%S")
    local out_dir="$SCRIPT_DIR/out/v${version}_${timestamp}"

    mkdir -p "$out_dir"

    if [ -f "$SCRIPT_DIR/src-tauri/target/release/siev" ]; then
        cp "$SCRIPT_DIR/src-tauri/target/release/siev" "$out_dir/siev_v${version}"
        tar -czf "$out_dir/SIEV_v${version}_linux_x64.tar.gz" -C "$SCRIPT_DIR/src-tauri/target/release" siev
        echo -e "${GREEN}  Binario y tarball guardados en $out_dir${NC}"
    fi

    if [ -d "$SCRIPT_DIR/src-tauri/target/release/bundle" ]; then
        cp -r "$SCRIPT_DIR/src-tauri/target/release/bundle/"* "$out_dir/" 2>/dev/null || true
        echo -e "${GREEN}  Bundles copiados a $out_dir${NC}"
    fi

    echo -e "\n${GREEN}  Build finalizado: ${out_dir}${NC}"
}

# ─────────────────────────────────────────────────────────
# Menú interactivo
# ─────────────────────────────────────────────────────────

show_menu() {
    echo ""
    echo -e "${BOLD}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}  SIEV - Panel de Desarrollo${NC}"
    echo -e "${BOLD}═══════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${CYAN}1)${NC} Instalar dependencias        ${DIM}(npm install + cargo fetch)${NC}"
    echo -e "  ${CYAN}2)${NC} Dev rápido                    ${DIM}(lanzar sin limpiar)${NC}"
    echo -e "  ${CYAN}3)${NC} Dev limpio                    ${DIM}(limpiar todo + dev)${NC}"
    echo -e "  ${CYAN}4)${NC} Dev alta velocidad            ${DIM}(modo release)${NC}"
    echo -e "  ${CYAN}5)${NC} Build producción              ${DIM}(binario + bundle)${NC}"
    echo -e "  ${CYAN}6)${NC} Limpiar todo                  ${DIM}(node_modules + cargo clean)${NC}"
    echo ""
    echo -e "  ${DIM}0) Salir${NC}"
    echo ""
    echo -ne "${BOLD}  Selecciona una opción [1-6]: ${NC}"
}

# ─────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────

# Si se pasa argumento directo, ejecutar sin menú
case "${1:-}" in
    install)   install_deps; exit 0 ;;
    dev)       cleanup_processes; check_cameras; run_dev; exit 0 ;;
    dev-clean) cleanup_processes; check_cameras; clean_all; install_deps; run_dev; exit 0 ;;
    dev-fast)  cleanup_processes; check_cameras; run_dev "--release"; exit 0 ;;
    build)     build_frontend; do_build; exit 0 ;;
    clean)     clean_all; exit 0 ;;
esac

# Modo interactivo
while true; do
    show_menu
    read -r choice

    case "$choice" in
        1)
            install_deps
            ;;
        2)
            cleanup_processes
            check_cameras
            run_dev
            ;;
        3)
            cleanup_processes
            check_cameras
            clean_all
            install_deps
            run_dev
            ;;
        4)
            cleanup_processes
            check_cameras
            run_dev "--release"
            ;;
        5)
            do_build
            ;;
        6)
            clean_all
            ;;
        0|q|Q)
            echo -e "${DIM}Hasta luego.${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}  Opción no válida.${NC}"
            ;;
    esac
done
