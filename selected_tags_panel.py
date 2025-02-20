from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from tag_list_panel import TagListPanel
from tag_widget import TagWidget

class SelectedTagsPanel(TagListPanel):
    def __init__(self, main_window, parent=None): # Accept main_window
        super().__init__(parent)
        self.main_window = main_window # Store main_window
        self.setAcceptDrops(True)

    def get_styling_mode(self):
        return "ignore_select"  # Right panel ignores selection for styling

    def update_display(self):
        # Clear existing widgets
        for i in reversed(range(self.layout.count())):
            widget = self.layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        # Get selected tags from MainWindow's in-memory list
        if self.main_window: # Access main_window directly
            tags = self.main_window.selected_tags_for_current_image # Access via stored main_window
            for tag_data in tags:
                tag_widget = TagWidget(tag_data.name, tag_data.selected, tag_data.is_known)
                tag_widget.set_styling_mode(self.get_styling_mode())  # Set styling
                tag_widget.tag_clicked.connect(self.main_window._handle_tag_clicked)
                self.layout.addWidget(tag_widget)
        else:
            print("Warning: SelectedTagsPanel does not have access to MainWindow instance.")
            # Consider adding a placeholder QLabel to indicate no image is loaded.
    
    
    def dragEnterEvent(self, event):
        """Handles drag enter events for the panel."""
        if event.mimeData().hasText(): # Check if mime data has text (tag name)
            event.acceptProposedAction() # Accept the proposed drop action (MoveAction)
            print("Drag Enter Event: Drag accepted for text data.") # Debug
        else:
            event.ignore() # Ignore drops with non-text data
            print("Drag Enter Event: Drag ignored - no text data.") # Debug
    
    # not needed for now
    def add_tag(self, tag_name, is_known=True):
        pass
    def remove_tag(self, tag_name):
        pass
    def clear_tags(self):
        pass
    def get_tags(self):
        pass
    def set_tags(self, tags):
        pass
    def set_tag_selected(self, tag_name, is_selected):
        pass
    def is_tag_draggable(self, tag_name):
        pass
    
    def dropEvent(self, event):
        """Handles drop events for the panel, implementing tag reordering."""
        if event.mimeData().hasText():
            tag_name = event.mimeData().text()
            print(f"Drop Event: Tag '{tag_name}' dropped!") # Debug

            drop_pos = event.pos() # Get drop position in panel coordinates
            drop_index = 0 # Default to top of list if panel is empty or drop is above all tags

            # Iterate through existing TagWidgets to find drop index
            for index in range(self.layout.count()):
                widget_item = self.layout.itemAt(index)
                if widget_item is not None and widget_item.widget() is not None:
                    tag_widget = widget_item.widget()
                    if isinstance(tag_widget, TagWidget):
                        if drop_pos.y() < tag_widget.geometry().bottom(): # Drop position is above current tag_widget's bottom edge
                            drop_index = index
                            print(f"  Drop index determined: {drop_index} (before tag '{tag_widget.tag_name}')") # Debug
                            break # Insert before this tag
                        else:
                            drop_index = index + 1 # If loop completes without breaking, drop at the end
            else:
                print("  Drop index determined: 0 (panel empty or dropped below all tags)") #Debug - in 'else' of for loop, meaning loop completed

            # Placeholder for reordering and workfile update - to be implemented in next steps

            event.acceptProposedAction()
            self.update_display() #TEMP: just update display for now - will be refined in next steps
        else:
            event.ignore()
            print("Drop Event: Drop ignored - no text data.")