import sys
import os
import json
from tag_widget import TagWidget
from center_panel import CenterPanel
from tag_list_panel import TagListPanel
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QFrame, QLabel,
                             QSizePolicy, QVBoxLayout, QScrollArea, QPushButton, QSpacerItem,
                             QFileDialog, QLineEdit)
from PySide6.QtGui import QColor, QPalette
from PySide6.QtCore import Qt, QSettings

class SelectionPanel(TagListPanel):
    """Panel for displaying and managing selected tags."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tag_names = []  # Store tag NAMES, not widgets.
        self.setAcceptDrops(True)  # Ensure the panel accepts drops.
        print(f"SelectionPanel drag_allowed: {self.is_tag_draggable('')}")  # Added for debugging

    def add_tag(self, tag_name, is_known=True):
        if tag_name not in self.tag_names:
            self.tag_names.append(tag_name)

    def remove_tag(self, tag_name):
        if tag_name in self.tag_names:
            self.tag_names.remove(tag_name)

    def clear_tags(self):
        self.tag_names = []

    def get_tags(self):
        return self.tag_names

    def set_tags(self, tags):
        self.tag_names = tags[:]  # Create a *copy* of the list.

    def set_tag_selected(self, tag_name, is_selected):
        for i in reversed(range(self.layout.count())):
            widget = self.layout.itemAt(i).widget()
            if isinstance(widget, TagWidget) and widget.tag_name == tag_name:
                widget.set_selected(is_selected)
                break

    def is_tag_draggable(self, tag_name):
        return True  # Tags in the RightPanel ARE draggable.

    def dropEvent(self, event):
        if isinstance(event.source(), TagWidget):
            print("SelectionPanel: dropEvent")  # DEBUG
            event.acceptProposedAction() # Add this!

    def dragEnterEvent(self, event):
        print("SelectionPanel: dragEnterEvent")  # DEBUG
        if isinstance(event.source(), TagWidget):  # Check if the source is a TagWidget
            print("SelectionPanel: dragEnterEvent-> acceptProposedAction")
            event.acceptProposedAction()
        else:
            print("SelectionPanel: dragEnterEvent-> event.source() was NOT a TagWidget")
            event.ignore()

    def dragMoveEvent(self, event):
        print("SelectionPanel: dragMoveEvent")
        if isinstance(event.source(), TagWidget):  # Check if the source is a TagWidget
            print("SelectionPanel: dragMoveEvent-> acceptProposedAction")
            event.acceptProposedAction()
        else: # Not needed, but good practice.
            event.ignore()


class MainWindow(QMainWindow):
    """Main application window for the Image Tagger."""

    @staticmethod
    def load_config():
        """Loads the configuration from config.json, creating it with defaults if it doesn't exist."""
        config_path = os.path.join(os.getcwd(), "config.json")
        default_config = {
            "last_opened_folder": ""
        }

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Ensure all expected keys are present, using defaults if needed
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
        except FileNotFoundError:
            print("config.json not found, creating with defaults.")
            # Create the file with default values
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2)  # Use indent for readability.
            return default_config
        except json.JSONDecodeError:
            print("Error decoding config.json. Using default values.")
            return default_config
        
    @staticmethod
    def save_config(config):
        """Saves the configuration to config.json."""
        config_path = os.path.join(os.getcwd(), "config.json")
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

    @staticmethod
    def set_config_value(key, value):
        """Sets a configuration value and saves the config file.

        Args:
            key (str): The configuration key to set.
            value (any): The value to set for the key.
        """
        config = MainWindow.load_config()  # Load existing config.
        config[key] = value  # Set the new value.
        MainWindow.save_config(config)  # Save the updated config.
    
    def _gather_all_tags(self, folder_path):
        """Gathers tag data for all images in the specified folder.

        Prioritizes loading from the workfile. Falls back to .txt files if
        workfile data is missing. Returns a dictionary where keys are image
        paths and values are lists of tags.
        """
        all_tags = {}  # Initialize an empty dictionary to store the results.
        workfile_path = self._get_workfile_path(folder_path)
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
        image_paths = []

        for filename in os.listdir(folder_path):
            if any(filename.lower().endswith(ext) for ext in image_extensions):
                image_path = os.path.join(folder_path, filename)
                image_paths.append(image_path)

        try:
            with open(workfile_path, 'r', encoding='utf-8') as f:
                workfile_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            workfile_data = {"image_tags": {}} # Initialize as though a blank workfile

        for image_path in image_paths:
            loaded_tags = [] # Initialize loaded tags

            if workfile_data:
                if image_path in workfile_data["image_tags"]:
                    loaded_tags = workfile_data["image_tags"][image_path]
                    print(f"  Loaded tags from workfile for {image_path}: {loaded_tags}")

            if not loaded_tags: # If no tags loaded from workfile (or workfile missing/corrupt)
                tag_file_path_no_ext = os.path.splitext(image_path)[0]
                tag_file_path_txt = tag_file_path_no_ext + ".txt"
                tag_file_path_ext_txt = image_path + ".txt"

                if os.path.exists(tag_file_path_txt):
                    tag_file_to_use = tag_file_path_txt
                elif os.path.exists(tag_file_path_ext_txt):
                    tag_file_to_use = tag_file_path_ext_txt
                else:
                    tag_file_to_use = None

                if tag_file_to_use:
                    print(f"  Loading tags from .txt for {image_path}")
                    try:
                        with open(tag_file_to_use, 'r', encoding='utf-8') as tag_file:
                            tag_content = tag_file.readline().strip()
                            loaded_tags = [tag.strip() for tag in tag_content.split(',')]
                    except Exception as e:
                        print(f"  Error reading tag file {tag_file_to_use}: {e}")
                        # loaded_tags remains an empty list

            all_tags[image_path] = loaded_tags  # Store the tags (even if empty)

        return all_tags
    
    def _export_tags(self):
        """Handles the export process: prompts for export directory, gathers tags, and writes files."""

        # Create the 'output' directory if it doesn't exist
        output_dir = os.path.join(os.getcwd(), "output")
        if not os.path.isdir(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        # Get the export directory from the user.
        export_dir = QFileDialog.getExistingDirectory(self, "Select Export Directory", output_dir)

        if export_dir:  # Proceed only if the user selected a directory.
            export_dir = os.path.normpath(export_dir)
            print(f"Exporting tags to: {export_dir}")

            all_tags = self._gather_all_tags(self.last_folder_path) #we assume if they are exporting, that they have opened a dir

            for image_path, tags in all_tags.items():
                filename = os.path.basename(image_path)
                base_filename, _ = os.path.splitext(filename)  # Remove extension
                txt_filename = base_filename + ".txt"
                txt_filepath = os.path.join(export_dir, txt_filename)

                try:
                    with open(txt_filepath, 'w', encoding='utf-8') as f:
                        f.write(", ".join(tags))  # Join tags with comma and space.
                    print(f"  Wrote tags for {filename} to {txt_filepath}")
                except Exception as e:
                    print(f"  Error writing to {txt_filepath}: {e}")
                    # Consider showing an error message to the user (QMessageBox).

            # Open the export directory in the file explorer.
            if sys.platform == 'win32':
                os.startfile(export_dir)
            elif sys.platform == 'darwin':  # macOS
                subprocess.Popen(['open', export_dir])
            else:  # Linux and other Unix-like
                subprocess.Popen(['xdg-open', export_dir]) # Try xdg-open (common on Linux)
        else:
            print("Export cancelled by user.")
    
    
    def __init__(self):
        """Initializes the main application window."""
        super().__init__()
        self.setWindowTitle("Image Tagger")
        self.resize(1024, 768)

        # --- Instance Variables ---
        self.image_paths = []  # List of image file paths in the currently loaded folder.
        self.current_image_index = 0  # Index of the currently displayed image.
        self.last_folder_path = None # Initialize self.last_folder_path *before* potentially loading from settings
        self.selected_tags_for_current_image = []  # List of tags selected for the current image.
        self.unknown_tags_for_current_image = []  # List of 'unknown' tags for the current image (loaded from file but not in tag_list.csv).
        self.tag_widgets_by_name = {}  # Dictionary to store TagWidget instances by tag name (for left panel lookup).
        
        # --- Load Configuration ---
        config = MainWindow.load_config()  # Load configuration using the static method.
        self.last_folder_path = config.get("last_opened_folder") # Set last folder from config
        
        # --- Staging Folder ---
        self.staging_folder_path = os.path.join(os.getcwd(), "staging")
        if not os.path.isdir(self.staging_folder_path):
            os.makedirs(self.staging_folder_path, exist_ok=True)

        # --- Setup UI and Load Tags ---
        self._setup_dark_mode_theme()
        self._setup_ui()
        self._load_tags()  # Load tags from tag_list.csv

        if (self.last_folder_path):
            print(f"Loading last opened folder: {self.last_folder_path}")
            self._load_image_folder(self.last_folder_path)  # Load last opened folder.
        else:
            print("No valid last opened folder, attempting to load initial directory.")
            self._load_initial_directory()  # Fallback to initial directory.
            # self._load_image_folder(None) May deprecate _load_initial_directory later and replace with this!

    def _setup_dark_mode_theme(self):
        """Sets up the application-wide dark mode theme."""
        app.setStyle("Fusion")  # Use the Fusion style for a consistent look.
        dark_palette = QPalette()
        dark_color = QColor(53, 53, 53)
        dark_disabled_color = QColor(127, 127, 127)
        dark_palette.setColor(QPalette.Window, dark_color)
        dark_palette.setColor(QPalette.WindowText, Qt.white)
        dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.AlternateBase, dark_color)
        dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
        dark_palette.setColor(QPalette.ToolTipText, Qt.white)
        dark_palette.setColor(QPalette.Text, Qt.white)
        dark_palette.setColor(QPalette.Disabled, QPalette.Text, dark_disabled_color)
        dark_palette.setColor(QPalette.Dark, QColor(35, 35, 35))
        dark_palette.setColor(QPalette.Shadow, QColor(20, 20, 20))
        dark_palette.setColor(QPalette.Button, dark_color)
        dark_palette.setColor(QPalette.ButtonText, Qt.white)
        dark_palette.setColor(QPalette.Disabled, QPalette.ButtonText, dark_disabled_color)
        dark_palette.setColor(QPalette.BrightText, Qt.red)
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Disabled, QPalette.Highlight, dark_disabled_color)
        dark_palette.setColor(QPalette.HighlightedText, Qt.white)
        app.setPalette(dark_palette)

    def _setup_ui(self):
        """Sets up the main user interface layout and elements."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # --- Menu Bar ---
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")  # '&' creates a keyboard shortcut (Alt+F)
        open_folder_action = file_menu.addAction("Open Folder...")
        open_folder_action.triggered.connect(self._open_folder_dialog)
        
        export_action = file_menu.addAction("Export Tags...")  # Add the Export action
        export_action.triggered.connect(self._export_tags)  # Connect it to _export_tags
        # --- End Menu Bar ---

        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)  # Remove spacing between layout elements.
        central_widget.setLayout(main_layout)

        panels_layout = QHBoxLayout()  # Horizontal layout for the three main panels.
        panels_layout.setSpacing(0)
        main_layout.addLayout(panels_layout)

        # --- Left Panel (Tag List) ---
        left_scroll_area = QScrollArea()
        left_scroll_area.setWidgetResizable(True)  # Allow the scroll area to resize its contents.
        left_scroll_area.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding) # Allow vertical expansion, fixed width.
        left_scroll_area.setFixedWidth(200)

        left_panel = QFrame()
        left_panel.setFrameShape(QFrame.StyledPanel)
        left_layout = QVBoxLayout()
        left_layout.setAlignment(Qt.AlignTop)  # Align widgets to the top of the panel.
        left_layout.setSpacing(0)
        left_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins around the layout.
        left_panel.setLayout(left_layout)
        self.tag_list_layout = left_layout  # Store the layout for later use (adding tags).

        # Search Bar for Left Panel
        self.tag_search_bar = QLineEdit()
        self.tag_search_bar.setPlaceholderText("Search tags...")
        self.tag_search_bar.setStyleSheet("color: #858585; background-color: #252525;")  # Dark theme styling.
        left_layout.addWidget(self.tag_search_bar)
        self.tag_search_bar.textChanged.connect(self._filter_tags)

        left_scroll_area.setWidget(left_panel)
        panels_layout.addWidget(left_scroll_area)

        # --- Center Panel (Image Display) ---
        self.center_panel = CenterPanel()
        self.center_panel.setFrameShape(QFrame.StyledPanel)
        self.center_panel.setMinimumSize(100, 100)  # Ensure the panel has a minimum size.
        panels_layout.addWidget(self.center_panel)

        # --- Right Panel (Selected Tags) ---
        right_scroll_area = QScrollArea()
        right_scroll_area.setWidgetResizable(True)
        right_scroll_area.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        right_scroll_area.setFixedWidth(200)

        self.right_panel = SelectionPanel(parent=self)

        right_scroll_area.setWidget(self.right_panel)
        panels_layout.addWidget(right_scroll_area)

        # --- Bottom Panel (Image Info and Buttons) ---
        bottom_panel = QFrame()
        bottom_panel.setFrameShape(QFrame.StyledPanel)
        bottom_panel.setFixedHeight(50)  # Fixed height for the bottom panel.
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(10)
        bottom_layout.setContentsMargins(10, 5, 10, 5)  # Add some margins for visual spacing.
        bottom_panel.setLayout(bottom_layout)

        # Add spacers and labels for a cleaner layout.
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

        main_layout.addWidget(bottom_panel)
        self.bottom_panel_layout = bottom_layout  # Store the layout (though we don't directly modify it later).

    def _get_workfile_path(self, folder_path):
        """Generates a valid workfile path based on the image folder path."""
        filename_safe_string = folder_path.replace(os.sep, '_').replace(':', '_') + ".json"
        return os.path.join(self.staging_folder_path, filename_safe_string)

    def _load_tags(self):
        """Loads tags from the CSV file (tag_list.csv) and populates the left panel."""
        layout = self.tag_list_layout
        tags_file_path = os.path.join("data", "tag_list.csv")
        try:
            with open(tags_file_path, 'r', encoding='utf-8') as file:
                next(file)  # Skip the header line in the CSV.
                for line in file:
                    tag_name = line.strip()  # Remove leading/trailing whitespace.
                    tag_widget = TagWidget(tag_name)  # Create a TagWidget for each tag.
                    tag_widget.tag_clicked.connect(self._handle_tag_clicked)
                    layout.addWidget(tag_widget)
                    self.tag_widgets_by_name[tag_name] = tag_widget  # Store the TagWidget instance for later lookup.
        except FileNotFoundError:
            error_label = QLabel("Error: tag_list.csv not found in 'data' folder.")
            layout.addWidget(error_label)

    def _filter_tags(self, text):
        """Filters the tags in the left panel based on the search bar text and highlights matches."""
        search_text = text.lower()  # Convert search text to lowercase for case-insensitive matching.
        highlight_color = "darkorange"
        for tag_name, tag_widget in self.tag_widgets_by_name.items():
            tag_lower = tag_name.lower()
            if search_text and search_text in tag_lower:  # Check if search text is present and not empty.
                # Construct HTML string with highlighting.
                start_index = tag_lower.find(search_text)
                end_index = start_index + len(search_text)
                highlighted_tag_name = (
                    tag_name[:start_index] +
                    f'<span style="color: {highlight_color};"><b>{tag_name[start_index:end_index]}</b></span>' +
                    tag_name[end_index:]
                )
                tag_widget.tag_label.setText(highlighted_tag_name)  # Set the QLabel text with HTML formatting.
                tag_widget.show()  # Show the TagWidget if it matches.
            elif search_text:  # If there's search text but no match, hide the tag.
                tag_widget.hide()
            else:  # If the search text is empty, reset to the plain tag name and show all.
                tag_widget.tag_label.setText(tag_name)
                tag_widget.show()

    def _load_initial_directory(self):
        """Loads images from an initial directory specified via an environment variable (for development)."""
        # --- TEMPORARY - For Development Convenience ---
        initial_directory = os.environ.get("IMAGE_TAGGER_INITIAL_DIR")

        if initial_directory:
            initial_directory = os.path.normpath(initial_directory)  # Normalize the path
            if os.path.isdir(initial_directory):
                print(f"Loading initial directory from environment variable: {initial_directory}")
                self._load_image_folder(initial_directory)
                self.last_folder_path = initial_directory  # Set for folder persistence.
                MainWindow.set_config_value("last_opened_folder", self.last_folder_path) # Save to config
            else:
                print("No valid initial directory found in IMAGE_TAGGER_INITIAL_DIR environment variable.")
                self._load_image_folder(None)
        else: #added else to account for None
            print("No valid initial directory found in IMAGE_TAGGER_INITIAL_DIR environment variable.")
            self._load_image_folder(None)
        # --- END TEMPORARY ---

    def _open_folder_dialog(self):
        """Opens a folder selection dialog and loads images from the selected folder."""
        start_directory = os.path.expanduser("~")  # Default to the user's home directory.
        if self.last_folder_path and os.path.isdir(self.last_folder_path):
            start_directory = self.last_folder_path  # Use the last folder path if it's valid.

        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Image Folder",
            start_directory,  # Start in the home directory or the last used directory.
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks  # Only show directories.
        )

        if folder_path:
            folder_path = os.path.normpath(folder_path)
            self.last_folder_path = folder_path  # Update last_folder_path.
            MainWindow.set_config_value("last_opened_folder", self.last_folder_path) 
            self._load_image_folder(folder_path)

    def _load_image_folder(self, folder_path):
        """Loads images from the given folder path and updates the UI."""
        if not folder_path:
            print("No folder path provided to _load_image_folder, handling as no images.")
            self.image_paths = []
            self.center_panel.clear()
            self.center_panel.setText("Initial directory not found:\ninput")  # Display an error message.
            self.filename_label.setText("No Image")
            self.index_label.setText("0 of 0")
            self.prev_button.setEnabled(False)
            self.next_button.setEnabled(False)
            return

        workfile_path = self._get_workfile_path(folder_path)
        if not os.path.exists(workfile_path):
            # Create a new, empty workfile
            try:
                with open(workfile_path, 'w', encoding='utf-8') as f:
                    json.dump({"image_tags": {}}, f)
            except Exception as e:
                print("error creating workfile")

        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']  # Supported image extensions.
        self.image_paths = []

        for filename in os.listdir(folder_path):
            if any(filename.lower().endswith(ext) for ext in image_extensions):
                image_path = os.path.join(folder_path, filename)
                self.image_paths.append(image_path)

        if self.image_paths:
            print(f"Found {len(self.image_paths)} images in folder: {folder_path}")
            self.current_image_index = 0
            self._load_and_display_image(self.image_paths[0])  # Load and display the first image.
            self._update_index_label()
            self.prev_button.setEnabled(True)  # Enable navigation buttons.
            self.next_button.setEnabled(True)
        else:
            print(f"No images found in folder: {folder_path}")
            self.center_panel.clear()
            self.center_panel.setText("No images found in this folder.")
            self.filename_label.setText("No Image")
            self.index_label.setText("0 of 0")
            self.prev_button.setEnabled(False)  # Disable navigation buttons.
            self.next_button.setEnabled(False)

    def _load_and_display_image(self, image_path):
        """Loads and displays an image, loads associated tags, identifies unknown tags."""
        # --- Clear Left Panel Selections ---
        print("  Clearing left panel selections...")
        for _, tag_widget in self.tag_widgets_by_name.items():  # Iterate through all TagWidgets.
            tag_widget.set_selected(False)  # Deselect each TagWidget.
        # --- End Clear Left Panel Selections ---

        self.center_panel.set_image_path(image_path)
        filename = os.path.basename(image_path)
        self.filename_label.setText(filename)

        loaded_tags_from_workfile = False  # Flag to track if tags were loaded from workfile.
        workfile_path = self._get_workfile_path(self.last_folder_path) # Get workfile path

        if os.path.exists(workfile_path): # Check if workfile exists
            try:
                with open(workfile_path, 'r', encoding='utf-8') as f:
                    workfile_data = json.load(f) # Load workfile JSON

                    image_key = image_path # Use full image path as key
                    if image_key in workfile_data["image_tags"]: # Check if image has tags in workfile
                        loaded_tags = workfile_data["image_tags"][image_key] # Load tags from workfile
                        print(f"  Loaded tags from workfile: {loaded_tags}")
                        loaded_tags_from_workfile = True # Set the flag
                    else:
                        print("  No tags found in workfile for this image. (Falling back to .txt or empty)")
            except FileNotFoundError:
                print(f"  Workfile not found (though existence was just checked). This is unexpected.") # Should not happen
            except json.JSONDecodeError:
                print(f"  Error reading workfile (JSON error). Falling back to .txt or empty.")
        else:
            print("  No workfile found. Falling back to .txt or empty.")

        if loaded_tags_from_workfile:
            print("  Skipping .txt file loading because tags were loaded from workfile.")
            pass # Skip the .txt loading logic below
        else:
            # --- Tag File Loading Logic (Existing - will only execute if not loaded from workfile) ---
            tag_file_path_no_ext = os.path.splitext(image_path)[0]  # Get path without extension.
            tag_file_path_txt = tag_file_path_no_ext + ".txt"  # Path with .txt extension.
            tag_file_path_ext_txt = image_path + ".txt"  # Path with .jpg.txt (or other image extension) + .txt.

            loaded_tags = [] # Initialize loaded_tags again here for .txt loading fallback

            if os.path.exists(tag_file_path_txt):
                tag_file_to_use = tag_file_path_txt
            elif os.path.exists(tag_file_path_ext_txt):
                tag_file_to_use = tag_file_path_ext_txt
            else:
                tag_file_to_use = None

            if tag_file_to_use:
                print(f"  Loading tags from: {tag_file_to_use}")
                try:
                    with open(tag_file_to_use, 'r', encoding='utf-8') as tag_file:
                        tag_content = tag_file.readline().strip()  # Read the first line and remove whitespace.
                        loaded_tags = [tag.strip() for tag in tag_content.split(',')]  # Split by comma, strip each tag.
                        print(f"  Loaded tags from .txt file: {loaded_tags}")
                except Exception as e:
                    print(f"  Error reading tag file: {e}")
                    loaded_tags = []  # Ensure loaded_tags is empty on error.
            else:
                print("  No tag file found for this image.")
                loaded_tags = []  # Ensure loaded_tags is empty if no file is found.

        # --- Identify Unknown Tags ---
        unknown_tags_for_current_image = []
        known_tag_names = set(self.tag_widgets_by_name.keys()) # Efficient lookup for known tags.

        for tag_name in loaded_tags:
            if tag_name not in known_tag_names:
                unknown_tags_for_current_image.append(tag_name)
                print(f"  Unknown tag loaded: '{tag_name}'")

        print(f"  Known tags loaded: {[tag for tag in loaded_tags if tag not in unknown_tags_for_current_image]}")
        self.unknown_tags_for_current_image = unknown_tags_for_current_image  # Store unknown tags.

        # --- Update Selected Tags and UI ---
        self._update_selected_tags(loaded_tags)  # Use the central update function.

    def _update_index_label(self):
        """Updates the image index label in the bottom panel."""
        if self.image_paths:
            index_text = f"{self.current_image_index + 1} of {len(self.image_paths)}"
        else:
            index_text = "0 of 0"  # If no images are loaded.
        self.index_label.setText(index_text)

    def _prev_image(self):
        """Navigates to the previous image in the list."""
        if not self.image_paths:
            return

        self.current_image_index -= 1
        if self.current_image_index < 0:
            self.current_image_index = len(self.image_paths) - 1  # Wrap around to the last image.

        image_path = self.image_paths[self.current_image_index]
        self._load_and_display_image(image_path)  # Load and display the previous image.
        self._update_index_label() # Update index

    def _next_image(self):
        """Navigates to the next image in the list."""
        if not self.image_paths:
            return

        self.current_image_index += 1
        if self.current_image_index >= len(self.image_paths):
            self.current_image_index = 0  # Wrap around to the first image.

        image_path = self.image_paths[self.current_image_index]
        self._load_and_display_image(image_path)  # Load and display the next image.
        self._update_index_label() # Update index

    def _handle_tag_clicked(self, tag_name):
        """Handles clicks on tags in the left panel (tag list)."""
        current_selected_tags = list(self.selected_tags_for_current_image)  # Work with a *copy* of the list.

        if tag_name not in current_selected_tags:
            current_selected_tags.append(tag_name)
            print(f"Tag '{tag_name}' selected and added (via left panel click).")
        else:
            current_selected_tags.remove(tag_name)
            print(f"Tag '{tag_name}' deselected and removed (via left panel click).")

        self._update_selected_tags(current_selected_tags)  # Use the central update function.
    
    def _update_right_panel_display(self):
        """Updates the right panel to display the currently selected tags."""
        # Clear existing widgets:
        for i in reversed(range(self.right_panel.layout.count())):
            widget = self.right_panel.layout.itemAt(i).widget()
            if isinstance(widget, TagWidget):  # Only remove TagWidgets
                widget.setParent(None)
                widget.deleteLater()

        # Add new widgets based on selected tag *names*:
        for tag_name in self.selected_tags_for_current_image:
            is_known = tag_name in self.tag_widgets_by_name
            tag_widget = TagWidget(tag_name, is_known_tag=is_known)
            tag_widget.tag_clicked.connect(self._handle_tag_clicked) # we now route ALL clicks through this
            self.right_panel.layout.addWidget(tag_widget)

        print(f"Right panel updated. Selected tags: {self.selected_tags_for_current_image}")

    def _update_selected_tags(self, new_tag_list):
        """Updates the selected_tags_for_current_image list and triggers UI updates.  This is the central point for all tag selection modifications."""
        print(f"Updating selected tags to: {new_tag_list}")

        self.selected_tags_for_current_image = new_tag_list  # Update the authoritative list.

        self._update_right_panel_display()  # Update the right panel.
        self._update_left_panel_display_based_on_selection()  # Update the left panel.

        # --- Workfile saving ---
        if self.last_folder_path:  # Only save if a folder has been loaded.
            workfile_path = self._get_workfile_path(self.last_folder_path)  # Get the workfile path.

            try:
                with open(workfile_path, 'r+', encoding='utf-8') as f:  # Open in read-write mode.
                    data = json.load(f)  # Load existing data from the workfile.

                    # Update the 'image_tags' dictionary with the current image's tags.
                    data["image_tags"][self.image_paths[self.current_image_index]] = self.selected_tags_for_current_image

                    f.seek(0)  # Rewind the file pointer to the beginning.
                    json.dump(data, f, indent=2)  # Write the updated data back, pretty-printed.
                    f.truncate() # needed when going from larger file to smaller file size

            except FileNotFoundError:
                print(f"Error: Workfile not found at {workfile_path}. This should not happen.")
                # TODO: Consider creating a new workfile here, or prompting the user.

            except json.JSONDecodeError:
                print(f"Error: Corrupted workfile at {workfile_path}.")
                # TODO: Consider prompting the user to delete or recover the workfile.

    def _update_left_panel_display_based_on_selection(self):
        """Updates the visual selection state of tags in the left panel based on selected_tags_for_current_image."""
        print("  Updating left panel selection states...")
        for tag_name, tag_widget in self.tag_widgets_by_name.items():
            tag_widget.set_selected(tag_name in self.selected_tags_for_current_image)  # Select/deselect based on presence in the list.

app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec()