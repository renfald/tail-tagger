"""The center panel stays idle while the grid covers it."""
import time

from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QColor, QImage, QPixmap

from tail_tagger.ui.panels.center_panel import CenterPanel


def _png(tmp_path, name, w, h):
    img = QImage(w, h, QImage.Format_RGB32)
    img.fill(QColor(90, 140, 200))
    path = str(tmp_path / name)
    assert img.save(path)
    return path


def _spin(ms):
    """Runs the event loop for ms. QTest.qWait keeps Python's lock, so decode threads wouldn't run."""
    end = time.monotonic() + ms / 1000
    while time.monotonic() < end:
        QCoreApplication.processEvents()
        time.sleep(0.01)


def test_inactive_panel_records_path_without_decoding(qapp, tmp_path):
    path = _png(tmp_path, "a.png", 200, 100)
    panel = CenterPanel()
    panel.set_active(False)
    panel.show_media(path)
    assert panel.media_path == path and panel._decoding is None and panel._wanted == []


def test_inactive_panel_ignores_prefetch(qapp, tmp_path):
    a, b = _png(tmp_path, "a.png", 50, 50), _png(tmp_path, "b.png", 50, 50)
    panel = CenterPanel()
    panel.set_active(False)
    panel.show_media(a)
    panel.prefetch([b])
    assert panel._decoding is None and panel._wanted == []


def test_reactivating_shows_the_recorded_image(qapp, tmp_path):
    path = _png(tmp_path, "a.png", 200, 100)
    panel = CenterPanel()
    panel.set_active(False)
    panel.show_media(path)
    panel.set_active(True)
    _spin(1000)
    assert panel._source_pixmap is not None and not panel._source_pixmap.isNull()


def test_inactive_panel_releases_video(qapp, tmp_path):
    video = str(tmp_path / "clip.webm")
    open(video, "wb").close()
    panel = CenterPanel()
    panel.show_media(video)
    panel.set_active(False)
    assert panel._player.source().isEmpty()


def _shown_panel(qapp, path):
    panel = CenterPanel()
    panel.resize(400, 300)
    panel.show()
    panel.show_media(path)
    _spin(500)
    return panel


def test_reactivating_on_an_undecoded_image_drops_the_old_picture(qapp, tmp_path):
    a, b = _png(tmp_path, "a.png", 200, 100), _png(tmp_path, "b.png", 3000, 3000)
    panel = _shown_panel(qapp, a)
    old = panel._source_pixmap
    panel.set_active(False)
    panel.show_media(b)  # the user moved far away in the grid
    panel.set_active(True)
    assert panel._source_pixmap is not old
    assert panel._image_label.pixmap().isNull()


def test_reactivating_shows_the_placeholder_until_decoded(qapp, tmp_path):
    a, b = _png(tmp_path, "a.png", 200, 100), _png(tmp_path, "b.png", 3000, 3000)
    panel = _shown_panel(qapp, a)
    panel.set_active(False)
    panel.show_media(b)
    thumb = QPixmap(35, 35)
    panel.set_active(True, placeholder=thumb)
    assert panel._source_pixmap is thumb
    _spin(3000)
    assert panel._source_pixmap is not thumb and panel._source_pixmap.width() > 35
