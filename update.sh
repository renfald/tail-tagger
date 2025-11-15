#!/bin/bash
# Update script for Tail Tagger (Linux/macOS)
# Pulls latest code from git and updates Python dependencies

echo "================================"
echo "Tail Tagger - Update Script"
echo "================================"
echo ""

# Detect Python command
echo "🔍 Detecting Python installation..."
if command -v py &> /dev/null; then
    PYTHON_CMD="py"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Error: Python not found in PATH"
    echo "Please install Python 3.10-3.12"
    exit 1
fi

# Display Python version
echo "Found Python:"
$PYTHON_CMD --version
echo ""

# Check we're in the correct directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: main.py not found"
    echo "Please run this script from the tail-tagger directory"
    exit 1
fi

# Check if git is available
echo "🔍 Checking for git..."
if ! command -v git &> /dev/null; then
    echo "❌ Error: Git not found in PATH"
    echo "Please install Git using your package manager"
    exit 1
fi
echo "✓ Git found."
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Error: Virtual environment not found"
    echo "Please run ./setup.sh first to create the environment"
    exit 1
fi

# Check for uncommitted changes
echo "🔍 Checking for uncommitted changes..."
git status --porcelain > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ Error: Could not check git status"
    exit 1
fi

if [ -n "$(git status --porcelain)" ]; then
    echo ""
    echo "❌ Error: You have uncommitted changes in your working directory"
    echo "Please commit or stash your changes before updating:"
    echo "  git add ."
    echo "  git commit -m \"your message\""
    echo "Or to temporarily stash changes:"
    echo "  git stash"
    echo ""
    git status --short
    exit 1
fi
echo "✓ No uncommitted changes found."
echo ""

# Check current branch
echo "🔍 Checking current branch..."
CURRENT_BRANCH=$(git branch --show-current)
echo "Current branch: $CURRENT_BRANCH"

if [ "$CURRENT_BRANCH" != "main" ]; then
    echo ""
    echo "⚠️  Warning: You are not on the main branch"
    echo "You are on: $CURRENT_BRANCH"
    echo "The main branch typically has the latest stable updates"
    echo ""
    read -p "Press Enter to continue updating $CURRENT_BRANCH anyway, or Ctrl+C to cancel..."
fi
echo ""

# Pull latest changes
echo "📥 Pulling latest changes from git..."
git pull
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Error: Git pull failed"
    echo "This could be due to:"
    echo "  - Network connectivity issues"
    echo "  - Merge conflicts"
    echo "  - Repository access issues"
    echo ""
    echo "Please resolve any issues and try again"
    exit 1
fi
echo "✓ Git pull completed successfully."
echo ""

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to activate virtual environment"
    echo "Please run ./setup.sh to recreate the environment"
    exit 1
fi
echo ""

# Upgrade pip
echo "📦 Upgrading pip..."
$PYTHON_CMD -m pip install --upgrade pip
if [ $? -ne 0 ]; then
    echo "⚠️  Warning: Failed to upgrade pip, continuing anyway..."
fi
echo ""

# Detect if GPU (CUDA) version is installed
echo "🔍 Detecting current PyTorch configuration..."
$PYTHON_CMD -c "import torch; exit(0 if torch.cuda.is_available() else 1)" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    REQUIREMENTS_FILE="requirements-cu128.txt"
    echo "✓ Detected GPU installation - will update CUDA dependencies"
else
    REQUIREMENTS_FILE="requirements.txt"
    echo "✓ Detected CPU installation - will update CPU dependencies"
fi
echo ""

# Install/update requirements
echo "📦 Updating Python dependencies from $REQUIREMENTS_FILE..."
pip install -r $REQUIREMENTS_FILE
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Error: Failed to install requirements"
    echo "Please check the error messages above"
    echo ""
    echo "You may need to:"
    echo "  1. Check your internet connection"
    echo "  2. Run ./setup.sh to recreate the environment"
    exit 1
fi

echo ""
echo "================================"
echo "✅ Update completed successfully!"
echo "================================"
echo ""
echo "Your Tail Tagger installation is now up to date."
echo "Run ./run.sh to start the application."
echo ""

exit 0
