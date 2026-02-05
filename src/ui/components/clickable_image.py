# src/ui/components/clickable_image.py

"""
A custom widget to display clickable and dynamically loaded images.

This widget can load images from local paths or URLs in a separate thread,
supports animated GIFs/APNGs (if Pillow is installed), WEBM videos (via QMediaPlayer),
and can display superimposed badges based on metadata.
"""
from PyQt6.QtWidgets import QLabel, QWidget, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QByteArray, QTimer, QPropertyAnimation, QEasingCurve, QRect, QUrl
from PyQt6.QtGui import QPixmap, QCursor, QImage
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from typing import cast
import requests
import os
os.environ['QT_LOGGING_RULES'] = 'qt.multimedia.ffmpeg=false'
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

    def __init__(self, parent_or_text=None, width: int = 200, height: int = 300,
                 metadata: dict = None, external_badges: bool = False):
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

        # Widget behält ORIGINALE Größe — Badge-Area ragt nach OBEN raus!
        # So entsteht KEINE Lücke im Layout
        self.setFixedSize(width, height)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        # image_label — füllt das ganze Widget aus (wie vorher)
        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("border: 1px solid #FDE100; background-color: #1b2838;")
        self.image_label.setGeometry(0, 0, width, height)
        self.image_label.setScaledContents(False)
        # Mouse-Events durchlassen damit enterEvent/leaveEvent auf self funktionieren
        self.image_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # Video widget for WEBM support (initially hidden)
        self.video_widget = QVideoWidget(self)
        self.video_widget.setGeometry(1, 1, width - 2, height - 2)  # Fit inside border
        self.video_widget.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)  # WICHTIG!
        self.video_widget.hide()
        self.video_widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # Media player for WEBM
        self.media_player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.audio_output.setVolume(0)  # Mute videos
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_widget)
        self.media_player.setLoops(QMediaPlayer.Loops.Infinite)  # Loop forever

        # --- Badge-Overlay System (SteamGridDB-Style) ---
        # NUR erstellen wenn external_badges=False!
        if not external_badges:
            # LIPPE: Dünner 5px Streifen AUF dem gelben Rahmen
            # ICON: 28×28px Badge das bei Hover darunter ausfährt
            self._STRIPE_HEIGHT: int = 5  # Dünne Lippe (wie bei SteamGridDB!)
            self._ICON_HEIGHT: int = 28  # Icon-Höhe
            self._BADGE_GAP: int = 2  # Abstand zwischen Lippe und Icon
            self._EXPANDED_HEIGHT: int = (  # Gesamthöhe wenn expandiert
                    self._STRIPE_HEIGHT + self._BADGE_GAP + self._ICON_HEIGHT
            )
            self._STRIPE_WIDTH: int = 28  # Icon-Breite
            self._STRIPE_GAP: int = 2  # Spalt zwischen mehreren Badges

            # Overlay-Container — sitzt bei y=-6 ÜBER dem Widget
            # HÖHE muss _EXPANDED_HEIGHT sein (35px) damit Icon ausfährt!
            # Die DÜNNE Lippe (5px) sitzt KOMPLETT ÜBER dem Bild (1px extra!)
            self.badge_overlay = QWidget(self)
            self.badge_overlay.setGeometry(0, -6, width, self._EXPANDED_HEIGHT)
            self.badge_overlay.raise_()
            self.badge_overlay.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

            overlay_layout = QVBoxLayout(self.badge_overlay)
            overlay_layout.setContentsMargins(5, 0, 0, 0)
            overlay_layout.setSpacing(self._BADGE_GAP)  # 1px Gap zwischen Lippe und Icon
            overlay_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

            # Streifen-Reihe — immer sichtbar (die 5px hohen farbigen Streifen)
            self.stripe_container = QWidget()
            stripe_layout = QHBoxLayout(self.stripe_container)
            stripe_layout.setContentsMargins(0, 0, 0, 0)
            stripe_layout.setSpacing(self._STRIPE_GAP)
            stripe_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
            self.stripe_container.setFixedHeight(self._STRIPE_HEIGHT)
            overlay_layout.addWidget(self.stripe_container)

            # Icon-Reihe — nur bei Hover sichtbar (die echten Badge-Icons)
            self.icon_container = QWidget()
            icon_layout = QHBoxLayout(self.icon_container)
            icon_layout.setContentsMargins(0, 0, 0, 0)
            icon_layout.setSpacing(self._STRIPE_GAP)
            icon_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
            overlay_layout.addWidget(self.icon_container)

            # Animation für das Overlay — animiert maximumHeight zwischen kollabiert und expandiert
            # Animation auf "geometry" — funktioniert bei absolut-positionierten Widgets
            # (maximumHeight wird bei setGeometry-Widgets vom Layout ignoriert)
            self.badge_animation = QPropertyAnimation(self.badge_overlay, b"geometry")
            self.badge_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            self.badge_animation.setDuration(180)  # ms — schnell aber nicht instant

            # Badge-Zustand
            self._badge_colors: list[str] = []  # Farben pro Badge (für die Streifen)
            self.badges: list[QWidget] = []  # Badge-Icon Widgets
        else:
            # External badges — setze dummy values
            self._STRIPE_HEIGHT = 0
            self._ICON_HEIGHT = 0
            self._EXPANDED_HEIGHT = 0
            self._STRIPE_WIDTH = 0
            self._STRIPE_GAP = 0
            self.badge_overlay = None
            self.stripe_container = None
            self.icon_container = None
            self.badge_animation = None
            self._badge_colors = []
            self.badges = []

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

    def load_image(self, url_or_path: str | None, metadata: dict = None):
        """Starts loading an image from a URL or local path.

        Supports images (PNG, JPG, GIF, WEBP, APNG) and videos (WEBM).

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

        # Stop any playing video
        self.media_player.stop()
        self.video_widget.hide()
        self.image_label.show()

        # Check if this is a WEBM video
        if url_or_path and url_or_path.lower().endswith('.webm'):
            self._load_webm_video(url_or_path)
            return

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

    def _load_webm_video(self, url: str):
        """Loads and plays a WEBM video.

        Args:
            url (str): The URL of the WEBM video to load.
        """
        self.image_label.hide()
        self.video_widget.show()
        self.video_widget.raise_()

        # Raise badges above video if they exist
        if self.badge_overlay:
            self.badge_overlay.raise_()

        self.media_player.setSource(QUrl(url))
        self.media_player.play()

        # Create animated badge for WEBM
        self._create_badges(is_animated=True)

    def _on_loaded(self, data: QByteArray):
        """Handles the loaded image data, parsing it with Pillow if available.

        Robust handling for animations (APNG, WEBP, GIF) and fallback to Qt
        to avoid red crosses or crashes.
        """
        if data.isEmpty():
            if self.default_image:
                self._load_local_image(self.default_image)
            else:
                self.image_label.setText(t('emoji.error'))
            return

        # 1. Attempt to load with Pillow (for Animations)
        if HAS_PILLOW:
            try:
                # Keep bytes alive!
                raw_bytes = data.data()
                img_data = io.BytesIO(raw_bytes)
                im = Image.open(img_data)

                # Use the static helper method (fixes 'static' warning)
                if self._is_animated_pillow(im):
                    self.frames = []
                    self.durations = []

                    for frame in ImageSequence.Iterator(im):
                        # Ensure RGBA mode
                        frame = frame.convert("RGBA")

                        # Save bytes to variable (Fixes garbage collection issue)
                        img_bytes = frame.tobytes("raw", "RGBA")

                        qim = QImage(
                            img_bytes,
                            frame.width,
                            frame.height,
                            QImage.Format.Format_RGBA8888
                        )

                        self.frames.append(QPixmap.fromImage(qim))
                        self.durations.append(frame.info.get('duration', 100))

                    if self.frames:
                        self._start_animation()
                        self._create_badges(is_animated=True)
                        return
                else:
                    # Static image via Pillow
                    im = im.convert("RGBA")
                    # CRITICAL FIX: Save bytes here too!
                    img_bytes = im.tobytes("raw", "RGBA")

                    qim = QImage(
                        img_bytes,
                        im.width,
                        im.height,
                        QImage.Format.Format_RGBA8888
                    )
                    self._apply_pixmap(QPixmap.fromImage(qim))
                    self._create_badges(is_animated=False)
                    return

            # Fix: Catch specific exceptions (Fixes 'Too broad exception clause')
            except (IOError, ValueError, TypeError, EOFError) as e:
                print(f"[ClickableImage] Pillow load failed (fallback to Qt): {e}")

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
            pixmap = self.frames[index]
            scaled = pixmap.scaled(
                self.w, self.h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.setPixmap(scaled)

    def _apply_pixmap(self, pixmap: QPixmap):
        """Applies a pixmap to the image label with scaling."""
        if pixmap.isNull():
            return
        scaled = pixmap.scaled(
            self.w, self.h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.image_label.setPixmap(scaled)

        # PERFORMANCE: Cache the pixmap
        if self.current_path:
            self._pixmap_cache[self.current_path] = pixmap

    def _load_local_image(self, path: str):
        """Loads an image from a local file path."""
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            self._apply_pixmap(pixmap)
        else:
            self.image_label.setText(t('emoji.error'))

    def mousePressEvent(self, event):
        """Handles mouse press events."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        elif event.button() == Qt.MouseButton.RightButton:
            self.right_clicked.emit()

    def enterEvent(self, event):
        """Handles mouse enter events for badge animation."""
        super().enterEvent(event)
        if not self.external_badges and self.badge_overlay:
            self._animate_overlay(self._EXPANDED_HEIGHT)

    def leaveEvent(self, event):
        """Handles mouse leave events for badge animation."""
        super().leaveEvent(event)
        if not self.external_badges and self.badge_overlay:
            self._animate_overlay(self._STRIPE_HEIGHT)

    def _animate_overlay(self, target_height: int):
        """Animates the badge overlay to a target height.

        Args:
            target_height (int): The target height for the overlay animation.
        """
        if not self.badge_overlay or not self.badge_animation:
            return

        current_geo = self.badge_overlay.geometry()
        target_geo = QRect(
            current_geo.x(),
            -6,  # Y bleibt konstant
            current_geo.width(),
            target_height
        )

        self.badge_animation.stop()
        self.badge_animation.setStartValue(current_geo)
        self.badge_animation.setEndValue(target_geo)
        self.badge_animation.start()

    def _create_badges(self, is_animated: bool = False):
        """
        Creates and displays badges based on game metadata.

        Badges are displayed in the top-left corner of the image. They can be
        either custom PNG icons or text labels with colored backgrounds.

        Args:
            is_animated (bool): Whether the loaded image is an animated GIF.
        """
        if self.external_badges:
            return  # Badges werden extern verwaltet

        self._clear_badges()

        if not self.metadata:
            return

        tags = [tag.lower() for tag in self.metadata.get('tags', [])]

        def add_badge(badge_type: str, label_text: str, color: str):
            """Helper function to add a badge stripe and icon.

            Args:
                badge_type (str): The type of badge (e.g., 'nsfw', 'humor').
                label_text (str): The text to display on the badge.
                color (str): The background color of the badge.
            """
            # Stripe (dünne Lippe)
            stripe = QWidget()
            stripe.setFixedSize(self._STRIPE_WIDTH, self._STRIPE_HEIGHT)
            stripe.setStyleSheet(f"background-color: {color};")
            cast(QHBoxLayout, self.stripe_container.layout()).addWidget(stripe)

            # Icon (Badge)
            icon_path = config.ICONS_DIR / f"flag_{badge_type}.png"
            badge_label = QLabel()

            if icon_path.exists():
                # PNG Icon
                pix = QPixmap(str(icon_path)).scaledToHeight(
                    self._ICON_HEIGHT,
                    Qt.TransformationMode.SmoothTransformation
                )
                badge_label.setPixmap(pix)
                badge_label.setFixedSize(self._STRIPE_WIDTH, self._ICON_HEIGHT)
                badge_label.setStyleSheet(
                    "QLabel { border: 1px solid rgba(0,0,0,0.5); "
                    "border-radius: 0 0 3px 3px; "
                    "background: rgba(0,0,0,0.35); padding: 2px; }"
                )
            else:
                # Fallback: Text Badge
                badge_label.setText(label_text)
                badge_label.setFixedSize(self._STRIPE_WIDTH, self._ICON_HEIGHT)
                badge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                badge_label.setStyleSheet(
                    f"background: {color}; color: white; "
                    f"border-radius: 0 0 4px 4px; font-weight: bold; "
                    f"font-size: 9px; border: 1px solid rgba(255,255,255,0.3);"
                )

            cast(QHBoxLayout, self.icon_container.layout()).addWidget(badge_label)
            self.badges.append(badge_label)
            self._badge_colors.append(color)

        # Add badges based on metadata
        if self.metadata.get('nsfw') or 'nsfw' in tags:
            add_badge('nsfw', t('ui.badges.nsfw'), "#d9534f")
        if self.metadata.get('humor') or 'humor' in tags:
            add_badge('humor', t('ui.badges.humor'), "#f0ad4e")
        if self.metadata.get('epilepsy') or 'epilepsy' in tags:
            add_badge('epilepsy', t('ui.badges.epilepsy'), "#0275d8")
        if is_animated:
            add_badge('animated', t('ui.badges.animated'), "#5cb85c")

    def _clear_badges(self):
        """Removes all badges, stripes, and resets the overlay to hidden."""
        if self.external_badges:
            return

        # Streifen löschen
        if self.stripe_container:
            layout = self.stripe_container.layout()
            if layout:
                while layout.count():
                    item = layout.takeAt(0)
                    widget = item.widget()
                    if widget:
                        widget.deleteLater()

        # Icons löschen
        if self.icon_container:
            layout = self.icon_container.layout()
            if layout:
                while layout.count():
                    item = layout.takeAt(0)
                    widget = item.widget()
                    if widget:
                        widget.deleteLater()

        self.badges.clear()
        self._badge_colors.clear()
