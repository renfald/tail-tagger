from abc import ABC, abstractmethod
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt

class TagListPanel(QWidget, ABC, metaclass=type('ABCMetaQWidget', (type(QWidget), type(ABC)), {})):  # Explicit metaclass
    """Abstract base class for tag list panels."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignTop)
        self.layout.setSpacing(1) # This is the space between the widgets
        self.layout.setContentsMargins(1, 1, 1, 1) # This is the margin around the entire panel, not the individual widgets
        self.setStyleSheet("background-color: #242424;") # This sets a dark grey background for the tag panels

    @abstractmethod
    def _get_tag_data_list(self):
        """Abstract method: Subclasses must implement to return the list of TagData objects."""
        pass

    @abstractmethod
    def get_styling_mode(self):
        """Abstract method: Subclasses must implement to return their styling mode."""
        pass

    def update_display(self):
        """Template method: Updates the panel display."""
        self._clear_widgets()  # Clear existing widgets (using helper method)
        tag_data_list = self._get_tag_data_list() # Get tag data from subclass

        for tag_data in tag_data_list:
            tag_widget = self._create_tag_widget(tag_data) # Create and configure TagWidget

            self.layout.addWidget(tag_widget) # Add to layout

    def _clear_widgets(self):
        """Helper method: Clears existing TagWidgets from the layout."""
        for i in reversed(range(self.layout.count())):
            widget = self.layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

    def _create_tag_widget(self, tag_data):
        """Helper method: Creates and configures a TagWidget."""
        from tag_widget import TagWidget # Import here to avoid circular dependency
        tag_widget = TagWidget(tag_data=tag_data, is_selected=None, is_known_tag=None) # Pass tag_data as first arg, remove positional is_selected and is_known_tag
        tag_widget.set_styling_mode(self.get_styling_mode()) # Set styling mode from subclass
        tag_widget.tag_clicked.connect(self.main_window._handle_tag_clicked) # Connect click signal
        return tag_widget


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
        pass

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