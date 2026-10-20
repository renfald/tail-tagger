"""Image decoding for the center panel: plain helpers plus a background worker."""
from PySide6.QtCore import QObject, QRunnable, Qt, Signal
from PySide6.QtGui import QImage, QImageReader

# Qt refuses to decode images over 256 MB by default, and for PNG that check uses the
# full-size image even when a smaller scaled size is set. The classifier decodes these
# images fine, so the viewer shouldn't be the one that fails.
QImageReader.setAllocationLimit(0)


def fit_size(source, box):
    """Returns source shrunk to fit inside box, keeping its aspect ratio. Never enlarges."""
    if source.isEmpty() or box.isEmpty():
        return source
    if source.width() <= box.width() and source.height() <= box.height():
        return source
    return source.scaled(box, Qt.KeepAspectRatio)


def decode_image(path, max_size):
    """Decodes path to fit inside max_size. Returns a null QImage if it can't be read."""
    reader = QImageReader(path)
    size = reader.size()
    if size.isValid():
        target = fit_size(size, max_size)
        if target != size:
            # Lets formats like JPEG decode straight at the smaller size
            reader.setScaledSize(target)
    return reader.read()


def neighbor_paths(paths, index):
    """The next and previous paths around index, wrapping at the ends, without the current path or repeats."""
    if not 0 <= index < len(paths):
        return []
    result = []
    for step in (1, -1):
        path = paths[(index + step) % len(paths)]
        if path != paths[index] and path not in result:
            result.append(path)
    return result


class DecodeSignals(QObject):
    finished = Signal(str, QImage)  # The path and its decoded image (null if it failed)


class DecodeWorker(QRunnable):
    """Decodes one image on a pool thread. Never touches widgets or QPixmap."""

    def __init__(self, path, max_size):
        super().__init__()
        self.path = path
        self.max_size = max_size
        # QRunnable isn't a QObject, so its signal lives on a separate object
        self.signals = DecodeSignals()

    def run(self):
        self.signals.finished.emit(self.path, decode_image(self.path, self.max_size))
