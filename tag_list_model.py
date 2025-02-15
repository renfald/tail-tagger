from PySide6.QtCore import QAbstractListModel, Qt, QModelIndex

class TagListModel(QAbstractListModel):
    """A model to hold a list of tags."""

    def __init__(self, parent=None):
        super().__init__(parent)
        # self.tags = []  # Removed

    def rowCount(self, parent=QModelIndex()):
        """Returns the number of rows (tags)."""
        return 0 # Modified

    def data(self, index, role=Qt.DisplayRole):
        """Returns data for a specific item and role."""
        return None # Modified

    # All other methods removed.