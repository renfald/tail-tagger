from abc import ABC, abstractmethod
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt

class TagListPanel(QWidget, ABC, metaclass=type('ABCMetaQWidget', (type(QWidget), type(ABC)), {})):  # Explicit metaclass
    """Abstract base class for panels that display a list of TagWidgets."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignTop)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setAcceptDrops(True) # Important: Enable drop events.

    @abstractmethod
    def add_tag(self, tag_name, is_known=True):
        """Adds a tag to the panel. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def remove_tag(self, tag_name):
        """Removes a tag from the panel.  Must be implemented by subclasses."""
        pass

    @abstractmethod
    def clear_tags(self):
        """Clears all tags from the panel. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def get_tags(self):
        """Returns a list of all tags in the panel (in their current order). Must be implemented by subclasses."""
        return [] # Return empty list

    @abstractmethod
    def set_tags(self, tags):
        """Sets the tags in the panel, replacing any existing tags. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def set_tag_selected(self, tag_name, is_selected):
        """Sets the selection state of a specific tag. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def is_tag_draggable(self, tag_name):
        """Returns True if the tag can be dragged, False otherwise. Must be implemented by subclasses."""
        return False  # Default: not draggable.

    def dragEnterEvent(self, event):
        if event.source() == self:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.source() == self:
            event.acceptProposedAction()

    @abstractmethod
    def dropEvent(self, event):
        """Handles drop events (reordering). Must be implemented by subclasses if dragging is allowed."""
        pass