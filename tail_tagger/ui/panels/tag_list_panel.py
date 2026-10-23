from abc import ABC, abstractmethod
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QKeyEvent
from tail_tagger.ui.widgets.tag_list_view import TagListView

class TagListPanel(QWidget, ABC, metaclass=type('ABCMetaQWidget', (type(QWidget), type(ABC)), {})):  # Explicit metaclass
    """Abstract base class for tag list panels."""

    reorderable = False  # Whether tags can be dragged to a new position in this panel

    def __init__(self, main_window=None, panel_title=""):
        super().__init__(main_window)
        self.main_window = main_window
        # self.setStyleSheet("background-color: #242424;") # This sets a dark grey background for the panel
        
        # Main layout for the panel
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create panel title label (fixed at top)
        self.title_label = QLabel(panel_title)
        self.title_label.setStyleSheet("color: white; font-weight: bold; padding: 3px; background-color: rgb(53,53,53); margin: 0px;")
        # self.title_label.setStyleSheet("color: white; font-weight: bold; padding: 3px; background-color: rgb(53,53,53); border-top: 2px solid #242424; margin: 0px;") # potentiall alternate. provides a spacer for the splitters but looks bad in selected tags panel
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.main_layout.addWidget(self.title_label, 0, Qt.AlignTop)
        
        # The tags, drawn by the shared list view
        self.view = TagListView(dim_on_select=self.get_styling_mode() == "dim_on_select", reorderable=self.reorderable)
        self.main_layout.addWidget(self.view, 1) # Make the list take remaining space
        self.view.tag_clicked.connect(self.main_window.toggle_tag)
        self.view.favorite_clicked.connect(self.main_window.toggle_favorite)
        self.view.tag_right_clicked.connect(self._handle_tag_right_clicked)
        self.view.tag_moved.connect(self._move_tag)
        # Rows are drawn from their TagData, so any change to selection, favorites or tags only needs a redraw
        for signal in (main_window.selection_changed, main_window.favorites_changed, main_window.tags_changed):
            signal.connect(self.view.repaint_tags)

    @abstractmethod
    def _get_tag_data_list(self):
        """Abstract method: Subclasses must implement to return the list of TagData objects."""
        pass

    @abstractmethod
    def get_styling_mode(self):
        """Abstract method: Subclasses must implement to return their styling mode."""
        pass

    def update_display(self):
        """Shows the panel's current tags."""
        self.view.set_tags(self._get_tag_data_list())

    def keyPressEvent(self, event: QKeyEvent):
        """Overrides keyPressEvent to handle keyboard shortcuts."""
        # Delegate event handling to KeyboardManager
        if not self.main_window.keyboard_manager.handle_key_press(event, self):
            # If event was not handled by KeyboardManager, pass it to the parent
            super().keyPressEvent(event)

    def _move_tag(self, tag_name, new_index):
        """Moves a dropped tag to new_index (its final position in this panel's list).
        Panels with reorderable = True override this; the others never receive a drop."""
        pass


    @abstractmethod
    def _get_bulk_operations(self):
        """Abstract method: Returns a list of allowed bulk operations for this panel.

        Returns:
            list: List of operation strings. Valid operations:
                  'add_front', 'add_end', 'remove'
                  Return empty list to disable bulk operations for this panel.
        """
        return []

    @Slot(str)
    def _handle_tag_right_clicked(self, tag_name):
        """Handles right-click events on tags. Creates and displays a context menu with panel-specific actions."""
        print(f"Right-clicked tag: {tag_name}")
        
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QCursor, QAction
        
        # Find tag data for the clicked tag
        tag_data = None
        for td in self._get_tag_data_list():
            if td.name == tag_name:
                tag_data = td
                break
        
        if not tag_data:
            print(f"Warning: Tag data not found for right-clicked tag '{tag_name}'")
            return
            
        # Create context menu
        menu = QMenu(self)

        # Add panel-specific actions to menu
        actions_added = self._add_context_menu_actions(menu, tag_data)

        # Add bulk operations submenu if this panel supports them
        bulk_ops = self._get_bulk_operations()
        if bulk_ops:
            # Add separator if panel-specific actions were added
            if actions_added:
                menu.addSeparator()

            # Create bulk operations submenu
            bulk_menu = menu.addMenu("Bulk Operations")

            if 'add_front' in bulk_ops:
                add_front_action = QAction(f"Add to All Images (Beginning)", self)
                add_front_action.triggered.connect(lambda: self.main_window.execute_bulk_operation('add_front', tag_name))
                bulk_menu.addAction(add_front_action)

            if 'add_end' in bulk_ops:
                add_end_action = QAction(f"Add to All Images (End)", self)
                add_end_action.triggered.connect(lambda: self.main_window.execute_bulk_operation('add_end', tag_name))
                bulk_menu.addAction(add_end_action)

            if 'remove' in bulk_ops:
                # Add separator between add and remove if both exist
                if ('add_front' in bulk_ops or 'add_end' in bulk_ops):
                    bulk_menu.addSeparator()

                remove_action = QAction(f"Remove from All Images", self)
                remove_action.triggered.connect(lambda: self.main_window.execute_bulk_operation('remove', tag_name))
                bulk_menu.addAction(remove_action)

            if 'replace' in bulk_ops:
                bulk_menu.addSeparator()

                replace_action = QAction("Replace in All Images...", self)
                replace_action.triggered.connect(lambda: self.main_window.start_replace_tag_operation(tag_name))
                bulk_menu.addAction(replace_action)

            actions_added = True  # Bulk operations count as actions

        # Only show menu if actions were added
        if actions_added:
            menu.popup(QCursor.pos())
            
    @abstractmethod
    def _add_context_menu_actions(self, menu, tag_data):
        """Abstract method: Add panel-specific context menu actions.
        Args:
            menu (QMenu): The menu to add actions to
            tag_data (TagData): The TagData object for the right-clicked tag
            
        Returns:
            bool: True if any actions were added, False otherwise
        """
        return False
