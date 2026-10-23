"""Thumbnails for the grid view: decoded on demand on a small thread pool into a capped cache."""
from collections import OrderedDict

from PySide6.QtCore import QCoreApplication, QObject, QSize, QThreadPool, Signal, Slot
from PySide6.QtGui import QImage, QPixmap

from tail_tagger.file_operations import FileOperations
from tail_tagger.ui.image_loading import DecodeWorker

THUMB_DECODE_SIZE = QSize(350, 350)  # Thumbnails are decoded once at this size; the grid scales them to draw
CACHE_LIMIT = 300  # Thumbnails kept in memory; the least recently used are dropped first

FAILED = object()  # Cached for a path that could not be decoded, so it isn't tried again


class ThumbnailCache:
    """A dict-like store that keeps at most limit entries, dropping the least recently used."""

    def __init__(self, limit):
        self.limit = limit
        self._items = OrderedDict()

    def get(self, path):
        """The value for path, or None. Marks path as the most recently used."""
        if path not in self._items:
            return None
        self._items.move_to_end(path)
        return self._items[path]

    def put(self, path, value):
        self._items[path] = value
        self._items.move_to_end(path)
        while len(self._items) > self.limit:
            self._items.popitem(last=False)

    def clear(self):
        self._items.clear()

    def __len__(self):
        return len(self._items)

    def __contains__(self, path):
        return path in self._items


class ThumbnailLoader(QObject):
    """Decodes the thumbnails the grid asks for, a few at a time, and announces each one."""

    ready = Signal(str)  # A path whose thumbnail (or FAILED) is now in the cache

    def __init__(self, threads=2, parent=None):
        super().__init__(parent)
        self.threads = threads
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(threads)
        self._cache = ThumbnailCache(CACHE_LIMIT)
        self._wanted = []  # Paths still to decode, most wanted first
        self._running = {}  # Path -> DecodeWorker, held until its result arrives so its signals object stays alive
        # Workers still running for paths that were dropped by reset(); their results are ignored
        self._retired = []
        # On quit, let running decodes finish first, or they can emit after Qt has deleted their signals objects
        QCoreApplication.instance().aboutToQuit.connect(self._pool.waitForDone)

    def thumbnail(self, path):
        """The cached thumbnail QPixmap, FAILED, or None when it hasn't been decoded (videos never are)."""
        return self._cache.get(path)

    def request(self, paths):
        """Replaces the paths to decode with these, in this order. Videos and cached paths are skipped."""
        self._wanted = [p for p in paths if p not in self._cache and p not in self._running
                        and not FileOperations.is_video_file(p)]
        self._start_next()

    def reset(self):
        """Forgets every thumbnail and queued path, e.g. when a different folder opens."""
        self._wanted = []
        self._cache.clear()
        self._retired.extend(self._running.values())
        self._running = {}

    def _start_next(self):
        while self._wanted and len(self._running) < self.threads:
            path = self._wanted.pop(0)
            worker = DecodeWorker(path, THUMB_DECODE_SIZE)
            worker.signals.finished.connect(self._on_decoded)
            self._running[path] = worker
            self._pool.start(worker)

    @Slot(str, QImage)
    def _on_decoded(self, path, image):
        # Runs on the UI thread (queued from the worker), so creating a QPixmap here is safe
        signals = self.sender()
        worker = self._running.get(path)
        if worker is not None and worker.signals is signals:
            del self._running[path]
            self._cache.put(path, FAILED if image.isNull() else QPixmap.fromImage(image))
            self.ready.emit(path)
        else:
            # A decode that was running when reset() was called
            self._retired = [w for w in self._retired if w.signals is not signals]
        self._start_next()
