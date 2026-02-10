@echo off
setlocal enabledelayedexpansion

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.9 or higher from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i

echo Found Python %PYTHON_VERSION%
echo Checking dependencies...

if not exist "requirements.txt" (
    echo ERROR: requirements.txt not found in the current directory.
    pause
    exit /b 1
)

echo Installing required packages...
python -m pip install --quiet --upgrade pip >nul 2>&1
python -m pip install --quiet -r requirements.txt >nul 2>&1

if %errorlevel% neq 0 (
    echo Warning: Some packages may have failed to install.
    echo Attempting to continue anyway...
)

if not exist "main.py" (
    echo ERROR: main.py not found in the current directory.
    pause
    exit /b 1
)

echo Launching Spotify AI Music Discovery...
start "" pythonw main.py

exit