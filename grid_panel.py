from PySide6.QtWidgets import QGridLayout, QWidget
from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt


class GridPanel(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.scroll_area = None
        self.layout = QGridLayout(self)
        self.layout.setHorizontalSpacing(4)
        self.layout.setVerticalSpacing(4)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.images = []
        self.labels = []
        self.selected = None

        self.thumbnail_size = 350

    def set_image_paths(self, image_paths):
        self.images = image_paths

        # Create labels which will store the image and handle everything
        for index, image_path in enumerate(self.images):
            pixmap = QPixmap(image_path).scaled(
                self.thumbnail_size,
                self.thumbnail_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

            label = self.ImageContainer(pixmap, image_path, index, self)

            self.labels.append(label)

        self.update_grid()

    def update_grid(self):
        if not self.labels:
            return

        available_width = self.scroll_area.viewport().width()

        margins = self.layout.contentsMargins()
        spacing = self.layout.horizontalSpacing()

        available_width -= margins.left() + margins.right()

        columns = max(
            1,
            (available_width + spacing) //
            (self.thumbnail_size + spacing)
        )
        # Dont redraw if nothing changed, we only want to change when we can add or subtract a column
        if columns == getattr(self, "_columns", None): 
            return

        self._columns = columns

        for label in self.labels:
            self.layout.removeWidget(label) # There's maybe a better way to do this? Performance doesnt seem too bad

        for index, label in enumerate(self.labels):
            self.layout.addWidget(label, index//columns, index%columns)
    
    # This should probably be it's own class file
    class ImageContainer(QLabel): 
        def __init__(self, pixmap, image_path, index, widget, parent=None):
            super().__init__(parent)
            self.setPixmap(pixmap)
            self.image_path = image_path
            self.widget = widget
            self.index = index
            self.main_window = widget.main_window

            self.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.resize(widget.thumbnail_size, widget.thumbnail_size)
            self.setStyleSheet("background: #404048; border: 1px solid #91a3b0;") 

        def mousePressEvent(self, event):
            if event.button() == Qt.MouseButton.LeftButton:
                self.main_window._load_and_display_image(self.image_path)
                # Handle bottom right nav section
                self.main_window.current_image_index = self.index
                self.main_window._update_index_label()
                self.setStyleSheet("background: #505058; border: 1px solid #91a3b0;")
                if self.widget.selected and self.widget.selected != self:
                    self.widget.selected.setStyleSheet("background: #404048; border: 1px solid #91a3b0;")
                    
                self.widget.selected = self # Update the selected reference in the parent widget
            super().mousePressEvent(event)
    