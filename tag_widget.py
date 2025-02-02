from PySide6.QtWidgets import QLabel, QFrame, QSizePolicy, QHBoxLayout
from PySide6.QtCore import Qt, QSize, Signal  

class TagWidget(QFrame):
    """Widget to display a tag with selection capability."""
    
    tag_clicked = Signal(str)
    
    def __init__(self, tag_name):
        super().__init__()
        self.tag_name = tag_name
        self.is_selected = False

        self._setup_ui()

    def _setup_ui(self):
        """Sets up the UI elements for the tag widget."""
        self.setFrameShape(QFrame.StyledPanel)
        self.setLineWidth(1)

        self.tag_label = QLabel(self.tag_name)
        self.tag_label.setAlignment(Qt.AlignCenter)
        self.tag_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        tag_layout = QHBoxLayout()
        tag_layout.addWidget(self.tag_label)
        tag_layout.setContentsMargins(0, 2, 0, 2)
        tag_layout.setSpacing(0)
        self.setLayout(tag_layout)

        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.setMinimumSize(QSize(0, 0))


    def mousePressEvent(self, event):
        """Handles mouse press events to toggle tag selection."""
        super().mousePressEvent(event)
        self.toggle_selection()
        self.tag_clicked.emit(self.tag_name)

    def toggle_selection(self):
        """Toggles the selection state of the tag."""
        self.is_selected = not self.is_selected
        self._update_style()

    def _update_style(self):
        """Updates the visual style of the tag based on its selection state."""
        if self.is_selected:
            self.setStyleSheet("background-color: #212121; color: #525252;")
        else:
            self.setStyleSheet("")