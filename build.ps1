# SIEV Production Build Script (Windows)
$ErrorActionPreference = "Stop"

Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  SIEV Production Build" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan

# 1. Build Frontend
Write-Host "
[1/2] Building Frontend..." -ForegroundColor Cyan
Set-Location frontend
npm install
npm run build
Set-Location ..

# 2. Build Tauri Bundle
Write-Host "
[2/2] Building Tauri Production Bundle..." -ForegroundColor Cyan
Set-Location src-tauri
# Ensure production dependencies are available
cargo build --release
# Generate the installers (msi, exe) using the cargo plugin
cargo tauri build
Set-Location ..

# ---------------------------------------------------------
# Step 3: Archiving & Versioning
# ---------------------------------------------------------
Write-Host "
[3/3] Archiving build artifacts..." -ForegroundColor Cyan

# Extract version from tauri.conf.json
$tauriConfig = Get-Content "src-tauri/tauri.conf.json" -Raw | ConvertFrom-Json
$VERSION = $tauriConfig.version
$TIMESTAMP = Get-Date -Format "yyyyMMdd_HHmmss"
$OUT_DIR = "out/v${VERSION}_${TIMESTAMP}"

New-Item -ItemType Directory -Force -Path $OUT_DIR | Out-Null

# Move binary
$exePath = "src-tauri/target/release/siev.exe"
if (Test-Path $exePath) {
    Copy-Item $exePath -Destination "$OUT_DIR/siev_v${VERSION}.exe"
    Write-Host "✓ Binary saved to $OUT_DIR" -ForegroundColor Green
}

# Copy bundles (if they were generated)
$bundlePath = "src-tauri/target/release/bundle"
if (Test-Path $bundlePath) {
    Copy-Item -Path "$bundlePath/*" -Destination $OUT_DIR -Recurse -Force
    Write-Host "✓ Bundles saved to $OUT_DIR" -ForegroundColor Green
}

Write-Host "
✅ Build completed and archived in: ${OUT_DIR}" -ForegroundColor Green
