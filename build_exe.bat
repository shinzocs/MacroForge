@echo off
title Building MACROFORGE.exe...
echo ================================
echo  MACROFORGE - EXE Builder
echo ================================
echo.

echo [1/3] Installing dependencies...
pip install pynput pyinstaller --quiet
if errorlevel 1 (
    echo ERROR: pip failed. Make sure Python is installed and in PATH.
    pause
    exit /b 1
)

echo [2/3] Building MACROFORGE.exe...
python -m PyInstaller --onefile --windowed --name MACROFORGE ^
  --icon=icon.ico ^
  --add-data "icon.png;." ^
  --hidden-import pynput.keyboard._win32 ^
  --hidden-import pynput.mouse._win32 ^
  macro_app.py

if errorlevel 1 (
    echo ERROR: Build failed. See above for details.
    pause
    exit /b 1
)

echo [3/3] Done!
echo.
echo Your MACROFORGE.exe is in the "dist" folder.
echo You can move it anywhere and run it directly.
echo.
pause
