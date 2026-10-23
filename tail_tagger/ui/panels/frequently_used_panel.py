# frequently_used_panel.py
from tail_tagger.ui.panels.tag_list_panel import TagListPanel
from PySide6.QtWidgets import QMenu
from PySide6.QtGui import QAction

class FrequentlyUsedPanel(TagListPanel):
    def __init__(self, main_window, parent=None):
        super().__init__(main_window, panel_title="Frequently Used")
        # Also rebuilt when tags change: switching source replaces every tag, and a
        # promoted tag may already have a usage count to show
        self.main_window.usage_changed.connect(self.update_display)
        self.main_window.tags_changed.connect(self.update_display)
        self.update_display()

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
        remove_action.triggered.connect(lambda: self.main_window.remove_from_frequent(tag_data.name))
        menu.addAction(remove_action)
        
        # Return True because we added an action
        return True

    # Required implementations for abstract methods
    def _get_bulk_operations(self):
        """Returns list of allowed bulk operations for this panel."""
        return ['add_front', 'add_end', 'remove', 'replace']
    
    