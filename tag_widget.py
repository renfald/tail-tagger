from PySide6.QtWidgets import QLabel, QFrame, QSizePolicy, QHBoxLayout
from PySide6.QtCore import Qt, QSize, Signal

class TagWidget(QFrame):
    """Widget to display a tag with selection and known/unknown status."""

    tag_clicked = Signal(str)  # Signal emitted when the tag is clicked.

    def __init__(self, tag_name, is_known_tag=True):
        """Initializes a TagWidget.

        Args:
            tag_name (str): The text of the tag.
            is_known_tag (bool, optional): Whether the tag is a "known" tag (from tag_list.csv). Defaults to True.
        """
        super().__init__()
        self.tag_name = tag_name
        self.is_selected = False  # Initially, the tag is not selected.
        self.is_known_tag = is_known_tag  # Initially, assume the tag is known.
        self._setup_ui()
        self._update_style() # Apply initial style based on is_known_tag and is_selected.

    def set_is_known_tag(self, is_known_tag):
        """Sets the is_known_tag property and updates the style.

        Args:
            is_known_tag (bool): The new value for is_known_tag.
        """
        # Currently unused, but may be leveraged when we add the feature to add new tags.
        self.is_known_tag = is_known_tag
        self._update_style()

    def _setup_ui(self):
        """Sets up the UI elements for the tag widget."""
        self.setFrameShape(QFrame.StyledPanel)
        self.setLineWidth(1)

        self.tag_label = QLabel(self.tag_name)
        self.tag_label.setAlignment(Qt.AlignCenter)
        self.tag_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        tag_layout = QHBoxLayout()
        tag_layout.addWidget(self.tag_label)
        tag_layout.setContentsMargins(0, 2, 0, 2)  # Add small margins for visual padding.
        tag_layout.setSpacing(0)  # No spacing between elements in the layout.
        self.setLayout(tag_layout)

        self.setCursor(Qt.PointingHandCursor)  # Change cursor to a hand when hovering.
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.setMinimumSize(QSize(0, 0))  # Allow the widget to shrink if needed.


    def mousePressEvent(self, event):
        """Handles mouse press events to toggle tag selection."""
        super().mousePressEvent(event)  # Call the base class implementation.
        self.toggle_selection()  # Toggle the selection state.
        self.tag_clicked.emit(self.tag_name)  # Emit the tag_clicked signal.

    def toggle_selection(self):
        """Toggles the selection state of the tag (selected/deselected)."""
        self._update_style()  # Update the style to reflect the new selection state.

    def _update_style(self):
        """Updates the visual style of the tag based on its selection state and is_known_tag status."""
        if not self.is_known_tag:
            self.setStyleSheet("background-color: #552121; color: #855252;")  # Desaturated dim red for unknown tags.
        elif self.is_selected:
            self.setStyleSheet("background-color: #212121; color: #525252;")  # Darker background for selected tags.
        else:
            self.setStyleSheet("")  # Default style (no special styling).

    def set_selected(self, is_selected):
        """Sets the selection state of the tag and updates its visual style."""
        self.is_selected = is_selected
        self._update_style()