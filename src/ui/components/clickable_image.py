"""
Clickable Image - Animated, Badges, Localized & Defaults
Speichern als: src/ui/components/clickable_image.py
"""
from PyQt6.QtWidgets import QLabel, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QByteArray, QTimer
from PyQt6.QtGui import QPixmap, QCursor, QImage
import requests
import os
import io
from pathlib import Path
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
    loaded = pyqtSignal(QByteArray)

    def __init__(self, url_or_path):
        super().__init__()
        self.url_or_path = url_or_path
        self._is_running = True

    def run(self):
        data = QByteArray()
        try:
            if not self.url_or_path:
                self.loaded.emit(data)
                return

            if os.path.exists(self.url_or_path):
                with open(self.url_or_path, 'rb') as f:
                    data = QByteArray(f.read())
            else:
                # Check for URL
                if str(self.url_or_path).startswith('http'):
                    headers = {'User-Agent': 'SteamLibraryManager/1.0'}
                    response = requests.get(self.url_or_path, headers=headers, timeout=15)
                    if response.status_code == 200:
                        data = QByteArray(response.content)
        except (requests.exceptions.RequestException, OSError):
            pass

        if self._is_running:
            self.loaded.emit(data)

    def stop(self):
        self._is_running = False
        self.quit()
        self.wait()


