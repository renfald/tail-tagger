from PySide6.QtCore import QAbstractListModel, Qt, QModelIndex

class TagListModel(QAbstractListModel):
    """A model to hold a list of tags for the image tagger."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tags = []  # List of dictionaries: [{'name': 'tag1', 'is_known': True}, ...]

    def rowCount(self, parent=QModelIndex()):
        """Returns the number of rows (tags) in the model."""
        return len(self.tags)
    
    def data(self, index, role=Qt.DisplayRole):
        """Returns data for a specific item and role."""
        if not index.isValid():
            return None

        if index.row() < 0 or index.row() >= len(self.tags):
            return None

        tag_data = self.tags[index.row()]

        if role == Qt.DisplayRole:
            return tag_data['name']  # Return the tag name for display.
        elif role == Qt.UserRole:
            return tag_data  # Return the entire tag data dictionary.
        # Add other roles as needed (e.g., Qt.DecorationRole for icons).

        return None
    
    def add_tag(self, tag_name, is_known=True):
        """Adds a tag to the model."""
        # Check if the tag already exists to avoid duplicates.
        if tag_name not in [tag['name'] for tag in self.tags]:
            self.beginInsertRows(QModelIndex(), len(self.tags), len(self.tags))
            self.tags.append({'name': tag_name, 'is_known': is_known})
            self.endInsertRows()
            print(f"Model: Added tag: {tag_name}")  # Debug print

    def remove_tag(self, tag_name):
        """Removes a tag from the model."""
        for i, tag_data in enumerate(self.tags):
            if tag_data['name'] == tag_name:
                self.beginRemoveRows(QModelIndex(), i, i)
                del self.tags[i]
                self.endRemoveRows()
                print(f"Model: Removed tag: {tag_name}")  # Debug print
                break

    def clear_tags(self):
        self.beginResetModel()
        self.tags = []
        self.endResetModel()
        print("model cleared")

    def get_tags(self):
        return [tag_data['name'] for tag_data in self.tags]

    def set_tags(self, tags):
        """Sets the tags in the model, replacing all current"""
        # tags is a list of tag names
        self.beginResetModel()
        self.tags = []
        for tag_name in tags:
            self.tags.append({'name': tag_name, 'is_known': True})
        self.endResetModel()
        print(f"Model: tags set to {tags}")