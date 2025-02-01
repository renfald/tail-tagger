from PySide6.QtWidgets import QLabel, QFrame, QVBoxLayout, QSizePolicy
from PySide6.QtCore import Qt

class TagWidget(QFrame):
    def __init__(self, tag_name):
        super().__init__()
        self.tag_name = tag_name
        self.is_selected = False  # Keep track of selection state

        self.setFrameShape(QFrame.StyledPanel) # Make it look like a panel
        self.setLineWidth(1)

        self.tag_label = QLabel(tag_name) # Label to display tag name
        self.tag_label.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout() # Vertical layout for tag widget
        layout.addWidget(self.tag_label)
        layout.setContentsMargins(5, 2, 5, 2) # Add some padding around the label
        
        self.setLayout(layout)

        self.setCursor(Qt.PointingHandCursor) # Change cursor to pointer on hover
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed) # Preferred width, fixed height

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