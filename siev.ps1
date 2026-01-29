# SIEV - Script principal de desarrollo y build (PowerShell)
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDir

# ─────────────────────────────────────────────────────────
# Funciones auxiliares
# ─────────────────────────────────────────────────────────

function Write-Color {
    param(
        [string]$Text,
        [ConsoleColor]$Color = "White"
    )
    Write-Host $Text -ForegroundColor $Color
}

function Cleanup-Processes {
    Write-Color "Limpiando procesos SIEV existentes..." Yellow
    Get-Process -Name "siev*" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Get-Process -Name "SIEV*" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
}

function Check-Cameras {
    Write-Color "Verificando dispositivos de video..." Yellow

    # En Windows verificamos procesos que usen la webcam via WMI
    try {
        $camProcesses = Get-Process | Where-Object {
            try {
                $_.Modules | Where-Object { $_.ModuleName -match "webcam|camera|video" }
            } catch { $false }
        } -ErrorAction SilentlyContinue

        if ($camProcesses) {
            Write-Color "Procesos posiblemente usando cámara:" Red
            $camProcesses | Format-Table Id, ProcessName, MainWindowTitle -AutoSize

            $answer = Read-Host "Matar estos procesos para liberar camaras? (S/n)"
            if (-not $answer) { $answer = "S" }

            if ($answer -match "^[SsYy]") {
                $camProcesses | Stop-Process -Force -ErrorAction SilentlyContinue
                Write-Color "  Camaras liberadas." Green
            } else {
                Write-Color "  Saltando. La app podria no acceder a la camara." Yellow
            }
        } else {
            Write-Color "  No hay dispositivos de video ocupados." Green
        }
    } catch {
        Write-Color "  No se pudo verificar camaras." DarkGray
    }
}

function Install-Deps {
    Write-Host ""
    Write-Color "-- Instalando dependencias --" Blue

    Write-Host "[npm] " -ForegroundColor Cyan -NoNewline
    Write-Host "Instalando dependencias del frontend..."
    Set-Location "$ScriptDir\frontend"
    npm install
    Write-Color "  Frontend OK" Green
    Set-Location $ScriptDir

    Write-Host "[cargo] " -ForegroundColor Cyan -NoNewline
    Write-Host "Verificando dependencias de Rust..."
    Set-Location "$ScriptDir\src-tauri"
    cargo fetch
    if ($LASTEXITCODE -eq 0) {
        Write-Color "  Rust OK" Green
    } else {
        Write-Color "  Error al obtener crates de Rust." Red
        exit 1
    }
    Set-Location $ScriptDir

    Write-Color "  Todas las dependencias instaladas." Green
}

function Build-Frontend {
    Write-Host "[npm] " -ForegroundColor Cyan -NoNewline
    Write-Host "Compilando frontend..."
    Set-Location "$ScriptDir\frontend"

    if (-not (Test-Path "node_modules")) {
        Write-Color "  node_modules no encontrado, instalando..." Yellow
        npm install
    }

    npm run build
    if ($LASTEXITCODE -ne 0) {
        Write-Color "  Error compilando frontend." Red
        Set-Location $ScriptDir
        exit 1
    }
    Write-Color "  Frontend compilado." Green
    Set-Location $ScriptDir
}

function Run-Dev {
    param([switch]$Release)

    Write-Host ""
    Write-Color "=======================================================" Green
    if ($Release) {
        Write-Color "  Lanzando Tauri Dev (RELEASE - Alta Velocidad)" Green
    } else {
        Write-Color "  Lanzando Tauri Dev (DEBUG)" Green
    }
    Write-Color "=======================================================" Green
    Write-Host ""

    if ($Release) {
        cargo tauri dev --release
    } else {
        cargo tauri dev
    }
}

function Clean-All {
    Write-Host ""
    Write-Color "-- Limpieza completa --" Yellow

    Write-Host "[npm] " -ForegroundColor Cyan -NoNewline
    Write-Host "Eliminando node_modules..."
    if (Test-Path "$ScriptDir\frontend\node_modules") {
        Remove-Item -Recurse -Force "$ScriptDir\frontend\node_modules"
    }
    if (Test-Path "$ScriptDir\frontend\dist") {
        Remove-Item -Recurse -Force "$ScriptDir\frontend\dist"
    }

    Write-Host "[cargo] " -ForegroundColor Cyan -NoNewline
    Write-Host "cargo clean..."
    Set-Location "$ScriptDir\src-tauri"
    cargo clean
    Set-Location $ScriptDir

    Write-Color "  Limpieza completada." Green
}

