"""The grid's model, its current tile, sizing and load requests."""
import time

from PySide6.QtCore import QCoreApplication, QPoint, QPointF, Qt
from PySide6.QtGui import QColor, QImage, QWheelEvent
from PySide6.QtTest import QTest

from tail_tagger.ui.grid_nav import TILE_DEFAULT
from tail_tagger.ui.widgets.media_grid_view import MediaGridView


def _pngs(tmp_path, count):
    paths = []
    for i in range(count):
        img = QImage(64, 48, QImage.Format_RGB32)
        img.fill(QColor(90, 140, 200))
        path = str(tmp_path / f"img{i:02d}.png")
        assert img.save(path)
        paths.append(path)
    return paths


def _settle(ms=100):
    """Runs the event loop for ms (QTest.qWait keeps Python's lock, so decode threads wouldn't run)."""
    end = time.monotonic() + ms / 1000
    while time.monotonic() < end:
        QCoreApplication.processEvents()
        time.sleep(0.01)


def _shown_view(tmp_path, count=12, width=800, height=600):
    view = MediaGridView()
    view.set_paths(_pngs(tmp_path, count))
    view.resize(width, height)
    view.show()
    _settle()
    return view


def _wheel(view, delta, modifiers):
    pos = QPointF(view.viewport().rect().center())
    event = QWheelEvent(pos, view.viewport().mapToGlobal(pos), QPoint(), QPoint(0, delta),
                        Qt.NoButton, modifiers, Qt.NoScrollPhase, False)
    QCoreApplication.sendEvent(view.viewport(), event)


def test_set_paths_fills_model_and_resets_current(qapp, tmp_path):
    view = MediaGridView()
    view.set_paths(_pngs(tmp_path, 12))
    model = view.model()
    assert model.rowCount() == 12
    assert model.current_row == -1
    assert model.index(0, 0).data(Qt.DisplayRole) == "img00.png"


def test_set_current_changes_only_two_rows(qapp, tmp_path):
    view = MediaGridView()
    view.set_paths(_pngs(tmp_path, 12))
    view.set_current(3)
    changed = []
    view.model().dataChanged.connect(lambda first, last, roles=None: changed.extend(range(first.row(), last.row() + 1)))
    view.set_current(5)
    assert sorted(changed) == [3, 5]


def test_columns_follow_width(qapp, tmp_path):
    view = _shown_view(tmp_path, width=800)
    assert view.tile_size == TILE_DEFAULT
    assert view.columns() == 2
    view.resize(1600, 600)
    _settle()
    assert view.columns() >= 4


def test_ctrl_wheel_steps_tile_size(qapp, tmp_path):
    view = _shown_view(tmp_path)
    _wheel(view, 120, Qt.ControlModifier)
    assert view.tile_size == 390
    _wheel(view, 120, Qt.NoModifier)
    assert view.tile_size == 390


def test_hidden_view_requests_no_thumbnails(qapp, tmp_path):
    view = MediaGridView()
    paths = _pngs(tmp_path, 12)
    view.set_paths(paths)
    _settle(500)
    assert view.loader._wanted == [] and view.loader._running == {}
    assert all(view.loader.thumbnail(p) is None for p in paths)


def test_shown_view_loads_visible_thumbnails(qapp, tmp_path):
    view = _shown_view(tmp_path)
    _settle(1000)
    assert view.loader.thumbnail(view.model().path_at(0)) is not None


def test_click_emits_row(qapp, tmp_path):
    view = _shown_view(tmp_path)
    clicked = []
    view.image_clicked.connect(clicked.append)
    rect = view.visualRect(view.model().index(1, 0))
    QTest.mouseClick(view.viewport(), Qt.LeftButton, Qt.NoModifier, rect.center())
    assert clicked == [1]


def test_empty_paths_show_message(qapp):
    view = MediaGridView()
    view.set_paths([], "No images found in this folder.")
    assert view.model().rowCount() == 0
    assert view.empty_text == "No images found in this folder."


def test_ctrl_wheel_small_deltas_add_up_to_one_step(qapp, tmp_path):
    # A touchpad sends many small deltas; four of 30 make one 120 notch
    view = _shown_view(tmp_path)
    for _ in range(4):
        _wheel(view, 30, Qt.ControlModifier)
    assert view.tile_size == 390


def test_hiding_the_grid_stops_queued_thumbnails(qapp, tmp_path):
    view = _shown_view(tmp_path, count=40, width=1600, height=1200)
    view.loader._wanted = list(view.model()._paths)  # as if many were still queued
    view.hide()
    assert view.loader._wanted == []
