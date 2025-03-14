from abc import ABC, abstractmethod
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy, QScrollArea
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent

class TagListPanel(QWidget, ABC, metaclass=type('ABCMetaQWidget', (type(QWidget), type(ABC)), {})):  # Explicit metaclass
    """Abstract base class for tag list panels."""

    def __init__(self, parent=None, panel_title=""):
        super().__init__(parent)
        # self.setStyleSheet("background-color: #242424;") # This sets a dark grey background for the panel
        
        # Main layout for the panel
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create panel title label (fixed at top)
        self.title_label = QLabel(panel_title)
        self.title_label.setStyleSheet("color: white; font-weight: bold; padding: 3px; background-color: rgb(53,53,53); border: none; margin: 0px;")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.main_layout.addWidget(self.title_label, 0, Qt.AlignTop)
        
        # Create scroll area for tag widgets
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: none;")
        self.scroll_area.viewport().setStyleSheet("background-color: #242424;") # Explicitly set viewport color
        self.main_layout.addWidget(self.scroll_area, 1) # Make scroll area take remaining space
        
        # Container widget for tag widgets inside scroll area
        self.tags_container = QWidget()
        # self.tags_container.setStyleSheet("background-color: #242424;")
        self.layout = QVBoxLayout(self.tags_container)
        self.layout.setAlignment(Qt.AlignTop)
        self.layout.setSpacing(1) # Space between the widgets
        self.layout.setContentsMargins(1, 1, 1, 1) # Margin around the tags container
        
        # Set the container as the scroll area's widget
        self.scroll_area.setWidget(self.tags_container)

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
            self.layout.addWidget(tag_widget) # Add to container layout

    def _clear_widgets(self):
        """Helper method: Clears existing TagWidgets from the layout."""
        # Clear all widgets from the tags container layout
        for i in reversed(range(self.layout.count())):
            widget = self.layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

    def _create_tag_widget(self, tag_data):
        """Helper method: Creates and configures a TagWidget."""
        from tag_widget import TagWidget # Import here to avoid circular dependency
        tag_widget = TagWidget(tag_data=tag_data, is_selected=None, is_known_tag=None) # Pass tag_data as first arg, remove positional is_selected and is_known_tag
        tag_widget.set_styling_mode(self.get_styling_mode()) # Set styling mode from subclass
        tag_widget.tag_clicked.connect(self.main_window._handle_tag_clicked) # Connect tag selection logic
        tag_widget.favorite_star_clicked.connect(self.main_window._handle_favorite_star_clicked) # Connect favorite logic
        return tag_widget

    def keyPressEvent(self, event: QKeyEvent):
        """Overrides keyPressEvent to handle keyboard shortcuts."""
        # Delegate event handling to KeyboardManager
        if not self.main_window.keyboard_manager.handle_key_press(event, self):
            # If event was not handled by KeyboardManager, pass it to the parent
            super().keyPressEvent(event)

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