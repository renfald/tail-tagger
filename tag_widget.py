from PySide6.QtWidgets import QLabel, QFrame, QSizePolicy, QHBoxLayout
from PySide6.QtCore import Qt, QSize, Signal, QMimeData
from PySide6.QtGui import QDrag
from math import sqrt

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
        # self.toggle_selection()  # Toggle the selection state.  <- REMOVE/COMMENT OUT THIS LINE
        # self.tag_clicked.emit(self.tag_name)  # Emit the tag_clicked signal. <- REMOVE/COMMENT OUT THIS LINE
        self.start_drag_pos = event.pos()  # Store widget-relative position.  <-- ADD THIS LINE
        self.start_drag_global_pos = event.globalPos()  # Store global position. <-- ADD THIS LINE
        print(f"Mouse press event. tag: {self.tag_name}, pos: {self.start_drag_pos}, global: {self.start_drag_global_pos}") #TEMP PRINT


    def mouseMoveEvent(self, event):
        """Handles mouse move events to initiate drag if threshold is exceeded."""
        print(f"mouseMoveEvent called for tag: {self.tag_name}")  # Debug print

        if event.buttons() != Qt.LeftButton:  # Only handle left-button drags
            print(f"mouseMoveEvent: Ignoring because left button is not pressed.")
            return

        if not self.parent().is_tag_draggable(self.tag_name):  # Check parent's is_tag_draggable
            print("drag not allowed")
            return

        # Calculate distance moved from initial press position.
        dx = event.globalPos().x() - self.start_drag_global_pos.x()
        dy = event.globalPos().y() - self.start_drag_global_pos.y()
        distance = sqrt(dx * dx + dy * dy)
        print(f"mouseMoveEvent: tag={self.tag_name}, distance={distance:.2f}, drag_allowed={self.parent().is_tag_draggable(self.tag_name)}")

        if distance > 8:  # Drag threshold (adjust as needed).
            print(f"Initiating drag for tag: {self.tag_name}")
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(self.tag_name)
            drag.setMimeData(mime_data)
            # drag.setPixmap(self.grab())  # Optional: Set a pixmap for the drag.
            drag.exec(Qt.MoveAction)  # Start the drag operation.
    
    
    def mouseReleaseEvent(self, event):
        """Handles mouse release events, completing click or drag"""
        # Calculate distance moved from initial press position.
        dx = event.globalPos().x() - self.start_drag_global_pos.x()
        dy = event.globalPos().y() - self.start_drag_global_pos.y()
        distance = sqrt(dx * dx + dy * dy)
        print(f"release distance: {distance}")

        if distance <= 8:  # Click threshold (adjust as needed).
            print(f"toggle selection: {self.tag_name}") #TEMP PRINT
            self.is_selected = not self.is_selected  # Toggle the selection state.
            self._update_style() # Update style
            self.tag_clicked.emit(self.tag_name)
    
    
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