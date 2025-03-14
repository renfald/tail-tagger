from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QWidget
from PySide6.QtCore import Qt
from tag_list_panel import TagListPanel
from tag_widget import TagWidget

# TODO: There is a bug where the tag will go one slot lower than expected if you are dragging downward past where it originally was. must be fixed here and in FavoritesPanel

class SelectedTagsPanel(TagListPanel):
    def __init__(self, main_window, parent=None): # Accept main_window
        super().__init__(main_window, panel_title="Selected Tags") # Pass main_window and panel title
        self.main_window = main_window # Store main_window (needed for drag/drop)
        self.setAcceptDrops(True)
        self.drop_indicator_line = None  # Initialize drop indicator line as None

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

            # --- Create and initialize the indicator line here ---
            if self.drop_indicator_line is None: # Only create if it doesn't exist
                self.drop_indicator_line = QWidget(self) # Use QWidget for simple line
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
            drop_index = 0
            indicator_y_pos = 0 # Initialize indicator Y position

            # --- Determine drop index and Y position ---
            insertion_point_found = False # Flag to track if we found an insertion point

            for index in range(self.layout.count()):
                widget_item = self.layout.itemAt(index)
                if widget_item is not None and widget_item.widget() is not None:
                    tag_widget = widget_item.widget()
                    if isinstance(tag_widget, TagWidget):
                        # Check if the mouse is less than 10px above the bottom of the tag. 
                        # We want the indicator to change if the mouse goes past the middle
                        if drop_pos.y() < tag_widget.geometry().bottom() - 10: # Adjust this if the line should change at a diff height
                            drop_index = index
                            indicator_y_pos = tag_widget.geometry().top() # Position line at the top of the tag
                            print(f"  Drop index determined: {drop_index} (before tag '{tag_widget.tag_name}')")
                            insertion_point_found = True
                            break # Exit loop, insertion point found
                        # else:  No else needed here, continue to next tag if not before current tag

            if not insertion_point_found:
                # If we didn't find an insertion point in the loop, it means we are dropping at the end
                if self.layout.count() > 0:
                    # Position the indicator line below the last tag
                    last_tag_widget = self.layout.itemAt(self.layout.count() - 1).widget()
                    indicator_y_pos = last_tag_widget.geometry().bottom()
                    drop_index = self.layout.count() # Insert at the end
                    print(f"  Drop index determined: {drop_index} (after last tag)")
                else:
                    # Panel is empty
                    print("  Drop index determined: 0 (panel empty)")
                    indicator_y_pos = 0 # Top of panel


            # --- Position and show the indicator line ---
            panel_width = self.width() # Get panel width to make line span across
            self.drop_indicator_line.setGeometry(0, indicator_y_pos, panel_width, 2) # x=0, y=calculated, width=panel width, height=2px
            self.drop_indicator_line.raise_() # Ensure it's on top of tags
            self.drop_indicator_line.show()

        else:
            event.ignore()
            print("Drag Move Event: Drag ignored - no text data.")

    def dragLeaveEvent(self, event):
        """Handles drag leave events."""
        print("Drag Leave Event: Hiding indicator")
        if self.drop_indicator_line:
            self.drop_indicator_line.hide() # Hide the indicator when drag leaves

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

            drop_pos = event.pos()
            drop_index = 0

            for index in range(self.layout.count()): # Re-calculate drop index just before insertion for robustness
                widget_item = self.layout.itemAt(index)
                if widget_item is not None and widget_item.widget() is not None:
                    tag_widget = widget_item.widget()
                    if isinstance(tag_widget, TagWidget):
                        if drop_pos.y() < tag_widget.geometry().bottom() - 10: # This should line up with the indicator logic
                            drop_index = index
                            print(f"  Drop index determined (on drop): {drop_index} (before tag '{tag_widget.tag_name}')")
                            break
                        else:
                            drop_index = index + 1
            else:
                print("  Drop index determined (on drop): 0 (panel empty or dropped below all tags)")

            # --- Reordering Logic ---
            dragged_tag_data = None
            for tag_data in self.main_window.selected_tags_for_current_image:
                if tag_data.name == tag_name:
                    dragged_tag_data = tag_data
                    break

            if dragged_tag_data:
                self.main_window.selected_tags_for_current_image.remove(dragged_tag_data)
                self.main_window.selected_tags_for_current_image.insert(drop_index, dragged_tag_data)
                print(f"  Tag '{tag_name}' reordered to index {drop_index}")

                # --- Workfile Update ---
                # updating the workfile based on the current state of the selected_tags_for_current_image
                self.main_window.update_workfile_for_current_image()
                print("  Workfile updated with new tag order.") # Debug

            else:
                print(f"Warning: Dragged tag '{tag_name}' not found in selected_tags_for_current_image list!")

            event.acceptProposedAction()
            self.update_display() #TEMP - keep update display for now - will be refined in next steps

        else:
            event.ignore()
            print("Drop Event: Drop ignored - no text data.")