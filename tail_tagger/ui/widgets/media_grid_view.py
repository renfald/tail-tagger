"""The grid view: the open folder's images as thumbnail tiles.

MediaGridModel holds the folder's paths in Prev/Next order and which one is current.
GridTileDelegate draws each tile from the path and its thumbnail. MediaGridView lays
the tiles out, asks its ThumbnailLoader for the thumbnails near the visible area, and
emits image_clicked / image_activated for MainWindow to act on. MainWindow handles the
grid's keys; the view itself only scrolls.
"""
import os

from PySide6.QtCore import QAbstractListModel, QModelIndex, QPoint, QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QAbstractItemView, QAbstractScrollArea, QFrame, QListView, QStyledItemDelegate

from tail_tagger.file_operations import FileOperations
from tail_tagger.ui.grid_nav import TILE_DEFAULT, load_order, step_tile_size
from tail_tagger.ui.thumbnail_loader import FAILED, ThumbnailLoader

TILE_GAP = 4  # Space around each tile, so neighbors are 2 * TILE_GAP apart
OUTLINE_WIDTH = 3  # White outline around the current image's tile
BACKGROUND = "#191919"
TILE_BACKGROUND = "#222222"
FAILED_BACKGROUND = "#3a2020"
FAILED_TEXT = "#cc8888"
PLACEHOLDER_TEXT = "#888888"
BADGE_TEXT = "#bbbbbb"
EMPTY_TEXT = "#cccccc"


class MediaGridModel(QAbstractListModel):
    """The folder's media paths in order, and the row of the current image (-1 for none)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._paths = []
        self._rows = {}
        self.current_row = -1

    def set_paths(self, paths):
        self.beginResetModel()
        self._paths = list(paths)
        self._rows = {path: row for row, path in enumerate(self._paths)}
        self.current_row = -1
        self.endResetModel()

    def path_at(self, row):
        """The path shown in this row, or None if there is no such row."""
        return self._paths[row] if 0 <= row < len(self._paths) else None

    def row_of(self, path):
        """The row showing path, or -1."""
        return self._rows.get(path, -1)

    def set_current(self, row):
        """Marks row as the current image. Only the old and new rows are redrawn."""
        old = self.current_row
        self.current_row = row
        for changed in {old, row}:
            if 0 <= changed < len(self._paths):
                index = self.index(changed, 0)
                self.dataChanged.emit(index, index)

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._paths)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        path = self._paths[index.row()]
        if role == Qt.DisplayRole:
            return os.path.basename(path)
        if role == Qt.UserRole:
            return path
        return None


class GridTileDelegate(QStyledItemDelegate):
    """Draws one tile: the thumbnail (or a placeholder), the name bar, the number badge,
    and an outline when it is the current image."""

    def __init__(self, view):
        super().__init__(view)
        self.view = view

    def sizeHint(self, option, index):
        """Called by the view to lay out the grid: every tile takes one grid cell."""
        return self.view.gridSize()

    def paint(self, painter, option, index):
        """Called by the view for each visible tile. option.rect is the tile's grid cell."""
        path = index.data(Qt.UserRole)
        tile = option.rect.adjusted(TILE_GAP, TILE_GAP, -TILE_GAP, -TILE_GAP)
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        thumbnail = self.view.loader.thumbnail(path)

        if FileOperations.is_video_file(path):
            painter.fillRect(tile, QColor(TILE_BACKGROUND))
            self._centered_text(painter, tile, "▶\nvideo", PLACEHOLDER_TEXT)
        elif thumbnail is FAILED:
            painter.fillRect(tile, QColor(FAILED_BACKGROUND))
            self._centered_text(painter, tile, "can't load", FAILED_TEXT)
        else:
            painter.fillRect(tile, QColor(TILE_BACKGROUND))
            if isinstance(thumbnail, QPixmap):
                # Fit the whole picture in the tile: nothing is cropped
                target = QRect(QPoint(0, 0), thumbnail.size().scaled(tile.size(), Qt.KeepAspectRatio))
                target.moveCenter(tile.center())
                painter.drawPixmap(target, thumbnail)

        self._paint_name_bar(painter, tile, index.data(Qt.DisplayRole))
        self._paint_badge(painter, tile, index.row() + 1)
        if index.row() == self.view.model().current_row:
            painter.setPen(QPen(QColor("white"), OUTLINE_WIDTH))
            painter.setBrush(Qt.NoBrush)
            half = OUTLINE_WIDTH / 2
            painter.drawRect(QRectF(tile).adjusted(half, half, -half, -half))
        painter.restore()

    @staticmethod
    def _centered_text(painter, rect, text, color):
        painter.setPen(QColor(color))
        painter.drawText(rect, Qt.AlignCenter, text)

    @staticmethod
    def _paint_name_bar(painter, tile, name):
        """The file name on a dark bar across the bottom of the tile, cut with "…" if too long."""
        metrics = painter.fontMetrics()
        bar = QRect(tile.left(), tile.bottom() - metrics.height() - 3, tile.width(), metrics.height() + 4)
        painter.fillRect(bar, QColor(0, 0, 0, 150))
        painter.setPen(QColor("white"))
        painter.drawText(bar, Qt.AlignCenter, metrics.elidedText(name, Qt.ElideRight, bar.width() - 8))

    @staticmethod
    def _paint_badge(painter, tile, number):
        """The image's position in the folder, in a small badge at the top-left corner."""
        metrics = painter.fontMetrics()
        text = str(number)
        badge = QRect(tile.left() + 4, tile.top() + 4, metrics.horizontalAdvance(text) + 8, metrics.height() + 2)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 140))
        painter.drawRoundedRect(badge, 3, 3)
        painter.setPen(QColor(BADGE_TEXT))
        painter.drawText(badge, Qt.AlignCenter, text)


