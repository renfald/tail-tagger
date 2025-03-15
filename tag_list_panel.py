from abc import ABC, abstractmethod
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy, QScrollArea
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from tag_widget import TagWidget  # Import for type hints

class TagListPanel(QWidget, ABC, metaclass=type('ABCMetaQWidget', (type(QWidget), type(ABC)), {})):  # Explicit metaclass
    """Abstract base class for tag list panels."""

    def __init__(self, main_window=None, panel_title=""):
        super().__init__(main_window)
        self.main_window = main_window
        # self.setStyleSheet("background-color: #242424;") # This sets a dark grey background for the panel
        
        # Main layout for the panel
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create panel title label (fixed at top)
        self.title_label = QLabel(panel_title)
        self.title_label.setStyleSheet("color: white; font-weight: bold; padding: 3px; background-color: rgb(53,53,53); margin: 0px;")
        # self.title_label.setStyleSheet("color: white; font-weight: bold; padding: 3px; background-color: rgb(53,53,53); border-top: 2px solid #242424; margin: 0px;") # potentiall alternate. provides a spacer for the splitters but looks bad in selected tags panel
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.main_layout.addWidget(self.title_label, 0, Qt.AlignTop)
        
        # Create scroll area for tag widgets
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.viewport().setStyleSheet("background-color: #191919;") # Explicitly set viewport color
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
        
        # Drag and drop properties
        self.drop_indicator_line = None  # Initialize drop indicator line as None
        self.dragged_tag_name = None  # Track the tag being dragged

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

    # Common drag and drop functionality
    def dragEnterEvent(self, event):
        """Handles drag enter events for the panel."""
        # Check if dragging is allowed in this panel for the tag being dragged
        if event.mimeData().hasText() and self._is_any_tag_draggable():
            event.acceptProposedAction()
            print("Drag Enter Event: Drag accepted for text data.")
            
            # Store the dragged tag name
            self.dragged_tag_name = event.mimeData().text()
            print(f"  Dragged tag name: {self.dragged_tag_name}")

            # --- Create and initialize the indicator line here ---
            if self.drop_indicator_line is None: # Only create if it doesn't exist
                self.drop_indicator_line = QWidget(self.tags_container) # Create in tags container instead of panel
                self.drop_indicator_line.setStyleSheet("background-color: white; height: 2px;") # Style as a white line, 2px height
                self.drop_indicator_line.hide() # Initially hidden
            else:
                self.drop_indicator_line.hide() # Ensure hidden at drag start
        else:
            event.ignore()
            print("Drag Enter Event: Drag ignored - no text data or panel does not support dragging.")

    def dragMoveEvent(self, event):
        """Handles drag move events for the panel, updating drop indicator."""
        if event.mimeData().hasText() and self._is_any_tag_draggable():
            event.acceptProposedAction()
            drop_pos = event.pos()
            # Convert position to be relative to the tags container
            container_pos = self.tags_container.mapFrom(self, drop_pos)
            
            # Get the visual insertion position (y-coordinate) and tag index
            visual_position, tag_index = self._get_visual_insertion_position(container_pos)
            
            # Set and show the indicator line
            container_width = self.tags_container.width()
            if self.drop_indicator_line is None:
                self.drop_indicator_line = QWidget(self.tags_container)
                self.drop_indicator_line.setStyleSheet("background-color: white; height: 2px;")
                self.drop_indicator_line.hide()
            
            self.drop_indicator_line.setGeometry(0, visual_position, container_width, 2)
            self.drop_indicator_line.raise_()
            self.drop_indicator_line.show()
        else:
            event.ignore()
            print("Drag Move Event: Drag ignored - no text data or panel does not support dragging.")

    def dragLeaveEvent(self, event):
        """Handles drag leave events."""
        print("Drag Leave Event: Hiding indicator")
        if self.drop_indicator_line:
            self.drop_indicator_line.hide() # Hide the indicator when drag leaves
        self.dragged_tag_name = None  # Reset dragged tag name
        
    def _is_any_tag_draggable(self):
        """Helper method to check if this panel supports dragging any tags."""
        for tag_data in self._get_tag_data_list():
            if self.is_tag_draggable(tag_data.name):
                return True
        return False

    def _get_visual_insertion_position(self, container_pos):
        """
        Determine the visual insertion position and corresponding tag index
        based on the container position, accounting for hidden tags.
        
        Returns:
        - visual_position: Y coordinate for the indicator line
        - tag_index: Index in the data model where the tag should be inserted
        """
        # Get visible tag widgets
        visible_tags = []
        for index in range(self.layout.count()):
            widget_item = self.layout.itemAt(index)
            if widget_item is not None and widget_item.widget() is not None:
                tag_widget = widget_item.widget()
                if isinstance(tag_widget, TagWidget) and tag_widget.isVisible():
                    visible_tags.append((index, tag_widget))
        
        # Find the desired position among visible tags
        insertion_point_found = False
        visual_position = 0
        tag_index = 0
        
        # Find the position in the visible tags
        for layout_index, tag_widget in visible_tags:
            tag_pos_bottom = tag_widget.geometry().bottom()
            # Check if the mouse is less than 10px above the bottom of the tag. 
            # We want the indicator to change if the mouse goes past the middle
            if container_pos.y() < tag_pos_bottom - 10:  # Adjust this if the line should change at a diff height
                visual_position = tag_widget.geometry().top()
                tag_index = self._get_data_index_for_tag(tag_widget.tag_name)
                print(f"  Drop index determined: {tag_index} (before tag '{tag_widget.tag_name}')")
                insertion_point_found = True
                break
        
        if not insertion_point_found:
            # Position at the end of visible tags
            if visible_tags:
                _, last_tag_widget = visible_tags[-1]
                visual_position = last_tag_widget.geometry().bottom()
                tag_index = len(self._get_tag_data_list())
                print(f"  Drop index determined: {tag_index} (after last tag)")
            else:
                # Panel is empty or all tags are hidden
                visual_position = 0
                tag_index = 0
                print("  Drop index determined: 0 (panel empty)")
        
        return visual_position, tag_index
    
    def _get_data_index_for_tag(self, tag_name):
        """
        Get the index of a tag in the data model by its name.
        Default implementation - override if necessary.
        """
        for i, tag_data in enumerate(self._get_tag_data_list()):
            if tag_data.name == tag_name:
                return i
        return 0  # Default to first position if not found

    def dropEvent(self, event):
        """Handles drop events for the panel, implementing tag reordering."""
        if event.mimeData().hasText() and self._is_any_tag_draggable() and self.is_tag_draggable(event.mimeData().text()):
            tag_name = event.mimeData().text()
            print(f"Drop Event: Tag '{tag_name}' dropped!")

            if self.drop_indicator_line:
                self.drop_indicator_line.hide() # Hide indicator on drop

            # Get the drop position
            drop_pos = event.pos()
            container_pos = self.tags_container.mapFrom(self, drop_pos)
            
            # Get visual position and data index
            _, drop_index = self._get_visual_insertion_position(container_pos)
            
            # Find and handle the dragged tag
            dragged_tag_data = None
            dragged_tag_orig_index = -1
            
            tag_data_list = self._get_tag_data_list()
            for i, tag_data in enumerate(tag_data_list):
                if tag_data.name == tag_name:
                    dragged_tag_data = tag_data
                    dragged_tag_orig_index = i
                    break
            
            if dragged_tag_data:
                # Account for the tag's original position when inserting
                self._remove_tag_from_data_list(dragged_tag_data)
                
                # Adjust drop index if needed
                if drop_index > dragged_tag_orig_index:
                    drop_index -= 1  # Adjust for the removal of the tag
                
                # Insert at the target position
                self._insert_tag_into_data_list(dragged_tag_data, drop_index)
                print(f"  Tag '{tag_name}' reordered from {dragged_tag_orig_index} to {drop_index}")

                # Update appropriate data (file, workfile, etc.)
                self._handle_post_drop_update(tag_name, dragged_tag_orig_index, drop_index)
            else:
                print(f"Warning: Dragged tag '{tag_name}' not found in tag list!")

            # Reset dragged tag name
            self.dragged_tag_name = None
            
            event.acceptProposedAction()
            self.update_display()
        else:
            event.ignore()
            print("Drop Event: Drop ignored - panel doesn't support dragging or tag not draggable.")

    @abstractmethod
    def _remove_tag_from_data_list(self, tag_data):
        """Abstract method: Remove a tag from the data list. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def _insert_tag_into_data_list(self, tag_data, index):
        """Abstract method: Insert a tag into the data list at specified index. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def _handle_post_drop_update(self, tag_name, original_index, new_index):
        """Abstract method: Handle updates after a tag is dropped. Must be implemented by subclasses."""
        pass

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