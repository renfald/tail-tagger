from PySide6.QtCore import QSize
from PySide6.QtGui import QImage, QColor
from tail_tagger.ui.image_loading import fit_size, decode_image, neighbor_paths


def _png(tmp_path, name, w, h):
    img = QImage(w, h, QImage.Format_RGB32)
    img.fill(QColor(90, 140, 200))
    path = str(tmp_path / name)
    assert img.save(path)
    return path


def test_fit_size_shrinks_keeping_aspect():
    assert fit_size(QSize(12000, 6000), QSize(3000, 3000)) == QSize(3000, 1500)


def test_fit_size_never_enlarges():
    assert fit_size(QSize(800, 600), QSize(3000, 3000)) == QSize(800, 600)


def test_decode_image_fits_box(tmp_path):
    assert decode_image(_png(tmp_path, "wide.png", 2000, 1000), QSize(500, 500)).size() == QSize(500, 250)


def test_decode_image_keeps_small_image_size(tmp_path):
    assert decode_image(_png(tmp_path, "small.png", 300, 200), QSize(500, 500)).size() == QSize(300, 200)


def test_decode_image_over_qt_default_limit(tmp_path):
    # 8200x8200 RGB32 is about 269 MB, over Qt's 256 MB default
    image = decode_image(_png(tmp_path, "big.png", 8200, 8200), QSize(2560, 2560))
    assert image.size() == QSize(2560, 2560)


def test_decode_image_unreadable_returns_null(tmp_path):
    path = tmp_path / "bad.png"
    path.write_text("not an image")
    assert decode_image(str(path), QSize(500, 500)).isNull()


def test_neighbor_paths_wraps_at_both_ends():
    paths = ["a", "b", "c", "d"]
    assert neighbor_paths(paths, 0) == ["b", "d"]
    assert neighbor_paths(paths, 3) == ["a", "c"]
    assert neighbor_paths(paths, 1) == ["c", "a"]


def test_neighbor_paths_small_folders():
    assert neighbor_paths(["a"], 0) == []
    assert neighbor_paths(["a", "b"], 0) == ["b"]
