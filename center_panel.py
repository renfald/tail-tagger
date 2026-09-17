from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QTimer

class CenterPanel(QLabel):
    RESIZE_SETTLE_MS = 120  # Delay after the last resize event before doing a more expensive smooth rescale

    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignCenter)  # Keep alignment from MainWindow
        self.image_path = None  # Store image path
        self._source_pixmap = None  # Cached decode of image_path
        self.setText("No image loaded. Select a folder from the file menu")

        self.setFocusPolicy(Qt.ClickFocus)

        # Fast-scale immediately for feedback, then do one smooth-scale pass after resizing settles. 
        self._smooth_rescale_timer = QTimer(self)
        self._smooth_rescale_timer.setSingleShot(True)
        self._smooth_rescale_timer.setInterval(self.RESIZE_SETTLE_MS)
        self._smooth_rescale_timer.timeout.connect(self._apply_smooth_scale)

    def set_image_path(self, image_path):
        """Sets the image path for the center panel."""
        self.image_path = image_path
        self._load_source_pixmap()
        self.update_image_display() # Call to load initially if path is set programmatically

    def _load_source_pixmap(self):
        """Decodes image_path once and caches the result."""
        if not self.image_path:
            self._source_pixmap = None
            return

        pixmap = QPixmap(self.image_path)
        self._source_pixmap = pixmap if not pixmap.isNull() else None

    def resizeEvent(self, event):
        """Handles resize events to scale and display the image."""
        super().resizeEvent(event) # Important: Call base class implementation first
        self.update_image_display(smooth=False)
        self._smooth_rescale_timer.start() # restart(): coalesces to one smooth pass after resizing settles

    def _apply_smooth_scale(self):
        """Timer callback: replaces the fast preview with a smooth-scaled pixmap."""
        self.update_image_display(smooth=True)

    def update_image_display(self, smooth=True):
        """Scales the cached image to fit the center panel."""
        if not self.image_path:
            self.setText("No image loaded. Select a folder from the file menu")
            return

        if self._source_pixmap is None:
            self.setText("Error loading image") # Keep error text from MainWindow
            return

        mode = Qt.TransformationMode.SmoothTransformation if smooth else Qt.TransformationMode.FastTransformation
        scaled_pixmap = self._source_pixmap.scaled(
            self.width(),
            self.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            mode
        )
        self.setPixmap(scaled_pixmap)