#!/usr/bin/env bash
# Simple local build helper using PyInstaller
set -euo pipefail

if ! command -v pyinstaller >/dev/null 2>&1; then
  python3 -m pip install --upgrade pip
  pip3 install pyinstaller
fi

pyinstaller --onefile main.py --name ageticker

echo "Built executable in dist/ageticker (or ageticker.exe on Windows)"

