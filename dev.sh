#!/bin/bash
# SIEV Development Script
# Ensures all components are built before launching Tauri

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "═══════════════════════════════════════════════════════"
echo "  SIEV Development Build"
echo "═══════════════════════════════════════════════════════"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Step 1: Build Frontend
echo -e "\n${BLUE}[1/3]${NC} Building Frontend..."
cd frontend
if npm run build; then
    echo -e "${GREEN}✓ Frontend built successfully${NC}"
else
    echo -e "${RED}✗ Frontend build failed${NC}"
    exit 1
fi
cd ..

# Step 2: Check Rust compilation
echo -e "\n${BLUE}[2/3]${NC} Checking Rust backend..."
cd src-tauri
if cargo check 2>/dev/null; then
    echo -e "${GREEN}✓ Rust backend OK${NC}"
else
    echo -e "${YELLOW}⚠ Rust needs compilation (will compile on launch)${NC}"
fi
cd ..

# Step 3: Verify Python backend
echo -e "\n${BLUE}[3/3]${NC} Checking Python backend..."
if python3 -c "import cv2, numpy, torch; print('Dependencies OK')" 2>/dev/null; then
    echo -e "${GREEN}✓ Python dependencies OK${NC}"
else
    echo -e "${YELLOW}⚠ Some Python dependencies may be missing${NC}"
fi

echo -e "\n${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Ready! Launching Tauri Dev Server...${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}\n"

# Launch Tauri dev
npm run tauri dev
