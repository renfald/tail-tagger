import sys
import os
import json
import theme
from config_manager import ConfigManager
from file_operations import FileOperations
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QFrame, QLabel,
                             QSizePolicy, QVBoxLayout, QScrollArea, QPushButton, QSpacerItem,
                             QFileDialog, QListView)
from PySide6.QtGui import QColor, QPalette
from PySide6.QtCore import Qt
from center_panel import CenterPanel #Added back import

class MainWindow(QMainWindow):
    """Main application window for the Image Tagger."""

    def __init__(self):
        """Initializes the main application window."""
        super().__init__()
        self.setWindowTitle("Image Tagger")
        self.resize(1024, 768)

        # --- Instance Variables ---
        self.image_paths = []  # List of image file paths.
        self.current_image_index = 0  # Index of the currently displayed image.
        self.last_folder_path = None  # Initialize.
        self.selected_tags_for_current_image = []  # List of tags for the current image.

        # --- Staging Folder ---
        self.staging_folder_path = os.path.join(os.getcwd(), "staging")
        if not os.path.isdir(self.staging_folder_path):
            os.makedirs(self.staging_folder_path, exist_ok=True)

        # --- Load Configuration ---
        self.config_manager = ConfigManager()
        config = self.config_manager.config  # Get the loaded config
        self.last_folder_path = config.get("last_opened_folder") # Set last folder from config

        # --- File Operations ---
        self.file_operations = FileOperations(self.staging_folder_path)

        # --- Setup UI and Load Tags/Images ---
        #self._setup_dark_mode_theme()
        self._setup_ui()
        # self._load_tags()  # Removed

        if (self.last_folder_path):
            print(f"Loading last opened folder: {self.last_folder_path}")
            self._load_image_folder(self.last_folder_path)
        else:
            print("No valid last opened folder, attempting to load initial directory.")
            self._load_initial_directory()
            # self._load_image_folder(None) # May deprecate

    def _setup_ui(self):
        """Sets up the main user interface layout and elements."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # --- Menu Bar ---
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")
        open_folder_action = file_menu.addAction("Open Folder...")
        open_folder_action.triggered.connect(self._open_folder_dialog)

        export_action = file_menu.addAction("Export Tags...")  # Add the Export action
        export_action.triggered.connect(self._export_tags)
        # --- End Menu Bar ---

        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        central_widget.setLayout(main_layout)

        panels_layout = QHBoxLayout()
        panels_layout.setSpacing(0)
        main_layout.addLayout(panels_layout)

        # --- Left Panel (Tag List) ---
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

        left_scroll_area.setWidget(left_panel)
        panels_layout.addWidget(left_scroll_area)

        # --- Center Panel (Image Display) ---
        self.center_panel = CenterPanel()
        self.center_panel.setFrameShape(QFrame.StyledPanel)
        self.center_panel.setMinimumSize(100, 100)
        panels_layout.addWidget(self.center_panel)

        # --- Right Panel (Selected Tags) ---
        right_scroll_area = QScrollArea()
        right_scroll_area.setWidgetResizable(True)
        right_scroll_area.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        right_scroll_area.setFixedWidth(200)

        self.right_panel = QFrame() # Use a basic QFrame as placeholder

        right_scroll_area.setWidget(self.right_panel)
        panels_layout.addWidget(right_scroll_area)

        # --- Bottom Panel (Image Info and Buttons) ---
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

    def _load_initial_directory(self):
        """Loads images from an initial directory (environment variable)."""
        initial_directory = os.environ.get("IMAGE_TAGGER_INITIAL_DIR")

        if initial_directory:
            initial_directory = os.path.normpath(initial_directory)
            if os.path.isdir(initial_directory):
                print(f"Loading initial directory: {initial_directory}")
                self._load_image_folder(initial_directory)
                self.last_folder_path = initial_directory
                self.config_manager.set_config_value("last_opened_folder", self.last_folder_path) # Save to config
            else:
                print("No valid initial directory found.")
                self._load_image_folder(None)
        else:
            print("No initial directory found in env variable")
            self._load_image_folder(None)

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
            self.center_panel.setText("Initial directory not found:\ninput")
            self.filename_label.setText("No Image")
            self.index_label.setText("0 of 0")
            self.prev_button.setEnabled(False)
            self.next_button.setEnabled(False)
            return

        workfile_path = self.file_operations.get_workfile_path(folder_path)
        if not os.path.exists(workfile_path):
            # Create new empty workfile
            try:
                with open(workfile_path, 'w', encoding='utf-8') as f:
                    json.dump({"image_tags": {}}, f)
            except Exception as e:
                print("error creating workfile")

        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
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
        """Loads and displays an image, loads associated tags."""
        # --- Clear Left Panel Selections --- # Removed

        self.center_panel.set_image_path(image_path)
        filename = os.path.basename(image_path)
        self.filename_label.setText(filename)

        # --- Load Tags for Image ---
        loaded_tags = self.file_operations.load_tags_for_image(image_path, self.last_folder_path)
        self.selected_tags_for_current_image = loaded_tags  # Store loaded tags
        print(f"Loaded Tags (for storage): {self.selected_tags_for_current_image}")
        self.file_operations.update_workfile(self.last_folder_path, image_path, self.selected_tags_for_current_image)

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


app = QApplication(sys.argv)
theme.setup_dark_mode(app)
window = MainWindow()
window.show()
app.exec()