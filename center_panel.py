from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

class CenterPanel(QLabel):
    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignCenter)  # Keep alignment from MainWindow
        self.image_path = None  # Store image path

    def set_image_path(self, image_path):
        """Sets the image path for the center panel."""
        self.image_path = image_path
        self.update_image_display() # Call to load initially if path is set programmatically

    def resizeEvent(self, event):
        """Handles resize events to scale and display the image."""
        super().resizeEvent(event) # Important: Call base class implementation first
        self.update_image_display()

    def update_image_display(self):
        """Loads and scales the image to fit the center panel."""
        if not self.image_path:
            self.clear() # Clear if no image path set
            return

        pixmap = QPixmap(self.image_path)

        if pixmap.isNull():
            self.setText("Error loading image") # Keep error text from MainWindow
            return

        panel_width = self.width()
        panel_height = self.height()

        scaled_pixmap = pixmap.scaled(
            panel_width,
            panel_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.setPixmap(scaled_pixmap)