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

### Tests

```bash
pip install -r requirements-dev.txt   # pytest; the setup scripts don't install it
python -m pytest tests -q             # run from the repo root
```

The tests in `tests/` cover the plain helper modules: tag list rules (`tag_state.py`),
image sizing and decoding (`ui/image_loading.py`), where a dragged tag lands
(`ui/tag_rows.py`), and grid moves and keys (`ui/grid_nav.py`). They also cover the
thumbnail loader, the grid view widget, and the center panel going inactive under the grid.
`tests/conftest.py` runs Qt on the offscreen platform (no windows open) and provides a
`qapp` fixture for tests that need widgets or `QPixmap`. Tests that wait for background
decodes spin `processEvents()` with short sleeps: `QTest.qWait` keeps Python's lock, so
the decode threads would never run. Other panels have no automated tests, so also validate
UI changes by running the app (`run.bat` / `./run.sh`) and exercising the affected panels.

## Project Architecture

### File Layout

```
main.py                         # Entry point and MainWindow
tail_tagger/                    # Application package (APP_ROOT in __init__.py = repo root)
├── tag_list_model.py           # TagData + TagListModel
├── tag_state.py                # List rules for selected tags and favorites (no Qt)
├── file_operations.py          # Workfiles, .txt tags, favorites, usage data, export
├── config_manager.py           # config.json
├── ui/
│   ├── theme.py                # Dark palette + tag category colors
│   ├── keyboard_manager.py
│   ├── image_loading.py        # Image decode helpers + background decode worker
│   ├── tag_rows.py             # Tag row colors, text width, drop position (no Qt)
│   ├── grid_nav.py             # Grid view row moves, key decisions, load order, tile size
│   ├── thumbnail_loader.py     # Grid thumbnails: background decodes into a capped cache
│   ├── panels/                 # Main window regions: left container, tag list panels, center, classifier
│   └── widgets/                # TagListView (every tag panel's list), MediaGridView (grid view)
├── classifier/
│   ├── classifier_manager.py   # ClassifierManager + background workers
│   ├── inference/              # Per-family load/preprocess/inference adapters
│   └── overrides/              # TagOverrideManager (overrides.toml)
├── bulk_operations/            # Right-click bulk tag operations
└── hydra/                      # Vendored Hydra package
resources/                      # Icons + compiled resources_rc.py
data/                           # Tag CSVs and user JSON files
classifiers/<model_id>/         # Model weights and overrides
tests/                          # pytest tests (Qt runs offscreen; see Tests above)
```

Most data paths (`data/`, `staging/`, `output/`, override files) are resolved from the
working directory, so the app must be run from the repo root (the run scripts do this).
Model discovery uses `APP_ROOT`.

### Core Components

1. **MainWindow** (`main.py`)
   - Owns the app state: the image list and current image, the current image's ordered
     tags, and the favorites. It is the only writer of `TagData.selected` and `TagData.favorite`.
   - Panels change state by calling its actions (`toggle_tag`, `toggle_favorite`,
     `move_selected_tag`, `move_favorite`, `add_tags`, `add_new_tag_to_model`, `switch_tag_source`)
   - Announces changes with signals: `image_changed`, `selection_changed`,
     `favorites_changed`, `usage_changed`, `tags_changed`
   - Saves workfiles, favorites and usage data

2. **Tag Model** (`tail_tagger/tag_list_model.py`)
   - Stores all tags in `TagData` objects
   - Implements search functionality
   - Tracks tag usage statistics

3. **Classifier System** (`tail_tagger/classifier/`, `tail_tagger/ui/panels/classifier_panel.py`, `tail_tagger/hydra/`)
   - Handles image analysis using ML models across two families, JTP-2 and Hydra (see Classifier System below)
   - Loads and runs each model through per-family adapters in `tail_tagger/classifier/inference/`
   - Applies calibration + tag implications (Hydra) and `overrides.toml` post-processing
   - Runs analysis in background threads

4. **Panel System** (all in `tail_tagger/ui/panels/`)
   - Left panel container (`left_panel_container.py`) manages multiple panels:
     - Tag search panel (`tag_search_panel.py`)
     - Frequently used panel (`frequently_used_panel.py`)
     - Classifier panel (`classifier_panel.py`)
     - Favorites panel (`favorites_panel.py`)
   - Center panel (`center_panel.py`) for image and video display. Images decode on a
     background thread at screen size; the next and previous images are decoded ahead and cached.
   - Grid view (`ui/widgets/media_grid_view.py`): the folder as thumbnail tiles. It shares the
     center of the window with the center panel in a `QStackedWidget`; `MainWindow` owns the
     view mode (`grid_mode`, `set_grid_mode`). The G key or the bottom-bar toggle switches views.
     The grid changes images only through `MainWindow.go_to_image` and follows `image_changed`.
     While the grid shows, the center panel is inactive (`set_active(False)`): it decodes
     nothing and plays no video. Thumbnails load only for tiles near the visible area, and
     only while the grid is showing. The grid's keys (G, Up, Down, Enter) are handled in
     `MainWindow.eventFilter`, not as shortcuts, so text boxes keep those keys while typing.
   - Right panel for selected tags (`selected_tags_panel.py`)

