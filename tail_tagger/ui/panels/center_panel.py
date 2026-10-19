from PySide6.QtWidgets import QFrame, QLabel, QStackedWidget, QVBoxLayout
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from tail_tagger.file_operations import FileOperations

DEFAULT_MESSAGE = "No image loaded. Select a folder from the file menu"

class CenterPanel(QFrame):
    RESIZE_SETTLE_MS = 120  # Delay after the last resize event before doing a more expensive smooth rescale

    def __init__(self):
        super().__init__()
        self.media_path = None  # Store path of the currently displayed image/video
        self._source_pixmap = None  # Cached decode of media_path, for images

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

    def set_media_path(self, media_path):
        """Sets the media path (image or video) for the center panel and displays it."""
        self._release_video()
        self.media_path = media_path

        if FileOperations.is_video_file(media_path):
            self._source_pixmap = None
            self._stack.setCurrentWidget(self._video_widget)
            self._player.setSource(QUrl.fromLocalFile(media_path))
            self._player.play()
        else:
            self._load_source_pixmap()
            if self._source_pixmap is None:
                self._show_message("Error loading image")
            else:
                self._stack.setCurrentWidget(self._image_label)
                self.update_image_display()

    def clear(self):
        """Clears the currently displayed media and shows the default message."""
        self._release_video()
        self.media_path = None
        self._source_pixmap = None
        self._show_message(DEFAULT_MESSAGE)

    def setText(self, text):
        """Shows a message in place of media, e.g. when no files are found."""
        self._release_video()
        self.media_path = None
        self._source_pixmap = None
        self._show_message(text)

    def _release_video(self):
        """Stops playback and clears the source so the video file isn't held open."""
        self._player.stop()
        self._player.setSource(QUrl())

    def _show_message(self, text):
        self._message_label.setText(text)
        self._stack.setCurrentWidget(self._message_label)

    def _load_source_pixmap(self):
        """Decodes media_path once and caches the result."""
        if not self.media_path:
            self._source_pixmap = None
            return

        pixmap = QPixmap(self.media_path)
        self._source_pixmap = pixmap if not pixmap.isNull() else None

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
