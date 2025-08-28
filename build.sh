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
    
    # Apply UPX compression if available
    if command -v upx &> /dev/null; then
        echo "📦 Compressing executable with UPX..."
        for exe in dist/AgeTicker dist/AgeTicker.exe; do
            if [ -f "$exe" ]; then
                original_size=$(stat -f%z "$exe" 2>/dev/null || stat -c%s "$exe" 2>/dev/null || echo "unknown")
                echo "Original size: $original_size bytes"
                
                # Try UPX compression with best settings
                if upx --best --lzma --force "$exe" 2>/dev/null; then
                    compressed_size=$(stat -f%z "$exe" 2>/dev/null || stat -c%s "$exe" 2>/dev/null || echo "unknown")
                    echo "✅ Compressed: $compressed_size bytes"
                    if [ "$original_size" != "unknown" ] && [ "$compressed_size" != "unknown" ]; then
                        savings=$((original_size - compressed_size))
                        percent=$((savings * 100 / original_size))
                        echo "💾 Space saved: $savings bytes ($percent%)"
                    fi
                else
                    echo "⚠️  UPX compression failed or minimal benefit"
                fi
            fi
        done
    else
        echo "ℹ️  UPX not available - install with: brew install upx (macOS) or apt install upx (Linux)"
    fi
    
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
