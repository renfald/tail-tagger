from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QPushButton, QInputDialog, QSpacerItem, QSizePolicy
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QKeyEvent, QIcon

from tail_tagger.ui.widgets.tag_list_view import TagListView

class TagSearchPanel(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._execute_search)
        self.search_query = ""
        self.highlighted_tag_index = -1 # Initialize highlighted index to -1 (no tag highlighted initially)
        self.search_results = [] # TagData in the results, for keyboard navigation
        self.exact_match_mode = False   # Initialize exact match mode to False (fuzzy search by default)
        self.setup_ui()
        self._display_search_results([])
        self.main_window.tags_changed.connect(self._on_tags_changed)
        # Selection and favorite changes don't need a new search: the results just redraw
        for signal in (self.main_window.selection_changed, self.main_window.favorites_changed, self.main_window.tags_changed):
            signal.connect(self.results_view.repaint_tags)

    def setup_ui(self):
        """
        Sets up the UI components for the TagSearchPanel.
        """
        # Main layout - setting minimal spacing between ui elements (search and results)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        self.setLayout(layout)

        # --- Header Layout (Search Label + Tag Source + Exact Match Toggle) ---
        header_layout = QHBoxLayout() # Horizontal layout for header
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(1) # Add some spacing between label and toggle
        header_container = QWidget() # Container being added so we can set max height and allow buttons to auto size vertically
        header_container.setLayout(header_layout)
        header_container.setMaximumHeight(25)
        layout.addWidget(header_container)
        
        # Search Label
        search_label = QLabel("Search") # Create QLabel for "Search" text
        search_label.setStyleSheet("color: white; font-weight: bold; padding: 3px; background-color: rgb(53,53,53);") # Match TagListPanel title style
        search_label.setAlignment(Qt.AlignLeft)
        header_layout.addWidget(search_label)

        header_spacer = QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum) # Create horizontal spacer
        header_layout.addItem(header_spacer) # Add spacer to header layout

        # Tag Source Toggle Button (E621 / Danbooru)
        self.tag_source_toggle_button = QPushButton()
        self.tag_source_toggle_button.setMinimumWidth(25)
        self.tag_source_toggle_button.setCheckable(True)
        self.tag_source_toggle_button.setChecked(self.main_window.current_tag_source == "booru") # Set based on current source
        self.tag_source_toggle_button.clicked.connect(self._toggle_tag_source)
        header_layout.addWidget(self.tag_source_toggle_button)
        self._update_tag_source_toggle_icon() # Initial icon setup

        # Exact Match Toggle Button
        self.exact_match_toggle_button = QPushButton()
        self.exact_match_toggle_button.setMinimumWidth(25)
        self.exact_match_toggle_button.setCheckable(True)
        self.exact_match_toggle_button.setChecked(False) # Default to Fuzzy Match (not checked)
        self.exact_match_toggle_button.clicked.connect(self._toggle_exact_match_mode) # Connect toggle signal
        self.exact_match_toggle_button.setIconSize(QSize(12, 12))
        self.exact_match_toggle_button.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding) # Fill vertical space
        header_layout.addWidget(self.exact_match_toggle_button) # Add toggle button to header layout
        self._update_exact_match_toggle_icon() # Initial icon and tooltip setup (call helper method below)
        
        # --- Search Input Area (Horizontal Layout for Input + Icon) ---
        search_input_layout = QHBoxLayout()
        search_input_layout.setContentsMargins(0, 0, 0, 0)
        search_input_layout.setSpacing(1)
        layout.addLayout(search_input_layout) # Add horizontal layout to main vertical layout

        # Search Input Field
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Type Tag Here...")
        self.search_input.setStyleSheet("background-color: #2B2B2B;color: white;")
        self.search_input.textChanged.connect(self._on_search_text_changed)
        search_input_layout.addWidget(self.search_input) # Add search input to horizontal layout


        # --- Add New Tag Icon Button ---
        self.add_new_tag_icon_button = QPushButton()
        self.add_new_tag_icon_button.setIcon(QIcon(":/icons/add-tag.svg"))
        self.add_new_tag_icon_button.setToolTip("Add New Tag")
        self.add_new_tag_icon_button.clicked.connect(self._handle_add_new_tag_icon_clicked)
        search_input_layout.addWidget(self.add_new_tag_icon_button)
        self.add_new_tag_icon_button.setStyleSheet("QPushButton { border: none; padding: 0px; margin: 0px; } QPushButton:hover { background-color: #2B2B2B; }")

        # Tag Results Display Area: the result list, or the add-tag button when nothing matches
        self.results_area = QWidget()
        self.results_area.setObjectName("results_area")
        self.results_area.setAttribute(Qt.WA_StyledBackground, True)
        self.results_area.setStyleSheet("#results_area { background-color: #191919; }")
        self.results_area_layout = QVBoxLayout(self.results_area) # Layout for results area
        self.results_area_layout.setSpacing(1)
        self.results_area_layout.setContentsMargins(0, 0, 0, 0)

        self.results_view = TagListView(dim_on_select=True, reorderable=False)
        self.results_view.tag_clicked.connect(self.main_window.toggle_tag)
        self.results_view.favorite_clicked.connect(self.main_window.toggle_favorite)
        self.results_view.tag_right_clicked.connect(self._handle_tag_right_clicked)
        self.results_area_layout.addWidget(self.results_view, 1)

        self.add_new_tag_button = QPushButton()
        self.add_new_tag_button.clicked.connect(self._handle_add_new_tag_button_clicked)
        self.results_area_layout.addWidget(self.add_new_tag_button)
        self.no_results_label = QLabel("No tags found.")
        self.results_area_layout.addWidget(self.no_results_label)
        # Takes the space when the list is hidden, so the add-tag button stays at the top
        self.results_area_layout.addStretch(0)
        layout.addWidget(self.results_area)

    def _toggle_exact_match_mode(self):
        """Toggles the exact match mode and updates the toggle icon and tooltip."""
        self.exact_match_mode = not self.exact_match_mode # Toggle the boolean state
        self._update_exact_match_toggle_icon() # Update the button's icon and tooltip based on mode
        self._execute_search() # Re-execute search with new mode

    def _update_exact_match_toggle_icon(self):
        """Updates the exact match toggle icon and tooltip based on the current mode."""
        if self.exact_match_mode:
            self.exact_match_toggle_button.setIcon(QIcon(":/icons/equal.svg")) # Set icon for Exact Match mode
            self.exact_match_toggle_button.setToolTip("Exact Match (Toggle to Fuzzy Match)") # Tooltip for Exact Match
        else:
            self.exact_match_toggle_button.setIcon(QIcon(":/icons/approx.svg")) # Set icon for Fuzzy Match mode
            self.exact_match_toggle_button.setToolTip("Fuzzy Match (Default) (Toggle to Exact Match)") # Tooltip for Fuzzy Match

    def _toggle_tag_source(self):
        """Toggles between e621 and danbooru tag sources and updates the button icon."""
        new_source = "booru" if self.main_window.current_tag_source == "e621" else "e621"
        self.main_window.switch_tag_source(new_source)
        self._update_tag_source_toggle_icon()

    def _update_tag_source_toggle_icon(self):
        """Updates the tag source toggle button icon and tooltip based on the current source."""
        if self.main_window.current_tag_source == "e621":
            self.tag_source_toggle_button.setIcon(QIcon(":/icons/e621.svg"))
            self.tag_source_toggle_button.setToolTip("Currently using e621 tags (Click to switch to Danbooru)")
            self.tag_source_toggle_button.setChecked(False)
        else:
            self.tag_source_toggle_button.setIcon(QIcon(":/icons/booru.svg"))
            self.tag_source_toggle_button.setToolTip("Currently using Danbooru tags (Click to switch to e621)")
            self.tag_source_toggle_button.setChecked(True)
    
    def _display_search_results(self, tag_data_list):
        """
        Shows the provided list of TagData objects as the results.
        Displays "Add New Tag" button if no results are found.
        """
        self.search_results = list(tag_data_list)
        # A note after the results when we've hit the result limit (hardcoded to 50 for now)
        # This value should match MAX_SEARCH_RESULTS in tag_list_model.py
        footer = None
        if len(self.search_results) >= 50 and self.search_query:
            footer = "Showing top 50 results. Refine your search for more specific matches."
        self.results_view.set_tags(self.search_results, footer=footer)

        has_results = bool(self.search_results)
        no_match = not has_results and bool(self.search_query)
        self.results_view.setVisible(has_results or not self.search_query)
        self.add_new_tag_button.setText(f"Add New Tag: '{self.search_query}'")
        self.add_new_tag_button.setVisible(no_match)
        self.no_results_label.setVisible(no_match)

        self.highlighted_tag_index = 0 if has_results else -1
        self._update_tag_highlight()

    def _on_tags_changed(self):
        """
        Re-runs the current search when the tag catalog changes (new tag, promotion, source switch).
        Uses the debounce timer so it batches with any pending text change.
        """
        self.search_timer.start(50)  # Shorter delay than for typing

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
            filtered_tags = self.main_window.tag_list_model.search_tags(query_text, self.exact_match_mode) # Perform search
            self._display_search_results(filtered_tags) # Update UI with search results

        if self.search_results: # Check if there are results to highlight
            self.highlighted_tag_index = 0 # Highlight the first tag (index 0)
            self._update_tag_highlight() # Update the visual highlight
        else:
            self.highlighted_tag_index = -1 # No results, reset highlight index
            self._update_tag_highlight() # Ensure no tag is highlighted

    def keyPressEvent(self, event: QKeyEvent):
        """Handles key press events for keyboard navigation and delegates to KeyboardManager."""
        if not self.search_results: # Keep existing check - Do nothing if no search results
            pass # Keep existing - do nothing if no search results
        elif event.key() == Qt.Key_Down or event.key() == Qt.Key_Up or event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter: # Keep existing panel-specific navigation
            # --- Panel-specific navigation logic (Up/Down/Enter) ---
            if event.key() == Qt.Key_Down:
                self.highlighted_tag_index = min(self.highlighted_tag_index + 1, len(self.search_results) - 1)
                self._update_tag_highlight()
                event.accept() # Accept the event
                return
            elif event.key() == Qt.Key_Up:
                self.highlighted_tag_index = max(self.highlighted_tag_index - 1, 0)
                self._update_tag_highlight()
                event.accept() # Accept the event
                return
            elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter: # Handle Enter key press
                if 0 <= self.highlighted_tag_index < len(self.search_results):
                    highlighted_tag = self.search_results[self.highlighted_tag_index]
                    self.main_window.toggle_tag(highlighted_tag.name) # Select the highlighted tag
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
        self.results_view.set_highlighted_row(self.highlighted_tag_index)

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
        
    def _handle_tag_right_clicked(self, tag_name):
        """Handles right-click events on tags in search results.
        Creates and displays a context menu with bulk operations.
        """
        print(f"Right-clicked tag in search: {tag_name}")

        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QCursor, QAction

        # Find tag data for the clicked tag
        tag_data = None
        for td in self.main_window.tag_list_model.tags:
            if td.name == tag_name:
                tag_data = td
                break

        if not tag_data:
            print(f"Warning: Tag data not found for right-clicked tag '{tag_name}'")
            return

        # Create context menu
        menu = QMenu(self)

        # Add bulk operations submenu
        bulk_menu = menu.addMenu("Bulk Operations")

        add_front_action = QAction("Add to All Images (Beginning)", self)
        add_front_action.triggered.connect(lambda: self.main_window.execute_bulk_operation('add_front', tag_name))
        bulk_menu.addAction(add_front_action)

        add_end_action = QAction("Add to All Images (End)", self)
        add_end_action.triggered.connect(lambda: self.main_window.execute_bulk_operation('add_end', tag_name))
        bulk_menu.addAction(add_end_action)

        bulk_menu.addSeparator()

        remove_action = QAction("Remove from All Images", self)
        remove_action.triggered.connect(lambda: self.main_window.execute_bulk_operation('remove', tag_name))
        bulk_menu.addAction(remove_action)

        bulk_menu.addSeparator()

        replace_action = QAction("Replace in All Images...", self)
        replace_action.triggered.connect(lambda: self.main_window.start_replace_tag_operation(tag_name))
        bulk_menu.addAction(replace_action)

        # Show menu
        menu.popup(QCursor.pos())