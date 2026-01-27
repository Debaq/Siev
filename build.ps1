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
# Generate the installers (msi, exe)
npm run tauri build
Set-Location ..

Write-Host "
✅ Build completed! Check src-tauri\target\release\bundle\ for installers." -ForegroundColor Green
