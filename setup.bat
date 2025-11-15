@echo off
setlocal enabledelayedexpansion
REM Tail Tagger Setup Script for Windows
REM This script sets up the virtual environment and installs dependencies

echo === Tail Tagger Setup ===
echo Setting up your environment...

REM Determine which python command to use
set "PYTHON_CMD=py"
%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 (
    set "PYTHON_CMD=python"
    !PYTHON_CMD! --version >nul 2>&1
    if errorlevel 1 (
        echo Error: Python is not installed or not in PATH.
        echo Please install Python 3.11 from python.org and try again.
        echo The 'py' launcher is recommended.
        pause
        exit /b 1
    )
)

REM Display Python version
for /f "tokens=*" %%i in ('!PYTHON_CMD! --version') do set PYTHON_VERSION=%%i
echo Found !PYTHON_VERSION!

REM Check if we're in the right directory
if not exist "main.py" (
    echo Error: main.py not found
    echo Please run this script from the Tail Tagger directory
    pause
    exit /b 1
)

REM Remove existing venv if it exists
if exist "venv" (
    echo Removing existing virtual environment...
    rmdir /s /q venv
)

REM Create virtual environment
echo Creating virtual environment...
!PYTHON_CMD! -m venv venv

if errorlevel 1 (
    echo Error: Failed to create virtual environment
    echo Make sure you have a complete Python installation
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

if errorlevel 1 (
    echo Error: Failed to activate virtual environment
    pause
    exit /b 1
)

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Prompt for GPU acceleration before installing dependencies
echo.
set /p USE_GPU="Enable GPU acceleration (NVIDIA only)? Requires a recent NVIDIA driver. [Y/N]: "
if /I "%USE_GPU%"=="Y" (
    set "REQ_FILE=requirements-cu128.txt"
) else (
    set "REQ_FILE=requirements.txt"
)

REM Install requirements based on choice
echo Installing dependencies from %REQ_FILE% ...
if exist "%REQ_FILE%" (
    pip install -r "%REQ_FILE%"
    if errorlevel 1 (
        echo Error: Failed to install dependencies from %REQ_FILE%
        echo Check the error messages above and try again
        pause
        exit /b 1
    )
) else (
    echo Error: %REQ_FILE% not found
    pause
    exit /b 1
)

REM Test the installation
echo Testing installation...
python -c "import PySide6; print('PySide6 imported successfully')" 2>nul
if errorlevel 1 (
    echo Warning: PySide6 import failed - there may be an issue with the installation
)

python -c "import torch; print('PyTorch imported successfully')" 2>nul
if errorlevel 1 (
    echo Warning: PyTorch import failed - AI features may not work
)

echo.
echo Setup complete!
echo.
echo Next steps:
echo 1. [Optional] Download AI models following instructions in classifiers\*\DOWNLOAD_INSTRUCTIONS.md
echo 2. Run the application with: run.bat
echo.
echo The application works perfectly without AI models for manual tagging.
echo.
pause