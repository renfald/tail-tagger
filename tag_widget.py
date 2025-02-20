from PySide6.QtWidgets import QLabel, QFrame, QSizePolicy, QHBoxLayout
from PySide6.QtCore import Qt, QSize, Signal, QMimeData
from PySide6.QtGui import QDrag, QFont
from math import sqrt

class TagWidget(QFrame):
    """Widget to display a tag."""

    tag_clicked = Signal(str)

    def __init__(self, tag_name, is_selected=False, is_known_tag=True):
        """Initializes a TagWidget.

        Args:
            tag_name (str): The text of the tag.
            is_known_tag (bool, optional): Whether the tag is "known". Defaults to True.
        """
        super().__init__()
        self.tag_name = tag_name
        self.is_selected = is_selected
        self.is_known_tag = is_known_tag
        self.styling_mode = "dim_on_select"
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
        # self.tag_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed) # consider this if I want the tags to be further collapsed
        self.tag_label.setContentsMargins(3, 4, 3, 4) # The widget will shrink to 6 pixels larger than the text before scrolling

        tag_layout = QHBoxLayout()
        tag_layout.addWidget(self.tag_label)
        tag_layout.setContentsMargins(0, 0, 0, 0) # Removing any default margins and letting the label above control it
        self.setLayout(tag_layout)

        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

    def mousePressEvent(self, event):
        """Handles mouse press events to initiate drag detection."""
        super().mousePressEvent(event) # Call base class implementation first! Important for focus and other default behaviors.
        if event.button() == Qt.LeftButton:
            self.start_drag_pos = event.pos()  # Record starting position
            self.start_drag_global_pos = event.globalPos() # Needed for calculating global distance
            print(f"Mouse press event. tag: {self.tag_name}, pos: {self.start_drag_pos}, global: {self.start_drag_global_pos}") # Debug

    def mouseMoveEvent(self, event):
        """Handles mouse move events to initiate drag operation."""
        print(f"mouseMoveEvent called for tag: {self.tag_name}") # Debug

        if event.buttons() != Qt.LeftButton: # Check if left button is still pressed
            print(f"mouseMoveEvent: Ignoring because left button is not pressed.") #Debug
            return # Ignore if not left button drag

        dx = event.globalPos().x() - self.start_drag_global_pos.x() # Calculate horizontal movement
        dy = event.globalPos().y() - self.start_drag_global_pos.y() # Calculate vertical movement
        distance = sqrt(dx * dx + dy * dy) # Calculate total distance using hypotenuse

        print(f"mouseMoveEvent: tag={self.tag_name}, distance={distance:.2f}") # Debug

        if distance > 8: # Drag threshold (pixels).  Adjust as needed.
            print(f"Initiating drag for tag: {self.tag_name}") # Debug
            drag = QDrag(self) # Create QDrag object, passing self (TagWidget) as parent
            mime_data = QMimeData() # Create QMimeData object to hold drag data
            mime_data.setText(self.tag_name) # For now, just tag name as plain text
            drag.setMimeData(mime_data) # Set the mime data for the drag operation
            # drag.setPixmap(self.grab()) # Optional: set a pixmap for visual feedback (later)
            drag.exec(Qt.MoveAction) # Start the drag and drop operation.  Qt.MoveAction indicates the widget is being moved (reordered)
            print(f"Drag operation started for tag: {self.tag_name}") # Debug

    def mouseReleaseEvent(self, event):
        """Handles mouse release events."""
        print(f"TagWidget '{self.tag_name}' mouseReleaseEvent!")
        if event.button() == Qt.LeftButton:  # Only handle left clicks
            self.tag_clicked.emit(self.tag_name)  # Emit the signal with tag name
        super().mouseReleaseEvent(event) # keep default functionality just in case

    def _update_style(self):
            """Updates the visual style."""

            # --- Base Styles (Apply to all states) ---
            base_style = """
                background-color: #353535;
                color: white;
                border: 1px solid #181818;
                border-radius: 5px;
            """
            
            # --- Font Settings (Apply to all states) ---
            font = QFont()
            font.setPointSize(8)
            self.tag_label.setFont(font)
            
            # --- State-Specific Styles ---
            if not self.is_known_tag:
                # Unknown Tag Style
                style = base_style + "background-color: #552121; color: #855252;"

            elif self.styling_mode == "dim_on_select" and self.is_selected:
                # Selected (Dimmed) Style
                style = base_style + "background-color: #212121; color: #888888;"
            else:
                # Default (Known, Unselected) Style
                style = base_style  # No additional changes needed

            # --- Apply the Combined Stylesheet ---
            self.setStyleSheet(style)


    def set_selected(self, is_selected):
        """Sets the selection state."""
        self.is_selected = is_selected
        self._update_style()

    def set_styling_mode(self, mode):
        """Sets the styling mode for the TagWidget."""
        if mode in ["dim_on_select", "ignore_select"]:
            self.styling_mode = mode
            self._update_style()  # Re-apply style
        else:
            print(f"Warning: Invalid styling mode: {mode}")