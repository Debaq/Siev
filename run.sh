#!/bin/bash
# SIEV - Universal Linux Runner
# Detects environment and launches the best available binary

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}SIEV - Launcher${NC}"

# 1. Check for Release Binary (Standard path)
RELEASE_BIN="./src-tauri/target/release/siev"
if [ -f "$RELEASE_BIN" ]; then
    echo -e "${GREEN}Launching release binary...${NC}"
    exec "$RELEASE_BIN"
fi

# 2. Check for AppImage (Generic Linux bundle)
APPIMAGE=$(find src-tauri/target/release/bundle/appimage/ -name "*.AppImage" | head -n 1)
if [ -n "$APPIMAGE" ] && [ -f "$APPIMAGE" ]; then
    echo -e "${GREEN}Launching AppImage: $APPIMAGE${NC}"
    chmod +x "$APPIMAGE"
    exec "$APPIMAGE"
fi

# 3. Fallback to Dev Mode (if source is available)
if [ -d "src-tauri" ]; then
    echo -e "${YELLOW}Release not found. Launching in development mode...${NC}"
    if command -v cargo >/dev/null 2>&1; then
        exec cargo tauri dev
    else
        echo -e "${RED}Error: Cargo not found. Please build the app first using ./build.sh${NC}"
        exit 1
    fi
fi

echo -e "${RED}Error: No SIEV binary or source found.${NC}"
exit 1
