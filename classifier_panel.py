# classifier_panel.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                             QScrollArea, QFrame, QMenu, QDoubleSpinBox, QComboBox, QCheckBox)
from PySide6.QtCore import Qt, Slot, QSize, Signal
from PySide6.QtGui import QAction, QIcon

# Import TagWidget - it will be needed for placeholder logic
from tag_widget import TagWidget
from tag_list_model import TagData

class ClassifierPanel(QWidget):
    # Custom signals
    auto_analyze_toggled = Signal(bool)  # Emits True when enabled, False when disabled

    def __init__(self, main_window, classifier_manager, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.classifier_manager = classifier_manager
        self.raw_results: list[tuple[str, float]] | None = None

        print("ClassifierPanel Initialized") # Basic check

        self._setup_ui()

    def _setup_ui(self):
        """Sets up the UI components for the ClassifierPanel."""

        # --- Main Layout ---
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(3)

        # --- Controls Row 1: Analyze Button & Auto-Analyze Toggle ---
        controls_row1_layout = QHBoxLayout()
        controls_row1_layout.setContentsMargins(0,0,0,0)
        controls_row1_layout.setSpacing(5)

        self.analyze_button = QPushButton("Analyze Image")
        controls_row1_layout.addWidget(self.analyze_button)

        self.auto_analyze_toggle_button = QPushButton()
        self.auto_analyze_toggle_button.setIcon(QIcon(":/icons/auto-analyze.svg")) # Path to your icon
        self.auto_analyze_toggle_button.setToolTip("Toggle Auto-Analyze on image load")
        self.auto_analyze_toggle_button.setCheckable(True)
        self.auto_analyze_toggle_button.setChecked(False)
        self.auto_analyze_toggle_button.setFixedSize(30, 30) # Maintain square shape
        self.auto_analyze_toggle_button.setIconSize(QSize(15, 15)) # Adjust icon size within button
        # Style to match exact_match_toggle_button with rounded corners
        self.auto_analyze_toggle_button.setStyleSheet("""
            QPushButton:checked {
                background-color: green;
            }
        """)
        controls_row1_layout.addWidget(self.auto_analyze_toggle_button)

        layout.addLayout(controls_row1_layout)

        # --- Controls Row 2: Model Selector & Threshold ---
        controls_row2_layout = QHBoxLayout()
        controls_row2_layout.setContentsMargins(0,0,0,0)
        controls_row2_layout.setSpacing(5)

        self.model_selector = QComboBox()
        self.model_selector.setToolTip("Select Classifier Model")
        controls_row2_layout.addWidget(self.model_selector, 1)

        self.threshold_spinbox = QDoubleSpinBox()
        self.threshold_spinbox.setRange(0.05, 0.95)
        self.threshold_spinbox.setSingleStep(0.05)
        self.threshold_spinbox.setDecimals(2)

        # --- Set initial threshold from config ---
        initial_threshold = self.main_window.config_manager.get_config_value("classifier_threshold")
        self.threshold_spinbox.setValue(initial_threshold)

        controls_row2_layout.addWidget(self.threshold_spinbox)

        layout.addLayout(controls_row2_layout)

        # --- Status Label ---
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        # --- Scroll Area for Results ---
        self.results_scroll_area = QScrollArea()
        self.results_scroll_area.setWidgetResizable(True)
        self.results_scroll_area.setFrameShape(QFrame.NoFrame) # Optional: remove frame
        self.results_scroll_area.viewport().setStyleSheet("background-color: #191919;")
        layout.addWidget(self.results_scroll_area, 1) # Make scroll area take remaining space

        # --- Container for Tag Widgets (inside scroll area) ---
        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setAlignment(Qt.AlignTop)
        self.results_layout.setSpacing(1)
        self.results_layout.setContentsMargins(1, 1, 1, 1)
        self.results_container.setLayout(self.results_layout)
        self.results_scroll_area.setWidget(self.results_container)

        # --- Connect Button Signals ---
        self.analyze_button.clicked.connect(self._handle_analyze_clicked)
        self.auto_analyze_toggle_button.clicked.connect(self._handle_auto_analyze_toggled)

        # --- Connect ClassifierManager Signals ---
        self.classifier_manager.analysis_started.connect(self._on_analysis_started)
        self.classifier_manager.analysis_finished.connect(self._on_analysis_finished)
        self.classifier_manager.error_occurred.connect(self._on_analysis_error)

        self.threshold_spinbox.valueChanged.connect(self._update_displayed_tags)
        self.threshold_spinbox.valueChanged.connect(self._save_threshold_setting)

        self.model_selector.textActivated.connect(self._handle_model_selection_changed)

        # Populate model selector after all UI elements are created
        self._populate_model_selector()

        print("ClassifierPanel UI Setup Complete and signals connected.")

    def _clear_results_widgets(self):
        """Helper to clear existing widgets from the results layout."""
        for i in reversed(range(self.results_layout.count())):
            widget_item = self.results_layout.itemAt(i)
            if widget_item is not None:
                widget = widget_item.widget()
                if widget is not None:
                    # Important: If widgets have observers (like TagWidget), remove them
                    if hasattr(widget, 'tag_data') and hasattr(widget, '_on_tag_data_changed'):
                         try:
                             # Check if tag_data exists before attempting removal
                             if widget.tag_data:
                                 widget.tag_data.remove_observer(widget._on_tag_data_changed)
                         except Exception as e:
                             print(f"Error removing observer during clear: {e}")
                    widget.deleteLater()

    def _handle_analyze_clicked(self):
        """Handles clicks on the 'Analyze Image' button."""
        print("Analyze Button Clicked - Requesting analysis...")
        current_path = self.main_window.current_image_path
        if current_path and self.classifier_manager:
            # --- Check loading state BEFORE requesting ---
            if self.classifier_manager.is_loading:
                self.status_label.setText("Model is loading, please wait...")
                # Optionally disable button here too, although request_analysis might handle it
                self.analyze_button.setEnabled(False)
                # We could queue the request here in the panel too, but manager handles it now
                print("Analysis request ignored, model load in progress.")
                return # Don't send another request

            # --- Proceed with request ---
            self.analyze_button.setEnabled(False)
            self.status_label.setText("Requesting analysis...")
            # request_analysis will handle the case where loading needs to START
            # and will store the pending path. If already loading, it returns quickly.
            self.classifier_manager.request_analysis(current_path)
            # Status will be updated by signals (started, error, finished)
            # OR if loading starts, the manager should maybe emit error/status?
            # Let's check manager state AGAIN after requesting, just in case loading was triggered
            if self.classifier_manager.is_loading:
                self.status_label.setText("Model is loading, please wait...")
        elif not current_path:
            print("No image loaded to analyze.")
            self.status_label.setText("No image loaded.")
        else:
            print("Classifier Manager not available.")
            self.status_label.setText("Error: Classifier not ready.")
    
    def _update_displayed_tags(self):
        """Filters stored raw results based on current threshold and updates display."""
        if self.raw_results is None:
            # No analysis run yet or results cleared
            # print("Update skipped: No raw results available.")
            self._clear_results_widgets() # Ensure display is clear
            # Reset status if called before analysis? Or assume status is handled elsewhere?
            # Let's only clear here. Status is set elsewhere.
            return

        current_threshold = self.threshold_spinbox.value()
        print(f"Updating display based on threshold: {current_threshold:.2f}")

        self._clear_results_widgets() # Clear previous widgets

        # --- Filter results based on current threshold ---
        filtered_results = [
            (tag_name, score) for tag_name, score in self.raw_results
            if score >= current_threshold
        ]

        # --- Populate results area with filtered results ---
        tag_model = self.main_window.tag_list_model
        widgets_added = 0
        for tag_name, score in filtered_results:
            tag_data = tag_model.tags_by_name.get(tag_name)
            if tag_data is None:
                tag_data = TagData(name=tag_name, is_known=False)
                tag_model.add_tag(tag_data)

            if tag_data:
                tag_widget = TagWidget(tag_data=tag_data)
                tag_widget.setToolTip(f"Confidence: {score:.2%}")
                tag_widget.set_styling_mode("dim_on_select")
                tag_widget.tag_clicked.connect(self.main_window._handle_tag_clicked)
                tag_widget.favorite_star_clicked.connect(self.main_window._handle_favorite_star_clicked)
                tag_widget.tag_right_clicked.connect(self._handle_tag_right_clicked)
                self.results_layout.addWidget(tag_widget)
                widgets_added += 1
            else:
                print(f"Error: Failed to get or create TagData for '{tag_name}'")

        # --- Update status label ---
        if widgets_added > 0:
            self.status_label.setText(f"Displaying {widgets_added} suggestions")
        else:
            if self.raw_results: # Check if analysis actually ran
                self.status_label.setText(f"No suggestions above threshold {current_threshold:.2f}")
            # else: status is likely "Ready" or "Loading", don't overwrite
        print(f"Displayed {widgets_added} widgets.")

    def clear_results(self):
        """Clears the results area and resets the status label."""
        print("ClassifierPanel: Clearing results.")
        self.raw_results = None
        self._clear_results_widgets()
        self.status_label.setText("Ready (New Image)")
        # Only enable analyze button if models are available
        if self.classifier_manager.get_available_models():
            self.analyze_button.setEnabled(True)
        else:
            self.analyze_button.setEnabled(False)
    
    def _populate_model_selector(self):
        """Gets available models from manager and populates the ComboBox."""
        self.model_selector.clear() # Clear existing items first

        available_ids = self.classifier_manager.get_available_models()
        active_id = self.classifier_manager.get_active_model_id()
        active_index = -1 # Initialize active index

        print(f"Populating model selector. Available: {available_ids}, Active: {active_id}")

        if not available_ids:
            self.model_selector.addItem("No Models Found")
            self.model_selector.setEnabled(False)
            # Disable analyze buttons when no models are available
            self.analyze_button.setEnabled(False)
            self.auto_analyze_toggle_button.setEnabled(False)
            self.status_label.setText("No classifier models available")
            return

        for index, model_id in enumerate(available_ids):
            display_name = self.classifier_manager.get_display_name(model_id)
            # Add item with display name (user visible) and internal ID (as data)
            self.model_selector.addItem(display_name, userData=model_id)
            if model_id == active_id:
                active_index = index # Found the index of the active model

        if active_index != -1:
            self.model_selector.setCurrentIndex(active_index)
            print(f"  Set initial selection to index {active_index} ('{self.model_selector.currentText()}')")
        elif available_ids: # If active_id wasn't found but list isn't empty
            print(f"Warning: Active model ID '{active_id}' not found in available list. Setting to first item.")
            self.model_selector.setCurrentIndex(0) # Default to first item

        self.model_selector.setEnabled(True)
        # Enable analyze buttons when models are available
        self.analyze_button.setEnabled(True)
        self.auto_analyze_toggle_button.setEnabled(True)
        self.status_label.setText("Ready")
    
    @Slot()
    def _on_analysis_started(self):
        """Slot called when analysis starts."""
        print("ClassifierPanel received: analysis_started")
        self.status_label.setText("Analyzing image...")
        self._clear_results_widgets()
        self.analyze_button.setEnabled(False)

    @Slot(list)
    def _on_analysis_finished(self, results):
        """Slot called when analysis finishes successfully."""
        # results is expected to be a list of [(tag_name, score), ...] sorted by score
        print(f"ClassifierPanel received: analysis_finished with {len(results)} raw results.")
        self.raw_results = results
        self.analyze_button.setEnabled(True)
        self._update_displayed_tags()


    @Slot(str)
    def _on_analysis_error(self, error_message):
        """Slot called when analysis encounters an error."""
        print(f"ClassifierPanel received: error_occurred: {error_message}")
        # Handle the specific "Model is loading" message - don't show "Error:"
        if "Model is loading" in error_message:
            self.status_label.setText(error_message)
            # Keep button disabled while loading
            self.analyze_button.setEnabled(False)
        elif "Model failed to load" in error_message:
            self.status_label.setText(error_message)
            # Only re-enable if models are available
            if self.classifier_manager.get_available_models():
                self.analyze_button.setEnabled(True)
        else:
            # Genuine analysis error
            self.status_label.setText(f"Analysis Error: {error_message}")
            # Only re-enable if models are available
            if self.classifier_manager.get_available_models():
                self.analyze_button.setEnabled(True)

        # Don't clear results on loading message
        if "Model is loading" not in error_message:
            self._clear_results_widgets()

    @Slot(str) # Receives the tag name emitted by the signal
    def _handle_tag_right_clicked(self, tag_name):
        """Handles right-clicks on TagWidgets in the results area."""
        print(f"Right-click detected on tag: {tag_name}")

        from PySide6.QtGui import QCursor

        # Find the TagData object for the clicked tag
        tag_data = self.main_window.tag_list_model.tags_by_name.get(tag_name)

        if not tag_data:
            print(f"Warning: TagData not found for right-clicked tag '{tag_name}'")
            return

        # Create the context menu
        menu = QMenu(self)
        actions_added = False

        # --- Add "Add to Known Tags" action ONLY for unknown tags ---
        if not tag_data.is_known:
            add_action = QAction("Add to Known Tags", self)
            # Use a lambda to pass the tag name to the main window's method
            add_action.triggered.connect(lambda: self.main_window.add_new_tag_to_model(tag_name))
            menu.addAction(add_action)
            actions_added = True
            print(f"  Added 'Add to Known Tags' action for '{tag_name}'")

        # --- Add bulk operations submenu ---
        # Add separator if previous actions were added
        if actions_added:
            menu.addSeparator()

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

        actions_added = True

        # --- Show the menu ---
        if actions_added:
            menu.popup(QCursor.pos())
        else:
            print(f"  No context actions applicable for tag '{tag_name}'")
    
    @Slot(float) # Use float since spinbox emits float
    def _save_threshold_setting(self, value):
        """Saves the new threshold value to the config file."""
        # print(f"Saving new threshold: {value:.2f}") # Debug
        self.main_window.config_manager.set_config_value("classifier_threshold", value)

    @Slot(str) # Receives the display text of the selected item
    def _handle_model_selection_changed(self, display_name):
        """Handles a change in the selected model from the ComboBox."""
        print(f"Model selector changed. Selected display name: '{display_name}'")

        # Get the internal model ID (stored as userData)
        selected_model_id = self.model_selector.currentData()

        if not selected_model_id or not isinstance(selected_model_id, str):
            print(f"ERROR: Could not retrieve valid model ID for selected item '{display_name}'. Aborting switch.")
            self.status_label.setText("Error: Invalid model selection.")
            # Optionally reset ComboBox selection? Complex, maybe defer.
            return

        print(f"Switching to internal model ID: '{selected_model_id}'")

        # --- Call the ClassifierManager method to perform the switch ---
        self.classifier_manager.set_active_model(selected_model_id)

        # --- Update UI State for the new model ---
        # Clear previous analysis results (they are for the old model)
        self.clear_results() # This also sets status to "Ready (New Image)" and enables button

        # Optionally refine status message
        self.status_label.setText(f"Model '{display_name}' selected. Ready to Analyze.")

        print(f"Model selection switch to '{display_name}' handled.")

    @Slot()
    def _handle_auto_analyze_toggled(self):
        """Handles the toggle of the auto-analyze button."""
        is_enabled = self.auto_analyze_toggle_button.isChecked()
        print(f"Auto-analyze toggle button clicked. New state: {'enabled' if is_enabled else 'disabled'}")

        # Emit signal for MainWindow to connect to
        self.auto_analyze_toggled.emit(is_enabled)