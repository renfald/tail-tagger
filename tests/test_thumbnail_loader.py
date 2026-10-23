"""The thumbnail cache's limit and the loader's handling of folders changing mid-decode."""
import time

from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QColor, QImage

from tail_tagger.ui.thumbnail_loader import FAILED, ThumbnailCache, ThumbnailLoader


def _png(tmp_path, name, w, h):
    img = QImage(w, h, QImage.Format_RGB32)
    img.fill(QColor(90, 140, 200))
    path = str(tmp_path / name)
    assert img.save(path)
    return path


def _wait(loader, paths, timeout_ms=5000):
    """Runs the event loop until every path has a thumbnail (or FAILED), or time runs out."""
    end = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < end:
        QCoreApplication.processEvents()
        if all(loader.thumbnail(p) is not None for p in paths):
            return
        time.sleep(0.01)


def _spin(ms):
    """Runs the event loop for ms. QTest.qWait can't be used: it keeps Python's lock,
    so the decode threads never get to run while it waits."""
    end = time.monotonic() + ms / 1000
    while time.monotonic() < end:
        QCoreApplication.processEvents()
        time.sleep(0.01)


def test_cache_drops_least_recently_used():
    cache = ThumbnailCache(limit=2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.get("a")  # a is now the most recently used
    cache.put("c", 3)
    assert "a" in cache and "c" in cache and "b" not in cache


def test_cache_never_exceeds_limit():
    cache = ThumbnailCache(limit=3)
    for i in range(10):
        cache.put(str(i), i)
    assert len(cache) == 3


def test_thumbnail_fits_decode_size(qapp, tmp_path):
    path = _png(tmp_path, "wide.png", 1400, 700)
    loader = ThumbnailLoader()
    loader.request([path])
    _wait(loader, [path])
    pixmap = loader.thumbnail(path)
    assert (pixmap.width(), pixmap.height()) == (350, 175)


def test_small_image_is_not_enlarged(qapp, tmp_path):
    path = _png(tmp_path, "small.png", 100, 80)
    loader = ThumbnailLoader()
    loader.request([path])
    _wait(loader, [path])
    pixmap = loader.thumbnail(path)
    assert (pixmap.width(), pixmap.height()) == (100, 80)


def test_unreadable_file_is_marked_failed(qapp, tmp_path):
    path = str(tmp_path / "broken.png")
    with open(path, "wb") as f:
        f.write(b"not an image")
    loader = ThumbnailLoader()
    loader.request([path])
    _wait(loader, [path])
    assert loader.thumbnail(path) is FAILED


def test_videos_are_never_decoded(qapp, tmp_path):
    path = str(tmp_path / "clip.webm")
    open(path, "wb").close()
    loader = ThumbnailLoader()
    seen = []
    loader.ready.connect(seen.append)
    loader.request([path])
    _spin(200)
    assert loader.thumbnail(path) is None and seen == []


def test_reset_drops_results_for_old_paths(qapp, tmp_path):
    old = [_png(tmp_path, f"old{i}.png", 2000, 2000) for i in range(4)]
    loader = ThumbnailLoader()
    loader.request(old)
    loader.reset()  # The folder changed while these decode
    _spin(2000)
    assert all(loader.thumbnail(p) is None for p in old)
