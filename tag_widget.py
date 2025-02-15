from PySide6.QtWidgets import QLabel, QFrame, QSizePolicy, QHBoxLayout
from PySide6.QtCore import Qt, QSize, Signal, QMimeData  # Signal might be removed
from PySide6.QtGui import QDrag
from math import sqrt

class TagWidget(QFrame):
    """Widget to display a tag."""

    def __init__(self, tag_name, is_known_tag=True):
        """Initializes a TagWidget.

        Args:
            tag_name (str): The text of the tag.
            is_known_tag (bool, optional): Whether the tag is "known". Defaults to True.
        """
        super().__init__()
        self.tag_name = tag_name
        self.is_selected = False  # Initially, not selected.
        self.is_known_tag = is_known_tag
        self._setup_ui()
        self._update_style()

    def set_is_known_tag(self, is_known_tag):
        """Sets the is_known_tag property."""
        self.is_known_tag = is_known_tag
        self._update_style()

    def _setup_ui(self):
        """Sets up the UI elements."""
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
        """Handles mouse press events."""
        pass

    def mouseMoveEvent(self, event):
        """Handles mouse move events."""
        pass

    def mouseReleaseEvent(self, event):
        """Handles mouse release events."""
        pass

    def _update_style(self):
        """Updates the visual style."""
        if not self.is_known_tag:
            self.setStyleSheet("background-color: #552121; color: #855252;")
        elif self.is_selected:
            self.setStyleSheet("background-color: #212121; color: #525252;")
        else:
            self.setStyleSheet("")

    def set_selected(self, is_selected):
        """Sets the selection state."""
        self.is_selected = is_selected
        self._update_style()