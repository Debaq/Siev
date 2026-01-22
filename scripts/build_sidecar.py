#!/usr/bin/env python3
"""
Build script for SIEV Backend Sidecar
Creates a standalone executable from the FastAPI server.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path


def main():
    project_root = Path(__file__).parent.parent.absolute()
    dist_path = project_root / 'dist'
    binaries_path = project_root / 'src-tauri' / 'binaries'

    print("=" * 60)
    print("SIEV Backend Sidecar Build")
    print("=" * 60)

    # Ensure PyInstaller is installed
    print("\n[1/5] Checking dependencies...")
    try:
        import PyInstaller
        print(f"  PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print("  Installing PyInstaller...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'],
                       check=True)

    # Clean previous builds
    print("\n[2/5] Cleaning previous builds...")
    for path in [dist_path, project_root / 'build']:
        if path.exists():
            shutil.rmtree(path)
            print(f"  Removed: {path}")

    # Run PyInstaller
    print("\n[3/5] Running PyInstaller...")
    spec_file = project_root / 'sidecar.spec'

    result = subprocess.run([
        sys.executable, '-m', 'PyInstaller',
        '--clean',
        '--noconfirm',
        str(spec_file)
    ], cwd=project_root)

    if result.returncode != 0:
        print("\nERROR: PyInstaller failed!")
        sys.exit(1)

    # Verify the executable was created
    print("\n[4/5] Verifying build...")
    exe_name = 'siev-backend.exe' if sys.platform == 'win32' else 'siev-backend'
    exe_path = dist_path / exe_name

    if not exe_path.exists():
        print(f"\nERROR: Executable not found at {exe_path}")
        sys.exit(1)

    file_size = exe_path.stat().st_size / (1024 * 1024)  # MB
    print(f"  Executable: {exe_path}")
    print(f"  Size: {file_size:.1f} MB")

    # Copy to Tauri binaries directory
    print("\n[5/5] Installing to Tauri binaries...")
    binaries_path.mkdir(parents=True, exist_ok=True)

    # Tauri expects specific naming convention for sidecars
    # Format: <name>-<target-triple>
    if sys.platform == 'win32':
        target_triple = 'x86_64-pc-windows-msvc'
    elif sys.platform == 'darwin':
        import platform
        if platform.machine() == 'arm64':
            target_triple = 'aarch64-apple-darwin'
        else:
            target_triple = 'x86_64-apple-darwin'
    else:
        target_triple = 'x86_64-unknown-linux-gnu'

    target_name = f"siev-backend-{target_triple}"
    if sys.platform == 'win32':
        target_name += '.exe'

    target_path = binaries_path / target_name
    shutil.copy2(exe_path, target_path)
    print(f"  Installed: {target_path}")

    print("\n" + "=" * 60)
    print("BUILD SUCCESSFUL!")
    print("=" * 60)
    print(f"\nSidecar executable: {target_path}")
    print("\nNext steps:")
    print("  1. cd frontend && npm install && npm run build")
    print("  2. cd src-tauri && cargo tauri build")


if __name__ == '__main__':
    main()
