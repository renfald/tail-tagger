from abc import ABC, abstractmethod
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy, QScrollArea
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QKeyEvent
from tag_widget import TagWidget

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
        
        # Connect to resize events to update tags when container size changes
        self.scroll_area.resizeEvent = self._on_scroll_area_resize

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
        for i in reversed(range(self.layout.count())):
            widget = self.layout.itemAt(i).widget()
            if widget is not None:
                self.layout.removeWidget(widget)
                if hasattr(widget, 'cleanup'):
                    widget.cleanup()
                widget.deleteLater()

    def _create_tag_widget(self, tag_data):
        """Helper method: Creates and configures a TagWidget."""
        from tag_widget import TagWidget # Import here to avoid circular dependency
        tag_widget = TagWidget(tag_data=tag_data, is_selected=None, is_known_tag=None) # Pass tag_data as first arg, remove positional is_selected and is_known_tag
        tag_widget.set_styling_mode(self.get_styling_mode()) # Set styling mode from subclass
        tag_widget.tag_clicked.connect(self.main_window._handle_tag_clicked) # Connect tag selection logic
        tag_widget.favorite_star_clicked.connect(self.main_window._handle_favorite_star_clicked) # Connect favorite logic
        tag_widget.tag_right_clicked.connect(self._handle_tag_right_clicked) # Connect right-click handling
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

            # Initialize or reset drop indicator
            self._ensure_drop_indicator_exists()
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
            self._ensure_drop_indicator_exists()
            
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
        
    def _ensure_drop_indicator_exists(self):
        """Helper method to initialize the drop indicator line if it doesn't exist yet."""
        if self.drop_indicator_line is None:
            self.drop_indicator_line = QWidget(self.tags_container)
            self.drop_indicator_line.setStyleSheet("background-color: white; height: 2px;")
            self.drop_indicator_line.hide()

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
    def is_tag_draggable(self, tag_name):
        """Returns True if draggable, False otherwise."""
        return False

    @abstractmethod
    def _get_bulk_operations(self):
        """Abstract method: Returns a list of allowed bulk operations for this panel.

        Returns:
            list: List of operation strings. Valid operations:
                  'add_front', 'add_end', 'remove'
                  Return empty list to disable bulk operations for this panel.
        """
        return []

    @Slot(str)
    def _handle_tag_right_clicked(self, tag_name):
        """Handles right-click events on TagWidgets. Creates and displays a context menu with panel-specific actions."""
        print(f"Right-clicked tag: {tag_name}")
        
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QCursor, QAction
        
        # Find tag data for the clicked tag
        tag_data = None
        for td in self._get_tag_data_list():
            if td.name == tag_name:
                tag_data = td
                break
        
        if not tag_data:
            print(f"Warning: Tag data not found for right-clicked tag '{tag_name}'")
            return
            
        # Create context menu
        menu = QMenu(self)

        # Add panel-specific actions to menu
        actions_added = self._add_context_menu_actions(menu, tag_data)

        # Add bulk operations submenu if this panel supports them
        bulk_ops = self._get_bulk_operations()
        if bulk_ops:
            # Add separator if panel-specific actions were added
            if actions_added:
                menu.addSeparator()

            # Create bulk operations submenu
            bulk_menu = menu.addMenu("Bulk Operations")

            if 'add_front' in bulk_ops:
                add_front_action = QAction(f"Add to All Images (Beginning)", self)
                add_front_action.triggered.connect(lambda: self.main_window.execute_bulk_operation('add_front', tag_name))
                bulk_menu.addAction(add_front_action)

            if 'add_end' in bulk_ops:
                add_end_action = QAction(f"Add to All Images (End)", self)
                add_end_action.triggered.connect(lambda: self.main_window.execute_bulk_operation('add_end', tag_name))
                bulk_menu.addAction(add_end_action)

            if 'remove' in bulk_ops:
                # Add separator between add and remove if both exist
                if ('add_front' in bulk_ops or 'add_end' in bulk_ops):
                    bulk_menu.addSeparator()

                remove_action = QAction(f"Remove from All Images", self)
                remove_action.triggered.connect(lambda: self.main_window.execute_bulk_operation('remove', tag_name))
                bulk_menu.addAction(remove_action)

            actions_added = True  # Bulk operations count as actions

        # Only show menu if actions were added
        if actions_added:
            menu.popup(QCursor.pos())
            
    @abstractmethod
    def _add_context_menu_actions(self, menu, tag_data):
        """Abstract method: Add panel-specific context menu actions.
        Args:
            menu (QMenu): The menu to add actions to
            tag_data (TagData): The TagData object for the right-clicked tag
            
        Returns:
            bool: True if any actions were added, False otherwise
        """
        return False
        
    def _on_scroll_area_resize(self, event):
        """Handle scroll area resize events to update tag widget elided text.
        
        This method ensures that when the panel is resized via splitter,
        the tag widgets will update their elided text accordingly.
        """
        # Call original resize event handler
        QScrollArea.resizeEvent(self.scroll_area, event)
        
        # Update all tag widgets
        self._update_tag_widgets_elided_text()
        
    def _update_tag_widgets_elided_text(self):
        """Update elided text in all tag widgets in this panel."""
        # Find all TagWidget instances in the container
        for i in range(self.layout.count()):
            widget_item = self.layout.itemAt(i)
            if widget_item and widget_item.widget():
                tag_widget = widget_item.widget()
                # Check if it's a TagWidget with _update_elided_text method
                if hasattr(tag_widget, '_update_elided_text'):
                    tag_widget._update_elided_text()