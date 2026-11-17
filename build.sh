#!/usr/bin/env bash
# Build a standalone app for the current OS (macOS -> .app, Linux -> binary).
set -e
cd "$(dirname "$0")"
python3 -m pytest -q tests
python3 -m PyInstaller --noconfirm --windowed --name "StockPhotoSorter" --icon assets/icon.icns --add-data "assets:assets" app.py
echo "Built: dist/"
