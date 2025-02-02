import sys
import os
from tag_widget import TagWidget
from center_panel import CenterPanel
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget,
                             QHBoxLayout, QFrame, QLabel, QListWidget,
                             QSizePolicy, QVBoxLayout, QScrollArea, QPushButton, QSpacerItem, QFileDialog, QListWidgetItem)
from PySide6.QtGui import QColor, QPalette, QPixmap, QImage
from PySide6.QtCore import Qt

class MainWindow(QMainWindow):
    """Main application window for the Image Tagger."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Tagger")
        self.resize(1024, 768)

        self.image_paths = []
        self.current_image_index = 0
        self.last_folder_path = None
        self.selected_tags_for_current_image = []
        self.tag_widgets_by_name = {}
        
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
        self.tag_list_layout = left_layout # Store layout for tag loading

        left_scroll_area.setWidget(left_panel)
        panels_layout.addWidget(left_scroll_area)

        # Center Panel - Image Display
        self.center_panel = CenterPanel()
        self.center_panel.setFrameShape(QFrame.StyledPanel)
        self.center_panel.setMinimumSize(100, 100)  # Set minimum size
        panels_layout.addWidget(self.center_panel)

        # Right Panel - Selected Tags (Currently Placeholder)
        self.right_panel = QListWidget()
        self.right_panel.setFrameShape(QFrame.StyledPanel)
        self.right_panel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.right_panel.setFixedWidth(200)
        self.right_panel.itemClicked.connect(self._handle_tag_clicked_right_panel)
        panels_layout.addWidget(self.right_panel)

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
        self.bottom_panel_layout = bottom_layout # Store for potential future use

    def _load_tags(self):
        """Loads tags from CSV file and populates the left panel."""
        layout = self.tag_list_layout
        tags_file_path = os.path.join("data", "tag_list.csv")
        try:
            with open(tags_file_path, 'r', encoding='utf-8') as file:
                next(file) # Skip header line
                for line in file:
                    tag_name = line.strip()
                    tag_widget = TagWidget(tag_name)
                    tag_widget.tag_clicked.connect(self._handle_tag_clicked_left_panel)
                    layout.addWidget(tag_widget)
                    self.tag_widgets_by_name[tag_name] = tag_widget
        except FileNotFoundError:
            error_label = QLabel("Error: tag_list.csv not found in 'data' folder.")
            layout.addWidget(error_label)

    def _load_initial_directory(self):
            """Loads images from a hardcoded initial directory for development."""
            sample_directory = r"J:\Repositories\image_tagger_app\input"  # <--- !!!  Set your sample directory here !!!
            if os.path.isdir(sample_directory): # Check if the directory exists
                print(f"Loading initial directory: {sample_directory}") # Debug print
                self._load_image_folder(sample_directory) # Load images from sample directory
                self.last_folder_path = sample_directory # Set last_folder_path to initial directory
            else:
                print(f"Initial directory not found: {sample_directory}") # Debug print
                self._load_image_folder(None)

    def _open_folder_dialog(self):
            """Opens a folder selection dialog, loads images, and updates UI.
            Preserves and reuses the last selected folder path."""

            start_directory = os.path.expanduser("~") # Default to home directory
            if self.last_folder_path and os.path.isdir(self.last_folder_path): # Check if last path is valid
                start_directory = self.last_folder_path # Use last folder path if valid

            folder_path = QFileDialog.getExistingDirectory(
                self,
                "Select Image Folder",
                start_directory, # Use start_directory (either last path or home dir)
                QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
            )

            if folder_path:
                self.last_folder_path = folder_path # Update last_folder_path with newly selected path
                self._load_image_folder(folder_path) # Call the new method to load images and update UI

    def _load_image_folder(self, folder_path):
        """Loads images from the given folder path and updates the UI."""
        if not folder_path: # Handle None folder_path (e.g., invalid initial directory)
            print("No folder path provided to _load_image_folder, handling as no images.") # Debug
            self.image_paths = [] # Clear image paths
            self.center_panel.clear() # Clear center panel
            self.center_panel.setText(f"Initial directory not found:\n{r'input'}") # Display error message, use 'input' as placeholder
            self.filename_label.setText("No Image") # Clear filename label
            self.index_label.setText("0 of 0") # Update index label to 0 of 0
            self.prev_button.setEnabled(False) # Disable "Prev" button
            self.next_button.setEnabled(False) # Disable "Next" button
            return # Exit the method early        
        
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp'] # Common image extensions
        self.image_paths = [] # Initialize image_paths list

        for filename in os.listdir(folder_path): # Iterate through files in folder
            if any(filename.lower().endswith(ext) for ext in image_extensions): # Check for image extension
                image_path = os.path.join(folder_path, filename) # Create full path
                self.image_paths.append(image_path) # Add to image paths list

        if self.image_paths: # If we found images
            print(f"Found {len(self.image_paths)} images in folder: {folder_path}") # Debug print
            self.current_image_index = 0 # Initialize image index
            self._load_and_display_image(self.image_paths[0]) # Load and display first image
            self._update_index_label() # Update index label
            self.prev_button.setEnabled(True)  # Enable "Prev" button
            self.next_button.setEnabled(True)  # Enable "Next" button
        else: # No images found
            print(f"No images found in folder: {folder_path}") # Debug print
            self.center_panel.clear() # Clear center panel
            self.center_panel.setText("No images found in this folder.") # Display message
            self.filename_label.setText("No Image") # Clear filename label
            self.index_label.setText("0 of 0") # Update index label to 0 of 0
            self.prev_button.setEnabled(False) # Disable "Prev" button
            self.next_button.setEnabled(False) # Disable "Next" button
    
    def _load_and_display_image(self, image_path):
        """Loads and displays an image in the center panel and updates filename label."""
        self.center_panel.set_image_path(image_path) # Use CenterPanel's method to load and display
        filename = os.path.basename(image_path)
        self.filename_label.setText(filename) # Update filename label

    def _update_index_label(self):
        """Updates the image index label in the bottom panel."""
        if self.image_paths:
            index_text = f"{self.current_image_index + 1} of {len(self.image_paths)}"
        else:
            index_text = "0 of 0" # No images loaded
        self.index_label.setText(index_text)

    def _prev_image(self):
        """Navigates to the previous image in the list."""
        if not self.image_paths: # No images loaded, do nothing
            return

        self.current_image_index -= 1 # Decrement index

        if self.current_image_index < 0: # Wrap around to the last image if needed
            self.current_image_index = len(self.image_paths) - 1

        image_path = self.image_paths[self.current_image_index] # Get path of previous image
        self._load_and_display_image(image_path) # Load and display
        self._update_index_label() # Update index label

    def _next_image(self):
        """Navigates to the next image in the list."""
        if not self.image_paths: # No images loaded, do nothing
            return

        self.current_image_index += 1 # Increment index

        if self.current_image_index >= len(self.image_paths): # Wrap around to the first image if needed
            self.current_image_index = 0

        image_path = self.image_paths[self.current_image_index] # Get path of next image
        self._load_and_display_image(image_path) # Load and display
        self._update_index_label() # Update index label

    def _handle_tag_clicked_left_panel(self, tag_name):
        """Handles clicks on tags in the left panel. Adds tag to selected tags."""
        tag_widget = self.tag_widgets_by_name.get(tag_name) # Get TagWidget instance from dictionary
        if not tag_widget:
            print(f"Warning: TagWidget not found for tag name: {tag_name}") # Debug - should not happen, but safety check
            return
        
        if tag_name not in self.selected_tags_for_current_image: # Prevent duplicates
            self.selected_tags_for_current_image.append(tag_name)
            print(f"Tag '{tag_name}' selected and added to right panel.") # Debug
            self._update_right_panel_display() # Update right panel after adding tag
            tag_widget.set_selected(True)
        else: # Tag was already selected, so deselect it
            self.selected_tags_for_current_image.remove(tag_name) # Remove tag from selected list
            print(f"Tag '{tag_name}' deselected and removed from right panel.") # Debug
            self._update_right_panel_display() # Update right panel after removing tag
            tag_widget.set_selected(False) # Visually mark tag as unselected in left panel
    
    def _handle_tag_clicked_right_panel(self, item):
        """Handles clicks on tags in the right panel. Removes tag from selected tags."""
        tag_name = item.text() # Get tag name from the clicked QListWidgetItem
        if tag_name in self.selected_tags_for_current_image:
            self.selected_tags_for_current_image.remove(tag_name) # Remove tag from selected list
            print(f"Tag '{tag_name}' deselected and removed from right panel.") # Debug
            self._update_right_panel_display() # Update right panel after removing tag
            tag_widget = self.tag_widgets_by_name.get(tag_name)
            if tag_widget:
                tag_widget.set_selected(False)
            else:
                print(f"Warning: TagWidget not found for tag name: {tag_name} (right panel click).")
        else:
            print(f"Tag '{tag_name}' not in selected tags (right panel click issue?).") # Debug - should not happen
    
    def _update_right_panel_display(self):
        """Updates the right panel to display the currently selected tags."""
        self.right_panel.clear() # Clear the right panel

        for tag_name in self.selected_tags_for_current_image: # Iterate through selected tags
            item = QListWidgetItem(tag_name) # Create a QListWidgetItem for each tag
            self.right_panel.addItem(item) # Add item to the right panel list
        print(f"Right panel updated. Selected tags: {self.selected_tags_for_current_image}") # Debug


app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec()