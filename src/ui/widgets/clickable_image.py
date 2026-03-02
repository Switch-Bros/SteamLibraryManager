# src/ui/components/clickable_image.py

"""
A custom widget to display clickable and dynamically loaded images.

This widget can load images from local paths or URLs in a separate thread,
supports animated GIFs (if Pillow is installed), and can display
superimposed badges based on metadata via ImageBadgeOverlay.
"""

from __future__ import annotations

__all__ = ["ClickableImage", "ImageLoader"]

import io
import logging
import os

import requests
from PyQt6.QtCore import QByteArray, Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QCursor, QImage, QPixmap
from PyQt6.QtWidgets import QLabel, QWidget

from src.ui.theme import Theme
from src.ui.widgets.image_badge_overlay import ImageBadgeOverlay
from src.utils.i18n import t

logger = logging.getLogger("steamlibmgr.clickable_image")

try:
    from PIL import Image, ImageSequence

    HAS_PILLOW = True
except ImportError:
    Image = None
    ImageSequence = None
    HAS_PILLOW = False
    logger.info(t("logs.image.pillow_missing"))


class ImageLoader(QThread):
    """A QThread to load image data from a path or URL without blocking the GUI."""

    loaded = pyqtSignal(QByteArray)

    def __init__(self, url_or_path: str):
        """
        Initializes the ImageLoader.

        Args:
            url_or_path (str): The URL or local file path to load the image from.
        """
        super().__init__()
        self.url_or_path = url_or_path
        self._is_running = True

    def run(self):
        """Loads image data and emits it via the loaded signal."""
        data = QByteArray()
        try:
            if not self.url_or_path:
                self.loaded.emit(data)
                return

            if os.path.exists(self.url_or_path):
                with open(self.url_or_path, "rb") as f:
                    data = QByteArray(f.read())
            elif str(self.url_or_path).startswith("http"):
                headers = {"User-Agent": "SteamLibraryManager/1.0"}
                response = requests.get(self.url_or_path, headers=headers, timeout=10)
                response.raise_for_status()
                data = QByteArray(response.content)
        except (OSError, ValueError, requests.RequestException):
            pass  # Fail silently, the UI will handle the empty data

        if self._is_running:
            self.loaded.emit(data)

    def stop(self):
        """Stops the thread from emitting the loaded signal if it's no longer needed."""
        self._is_running = False


