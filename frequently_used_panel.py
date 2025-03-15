# frequently_used_panel.py
from tag_list_panel import TagListPanel
from PySide6.QtWidgets import QMenu
from PySide6.QtGui import QAction

class FrequentlyUsedPanel(TagListPanel):
    def __init__(self, main_window, parent=None):
        super().__init__(main_window, panel_title="Frequently Used")

    def _get_tag_data_list(self):
        """Returns the list of TagData objects for this panel (Frequently Used Tags), ordered by usage frequency."""
        return self.main_window.tag_list_model.get_frequent_tags()

    def get_styling_mode(self):
        """Returns the styling mode for this panel."""
        return "dim_on_select" # Or "ignore_select" - choose the desired styling
    
    def _handle_tag_right_clicked(self, tag_name):
        """Handles right-click events on TagWidgets in this panel.
        Creates and displays a context menu with "Remove from Frequently Used" option.
        """
        print(f"Right-clicked tag: {tag_name}")

        menu = QMenu(self)
        remove_action = QAction("Remove from Frequently Used", self)
        remove_action.triggered.connect(lambda: self._remove_tag_from_frequent_list(tag_name))
        menu.addAction(remove_action)

        menu.popup(self.mapToGlobal(self.rect().topLeft()) + self.mapFromGlobal(self.cursor().pos())) # Popup menu at cursor position
    
    # overriding the base class method to handle the right-click event. Don't like it. feel like we should handle right click in a more centralized way TODO:
    def _create_tag_widget(self, tag_data):
        """Helper method: Creates and configures a TagWidget."""
        tag_widget = super()._create_tag_widget(tag_data)
        tag_widget.tag_right_clicked.connect(self._handle_tag_right_clicked) # Add right-click handling
        return tag_widget

    def _remove_tag_from_frequent_list(self, tag_name):
        """Handles removing a tag from the frequently used list (and usage data)."""
        print(f"Removing tag '{tag_name}' from frequently used list.") # Debug message

        self.main_window.tag_list_model.remove_tag_usage(tag_name) # Call TagListModel to remove usage data
        self.main_window.file_operations.save_usage_data(self.main_window.tag_list_model.tag_usage_counts) # Save updated usage data to file
        self.update_display() # Refresh the FrequentlyUsedPanel display
    
    # Required implementations for abstract methods
    def is_tag_draggable(self, tag_name):
        return False # Not draggable in this panel

    def _remove_tag_from_data_list(self, tag_data):
        """Not used in non-draggable panel."""
        pass

    def _insert_tag_into_data_list(self, tag_data, index):
        """Not used in non-draggable panel."""
        pass

    def _handle_post_drop_update(self, tag_name, original_index, new_index):
        """Not used in non-draggable panel."""
        pass
    
    # Implementing abstract methods to meet TagListPanel requirements
    def add_tag(self, tag_name, is_known=True):
        pass  # Not needed

    def remove_tag(self, tag_name):
        pass  # Not needed

    def clear_tags(self):
        pass  # Not needed

    def get_tags(self):
        pass  # Not needed

    def set_tags(self, tags):
        pass # Not needed

    def set_tag_selected(self, tag_name, is_selected):
        pass  # Not needed