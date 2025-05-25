# Tail Tagger

A desktop application built with PySide6 for manual and AI-assisted image tagging, designed for the furry art community using the e621 tagging system. Features machine learning model integration for automatic tag suggestions and comprehensive tag management.

## Features

- **Manual Image Tagging**: Browse and tag images with the comprehensive e621 tag system
- **AI-Assisted Tagging**: Optional machine learning models provide intelligent tag suggestions
- **Tag Management**: Search, favorite, and track frequently used tags
- **Flexible Workflow**: Works with or without ML models - pure manual tagging supported
- **Persistent Data**: Saves tags, favorites, and usage statistics
- **Furry-Focused**: Designed specifically for furry art with e621-compatible tagging

## Installation

### Prerequisites

- Python 3.8 or higher
- Git

### Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/tail-tagger.git
   cd tail-tagger
   ```

2. **Create and activate a virtual environment:**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **[Optional] Download AI Models:**
   
   Tail Tagger works perfectly without AI models for manual tagging only. To enable AI-assisted tagging:
   
   - Visit [RedRocket/JointTaggerProject on Hugging Face](https://huggingface.co/RedRocket/JointTaggerProject)
   - Download model files following instructions in:
     - `classifiers/JTP_PILOT/DOWNLOAD_INSTRUCTIONS.md`
     - `classifiers/JTP_PILOT2/DOWNLOAD_INSTRUCTIONS.md`

## Usage

### Running the Application

```bash
python main.py
```

### Basic Workflow

1. **Load Images**: File → Open Folder to select a directory containing furry art
2. **Navigate**: Use arrow keys or Next/Previous buttons to browse images
3. **Manual Tagging**: 
   - Search for e621-compatible tags in the left panel
   - Click tags to select/deselect them
   - Use favorites panel for commonly used tags
4. **AI-Assisted Tagging** (if models installed):
   - Click "Analyze Image" for intelligent tag suggestions
   - Enable "Auto-Analyze" toggle for automatic analysis on image load
   - Adjust confidence threshold to filter suggestions
5. **Save Work**: Tags are automatically saved as you work
6. **Export**: File → Export Tags to save tag data for upload to e621 or other sites

### Interface Overview

- **Left Panel**: Tag search, frequently used tags, AI classifier controls, favorites
- **Center Panel**: Image display and navigation
- **Right Panel**: Currently selected tags for the active image

### AI Models

Tail Tagger supports two classifier models trained on furry art:
- **JTP_PILOT**: General-purpose furry art tagging model
- **JTP_PILOT2**: Enhanced version with improved accuracy

Models are optional - the app provides full manual tagging functionality without them.

## File Structure

```
├── main.py                 # Main application entry point
├── classifiers/           # AI model directory (download separately)
│   ├── JTP_PILOT/        # First classifier model files
│   └── JTP_PILOT2/       # Second classifier model files
├── data/                  # Application data (auto-generated)
│   ├── config.json       # User settings
│   ├── favorites.json    # Favorite tags
│   └── usage_data.json   # Tag usage statistics
├── resources/             # UI resources and icons
└── [various .py files]   # Application modules
```

## Configuration

Tail Tagger automatically creates configuration files in the `data/` directory:
- **config.json**: Application settings (last folder, model preferences, thresholds)
- **favorites.json**: User's favorite tags
- **usage_data.json**: Tag usage frequency tracking

## Troubleshooting

### Virtual Environment Issues

If you encounter problems with the virtual environment:

1. Delete the existing `venv` directory:
   ```bash
   # Windows
   rmdir /s /q venv
   
   # macOS/Linux
   rm -rf venv
   ```

2. Create a new virtual environment following the installation steps above

### GPU/CUDA Support

- Tail Tagger automatically detects and uses GPU acceleration if available
- Falls back gracefully to CPU if no GPU is detected
- For GPU support, ensure compatible CUDA drivers are installed

### Model Loading Issues

- Ensure model files are placed in the correct directories
- Check `DOWNLOAD_INSTRUCTIONS.md` files in classifier folders
- Restart the application after adding new models
- The app works fine without models for manual tagging

### WSL/Windows Path Issues

If using WSL with Windows:
- Ensure paths are correctly formatted for your environment
- For Windows drive access, use mount paths (e.g., `/mnt/c/...`)

## System Requirements

- **OS**: Windows 10/11, macOS 10.14+, or Linux
- **Python**: 3.8 or higher
- **RAM**: 4GB minimum (8GB+ recommended with AI models)
- **Storage**: 500MB for app + 3.5GB per AI model
- **GPU**: Optional, CUDA-compatible GPU for faster AI inference

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

## Credits

- AI models provided by [RedRocket/JointTaggerProject](https://huggingface.co/RedRocket/JointTaggerProject)
- Designed for the furry art community and e621 tagging system
- Built with PySide6, PyTorch, and other open-source libraries