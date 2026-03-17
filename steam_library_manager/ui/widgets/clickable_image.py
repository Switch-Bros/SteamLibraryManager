#
# steam_library_manager/ui/widgets/clickable_image.py
# Image widget with click signals, animation support and badge overlays
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

__all__ = ["ClickableImage", "ImageLoader"]

import io
import logging
import os

import requests
from PyQt6.QtCore import QByteArray, Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QCursor, QImage, QPixmap
from PyQt6.QtWidgets import QLabel, QWidget

from steam_library_manager.ui.theme import Theme
from steam_library_manager.ui.widgets.image_badge_overlay import ImageBadgeOverlay
from steam_library_manager.utils.i18n import t
from steam_library_manager.utils.timeouts import HTTP_TIMEOUT

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
    # loads image data in background so UI doesn't freeze
    loaded = pyqtSignal(QByteArray)

    def __init__(self, url_or_path, fallback_urls=None):
        super().__init__()
        self.url_or_path = url_or_path
        self.fallbacks = fallback_urls or []
        self._running = True

    def run(self):
        data = QByteArray()
        try:
            if not self.url_or_path:
                self.loaded.emit(data)
                return

            if os.path.exists(self.url_or_path):
                with open(self.url_or_path, "rb") as f:
                    data = QByteArray(f.read())
            elif str(self.url_or_path).startswith("http"):
                data = self._fetch()
        except (OSError, ValueError, requests.RequestException):
            pass

        if self._running:
            self.loaded.emit(data)

    def _fetch(self):
        # try primary url first, then fallbacks
        hdrs = {"User-Agent": "SteamLibraryManager/1.0"}
        urls = [self.url_or_path] + self.fallbacks
        for url in urls:
            try:
                resp = requests.get(url, headers=hdrs, timeout=HTTP_TIMEOUT)
                if resp.status_code == 200 and len(resp.content) > 100:
                    return QByteArray(resp.content)
            except requests.RequestException:
                continue
        return QByteArray()

    def stop(self):
        self._running = False


