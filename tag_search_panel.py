from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QLabel, QScrollArea
from PySide6.QtCore import Qt
from tag_widget import TagWidget

class TagSearchPanel(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setup_ui()
        initial_tag_list = self.main_window.tag_list_model.search_tags("") # Get all known tags via stubbed search
        self._display_search_results(initial_tag_list) # Display the tags in the panel
        self.main_window.tag_list_model.tags_selected_changed.connect(self._on_tags_changed)

    def setup_ui(self):
        """
        Sets up the UI components for the TagSearchPanel.
        """
        # Main layout - setting minimal spacing between ui elements (search and results)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        layout.setSpacing(0)
        self.setLayout(layout)

        # Search Input Field
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search Tags...") # Placeholder text
        self.search_input.setStyleSheet("background-color: #2B2B2B;color: white;")
        layout.addWidget(self.search_input)

        # Tag Results Display Area (in Scroll Area)
        self.results_scroll_area = QScrollArea()
        self.results_scroll_area.setWidgetResizable(True)
        self.results_scroll_area.viewport().setStyleSheet("background-color: #242424;") # Scroll area
        
        self.results_area = QWidget()
        self.results_area_layout = QVBoxLayout(self.results_area) # Layout for results area
        self.results_area_layout.setAlignment(Qt.AlignTop) # Align tags to top
        self.results_area_layout.setSpacing(1)
        self.results_area_layout.setContentsMargins(1, 1, 1, 1)
        self.results_area.setLayout(self.results_area_layout)
        self.results_scroll_area.setWidget(self.results_area) # Add results_area TO Scroll Area
        layout.addWidget(self.results_scroll_area) # Add Scroll Area TO Main Layout

    def _display_search_results(self, tag_data_list):
        """
        Clears the current results and displays the provided list of TagData objects as TagWidgets.
        """
        # Clear existing widgets in the results area
        for i in reversed(range(self.results_area_layout.count())):
            widget = self.results_area_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        # Display new TagWidgets from the provided list
        for tag_data in tag_data_list:
            tag_widget = TagWidget(tag_data=tag_data) # Create TagWidget instance
            tag_widget.set_styling_mode("dim_on_select")
            tag_widget.tag_clicked.connect(self.main_window._handle_tag_clicked) # Connect tag_clicked signal
            tag_widget.favorite_star_clicked.connect(self.main_window._handle_favorite_star_clicked)
            self.results_area_layout.addWidget(tag_widget) # Add TagWidget to layout

    def _on_tags_changed(self):
        """
        Handles updates when the tag selection state changes.
        Re-renders the tag display using the stubbed search.
        """
        updated_tag_list = self.main_window.tag_list_model.search_tags("")  # Get all known tags (stubbed search)
        self._display_search_results(updated_tag_list)  # Re-display the tags