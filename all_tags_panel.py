from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from tag_list_panel import TagListPanel
from tag_widget import TagWidget

class AllTagsPanel(TagListPanel):
    def __init__(self, tag_list_model, parent=None):
        super().__init__(parent)
        self.tag_list_model = tag_list_model  # Store the model
        # self.setStyleSheet("background-color: #744444;")  # red  background

    def get_styling_mode(self):
        return "dim_on_select"

    def update_display(self):
        # Clear existing widgets
        for i in reversed(range(self.layout.count())):
            widget = self.layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        # Get all *known* tags from the model
        tags = self.tag_list_model.get_known_tags()

        # Create and add TagWidgets
        for tag_data in tags:
            tag_widget = TagWidget(tag_data.name, tag_data.selected, tag_data.is_known)
            tag_widget.set_styling_mode(self.get_styling_mode()) # Set styling mode
            self.layout.addWidget(tag_widget)

    def add_tag(self, tag_name, is_known=True):
        pass # Not needed

    def remove_tag(self, tag_name):
        pass  # Not needed

    def clear_tags(self):
        pass  # Not needed

    def get_tags(self):
        pass # Not needed

    def set_tags(self, tags):
        pass  # Not needed

    def set_tag_selected(self, tag_name, is_selected):
        pass  # Not needed

    def is_tag_draggable(self, tag_name):
        pass

    def dropEvent(self, event):
        pass