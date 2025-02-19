import sys
import os
import json
import theme
from config_manager import ConfigManager
from file_operations import FileOperations
from tag_list_model import TagListModel, TagData
from all_tags_panel import AllTagsPanel
from selected_tags_panel import SelectedTagsPanel
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QFrame, QLabel,
                             QSizePolicy, QVBoxLayout, QScrollArea, QPushButton, QSpacerItem,
                             QFileDialog, QListView, QSplitter)
from PySide6.QtGui import QColor, QPalette
from PySide6.QtCore import Qt
from center_panel import CenterPanel #Added back import

class MainWindow(QMainWindow):
    """Main application window for the Image Tagger."""

    def __init__(self):
        """Initializes the main application window."""
        super().__init__()
        self.setWindowTitle("Image Tagger")
        self.resize(1280, 960)

        # --- Instance Variables ---
        self.image_paths = []  # List of image file paths.
        self.current_image_index = 0  # Index of the currently displayed image.
        self.last_folder_path = None  # Initialize.
        self.selected_tags_for_current_image = []  # List of tags for the current image.
        
        # --- File Operations ---
        self.file_operations = FileOperations()
        self.tag_list_model = TagListModel()

        # --- Staging Folder ---
        self.staging_folder_path = os.path.join(os.getcwd(), "staging")
        if not os.path.isdir(self.staging_folder_path):
            os.makedirs(self.staging_folder_path, exist_ok=True)
        self.file_operations.staging_folder_path = self.staging_folder_path


        # --- Load Configuration ---
        self.config_manager = ConfigManager()
        config = self.config_manager.config  # Get the loaded config
        self.last_folder_path = config.get("last_opened_folder") # Set last folder from config

        # --- Load Tags from CSV ---
        self.csv_path = os.path.join(os.getcwd(), "data", "tags-list.csv")
        self.tag_list_model.load_tags_from_csv(self.csv_path)

        # --- Tag Panels ---
        # self.all_tags_panel = AllTagsPanel(self.tag_list_model) Not sure if we're gonna do it this way. right now this is directly in setup ui.
        self.selected_tags_panel = SelectedTagsPanel(self)


        # --- Setup UI and Load Tags/Images ---
        self._setup_ui()

        if (self.last_folder_path):
            print(f"Loading last opened folder: {self.last_folder_path}")
            self._load_image_folder(self.last_folder_path)
        else:
            print("No valid last opened folder, attempting to load initial directory.")
            self._load_initial_directory()            # self._load_image_folder(None) # May deprecate


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

        main_layout = QVBoxLayout(central_widget) # Set layout on central widget
        main_layout.setSpacing(0)
        # central_widget.setLayout(main_layout) # Removed

        # --- Main Horizontal Splitter (Left, Center, Right) ---
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.setChildrenCollapsible(False)
        main_layout.addWidget(main_splitter) # Add splitter to main layout


        # --- Left Panel (Resizable) ---
        left_panel = QFrame()
        left_panel.setFrameShape(QFrame.StyledPanel)
        left_panel.setFixedWidth(150) # Initial width
        left_panel.setMinimumWidth(75) # Minimum width
        left_panel.setMaximumWidth(300) # Maximum width
        left_layout = QVBoxLayout(left_panel)  # Add a layout
        left_layout.setContentsMargins(0, 0, 0, 0) # Add this to remove margin
        left_layout.setSpacing(0)


        # --- Vertical Splitter (Inside Left Panel) ---
        left_splitter = QSplitter(Qt.Vertical)
        left_splitter.setChildrenCollapsible(False)
        left_layout.addWidget(left_splitter)
        
        # --- All Tags Panel ---
        self.all_tags_panel = AllTagsPanel(self.tag_list_model)
        self.tag_list_model.tags_selected_changed.connect(self._update_tag_panels)

        all_tags_scroll_area = QScrollArea() # A QScrollArea is a scrollable area that can contain another widget.
        all_tags_scroll_area.setWidgetResizable(True) 
        # all_tags_panel = QFrame()  # taking this out and moving the alltagspanel from init to here. unclear if we really need it to be "self"
        all_tags_layout = QVBoxLayout(self.all_tags_panel)
        all_tags_layout.setAlignment(Qt.AlignTop)
        all_tags_layout.addWidget(self.all_tags_panel)
        all_tags_scroll_area.setWidget(self.all_tags_panel)

        # --- Frequently Used Panel ---
        frequently_used_scroll_area = QScrollArea()
        frequently_used_scroll_area.setWidgetResizable(True)
        frequently_used_panel = QFrame()
        frequently_used_layout = QVBoxLayout(frequently_used_panel)
        frequently_used_layout.setAlignment(Qt.AlignTop)
        frequently_used_layout.addWidget(QLabel("Frequently Used"))
        frequently_used_scroll_area.setWidget(frequently_used_panel)


        # --- Favorites Panel ---
        favorites_scroll_area = QScrollArea()
        favorites_scroll_area.setWidgetResizable(True)
        favorites_panel = QFrame()
        favorites_layout = QVBoxLayout(favorites_panel)
        favorites_layout.setAlignment(Qt.AlignTop)
        favorites_layout.addWidget(QLabel("Favorites"))
        favorites_scroll_area.setWidget(favorites_panel)
        
        # --- Style the viewports ---  this is temporary and will not be needed when the full panels get implemented
        darker_background_color = "#242424"  # Darker gray.  Adjust as needed.
        # all_tags_scroll_area.viewport().setStyleSheet(f"background-color: {darker_background_color};")
        frequently_used_scroll_area.viewport().setStyleSheet(f"background-color: {darker_background_color};")
        favorites_scroll_area.setStyleSheet(f"background-color: {darker_background_color};")


        # Add scroll areas to left splitter
        left_splitter.addWidget(all_tags_scroll_area)
        left_splitter.addWidget(frequently_used_scroll_area)
        left_splitter.addWidget(favorites_scroll_area)
        
        left_splitter.setSizes([300, 200, 200])
        
        # Set stretch factors for the left panels 0 = fixed size, 1 = stretchable
        left_splitter.setStretchFactor(0, 0) # All Tags
        left_splitter.setStretchFactor(1, 0) # Frequently Used
        left_splitter.setStretchFactor(2, 1) # Favorites

        main_splitter.addWidget(left_panel) # Add to splitter

        # --- Center Panel (Image Display) ---
        self.center_panel = CenterPanel()
        self.center_panel.setFrameShape(QFrame.StyledPanel)
        self.center_panel.setMinimumSize(100, 100)
        main_splitter.addWidget(self.center_panel)  # Add to splitter

        # --- Right Panel (Selected Tags) ---
        right_panel_scroll_area = QScrollArea()
        right_panel_scroll_area.setWidgetResizable(True)
        self.selected_tags_panel = SelectedTagsPanel(self) # Instance is now directly the right panel
        right_panel_scroll_area.setWidget(self.selected_tags_panel) # Set panel as scroll area widget
        main_splitter.addWidget(right_panel_scroll_area)  # Add scroll area to splitter

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
        # bottom_panel.setLayout(bottom_layout) # Removed

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

        self.file_operations.create_default_workfile(folder_path) # Create workfile if it doesn't exist

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

        self.center_panel.set_image_path(image_path)
        filename = os.path.basename(image_path)
        self.filename_label.setText(filename)

        # --- Load Tags for Image ---
        loaded_tags = self.file_operations.load_tags_for_image(image_path, self.last_folder_path)
        self.selected_tags_for_current_image = [] # Clear and repopulate
        self.tag_list_model.clear_selected_tags() # Clear *selected* status
        self.tag_list_model.remove_unknown_tags() # Remove any unknown tags
        
        for tag_name in loaded_tags:
            # Check if the tag already exists in the model
            existing_tag = None
            for tag in self.tag_list_model.get_all_tags():
                if tag.name == tag_name:
                    existing_tag = tag
                    break

            if existing_tag:
                # Tag exists, update selection
                self.tag_list_model.set_tag_selected(tag_name, True)
                self.selected_tags_for_current_image.append(existing_tag)
            else:
                # Tag doesn't exist, create a new one (unknown)
                new_tag = TagData(name=tag_name, selected=True, is_known=False)
                self.tag_list_model.add_tag(new_tag)
                self.selected_tags_for_current_image.append(new_tag)
        
        self.file_operations.update_workfile(self.last_folder_path, image_path, self.selected_tags_for_current_image)
        
        # Now that we've updated the model, all panels must be populated with the appropriate tags
        self._update_tag_panels()

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


    def _update_tag_panels(self):
        """Updates all tag panels."""
        self.all_tags_panel.update_display()
        self.selected_tags_panel.update_display()
        # any other panels to update will go here once implemented

app = QApplication(sys.argv)
theme.setup_dark_mode(app)
window = MainWindow()
window.show()
app.exec()