class ClickableImage(QWidget):
    clicked = pyqtSignal(str)
    right_clicked = pyqtSignal(str)

    def __init__(self, img_type, width, height, metadata=None):
        super().__init__()
        self.img_type = img_type
        self.w = width
        self.h = height
        self.loader = None
        self.metadata = metadata or {}

        self.frames = []
        self.durations = []
        self.current_frame = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._next_frame)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(2)

        self.img_container = QWidget()
        self.img_container.setFixedSize(width, height)
        self.img_container.setStyleSheet("background-color: #222; border-radius: 4px; border: 1px solid #444;")
        self.img_container.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.image_label = QLabel(self.img_container)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("border: none; background: transparent;")

        self.layout.addWidget(self.img_container)

        # Autor Label
        author_text = t('ui.game_details.value_unknown')
        if self.metadata and 'author' in self.metadata:
            auth_data = self.metadata['author']
            if isinstance(auth_data, dict):
                author_text = auth_data.get('name', t('ui.game_details.value_unknown'))
            else:
                author_text = str(auth_data)
        elif not self.metadata:
            author_text = t(f'ui.game_details.gallery.{img_type}')

        self.author_label = QLabel(author_text)
        self.author_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.author_label.setStyleSheet("color: #888; font-size: 10px; padding-top: 2px;")
        self.author_label.setFixedWidth(width)

        font_metrics = self.author_label.fontMetrics()
        elided = font_metrics.elidedText(author_text, Qt.TextElideMode.ElideRight, width - 10)
        self.author_label.setText(elided)
        self.author_label.setToolTip(author_text)

        self.layout.addWidget(self.author_label)

    def _get_default_image_path(self):
        """Liefert den Pfad zum Platzhalter-Bild, falls vorhanden"""
        # Annahme: config.RESOURCES_DIR ist definiert (z.B. resources/images/)
        # Falls in src/config.py RESOURCES_DIR nicht definiert ist, nutze Fallback
        try:
            base_dir = config.RESOURCES_DIR
        except AttributeError:
            # Fallback relativ zur Datei
            base_dir = Path(__file__).parent.parent.parent.parent / 'resources'

        default_path = base_dir / 'images' / f'default_{self.img_type}.png'
        return str(default_path) if default_path.exists() else None

    def _create_badges(self, is_animated_file=False):
        def get_icon_path(name):
            p = config.ICONS_DIR / f"{name}.png"
            return str(p) if p.exists() else None

        badges = []
        mime = self.metadata.get('mime', '')
        tags = self.metadata.get('tags', [])

        is_anim = is_animated_file or 'webp' in mime or 'gif' in mime or 'animated' in tags
        if is_anim:
            badges.append({
                'icon': get_icon_path('flag_animated'),
                'fallback': 'GIF',
                'color': '#FFD700',
                'tip': t('ui.badges.animated')
            })

        if self.metadata.get('humor'):
            badges.append({
                'icon': get_icon_path('flag_humor'),
                'fallback': '😂',
                'color': '#3498db',
                'tip': t('ui.badges.humor')
            })

        if self.metadata.get('nsfw'):
            badges.append({
                'icon': get_icon_path('flag_nsfw'),
                'fallback': '🔞',
                'color': '#e74c3c',
                'tip': t('ui.badges.nsfw')
            })

        if self.metadata.get('epilepsy'):
            badges.append({
                'icon': get_icon_path('flag_epilepsy'),
                'fallback': '⚡',
                'color': '#9b59b6',
                'tip': t('ui.badges.epilepsy')
            })

        if self.metadata.get('lock_tags'):
            badges.append({
                'icon': get_icon_path('flag_untagged'),
                'fallback': '?',
                'color': '#95a5a6',
                'tip': t('ui.badges.untagged')
            })

        for child in self.img_container.children():
            if isinstance(child, QLabel) and child != self.image_label:
                child.deleteLater()

        x_pos, y_pos = 4, 4
        for badge in badges:
            lbl = QLabel(self.img_container)
            lbl.setToolTip(badge['tip'])

            if badge['icon']:
                pix = QPixmap(badge['icon'])
                if not pix.isNull():
                    pix = pix.scaled(20, 20, Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation)
                    lbl.setPixmap(pix)
                    lbl.resize(20, 20)
            else:
                lbl.setText(badge['fallback'])
                lbl.setStyleSheet(
                    f"background-color: {badge['color']}; color: #000; font-weight: bold; border-radius: 3px; padding: 2px;")
                lbl.adjustSize()

            lbl.move(x_pos, y_pos)
            lbl.show()
            lbl.raise_()
            x_pos += lbl.width() + 4

    def load_image(self, url_or_path):
        """Lädt Bild von URL/Pfad oder Default"""
        self.timer.stop()
        self.frames = []
        self.durations = []
        self.current_frame = 0
        self.image_label.clear()

        # Ermittle Zielpfad (Parameter oder Default)
        target = url_or_path
        if not target or (not str(target).startswith('http') and not os.path.exists(str(target))):
            default = self._get_default_image_path()
            if default:
                target = default

        if self.loader and self.loader.isRunning():
            self.loader.stop()

        self.image_label.setText("⏳")
        self.loader = ImageLoader(target)
        self.loader.loaded.connect(self._on_loaded)
        self.loader.start()

    def _apply_pixmap(self, pixmap):
        scaled = pixmap.scaled(
            self.w, self.h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.image_label.resize(scaled.size())
        self.image_label.setPixmap(scaled)
        self._center_image()

    def _on_loaded(self, data: QByteArray):
        if data.isEmpty():
            # Wenn Laden fehlgeschlagen, versuche Default, falls noch nicht geschehen
            # (aber hier sind wir schon im Result Callback, vermeiden wir Endlosschleifen)
            self.image_label.setText("❌")
            if self.metadata: self._create_badges(False)
            return

        if HAS_PILLOW:
            try:
                byte_stream = io.BytesIO(data.data())
                im = Image.open(byte_stream)

                is_animated = getattr(im, "is_animated", False)
                self.frames = []
                self.durations = []

                if is_animated:
                    for frame in ImageSequence.Iterator(im):
                        frame_rgba = frame.convert("RGBA")
                        data_rgba = frame_rgba.tobytes("raw", "RGBA")
                        qimg = QImage(data_rgba, frame_rgba.width, frame_rgba.height, QImage.Format.Format_RGBA8888)
                        pix = QPixmap.fromImage(qimg)
                        scaled = pix.scaled(self.w, self.h, Qt.AspectRatioMode.KeepAspectRatio,
                                            Qt.TransformationMode.SmoothTransformation)
                        self.frames.append(scaled)
                        duration = frame.info.get('duration', 100)
                        self.durations.append(duration)

                    if self.frames:
                        self._start_animation()
                        self._create_badges(True)
                        return
                else:
                    im_rgba = im.convert("RGBA")
                    data_rgba = im_rgba.tobytes("raw", "RGBA")
                    qimg = QImage(data_rgba, im_rgba.width, im_rgba.height, QImage.Format.Format_RGBA8888)
                    self._apply_pixmap(QPixmap.fromImage(qimg))
                    self._create_badges(False)
                    return

            except (IOError, ValueError):
                pass

        pixmap = QPixmap()
        pixmap.loadFromData(data)

        if not pixmap.isNull():
            self._apply_pixmap(pixmap)
            self._create_badges(False)
        else:
            self.image_label.setText("❌")
            if self.metadata: self._create_badges(False)

    def _start_animation(self):
        if not self.frames: return
        self.current_frame = 0
        self._show_frame(0)
        self.timer.start(self.durations[0])

    def _next_frame(self):
        if not self.frames: return
        self.current_frame = (self.current_frame + 1) % len(self.frames)
        self._show_frame(self.current_frame)
        self.timer.start(self.durations[self.current_frame])

    def _show_frame(self, index):
        pix = self.frames[index]
        self.image_label.resize(pix.size())
        self.image_label.setPixmap(pix)
        self._center_image()

    def _center_image(self):
        lw = self.image_label.width()
        lh = self.image_label.height()
        x = (self.w - lw) // 2
        y = (self.h - lh) // 2
        self.image_label.move(x, y)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.img_type)
        elif event.button() == Qt.MouseButton.RightButton:
            self.right_clicked.emit(self.img_type)