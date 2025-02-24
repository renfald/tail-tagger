from PySide6.QtWidgets import QLabel, QFrame, QSizePolicy, QHBoxLayout
from PySide6.QtCore import Qt, QSize, Signal, QMimeData
from PySide6.QtGui import QDrag, QFont
from math import sqrt

# Import compiled resources for icons
# pyside6-rcc resources/resources.qrc -o resources/resources_rc.py
import resources.resources_rc as resources_rc  

class TagWidget(QFrame):
    """Widget to display a tag."""

    tag_clicked = Signal(str)
    favorite_star_clicked = Signal(str)

    def __init__(self, tag_data, is_selected=False, is_known_tag=True): # Modified constructor - tag_data first
        """Initializes a TagWidget.

        Args:
            tag_data (TagData): The TagData object representing the tag. # Modified docstring
            is_selected (bool, optional): Whether the tag is selected. Defaults to False. # Keep for now, panel can override if needed
            is_known_tag (bool, optional): Whether the tag is "known". Defaults to True. # Keep for now, panel can override if needed
        """
        super().__init__()
        self.tag_data = tag_data # Store TagData object
        self.tag_name = tag_data.name # Extract tag_name from TagData
        self.is_selected = is_selected if is_selected is not None else tag_data.selected # Use constructor param if provided, else TagData
        self.is_known_tag = is_known_tag if is_known_tag is not None else tag_data.is_known # Use constructor param if provided, else TagData
        self.styling_mode = "dim_on_select"
        self._setup_ui()
        self._update_style()

    def set_is_known_tag(self, is_known_tag):
        """Sets the is_known_tag property."""
        self.is_known_tag = is_known_tag
        self._update_style()

    def _setup_ui(self):
        """Sets up the UI elements."""
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        tag_layout = QHBoxLayout()
        tag_layout.setContentsMargins(0, 0, 0, 0) # Removing any default margins and letting the label control it
        tag_layout.setSpacing(0) # Removing any default spacing

        self.tag_label = QLabel(self.tag_name)
        self.tag_label.setAlignment(Qt.AlignCenter)
        self.tag_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # self.tag_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed) # consider this if I want the tags to be further collapsed
        self.tag_label.setContentsMargins(3, 4, 3, 4) # The widget will shrink to 6 pixels larger than the text before scrolling

        # --- Star Icon Label ---
        self.star_label = QLabel(self)  # Create QLabel instance
        self.star_label.setFixedSize(QSize(22, 22)) # Set a fixed size for the star icon (adjust as needed)
        self.star_label.setScaledContents(True) # Ensure SVG scales nicely to fit label size
        self.star_label.hide() # Initially hide the star icon
        # --- End Star Icon Label ---

        # --- Set Initial Star Icon ---
        from PySide6.QtGui import QPixmap # Import QPixmap here
        pixmap = QPixmap(":/icons/star-outline.svg") # Load the outline star SVG from resources
        self.star_label.setPixmap(pixmap) # Set the pixmap for the star_label
        # --- End Set Initial Star Icon ---

        tag_layout.addWidget(self.tag_label)
        tag_layout.addWidget(self.star_label)
        self.setLayout(tag_layout)


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
            if self.star_label.geometry().contains(event.pos()): # Check if click is within star_label
                print(f"Star icon clicked for tag: {self.tag_name}") # Debug
                self.favorite_star_clicked.emit(self.tag_name) # Emit favorite_star_clicked signal
            else:
                print(f"Tag label clicked for tag: {self.tag_name}") # Debug
                self.tag_clicked.emit(self.tag_name)  # Emit the tag_clicked signal (existing functionality)
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

            # --- Apply the Combined Stylesheet to label ---
            self.tag_label.setStyleSheet(style)


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

    # --- Hover Event Handlers ---
    def enterEvent(self, event):
        """Handles mouse enter events."""
        print(f"Mouse enter event for tag: {self.tag_name}") # Debug
        self.set_favorite_state() # Call set_favorite_state on hover

    def leaveEvent(self, event):
        """Handles mouse leave events."""
        print(f"Mouse leave event for tag: {self.tag_name}") # Debug
        self.set_favorite_state() # Call set_favorite_state on leave
    # --- End Hover Event Handlers ---

        # --- set_favorite_state method (Implementation in next action) ---
    def set_favorite_state(self):
        """Updates the star icon based on favorite state and hover."""
        from PySide6.QtGui import QPixmap # Import QPixmap here (if not already imported)

        # Determine star icon based on tag_data.favorite (currently always False)
        if self.tag_data.favorite: # Access tag_data.favorite directly! (Currently always False)
            pixmap = QPixmap(":/icons/star-fill.svg")
        else:
            pixmap = QPixmap(":/icons/star-outline.svg")

        # Show star ONLY on hover AND if it's a known tag
        if self.underMouse() and self.is_known_tag: # Check for mouse hover and is_known_tag
            self.star_label.setPixmap(pixmap) # Set the appropriate star icon
            self.star_label.show() # Show the star label
        else:
            self.star_label.hide() # Hide the star label