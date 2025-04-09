# left_panel_container.py
from PySide6.QtWidgets import QWidget, QSplitter, QVBoxLayout, QFrame, QTabWidget
from PySide6.QtCore import Qt

from tag_search_panel import TagSearchPanel
from frequently_used_panel import FrequentlyUsedPanel
from favorites_panel import FavoritesPanel
from classifier_panel import ClassifierPanel

class LeftPanelContainer(QWidget):
    def __init__(self, main_window, classifier_manager, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.classifier_manager = classifier_manager
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.splitter = QSplitter(Qt.Vertical)
        self.layout.addWidget(self.splitter)

        # --- Tag Search Panel ---
        self.tag_search_panel = TagSearchPanel(main_window=self.main_window)
        # We want the text input to be focused when the app starts
        self.tag_search_panel.setFocus()
        self.tag_search_panel.search_input.setFocus()


        # --- Tab Widget for Middle Section ---
        self.middle_tab_widget = QTabWidget()

        # --- Frequently Used Panel ---
        self.frequently_used_panel = FrequentlyUsedPanel(main_window=self.main_window)
        self.middle_tab_widget.addTab(self.frequently_used_panel, "Frequent")

        # --- Classifier Suggest Panel ---
        # TODO: rename classifier_suggest_panel to classifier_panel
        self.classifier_suggest_panel = ClassifierPanel(main_window=self.main_window, classifier_manager=self.classifier_manager)
        self.middle_tab_widget.addTab(self.classifier_suggest_panel, "Classifier")  

        # --- Favorites Panel ---
        self.favorites_panel = FavoritesPanel(main_window=self.main_window)

        # --- Add panels directly to the splitter ---
        self.splitter.addWidget(self.tag_search_panel)
        self.splitter.addWidget(self.middle_tab_widget)
        self.splitter.addWidget(self.favorites_panel)

        self.splitter.setChildrenCollapsible(False)
        self.splitter.setSizes([300, 200, 200])
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 0)
        self.splitter.setStretchFactor(2, 1)

        # No need for initial update_display() here - handled by MainWindow's _update_tag_panels

    def update_all_displays(self):
        """Updates all internal panels."""
        self.frequently_used_panel.update_display()
        self.favorites_panel.update_display()
        # Future panels will be updated here as well