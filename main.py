import sys
import os
import time
import theme
from file_operations import FileOperations
from config_manager import ConfigManager
from keyboard_manager import KeyboardManager
from classifier_manager import ClassifierManager
from tag_list_model import TagListModel, TagData

from left_panel_container import LeftPanelContainer
from center_panel import CenterPanel
from selected_tags_panel import SelectedTagsPanel

# Start application timer
app_start_time = time.time()
import resources.resources_rc as resources_rc  
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QFrame, QLabel, QSizePolicy, 
                               QVBoxLayout, QPushButton, QSpacerItem, QFileDialog, QSplitter, QMessageBox)
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QKeySequence, QShortcut, QIcon

# TODO: its probably better for tag widget shading to not need every panel to rebuild their tag list and instead just 
# check their current state. better yet a single tag should be able to know if it needs an update

# Import compiled resources for icons
# Update resources.qrc and run this command to recompile:
# pyside6-rcc resources/resources.qrc -o resources/resources_rc.py

class MainWindow(QMainWindow):
    """Main application window for the Image Tagger."""

    def __init__(self):
        """Initializes the main application window."""
        super().__init__()
        self.setWindowTitle("Tail Tagger")
        self.setWindowIcon(QIcon(":/icons/app-icon.png"))
        self.resize(1280, 960)

        # --- Instance Variables ---
        self.image_paths = []  # List of image file paths for the loaded folder.
        self.current_image_index = 0
        self.current_image_path = None
        self.last_folder_path = None
        
        # --- Tag Management ---
        """These lists are used by panels that need to display tags in a particular order.
        They are populated with references to TagData objects from the model.
        This means any changes to the TagData objects in the model will be reflected in these lists automatically and vice versa."""
        self.selected_tags_for_current_image = []  # List of tags for the current image.
        self.favorite_tags_ordered = []  # List of favorite tags in order.
        
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

        # --- Auto-Analyze Timer ---
        self.auto_analyze_timer = QTimer(self)
        self.auto_analyze_timer.setSingleShot(True) # Important: only fire once per start
        self.auto_analyze_timer.timeout.connect(self._trigger_auto_analysis_from_timer)
        self.AUTO_ANALYZE_DELAY_MS = 1500 # 1.5 seconds (configurable if needed later)
        self.auto_analyze_enabled = False

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

        # Connect auto-analyze signal from classifier panel
        self.left_panel_container.classifier_panel.auto_analyze_toggled.connect(self._handle_auto_analyze_toggled)


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

        left_spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        bottom_layout.addItem(left_spacer)

        self.filename_label = QLabel("No Image")
        bottom_layout.addWidget(self.filename_label)

        self.index_label = QLabel("0 of 0")
        bottom_layout.addWidget(self.index_label)

        right_spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        bottom_layout.addItem(right_spacer)

        self.prev_button = QPushButton("< Prev")
        self.prev_button.clicked.connect(self._prev_image)
        bottom_layout.addWidget(self.prev_button)

        self.next_button = QPushButton("Next >")
        self.next_button.clicked.connect(self._next_image)
        bottom_layout.addWidget(self.next_button)

        main_layout.addWidget(bottom_panel) # Add bottom panel to main layout

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
            self.image_paths = []
            self.center_panel.clear()
            self.filename_label.setText("No Image")
            self.index_label.setText("0 of 0")
            self.prev_button.setEnabled(False)
            self.next_button.setEnabled(False)
            return

        self.file_operations.create_default_workfile(folder_path) # Create workfile if it doesn't exist
        
        self.image_paths = self.file_operations.get_sorted_image_files(folder_path)

        if self.image_paths:
            print(f"Found {len(self.image_paths)} images in folder: {folder_path}")
            self.current_image_index = 0
            self._load_and_display_image(self.image_paths[0])
            self._update_index_label()
            self.prev_button.setEnabled(True)
            self.next_button.setEnabled(True)
        else:
            print(f"No images found in folder: {folder_path}")
            self.center_panel.clear()
            self.center_panel.setText("No images found in this folder.")
            self.filename_label.setText("No Image")
            self.index_label.setText("0 of 0")
            self.prev_button.setEnabled(False)
            self.next_button.setEnabled(False)

    def _load_and_display_image(self, image_path):
        """Loads and displays an image, loads associated tags."""

        self.center_panel.set_image_path(image_path)
        filename = os.path.basename(image_path)
        self.filename_label.setText(filename)
        # current_image_path used for workfile updates
        self.current_image_path = image_path

        self.left_panel_container.classifier_panel.clear_results()

        # Use our internal state variable instead of walking the widget tree
        if self.auto_analyze_enabled:
            print("Auto-analyze is enabled. Resetting/starting timer.")
            self.auto_analyze_timer.stop() # Stop any pending timer
            self.auto_analyze_timer.start(self.AUTO_ANALYZE_DELAY_MS) # Start new delay
        else:
            # If auto-analyze is disabled, ensure timer is stopped
            self.auto_analyze_timer.stop()

        # --- Load Tags for Image ---
        loaded_tag_names = self.file_operations.load_tags_for_image(image_path, self.last_folder_path) # Get list of tag *names*
        self.selected_tags_for_current_image = []  # Clear the list of selected tag widgets
        self.tag_list_model.clear_selected_tags() # Clear selections attrs in model
        self.tag_list_model.remove_unknown_tags() # Remove any unknown tags
        # Process tag names against current model to get proper TagData objects
        self.selected_tags_for_current_image = self._process_tag_names_for_selection(loaded_tag_names)

        self.update_workfile_for_current_image() # Update workfile with current tags

        # Now that we've updated the model, all panels must be populated with the appropriate tags
        self._update_tag_panels()

        # we load the search panel differently than the others (update_display()) because I'm a bad developer
        self.left_panel_container.tag_search_panel._on_tags_changed()  

        # Debugging prints to be deleted later!
        total_tags = len(self.tag_list_model.tags)
        selected_tags = len([tag for tag in self.tag_list_model.tags if tag.selected])
        unknown_tags = len([tag for tag in self.tag_list_model.tags if not tag.is_known])
        
        print(f"Total tags in model: {total_tags}")
        print(f"Selected tags: {selected_tags}")
        print(f"Unknown tags: {unknown_tags}")

    def _update_index_label(self):
        """Updates the image index label."""
        if self.image_paths:
            index_text = f"{self.current_image_index + 1} of {len(self.image_paths)}"
        else:
            index_text = "0 of 0"
        self.index_label.setText(index_text)

    def _prev_image(self):
        """Navigates to the previous image."""
        if not self.image_paths:
            return

        self.current_image_index -= 1
        if self.current_image_index < 0:
            self.current_image_index = len(self.image_paths) - 1

        image_path = self.image_paths[self.current_image_index]
        self._load_and_display_image(image_path)
        self._update_index_label()

    def _next_image(self):
        """Navigates to the next image."""
        if not self.image_paths:
            return

        self.current_image_index += 1
        if self.current_image_index >= len(self.image_paths):
            self.current_image_index = 0

        image_path = self.image_paths[self.current_image_index]
        self._load_and_display_image(image_path)
        self._update_index_label()

    def _export_tags(self):
        self.file_operations.export_tags(self, self.last_folder_path)

    # LEGACY: This method is kept for backward compatibility and for full refreshes
    # Modern approach uses observer pattern and targeted panel updates
    def _update_tag_panels(self):
        """Updates all tag panels. 
        
        Note: This method is only needed for major changes that require full panel refreshes,
        such as loading a new image or when the entire model changes. For individual tag state
        changes (selected/unselected, favorite), the observer pattern handles updates automatically.
        """
        self.left_panel_container.update_all_displays()
        self.selected_tags_panel.update_display()

    def _load_favorites(self):
        """Loads favorite tags from favorites.json and populates favorite_tags_ordered list."""
        print("Loading favorites...")
        
        # Clear existing favorites
        self.favorite_tags_ordered = []
        
        # Load favorite tag names from file
        favorite_tag_names = self.file_operations.load_favorites()
        
        # Find matching TagData objects in the current model and mark as favorites
        for tag_name in favorite_tag_names:
            for tag in self.tag_list_model.get_all_tags():
                if tag.name == tag_name:
                    tag.favorite = True
                    self.favorite_tags_ordered.append(tag)
                    break # Move to next fav tag name
                    
        print(f"Loaded {len(self.favorite_tags_ordered)} favorite tags")

    def _handle_tag_clicked(self, clicked_tag_name):
        """Handles tag click events, updates model, workfile, and selected tags list."""

        # Find the TagData object in the model
        clicked_tag_data = None
        for tag in self.tag_list_model.get_all_tags():
            if tag.name == clicked_tag_name:
                clicked_tag_data = tag
                break

        if clicked_tag_data:
            # Toggle the selected state in the model
            new_selected_state = not clicked_tag_data.selected
            self.tag_list_model.set_tag_selected_state(clicked_tag_name, new_selected_state)
            # Note: set_tag_selected_state now handles notifying observers and emitting signals

            if new_selected_state:
                # Tag was just selected, add it to selected_tags_for_current_image
                if clicked_tag_data not in self.selected_tags_for_current_image: # Prevent Duplicates
                    self.selected_tags_for_current_image.append(clicked_tag_data)
                self.tag_list_model.increment_tag_usage(clicked_tag_name)
                self.file_operations.save_usage_data(self.tag_list_model.tag_usage_counts)
            else:
                # Tag was just deselected, remove it from selected_tags_for_current_image
                if clicked_tag_data in self.selected_tags_for_current_image:
                    self.selected_tags_for_current_image.remove(clicked_tag_data)

            # Update the workfile with the changes
            self.update_workfile_for_current_image()

            # Only update the selected panel as it needs to rebuild its list
            self.selected_tags_panel.update_display()
            
            # Frequently used panel needs to refresh if usage changed
            if new_selected_state:  # Only update on selection, not deselection
                self.left_panel_container.frequently_used_panel.update_display()
        else:
            print(f"Warning: Clicked tag '{clicked_tag_name}' not found in TagListModel.")

    def _handle_favorite_star_clicked(self, clicked_tag_name):
        """Handles clicks on the favorite star icon in TagWidget."""
        print(f"Favorite star clicked for tag: {clicked_tag_name}") # Debug - basic confirmation

        # 1. Find the TagData object in the model
        clicked_tag_data = None
        for tag in self.tag_list_model.get_all_tags():
            if tag.name == clicked_tag_name:
                clicked_tag_data = tag
                break

        if clicked_tag_data:
            # 2. Toggle the 'favorite' attribute in TagData
            clicked_tag_data.favorite = not clicked_tag_data.favorite
            new_favorite_state = clicked_tag_data.favorite # Get the new state

            # 3. Update favorite_tags_ordered list
            if new_favorite_state:
                # Tag is now a favorite, add it to the list (append to end)
                if clicked_tag_data not in self.favorite_tags_ordered: # Prevent duplicates
                    self.favorite_tags_ordered.append(clicked_tag_data)
                print(f"Tag '{clicked_tag_name}' added to favorites.") # Debug
            else:
                # Tag is no longer a favorite, remove it from the list
                if clicked_tag_data in self.favorite_tags_ordered:
                    self.favorite_tags_ordered.remove(clicked_tag_data)
                print(f"Tag '{clicked_tag_name}' removed from favorites.") # Debug

            # 4. Save updated favorites to favorites.json
            self.file_operations.save_favorites(self.favorite_tags_ordered)
            print("favorites.json updated.") # Debug

            # 5. Notify observers of state change
            clicked_tag_data.notify_observers()
            self.tag_list_model.tag_state_changed.emit(clicked_tag_name)

            # 6. Update only the favorites panel as it needs to rebuild
            self.left_panel_container.favorites_panel.update_display()
            print("Favorites panel updated to reflect favorite changes.") # Debug

        else:
            print(f"Warning: Favorite star clicked for tag '{clicked_tag_name}', but tag not found in TagListModel.")
    
    def update_workfile_for_current_image(self):
        """Updates the workfile for the current image. Make sure selected_tags_for_current_image is up to date before calling this."""
        self.file_operations.update_workfile(
            self.last_folder_path,
            self.current_image_path,
            self.selected_tags_for_current_image
        )

    def add_new_tag_to_model(self, tag_name):
        """
        Adds a new tag to the application, handling CSV updates, model updates, and panel refreshes.
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
            # Notify observers about the change
            existing_unknown_tag_data.notify_observers()
            self.tag_list_model.tag_state_changed.emit(underscored_tag_name)
            print(f"Unknown tag '{underscored_tag_name}' promoted to known tag (in-place update).")

        else:
            # --- Add completely new tag ---
            csv_added_successfully = self.file_operations.add_tag_to_csv(self.csv_path, underscored_tag_name)
            if not csv_added_successfully:
                QMessageBox.critical(self, "Error Adding Tag", f"Error adding tag to CSV file.", QMessageBox.Ok)
                return

            # Add new tag to model
            new_tag_data = TagData(name=underscored_tag_name, category="9", post_count=0, is_known=True)
            self.tag_list_model.add_tag(new_tag_data)
            print(f"New tag '{underscored_tag_name}' added to TagListModel.")

        # --- Update UI (All relevant panels) ---
        # Still need to update search panel for new searches to include the tag
        self.tag_list_model.tags_selected_changed.emit() 
        # Updates are needed for SelectedTagsPanel if we just promoted a tag that's in the current image
        self.selected_tags_panel.update_display()

    @Slot(bool)
    def _handle_auto_analyze_toggled(self, enabled):
        """Handles the auto_analyze_toggled signal from ClassifierPanel."""
        print(f"Main window received auto-analyze toggle: {enabled}")
        self.auto_analyze_enabled = enabled

        # If auto-analyze was just enabled and we have a current image,
        # start the timer to trigger analysis after a delay
        if enabled and self.current_image_path:
            print("Auto-analyze is enabled. Starting timer for current image.")
            self.auto_analyze_timer.stop() # Ensure any previous timer is stopped
            self.auto_analyze_timer.start(self.AUTO_ANALYZE_DELAY_MS)
        elif not enabled:
            # If auto-analyze was disabled, make sure the timer is stopped
            self.auto_analyze_timer.stop()
            print("Auto-analyze is disabled. Timer stopped.")

    @Slot()
    def _trigger_auto_analysis_from_timer(self):
        """Called when the auto-analyze timer fires."""
        print("Auto-analyze timer fired.")
        if self.current_image_path and hasattr(self, 'left_panel_container') and \
        hasattr(self.left_panel_container, 'classifier_panel'):
            # Check if auto-analyze is STILL enabled (user might have disabled it during delay)
            if self.auto_analyze_enabled:
                print("  Auto-analyze is enabled. Triggering analysis.")
                # Call the panel's existing analyze button click handler
                # This ensures UI updates (button disable, status) are consistent
                self.left_panel_container.classifier_panel._handle_analyze_clicked()
            else:
                print("  Auto-analyze was disabled during delay. Analysis cancelled.")
        else:
            print("  Auto-analyze: No current image or panel not ready. Analysis skipped.")

    # TODO: I really don't like this. This method does seemingly arbitrary things to the model and UI
    # fundamentally its solving the problem of determining what the current state of unknown tags is
    # and ensuring the model and UI are in sync. But that entire process needs to be reworked. This works. But it should be cleaner.

    def _process_tag_names_for_selection(self, tag_names):
        """
        Process a list of tag names against the current model to produce TagData objects
        ready for selection. This is the shared logic between loading image tags and
        reprocessing tags after switching the tag source.

        Args:
            tag_names: List of tag name strings to process
            
        Returns:
            List of TagData objects (known tags from model or newly created unknown tags)
        """
        result_tag_data_list = []
        
        for tag_name in tag_names:
            # Find existing TagData in current model
            existing_tag_data = None
            for tag in self.tag_list_model.get_all_tags():
                if tag.name == tag_name:
                    existing_tag_data = tag
                    break

            if existing_tag_data:
                # Known tag found in model
                self.tag_list_model.set_tag_selected_state(tag_name, True)
                result_tag_data_list.append(existing_tag_data)
            else:
                # Unknown tag: create TagData object (is_known=False)
                new_tag_data = TagData(name=tag_name, selected=True, is_known=False)
                self.tag_list_model.add_tag(new_tag_data)
                result_tag_data_list.append(new_tag_data)
        
        return result_tag_data_list

    def switch_tag_source(self, source_type):
        """Switches between e621 and danbooru tag sources"""
        print(f"Switching tag source from {self.current_tag_source} to {source_type}")
        
        # Update config for persistence
        self.config_manager.set_config_value("tag_source", source_type)
        self.current_tag_source = source_type
        
        # Reload tags from new source
        csv_path = os.path.join(os.getcwd(), "data", f"{source_type}-tags-list.csv")
        self.tag_list_model.switch_tag_source(csv_path)
        
        # Reload favorites with new tag model. We only load favorites that exist in the currently loaded model
        self._load_favorites()
        
        # Reprocess current image tags against new model (if we have a current image)
        if self.current_image_path and self.selected_tags_for_current_image:
            current_tag_names = [tag.name for tag in self.selected_tags_for_current_image]
            self.selected_tags_for_current_image = []
            self.tag_list_model.clear_selected_tags()
            self.tag_list_model.remove_unknown_tags()
            
            self.selected_tags_for_current_image = self._process_tag_names_for_selection(current_tag_names)
            self.update_workfile_for_current_image()
        
        # Full UI refresh
        self._update_tag_panels()

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