class ClickableImage(QWidget):
    """A widget that displays an image and emits signals on clicks.

    Signals:
        clicked: Emitted on left click.
        right_clicked: Emitted on right click.
        load_finished: Emitted when image loading completes (success or failure).
    """

    clicked = pyqtSignal()
    right_clicked = pyqtSignal()
    load_finished = pyqtSignal()

    def __init__(
        self,
        parent_or_text=None,
        width: int = 200,
        height: int = 300,
        metadata: dict = None,
        external_badges: bool = False,
    ):
        """
        Initializes the ClickableImage widget.

        Args:
            parent_or_text: The parent widget or a text string (legacy parameter).
            width (int): The fixed width of the widget.
            height (int): The fixed height of the widget.
            metadata (dict): Optional metadata dictionary for badge display.
            external_badges (bool): If True, badge system is managed externally.
        """
        parent = parent_or_text if not isinstance(parent_or_text, str) else None
        super().__init__(parent)
        self.w = width
        self.h = height
        self.metadata = metadata
        self.external_badges = external_badges

        # Widget keeps ORIGINAL size — badge area extends UPWARDS!
        # This prevents gaps in the layout
        self.setFixedSize(width, height)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        # image_label — fills the entire widget (as before)
        # Generation counter — incremented on every load_image() call.
        # _on_loaded() checks this to discard stale results from previous loads.
        self._load_generation: int = 0

        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet(f"border: 1px solid {Theme.PEGI_HOVER}; background-color: {Theme.BG_PRIMARY};")
        self.image_label.setGeometry(0, 0, width, height)
        self.image_label.setScaledContents(False)
        # Pass through mouse events so enterEvent/leaveEvent work on self
        self.image_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # Badge overlay system (SteamGridDB-style)
        self._badge_overlay: ImageBadgeOverlay | None = ImageBadgeOverlay(self, width) if not external_badges else None

        self.default_image = None
        self.current_path = None
        self.loader = None

        self.frames = []
        self.durations = []
        self.current_frame = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._next_frame)

        # PERFORMANCE: Cache for loaded pixmaps
        self._pixmap_cache = {}  # {path: QPixmap}

    def set_default_image(self, path: str):
        """
        Sets a default image to show if the primary image fails to load.

        Args:
            path (str): The path to the default image file.
        """
        self.default_image = path
        if not self.current_path:
            self._load_local_image(path)

    @staticmethod
    def _is_animated_pillow(im) -> bool:
        """Checks if a Pillow image is animated (APNG, GIF, WEBP) using seek fallback.

        Args:
            im: The Pillow Image object.

        Returns:
            bool: True if animated, False otherwise.
        """
        # 1. Standard check (GIF, WEBP often set this)
        if getattr(im, "is_animated", False):
            return True

        # 2. Fallback check (APNG detection via seeking)
        try:
            im.seek(1)  # Try to go to 2nd frame
            im.seek(0)  # Reset to 1st frame
            return True
        except (EOFError, ValueError):
            return False

    @staticmethod
    def _pillow_to_pixmap(pil_image) -> QPixmap:
        """Converts a Pillow Image to QPixmap via RGBA conversion.

        Args:
            pil_image: A PIL/Pillow Image object.

        Returns:
            QPixmap created from the converted image data.
        """
        frame = pil_image.convert("RGBA")
        img_bytes = frame.tobytes("raw", "RGBA")
        qim = QImage(img_bytes, frame.width, frame.height, QImage.Format.Format_RGBA8888)
        return QPixmap.fromImage(qim)

    def load_image(self, url_or_path: str | None, metadata: dict = None):
        """Starts loading an image from a URL or local path.

        Supports images (PNG, JPG, GIF, WEBP, APNG). Animated formats are
        handled via Pillow. WEBM videos show the default placeholder.

        Args:
            url_or_path (str | None): The URL or file path of the image to load, or None to clear.
            metadata (dict): Optional metadata for badge display.
        """
        if metadata is not None:
            self.metadata = metadata

        self.current_path = url_or_path
        self._load_generation += 1
        self.timer.stop()
        self.frames = []
        self._clear_badges()

        # If url_or_path is None, load default image immediately without showing loading text
        if url_or_path is None:
            if self.default_image:
                self._load_local_image(self.default_image)
            return

        # WEBM videos can't be displayed as images — show default
        if url_or_path and url_or_path.lower().endswith(".webm"):
            if self.default_image:
                self._load_local_image(self.default_image)
            else:
                self.image_label.setText(t("emoji.no_image"))
            self.load_finished.emit()
            return

        # PERFORMANCE: Check cache first
        if url_or_path and url_or_path in self._pixmap_cache:
            cached_pixmap = self._pixmap_cache[url_or_path]
            if not cached_pixmap.isNull():
                self._apply_pixmap(cached_pixmap)
                self._create_badges(is_animated=False)
                self.load_finished.emit()
                return

        if self.loader and self.loader.isRunning():
            self.loader.stop()
            self.loader.wait()

        self.image_label.setText(t("common.loading"))

        # Capture generation so the callback can detect stale results
        gen = self._load_generation
        self.loader = ImageLoader(url_or_path)
        self.loader.loaded.connect(lambda data, g=gen: self._on_loaded(data, g))
        self.loader.start()

    def _on_loaded(self, data: QByteArray, generation: int = -1):
        """Handles the loaded image data, parsing it with Pillow if available.

        Discards stale results from previous load_image() calls to prevent
        race conditions when clicking rapidly between games.

        Args:
            data: The raw image bytes.
            generation: Load generation counter.  If it doesn't match the
                current generation, the result is stale and discarded.
        """
        # Stale result — a newer load_image() call has been made since this one started
        if generation != -1 and generation != self._load_generation:
            return

        if data.isEmpty():
            if self.default_image:
                self.current_path = None  # Reset to prevent caching default image under wrong path
                self._load_local_image(self.default_image)
            else:
                self.image_label.setText(t("emoji.error"))
            self.load_finished.emit()
            return

        # 1. Attempt to load with Pillow (for Animations)
        if HAS_PILLOW:
            try:
                # Keep bytes alive!
                raw_bytes = data.data()
                img_data = io.BytesIO(raw_bytes)
                im = Image.open(img_data)

                if self._is_animated_pillow(im):
                    self.frames = []
                    self.durations = []

                    for frame in ImageSequence.Iterator(im):
                        self.frames.append(self._pillow_to_pixmap(frame))
                        self.durations.append(frame.info.get("duration", 100))

                    if self.frames:
                        self._start_animation()
                        self._create_badges(is_animated=True)
                        self.load_finished.emit()
                        return
                else:
                    # Static image via Pillow
                    self._apply_pixmap(self._pillow_to_pixmap(im))
                    self._create_badges(is_animated=False)
                    self.load_finished.emit()
                    return

            # Fix: Catch specific exceptions (Fixes 'Too broad exception clause')
            except (IOError, ValueError, TypeError, EOFError) as e:
                logger.error(t("logs.image.pillow_fallback", error=e))

        # 2. Fallback: Standard Qt Loading
        pixmap = QPixmap()
        pixmap.loadFromData(data)

        if not pixmap.isNull():
            self._apply_pixmap(pixmap)
            self._create_badges(is_animated=False)
        else:
            if self.default_image:
                self._load_local_image(self.default_image)
            else:
                self.image_label.setText(t("emoji.error"))
        self.load_finished.emit()

    def _start_animation(self):
        """Starts or restarts the GIF animation."""
        if not self.frames:
            return
        self.current_frame = 0
        self._show_frame(0)
        self.timer.start(int(self.durations[0]))  # Convert to int!

    def _next_frame(self):
        """Advances to the next frame of the animation."""
        if not self.frames:
            return
        self.current_frame = (self.current_frame + 1) % len(self.frames)
        self._show_frame(self.current_frame)
        self.timer.start(int(self.durations[self.current_frame]))  # Convert to int!

    def _show_frame(self, index: int):
        """Displays a specific frame of the animation."""
        if 0 <= index < len(self.frames):
            self._apply_pixmap(self.frames[index])

    def _apply_pixmap(self, pixmap: QPixmap):
        """Scales and sets the pixmap on the label."""
        scaled = pixmap.scaled(
            self.w, self.h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        self.image_label.setPixmap(scaled)
        if self._badge_overlay:
            self._badge_overlay.raise_()

        # PERFORMANCE: Cache the original pixmap for future reuse
        if self.current_path and self.current_path not in self._pixmap_cache:
            self._pixmap_cache[self.current_path] = pixmap

    def _load_local_image(self, path: str):
        """Directly loads an image from a local path."""
        if os.path.exists(path):
            self._apply_pixmap(QPixmap(path))

    def mousePressEvent(self, event):
        """Emits signals for left and right clicks."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        elif event.button() == Qt.MouseButton.RightButton:
            self.right_clicked.emit()

    def enterEvent(self, event):
        """Triggers badge expansion animation on mouse enter."""
        super().enterEvent(event)
        if self._badge_overlay:
            self._badge_overlay.expand()

    def leaveEvent(self, event):
        """Triggers badge collapse animation on mouse leave."""
        super().leaveEvent(event)
        if self._badge_overlay:
            self._badge_overlay.collapse()

    def _create_badges(self, is_animated: bool = False):
        """Creates badges on the overlay from current metadata."""
        if self._badge_overlay:
            self._badge_overlay.create_badges(self.metadata, is_animated)

    def _clear_badges(self):
        """Removes all badges and resets the overlay."""
        if self._badge_overlay:
            self._badge_overlay.clear_badges()

    def clear(self):
        """
        Clears the image and shows the default image or empty state.

        This method is useful when you want to reset the widget to its initial state,
        such as when clearing a multi-selection view.
        """
        self.timer.stop()
        self.frames = []
        self.current_path = None
        self._clear_badges()

        if self.default_image:
            self._load_local_image(self.default_image)
        else:
            self.image_label.clear()
            self.image_label.setText("")
