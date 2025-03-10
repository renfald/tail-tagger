# frequently_used_panel.py
from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtCore import Qt
from tag_list_panel import TagListPanel

class FrequentlyUsedPanel(TagListPanel):
    def __init__(self, main_window, parent=None):
        super().__init__(main_window)
        self.main_window = main_window

    def _get_tag_data_list(self):
        """Returns the list of TagData objects for this panel (Frequently Used Tags), ordered by usage frequency."""
        return self.main_window.tag_list_model.get_frequent_tags()

    def get_styling_mode(self):
        """Returns the styling mode for this panel."""
        return "dim_on_select" # Or "ignore_select" - choose the desired styling