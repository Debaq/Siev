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
echo -e "\n${BLUE}[1/3] Building Frontend...${NC}"
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
echo -e "\n${BLUE}[2/3] Checking Rust backend...${NC}"
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
# Step 3: Python Backend
# ---------------------------------------------------------
echo -e "\n${BLUE}[3/3] Checking Python backend...${NC}"

check_python_deps() {
    python3 -c "import cv2, numpy, torch; print('Dependencies OK')" 2>/dev/null
}

if check_python_deps; then
    echo -e "${GREEN}✓ Python dependencies OK${NC}"
else
    echo -e "${YELLOW}⚠ Python dependencies missing.${NC}"
    
    # Check for managers
    if ! command -v micromamba >/dev/null 2>&1 && ! command -v conda >/dev/null 2>&1; then
        echo -e "${YELLOW}No Conda or Micromamba found.${NC}"
        ask_with_default "Install Micromamba now?" "Y" INSTALL_MAMBA
        if [[ "$INSTALL_MAMBA" =~ ^[Yy] ]]; then
            echo "Installing Micromamba..."
            "${SHELL}" <(curl -L micro.mamba.pm/install.sh)
            # Attempt to add to PATH if installed to default location
            [ -f "$HOME/.local/bin/micromamba" ] && export PATH="$HOME/.local/bin:$PATH"
        fi
    fi
    
    ask_with_default "Setup/Activate Python environment?" "Y" SETUP_ENV
    
    if [[ "$SETUP_ENV" =~ ^[Yy] ]]; then
        # Determine default manager
        DEF_MGR="micromamba"
        if ! command -v micromamba >/dev/null 2>&1 && command -v conda >/dev/null 2>&1; then
            DEF_MGR="conda"
        fi

        ask_with_default "Manager [micromamba/conda]?" "$DEF_MGR" MGR
        ask_with_default "Environment name?" "siev" ENV_NAME
        
        # 1. Initialize Shell Hook
        if command -v $MGR >/dev/null 2>&1; then
            if [ "$MGR" = "micromamba" ]; then
                eval "$(micromamba shell hook --shell bash)"
            else
                eval "$(conda shell.bash hook)"
            fi
        else
            echo -e "${RED}✗ $MGR not found in PATH.${NC}"
            exit 1
        fi

        # 2. Try Activate
        echo "Attempting to activate '$ENV_NAME'..."
        if ! $MGR activate "$ENV_NAME" 2>/dev/null; then
            echo -e "${YELLOW}Environment '$ENV_NAME' not found.${NC}"
            
            ask_with_default "Create environment '$ENV_NAME'?" "Y" CREATE_ENV
            if [[ "$CREATE_ENV" =~ ^[Yy] ]]; then
                echo "Creating '$ENV_NAME' (python 3.10)..."
                # Use -y to confirm
                $MGR create -n "$ENV_NAME" python=3.10 -y
                
                echo "Activating..."
                $MGR activate "$ENV_NAME"
            fi
        fi
        
        # 3. Check Dependencies Again
        if check_python_deps; then
            echo -e "${GREEN}✓ Environment activated & dependencies OK${NC}"
        else
            echo -e "${YELLOW}Dependencies still missing in '$ENV_NAME'.${NC}"
            
            if [ -f "requirements.txt" ]; then
                ask_with_default "Install dependencies from requirements.txt?" "Y" INSTALL_DEPS
                if [[ "$INSTALL_DEPS" =~ ^[Yy] ]]; then
                    echo "Checking for NVIDIA GPU..."
                    if ! (lspci | grep -i nvidia > /dev/null 2>&1) && ! command -v nvidia-smi &> /dev/null; then
                        echo -e "${YELLOW}No NVIDIA GPU detected. Installing CPU-only PyTorch...${NC}"
                        pip install "torch<2.10" torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
                    else
                         echo -e "${GREEN}NVIDIA GPU detected (or check skipped). Proceeding with standard install...${NC}"
                    fi

                    echo "Installing dependencies..."
                    pip install -r requirements.txt
                    
                    if check_python_deps; then
                        echo -e "${GREEN}✓ Dependencies installed successfully${NC}"
                    else
                        echo -e "${RED}✗ Dependencies check failed even after install.${NC}"
                    fi
                fi
            else
                echo -e "${RED}✗ requirements.txt not found in root.${NC}"
            fi
        fi
    fi
fi

echo -e "\n${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Ready! Launching Tauri Dev Server...${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}\n"

# Launch Tauri dev (using Cargo as fixed previously)
cargo tauri dev