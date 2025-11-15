@echo off
setlocal enabledelayedexpansion
REM Update script for Tail Tagger (Windows)
REM Pulls latest code from git and updates Python dependencies

echo ================================
echo Tail Tagger - Update Script
echo ================================
echo.

REM Detect Python command
echo Detecting Python installation...
where py >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=py"
) else (
    where python >nul 2>&1
    if %errorlevel% equ 0 (
        set "PYTHON_CMD=python"
    ) else (
        echo Error: Python not found in PATH
        echo Please install Python 3.10-3.12 from python.org
        pause
        exit /b 1
    )
)

REM Display Python version
echo Found Python:
!PYTHON_CMD! --version
echo.

REM Check we're in the correct directory
if not exist "main.py" (
    echo Error: main.py not found
    echo Please run this script from the tail-tagger directory
    pause
    exit /b 1
)

REM Check if git is available
echo Checking for git...
where git >nul 2>&1
if errorlevel 1 (
    echo Error: Git not found in PATH
    echo Please install Git from https://git-scm.com/
    pause
    exit /b 1
)
echo Git found.
echo.

REM Check if venv exists
if not exist "venv\" (
    echo Error: Virtual environment not found
    echo Please run setup.bat first to create the environment
    pause
    exit /b 1
)

REM Check for uncommitted changes
echo Checking for uncommitted changes...
git status --porcelain > nul 2>&1
if errorlevel 1 (
    echo Error: Could not check git status
    pause
    exit /b 1
)

for /f %%i in ('git status --porcelain') do (
    echo.
    echo Error: You have uncommitted changes in your working directory
    echo Please commit or stash your changes before updating:
    echo   git add .
    echo   git commit -m "your message"
    echo Or to temporarily stash changes:
    echo   git stash
    echo.
    git status --short
    pause
    exit /b 1
)
echo No uncommitted changes found.
echo.

REM Check current branch
echo Checking current branch...
for /f "tokens=*" %%i in ('git branch --show-current') do set CURRENT_BRANCH=%%i
echo Current branch: %CURRENT_BRANCH%

if not "%CURRENT_BRANCH%"=="main" (
    echo.
    echo Warning: You are not on the main branch
    echo You are on: %CURRENT_BRANCH%
    echo The main branch typically has the latest stable updates
    echo.
    echo Press any key to continue updating %CURRENT_BRANCH% anyway, or Ctrl+C to cancel
    pause >nul
)
echo.

REM Pull latest changes
echo Pulling latest changes from git...
git pull
if errorlevel 1 (
    echo.
    echo Error: Git pull failed
    echo This could be due to:
    echo   - Network connectivity issues
    echo   - Merge conflicts
    echo   - Repository access issues
    echo.
    echo Please resolve any issues and try again
    pause
    exit /b 1
)
echo Git pull completed successfully.
echo.

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo Error: Failed to activate virtual environment
    echo Please run setup.bat to recreate the environment
    pause
    exit /b 1
)
echo.

REM Upgrade pip
echo Upgrading pip...
!PYTHON_CMD! -m pip install --upgrade pip
if errorlevel 1 (
    echo Warning: Failed to upgrade pip, continuing anyway...
)
echo.

REM Detect if GPU (CUDA) version is installed
echo Detecting current PyTorch configuration...
!PYTHON_CMD! -c "import torch; exit(0 if torch.cuda.is_available() else 1)" >nul 2>&1
if %errorlevel% equ 0 (
    set "REQUIREMENTS_FILE=requirements-cu128.txt"
    echo Detected GPU installation - will update CUDA dependencies
) else (
    set "REQUIREMENTS_FILE=requirements.txt"
    echo Detected CPU installation - will update CPU dependencies
)
echo.

REM Install/update requirements
echo Updating Python dependencies from %REQUIREMENTS_FILE%...
pip install -r %REQUIREMENTS_FILE%
if errorlevel 1 (
    echo.
    echo Error: Failed to install requirements
    echo Please check the error messages above
    echo.
    echo You may need to:
    echo   1. Check your internet connection
    echo   2. Run setup.bat to recreate the environment
    pause
    exit /b 1
)

echo.
echo ================================
echo Update completed successfully!
echo ================================
echo.
echo Your Tail Tagger installation is now up to date.
echo Run run.bat to start the application.
echo.
pause
