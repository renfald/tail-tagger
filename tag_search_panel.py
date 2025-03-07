from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QScrollArea, QPushButton, QInputDialog, QMessageBox
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeyEvent, QIcon

from tag_widget import TagWidget
from file_operations import FileOperations
from tag_list_model import TagData

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
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        # --- Search Input Area (Horizontal Layout for Input + Icon) ---
        search_input_layout = QHBoxLayout()
        search_input_layout.setContentsMargins(0, 0, 0, 0)
        search_input_layout.setSpacing(0)
        layout.addLayout(search_input_layout) # Add horizontal layout to main vertical layout

        # Search Input Field
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search Tags...")
        self.search_input.setStyleSheet("background-color: #2B2B2B;color: white;")
        self.search_input.textChanged.connect(self._on_search_text_changed)
        search_input_layout.addWidget(self.search_input) # Add search input to horizontal layout


        # --- Add New Tag Icon Button ---
        self.add_new_tag_icon_button = QPushButton()
        self.add_new_tag_icon_button.setIcon(QIcon(":/icons/add-tag.svg"))
        self.add_new_tag_icon_button.setToolTip("Add New Tag")
        self.add_new_tag_icon_button.clicked.connect(self._handle_add_new_tag_icon_clicked)
        search_input_layout.addWidget(self.add_new_tag_icon_button)
        self.add_new_tag_icon_button.setStyleSheet("QPushButton { background-color: #2B2B2B; border: none; padding: 0px; margin: 0px; } QPushButton:hover { background-color: #353535; }")

        # Tag Results Display Area (in Scroll Area)
        self.results_scroll_area = QScrollArea()
        self.results_scroll_area.setWidgetResizable(True)
        self.results_scroll_area.viewport().setStyleSheet("background-color: #242424;") # Scroll area

        self.results_area = QWidget()
        self.results_area_layout = QVBoxLayout(self.results_area) # Layout for results area
        self.results_area_layout.setAlignment(Qt.AlignTop)
        self.results_area_layout.setSpacing(1)
        self.results_area_layout.setContentsMargins(1, 1, 1, 1)
        self.results_area.setLayout(self.results_area_layout)
        self.results_scroll_area.setWidget(self.results_area)
        layout.addWidget(self.results_scroll_area)

    def _display_search_results(self, tag_data_list):
        """
        Clears the current results and displays the provided list of TagData objects as TagWidgets.
        Displays "Add New Tag" button if no results are found.
        """
        # Clear existing widgets in the results area
        for i in reversed(range(self.results_area_layout.count())):
            widget = self.results_area_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        self.search_results_tag_widgets = []
        self.highlighted_tag_index = -1

        if not tag_data_list: # Check if tag_data_list is empty (no results)
            if self.search_query: # Check if search_query is NOT empty
                add_new_tag_button = QPushButton(f"Add New Tag: '{self.search_query}'") # Create button
                add_new_tag_button.clicked.connect(self._handle_add_new_tag_button_clicked) # Connect signal
                self.results_area_layout.addWidget(add_new_tag_button) # Add button to layout
                no_results_label = QLabel("No tags found.") # Keep "No tags found" message
                self.results_area_layout.addWidget(no_results_label)

        else: # If there are search results (tag_data_list is not empty)
            # Display new TagWidgets from the provided list (Existing code - no change here)
            for tag_data in tag_data_list:
                tag_widget = TagWidget(tag_data=tag_data)
                tag_widget.set_styling_mode("dim_on_select")
                tag_widget.tag_clicked.connect(self.main_window._handle_tag_clicked)
                tag_widget.favorite_star_clicked.connect(self.main_window._handle_favorite_star_clicked)
                self.results_area_layout.addWidget(tag_widget)
                self.search_results_tag_widgets.append(tag_widget)

        if self.search_results_tag_widgets:
            self.highlighted_tag_index = 0
            self._update_tag_highlight()
        else:
            self.highlighted_tag_index = -1
            self._update_tag_highlight()

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
        """Handles key press events for keyboard navigation and delegates to KeyboardManager."""
        if not self.search_results_tag_widgets: # Keep existing check - Do nothing if no search results
            pass # Keep existing - do nothing if no search results
        elif event.key() == Qt.Key_Down or event.key() == Qt.Key_Up or event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter: # Keep existing panel-specific navigation
            # --- Panel-specific navigation logic (Up/Down/Enter) ---
            if event.key() == Qt.Key_Down:
                self.highlighted_tag_index = min(self.highlighted_tag_index + 1, len(self.search_results_tag_widgets) - 1)
                self._update_tag_highlight()
                event.accept() # Accept the event
                return
            elif event.key() == Qt.Key_Up:
                self.highlighted_tag_index = max(self.highlighted_tag_index - 1, 0)
                self._update_tag_highlight()
                event.accept() # Accept the event
                return
            elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter: # Handle Enter key press
                if 0 <= self.highlighted_tag_index < len(self.search_results_tag_widgets):
                    highlighted_tag_widget = self.search_results_tag_widgets[self.highlighted_tag_index]
                    self.main_window._handle_tag_clicked(highlighted_tag_widget.tag_name) # Select the highlighted tag
                    self.search_input.clear() # Clear search input after selection - for next phase
                    self._execute_search() # Refresh results to be empty - for next phase
                event.accept() # Accept the event
                return
        # --- Delegate to KeyboardManager for unhandled events ---
        if not self.main_window.keyboard_manager.handle_key_press(event, self):
            super().keyPressEvent(event) # Pass event to parent for default handling
        # --- End Delegation ---

    def _update_tag_highlight(self):
        """Updates the visual highlight of the currently highlighted tag."""
        for index, tag_widget in enumerate(self.search_results_tag_widgets):
            if index == self.highlighted_tag_index:
                tag_widget.setStyleSheet("border: 2px solid grey;") # Highlight style
            else:
                tag_widget.setStyleSheet("") # Reset to default style

    def _handle_add_new_tag_button_clicked(self):
        """Handles clicks on the "Add New Tag" button (no search results)."""
        tag_name = self.search_query # Get tag name from the search query
        self._add_new_tag(tag_name) # Call helper method to add the tag

    def _handle_add_new_tag_icon_clicked(self):
        """Handles clicks on the "+" icon "Add New Tag" button.
        Prefills the dialog with the current search text.
        """
        current_search_text = self.search_input.text() # Get current text from search input
        text, ok = QInputDialog.getText(
            self,
            "Add New Tag",
            "Enter New Tag Name:",
            QLineEdit.Normal,
            current_search_text
        )
        if ok and text: # If user clicked OK and entered text
            tag_name = text.strip() # Get tag name from input dialog, stripping whitespace
            if tag_name:
                self._add_new_tag(tag_name)

    def _add_new_tag(self, tag_name):
        """
        Helper method to add a new tag to the application, or promote an existing tag.
        Calls MainWindow.add_new_tag_to_model() to handle tag addition.
        """
        self.main_window.add_new_tag_to_model(tag_name)