@echo off
title Building MacroForge Installer...
echo ============================================
echo   MacroForge - Installer Builder
echo ============================================
echo.

echo [1/3] Installing Python dependencies...
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
    echo ERROR: PyInstaller build failed.
    pause
    exit /b 1
)

echo [3/3] Building installer with Inno Setup...

REM Try common Inno Setup install locations
set ISCC=""
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe"       set ISCC="C:\Program Files\Inno Setup 6\ISCC.exe"

if %ISCC%=="" (
    echo.
    echo ERROR: Inno Setup not found!
    echo Please download and install it from: https://jrsoftware.org/isdl.php
    echo Then run this script again.
    pause
    exit /b 1
)

%ISCC% MacroForge.iss
if errorlevel 1 (
    echo ERROR: Inno Setup compilation failed.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Done! Installer is in: installer_output\
echo ============================================
echo.
pause
