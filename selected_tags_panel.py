from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget, QApplication
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import QSize
from tag_list_panel import TagListPanel
from file_operations import FileOperations

class SelectedTagsPanel(TagListPanel):
    def __init__(self, main_window, parent=None):
        super().__init__(main_window, panel_title="Selected Tags")
        self.setAcceptDrops(True)  # This panel accepts drops

        # --- Button Section (below title, above tags area) ---
        # Create a container widget for the button row
        button_row_widget = QWidget()
        button_row_layout = QHBoxLayout(button_row_widget)
        button_row_layout.setContentsMargins(5, 2, 5, 2)
        button_row_layout.setSpacing(5)

        # Add stretch to push button to the right
        button_row_layout.addStretch()

        # Copy Tags button (aligned to right)
        self.copy_tags_button = QPushButton()
        self.copy_tags_button.setIcon(QIcon(":/icons/copy-Tags.svg"))
        self.copy_tags_button.setToolTip("Copy Tags to Clipboard")
        self.copy_tags_button.setFixedSize(28, 30)
        self.copy_tags_button.setIconSize(QSize(20, 24))
        button_row_layout.addWidget(self.copy_tags_button)

        # Insert button row into main layout (between title and scroll area)
        # Index 1 is right after the title_label, pushing scroll_area down
        # TODO: This feels like an oversight in the base class design. Tag Panels do not natively support adding widgets 
        # between title and scroll area. Consider refactoring base class to allow more flexible layouts.
        self.main_layout.insertWidget(1, button_row_widget, 0)  # 0 stretch factor

        # Connect button signal
        self.copy_tags_button.clicked.connect(self._handle_copy_tags_clicked)

    def _handle_copy_tags_clicked(self):
        """Copies all selected tags for current image to clipboard."""
        # Get the selected tags list from main window
        selected_tags = self.main_window.selected_tags_for_current_image

        # Convert tag names from underscores to spaces
        spaced_tags = [
            FileOperations.convert_underscores_to_spaces(tag.name)
            for tag in selected_tags
        ]

        # Join with comma-space separator (matches export format)
        tags_string = ", ".join(spaced_tags)

        # Copy to clipboard (will be empty string if no tags)
        clipboard = QApplication.clipboard()
        clipboard.setText(tags_string)

        print(f"Copied {len(spaced_tags)} tags to clipboard")

    def get_styling_mode(self):
        return "ignore_select"  # Right panel ignores selection for styling

    def _get_tag_data_list(self):
        """Returns the list of TagData objects for this panel (Selected Tags)."""
        if self.main_window:
            return self.main_window.selected_tags_for_current_image
        else:
            print("Warning: SelectedTagsPanel does not have access to MainWindow instance.")
            return [] # Return empty list if no main_window

    def _add_context_menu_actions(self, menu, tag_data):
        """Add panel-specific context menu actions for SelectedTagsPanel.
        Adds 'Add to Known Tags' option for unknown tags.
        """
        actions_added = False
        
        # Only add the "Add to Known Tags" action for unknown tags
        if not tag_data.is_known:
            add_action = QAction("Add to Known Tags", self)
            add_action.triggered.connect(lambda: self.main_window.add_new_tag_to_model(tag_data.name))
            menu.addAction(add_action)
            actions_added = True
            
        return actions_added

    def is_tag_draggable(self, tag_name):
        """Always allow dragging in this panel."""
        return True

    def _get_bulk_operations(self):
        """Returns list of allowed bulk operations for this panel."""
        return ['add_front', 'add_end', 'remove']

    def _remove_tag_from_data_list(self, tag_data):
        """Remove tag from the selected tags list."""
        self.main_window.selected_tags_for_current_image.remove(tag_data)

    def _insert_tag_into_data_list(self, tag_data, index):
        """Insert tag into the selected tags list at specified index."""
        self.main_window.selected_tags_for_current_image.insert(index, tag_data)

    def _handle_post_drop_update(self, tag_name, original_index, new_index):
        """Update workfile after tag order changes."""
        self.main_window.update_workfile_for_current_image()
        print("  Workfile updated with new tag order.")

    