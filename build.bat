@echo off
REM Build StockPhotoSorter.exe on Windows (run from this folder)
python -m pytest -q tests || exit /b 1
python -m PyInstaller --noconfirm --windowed --onefile --name StockPhotoSorter --icon assets\icon.ico --add-data "assets;assets" app.py
echo Built: dist\StockPhotoSorter.exe
