from abc import ABC, abstractmethod
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt

class TagListPanel(QWidget, ABC, metaclass=type('ABCMetaQWidget', (type(QWidget), type(ABC)), {})):  # Explicit metaclass
    """Abstract base class for panels."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignTop)
        self.layout.setSpacing(1) # This is the space between the widgets
        self.layout.setContentsMargins(1, 1, 1, 1) # This is the margin around the entire panel, not the individual widgets
        self.setStyleSheet("background-color: #242424;") # This sets a dark grey background for the tag panels

    @abstractmethod
    def add_tag(self, tag_name, is_known=True):
        """Adds a tag."""
        pass

    @abstractmethod
    def remove_tag(self, tag_name):
        """Removes a tag."""
        pass

    @abstractmethod
    def clear_tags(self):
        """Clears all tags."""
        pass # Modified

    @abstractmethod
    def get_tags(self):
        """Returns a list of all tags."""
        return []

    @abstractmethod
    def set_tags(self, tags):
        """Sets the tags."""
        pass

    @abstractmethod
    def set_tag_selected(self, tag_name, is_selected):
        """Sets the selection state."""
        pass

    @abstractmethod
    def is_tag_draggable(self, tag_name):
        """Returns True if draggable, False otherwise."""
        return False

    @abstractmethod
    def dropEvent(self, event):
        """Handles drop events."""
        pass

    @abstractmethod
    def get_styling_mode(self):
        """Gets the styling mode."""
        pass