#!/bin/bash
# SIEV Development Script
# Ensures all components are built before launching Tauri

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "═══════════════════════════════════════════════════════"
echo "  SIEV Development Build & Setup"
echo "═══════════════════════════════════════════════════════"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ---------------------------------------------------------
# Step 0: Cleanup
# ---------------------------------------------------------
echo -e "${YELLOW}Cleaning up existing SIEV processes...${NC}"
# Kill any existing tauri processes
pkill -f "siev" || true

# Check for busy cameras
echo -e "${YELLOW}Checking for busy video devices...${NC}"
if command -v lsof >/dev/null 2>&1; then
    OS_NAME=$(uname -s)
    BUSY_CAMS=""
    
    if [ "$OS_NAME" = "Darwin" ]; then
        # macOS detection
        BUSY_CAMS=$(lsof | grep -E "AppleCamera|VDCAssistant" | grep -v "grep" || true)
    else
        # Linux detection
        BUSY_CAMS=$(lsof /dev/video* 2>/dev/null || true)
    fi

    if [ -n "$BUSY_CAMS" ]; then
        echo -e "${RED}Warning: The following processes are using video devices:${NC}"
        echo "$BUSY_CAMS"
        
        # Extract unique PIDs (different parsing for Mac vs Linux usually, but awk prints column 2 for both)
        BUSY_PIDS=$(echo "$BUSY_CAMS" | awk '{print $2}' | sort -u)
        
        if [ -n "$BUSY_PIDS" ]; then
            echo -ne "${RED}Do you want to force kill these processes to free the cameras? (Y/n): ${NC}"
            read -r KILL_CAMS
            KILL_CAMS=${KILL_CAMS:-Y}
            
            if [[ "$KILL_CAMS" =~ ^[Yy] ]]; then
                echo "Killing processes: $BUSY_PIDS"
                echo "$BUSY_PIDS" | xargs kill -9 2>/dev/null || true
                echo -e "${GREEN}Cameras should be free now.${NC}"
            else
                echo -e "${YELLOW}Skipping camera cleanup. App might fail to access camera.${NC}"
            fi
        fi
    else
        echo -e "${GREEN}✓ No busy video devices found.${NC}"
    fi
else
    echo -e "${YELLOW}lsof not found, skipping camera check.${NC}"
fi

# Helper: Prompt with Timeout
ask_with_default() {
    # $1 = Prompt text, $2 = Default, $3 = Var Name
    local prompt="$1"
    local default="$2"
    local var_name="$3"
    local input
    
    echo -ne "$prompt (Default 5s: $default): "
    if read -t 5 -r input; then
        eval "$var_name=\"\${input:-$default}\""
    else
        echo "$default (Timeout)"
        eval "$var_name=\"$default\""
    fi
}

# ---------------------------------------------------------
# Step 1: Frontend (Vite/Node)
# ---------------------------------------------------------
echo -e "\n${BLUE}[1/2] Building Frontend...${NC}"
cd frontend

# Check if we need to install first
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}node_modules not found. Installing dependencies...${NC}"
    npm install
fi

# Try building
if npm run build; then
    echo -e "${GREEN}✓ Frontend built successfully${NC}"
else
    echo -e "${RED}✗ Frontend build failed.${NC}"
    ask_with_default "Attempt to fix by running 'npm install'?" "Y" FIX_NPM
    
    if [[ "$FIX_NPM" =~ ^[Yy] ]]; then
        echo "Running npm install..."
        npm install
        echo "Retrying build..."
        if npm run build; then
            echo -e "${GREEN}✓ Frontend built successfully (after fix)${NC}"
        else
            echo -e "${RED}✗ Frontend build failed again.${NC}"
            exit 1
        fi
    else
        exit 1
    fi
fi
cd ..

# ---------------------------------------------------------
# Step 2: Rust Backend (Tauri)
# ---------------------------------------------------------
echo -e "\n${BLUE}[2/2] Checking Rust backend...${NC}"
cd src-tauri
# Cargo automatically handles deps on build/check, but we can check connectivity/setup
if cargo check 2>/dev/null; then
    echo -e "${GREEN}✓ Rust backend OK${NC}"
else
    echo -e "${YELLOW}⚠ Rust check failed or dependencies missing.${NC}"
    echo "Compiling dependencies usually happens automatically."
    echo "Running 'cargo fetch' to verify network/crates..."
    if cargo fetch; then
        echo -e "${GREEN}✓ Crates fetched.${NC}"
    else
        echo -e "${RED}✗ Failed to fetch Rust crates.${NC}"
        # We don't exit here because sometimes check fails on code errors but fetch worked
    fi
fi
cd ..

# ---------------------------------------------------------
# Step 3: Final Launch
# ---------------------------------------------------------
ask_with_default "Launch in Release mode for maximum performance?" "N" RELEASE_MODE

echo -e "\n${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Ready! Launching Tauri Dev Server...${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}\n"

# Launch Tauri dev
if [[ "$RELEASE_MODE" =~ ^[Yy] ]]; then
    echo -e "${YELLOW}Running in RELEASE mode (High Performance)...${NC}"
    cargo tauri dev --release
else
    echo -e "${BLUE}Running in DEBUG mode...${NC}"
    cargo tauri dev
fi
