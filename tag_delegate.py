from PySide6.QtWidgets import QStyledItemDelegate, QWidget
from PySide6.QtCore import QSize, Qt, QPoint
from tag_widget import TagWidget

class TagDelegate(QStyledItemDelegate):
    """Custom delegate to render TagWidgets within a QListView."""

    def __init__(self, parent=None):
        super().__init__(parent)

    def paint(self, painter, option, index):
        """Paints the TagWidget for the given item."""
        # Placeholder Implementation: Just draw a rectangle
        painter.save()
        painter.setBrush(Qt.gray)  # Placeholder color
        painter.drawRect(option.rect)
        painter.restore()


    def sizeHint(self, option, index):
        """Returns the size hint for the TagWidget."""
        # We'll use a placeholder tag name for size calculation.
        tag_widget = TagWidget("placeholder")
        return tag_widget.sizeHint()