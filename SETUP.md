# Setup Instructions

This document provides instructions for setting up and running the Image Tagger App.

## Prerequisites

- Python 3.8+ installed
- Git (for cloning the repository)

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/image_tagger_app_mk2.git
   cd image_tagger_app_mk2
   ```

2. Create a virtual environment:
   ```
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Running the Application

With the virtual environment activated, run:
```
python main.py
```

## Usage

1. Open a folder containing images using File > Open Folder
2. Navigate through images using arrow keys or the Next/Previous buttons
3. Add tags by:
   - Selecting from the list in the left panel
   - Using the search functionality 
   - Using the automatic classifier suggestions

4. Export tagged images using File > Export Tags

## Troubleshooting

### Virtual Environment Issues

If you encounter problems with the virtual environment:

1. Delete the existing `venv` directory:
   ```
   # Windows
   rmdir /s /q venv
   
   # macOS/Linux
   rm -rf venv
   ```

2. Create a new virtual environment following the installation steps above

### Package Installation Issues

If you encounter issues installing the packages:

- For GPU support, ensure you have compatible CUDA drivers installed for PyTorch
- If you don't need GPU support, you can install CPU-only versions of the packages

### WSL/Windows Path Issues

If using WSL with Windows and encountering path issues:
- Ensure paths are correctly formatted for the environment you're working in
- For image directories on Windows drives, use the appropriate mount path prefix (e.g., `/mnt/c/...`)