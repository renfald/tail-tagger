from PySide6.QtWidgets import QLabel, QFrame, QSizePolicy, QHBoxLayout
from PySide6.QtCore import Qt, QSize, Signal, QMimeData  # Signal might be removed
from PySide6.QtGui import QDrag, QFont
from math import sqrt

class TagWidget(QFrame):
    """Widget to display a tag."""

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