5. **Configuration and Persistence**
   - `tail_tagger/config_manager.py` - Manages application configuration
   - `tail_tagger/file_operations.py` - Handles file I/O operations
   - Data stored in JSON files under `data/`

### Data Flow

1. Images are loaded from a selected folder
2. Tags can be selected manually or suggested by the classifier
3. Tags are stored in both:
   - Memory during runtime (via TagData objects)
   - JSON workfiles for persistence
4. Tag changes go through MainWindow, which emits a signal; panels rebuild or redraw their lists in response

## Key Implementation Details

### Tag Management

- Tags are stored as `TagData` objects with properties like `name`, `selected`, `favorite`
- Tag names are stored with underscores internally (`tag_name`) but displayed with spaces ("tag name")
- The `TagListModel` holds all tags and provides lookup, search and usage counts
- Each panel displays tags in different groupings (search results, favorites, etc.)
- Every tag list is a `TagListView` (`ui/widgets/tag_list_view.py`): a `QListView` with a
  delegate that draws each row from its `TagData`. Because rows read their `TagData` each
  time they are drawn, a flag change only needs `repaint_tags()`; a change to which tags a
  list shows needs `set_tags()`. The view emits `tag_clicked`, `favorite_clicked`,
  `tag_right_clicked` and `tag_moved`, and the panel decides what each one does.

### Classifier System

Models live in `classifiers/<model_id>/` and are grouped into **families** by
`MODEL_FAMILY` in `tail_tagger/classifier/classifier_manager.py`, which decides how each is loaded and
post-processed:

- **`jtp2`** — legacy JTP Pilot v1/v2. timm/torchvision with PIL preprocessing and a
  flat, user-adjustable confidence threshold. Requires `<id>.safetensors` + `tags.json`.
- **`hydra`** — JTP-3 and Hydra 3.5. Runs on the vendored Hydra package with pyvips
  preprocessing and per-tag **calibration** + e621 tag **implications** instead of a flat
  cutoff. JTP-3 (`rr_hydra`) also needs external `<id>-tags.csv` / `<id>-val.csv` in its
  folder; Hydra 3.5 (`rr_hydra2`) is self-contained (labels + calibration data embedded in
  the safetensors).

Architecture layers:

- `tail_tagger/classifier/inference/` — thin per-family adapters (`jtp2_inference.py`, `hydra_inference.py`,
  shared helpers in `base.py`) exposing load / preprocess / run-inference functions.
- `tail_tagger/hydra/` — **vendored** copy of RedRocket's Hydra package. It carries three
  local patches; read `tail_tagger/hydra/VENDOR_PATCHES.md` before updating it.
- `tail_tagger/classifier/overrides/` — `TagOverrideManager` applies each model's
  `overrides.toml` (blacklist / tag translation / dedup) as the final post-processing step.

`ClassifierManager` orchestrates loading, inference, calibration, and overrides; all model
work runs off the UI thread via `QThreadPool`/`QRunnable`, with results returned through Qt
signals. Large model weights and the JTP-3 CSVs are gitignored and downloaded separately —
see each model folder's `DOWNLOAD_INSTRUCTIONS.md`.

### UI Component Relationships

- `MainWindow` is the parent for all major panels
- `LeftPanelContainer` manages multiple tag selection panels
- Each tag panel shows its tags in a `TagListView` and connects its signals to `MainWindow` actions
- Panels connect to `MainWindow`'s signals and update their lists when state changes

## Bulk Operations Architecture

### Current Implementation

**Tag Bulk Operations** (`tail_tagger/bulk_operations/`):
- Right-click context menu operations on tags
- Four operations: Add to Beginning, Add to End, Remove from All, Replace in All (in-place)
- `BulkOperationsManager` handles core logic (direct workfile manipulation)
- `TagBulkOperationDialog` provides progress feedback and results
- `ReplaceTagDialog` collects the replacement tag name before the operation runs
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
   - Common utilities like `ensure_workfile_complete()` in `tail_tagger/file_operations.py`

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
    ├── tag_operations_dialog.py # Progress/result UI for right-click tag operations
    └── replace_tag_dialog.py   # Input dialog for the Replace in All Images operation
```

Import style:
```python
from tail_tagger.bulk_operations import BulkOperationsManager, TagBulkOperationDialog, ReplaceTagDialog
```

## File Format Information

- `config.json`: Application settings (last folder, active model, confidence/threshold, implication mode)
- `favorites.json`: Ordered favorite tag names across all tag sources (the panel shows only those known in the current source)
- `usage_data.json`: Counter of tag usage frequency
- Tag files: Comma-separated tag lists stored as .txt files
- Workfiles: JSON files mapping image paths to their tags