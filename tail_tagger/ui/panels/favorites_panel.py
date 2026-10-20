from PySide6.QtWidgets import QFrame, QMenu
from PySide6.QtGui import QAction
from tail_tagger.ui.panels.tag_list_panel import TagListPanel

class FavoritesPanel(TagListPanel):
    def __init__(self, main_window, parent=None):
        super().__init__(main_window, panel_title="Favorites")
        self.setAcceptDrops(True)  # This panel accepts drops
        # Switching tag source or adding a tag can change which favorites are shown
        self.main_window.favorites_changed.connect(self.update_display)
        self.main_window.tags_changed.connect(self.update_display)
        self.update_display()

    def get_styling_mode(self):
        return "dim_on_select"

    def _get_tag_data_list(self):
        """Returns the list of TagData objects for this panel (Favorites)."""
        return self.main_window.visible_favorite_tags()

    def is_tag_draggable(self, tag_name):
        """Always allow dragging in this panel."""
        return True

    def _get_bulk_operations(self):
        """Returns list of allowed bulk operations for this panel."""
        return ['add_front', 'add_end', 'remove', 'replace']

    def _move_tag(self, tag_name, new_index):
        """Reorder favorites and save."""
        self.main_window.move_favorite(tag_name, new_index)

    
        
    def _add_context_menu_actions(self, menu, tag_data):
        """Add panel-specific context menu actions for FavoritesPanel.
        No specific actions for this panel yet.
        """
        # For now, we don't have specific actions for favorite tags
        # Could add "Remove from Favorites" option here in the future
        return False  # No actions added

