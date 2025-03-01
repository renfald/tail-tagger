from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QLabel, QScrollArea
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeyEvent
from tag_widget import TagWidget


class TagSearchPanel(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._execute_search)
        self.search_query = ""
        self.highlighted_tag_index = -1 # Initialize highlighted index to -1 (no tag highlighted initially)
        self.search_results_tag_widgets = [] # Store TagWidgets in search results for navigation
        self.setup_ui()
        self._display_search_results([])
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
        self.search_input.textChanged.connect(self._on_search_text_changed)
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
    
        self.search_results_tag_widgets = [] # Reset tag widget list
        self.highlighted_tag_index = -1 # Reset highlighted index


        # Display new TagWidgets from the provided list
        for tag_data in tag_data_list:
            tag_widget = TagWidget(tag_data=tag_data) # Create TagWidget instance
            tag_widget.set_styling_mode("dim_on_select")
            tag_widget.tag_clicked.connect(self.main_window._handle_tag_clicked) # Connect tag_clicked signal
            tag_widget.favorite_star_clicked.connect(self.main_window._handle_favorite_star_clicked)
            self.results_area_layout.addWidget(tag_widget) # Add TagWidget to layout
            self.search_results_tag_widgets.append(tag_widget) # Store TagWidget in list

    def _on_tags_changed(self):
        """
        Handles updates when the tag selection state changes.
        """
        self._execute_search()

    def _on_search_text_changed(self, text):
        """
        Handles changes in the search input text.
        Implements debounce to delay the search execution.
        """
        self.search_query = text # Store the search query
        self.search_timer.start(250) # Start debounce timer with 250ms delay

    def _execute_search(self):
        """
        Executes the tag search and updates the display.
        Handles empty search query case.
        This method is called by the debounce timer.
        """
        query_text = self.search_query # Retrieve stored search query
        if not query_text: # Check if search query is empty
            self._display_search_results([]) # Display empty results area if query is empty
        else:
            filtered_tags = self.main_window.tag_list_model.search_tags(query_text) # Perform search
            self._display_search_results(filtered_tags) # Update UI with search results

        if self.search_results_tag_widgets: # Check if there are results to highlight
            self.highlighted_tag_index = 0 # Highlight the first tag (index 0)
            self._update_tag_highlight() # Update the visual highlight
        else:
            self.highlighted_tag_index = -1 # No results, reset highlight index
            self._update_tag_highlight() # Ensure no tag is highlighted

    def keyPressEvent(self, event: QKeyEvent):
        """Handles key press events for keyboard navigation."""
        if not self.search_results_tag_widgets: # Do nothing if no search results
            return

        if event.key() == Qt.Key_Down:
            self.highlighted_tag_index = min(self.highlighted_tag_index + 1, len(self.search_results_tag_widgets) - 1)
            self._update_tag_highlight()
            event.accept() # Accept the event
        elif event.key() == Qt.Key_Up:
            self.highlighted_tag_index = max(self.highlighted_tag_index - 1, 0)
            self._update_tag_highlight()
            event.accept() # Accept the event
        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter: # Handle Enter key press
            if 0 <= self.highlighted_tag_index < len(self.search_results_tag_widgets):
                highlighted_tag_widget = self.search_results_tag_widgets[self.highlighted_tag_index]
                self.main_window._handle_tag_clicked(highlighted_tag_widget.tag_name) # Select the highlighted tag
                self.search_input.clear() # Clear search input after selection - for next phase
                self._execute_search() # Refresh results to be empty - for next phase
            event.accept() # Accept the event
        else:
            super().keyPressEvent(event) # Pass event to parent for default handling

    def _update_tag_highlight(self):
        """Updates the visual highlight of the currently highlighted tag."""
        for index, tag_widget in enumerate(self.search_results_tag_widgets):
            if index == self.highlighted_tag_index:
                tag_widget.setStyleSheet("border: 2px solid grey;") # Highlight style
            else:
                tag_widget.setStyleSheet("") # Reset to default style