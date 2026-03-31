@echo off
title MACROFORGE
echo Installing dependencies...
pip install pynput >nul 2>&1
echo Starting MacroForge...
python macro_app.py
pause
