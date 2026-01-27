#!/bin/bash
# SIEV Production Build Script (Unix)
set -e

echo "═══════════════════════════════════════════════════════"
echo "  SIEV Production Build"
echo "═══════════════════════════════════════════════════════"

# 1. Build Frontend
echo -e "\n[1/2] Building Frontend..."
cd frontend
npm install
npm run build
cd ..

# 2. Build Tauri Bundle
echo -e "\n[2/2] Building Tauri Production Bundle..."
cd src-tauri
# Ensure production dependencies are available
cargo build --release
# Generate the installers (deb, appimage, etc.)
npm run tauri build
cd ..

echo -e "\n✅ Build completed! Check src-tauri/target/release/bundle/ for installers."
