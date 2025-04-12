# classifier_panel.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel,
                             QScrollArea, QFrame)
from PySide6.QtCore import Qt, Slot

# Import TagWidget - it will be needed for placeholder logic
from tag_widget import TagWidget
from tag_list_model import TagData

class ClassifierPanel(QWidget):
    def __init__(self, main_window, classifier_manager, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.classifier_manager = classifier_manager

        print("ClassifierPanel Initialized") # Basic check

        self._setup_ui()

    def _setup_ui(self):
        # --- Main Layout ---
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2) # Small margins
        layout.setSpacing(3) # Small spacing

        # --- Analyze Button (Top) ---
        self.analyze_button = QPushButton("Analyze Image")
        layout.addWidget(self.analyze_button)

        # --- Status Label ---
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignCenter)
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

        # --- Connect Button Signal ---
        self.analyze_button.clicked.connect(self._handle_analyze_clicked)

        # --- Connect ClassifierManager Signals ---
        self.classifier_manager.analysis_started.connect(self._on_analysis_started)
        self.classifier_manager.analysis_finished.connect(self._on_analysis_finished)
        self.classifier_manager.error_occurred.connect(self._on_analysis_error)

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
    
    def clear_results(self):
        """Clears the results area and resets the status label."""
        print("ClassifierPanel: Clearing results.")
        self._clear_results_widgets()
        self.status_label.setText("Ready (New Image)") # Or simply "Ready"
        # Ensure button is enabled when results are cleared due to image change
        self.analyze_button.setEnabled(True)
    
    
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
        print(f"ClassifierPanel received: analysis_finished with {len(results)} results.")
        self._clear_results_widgets() # Clear again just in case

        if not results:
            self.status_label.setText("Analysis complete: No tags found above threshold.")
            self.analyze_button.setEnabled(True) # Re-enable button
            return

        # --- Populate results area ---
        tag_model = self.main_window.tag_list_model
        for tag_name, score in results:
            tag_data = None
            # Check efficiently if tag exists (known or unknown)
            tag_data = tag_model.tags_by_name.get(tag_name)

            if tag_data is None:
                # Tag doesn't exist in the model at all, add as unknown
                print(f"Suggested tag '{tag_name}' not found in model. Adding as unknown.")
                # Important: Ensure TagData init handles default values appropriately if needed
                tag_data = TagData(name=tag_name, is_known=False)
                tag_model.add_tag(tag_data) # Add to the central model

            # Create and add the TagWidget
            if tag_data: # Double check tag_data is valid before creating widget
                tag_widget = TagWidget(tag_data=tag_data)
                # Optional: Display score? Maybe later. Add tooltip?
                tag_widget.setToolTip(f"Confidence: {score:.2%}")
                tag_widget.set_styling_mode("dim_on_select") # Match search panel styling
                tag_widget.tag_clicked.connect(self.main_window._handle_tag_clicked)
                tag_widget.favorite_star_clicked.connect(self.main_window._handle_favorite_star_clicked)
                self.results_layout.addWidget(tag_widget)
            else:
                print(f"Error: Failed to get or create TagData for '{tag_name}'")


        self.status_label.setText(f"Analysis complete: {len(results)} suggestions found.")
        self.analyze_button.setEnabled(True) # Re-enable button

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
            self.analyze_button.setEnabled(True) # Re-enable button on load failure
        else:
            # Genuine analysis error
            self.status_label.setText(f"Analysis Error: {error_message}")
            self.analyze_button.setEnabled(True) # Re-enable button on analysis error

        # Don't clear results on loading message
        if "Model is loading" not in error_message:
            self._clear_results_widgets()