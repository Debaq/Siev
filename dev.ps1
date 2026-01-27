Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  SIEV Development Build & Setup (Windows)" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan

# ---------------------------------------------------------
# Step 0: Cleanup
# ---------------------------------------------------------
Write-Host "Cleaning up existing SIEV processes..." -ForegroundColor Yellow

# Kill processes safely
function Kill-ProcessSafe ($name) {
    Get-Process -Name $name -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
}

Kill-ProcessSafe "python"
Kill-ProcessSafe "siev"
Kill-ProcessSafe "node" # Be careful if running other node apps, but usually needed for Vite zombies

# Clean Python Cache
Write-Host "Cleaning up Python cache..." -ForegroundColor Yellow
Get-ChildItem -Path "backend" -Recurse -Filter "__pycache__" -Directory -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
Get-ChildItem -Path "backend" -Recurse -Filter "*.pyc" -File -ErrorAction SilentlyContinue | Remove-Item -Force

# ---------------------------------------------------------
# Step 1: Frontend
# ---------------------------------------------------------
Write-Host "`n[1/3] Building Frontend..." -ForegroundColor Cyan
Set-Location frontend

if (-not (Test-Path "node_modules")) {
    Write-Host "node_modules not found. Installing dependencies..." -ForegroundColor Yellow
    npm install
}

npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "Frontend build failed." -ForegroundColor Red
    exit 1
}
Write-Host "✓ Frontend built successfully" -ForegroundColor Green
Set-Location ..

# ---------------------------------------------------------
# Step 2: Rust Backend
# ---------------------------------------------------------
Write-Host "`n[2/3] Checking Rust backend..." -ForegroundColor Cyan
Set-Location src-tauri
cargo check
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Rust backend OK" -ForegroundColor Green
} else {
    Write-Host "⚠ Rust check failed. Trying to fetch..." -ForegroundColor Yellow
    cargo fetch
}
Set-Location ..

# ---------------------------------------------------------
# Step 3: Python Backend
# ---------------------------------------------------------
Write-Host "`n[3/3] Checking Python backend..." -ForegroundColor Cyan

try {
    python -c "import cv2, numpy, torch; print('Dependencies OK')" | Out-Null
    Write-Host "✓ Python dependencies OK" -ForegroundColor Green
} catch {
    Write-Host "⚠ Python dependencies missing or environment not active." -ForegroundColor Yellow
    Write-Host "Please ensure your Conda/Micromamba environment is active."
    Write-Host "Try: micromamba activate siev"
    
    $conf = Read-Host "Attempt to install requirements via pip? (Y/n)"
    if ($conf -match "^[Yy]") {
        pip install -r requirements.txt
    }
}

Write-Host "`n═══════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  Ready! Launching Tauri Dev Server..." -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════`n" -ForegroundColor Green

cargo tauri dev
