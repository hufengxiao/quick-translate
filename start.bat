@echo off
cd /d "%~dp0"

:: Quick Translate - Windows Dictionary Tool
:: Apple HIG design, Spotlight-style experience

echo Starting Quick Translate...
python main.py
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to start. Make sure Python 3.10+ is installed.
    echo Download: https://www.python.org/downloads/
    echo.
    pause
)
