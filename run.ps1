# SIEV - Universal Windows Launcher
$ErrorActionPreference = "Continue"

Write-Host "SIEV - Launcher" -ForegroundColor Cyan

# 1. Check for Release Binary
$RELEASE_BIN = "src-tauri\target\release\siev.exe"
if (Test-Path $RELEASE_BIN) {
    Write-Host "Launching release binary..." -ForegroundColor Green
    Start-Process $RELEASE_BIN
    exit
}

# 2. Check for MSI/EXE Installer (if already installed)
# Standard installation path would go here, but for now we look in build artifacts
$INSTALLER = Get-ChildItem -Path "src-tauri\target\release\bundle\nsis\*.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($null -ne $INSTALLER) {
    Write-Host "Launching from bundle: $($INSTALLER.Name)" -ForegroundColor Green
    Start-Process $INSTALLER.FullName
    exit
}

# 3. Fallback to Dev Mode
if (Test-Path "src-tauri") {
    Write-Host "Release not found. Launching in development mode..." -ForegroundColor Yellow
    cargo tauri dev
} else {
    Write-Host "Error: No SIEV binary or source found." -ForegroundColor Red
    exit 1
}

