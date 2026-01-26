"""
Clickable Image - Custom Flag Icons & Badges
Speichern als: src/ui/components/clickable_image.py
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
                if str(self.url_or_path).startswith('http'):
                    headers = {'User-Agent': 'SteamLibraryManager/1.0'}
                    response = requests.get(self.url_or_path, headers=headers, timeout=10)
                    if response.status_code == 200:
                        data = QByteArray(response.content)
        except (OSError, ValueError, requests.RequestException):
            pass

        if self._is_running:
            self.loaded.emit(data)

    def stop(self):
        self._is_running = False


class ClickableImage(QWidget):
    clicked = pyqtSignal()
    right_clicked = pyqtSignal()

    def __init__(self, parent_or_text=None, width=200, height=300, metadata=None):
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

    def set_default_image(self, path):
        self.default_image = path
        if not self.current_path:
            self._load_local_image(path)

    def load_image(self, url_or_path, metadata=None):
        if metadata is not None:
            self.metadata = metadata

        self.current_path = url_or_path

        self.timer.stop()
        self.frames = []
        self._clear_badges()

        if self.loader and self.loader.isRunning():
            self.loader.stop()
            self.loader.wait()

        self.image_label.setText(t('ui.loading.dots'))

        self.loader = ImageLoader(url_or_path)
        self.loader.loaded.connect(self._on_loaded)
        self.loader.start()

    def _on_loaded(self, data: QByteArray):
        if data.isEmpty():
            if self.default_image:
                self._load_local_image(self.default_image)
            else:
                self.image_label.setText("❌")
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
                pass

        pixmap = QPixmap()
        pixmap.loadFromData(data)

        if not pixmap.isNull():
            self._apply_pixmap(pixmap)
            self._create_badges(is_animated=False)
        else:
            if self.default_image:
                self._load_local_image(self.default_image)
            else:
                self.image_label.setText("❌")

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
        self._apply_pixmap(pix)

    def _apply_pixmap(self, pixmap):
        scaled = pixmap.scaled(
            self.w, self.h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.image_label.setPixmap(scaled)

    def _load_local_image(self, path):
        if os.path.exists(path):
            pix = QPixmap(path)
            self._apply_pixmap(pix)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        elif event.button() == Qt.MouseButton.RightButton:
            self.right_clicked.emit()

    def _create_badges(self, is_animated=False):
        """Erstellt Badges (Icons oder Text) oben links"""
        self._clear_badges()

        if not self.metadata:
            return

        tags = self.metadata.get('tags', [])

        # Helper: Fügt entweder Icon oder Text-Badge hinzu
        def add_badge(type_key, text, bg_color="#000000"):
            # 1. Custom Icon prüfen (z.B. flag_nsfw.png)
            icon_name = f"flag_{type_key}.png"
            icon_path = config.ICONS_DIR / icon_name

            if icon_path.exists():
                lbl = QLabel()
                pix = QPixmap(str(icon_path))
                # Skaliere Icon (z.B. 24px Höhe), Aspect Ratio behalten
                lbl.setPixmap(pix.scaledToHeight(24, Qt.TransformationMode.SmoothTransformation))
                lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
                self.badge_layout.addWidget(lbl)
                self.badges.append(lbl)
            else:
                # 2. Fallback: Text Badge
                lbl = QLabel(text)
                lbl.setStyleSheet(f"""
                    background-color: {bg_color}; 
                    color: white; 
                    padding: 3px 6px; 
                    border-radius: 4px; 
                    font-weight: bold; 
                    font-size: 10px;
                    border: 1px solid rgba(255,255,255,0.3);
                """)
                lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
                self.badge_layout.addWidget(lbl)
                self.badges.append(lbl)

        # 1. NSFW
        if self.metadata.get('nsfw') or 'nsfw' in tags:
            add_badge('nsfw', t('ui.badges.nsfw'), "#d9534f")

        # 2. Humor
        if self.metadata.get('humor') or 'humor' in tags:
            add_badge('humor', t('ui.badges.humor'), "#f0ad4e")

        # 3. Epilepsy
        if self.metadata.get('epilepsy') or 'epilepsy' in tags:
            add_badge('epilepsy', t('ui.badges.epilepsy'), "#0275d8")

        # 4. Animated
        if is_animated:
            add_badge('animated', t('ui.badges.animated'), "#5cb85c")

        # 5. Untagged (optional)
        # if 'untagged' in tags: ...

    def _clear_badges(self):
        for b in self.badges:
            self.badge_layout.removeWidget(b)
            b.deleteLater()
        self.badges = []