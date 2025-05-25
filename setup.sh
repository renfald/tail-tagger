#!/bin/bash

# Tail Tagger Setup Script for Linux/macOS
# This script sets up the virtual environment and installs dependencies

echo "=== Tail Tagger Setup ==="
echo "Setting up your environment..."

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.8 or higher and try again"
    exit 1
fi

# Display Python version
PYTHON_VERSION=$(python3 --version)
echo "✓ Found $PYTHON_VERSION"

# Check if we're already in the right directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: main.py not found"
    echo "Please run this script from the Tail Tagger directory"
    exit 1
fi

# Remove existing venv if it exists
if [ -d "venv" ]; then
    echo "🗑️  Removing existing virtual environment..."
    rm -rf venv
fi

# Create virtual environment
echo "🔧 Creating virtual environment..."
python3 -m venv venv

if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to create virtual environment"
    echo "Make sure you have python3-venv installed:"
    echo "  Ubuntu/Debian: sudo apt install python3-venv"
    echo "  macOS: Should be included with Python"
    exit 1
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to activate virtual environment"
    exit 1
fi

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📦 Installing dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    
    if [ $? -ne 0 ]; then
        echo "❌ Error: Failed to install dependencies"
        echo "Check the error messages above and try again"
        exit 1
    fi
else
    echo "❌ Error: requirements.txt not found"
    exit 1
fi

# Test the installation
echo "🧪 Testing installation..."
python -c "import PySide6; print('✓ PySide6 imported successfully')" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Warning: PySide6 import failed - there may be an issue with the installation"
fi

python -c "import torch; print('✓ PyTorch imported successfully')" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Warning: PyTorch import failed - AI features may not work"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. [Optional] Download AI models following instructions in classifiers/*/DOWNLOAD_INSTRUCTIONS.md"
echo "2. Run the application with: ./run.sh"
echo ""
echo "The application works perfectly without AI models for manual tagging."