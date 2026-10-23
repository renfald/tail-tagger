import os
from PySide6.QtWidgets import QFrame, QLabel, QStackedWidget, QVBoxLayout
from PySide6.QtGui import QGuiApplication, QImage, QPixmap
from PySide6.QtCore import QCoreApplication, Qt, QSize, QThreadPool, QTimer, QUrl, Slot
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from tail_tagger.file_operations import FileOperations
from tail_tagger.ui.image_loading import DecodeWorker

DEFAULT_MESSAGE = "No image loaded. Select a folder from the file menu"

class CenterPanel(QFrame):
    RESIZE_SETTLE_MS = 120  # Delay after the last resize event before doing a more expensive smooth rescale
    DECODE_MARGIN = 1.25  # Decode images up to this much bigger than the largest screen

    def __init__(self):
        super().__init__()
        self.media_path = None  # Store path of the currently displayed image/video
        self._source_pixmap = None  # Cached decode of the image on screen
        # False while the grid view covers the panel: it then only remembers media_path
        self._active = True

        # Images decode on one background thread. _wanted lists the paths still to decode,
        # current image first; _decoding is the one in progress.
        self._decode_pool = QThreadPool(self)
        self._decode_pool.setMaxThreadCount(1)
        self._wanted = []
        self._decoding = None
        self._decode_worker = None  # Held until its result arrives, so its signals object stays alive
        self._decoding_mtime = None  # Modified time of the file being decoded, read when the decode started
        # Decoded images kept in memory: the current one plus the neighbors from the last prefetch().
        # Each entry is (file modified time, pixmap); a None pixmap means that path failed to decode.
        self._cache = {}
        # On quit, let a running decode finish first, or it can emit after Qt has deleted its signals object
        QCoreApplication.instance().aboutToQuit.connect(self._wait_for_decode)

        self._message_label = QLabel()
        self._message_label.setAlignment(Qt.AlignCenter)
        self._message_label.setText(DEFAULT_MESSAGE)

        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignCenter)

        self._video_widget = QVideoWidget()
        self._audio_output = QAudioOutput()
        self._audio_output.setMuted(True)  # No playback controls, so keep video silent by default
        self._player = QMediaPlayer(self)
        self._player.setAudioOutput(self._audio_output)
        self._player.setVideoOutput(self._video_widget)
        self._player.setLoops(QMediaPlayer.Infinite)

        self._stack = QStackedWidget(self)
        self._stack.addWidget(self._message_label)
        self._stack.addWidget(self._image_label)
        self._stack.addWidget(self._video_widget)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._stack)

        self.setFocusPolicy(Qt.ClickFocus)

        # Fast-scale immediately for feedback, then do one smooth-scale pass after resizing settles.
        self._smooth_rescale_timer = QTimer(self)
        self._smooth_rescale_timer.setSingleShot(True)
        self._smooth_rescale_timer.setInterval(self.RESIZE_SETTLE_MS)
        self._smooth_rescale_timer.timeout.connect(self._apply_smooth_scale)

    def set_active(self, active, placeholder=None):
        """Starts or stops the panel's work. While inactive (the grid covers it), new media
        is only remembered: nothing decodes and no video plays. Becoming active shows it.

        The picture from before the panel went inactive belongs to a different image, so
        while the remembered image decodes, the panel shows placeholder (e.g. the grid's
        thumbnail, scaled up) or nothing.
        """
        if active == self._active:
            return
        self._active = active
        if not active:
            self._release_video()
            self._wanted = []
        elif self.media_path:
            if not FileOperations.is_video_file(self.media_path) and not self._is_cached(self.media_path):
                self._source_pixmap = placeholder
                self._image_label.clear()
                self._stack.setCurrentWidget(self._image_label)
                self.update_image_display(smooth=False)
            self.set_media_path(self.media_path)

    def set_media_path(self, media_path):
        """Sets the media path (image or video) for the center panel and displays it."""
        self._release_video()
        self.media_path = media_path
        if not self._active:
            self._wanted = []
            return

        if FileOperations.is_video_file(media_path):
            self._wanted = []
            self._source_pixmap = None
            self._stack.setCurrentWidget(self._video_widget)
            self._player.setSource(QUrl.fromLocalFile(media_path))
            self._player.play()
        elif self._is_cached(media_path):
            self._wanted = []
            self._show_decoded(self._cache[media_path][1])
        else:
            # The previous image stays on screen until this one is decoded, which avoids a blank flash
            self._wanted = [media_path]
            self._start_next_decode()

    def prefetch(self, paths):
        """Decodes these images in the background after the current one, and forgets any others."""
        if not self._active:
            return
        current = self.media_path
        if current and FileOperations.is_video_file(current):
            current = None
        paths = [p for p in paths if p != current and not FileOperations.is_video_file(p)]

        keep = set(paths) | {current}
        self._cache = {p: pixmap for p, pixmap in self._cache.items() if p in keep}
        self._wanted = [p for p in [current] + paths if p and not self._is_cached(p)]
        self._start_next_decode()

    def show_media(self, media_path):
        """Shows media_path, or clears the panel when it is None."""
        if media_path:
            self.set_media_path(media_path)
        else:
            self.clear()

    def clear(self):
        """Clears the currently displayed media and shows the default message."""
        self.setText(DEFAULT_MESSAGE)

    def setText(self, text):
        """Shows a message in place of media, e.g. when no files are found."""
        self._release_video()
        self.media_path = None
        self._source_pixmap = None
        self._wanted = []
        self._cache = {}
        self._show_message(text)

    def _release_video(self):
        """Stops playback and clears the source so the video file isn't held open."""
        self._player.stop()
        self._player.setSource(QUrl())

    def _show_message(self, text):
        self._message_label.setText(text)
        self._stack.setCurrentWidget(self._message_label)

    def _decode_box(self):
        """The largest size worth decoding: the biggest screen width and height, in physical pixels, plus a margin."""
        width = height = 0
        for screen in QGuiApplication.screens():
            ratio = screen.devicePixelRatio()
            width = max(width, screen.geometry().width() * ratio)
            height = max(height, screen.geometry().height() * ratio)
        return QSize(round(width * self.DECODE_MARGIN), round(height * self.DECODE_MARGIN))

    def _start_next_decode(self):
        """Starts decoding the first wanted path, unless a decode is already running."""
        if self._decoding is not None or not self._wanted:
            return
        self._decoding = self._wanted[0]
        self._decoding_mtime = self._modified_time(self._decoding)
        self._decode_worker = DecodeWorker(self._decoding, self._decode_box())
        self._decode_worker.signals.finished.connect(self._on_decoded)
        self._decode_pool.start(self._decode_worker)

    @staticmethod
    def _modified_time(path):
        try:
            return os.path.getmtime(path)
        except OSError:
            return None

    def _is_cached(self, path):
        """True when path has a cached decode and the file hasn't changed since it was read."""
        # Checking the modified time means an image edited elsewhere, or one that failed
        # because it was still being copied, gets decoded again instead of shown stale
        entry = self._cache.get(path)
        return entry is not None and entry[0] == self._modified_time(path)

    def _wait_for_decode(self):
        self._decode_pool.waitForDone()

    @Slot(str, QImage)
    def _on_decoded(self, path, image):
        """Caches a finished decode, shows it if it is the current image, then starts the next one."""
        mtime = self._decoding_mtime
        self._decoding = None
        self._decode_worker = None
        # A path no longer wanted means the user moved on, or the panel was cleared, while it decoded
        if path in self._wanted:
            self._wanted.remove(path)
            pixmap = None if image.isNull() else QPixmap.fromImage(image)
            self._cache[path] = (mtime, pixmap)
            if path == self.media_path:
                self._show_decoded(pixmap)
        self._start_next_decode()

    def _show_decoded(self, pixmap):
        """Shows a decoded image, or the error message when the decode failed (pixmap is None)."""
        self._source_pixmap = pixmap
        if pixmap is None:
            self._show_message("Error loading image")
        else:
            self._stack.setCurrentWidget(self._image_label)
            self.update_image_display()

    def resizeEvent(self, event):
        """Handles resize events to scale and display the image."""
        super().resizeEvent(event) # Important: Call base class implementation first
        if self._stack.currentWidget() is self._image_label:
            self.update_image_display(smooth=False)
            self._smooth_rescale_timer.start() # restart(): coalesces to one smooth pass after resizing settles

    def _apply_smooth_scale(self):
        """Timer callback: replaces the fast preview with a smooth-scaled pixmap."""
        self.update_image_display(smooth=True)

    def update_image_display(self, smooth=True):
        """Scales the cached image to fit the center panel."""
        if self._source_pixmap is None:
            return

        mode = Qt.TransformationMode.SmoothTransformation if smooth else Qt.TransformationMode.FastTransformation
        scaled_pixmap = self._source_pixmap.scaled(
            self._image_label.width(),
            self._image_label.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            mode
        )
        self._image_label.setPixmap(scaled_pixmap)
