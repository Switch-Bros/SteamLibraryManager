# src/ui/components/clickable_image.py

"""
A custom widget to display clickable and dynamically loaded images.

This widget can load images from local paths or URLs in a separate thread,
supports animated GIFs (if Pillow is installed), and can display
superimposed badges based on metadata.
"""
from PyQt6.QtWidgets import QLabel, QWidget, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QByteArray, QTimer
from PyQt6.QtGui import QPixmap, QCursor, QImage
import requests
import os
import io
from src.config import config
from src.utils.i18n import t

try:
    from PIL import Image, ImageSequence

    HAS_PILLOW = True
except ImportError:
    Image = None
    ImageSequence = None
    HAS_PILLOW = False
    print(t('logs.image.pillow_missing'))


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
                with open(self.url_or_path, 'rb') as f:
                    data = QByteArray(f.read())
            elif str(self.url_or_path).startswith('http'):
                headers = {'User-Agent': 'SteamLibraryManager/1.0'}
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
    """A widget that displays an image and emits signals on clicks."""
    clicked = pyqtSignal()
    right_clicked = pyqtSignal()

    def __init__(self, parent_or_text=None, width: int = 200, height: int = 300, metadata: dict = None):
        """
        Initializes the ClickableImage widget.

        Args:
            parent_or_text: The parent widget or a text string (legacy parameter).
            width (int): The fixed width of the widget.
            height (int): The fixed height of the widget.
            metadata (dict): Optional metadata dictionary for badge display.
        """
        parent = parent_or_text if not isinstance(parent_or_text, str) else None
        super().__init__(parent)
        self.w = width
        self.h = height
        self.metadata = metadata

        self.setFixedSize(width, height)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("border: 1px solid #FDE100; background-color: #1b2838;")
        self.image_label.setFixedSize(width, height)
        self.image_label.setScaledContents(False)
        layout.addWidget(self.image_label)

        self.badge_layout = QHBoxLayout(self.image_label)
        self.badge_layout.setContentsMargins(5, 5, 5, 5)
        self.badge_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.badge_layout.setSpacing(4)

        self.default_image = None
        self.current_path = None
        self.loader = None

        self.frames = []
        self.durations = []
        self.current_frame = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._next_frame)

        self.badges = []

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

    def load_image(self, url_or_path: str | None, metadata: dict = None):
        """Starts loading an image from a URL or local path.

        Args:
            url_or_path (str | None): The URL or file path of the image to load, or None to clear.
            metadata (dict): Optional metadata for badge display.
        """
        if metadata is not None:
            self.metadata = metadata

        self.current_path = url_or_path
        self.timer.stop()
        self.frames = []
        self._clear_badges()

        # PERFORMANCE: Check cache first
        if url_or_path and url_or_path in self._pixmap_cache:
            cached_pixmap = self._pixmap_cache[url_or_path]
            if not cached_pixmap.isNull():
                self._apply_pixmap(cached_pixmap)
                self._create_badges(is_animated=False)
                return

        if self.loader and self.loader.isRunning():
            self.loader.stop()
            self.loader.wait()

        self.image_label.setText(t('ui.loading.dots'))

        self.loader = ImageLoader(url_or_path)
        self.loader.loaded.connect(self._on_loaded)
        self.loader.start()

    def _on_loaded(self, data: QByteArray):
        """Handles the loaded image data, parsing it with Pillow if available."""
        if data.isEmpty():
            if self.default_image:
                self._load_local_image(self.default_image)
            else:
                # Use centralised error emoji — image_load_error key removed
                self.image_label.setText(t('emoji.error'))
            return

        if HAS_PILLOW:
            try:
                img_data = io.BytesIO(data.data())
                im = Image.open(img_data)
                is_animated = getattr(im, "is_animated", False)

                if is_animated:
                    self.frames = []
                    self.durations = []
                    for frame in ImageSequence.Iterator(im):
                        frame = frame.convert("RGBA")
                        qim = QImage(frame.tobytes("raw", "RGBA"), frame.width, frame.height,
                                     QImage.Format.Format_RGBA8888)
                        self.frames.append(QPixmap.fromImage(qim))
                        self.durations.append(frame.info.get('duration', 100))
                    if self.frames:
                        self._start_animation()
                        self._create_badges(is_animated=True)
                        return
                else:
                    im = im.convert("RGBA")
                    qimg = QImage(im.tobytes("raw", "RGBA"), im.width, im.height, QImage.Format.Format_RGBA8888)
                    self._apply_pixmap(QPixmap.fromImage(qimg))
                    self._create_badges(is_animated=False)
                    return
            except (IOError, ValueError):
                pass  # Fallback to standard QPixmap loading

        pixmap = QPixmap()
        pixmap.loadFromData(data)
        if not pixmap.isNull():
            self._apply_pixmap(pixmap)
            self._create_badges(is_animated=False)
        else:
            if self.default_image:
                self._load_local_image(self.default_image)
            else:
                self.image_label.setText(t('emoji.error'))

    def _start_animation(self):
        """Starts or restarts the GIF animation."""
        if not self.frames:
            return
        self.current_frame = 0
        self._show_frame(0)
        self.timer.start(self.durations[0])

    def _next_frame(self):
        """Advances to the next frame of the animation."""
        if not self.frames:
            return
        self.current_frame = (self.current_frame + 1) % len(self.frames)
        self._show_frame(self.current_frame)
        self.timer.start(self.durations[self.current_frame])

    def _show_frame(self, index: int):
        """Displays a specific frame of the animation."""
        if 0 <= index < len(self.frames):
            self._apply_pixmap(self.frames[index])

    def _apply_pixmap(self, pixmap: QPixmap):
        """Scales and sets the pixmap on the label."""
        scaled = pixmap.scaled(self.w, self.h, Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
        self.image_label.setPixmap(scaled)

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

    def _create_badges(self, is_animated: bool = False):
        """
        Creates and displays badges based on game metadata.

        Badges are displayed in the top-left corner of the image. They can be
        either custom PNG icons or text labels with colored backgrounds.

        Args:
            is_animated (bool): Whether the loaded image is an animated GIF.
        """
        self._clear_badges()
        if not self.metadata:
            return

        tags = self.metadata.get('tags', [])

        def add_badge(type_key: str, text: str, bg_color: str = "#000000"):
            """Helper function to add a badge (icon or text)."""
            icon_path = config.ICONS_DIR / f"flag_{type_key}.png"
            if icon_path.exists():
                lbl = QLabel()
                pix = QPixmap(str(icon_path)).scaledToHeight(24, Qt.TransformationMode.SmoothTransformation)
                lbl.setPixmap(pix)
                lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
                self.badge_layout.addWidget(lbl)
                self.badges.append(lbl)
            else:
                # Fallback to text badge
                lbl = QLabel(text)
                lbl.setStyleSheet(
                    f"background-color: {bg_color}; color: white; padding: 3px 6px; border-radius: 4px; font-weight: bold; font-size: 10px; border: 1px solid rgba(255,255,255,0.3);")
                lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
                self.badge_layout.addWidget(lbl)
                self.badges.append(lbl)

        if self.metadata.get('nsfw') or 'nsfw' in tags:
            add_badge('nsfw', f"{t('emoji.nsfw')} {t('ui.badges.nsfw')}", "#d9534f")
        if self.metadata.get('humor') or 'humor' in tags:
            add_badge('humor', f"{t('emoji.humor')} {t('ui.badges.humor')}", "#f0ad4e")
        if self.metadata.get('epilepsy') or 'epilepsy' in tags:
            add_badge('epilepsy', f"{t('emoji.epilepsy')} {t('ui.badges.epilepsy')}", "#0275d8")
        if is_animated:
            add_badge('animated', f"{t('emoji.animated')} {t('ui.badges.animated')}", "#5cb85c")

    def _clear_badges(self):
        """Removes all current badges from the layout."""
        for b in self.badges:
            self.badge_layout.removeWidget(b)
            b.deleteLater()
        self.badges = []

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
