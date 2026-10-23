"""The tag list used by every tag panel.

TagRowsModel holds the tags a list shows, in order. TagDelegate draws each row from its
TagData. TagListView turns mouse input into signals (tag_clicked, favorite_clicked,
tag_right_clicked, tag_moved) that the panel acts on. Rows read their TagData each time
they are drawn, so a panel calls repaint_tags() after selection, favorites or tags change.
"""
from math import sqrt

from PySide6.QtCore import QAbstractListModel, QEvent, QMimeData, QModelIndex, QPoint, QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QDrag, QFont, QFontMetrics, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QAbstractScrollArea, QAbstractItemView, QListView, QStyledItemDelegate

from tail_tagger.file_operations import FileOperations
from tail_tagger.ui.tag_rows import (DRAG_THRESHOLD, STAR_SIZE, TEXT_MARGIN, final_index, insertion_point,
                                     tag_colors, text_width)

ROW_GAP = 1  # Space above each row and at the list's left and right edges
BORDER_WIDTH = 1  # Dark border around the tag box
HIGHLIGHT_WIDTH = 2  # Grey frame around Search's keyboard-highlighted result
CORNER_RADIUS = 5
STRIPE_WIDTH = 2  # Category color stripe on the left edge of the box
DROP_LINE_WIDTH = 2  # The white line showing where a dragged tag will land
FOOTER_PADDING = 5  # Space around the footer note's text
FOOTER_COLOR = "#888888"
TOOLTIP_STYLE = "QToolTip { color: #FFFFFF; background-color: #353535; border: 1px solid #555555; }"


