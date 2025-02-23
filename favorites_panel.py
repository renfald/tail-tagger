from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from tag_list_panel import TagListPanel
from tag_widget import TagWidget  # Import TagWidget

class FavoritesPanel(TagListPanel):
    def __init__(self, main_window, parent=None):
        super().__init__(main_window) # Pass main_window to TagListPanel parent init
        self.main_window = main_window  # Store main_window

    def get_styling_mode(self):
        return "ignore_select"

    def _get_tag_data_list(self):
        """Returns the list of TagData objects for this panel (Favorites)."""
        return self.main_window.favorite_tags_ordered

    # No longer need update_display - inherit from TagListPanel

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

    def is_tag_draggable(self, tag_name):
        return True # Always draggable in this panel

    def dropEvent(self, event):
        pass # To be implemented