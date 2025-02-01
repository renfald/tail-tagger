from PySide6.QtWidgets import QLabel, QFrame, QSizePolicy, QHBoxLayout
from PySide6.QtCore import Qt, QSize

class TagWidget(QFrame):
    def __init__(self, tag_name):
        super().__init__()
        self.tag_name = tag_name
        self.is_selected = False

        self.setFrameShape(QFrame.StyledPanel) # Make it look like a panel
        self.setLineWidth(1)

        self.tag_label = QLabel(tag_name)
        self.tag_label.setAlignment(Qt.AlignCenter)
        self.tag_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed) # <--- Add Size Policy to tag_label

        # --- Use QHBoxLayout to control TagWidget width ---
        tag_layout = QHBoxLayout()
        tag_layout.addWidget(self.tag_label)
        tag_layout.setContentsMargins(0, 2, 0, 2)
        tag_layout.setSpacing(0)
        self.setLayout(tag_layout)
        # --- End QHBoxLayout ---

        self.setCursor(Qt.PointingHandCursor) # Change cursor to pointer on hover
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed) # Preferred width, fixed height
        # --- Set minimum size hint to control width ---
        self.setMinimumSize(QSize(0, 0)) # Let layout manage width, but set min size hint
        # --- End minimum size hint ---

    def mousePressEvent(self, event): # Handle mouse click events
        super().mousePressEvent(event) # Call parent class's method
        self.toggle_selection() # Toggle selection on click

    def toggle_selection(self):
        self.is_selected = not self.is_selected # Toggle boolean
        self.update_style() # Update visual style based on selection

    def update_style(self):
        if self.is_selected:
            self.setStyleSheet("background-color: #606060; border: 1px solid #A0A0A0;") # Darker background, lighter border when selected
        else:
            self.setStyleSheet("") # Reset to default style when not selected