class TagRowsModel(QAbstractListModel):
    """The tags one list shows, in order, plus optional tooltips by tag name.

    An optional footer note adds one last row after the tags. tag_at() gives None for it.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tags = []
        self._tooltips = {}
        self._footer = None

    def set_tags(self, tags, tooltips=None, footer=None):
        self.beginResetModel()
        self._tags = list(tags)
        self._tooltips = dict(tooltips or {})
        self._footer = footer or None
        self.endResetModel()

    def tag_count(self):
        return len(self._tags)

    def has_footer(self):
        return self._footer is not None

    def tag_at(self, row):
        """The TagData shown in this row, or None for the footer row."""
        return self._tags[row] if 0 <= row < len(self._tags) else None

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self._tags) + (1 if self._footer else 0)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        if index.row() >= len(self._tags):
            return self._footer if role == Qt.DisplayRole else None
        tag = self._tags[index.row()]
        if role == Qt.DisplayRole:
            return FileOperations.convert_underscores_to_spaces(tag.name)
        if role == Qt.ToolTipRole:
            return self._tooltips.get(tag.name)
        if role == Qt.UserRole:
            return tag
        return None


class TagDelegate(QStyledItemDelegate):
    """Paints one tag row: the rounded box, category stripe, name, and the hover star."""

    def __init__(self, view, dim_on_select):
        super().__init__(view)
        self.view = view
        self.dim_on_select = dim_on_select
        self.font = QFont()
        self.font.setPointSize(8)
        # One line of text, plus the text margin and the border above and below it
        self.row_height = QFontMetrics(self.font).height() + 2 * TEXT_MARGIN + 2 * BORDER_WIDTH
        self.footer_font = QFont(view.font())
        self.footer_font.setItalic(True)
        self.star_icons = {True: QIcon(":/icons/star-fill.svg"), False: QIcon(":/icons/star-outline.svg")}

    def sizeHint(self, option, index):
        """Called by the view when it lays out the list, to get each row's height."""
        if index.data(Qt.UserRole) is None:
            return QSize(option.rect.width(), ROW_GAP + self._footer_rect(index).height() + 2 * FOOTER_PADDING)
        # The highlight frame sits outside the box, so a highlighted row is taller
        extra = 2 * HIGHLIGHT_WIDTH if index.row() == self.view.highlighted_row else 0
        return QSize(option.rect.width(), ROW_GAP + self.row_height + extra)

    def _footer_rect(self, index):
        """The footer note's wrapped text size at the list's current width."""
        width = self.view.viewport().width() - 2 * ROW_GAP - 2 * FOOTER_PADDING
        return QFontMetrics(self.footer_font).boundingRect(QRect(0, 0, max(width, 1), 10000), Qt.TextWordWrap,
                                                           index.data(Qt.DisplayRole) or "")

    def paint(self, painter, option, index):
        """Called by the view for each visible row when the list redraws. option.rect is the row's
        place in the list. Draws the footer note here, and hands tag rows to paint_row()."""
        painter.save()
        tag = index.data(Qt.UserRole)
        if tag is None:
            painter.setFont(self.footer_font)
            painter.setPen(QColor(FOOTER_COLOR))
            text_rect = self.view.fit_row(option.rect).adjusted(FOOTER_PADDING, FOOTER_PADDING, -FOOTER_PADDING, -FOOTER_PADDING)
            painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap, index.data(Qt.DisplayRole))
        else:
            painter.setRenderHint(QPainter.Antialiasing)
            self.paint_row(painter, self.view.fit_row(option.rect), tag, index.row())
        painter.restore()

    def paint_row(self, painter, rect, tag, row):
        """Draws one tag row into rect: Search's highlight frame, the box, the name, and the star on hover.

        Separate from paint() so the drag ghost can draw the same row into a pixmap.
        """
        content = QRect(rect)
        if row == self.view.highlighted_row:
            pen = QPen(QColor("grey"), HIGHLIGHT_WIDTH)
            pen.setJoinStyle(Qt.MiterJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            half = HIGHLIGHT_WIDTH / 2
            painter.drawRect(QRectF(rect).adjusted(half, half, -half, -half))
            content = rect.adjusted(HIGHLIGHT_WIDTH, HIGHLIGHT_WIDTH, -HIGHLIGHT_WIDTH, -HIGHLIGHT_WIDTH)

        # On hover, a known tag's box is drawn STAR_SIZE px narrower and the star goes in the space to its right
        show_star = tag.is_known and row == self.view.hover_row
        box = QRect(content)
        if show_star:
            box.setRight(content.right() - STAR_SIZE)

        background, text_color, stripe = tag_colors(tag.category, tag.is_known, tag.selected, self.dim_on_select)
        self._paint_box(painter, box, background, stripe)

        # Long names are cut to the width available with the star's room reserved (for known tags),
        # so the text doesn't change when the star appears
        painter.setFont(self.font)
        painter.setPen(QColor(text_color))
        name = FileOperations.convert_underscores_to_spaces(tag.name)
        width = text_width(self.view.viewport().width(), tag.is_known)
        if width > 10:
            name = painter.fontMetrics().elidedText(name, Qt.ElideRight, width)
        text_rect = box.adjusted(STRIPE_WIDTH + TEXT_MARGIN, 1 + TEXT_MARGIN, -1 - TEXT_MARGIN, -1 - TEXT_MARGIN)
        painter.drawText(text_rect, Qt.AlignCenter, name)

        if show_star:
            star = self.view.star_rect(content)
            size = min(STAR_SIZE, star.height())
            icon_rect = QRect(0, 0, size, size)
            icon_rect.moveCenter(star.center())
            self.star_icons[bool(tag.favorite)].paint(painter, icon_rect)

    def _paint_box(self, painter, box, background, stripe):
        """The rounded box with a 1 px dark border and the category stripe along its left edge."""
        outer = QPainterPath()
        outer.addRoundedRect(QRectF(box), CORNER_RADIUS, CORNER_RADIUS)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#121212"))
        painter.drawPath(outer)

        # The stripe follows the rounded left edge, like a thick left border would
        painter.save()
        painter.setClipPath(outer)
        painter.setBrush(QColor(stripe))
        painter.drawRect(QRect(box.left(), box.top(), CORNER_RADIUS + 1, box.height()))
        painter.restore()

        inner = QPainterPath()
        inner.addRoundedRect(QRectF(box).adjusted(STRIPE_WIDTH, BORDER_WIDTH, -BORDER_WIDTH, -BORDER_WIDTH),
                             CORNER_RADIUS - 1, CORNER_RADIUS - 1)
        painter.setBrush(QColor(background))
        painter.drawPath(inner)


class TagListView(QListView):
    """A list of tags. Emits what the user did; the panel decides what that means."""

    tag_clicked = Signal(str)
    favorite_clicked = Signal(str)
    tag_right_clicked = Signal(str)
    tag_moved = Signal(str, int)  # Tag name and its new index, after a drag within this list

    def __init__(self, dim_on_select, reorderable, parent=None):
        super().__init__(parent)
        self.reorderable = reorderable
        self.hover_row = -1
        self.highlighted_row = -1
        self._press_row = -1
        self._press_pos = None
        self._drop_line_y = None  # Where the drop line is drawn during a drag, or None

        self._model = TagRowsModel(self)
        self.setModel(self._model)
        self._delegate = TagDelegate(self, dim_on_select)
        self.setItemDelegate(self._delegate)

        self.setSelectionMode(QAbstractItemView.NoSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setMouseTracking(True)
        self.setStyleSheet("QListView { background-color: #191919; } " + TOOLTIP_STYLE)
        # Drops land on the viewport, so it has to accept them too
        self.setAcceptDrops(reorderable)
        self.viewport().setAcceptDrops(reorderable)

    # --- data ---
    def set_tags(self, tags, tooltips=None, footer=None):
        """Shows these tags, keeping the scroll position. A footer note, if given, scrolls in after the last tag."""
        scroll = self.verticalScrollBar().value()
        # A press on the previous tags can't become a click on whichever tag now has that row number
        self._press_row = -1
        self._model.set_tags(tags, tooltips, footer)
        # Lay out now so the scroll range is right before the old position goes back
        self.doItemsLayout()
        self.verticalScrollBar().setValue(min(scroll, self.verticalScrollBar().maximum()))
        self._update_hover(self.viewport().mapFromGlobal(QCursor.pos()))

    def repaint_tags(self):
        """Redraws the visible rows, picking up selection, favorite and known-tag changes."""
        self.viewport().update()

    def set_highlighted_row(self, row):
        if row == self.highlighted_row:
            return
        self.highlighted_row = row
        # The highlighted row is taller, so the rows need laying out again
        self.scheduleDelayedItemsLayout()
        self.viewport().update()

    def fit_row(self, rect):
        """The rect a row is drawn in: the item's rect minus ROW_GAP at the top and both sides.

        sizeHint() makes each item ROW_GAP taller than the row, and the row is drawn below
        that gap. QListView.setSpacing() isn't used because it adds the space both above and
        below every item, which makes the gap between rows twice as wide.
        """
        return QRect(rect.left() + ROW_GAP, rect.top() + ROW_GAP,
                     self.viewport().width() - 2 * ROW_GAP, rect.height() - ROW_GAP)

    def star_rect(self, content_rect):
        """Where the star sits in a row's content rect (fit_row, inside any highlight): its right STAR_SIZE pixels."""
        return QRect(content_rect.right() - STAR_SIZE + 1, content_rect.top(), STAR_SIZE, content_rect.height())

    def _content_rect(self, row):
        """The row's rect inside the highlight frame, if it has one."""
        rect = self.fit_row(self.visualRect(self._model.index(row, 0)))
        if row == self.highlighted_row:
            rect = rect.adjusted(HIGHLIGHT_WIDTH, HIGHLIGHT_WIDTH, -HIGHLIGHT_WIDTH, -HIGHLIGHT_WIDTH)
        return rect

    def _tag_row(self, pos):
        """The tag row at pos, or -1 for empty space and the footer."""
        row = self.indexAt(pos).row()
        return row if 0 <= row < self._model.tag_count() else -1

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # The footer wraps to the width, so its height changes with it; tag rows don't
        if self._model.has_footer() and event.size().width() != event.oldSize().width():
            self.scheduleDelayedItemsLayout()

    # --- hover ---
    def _update_hover(self, pos):
        row = self._tag_row(pos) if self.viewport().rect().contains(pos) else -1
        if not self.viewport().underMouse():
            row = -1
        if row != self.hover_row:
            self.hover_row = row
            self.viewport().update()
        if row >= 0:
            self.viewport().setCursor(Qt.PointingHandCursor)
        else:
            self.viewport().unsetCursor()

    def viewportEvent(self, event):
        if event.type() == QEvent.Leave:
            self.hover_row = -1
            self.viewport().unsetCursor()
            self.viewport().update()
        return super().viewportEvent(event)

    # --- mouse ---
    def mousePressEvent(self, event):
        # QListView's own handling would select rows and move the current index; tags don't use either
        if event.button() == Qt.LeftButton:
            self._press_pos = event.position().toPoint()
            self._press_row = self._tag_row(self._press_pos)
        event.accept()

    def mouseDoubleClickEvent(self, event):
        # A double click is two clicks, so it toggles twice
        self.mousePressEvent(event)

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        if not (event.buttons() & Qt.LeftButton):
            self._update_hover(pos)
            return
        if self._press_row < 0 or self._press_pos is None:
            return
        delta = pos - self._press_pos
        if sqrt(delta.x() ** 2 + delta.y() ** 2) > DRAG_THRESHOLD:
            row = self._press_row
            # Once a press becomes a drag it can no longer count as a click
            self._press_row = -1
            self._start_drag(row)

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton or self._press_row < 0:
            return
        row = self._press_row
        self._press_row = -1
        tag = self._model.tag_at(row)
        pos = event.position().toPoint()
        # The star only counts where it's showing: a known tag under the mouse
        if tag.is_known and row == self.hover_row and self.star_rect(self._content_rect(row)).contains(pos):
            self.favorite_clicked.emit(tag.name)
        else:
            self.tag_clicked.emit(tag.name)

    def contextMenuEvent(self, event):
        row = self._tag_row(event.pos())
        if event.reason() == event.Reason.Mouse and row >= 0:
            self.tag_right_clicked.emit(self._model.tag_at(row).name)
            event.accept()
        else:
            super().contextMenuEvent(event)

    # --- keys ---
    def keyPressEvent(self, event):
        # Keys only scroll the list, like a plain scroll area: no row navigation or
        # type-to-search, so other keys still reach the panel
        QAbstractScrollArea.keyPressEvent(self, event)

    # --- drag ---
    def _start_drag(self, row):
        """Drags a tag. Lists that can't be reordered start a drag that shows nothing and
        drops nowhere, so dragging off a misclick doesn't toggle the tag."""
        tag = self._model.tag_at(row)
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(tag.name)
        drag.setMimeData(mime)

        if not self.reorderable:
            empty = QPixmap(1, 1)
            empty.fill(Qt.transparent)
            drag.setPixmap(empty)
            drag.exec(Qt.MoveAction)
            return

        # The ghost is the row as it looks now (star included, since it's under the mouse) at half opacity
        rect = self.fit_row(self.visualRect(self._model.index(row, 0)))
        # Drawn at the screen's pixel ratio so the ghost stays sharp with display scaling
        ratio = self.devicePixelRatioF()
        ghost = QPixmap(rect.size() * ratio)
        ghost.setDevicePixelRatio(ratio)
        ghost.fill(Qt.transparent)
        painter = QPainter(ghost)
        painter.setOpacity(0.5)
        painter.setRenderHint(QPainter.Antialiasing)
        self._delegate.paint_row(painter, QRect(QPoint(0, 0), rect.size()), tag, row)
        painter.end()
        drag.setPixmap(ghost)
        drag.setHotSpot(QPoint(rect.width() // 2, rect.height() // 2))

        # The dragged tag leaves the list while it's dragged, so the rows close up around it
        self.hover_row = -1
        self.setRowHidden(row, True)
        drag.exec(Qt.MoveAction)

        # Whatever happened (moved, dropped in place, dropped elsewhere, cancelled), no row stays
        # hidden. A move resets the rows during exec(), so the original row number may be stale.
        self._drop_line_y = None
        for r in range(self._model.rowCount()):
            if self.isRowHidden(r):
                self.setRowHidden(r, False)
        self._update_hover(self.viewport().mapFromGlobal(QCursor.pos()))
        self.viewport().update()

    def _visible_rows(self):
        """(top, bottom, row) of each shown row, in order, as insertion_point expects."""
        rows = []
        for row in range(self._model.tag_count()):
            if not self.isRowHidden(row):
                rect = self.fit_row(self.visualRect(self._model.index(row, 0)))
                rows.append((rect.top(), rect.bottom(), row))
        return rows

    def _drop_target(self, y):
        """(line_y, insert_index) for a drop at y in viewport coordinates."""
        return insertion_point(self._visible_rows(), y, self._model.tag_count())

    def _finish_drop(self, name, y):
        """Works out the dropped tag's new index and announces the move."""
        names = [self._model.tag_at(row).name for row in range(self._model.tag_count())]
        if name not in names:
            return
        _, insert_index = self._drop_target(y)
        self.tag_moved.emit(name, final_index(insert_index, names.index(name)))

    def _accepts_drag(self, event):
        """Accepts only drags this list started, and only if it can be reordered."""
        return self.reorderable and event.source() is self

    def dragEnterEvent(self, event):
        if self._accepts_drag(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if not self._accepts_drag(event):
            event.ignore()
            return
        event.acceptProposedAction()
        line_y, _ = self._drop_target(event.position().toPoint().y())
        if line_y != self._drop_line_y:
            self._drop_line_y = line_y
            self.viewport().update()

    def dragLeaveEvent(self, event):
        self._drop_line_y = None
        self.viewport().update()

    def dropEvent(self, event):
        if not self._accepts_drag(event):
            event.ignore()
            return
        self._drop_line_y = None
        self.viewport().update()
        event.acceptProposedAction()
        self._finish_drop(event.mimeData().text(), event.position().toPoint().y())

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._drop_line_y is not None:
            painter = QPainter(self.viewport())
            painter.fillRect(0, self._drop_line_y, self.viewport().width(), DROP_LINE_WIDTH, QColor("white"))
            painter.end()
