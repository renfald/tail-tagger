import sys
import os
from tag_widget import TagWidget
from center_panel import CenterPanel
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget,
                             QHBoxLayout, QFrame, QLabel, QListWidget,
                             QSizePolicy, QVBoxLayout, QScrollArea, QPushButton, QSpacerItem, QFileDialog)
from PySide6.QtGui import QColor, QPalette, QPixmap, QImage
from PySide6.QtCore import Qt

class MainWindow(QMainWindow):
    """Main application window for the Image Tagger."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Tagger")
        self.resize(1024, 768)

        self._setup_dark_mode_theme()
        self._setup_ui()
        self._load_tags()
        self._load_initial_image()

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
        right_panel = QListWidget()
        right_panel.setFrameShape(QFrame.StyledPanel)
        right_panel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        right_panel.setFixedWidth(200)
        panels_layout.addWidget(right_panel)

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

        self.filename_label = QLabel("filename.jpg")
        bottom_layout.addWidget(self.filename_label)

        self.index_label = QLabel("1 of 100")
        bottom_layout.addWidget(self.index_label)

        right_spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        bottom_layout.addItem(right_spacer)

        prev_button = QPushButton("< Prev")
        bottom_layout.addWidget(prev_button)

        next_button = QPushButton("Next >")
        bottom_layout.addWidget(next_button)

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
                    layout.addWidget(tag_widget)
        except FileNotFoundError:
            error_label = QLabel("Error: tag_list.csv not found in 'data' folder.")
            layout.addWidget(error_label)

    def _load_initial_image(self):
        """Loads the initial test image and displays it in the center panel."""
        self.image_path = r"input\sample.png" # Initial test image path
        # Set image path in CenterPanel and update
        self.center_panel.set_image_path(self.image_path)
        
        filename = os.path.basename(self.image_path)
        self.filename_label.setText(filename)

    def _open_folder_dialog(self):
            """Opens a folder selection dialog and handles the selected folder."""
            folder_path = QFileDialog.getExistingDirectory(
                self,
                "Select Image Folder", # Dialog title
                os.path.expanduser("~"), # Start directory (user's home directory)
                QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
            )

            if folder_path: # If a folder was selected (not cancelled)
                print(f"Selected folder: {folder_path}") # For now, just print the path
                # We'll add image loading logic here in the next step

app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec()