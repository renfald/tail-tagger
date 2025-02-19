from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from tag_list_panel import TagListPanel
from tag_widget import TagWidget

class SelectedTagsPanel(TagListPanel):
    def __init__(self, main_window, parent=None): # Accept main_window
        super().__init__(parent)
        self.main_window = main_window # Store main_window
        # self.setStyleSheet("background-color: transparent;") # if you need a bg color

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
                self.layout.addWidget(tag_widget)
        else:
            print("Warning: SelectedTagsPanel does not have access to MainWindow instance.")
            # Consider adding a placeholder QLabel to indicate no image is loaded.

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
        pass