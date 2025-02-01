import sys
import os  # Import the 'os' module for file paths
from tag_widget import TagWidget  # Import TagWidget from tag_widget.py
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget,
                             QHBoxLayout, QFrame, QLabel, QListWidget,
                             QSizePolicy, QVBoxLayout, QScrollArea) # Added QVBoxLayout
from PySide6.QtGui import QColor, QPalette
from PySide6.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Tagger")

        # Set initial window size
        self.resize(1024, 768)  # Add this line to set initial size

        # --- Dark Mode Theme ---
        app.setStyle("Fusion") # Good for cross-platform dark mode
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
        # --- End Dark Mode Theme ---


        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QHBoxLayout()
        central_widget.setLayout(layout)
        layout.setSpacing(5)

        # --- Left Panel with Scroll Area ---
        left_scroll_area = QScrollArea() # <--- Create QScrollArea
        left_scroll_area.setWidgetResizable(True) # <--- Important: Make content widget resizable
        left_panel = QFrame()
        left_panel.setFrameShape(QFrame.StyledPanel)
        left_panel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        left_panel.setFixedWidth(200)
        left_layout = QVBoxLayout() # Vertical layout for tags in left panel
        left_layout.setAlignment(Qt.AlignTop) # Align tags to the top
        left_panel.setLayout(left_layout) # Set layout for left panel
        left_scroll_area.setWidget(left_panel) # <--- Set left_panel as the scroll area's widget
        layout.addWidget(left_scroll_area) # <--- Add QScrollArea to main layout
        # --- End Left Panel with Scroll Area ---

        # Center Panel (Image Display)
        center_panel = QLabel()
        center_panel.setFrameShape(QFrame.StyledPanel)
        center_panel.setAlignment(Qt.AlignCenter)
        center_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(center_panel)

        # Right Panel (Tag List)
        right_panel = QListWidget()
        right_panel.setFrameShape(QFrame.StyledPanel)
        right_panel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        right_panel.setFixedWidth(200)
        layout.addWidget(right_panel)

        # --- Load Tags from CSV ---
        self.load_tags_from_csv(left_layout) # Call function to load tags
        # --- End Load Tags from CSV ---


    def load_tags_from_csv(self, layout):
        tags_file_path = os.path.join("data", "tag_list.csv")
        try:
            with open(tags_file_path, 'r', encoding='utf-8') as file:
                next(file) # Skip the header line
                for line in file:
                    tag_name = line.strip()
                    tag_widget = TagWidget(tag_name) # Create TagWidget instead of QLabel <---- CHANGED THIS LINE
                    layout.addWidget(tag_widget) # Add TagWidget to layout
        except FileNotFoundError:
            error_label = QLabel("Error: tag_list.csv not found in 'data' folder.")
            layout.addWidget(error_label)


app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec()