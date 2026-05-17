#!/bin/bash

# Tail Tagger Run Script for Linux/macOS
# This script activates the virtual environment and runs the application

# Find a suitable python command
if command -v py &> /dev/null; then
    PYTHON_CMD="py"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Error: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.11 and try again"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Error: Virtual environment not found"
    echo "Please run setup.sh first to set up the environment"
    exit 1
fi

# Check if main.py exists
if [ ! -f "main.py" ]; then
    echo "❌ Error: main.py not found"
    echo "Please run this script from the Tail Tagger directory"
    exit 1
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to activate virtual environment"
    echo "Try running setup.sh again to recreate the environment"
    exit 1
fi

# Run the application
echo "🚀 Starting Tail Tagger..."
$PYTHON_CMD main.py

# Check if the application exited with an error
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Application exited with an error"
    echo "If you're having issues:"
    echo "1. Try running setup.sh again"
    echo "2. Check that all model files are properly downloaded (if using AI features)"
    echo "3. Make sure your Python version is 3.11 or lower"
fi

exit 0