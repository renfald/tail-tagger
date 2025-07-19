@echo off
REM Tail Tagger Run Script for Windows
REM This script activates the virtual environment and runs the application

REM Determine which python command to use
set "PYTHON_CMD=py"
%PYTHON_CMD% -V >nul 2>&1
if errorlevel 1 (
    set "PYTHON_CMD=python"
    %PYTHON_CMD% -V >nul 2>&1
    if errorlevel 1 (
        echo ❌ Error: Python is not installed or not in PATH.
        echo Please install Python 3.11 from python.org and try again.
        echo The 'py' launcher is recommended.
        pause
        exit /b 1
    )
)

REM Check if virtual environment exists
if not exist "venv" (
    echo ❌ Error: Virtual environment not found
    echo Please run setup.bat first to set up the environment
    pause
    exit /b 1
)

REM Check if main.py exists
if not exist "main.py" (
    echo ❌ Error: main.py not found
    echo Please run this script from the Tail Tagger directory
    pause
    exit /b 1
)

REM Activate virtual environment
echo 🔌 Activating virtual environment...
call venv\Scripts\activate.bat

if errorlevel 1 (
    echo ❌ Error: Failed to activate virtual environment
    echo Try running setup.bat again to recreate the environment
    pause
    exit /b 1
)

REM Run the application
echo 🚀 Starting Tail Tagger...
%PYTHON_CMD% main.py

REM Check if the application exited with an error
if errorlevel 1 (
    echo.
    echo ❌ Application exited with an error
    echo If you're having issues:
    echo 1. Try running setup.bat again
    echo 2. Check that all model files are properly downloaded ^(if using AI features^)
    echo 3. Make sure your Python version is 3.11 or lower
    echo.
    pause
)