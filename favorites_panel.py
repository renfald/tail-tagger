from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from tag_list_panel import TagListPanel
from tag_widget import TagWidget  # Import TagWidget

class FavoritesPanel(TagListPanel):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window  # Store main_window

    def get_styling_mode(self):
        return "ignore_select"

    def update_display(self):
        # Clear existing widgets
        for i in reversed(range(self.layout.count())):
            widget = self.layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        # Get the ordered list of favorite tags from MainWindow
        favorite_tags = self.main_window.favorite_tags_ordered

        # Create and add TagWidgets
        for tag_data in favorite_tags:
            tag_widget = TagWidget(tag_data.name, is_known_tag=tag_data.is_known)  # Pass is_known
            tag_widget.set_styling_mode(self.get_styling_mode())
            tag_widget.tag_clicked.connect(self.main_window._handle_tag_clicked)
            self.layout.addWidget(tag_widget)

    def add_tag(self, tag_name, is_known=True):
        pass  # Not needed

    def remove_tag(self, tag_name):
        pass  # Not needed

    def clear_tags(self):
        pass  # Not needed

    def get_tags(self):
        pass  # Not needed

    def set_tags(self, tags):
        pass # Not needed

    def set_tag_selected(self, tag_name, is_selected):
        pass  # Not needed

    def is_tag_draggable(self, tag_name):
        return True # Always draggable in this panel

    def dropEvent(self, event):
        pass # To be implemented