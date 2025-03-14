from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from tag_list_panel import TagListPanel
from tag_widget import TagWidget

class AllTagsPanel(TagListPanel):
    def __init__(self, main_window, tag_list_model, parent=None): # Accept main_window
        super().__init__(main_window, panel_title="All Tags") # Pass main_window and panel title
        self.main_window = main_window # Store main_window
        self.tag_list_model = tag_list_model  # Store the model

    def get_styling_mode(self):
        return "dim_on_select"

    def _get_tag_data_list(self):
        """Returns the list of TagData objects for this panel (All Tags)."""
        return self.tag_list_model.get_known_tags()

    # No longer need update_display - using template method from base class

    def add_tag(self, tag_name, is_known=True):
        pass # Not needed

    def remove_tag(self, tag_name):
        pass  # Not needed

    def clear_tags(self):
        pass  # Not needed

    def get_tags(self):
        pass # Not needed

    def set_tags(self, tags):
        pass  # Not needed

    def set_tag_selected(self, tag_name, is_selected):
        pass  # Not needed

    def is_tag_draggable(self, tag_name):
        pass

    def dropEvent(self, event):
        pass