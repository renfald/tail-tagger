# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Tail Tagger App

This app is a desktop application built with PySide6 (Qt for Python) for tagging furry art images using the e621 tagging system. The application features optional machine learning model integration for auto-tagging suggestions.

## Build/Run Commands

```bash
# Recommended setup (automated):
# Windows: setup.bat
# Linux/Mac: ./setup.sh

# Run the application:
# Windows: run.bat  
# Linux/Mac: ./run.sh

# Manual setup (if needed):
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install -r requirements.txt
python main.py
```

## Project Architecture

### Core Components

1. **MainWindow** (`main.py`)
   - Orchestrates the application flow
   - Manages image loading and navigation
   - Coordinates tag management across panels
   - Handles file operations for saving/loading tags

2. **Tag Model** (`tag_list_model.py`)
   - Stores all tags in `TagData` objects
   - Manages tag selection state
   - Implements search functionality
   - Tracks tag usage statistics

3. **Classifier System** (`classifier_manager.py`, `classifier_panel.py`)
   - Handles image analysis using machine learning models
   - Supports multiple classifier models
   - Processes model output with confidence thresholds
   - Runs analysis in background threads

4. **Panel System**
   - Left panel container (`left_panel_container.py`) manages multiple panels:
     - Tag search panel (`tag_search_panel.py`)
     - Frequently used panel (`frequently_used_panel.py`)
     - Classifier panel (`classifier_panel.py`)
     - Favorites panel (`favorites_panel.py`)
   - Center panel (`center_panel.py`) for image display
   - Right panel for selected tags (`selected_tags_panel.py`)

5. **Configuration and Persistence**
   - `config_manager.py` - Manages application configuration
   - `file_operations.py` - Handles file I/O operations
   - Data stored in JSON files under `data/`

### Data Flow

1. Images are loaded from a selected folder
2. Tags can be selected manually or suggested by the classifier
3. Tags are stored in both:
   - Memory during runtime (via TagData objects)
   - JSON workfiles for persistence
4. Tag changes trigger UI updates via the observer pattern and Qt signals

## Key Implementation Details

### Tag Management

- Tags are stored as `TagData` objects with properties like `name`, `selected`, `favorite`
- Tag names are stored with underscores internally (`tag_name`) but displayed with spaces ("tag name")
- The `TagListModel` manages all tags and provides methods to get/set tag states
- Each panel displays tags in different groupings (search results, favorites, etc.)

### Classifier System

- Machine learning models are located in the `classifiers/` directory
- Each model has:
  - A weights file (`.safetensors`) 
  - A tags mapping file (`tags.json`)
- Analysis is performed asynchronously using QThreadPool
- Confidence threshold is user-adjustable

### UI Component Relationships

- `MainWindow` is the parent for all major panels
- `LeftPanelContainer` manages multiple tag selection panels
- `TagWidget` instances represent individual tags and handle selection/favorite toggling
- Panels observe model changes and update their displays accordingly

## Bulk Operations Architecture

### Current Implementation

**Tag Bulk Operations** (`tail_tagger/bulk_operations/`):
- Right-click context menu operations on tags
- Three operations: Add to Beginning, Add to End, Remove from All
- `BulkOperationsManager` handles core logic (direct workfile manipulation)
- `TagBulkOperationDialog` provides progress feedback and results
- `BulkOperationWorker` runs operations in background thread
- Operations are typically sub-second even on 1000+ images
- Backups created in `staging/backups/` before modifications

### Future Extensibility

**Architecture Layers for Future Bulk Tools:**

1. **Setup/Configuration Layer** (tool-specific dialogs):
   - `tail_tagger/bulk_operations/tag_operations_dialog.py` - Current right-click tag operations
   - Future: `tail_tagger/tag_sorter/` - UI for ranking/ordering tags across dataset
   - Future: `tail_tagger/find_replace_tags/` - Pattern-based tag find/replace with preview
   - Future: `tail_tagger/bulk_classifier/` - Batch image analysis configuration

2. **Execution Layer** (reusable):
   - `tail_tagger/bulk_operations/manager.py` - Core operations that manipulate workfiles
   - `BulkOperationWorker` - Generic threaded execution (in tag_operations_dialog.py)
   - Common utilities like `ensure_workfile_complete()` in `file_operations.py`

3. **Progress/Results Layer**:
   - Tool-specific dialogs show their own progress and results
   - Consider extracting `ProgressDialog` base class when second tool is added
   - Threading pattern is established and reusable

**Design Principles:**
- Each bulk tool gets its own file with clear naming
- Share common operations via `BulkOperationsManager`
- Use background threads for any disk I/O operations
- Create backups before modifying data
- Provide clear progress feedback and result summaries

**Avoid:**
- Don't make `tag_operations_dialog.py` a catch-all for all bulk operations
- Don't create a generic dialog that handles every tool (becomes a God Class)
- Each tool should be self-contained with its own UI and result formatting

### File Structure

```
tail_tagger/                    # Application package
├── __init__.py
└── bulk_operations/            # Bulk operations module
    ├── __init__.py             # Exports BulkOperationsManager, TagBulkOperationDialog, etc.
    ├── manager.py              # Core logic for bulk tag operations
    └── tag_operations_dialog.py # UI for right-click tag operations
```

Import style:
```python
from tail_tagger.bulk_operations import BulkOperationsManager, TagBulkOperationDialog
```

## File Format Information

- `config.json`: Application settings (last folder, model ID, threshold)
- `favorites.json`: List of favorite tag names
- `usage_data.json`: Counter of tag usage frequency
- Tag files: Comma-separated tag lists stored as .txt files
- Workfiles: JSON files mapping image paths to their tags