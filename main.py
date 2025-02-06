import sys
import os
from tag_widget import TagWidget
from center_panel import CenterPanel
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QFrame, QLabel,
                             QSizePolicy, QVBoxLayout, QScrollArea, QPushButton, QSpacerItem,
                             QFileDialog, QLineEdit)
from PySide6.QtGui import QColor, QPalette
from PySide6.QtCore import Qt

class MainWindow(QMainWindow):
    """Main application window for the Image Tagger."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Tagger")
        self.resize(1024, 768)

        self.image_paths = []  # List of image file paths in the loaded folder
        self.current_image_index = 0  # Index of the currently displayed image
        self.last_folder_path = None  # Path of the last loaded folder (for persistence)
        self.selected_tags_for_current_image = []  # List of tags selected for the current image (tag names)
        self.tag_widgets_by_name = {}  # Dictionary to store TagWidget instances by tag name (for left panel)

        self._setup_dark_mode_theme()
        self._setup_ui()
        self._load_tags()
        self._load_initial_directory()

    def _setup_dark_mode_theme(self):
        """Sets up the application-wide dark mode theme."""
        app.setStyle("Fusion")
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
        file_menu = menu_bar.addMenu("&File")
        open_folder_action = file_menu.addAction("Open Folder...")
        open_folder_action.triggered.connect(self._open_folder_dialog)
        # --- End Menu Bar ---

        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        central_widget.setLayout(main_layout)

        panels_layout = QHBoxLayout()
        panels_layout.setSpacing(0)
        main_layout.addLayout(panels_layout)

        # Left Panel - Tag List
        left_scroll_area = QScrollArea()
        left_scroll_area.setWidgetResizable(True)
        left_scroll_area.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        left_scroll_area.setFixedWidth(200)

        left_panel = QFrame()
        left_panel.setFrameShape(QFrame.StyledPanel)
        left_layout = QVBoxLayout()
        left_layout.setAlignment(Qt.AlignTop)
        left_layout.setSpacing(0)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_panel.setLayout(left_layout)
        self.tag_list_layout = left_layout

        # Search Bar for Left Panel
        self.tag_search_bar = QLineEdit()  # Search input field
        self.tag_search_bar.setPlaceholderText("Search tags...")
        self.tag_search_bar.setStyleSheet("color: #858585; background-color: #252525;")  # Style to match dark theme
        left_layout.addWidget(self.tag_search_bar)
        self.tag_search_bar.textChanged.connect(self._filter_tags)

        left_scroll_area.setWidget(left_panel)
        panels_layout.addWidget(left_scroll_area)

        # Center Panel - Image Display
        self.center_panel = CenterPanel()
        self.center_panel.setFrameShape(QFrame.StyledPanel)
        self.center_panel.setMinimumSize(100, 100)
        panels_layout.addWidget(self.center_panel)

        # Right Panel - Selected Tags
        right_scroll_area = QScrollArea()
        right_scroll_area.setWidgetResizable(True)
        right_scroll_area.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        right_scroll_area.setFixedWidth(200)

        self.right_panel = QFrame()  # Container for selected tags
        self.right_panel.setFrameShape(QFrame.StyledPanel)
        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignTop)
        right_layout.setSpacing(0)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_panel.setLayout(right_layout)
        self.right_panel_layout = right_layout

        right_scroll_area.setWidget(self.right_panel)
        panels_layout.addWidget(right_scroll_area)

        # Bottom Panel - Image Info and Buttons
        bottom_panel = QFrame()
        bottom_panel.setFrameShape(QFrame.StyledPanel)
        bottom_panel.setFixedHeight(50)
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(10)
        bottom_layout.setContentsMargins(10, 5, 10, 5)
        bottom_panel.setLayout(bottom_layout)

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
        self.bottom_panel_layout = bottom_layout

    def _load_tags(self):
        """Loads tags from CSV file and populates the left panel."""
        layout = self.tag_list_layout
        tags_file_path = os.path.join("data", "tag_list.csv")
        try:
            with open(tags_file_path, 'r', encoding='utf-8') as file:
                next(file)  # Skip header line
                for line in file:
                    tag_name = line.strip()
                    tag_widget = TagWidget(tag_name)
                    tag_widget.tag_clicked.connect(self._handle_tag_clicked_left_panel)
                    layout.addWidget(tag_widget)
                    self.tag_widgets_by_name[tag_name] = tag_widget  # Store TagWidget instance by name
        except FileNotFoundError:
            error_label = QLabel("Error: tag_list.csv not found in 'data' folder.")
            layout.addWidget(error_label)

    def _filter_tags(self, text):
        """Filters the tags in the left panel and highlights the search term in light yellow."""
        search_text = text.lower()
        highlight_color = "darkorange"  # Define the highlight color here
        for tag_name, tag_widget in self.tag_widgets_by_name.items():
            tag_lower = tag_name.lower()
            if search_text and search_text in tag_lower:
                start_index = tag_lower.find(search_text)
                end_index = start_index + len(search_text)

                highlighted_tag_name = (
                    tag_name[:start_index] +
                    f'<span style="color: {highlight_color};"><b>{tag_name[start_index:end_index]}</b></span>' +
                    tag_name[end_index:]
                )
                tag_widget.tag_label.setText(highlighted_tag_name)
                tag_widget.show()
            elif search_text:
                tag_widget.hide()
            else:
                tag_widget.tag_label.setText(tag_name)
                tag_widget.show()
    
    def _load_initial_directory(self):
        """Loads images from a hardcoded initial directory for development."""
        sample_directory = r"J:\Repositories\image_tagger_app\input"  # <--- !!!  Set your sample directory here
        if os.path.isdir(sample_directory):
            print(f"Loading initial directory: {sample_directory}")
            self._load_image_folder(sample_directory)
            self.last_folder_path = sample_directory  # Set last_folder_path for folder persistence
        else:
            print(f"Initial directory not found: {sample_directory}")
            self._load_image_folder(None)

    def _open_folder_dialog(self):
        """Opens a folder selection dialog, loads images, and updates UI.
        Preserves and reuses the last selected folder path."""
        start_directory = os.path.expanduser("~")  # Default to home directory
        if self.last_folder_path and os.path.isdir(self.last_folder_path):
            start_directory = self.last_folder_path  # Use last folder path if valid

        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Image Folder",
            start_directory,  # Use start_directory (either last path or home dir)
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )

        if folder_path:
            self.last_folder_path = folder_path  # Update last_folder_path with newly selected path
            self._load_image_folder(folder_path)  # Call the new method to load images and update UI

    def _load_image_folder(self, folder_path):
        """Loads images from the given folder path and updates the UI."""
        if not folder_path:  # Handle None folder_path (e.g., invalid initial directory)
            print("No folder path provided to _load_image_folder, handling as no images.")
            self.image_paths = []
            self.center_panel.clear()
            self.center_panel.setText("Initial directory not found:\ninput")  # Using "input" as placeholder
            self.filename_label.setText("No Image")
            self.index_label.setText("0 of 0")
            self.prev_button.setEnabled(False)
            self.next_button.setEnabled(False)
            return

        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']  # Common image extensions
        self.image_paths = []

        for filename in os.listdir(folder_path):
            if any(filename.lower().endswith(ext) for ext in image_extensions):
                image_path = os.path.join(folder_path, filename)
                self.image_paths.append(image_path)

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
        """Loads and displays an image, and now loads associated tags and clears previous selections."""
        # --- Clear Left Panel Selections ---
        print("  Clearing left panel selections...") # Debug message
        for tag_name, tag_widget in self.tag_widgets_by_name.items(): # Iterate through all TagWidgets
            tag_widget.set_selected(False) # Deselect each TagWidget
        # --- End Clear Left Panel Selections ---

        self.center_panel.set_image_path(image_path)
        filename = os.path.basename(image_path)
        self.filename_label.setText(filename)

        # --- Tag File Loading Logic ---
        tag_file_path_no_ext = os.path.splitext(image_path)[0] # Path without image extension
        tag_file_path_txt = tag_file_path_no_ext + ".txt"      # Try .txt extension
        tag_file_path_ext_txt = image_path + ".txt"           # Try .jpg.txt extension (or .png.txt etc.)

        loaded_tags = [] # Initialize an empty list to store loaded tags

        if os.path.exists(tag_file_path_txt): # Check for .txt tag file first
            tag_file_to_use = tag_file_path_txt
        elif os.path.exists(tag_file_path_ext_txt): # If not, check for .jpg.txt style
            tag_file_to_use = tag_file_path_ext_txt
        else:
            tag_file_to_use = None # No tag file found

        if tag_file_to_use:
            print(f"  Loading tags from: {tag_file_to_use}") # Indicate tag file loading
            try:
                with open(tag_file_to_use, 'r', encoding='utf-8') as tag_file:
                    tag_content = tag_file.readline().strip() # Read the first line and strip whitespace
                    loaded_tags = [tag.strip() for tag in tag_content.split(',')] # Split by comma and space, strip tags
                    print(f"  Loaded tags: {loaded_tags}") # Print the loaded tags to console
            except Exception as e: # Catch any potential errors during file reading
                print(f"  Error reading tag file: {e}") # Print error message if something goes wrong
        else:
            print("  No tag file found for this image.") # Indicate no tag file found
            loaded_tags = [] # Ensure loaded_tags is empty if no file

        self.selected_tags_for_current_image = loaded_tags # For now, just set loaded tags as selected
        # --- Left Panel Tag Synchronization ---
        for tag_name in loaded_tags: # Iterate through loaded tags
            tag_widget = self.tag_widgets_by_name.get(tag_name) # Try to get TagWidget from left panel
            if tag_widget: # If TagWidget found in left panel
                tag_widget.set_selected(True) # Visually select it in left panel
                print(f"  Synchronized left panel: Tag '{tag_name}' selected.") # Debug message
            else:
                print(f"  Warning: TagWidget not found in left panel for loaded tag '{tag_name}'.") # Warning if not found
        # --- End Left Panel Tag Synchronization ---
        self._update_right_panel_display() # Update right panel to show loaded tags
        # --- End Tag File Loading Logic ---

    def _update_index_label(self):
        """Updates the image index label in the bottom panel."""
        if self.image_paths:
            index_text = f"{self.current_image_index + 1} of {len(self.image_paths)}"
        else:
            index_text = "0 of 0"  # No images loaded
        self.index_label.setText(index_text)

    def _prev_image(self):
        """Navigates to the previous image in the list."""
        if not self.image_paths:
            return

        self.current_image_index -= 1

        if self.current_image_index < 0:
            self.current_image_index = len(self.image_paths) - 1

        image_path = self.image_paths[self.current_image_index]
        self._load_and_display_image(image_path)
        self._update_index_label()

    def _next_image(self):
        """Navigates to the next image in the list."""
        if not self.image_paths:
            return

        self.current_image_index += 1

        if self.current_image_index >= len(self.image_paths):
            self.current_image_index = 0

        image_path = self.image_paths[self.current_image_index]
        self._load_and_display_image(image_path)
        self._update_index_label()

    def _handle_tag_clicked_left_panel(self, tag_name):
        """Handles clicks on tags in the left panel. Adds/removes tag from selected tags and updates UI."""
        tag_widget = self.tag_widgets_by_name.get(tag_name)  # Get TagWidget instance from dictionary
        if not tag_widget:
            print(f"Warning: TagWidget not found for tag name: {tag_name}")  # Debug - should not happen, but safety check
            return

        if tag_name not in self.selected_tags_for_current_image:  # Tag is NOT currently selected
            self.selected_tags_for_current_image.append(tag_name)  # Add tag to selected list
            print(f"Tag '{tag_name}' selected and added to right panel (via left panel click).")  # Debug
            tag_widget.set_selected(True)  # Visually mark tag as selected in left panel
        else:  # Tag IS already selected (deselecting)
            self.selected_tags_for_current_image.remove(tag_name)  # Remove tag from selected list
            print(f"Tag '{tag_name}' deselected and removed from right panel (via left panel click).")  # Debug
            tag_widget.set_selected(False)  # Visually mark tag as unselected in left panel

        self._update_right_panel_display()  # Update right panel AFTER any changes

    def _handle_tag_clicked_right_panel_tag_widget(self, tag_name):
        """Handles clicks on TagWidgets in the right panel. Deselects and removes the tag, and deselects in left panel."""
        if tag_name in self.selected_tags_for_current_image:
            self.selected_tags_for_current_image.remove(tag_name)  # Remove tag from selected list
            print(f"Tag '{tag_name}' deselected and removed from right panel (via TagWidget click).")  # Debug

            tag_widget_left_panel = self.tag_widgets_by_name.get(tag_name)  # Get TagWidget instance from left panel
            if tag_widget_left_panel:
                tag_widget_left_panel.set_selected(False)  # Visually mark tag as unselected in left panel
                print(f"  Synchronized left panel: Tag '{tag_name}' deselected (via right panel click).") # Debug
            else:
                print(f"  Warning: TagWidget not found in left panel for tag name: {tag_name} (right panel TagWidget click).")  # Debug - should not happen

            self._update_right_panel_display()  # Update right panel AFTER removing tag
        else:
            print(f"Tag '{tag_name}' not in selected tags (right panel TagWidget click issue?).")  # Debug - should not happen

    def _update_right_panel_display(self):
        """Updates the right panel to display the currently selected tags."""
        layout = self.right_panel_layout
        for i in reversed(range(layout.count())):  # Clear existing widgets in layout
            layout.itemAt(i).widget().setParent(None)  # Remove widget from layout and set parent to None for cleanup

        for tag_name in self.selected_tags_for_current_image:
            tag_widget = TagWidget(tag_name)  # Create a TagWidget instance for each tag
            tag_widget.tag_clicked.connect(self._handle_tag_clicked_right_panel_tag_widget)
            layout.addWidget(tag_widget)  # Add TagWidget to the right panel layout
        print(f"Right panel updated. Selected tags: {self.selected_tags_for_current_image}")  # Debug


app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec()