import sys
import os

def check_dependencies():
    """Verify critical dependencies can be imported."""
    missing = []

    # Check for einops (new dependency for JTP-3)
    try:
        import einops
    except ImportError:
        missing.append("einops (new dependency for JTP-3)")

    # Check for timm with NAFlex support
    try:
        import timm
        # Try to list NAFlex models to verify timm has the feature
        timm.list_models("naflexvit*")  # Will work if timm >= 1.0.19
    except ImportError:
        missing.append("timm")
    except Exception:
        missing.append("timm (outdated - needs >= 1.0.19 for JTP-3 support)")

    if missing:
        print("\n" + "="*60)
        print("ERROR: Missing or outdated dependencies:")
        for item in missing:
            print(f"  - {item}")
        print("\nPlease update your environment:")
        print("  Option 1: pip install -r requirements.txt --upgrade")
        print("  Option 2: Re-run setup.bat (deletes venv and reinstalls)")
        print("="*60 + "\n")
        sys.exit(1)

# Check dependencies before importing heavy modules
check_dependencies()

import time
from tail_tagger.ui import theme
from tail_tagger.file_operations import FileOperations
from tail_tagger.config_manager import ConfigManager
from tail_tagger.ui.keyboard_manager import KeyboardManager
from tail_tagger.classifier.classifier_manager import ClassifierManager
from tail_tagger.tag_list_model import TagListModel, TagData
from tail_tagger.tag_state import toggle_name, append_names, move_name, visible_favorites, move_favorite_name
from tail_tagger.bulk_operations import BulkOperationsManager, TagBulkOperationDialog, ReplaceTagDialog

from tail_tagger.ui.panels.left_panel_container import LeftPanelContainer
from tail_tagger.ui.panels.center_panel import CenterPanel
from tail_tagger.ui.image_loading import neighbor_paths
from tail_tagger.ui.panels.selected_tags_panel import SelectedTagsPanel

# Start application timer
app_start_time = time.time()
import resources.resources_rc as resources_rc  
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QFrame, QLabel, QSizePolicy, 
                               QVBoxLayout, QPushButton, QSpacerItem, QFileDialog, QSplitter, QMessageBox)
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QKeySequence, QShortcut, QIcon, QDesktopServices

# Import compiled resources for icons
# Update resources.qrc and run this command to recompile:
# pyside6-rcc resources/resources.qrc -o resources/resources_rc.py

class MainWindow(QMainWindow):
    """Main application window for the Image Tagger."""

    # Panels listen to these and refresh themselves, so actions don't need to know which panels exist
    image_changed = Signal(object)  # The new current path, or None when the folder turns out to have no images
    selection_changed = Signal()    # The current image's ordered tag list changed
    favorites_changed = Signal()    # Favorites were starred, unstarred, reordered, or reloaded
    usage_changed = Signal()        # Usage counts changed, so Frequently Used may reorder
    tags_changed = Signal()         # The tag catalog changed: a tag was added or promoted, or the tag source switched

    def __init__(self):
        """Initializes the main application window."""
        super().__init__()
        self.setWindowTitle("Tail Tagger")
        self.setWindowIcon(QIcon(":/icons/app-icon.png"))
        self.resize(1280, 960)

        # --- Instance Variables ---
        self.image_paths = []  # List of image file paths for the loaded folder.
        self.current_image_index = 0
        self.last_folder_path = None
        
        # --- Tag Management ---
        """These lists are used by panels that need to display tags in a particular order.
        They are populated with references to TagData objects from the model.
        This means any changes to the TagData objects in the model will be reflected in these lists automatically and vice versa."""
        self.selected_tags_for_current_image = []  # List of tags for the current image.
        self.favorite_tag_names = []  # All favorite tag names across every tag source, in order. Mirrors favorites.json.
        
        # --- File Operations ---
        self.file_operations = FileOperations()
        self.tag_list_model = TagListModel()

        # --- Load Configuration ---
        self.config_manager = ConfigManager()
        config = self.config_manager.config
        self.last_folder_path = config.get("last_opened_folder") # Set last folder from config
        self.current_tag_source = config.get("tag_source", "e621")  # Default to e621 tags

        # --- Managers ---
        self.keyboard_manager = KeyboardManager(self)
        self.classifier_manager = ClassifierManager(config_manager=self.config_manager, use_gpu=True)
        self.bulk_operations_manager = BulkOperationsManager(self.file_operations)

        # --- Global Keyboard Shortcuts ---
        self.prev_shortcut = QShortcut(QKeySequence(Qt.Key_Left), self)
        self.prev_shortcut.activated.connect(self._prev_image)
        self.prev_shortcut.setContext(Qt.ApplicationShortcut)

        self.next_shortcut = QShortcut(QKeySequence(Qt.Key_Right), self)
        self.next_shortcut.setContext(Qt.ApplicationShortcut)
        self.next_shortcut.activated.connect(self._next_image)
       
        # --- Staging Folder ---
        self.staging_folder_path = os.path.join(os.getcwd(), "staging")
        if not os.path.isdir(self.staging_folder_path):
            os.makedirs(self.staging_folder_path, exist_ok=True)
        self.file_operations.staging_folder_path = self.staging_folder_path

        # --- Load Tags from CSV ---
        csv_load_start = time.time()
        self.csv_path = os.path.join(os.getcwd(), "data", f"{self.current_tag_source}-tags-list.csv")
        self.tag_list_model.load_tags_from_csv(self.csv_path)
        csv_load_end = time.time()
        print(f"CSV loading complete in {csv_load_end - csv_load_start:.4f} seconds")

        # --- Load Favorites After Tag Model is Ready ---
        self._load_favorites()

        # --- Tag Panels ---
        self.selected_tags_panel = SelectedTagsPanel(self)

        # --- Setup UI and Load Tags/Images ---
        self._setup_ui()

        # --- Validate and Load Last Opened Folder ---
        if self.last_folder_path and not os.path.isdir(self.last_folder_path):
            print(f"Last opened folder not found: {self.last_folder_path}. Clearing from config.")
            self.last_folder_path = None
            self.config_manager.set_config_value("last_opened_folder", None)

        if (self.last_folder_path):
            print(f"Loading last opened folder: {self.last_folder_path}")
            self._load_image_folder(self.last_folder_path)
        else:
            print("No valid last opened folder. Select a folder from the file menu.")
            self._load_image_folder(None)

    def _setup_ui(self):
        """Sets up the main user interface layout and elements."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # --- Menu Bar ---
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")
        open_folder_action = file_menu.addAction("Open Folder...")
        open_folder_action.triggered.connect(self._open_folder_dialog)

        export_action = file_menu.addAction("Export Tags...")
        export_action.triggered.connect(self._export_tags)
        # --- End Menu Bar ---

        main_layout = QVBoxLayout(central_widget) # Set layout on central widget
        main_layout.setSpacing(0)

        # --- Main Horizontal Splitter (Left, Center, Right) ---
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.setChildrenCollapsible(False)
        main_layout.addWidget(main_splitter) # Add splitter to main layout


        # --- Left Panel ---
        self.left_panel_container = LeftPanelContainer(main_window=self, classifier_manager=self.classifier_manager)
        main_splitter.addWidget(self.left_panel_container)  # Add to main splitter

        # --- Center Panel (Image Display) ---
        self.center_panel = CenterPanel()
        self.center_panel.setFrameShape(QFrame.StyledPanel)
        self.center_panel.setMinimumSize(100, 100)
        main_splitter.addWidget(self.center_panel)  # Add to splitter

        # --- Right Panel (Selected Tags) ---
        main_splitter.addWidget(self.selected_tags_panel)  # Add panel directly to splitter

        # Set initial sizes for the splitter. Essentially left and right will be fixed width between this and the set stretch factors
        main_splitter.setSizes([150, 200, 150])
        # Set stretch factors. 0 = fixed size, 1 = stretchable
        main_splitter.setStretchFactor(0, 0) # Left Panel
        main_splitter.setStretchFactor(1, 1) # Center Panel
        main_splitter.setStretchFactor(2, 0) # Right Panel


        # --- Bottom Panel (Image Info and Buttons) ---
        bottom_panel = QFrame()
        bottom_panel.setFrameShape(QFrame.StyledPanel)
        bottom_panel.setFixedHeight(50)
        bottom_layout = QHBoxLayout(bottom_panel)
        bottom_layout.setSpacing(10)
        bottom_layout.setContentsMargins(10, 5, 10, 5)

        # Left container (folder path)
        left_bottom_container = QWidget()
        left_bottom_layout = QHBoxLayout(left_bottom_container)
        left_bottom_layout.setContentsMargins(0, 0, 0, 0)
        self.folder_path_label = QLabel("Opened Folder: (none)")
        self.folder_path_label.setTextFormat(Qt.RichText)
        self.folder_path_label.setOpenExternalLinks(False)
        self.folder_path_label.linkActivated.connect(self._open_current_folder)
        left_bottom_layout.addWidget(self.folder_path_label)
        left_bottom_layout.addStretch()
        bottom_layout.addWidget(left_bottom_container, 1)  # stretch factor 1

        # Center filename
        self.filename_label = QLabel("No Image")
        self.filename_label.setAlignment(Qt.AlignCenter)
        bottom_layout.addWidget(self.filename_label, 0)  # no stretch

        # Right container (buttons and index)
        right_bottom_container = QWidget()
        right_bottom_layout = QHBoxLayout(right_bottom_container)
        right_bottom_layout.setContentsMargins(0, 0, 0, 0)
        right_bottom_layout.addStretch()
        
        # Prev/Next start disabled; _on_image_changed enables them once a folder has images
        self.prev_button = QPushButton("< Prev")
        self.prev_button.setEnabled(False)
        self.prev_button.clicked.connect(self._prev_image)
        right_bottom_layout.addWidget(self.prev_button)

        # Index label with fixed width to prevent button shifting
        self.index_label = QLabel("0 of 0")
        self.index_label.setFixedWidth(55)  # Wide enough for "xxx of xxx"
        self.index_label.setAlignment(Qt.AlignCenter)
        right_bottom_layout.addWidget(self.index_label)

        self.next_button = QPushButton("Next >")
        self.next_button.setEnabled(False)
        self.next_button.clicked.connect(self._next_image)
        right_bottom_layout.addWidget(self.next_button)

        bottom_layout.addWidget(right_bottom_container, 1)  # stretch factor 1 (equal to left)

        main_layout.addWidget(bottom_panel) # Add bottom panel to main layout

        # The center panel and bottom bar don't know about MainWindow, so they're connected here
        # (other panels connect themselves)
        self.image_changed.connect(self.center_panel.show_media)
        self.image_changed.connect(self._on_image_changed)

    def _open_folder_dialog(self):
        """Opens a folder selection dialog and loads images."""
        start_directory = os.path.expanduser("~")
        if self.last_folder_path and os.path.isdir(self.last_folder_path):
            start_directory = self.last_folder_path

        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Image Folder",
            start_directory,
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )

        if folder_path:
            folder_path = os.path.normpath(folder_path)
            self.last_folder_path = folder_path
            self.config_manager.set_config_value("last_opened_folder", self.last_folder_path)
            self._load_image_folder(folder_path)

    def _load_image_folder(self, folder_path):
        """Loads images from the given folder and updates the UI."""
        if not folder_path:
            print("No folder path, handling as no images.")
            self.folder_path_label.setText("Opened Folder: (none)")
            self.folder_path_label.setToolTip("")
            self._show_no_images(None)
            return

        self.file_operations.create_default_workfile(folder_path) # Create workfile if it doesn't exist

        # Update folder path label with elided text
        self._update_folder_path_label(folder_path)

        media_paths = self.file_operations.get_sorted_media_files(folder_path)

        if media_paths:
            print(f"Found {len(media_paths)} images in folder: {folder_path}")
            self.image_paths = media_paths
            self.go_to_image(0)
        else:
            print(f"No images found in folder: {folder_path}")
            self._show_no_images("No images found in this folder.")

    def _show_no_images(self, message):
        """Clears the media list and, if an image was showing, its tags and classifier results."""
        had_image = self.current_image_path is not None
        self.image_paths = []
        self.current_image_index = 0

        # Only announce a change when an image was actually showing, so startup with
        # no folder leaves the classifier's status text alone
        if had_image:
            self.tag_list_model.remove_unknown_tags()
            self._apply_selection([])
            self.image_changed.emit(None)

        # Set the message after the emit, since image_changed(None) clears the center panel
        if message:
            self.center_panel.setText(message)
        else:
            self.center_panel.clear()

    @property
    def current_image_path(self):
        """Path of the image at current_image_index, or None when no images are loaded."""
        if 0 <= self.current_image_index < len(self.image_paths):
            return self.image_paths[self.current_image_index]
        return None

    def go_to_image(self, index):
        """Shows the image at index and loads its tags. Out-of-range indexes are ignored."""
        if not 0 <= index < len(self.image_paths):
            return

        self.current_image_index = index
        self.tag_list_model.remove_unknown_tags() # Unknown tags belong to the previous image
        self._reload_current_image_tags()
        self.image_changed.emit(self.current_image_path)
        # The center panel can't see the image list, so it's told which images come next
        self.center_panel.prefetch(neighbor_paths(self.image_paths, index))

    def _reload_current_image_tags(self):
        """Reads the current image's tags (workfile, else .txt) and selects them.

        Unknown tags already in the model are kept, so classifier suggestions stay valid.
        """
        tag_names = self.file_operations.load_tags_for_image(self.current_image_path, self.last_folder_path)
        self._apply_selection(self._tags_for_names(tag_names))

        self.update_workfile_for_current_image() # Writes .txt tags into the workfile on first visit

    def _on_image_changed(self, image_path):
        """Updates the bottom bar's filename, index label, and Prev/Next buttons."""
        if image_path:
            self.filename_label.setText(os.path.basename(image_path))
            self.index_label.setText(f"{self.current_image_index + 1} of {len(self.image_paths)}")
        else:
            self.filename_label.setText("No Image")
            self.index_label.setText("0 of 0")
        self.prev_button.setEnabled(bool(self.image_paths))
        self.next_button.setEnabled(bool(self.image_paths))

    def _update_folder_path_label(self, folder_path):
        """Updates the folder path label with elided text."""
        if folder_path:
            # Set full path as tooltip
            self.folder_path_label.setToolTip(folder_path)
            # Use elided text from the left
            display_prefix = "Opened Folder: "
            font_metrics = self.folder_path_label.fontMetrics()
            elided_path = font_metrics.elidedText(folder_path, Qt.ElideLeft, self.folder_path_label.width() - font_metrics.horizontalAdvance(display_prefix))
            # Use rich text with link for hover effect and theme color
            self.folder_path_label.setText(f'{display_prefix}<a href="#">{elided_path}</a>')
        else:
            self.folder_path_label.setText("Opened Folder: (none)")
            self.folder_path_label.setToolTip("")

    def _open_current_folder(self, link=None):
        """Opens the current folder in the system file manager."""
        if self.last_folder_path and os.path.isdir(self.last_folder_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.last_folder_path))
        else:
            print("No valid folder to open.")

    def _prev_image(self):
        """Navigates to the previous image, wrapping to the last."""
        if self.image_paths:
            self.go_to_image((self.current_image_index - 1) % len(self.image_paths))

    def _next_image(self):
        """Navigates to the next image, wrapping to the first."""
        if self.image_paths:
            self.go_to_image((self.current_image_index + 1) % len(self.image_paths))

    def _export_tags(self):
        self.file_operations.export_tags(self, self.last_folder_path)

    def _load_favorites(self):
        """Loads favorite names from favorites.json and marks the visible ones as favorites."""
        self.favorite_tag_names = self.file_operations.load_favorites()

        visible = self.visible_favorite_tags()
        for tag in visible:
            tag.favorite = True

        print(f"Loaded {len(visible)} of {len(self.favorite_tag_names)} favorite tags for this tag source")
        self.favorites_changed.emit()

    def _is_visible_favorite(self, tag_name):
        """A favorite is shown when it is a known tag in the current tag source."""
        tag = self.tag_list_model.tags_by_name.get(tag_name)
        return tag is not None and tag.is_known

    def visible_favorite_tags(self):
        """Favorites known in the current tag source, in favorites order."""
        names = visible_favorites(self.favorite_tag_names, self._is_visible_favorite)
        return [self.tag_list_model.tags_by_name[name] for name in names]

    def move_favorite(self, tag_name, new_index):
        """Moves a favorite to new_index among the visible favorites and saves.

        Favorites hidden by the current tag source keep their positions.
        """
        self.favorite_tag_names = move_favorite_name(
            self.favorite_tag_names, self._is_visible_favorite, tag_name, new_index)
        self.file_operations.save_favorites(self.favorite_tag_names)
        self.favorites_changed.emit()

    def toggle_tag(self, tag_name):
        """Adds a tag to the end of the current image's tags, or removes it if present."""
        if not self.current_image_path:
            return
        if tag_name not in self.tag_list_model.tags_by_name:
            print(f"Warning: Clicked tag '{tag_name}' not found in TagListModel.")
            return

        old_names = self._selected_names()
        selecting = tag_name not in old_names
        self._apply_selection(self._tags_for_names(toggle_name(old_names, tag_name)))
        self.update_workfile_for_current_image()

        # Usage only counts when a tag is selected, not deselected, so Frequently Used stays put on removal
        if selecting:
            self.tag_list_model.increment_tag_usage(tag_name)
            self.file_operations.save_usage_data(self.tag_list_model.tag_usage_counts)
            self.usage_changed.emit()

    def move_selected_tag(self, tag_name, new_index):
        """Moves one of the current image's tags to new_index and saves the workfile."""
        if not self.current_image_path:
            return
        self._apply_selection(self._tags_for_names(move_name(self._selected_names(), tag_name, new_index)))
        self.update_workfile_for_current_image()

    def remove_from_frequent(self, tag_name):
        """Clears a tag's usage count so it leaves the Frequently Used panel."""
        self.tag_list_model.remove_tag_usage(tag_name)
        self.file_operations.save_usage_data(self.tag_list_model.tag_usage_counts)
        self.usage_changed.emit()

    def toggle_favorite(self, tag_name):
        """Stars or unstars a tag, saves favorites, and emits favorites_changed."""
        tag = self.tag_list_model.tags_by_name.get(tag_name)
        if tag is None or not tag.is_known:
            print(f"Warning: Favorite toggled for '{tag_name}', but it is not a known tag.")
            return

        # The stored list decides, so the flag can't disagree with favorites.json
        if tag_name in self.favorite_tag_names:
            self.favorite_tag_names = [name for name in self.favorite_tag_names if name != tag_name]
        else:
            self.favorite_tag_names = append_names(self.favorite_tag_names, [tag_name])
        tag.favorite = tag_name in self.favorite_tag_names

        self.file_operations.save_favorites(self.favorite_tag_names)
        tag.notify_observers() # Updates the star on every widget showing this tag
        self.favorites_changed.emit()

    def add_tags(self, tag_names):
        """Appends tags not already on the current image, in the given order. Does not count usage."""
        if not tag_names or not self.current_image_path:
            return

        known_names = []
        for tag_name in tag_names:
            if tag_name in self.tag_list_model.tags_by_name:
                known_names.append(tag_name)
            else:
                print(f"Warning: Tag '{tag_name}' not found in model during bulk add")

        # Tags already on the image keep their position; only new ones go on the end
        old_names = self._selected_names()
        new_names = append_names(old_names, known_names)
        if new_names == old_names:
            print("Bulk add: No new tags added (all already selected)")
            return

        self._apply_selection(self._tags_for_names(new_names))
        self.update_workfile_for_current_image() # One workfile write for all the additions
        print(f"Bulk add complete: {len(new_names) - len(old_names)} tags added")

    def update_workfile_for_current_image(self):
        """Updates the workfile for the current image. Make sure selected_tags_for_current_image is up to date before calling this."""
        if not self.current_image_path:
            return
        self.file_operations.update_workfile(
            self.last_folder_path,
            self.current_image_path,
            self.selected_tags_for_current_image
        )

    def execute_bulk_operation(self, operation_type, tag_name):
        """Executes a bulk tag operation across all images in the current folder.

        Args:
            operation_type (str): 'add_front', 'add_end', or 'remove'
            tag_name (str): Name of the tag to operate on
        """
        # Validate that a folder is loaded
        if not self.last_folder_path:
            QMessageBox.warning(
                self,
                "No Folder Loaded",
                "Please open a folder before performing bulk operations."
            )
            return

        tag_data = self.tag_list_model.tags_by_name.get(tag_name)
        if not tag_data:
            QMessageBox.warning(
                self,
                "Tag Not Found",
                f"Tag '{tag_name}' not found in the tag model."
            )
            return

        # For add operations on unknown tags, promote them to known tags
        if operation_type in ['add_front', 'add_end'] and not tag_data.is_known:
            print(f"Auto-promoting unknown tag '{tag_name}' to known tag for bulk add operation")
            self.add_new_tag_to_model(tag_name)

        # Create and show progress dialog
        dialog = TagBulkOperationDialog(self, operation_type, tag_name)
        result = dialog.execute_operation(self.bulk_operations_manager, self.last_folder_path)

        # If operation was successful, reload current image to sync UI
        if result and result.get('success'):
            print(f"Bulk operation completed successfully. Reloading current image tags.")
            # Reload current image to refresh tag state
            if self.current_image_path:
                self._reload_current_image_tags()

    def start_replace_tag_operation(self, source_tag_name):
        """Shows the replace tag dialog and executes the replacement if confirmed.

        Args:
            source_tag_name (str): Name of the tag to replace (stored with underscores)
        """
        if not self.last_folder_path:
            QMessageBox.warning(
                self,
                "No Folder Loaded",
                "Please open a folder before performing bulk operations."
            )
            return

        dialog = ReplaceTagDialog(self, source_tag_name)
        if dialog.exec() != ReplaceTagDialog.Accepted:
            return

        target_tag = dialog.get_target_tag()
        if not target_tag:
            return

        source_display = source_tag_name.replace('_', ' ')
        target_display = target_tag.replace('_', ' ')
        print(f"Bulk replace: '{source_display}' → '{target_display}'")

        progress_dialog = TagBulkOperationDialog(self, 'replace', source_tag_name, target_tag=target_tag)
        result = progress_dialog.execute_operation(self.bulk_operations_manager, self.last_folder_path)

        if result and result.get('success'):
            print(f"Bulk replace completed successfully. Reloading current image tags.")
            if self.current_image_path:
                self._reload_current_image_tags()

    def add_new_tag_to_model(self, tag_name):
        """
        Adds a new tag to the application, handling CSV updates and model updates, then emits tags_changed.
        Centralized method for tag addition, promoting unknown tags if necessary.
        """
        underscored_tag_name = self.file_operations.convert_spaces_to_underscores(tag_name)

        # --- Check for existing tags (prioritize known, then check unknown) ---
        existing_tag_data = None
        existing_unknown_tag_data = None
        for tag in self.tag_list_model.get_all_tags():
            if tag.name.lower() == underscored_tag_name.lower():
                if tag.is_known:
                    existing_tag_data = tag
                    break  # Exit loop, known tag found
                else:
                    existing_unknown_tag_data = tag # Found existing UNKNOWN tag, keep track of it

        if existing_tag_data:
            # If tag already exists as a *known* tag, show warning and return
            QMessageBox.warning(self, "Tag Already Exists", f"Tag '{FileOperations.convert_underscores_to_spaces(underscored_tag_name)}' already exists as a known tag.", QMessageBox.Ok)
            return

        if existing_unknown_tag_data:
            # --- Promote existing unknown tag to known ---
            csv_added_successfully = self.file_operations.add_tag_to_csv(self.csv_path, underscored_tag_name)
            if not csv_added_successfully:
                QMessageBox.critical(self, "Error Adding Tag", f"Error adding tag to CSV file.", QMessageBox.Ok)
                return

            # In-place update of existing TagData object:
            existing_unknown_tag_data.is_known = True
            existing_unknown_tag_data.category = "9"
            existing_unknown_tag_data.post_count = 0
            existing_unknown_tag_data.favorite = underscored_tag_name in self.favorite_tag_names
            self.tag_list_model.index_tag(existing_unknown_tag_data)
            # Restyles the tag wherever it's already shown
            existing_unknown_tag_data.notify_observers()
            print(f"Unknown tag '{underscored_tag_name}' promoted to known tag (in-place update).")

        else:
            # --- Add completely new tag ---
            csv_added_successfully = self.file_operations.add_tag_to_csv(self.csv_path, underscored_tag_name)
            if not csv_added_successfully:
                QMessageBox.critical(self, "Error Adding Tag", f"Error adding tag to CSV file.", QMessageBox.Ok)
                return

            # Add new tag to model
            new_tag_data = TagData(name=underscored_tag_name, category="9", post_count=0, is_known=True,
                                   favorite=underscored_tag_name in self.favorite_tag_names)
            self.tag_list_model.add_tag(new_tag_data)
            print(f"New tag '{underscored_tag_name}' added to TagListModel.")

        # Search re-runs so the tag shows up in results, and the other panels pick up the change
        self.tags_changed.emit()

    # TODO: I really don't like this. This method does seemingly arbitrary things to the model and UI
    # fundamentally its solving the problem of determining what the current state of unknown tags is
    # and ensuring the model and UI are in sync. But that entire process needs to be reworked. This works. But it should be cleaner.

    def _tags_for_names(self, tag_names):
        """Returns the TagData for each name, creating unknown tags for names not in the model."""
        tags = []
        for tag_name in tag_names:
            tag = self.tag_list_model.tags_by_name.get(tag_name)
            if tag is None:
                tag = TagData(name=tag_name, is_known=False)
                self.tag_list_model.add_tag(tag)
            tags.append(tag)
        return tags

    def _apply_selection(self, tags):
        """Sets the current image's ordered tags. The only writer of the list and of TagData.selected.

        Flags change only on tags entering or leaving the list, and only those tags notify
        their widgets.
        """
        old_list = self.selected_tags_for_current_image
        old_tags = set(old_list)
        new_tags = set(tags)
        self.selected_tags_for_current_image = list(tags)

        for tag in old_tags - new_tags:
            tag.selected = False
            tag.notify_observers()
        for tag in new_tags - old_tags:
            tag.selected = True
            tag.notify_observers()

        # Skip the signal when nothing changed, so reloading the same tags rebuilds nothing
        if self.selected_tags_for_current_image != old_list:
            self.selection_changed.emit()

    def _selected_names(self):
        return [tag.name for tag in self.selected_tags_for_current_image]

    def switch_tag_source(self, source_type):
        """Switches between e621 and danbooru tag sources"""
        print(f"Switching tag source from {self.current_tag_source} to {source_type}")
        
        # Update config for persistence
        self.config_manager.set_config_value("tag_source", source_type)
        self.current_tag_source = source_type
        
        # Reload tags from new source
        self.csv_path = os.path.join(os.getcwd(), "data", f"{source_type}-tags-list.csv")
        self.tag_list_model.switch_tag_source(self.csv_path)
        
        # Reload favorites with new tag model. We only load favorites that exist in the currently loaded model
        self._load_favorites()
        
        # Reprocess current image tags against new model (if we have a current image)
        if self.current_image_path and self.selected_tags_for_current_image:
            self._apply_selection(self._tags_for_names(self._selected_names()))
            self.update_workfile_for_current_image()

        # Every TagData object was replaced, so panels rebuild their widgets against the new ones
        self.tags_changed.emit()

app = QApplication(sys.argv)
theme.setup_dark_mode(app)

# Create main window
window_start_time = time.time()
window = MainWindow()
window_end_time = time.time()
print(f"MainWindow initialization took {window_end_time - window_start_time:.4f} seconds")

# Show window
window.show()
app_ready_time = time.time()
print(f"Total application startup time: {app_ready_time - app_start_time:.4f} seconds")

app.exec()