class ClickableImage(QWidget):
    """Image widget with click/hover signals and optional badge overlay."""

    clicked = pyqtSignal()
    right_clicked = pyqtSignal()
    load_finished = pyqtSignal()

    def __init__(self, parent_or_text=None, width=200, height=300, metadata=None, external_badges=False):
        parent = parent_or_text if not isinstance(parent_or_text, str) else None
        super().__init__(parent)
        self.w = width
        self.h = height
        self.metadata = metadata
        self.external_badges = external_badges

        self.setFixedSize(width, height)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        # generation counter to discard stale results
        self._gen = 0

        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("border: 1px solid %s; background-color: %s;" % (Theme.PEGI_HVR, Theme.BG_PRI))
        self.image_label.setGeometry(0, 0, width, height)
        self.image_label.setScaledContents(False)
        self.image_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # badge overlay (steamgriddb style)
        self._badges = ImageBadgeOverlay(self, width) if not external_badges else None

        self.default_image = None
        self.current_path = None
        self.loader = None

        # animation state
        self.frames = []
        self.durations = []
        self.current_frame = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._next_frame)

        # pixmap cache
        self._px_cache = {}

    def set_default_image(self, path):
        self.default_image = path
        if not self.current_path:
            self._load_local(path)

    @staticmethod
    def _is_animated(im):
        # check if pillow image has multiple frames
        if getattr(im, "is_animated", False):
            return True
        try:
            im.seek(1)
            im.seek(0)
            return True
        except (EOFError, ValueError):
            return False

    @staticmethod
    def _pil_to_pixmap(pil_img):
        frame = pil_img.convert("RGBA")
        raw = frame.tobytes("raw", "RGBA")
        qim = QImage(raw, frame.width, frame.height, QImage.Format.Format_RGBA8888)
        return QPixmap.fromImage(qim)

    def load_image(self, url_or_path, metadata=None, fallback_urls=None):
        """Load all the images from URL/path with caching and animation support.

        Handles static and animated Images (GIF/APNG/WEBP) via PILLOW,
        CDN fallback for missing artwork.

        First = Load static Images as Thumbs in bulks (not all at once)
        Second = Load animated Images with full URL (thumbnails will break animated Images)
        """

        if metadata is not None:
            self.metadata = metadata

        self.current_path = url_or_path
        self._gen += 1
        self.timer.stop()
        self.frames = []
        self._clear_badges()

        if url_or_path is None:
            if self.default_image:
                self._load_local(self.default_image)
            return

        # webm can't be displayed
        if url_or_path and url_or_path.lower().endswith(".webm"):
            if self.default_image:
                self._load_local(self.default_image)
            else:
                self.image_label.setText(t("emoji.no_image"))
            self.load_finished.emit()
            return

        # check cache first
        if url_or_path and url_or_path in self._px_cache:
            px = self._px_cache[url_or_path]
            if not px.isNull():
                self._apply_px(px)
                self._make_badges(animated=False)
                self.load_finished.emit()
                return

        if self.loader and self.loader.isRunning():
            self.loader.stop()
            self.loader.wait()

        self.image_label.setText(t("common.loading"))

        gen = self._gen
        self.loader = ImageLoader(url_or_path, fallback_urls=fallback_urls)
        self.loader.loaded.connect(lambda data, g=gen: self._on_loaded(data, g))
        self.loader.start()

    def _on_loaded(self, data, generation=-1):
        # Check all stale results
        if generation != -1 and generation != self._gen:
            return

        if data.isEmpty():
            if self.default_image:
                self.current_path = None
                self._load_local(self.default_image)
            else:
                self.image_label.setText(t("emoji.error"))
            self.load_finished.emit()
            return

        # try pillow first (animation support)
        if HAS_PILLOW:
            try:
                raw = data.data()
                buf = io.BytesIO(raw)
                im = Image.open(buf)

                if self._is_animated(im):
                    self.frames = []
                    self.durations = []
                    for frame in ImageSequence.Iterator(im):
                        self.frames.append(self._pil_to_pixmap(frame))
                        self.durations.append(frame.info.get("duration", 100))
                    if self.frames:
                        self._start_anim()
                        self._make_badges(animated=True)
                        self.load_finished.emit()
                        return
                else:
                    self._apply_px(self._pil_to_pixmap(im))
                    self._make_badges(animated=False)
                    self.load_finished.emit()
                    return
            except (IOError, ValueError, TypeError, EOFError) as e:
                logger.error(t("logs.image.pillow_fallback", error=e))

        # fallback: standard qt loading
        px = QPixmap()
        px.loadFromData(data)
        if not px.isNull():
            self._apply_px(px)
            self._make_badges(animated=False)
        else:
            if self.default_image:
                self._load_local(self.default_image)
            else:
                self.image_label.setText(t("emoji.error"))
        self.load_finished.emit()

    def _start_anim(self):
        if not self.frames:
            return
        self.current_frame = 0
        self._show_frame(0)
        self.timer.start(int(self.durations[0]))

    def _next_frame(self):
        if not self.frames:
            return
        self.current_frame = (self.current_frame + 1) % len(self.frames)
        self._show_frame(self.current_frame)
        self.timer.start(int(self.durations[self.current_frame]))

    def _show_frame(self, idx):
        if 0 <= idx < len(self.frames):
            self._apply_px(self.frames[idx])

    def _apply_px(self, pixmap):
        scaled = pixmap.scaled(
            self.w, self.h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        self.image_label.setPixmap(scaled)
        if self._badges:
            self._badges.raise_()
        # cache for reuse
        if self.current_path and self.current_path not in self._px_cache:
            self._px_cache[self.current_path] = pixmap

    def _load_local(self, path):
        if os.path.exists(path):
            self._apply_px(QPixmap(path))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        elif event.button() == Qt.MouseButton.RightButton:
            self.right_clicked.emit()

    def enterEvent(self, event):
        super().enterEvent(event)
        if self._badges:
            self._badges.expand()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        if self._badges:
            self._badges.collapse()

    def _make_badges(self, animated=False):
        if self._badges:
            self._badges.create_badges(self.metadata, animated)

    def _clear_badges(self):
        if self._badges:
            self._badges.clear_badges()

    def clear(self):
        self.timer.stop()
        self.frames = []
        self.current_path = None
        self._clear_badges()
        if self.default_image:
            self._load_local(self.default_image)
        else:
            self.image_label.clear()
            self.image_label.setText("")
