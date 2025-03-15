from PySide6.QtWidgets import QFrame
from tag_list_panel import TagListPanel

class SelectedTagsPanel(TagListPanel):
    def __init__(self, main_window, parent=None):
        super().__init__(main_window, panel_title="Selected Tags")
        self.setAcceptDrops(True)  # This panel accepts drops

    def get_styling_mode(self):
        return "ignore_select"  # Right panel ignores selection for styling

    def _get_tag_data_list(self):
        """Returns the list of TagData objects for this panel (Selected Tags)."""
        if self.main_window:
            return self.main_window.selected_tags_for_current_image
        else:
            print("Warning: SelectedTagsPanel does not have access to MainWindow instance.")
            return [] # Return empty list if no main_window

    def is_tag_draggable(self, tag_name):
        """Always allow dragging in this panel."""
        return True

    def _remove_tag_from_data_list(self, tag_data):
        """Remove tag from the selected tags list."""
        self.main_window.selected_tags_for_current_image.remove(tag_data)

    def _insert_tag_into_data_list(self, tag_data, index):
        """Insert tag into the selected tags list at specified index."""
        self.main_window.selected_tags_for_current_image.insert(index, tag_data)

    def _handle_post_drop_update(self, tag_name, original_index, new_index):
        """Update workfile after tag order changes."""
        self.main_window.update_workfile_for_current_image()
        print("  Workfile updated with new tag order.")

    # These methods are not needed for SelectedTagsPanel
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