class MediaGridView(QListView):
    """The folder as a grid of tiles. Emits what the user clicked; MainWindow decides what that means."""

    image_clicked = Signal(int)  # Row of a clicked tile
    image_activated = Signal(int)  # Row of a double-clicked tile

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tile_size = TILE_DEFAULT
        self._wheel_remainder = 0  # Ctrl+wheel delta not yet used; a notch is 120
        self.empty_text = ""  # Drawn in the middle when the folder has no images
        self.loader = ThumbnailLoader(parent=self)
        self.loader.ready.connect(self._on_thumbnail_ready)

        self._model = MediaGridModel(self)
        self.setModel(self._model)
        self.setItemDelegate(GridTileDelegate(self))

        self.setViewMode(QListView.IconMode)
        self.setResizeMode(QListView.Adjust)
        self.setMovement(QListView.Static)
        self.setUniformItemSizes(True)
        self.setSelectionMode(QAbstractItemView.NoSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet(f"QListView {{ background-color: {BACKGROUND}; }}")
        self._apply_tile_size()

        self.clicked.connect(lambda index: self.image_clicked.emit(index.row()))
        self.doubleClicked.connect(lambda index: self.image_activated.emit(index.row()))
        self.verticalScrollBar().valueChanged.connect(self._request_visible)

    # --- data ---
    def set_paths(self, paths, empty_text=""):
        """Shows these paths as tiles, dropping the previous folder's thumbnails."""
        self.loader.reset()
        self._model.set_paths(paths)
        self.empty_text = empty_text
        self.viewport().update()
        self._request_visible()

    def set_current(self, row, center=False):
        """Marks row as the current image and scrolls its tile into view (to the middle if center)."""
        self._model.set_current(row)
        if not 0 <= row < self._model.rowCount():
            return
        if self.isVisible():
            # Lay out first, or scrolling to a tile right after the grid appears lands short
            self.doItemsLayout()
        hint = QAbstractItemView.PositionAtCenter if center else QAbstractItemView.EnsureVisible
        self.scrollTo(self._model.index(row, 0), hint)

    def columns(self):
        """How many tiles fit across the grid at its current width."""
        return max(1, self.viewport().width() // self.gridSize().width())

    # --- sizing ---
    def _apply_tile_size(self):
        cell = self.tile_size + 2 * TILE_GAP
        self.setGridSize(QSize(cell, cell))

    def wheelEvent(self, event):
        # Ctrl + wheel resizes the tiles; the plain wheel scrolls
        if event.modifiers() & Qt.ControlModifier:
            # Touchpads and smooth wheels send many small deltas, so they add up to whole notches
            self._wheel_remainder += event.angleDelta().y()
            notches = int(self._wheel_remainder / 120)
            if notches:
                self._wheel_remainder -= notches * 120
                self.tile_size = step_tile_size(self.tile_size, notches)
                self._apply_tile_size()
                self.doItemsLayout()
            event.accept()
            return
        super().wheelEvent(event)

    def keyPressEvent(self, event):
        # Keys only scroll, like a plain scroll area. MainWindow handles the grid's keys,
        # and QListView's own handling would move an index MainWindow doesn't use.
        QAbstractScrollArea.keyPressEvent(self, event)

    # --- loading ---
    def updateGeometries(self):
        # Called after every layout, so the visible tiles are known here
        super().updateGeometries()
        self._request_visible()

    def showEvent(self, event):
        super().showEvent(event)
        self._request_visible()

    def hideEvent(self, event):
        # Queued thumbnails would compete with the single view's full-size decode
        super().hideEvent(event)
        self.loader.request([])

    def _request_visible(self):
        """Asks the loader for the visible tiles' thumbnails, then two rows below and two rows above them.
        Does nothing while the grid is hidden, so opening a folder in single view decodes nothing."""
        count = self._model.rowCount()
        if not self.isVisible() or count == 0:
            return
        columns = self.columns()
        cell = self.gridSize().height()
        top = self.verticalScrollBar().value()
        first = (top // cell) * columns
        last = min(count - 1, ((top + self.viewport().height()) // cell + 1) * columns - 1)
        rows = load_order(first, last, count, ahead=2 * columns)
        self.loader.request([self._model.path_at(row) for row in rows])

    def _on_thumbnail_ready(self, path):
        row = self._model.row_of(path)
        if row >= 0:
            self.update(self._model.index(row, 0))

    # --- painting ---
    def paintEvent(self, event):
        super().paintEvent(event)
        if self._model.rowCount() == 0 and self.empty_text:
            painter = QPainter(self.viewport())
            painter.setPen(QColor(EMPTY_TEXT))
            painter.drawText(self.viewport().rect(), Qt.AlignCenter, self.empty_text)
            painter.end()
