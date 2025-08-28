#!/bin/bash

# AgeTicker Build Script
# This script creates executables using PyInstaller

set -e

echo "=== AgeTicker Build Script ==="

# Check if PyInstaller is installed
PYINSTALLER_CMD="pyinstaller"
if ! command -v pyinstaller &> /dev/null; then
    # Try user local installation
    if [ -f "$HOME/Library/Python/3.9/bin/pyinstaller" ]; then
        PYINSTALLER_CMD="$HOME/Library/Python/3.9/bin/pyinstaller"
        echo "Using PyInstaller from: $PYINSTALLER_CMD"
    else
        echo "PyInstaller not found. Installing..."
        pip3 install -r requirements-build.txt
        PYINSTALLER_CMD="$HOME/Library/Python/3.9/bin/pyinstaller"
    fi
else
    echo "Using system PyInstaller"
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist __pycache__ *.spec~

# Create executable using spec file
echo "Building AgeTicker executable..."
$PYINSTALLER_CMD ageticker.spec

# Check if build was successful
if [ -f "dist/AgeTicker" ] || [ -f "dist/AgeTicker.exe" ]; then
    echo "✅ Build successful!"
    echo "Executable location: dist/"
    ls -la dist/
else
    echo "❌ Build failed!"
    exit 1
fi

echo ""
echo "=== Build Instructions ==="
echo "For Windows builds from macOS:"
echo "1. Use GitHub Actions (recommended) - see .github/workflows/build.yml"
echo "2. Use a Windows VM or machine with Python and PyInstaller installed"
echo "3. Cross-compilation from macOS has limited support"
echo ""
echo "To run the executable:"
echo "  ./dist/AgeTicker       (macOS/Linux)"
echo "  ./dist/AgeTicker.exe   (Windows)"
