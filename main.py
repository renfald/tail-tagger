import sys
import os  # Import the 'os' module for file paths
from tag_widget import TagWidget  # Import TagWidget from tag_widget.py
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget,
                             QHBoxLayout, QFrame, QLabel, QListWidget,
                             QSizePolicy, QVBoxLayout, QScrollArea, QPushButton, QSpacerItem)
from PySide6.QtGui import QColor, QPalette, QPixmap, QImage
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

        # --- Main Layout Changed to QVBoxLayout ---
        main_layout = QVBoxLayout() # <--- Changed to QVBoxLayout for main window
        main_layout.setSpacing(0) # No spacing in main layout
        central_widget.setLayout(main_layout) # <--- Set QVBoxLayout
        # --- End Main Layout Change ---


        # --- Top Horizontal Layout for Panels (now inside main QVBoxLayout) ---
        panels_layout = QHBoxLayout() # <--- Create QHBoxLayout for panels
        panels_layout.setSpacing(0) # No spacing between panels
        main_layout.addLayout(panels_layout) # <--- Add panels_layout to main_layout
        # --- End Top Horizontal Layout for Panels ---

        left_scroll_area = QScrollArea()
        left_scroll_area.setWidgetResizable(True)
        left_scroll_area.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        left_scroll_area.setFixedWidth(200)

        left_panel = QFrame()
        left_panel.setFrameShape(QFrame.StyledPanel)
        
        left_layout = QVBoxLayout()
        left_layout.setAlignment(Qt.AlignTop)
        left_layout.setSpacing(0) # <--- Set QVBoxLayout spacing to 0
        left_layout.setContentsMargins(0, 0, 0, 0) # <--- Set QVBoxLayout margins to 0
        
        left_panel.setLayout(left_layout)

        left_scroll_area.setWidget(left_panel)
        panels_layout.addWidget(left_scroll_area)

        # Center Panel (Image Display)
        self.center_panel = QLabel() # <--- Make center_panel an instance variable (self.center_panel)
        self.center_panel.setFrameShape(QFrame.StyledPanel)
        self.center_panel.setAlignment(Qt.AlignCenter)
        self.center_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        panels_layout.addWidget(self.center_panel)
        

        # Right Panel (Tag List)
        right_panel = QListWidget()
        right_panel.setFrameShape(QFrame.StyledPanel)
        right_panel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        right_panel.setFixedWidth(200)
        panels_layout.addWidget(right_panel)

        # --- Bottom Panel for Image Info and Buttons ---
        bottom_panel = QFrame() # <--- Create bottom panel QFrame
        bottom_panel.setFrameShape(QFrame.StyledPanel) # Give it a border
        bottom_panel.setFixedHeight(50) # Set a fixed height for bottom panel
        bottom_layout = QHBoxLayout() # <--- Create QHBoxLayout for bottom panel
        bottom_layout.setSpacing(10) # Add some spacing between elements in bottom panel
        bottom_layout.setContentsMargins(10, 5, 10, 5) # Add margins around content
        bottom_panel.setLayout(bottom_layout)

        # --- Horizontal Spacers to Center Content ---
        left_spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum) # Flexible spacer on the left
        bottom_layout.addItem(left_spacer) # Add left spacer

        # Image Filename Label
        self.filename_label = QLabel("filename.jpg") # <--- Instance variable for filename label
        bottom_layout.addWidget(self.filename_label)

        # Image Index Label
        self.index_label = QLabel("1 of 100") # <--- Instance variable for index label
        bottom_layout.addWidget(self.index_label)

        right_spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum) # Flexible spacer on the right
        bottom_layout.addItem(right_spacer) # Add right spacer
        # --- End Horizontal Spacers ---

        # Previous Image Button
        prev_button = QPushButton("< Prev") # <--- Create Previous button
        bottom_layout.addWidget(prev_button)

        # Next Image Button
        next_button = QPushButton("Next >") # <--- Create Next button
        bottom_layout.addWidget(next_button)


        main_layout.addWidget(bottom_panel) # <--- Add bottom_panel to main_layout (QVBoxLayout)
        # --- End Bottom Panel ---  


        # --- Load Tags from CSV ---
        self.load_tags_from_csv(left_layout) # Call function to load tags
        # --- End Load Tags from CSV ---

        # --- Image Loading and Display ---
        self.image_path = r"input\sample4.jpg" # <--- REPLACE WITH YOUR IMAGE PATH
        self.update_image_display() # <--- Call update_image_display initially
        # --- End Initial Image Load and Display ---

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

    def update_image_display(self): # <--- New function to handle image loading and scaling
        pixmap = QPixmap(self.image_path) # Load image

        if pixmap.isNull(): # Error handling
            self.center_panel.setText("Error loading image")
            return

        # --- Image Scaling ---
        panel_width = self.center_panel.width() # Get current panel width
        panel_height = self.center_panel.height() # Get current panel height

        scaled_pixmap = pixmap.scaled(
            panel_width,
            panel_height,
            Qt.AspectRatioMode.KeepAspectRatio, # Maintain aspect ratio
            Qt.TransformationMode.SmoothTransformation # Use smooth scaling algorithm
        )
        # --- End Image Scaling ---

        self.center_panel.setPixmap(scaled_pixmap) # Set scaled pixmap to QLabel


app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec()