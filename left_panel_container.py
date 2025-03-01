# left_panel_container.py
from PySide6.QtWidgets import QWidget, QSplitter, QVBoxLayout, QFrame, QScrollArea
from PySide6.QtCore import Qt
from all_tags_panel import AllTagsPanel
from tag_search_panel import TagSearchPanel
from favorites_panel import FavoritesPanel

class LeftPanelContainer(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)  # Add margins here
        self.layout.setSpacing(0)  # Add spacing here
        self.splitter = QSplitter(Qt.Vertical)
        self.layout.addWidget(self.splitter)

        # --- Tag Search Panel (Replaces All Tags Panel) ---
        self.tag_search_panel = TagSearchPanel(main_window=self.main_window)
        # We want the text input to be focused when the app starts
        self.tag_search_panel.setFocus()
        self.tag_search_panel.search_input.setFocus()

        # --- Frequently Used Panel (Placeholder with Scroll Area) ---
        self.frequently_used_scroll_area = QScrollArea()
        self.frequently_used_scroll_area.setWidgetResizable(True)
        self.frequently_used_panel = QFrame()  # Placeholder
        frequently_used_layout = QVBoxLayout(self.frequently_used_panel) # Placeholder
        frequently_used_layout.setAlignment(Qt.AlignTop)  # Placeholder
        self.frequently_used_scroll_area.setWidget(self.frequently_used_panel)

        # --- Favorites Panel (Placeholder with Scroll Area) ---
        self.favorites_scroll_area = QScrollArea()
        self.favorites_scroll_area.setWidgetResizable(True)
        self.favorites_panel = FavoritesPanel(main_window=self.main_window)
        favorites_layout = QVBoxLayout(self.favorites_panel)
        favorites_layout.setAlignment(Qt.AlignTop)
        self.favorites_scroll_area.setWidget(self.favorites_panel)

        # --- Add *scroll areas* to the splitter ---
        self.splitter.addWidget(self.tag_search_panel)
        self.splitter.addWidget(self.frequently_used_scroll_area)
        self.splitter.addWidget(self.favorites_scroll_area)

        self.splitter.setChildrenCollapsible(False)
        self.splitter.setSizes([300, 200, 200])
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 0)
        self.splitter.setStretchFactor(2, 1)

        # No need for initial update_display() here - handled by MainWindow's _update_tag_panels

    def update_all_displays(self):
        """Updates all internal panels."""
        # self.all_tags_panel.update_display()
        self.favorites_panel.update_display()
        # Future panels will be updated here as well