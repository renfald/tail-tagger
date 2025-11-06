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
    
    def _add_context_menu_actions(self, menu, tag_data):
        """Add panel-specific context menu actions for FrequentlyUsedPanel.
        Adds 'Remove from Frequently Used' option.
        """
        remove_action = QAction("Remove from Frequently Used", self)
        remove_action.triggered.connect(lambda: self._remove_tag_from_frequent_list(tag_data.name))
        menu.addAction(remove_action)
        
        # Return True because we added an action
        return True

    def _remove_tag_from_frequent_list(self, tag_name):
        """Handles removing a tag from the frequently used list (and usage data)."""
        print(f"Removing tag '{tag_name}' from frequently used list.") # Debug message

        self.main_window.tag_list_model.remove_tag_usage(tag_name) # Call TagListModel to remove usage data
        self.main_window.file_operations.save_usage_data(self.main_window.tag_list_model.tag_usage_counts) # Save updated usage data to file
        self.update_display() # Refresh the FrequentlyUsedPanel display
    
    # Required implementations for abstract methods
    def is_tag_draggable(self, tag_name):
        return False # Not draggable in this panel

    def _get_bulk_operations(self):
        """Returns list of allowed bulk operations for this panel."""
        return ['add_front', 'add_end', 'remove']

    def _remove_tag_from_data_list(self, tag_data):
        """Not used in non-draggable panel."""
        pass

    def _insert_tag_into_data_list(self, tag_data, index):
        """Not used in non-draggable panel."""
        pass

    def _handle_post_drop_update(self, tag_name, original_index, new_index):
        """Not used in non-draggable panel."""
        pass
    
    