function Do-Build {
    Write-Host ""
    Write-Color "-- Build de Produccion --" Blue

    Build-Frontend

    Write-Host "[cargo] " -ForegroundColor Cyan -NoNewline
    Write-Host "Compilando binario release..."
    Set-Location "$ScriptDir\src-tauri"
    cargo build --release

    cargo tauri build
    if ($LASTEXITCODE -ne 0) {
        Write-Color "  El bundling fallo. El binario fue compilado correctamente." Yellow
    }
    Set-Location $ScriptDir

    # Archivado
    $tauriConf = Get-Content "$ScriptDir\src-tauri\tauri.conf.json" -Raw | ConvertFrom-Json
    $version = $tauriConf.version
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $outDir = "$ScriptDir\out\v${version}_${timestamp}"

    New-Item -ItemType Directory -Force -Path $outDir | Out-Null

    $releaseBin = "$ScriptDir\src-tauri\target\release\siev.exe"
    if (Test-Path $releaseBin) {
        Copy-Item $releaseBin "$outDir\siev_v${version}.exe"
        Write-Color "  Binario guardado en $outDir" Green
    }

    $bundleDir = "$ScriptDir\src-tauri\target\release\bundle"
    if (Test-Path $bundleDir) {
        Copy-Item -Recurse "$bundleDir\*" $outDir -ErrorAction SilentlyContinue
        Write-Color "  Bundles copiados a $outDir" Green
    }

    Write-Host ""
    Write-Color "  Build finalizado: $outDir" Green
}

# ─────────────────────────────────────────────────────────
# Menu interactivo
# ─────────────────────────────────────────────────────────

function Show-Menu {
    Write-Host ""
    Write-Color "=======================================================" White
    Write-Host "  SIEV - Panel de Desarrollo" -ForegroundColor White
    Write-Color "=======================================================" White
    Write-Host ""
    Write-Host "  " -NoNewline; Write-Host "1)" -ForegroundColor Cyan -NoNewline; Write-Host " Instalar dependencias        " -NoNewline; Write-Host "(npm install + cargo fetch)" -ForegroundColor DarkGray
    Write-Host "  " -NoNewline; Write-Host "2)" -ForegroundColor Cyan -NoNewline; Write-Host " Dev rapido                    " -NoNewline; Write-Host "(lanzar sin limpiar)" -ForegroundColor DarkGray
    Write-Host "  " -NoNewline; Write-Host "3)" -ForegroundColor Cyan -NoNewline; Write-Host " Dev limpio                    " -NoNewline; Write-Host "(limpiar todo + dev)" -ForegroundColor DarkGray
    Write-Host "  " -NoNewline; Write-Host "4)" -ForegroundColor Cyan -NoNewline; Write-Host " Dev alta velocidad            " -NoNewline; Write-Host "(modo release)" -ForegroundColor DarkGray
    Write-Host "  " -NoNewline; Write-Host "5)" -ForegroundColor Cyan -NoNewline; Write-Host " Build produccion              " -NoNewline; Write-Host "(binario + bundle)" -ForegroundColor DarkGray
    Write-Host "  " -NoNewline; Write-Host "6)" -ForegroundColor Cyan -NoNewline; Write-Host " Limpiar todo                  " -NoNewline; Write-Host "(node_modules + cargo clean)" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  0) Salir" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  Selecciona una opcion [1-6]: " -NoNewline
}

# ─────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────

# Argumento directo
if ($args.Count -gt 0) {
    switch ($args[0]) {
        "install"   { Install-Deps; exit 0 }
        "dev"       { Cleanup-Processes; Check-Cameras; Run-Dev; exit 0 }
        "dev-clean" { Cleanup-Processes; Check-Cameras; Clean-All; Install-Deps; Run-Dev; exit 0 }
        "dev-fast"  { Cleanup-Processes; Check-Cameras; Run-Dev -Release; exit 0 }
        "build"     { Build-Frontend; Do-Build; exit 0 }
        "clean"     { Clean-All; exit 0 }
        default     { Write-Color "Argumento no reconocido: $($args[0])" Red; exit 1 }
    }
}

# Modo interactivo
while ($true) {
    Show-Menu
    $choice = Read-Host

    switch ($choice) {
        "1" { Install-Deps }
        "2" { Cleanup-Processes; Check-Cameras; Run-Dev }
        "3" { Cleanup-Processes; Check-Cameras; Clean-All; Install-Deps; Run-Dev }
        "4" { Cleanup-Processes; Check-Cameras; Run-Dev -Release }
        "5" { Do-Build }
        "6" { Clean-All }
        { $_ -in "0","q","Q" } { Write-Host "Hasta luego." -ForegroundColor DarkGray; exit 0 }
        default { Write-Color "  Opcion no valida." Red }
    }
}
