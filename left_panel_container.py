# left_panel_container.py
from PySide6.QtWidgets import QWidget, QSplitter, QVBoxLayout, QFrame, QScrollArea
from PySide6.QtCore import Qt
from all_tags_panel import AllTagsPanel

class LeftPanelContainer(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)  # Add margins here
        self.layout.setSpacing(0)  # Add spacing here
        self.splitter = QSplitter(Qt.Vertical)
        self.layout.addWidget(self.splitter)

        # --- All Tags Panel with Scroll Area ---
        self.all_tags_scroll_area = QScrollArea()
        self.all_tags_scroll_area.setWidgetResizable(True)
        self.all_tags_panel = AllTagsPanel(main_window=self.main_window, tag_list_model=self.main_window.tag_list_model)
        self.all_tags_scroll_area.setWidget(self.all_tags_panel)

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
        self.favorites_panel = QFrame()  # Placeholder
        favorites_layout = QVBoxLayout(self.favorites_panel)
        favorites_layout.setAlignment(Qt.AlignTop)
        self.favorites_scroll_area.setWidget(self.favorites_panel)

        # --- Add *scroll areas* to the splitter ---
        self.splitter.addWidget(self.all_tags_scroll_area)
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
        self.all_tags_panel.update_display()
        # Future panels will be updated here as well