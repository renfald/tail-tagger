# classifier_panel.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel,
                             QScrollArea, QFrame)
from PySide6.QtCore import Qt

# Import TagWidget - it will be needed for placeholder logic
from tag_widget import TagWidget

class ClassifierPanel(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window

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

        # --- Connect Button Signal (Placeholder Logic) ---
        self.analyze_button.clicked.connect(self._handle_analyze_clicked_placeholder)

        print("ClassifierPanel UI Setup Complete")

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

    def _handle_analyze_clicked_placeholder(self):
        """Placeholder logic for the analyze button click."""
        print("Analyze Button Clicked (Placeholder)")
        self._clear_results_widgets() # Clear previous placeholders
        self.status_label.setText("Displaying placeholders...")

        # --- Get some placeholder tags ---
        # Access the model via main_window
        if not self.main_window or not self.main_window.tag_list_model:
            print("Error: Cannot access TagListModel from MainWindow.")
            self.status_label.setText("Error: Model not found.")
            return

        known_tags = self.main_window.tag_list_model.get_known_tags()
        placeholder_tag_data_list = known_tags[:5] # Get the first 5 known tags

        if not placeholder_tag_data_list:
            self.status_label.setText("No placeholder tags found.")
            return

        # --- Create and add TagWidgets ---
        for tag_data in placeholder_tag_data_list:
            # Check if tag_data is valid
            if tag_data and hasattr(tag_data, 'name'):
                tag_widget = TagWidget(tag_data=tag_data)
                # Classifier suggestions likely won't dim on select, similar to search
                tag_widget.set_styling_mode("dim_on_select") # Or "ignore_select" if preferred
                # Connect signals if needed (e.g., to add tag to selection)
                # tag_widget.tag_clicked.connect(self.main_window._handle_tag_clicked) # Example
                self.results_layout.addWidget(tag_widget)
            else:
                print(f"Warning: Invalid placeholder tag data encountered.")


        self.status_label.setText(f"{len(placeholder_tag_data_list)} placeholders displayed.")
        print(f"Added {len(placeholder_tag_data_list)} placeholder TagWidgets.")