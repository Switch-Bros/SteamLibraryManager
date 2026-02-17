# src/ui/components/clickable_image.py

"""
A custom widget to display clickable and dynamically loaded images.

This widget can load images from local paths or URLs in a separate thread,
supports animated GIFs (if Pillow is installed), and can display
superimposed badges based on metadata.
"""

from __future__ import annotations

import logging
import os
from typing import cast

import requests
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QByteArray, QTimer, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QPixmap, QCursor, QImage
from PyQt6.QtWidgets import QLabel, QWidget, QVBoxLayout, QHBoxLayout

os.environ["OPENCV_LOG_LEVEL"] = "SILENT"
import io
from src.config import config
from src.ui.theme import Theme
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

try:
    import cv2
    import numpy as np

    HAS_OPENCV = True
except ImportError:
    cv2 = None
    np = None
    HAS_OPENCV = False


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
    """A widget that displays an image and emits signals on clicks."""

    clicked = pyqtSignal()
    right_clicked = pyqtSignal()

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
        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet(f"border: 1px solid {Theme.PEGI_HOVER}; background-color: {Theme.BG_PRIMARY};")
        self.image_label.setGeometry(0, 0, width, height)
        self.image_label.setScaledContents(False)
        # Pass through mouse events so enterEvent/leaveEvent work on self
        self.image_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # --- Badge-Overlay System (SteamGridDB-Style) ---
        # NUR erstellen wenn external_badges=False!
        if not external_badges:
            # STRIPE: Thin 5px strip ON the yellow border
            # ICON: 28×28px badge that extends below on hover
            self._STRIPE_HEIGHT: int = 5  # Thin stripe (like SteamGridDB!)
            self._ICON_HEIGHT: int = 28  # Icon height
            self._BADGE_GAP: int = 2  # Gap between stripe and icon
            self._EXPANDED_HEIGHT: int = (  # Total height when expanded
                self._STRIPE_HEIGHT + self._BADGE_GAP + self._ICON_HEIGHT
            )
            self._STRIPE_WIDTH: int = 28  # Icon width
            self._STRIPE_GAP: int = 2  # Gap between multiple badges

            # Overlay container — positioned at y=-6 ABOVE the widget
            # HEIGHT must be _EXPANDED_HEIGHT (35px) for icon expansion!
            # The THIN stripe (5px) sits COMPLETELY ABOVE the image (1px extra!)
            self.badge_overlay = QWidget(self)
            self.badge_overlay.setGeometry(0, -6, width, self._EXPANDED_HEIGHT)
            self.badge_overlay.raise_()
            self.badge_overlay.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

            overlay_layout = QVBoxLayout(self.badge_overlay)
            overlay_layout.setContentsMargins(5, 0, 0, 0)
            overlay_layout.setSpacing(self._BADGE_GAP)  # 1px gap between stripe and icon
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

            # Animation for the overlay — animates maximumHeight between collapsed and expanded
            # Animation on "geometry" — works for absolutely positioned widgets
            # (maximumHeight is ignored by the layout for setGeometry widgets)
            self.badge_animation = QPropertyAnimation(self.badge_overlay, b"geometry")
            self.badge_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            self.badge_animation.setDuration(180)  # ms — fast but not instant

            # Badge state
            self._badge_colors: list[str] = []  # Colors per badge (for the stripes)
            self.badges: list[QWidget] = []  # Badge icon widgets
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

        # WEBM video playback with OpenCV
        self.video_cap = None  # cv2.VideoCapture object
        self.video_timer = QTimer(self)
        self.video_timer.timeout.connect(self._next_video_frame)
        self.is_playing_video = False

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

        Supports images (PNG, JPG, GIF, WEBP, APNG) and videos (WEBM via OpenCV).

        Args:
            url_or_path (str | None): The URL or file path of the image to load, or None to clear.
            metadata (dict): Optional metadata for badge display.
        """
        if metadata is not None:
            self.metadata = metadata

        self.current_path = url_or_path
        self.timer.stop()
        self.video_timer.stop()
        self.frames = []
        self._clear_badges()

        # Stop any playing video
        if self.video_cap:
            self.video_cap.release()
            self.video_cap = None
        self.is_playing_video = False

        # If url_or_path is None, load default image immediately without showing loading text
        if url_or_path is None:
            if self.default_image:
                self._load_local_image(self.default_image)
            return

        # Check if this is a WEBM video
        if url_or_path and url_or_path.lower().endswith(".webm"):
            if HAS_OPENCV:
                self._load_webm_video(url_or_path)
                return
            else:
                # Fallback: try to load as image
                pass

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

        self.image_label.setText(t("common.loading"))

        self.loader = ImageLoader(url_or_path)
        self.loader.loaded.connect(self._on_loaded)
        self.loader.start()

    def _on_loaded(self, data: QByteArray):
        """Handles the loaded image data, parsing it with Pillow if available.

        Robust handling for animations (APNG, WEBP, GIF) and fallback to Qt
        to avoid red crosses or crashes.
        """
        if data.isEmpty():
            if self.default_image:
                self.current_path = None  # Reset to prevent caching default image under wrong path
                self._load_local_image(self.default_image)
            else:
                self.image_label.setText(t("emoji.error"))
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

                        qim = QImage(img_bytes, frame.width, frame.height, QImage.Format.Format_RGBA8888)

                        self.frames.append(QPixmap.fromImage(qim))
                        self.durations.append(frame.info.get("duration", 100))

                    if self.frames:
                        self._start_animation()
                        self._create_badges(is_animated=True)
                        return
                else:
                    # Static image via Pillow
                    im = im.convert("RGBA")
                    # CRITICAL FIX: Save bytes here too!
                    img_bytes = im.tobytes("raw", "RGBA")

                    qim = QImage(img_bytes, im.width, im.height, QImage.Format.Format_RGBA8888)
                    self._apply_pixmap(QPixmap.fromImage(qim))
                    self._create_badges(is_animated=False)
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

    def _load_webm_video(self, url: str):
        """Loads and plays a WEBM video using OpenCV.

        Args:
            url (str): The URL of the WEBM video to load.
        """
        if not HAS_OPENCV:
            self.image_label.setText(t("emoji.error"))
            return

        try:
            self.video_cap = cv2.VideoCapture(url)
            if not self.video_cap.isOpened():
                raise Exception("Failed to open video")

            # Get FPS for timer interval
            fps = self.video_cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0:
                fps = 30  # Default to 30 FPS

            interval_ms = int(1000 / fps)

            self.is_playing_video = True
            self.video_timer.start(interval_ms)

            # Create animated badge for WEBM
            self._create_badges(is_animated=True)

        except Exception as e:
            logger.error(t("logs.image.webm_load_failed", error=e))
            self.image_label.setText(t("emoji.error"))
            if self.video_cap:
                self.video_cap.release()
                self.video_cap = None

    def _next_video_frame(self):
        """Reads and displays the next frame from the WEBM video."""
        if not self.video_cap or not self.is_playing_video:
            return

        ret, frame = self.video_cap.read()

        if not ret:
            # Loop video
            self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.video_cap.read()

            if not ret:
                # Failed to loop, stop playback
                self.video_timer.stop()
                self.is_playing_video = False
                return

        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Convert to QImage
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        qt_image = QImage(frame_rgb.tobytes(), w, h, bytes_per_line, QImage.Format.Format_RGB888)

        # Convert to QPixmap and display
        pixmap = QPixmap.fromImage(qt_image)
        self._apply_pixmap(pixmap)

    def _apply_pixmap(self, pixmap: QPixmap):
        """Scales and sets the pixmap on the label."""
        scaled = pixmap.scaled(
            self.w, self.h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        self.image_label.setPixmap(scaled)
        # Overlay nach oben bringen — setPixmap kann Z-Reihenfolge beeinflussen
        # NUR wenn badge_overlay existiert (nicht bei external_badges)
        if self.badge_overlay:
            self.badge_overlay.raise_()

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

    def _animate_overlay(self, target_height: int):
        """Helper method to animate the badge overlay to a target height.

        Args:
            target_height (int): The target height in pixels.
        """
        if self.external_badges or not self.badges:
            return
        self.badge_animation.stop()
        current: QRect = self.badge_overlay.geometry()
        self.badge_animation.setStartValue(current)
        self.badge_animation.setEndValue(QRect(0, 0, self.w, target_height))
        self.badge_animation.start()

    def enterEvent(self, event):
        """Triggers badge expansion animation on mouse enter.

        Animates the badge overlay geometry from collapsed (stripes only) to
        expanded (full badge icons visible) via QRect interpolation.
        """
        super().enterEvent(event)
        if not self.external_badges:
            self._animate_overlay(self._EXPANDED_HEIGHT)

    def leaveEvent(self, event):
        """Triggers badge collapse animation on mouse leave.

        Animates the badge overlay geometry back from expanded to collapsed
        (stripes only visible) via QRect interpolation.
        """
        super().leaveEvent(event)
        if not self.external_badges:
            self._animate_overlay(self._STRIPE_HEIGHT)

    def _create_badges(self, is_animated: bool = False):
        """
        Creates animated slide-down badges (SteamGridDB style).

        Normal state: only thin colored stripes visible at the top edge.
        On hover: badges slide down smoothly to reveal full icons.

        Args:
            is_animated (bool): Whether the loaded image is an animated GIF.
        """
        if self.external_badges:
            return  # Badges werden extern verwaltet

        self._clear_badges()
        if not self.metadata:
            return

        tags: list[str] = self.metadata.get("tags", [])

        # Badge-Definitionen: (type_key, text, bg_color, condition)
        badge_defs: list[tuple[str, str, str, bool]] = [
            (
                "nsfw",
                f"{t('emoji.nsfw')} {t('ui.badges.nsfw')}",
                "#d9534f",
                bool(self.metadata.get("nsfw") or "nsfw" in tags),
            ),
            (
                "humor",
                f"{t('emoji.humor')} {t('ui.badges.humor')}",
                "#f0ad4e",
                bool(self.metadata.get("humor") or "humor" in tags),
            ),
            (
                "epilepsy",
                f"{t('emoji.blitz')} {t('ui.badges.epilepsy')}",
                "#0275d8",
                bool(self.metadata.get("epilepsy") or "epilepsy" in tags),
            ),
            ("animated", f"{t('emoji.animated')} {t('ui.badges.animated')}", "#5cb85c", is_animated),
        ]

        # Nur die aktiven Badges aufbauen
        active_badges: list[tuple[str, str, str]] = [
            (key, text, color) for key, text, color, active in badge_defs if active
        ]

        if not active_badges:
            # No badges → hide overlay completely
            self.badge_overlay.setGeometry(0, 0, self.w, 0)
            return

        # cast(): .layout() returns QLayout|None — we know it's QHBoxLayout
        stripe_layout: QHBoxLayout = cast(QHBoxLayout, self.stripe_container.layout())
        icon_layout: QHBoxLayout = cast(QHBoxLayout, self.icon_container.layout())

        for type_key, text, bg_color in active_badges:
            # --- Add stripe (always visible, square 28×28) ---
            stripe = QWidget()
            stripe.setFixedSize(self._STRIPE_WIDTH, self._STRIPE_HEIGHT)
            stripe.setStyleSheet(f"background-color: {bg_color};")
            stripe_layout.addWidget(stripe)

            # --- Add icon (only visible on hover) ---
            icon_path = config.ICONS_DIR / f"flag_{type_key}.png"
            if icon_path.exists():
                lbl = QLabel()
                pix = QPixmap(str(icon_path)).scaledToHeight(
                    self._ICON_HEIGHT, Qt.TransformationMode.SmoothTransformation
                )
                lbl.setPixmap(pix)
                lbl.setFixedWidth(self._STRIPE_WIDTH)
                # Subtiler Shadow damit Icons auf dunklen Covers sichtbar bleiben
                lbl.setStyleSheet(
                    "QLabel { "
                    "  border: 1px solid rgba(0, 0, 0, 0.45); "
                    "  border-radius: 0px 0px 3px 3px; "
                    "  background-color: rgba(0, 0, 0, 0.25); "
                    "  padding: 1px; "
                    "}"
                )
            else:
                # Fallback: Text-Badge wenn kein PNG vorhanden
                # FEST 28×28px — NICHT dynamisch anpassen!
                lbl = QLabel(text)
                lbl.setFixedSize(self._STRIPE_WIDTH, self._ICON_HEIGHT)  # 28×28px FEST!
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Text zentrieren
                lbl.setStyleSheet(
                    f"background-color: {bg_color}; color: white; "
                    f"border-radius: 0px 0px 4px 4px; "
                    f"font-weight: bold; font-size: 9px; "
                    f"border: 1px solid rgba(255,255,255,0.3);"
                )
            icon_layout.addWidget(lbl)

            # Save color for later reference
            self._badge_colors.append(bg_color)
            self.badges.append(lbl)

        # Overlay auf kollabierten Zustand setzen — nur Streifen sichtbar
        # Qt clippt Children automatisch an der Widget-Geometrie
        self.badge_overlay.setGeometry(0, 0, self.w, self._STRIPE_HEIGHT)

    def _clear_badges(self):
        """Removes all badges, stripes, and resets the overlay to hidden."""
        if self.external_badges:
            return  # Badges are managed externally — nothing to clear

        # Icons aus dem icon_container entfernen
        icon_layout: QHBoxLayout = cast(QHBoxLayout, self.icon_container.layout())
        for b in self.badges:
            icon_layout.removeWidget(b)
            b.deleteLater()
        self.badges = []

        # Streifen aus dem stripe_container entfernen
        stripe_layout: QHBoxLayout = cast(QHBoxLayout, self.stripe_container.layout())
        while stripe_layout.count():
            item = stripe_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Reset state — overlay invisible
        self._badge_colors = []
        self.badge_overlay.setGeometry(0, 0, self.w, 0)

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
