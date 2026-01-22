# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for SIEV Backend Sidecar
Builds the FastAPI server as a standalone executable for Tauri.
"""

import sys
from pathlib import Path

# Project paths
project_root = Path(SPECPATH)
src_path = project_root / 'backend'

# Collect data files
datas = [
    # YOLO model files
    (str(src_path / 'models' / '*.pt'), 'models'),
]

# Hidden imports for FastAPI and dependencies
hiddenimports = [
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'fastapi',
    'fastapi.responses',
    'fastapi.middleware',
    'fastapi.middleware.cors',
    'starlette',
    'starlette.responses',
    'starlette.routing',
    'starlette.middleware',
    'pydantic',
    'pydantic.fields',
    'multipart',
    'sse_starlette',
    # OpenCV and vision
    'cv2',
    'numpy',
    # PyTorch and YOLO
    'torch',
    'torchvision',
    'ultralytics',
    # Serial communication
    'serial',
    'serial.tools',
    'serial.tools.list_ports',
]

# Exclude unnecessary packages to reduce size
excludes = [
    'tkinter',
    'matplotlib',
    'PySide6',
    'PyQt6',
    'PyQt5',
    'pyqtgraph',
]

block_cipher = None

a = Analysis(
    [str(src_path / 'server.py')],
    pathex=[str(src_path)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='siev-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / 'src-tauri' / 'icons' / 'icon.ico') if (project_root / 'src-tauri' / 'icons' / 'icon.ico').exists() else None,
)
