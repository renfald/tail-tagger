from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QWidget
from PySide6.QtCore import Qt
from tag_list_panel import TagListPanel
from tag_widget import TagWidget

class SelectedTagsPanel(TagListPanel):
    def __init__(self, main_window, parent=None): # Accept main_window
        super().__init__(main_window, panel_title="Selected Tags") # Pass main_window and panel title
        self.main_window = main_window # Store main_window (needed for drag/drop)
        self.setAcceptDrops(True)
        self.drop_indicator_line = None  # Initialize drop indicator line as None
        self.dragged_tag_name = None  # Track the tag being dragged

    def get_styling_mode(self):
        return "ignore_select"  # Right panel ignores selection for styling

    def _get_tag_data_list(self):
        """Returns the list of TagData objects for this panel (Selected Tags)."""
        if self.main_window:
            return self.main_window.selected_tags_for_current_image
        else:
            print("Warning: SelectedTagsPanel does not have access to MainWindow instance.")
            return [] # Return empty list if no main_window

    def dragEnterEvent(self, event):
        """Handles drag enter events for the panel."""
        if event.mimeData().hasText():
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
            print("Drag Enter Event: Drag ignored - no text data.")

    def dragMoveEvent(self, event):
        """Handles drag move events for the panel, updating drop indicator."""
        if event.mimeData().hasText():
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
            print("Drag Move Event: Drag ignored - no text data.")

    def dragLeaveEvent(self, event):
        """Handles drag leave events."""
        print("Drag Leave Event: Hiding indicator")
        if self.drop_indicator_line:
            self.drop_indicator_line.hide() # Hide the indicator when drag leaves
        self.dragged_tag_name = None  # Reset dragged tag name

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
                tag_index = len(self.main_window.selected_tags_for_current_image)
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
        """
        for i, tag_data in enumerate(self.main_window.selected_tags_for_current_image):
            if tag_data.name == tag_name:
                return i
        return 0  # Default to first position if not found

    # not needed for now
    def add_tag(self, tag_name, is_known=True):
        pass
    def remove_tag(self, tag_name):
        pass
    def clear_tags(self):
        pass
    def get_tags(self):
        pass
    def set_tags(self, tags):
        pass
    def set_tag_selected(self, tag_name, is_selected):
        pass
    def is_tag_draggable(self, tag_name):
        pass

    def dropEvent(self, event):
        """Handles drop events for the panel, implementing tag reordering and workfile update."""
        if event.mimeData().hasText():
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
            
            for i, tag_data in enumerate(self.main_window.selected_tags_for_current_image):
                if tag_data.name == tag_name:
                    dragged_tag_data = tag_data
                    dragged_tag_orig_index = i
                    break
            
            if dragged_tag_data:
                # Account for the tag's original position when inserting
                self.main_window.selected_tags_for_current_image.remove(dragged_tag_data)
                
                # Adjust drop index if needed
                if drop_index > dragged_tag_orig_index:
                    drop_index -= 1  # Adjust for the removal of the tag
                
                # Insert at the target position
                self.main_window.selected_tags_for_current_image.insert(drop_index, dragged_tag_data)
                print(f"  Tag '{tag_name}' reordered from {dragged_tag_orig_index} to {drop_index}")

                # Update workfile
                self.main_window.update_workfile_for_current_image()
                print("  Workfile updated with new tag order.")
            else:
                print(f"Warning: Dragged tag '{tag_name}' not found in selected_tags_for_current_image list!")

            # Reset dragged tag name
            self.dragged_tag_name = None
            
            event.acceptProposedAction()
            self.update_display()
        else:
            event.ignore()
            print("Drop Event: Drop ignored - no text data.")