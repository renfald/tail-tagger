import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget,
                             QHBoxLayout, QFrame, QLabel, QListWidget,
                             QSizePolicy)
from PySide6.QtGui import QColor, QPalette


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Tagger")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QHBoxLayout()
        central_widget.setLayout(layout)
        layout.setSpacing(5)  # Add some spacing between panels

        # Left Panel (Tag Input Area)
        left_panel = QFrame()
        left_panel.setFrameShape(QFrame.StyledPanel)  # Give it a border
        left_panel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding) # Fixed width, expanding height
        left_panel.setFixedWidth(200)  # Set initial width
        layout.addWidget(left_panel)

        # Center Panel (Image Display)
        center_panel = QLabel()
        center_panel.setFrameShape(QFrame.StyledPanel) # Give it a border
        center_panel.setAlignment(Qt.AlignCenter) # Center content
        center_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding) # Expanding in both directions
        layout.addWidget(center_panel)

        # Right Panel (Tag List)
        right_panel = QListWidget()
        right_panel.setFrameShape(QFrame.StyledPanel) # Give it a border
        right_panel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding) # Fixed width, expanding height
        right_panel.setFixedWidth(200) # Set initial width
        layout.addWidget(right_panel)


from PySide6.QtCore import Qt  # Import Qt namespace for alignment

app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec()