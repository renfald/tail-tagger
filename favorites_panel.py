from PySide6.QtWidgets import QFrame, QMenu
from PySide6.QtGui import QAction
from tag_list_panel import TagListPanel

class FavoritesPanel(TagListPanel):
    def __init__(self, main_window, parent=None):
        super().__init__(main_window, panel_title="Favorites")
        self.setAcceptDrops(True)  # This panel accepts drops

    def get_styling_mode(self):
        return "dim_on_select"

    def _get_tag_data_list(self):
        """Returns the list of TagData objects for this panel (Favorites)."""
        return self.main_window.favorite_tags_ordered

    def is_tag_draggable(self, tag_name):
        """Always allow dragging in this panel."""
        return True

    def _get_bulk_operations(self):
        """Returns list of allowed bulk operations for this panel."""
        return ['add_front', 'add_end', 'remove']

    def _remove_tag_from_data_list(self, tag_data):
        """Remove tag from the favorites list."""
        self.main_window.favorite_tags_ordered.remove(tag_data)

    def _insert_tag_into_data_list(self, tag_data, index):
        """Insert tag into the favorites list at specified index."""
        self.main_window.favorite_tags_ordered.insert(index, tag_data)

    def _handle_post_drop_update(self, tag_name, original_index, new_index):
        """Save favorites after tag order changes."""
        self.main_window.file_operations.save_favorites(self.main_window.favorite_tags_ordered)
        print(f"  favorites.json updated with new tag order.")

    
        
    def _add_context_menu_actions(self, menu, tag_data):
        """Add panel-specific context menu actions for FavoritesPanel.
        No specific actions for this panel yet.
        """
        # For now, we don't have specific actions for favorite tags
        # Could add "Remove from Favorites" option here in the future
        return False  # No actions added

