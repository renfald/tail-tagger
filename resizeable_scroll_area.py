from PySide6.QtWidgets import QScrollArea
from PySide6.QtCore import Signal
class ResizableScrollArea(QScrollArea):
    resized = Signal()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resized.emit()