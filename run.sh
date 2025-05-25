#!/bin/bash

# Tail Tagger Run Script for Linux/macOS
# This script activates the virtual environment and runs the application

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
python main.py

# Check if the application exited with an error
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Application exited with an error"
    echo "If you're having issues:"
    echo "1. Try running setup.sh again"
    echo "2. Check that all model files are properly downloaded (if using AI features)"
    echo "3. Make sure your Python version is 3.8 or higher"
fi