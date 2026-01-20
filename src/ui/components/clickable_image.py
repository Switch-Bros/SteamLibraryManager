"""
Clickable Image Label - Handles Loading & Clicking (Left & Right Click)
Speichern als: src/ui/components/clickable_image.py
"""
from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QPixmap, QCursor
import requests
import os
from src.utils.i18n import t


class ImageLoader(QThread):
    loaded = pyqtSignal(QPixmap)

    def __init__(self, url_or_path):
        super().__init__()
        self.url_or_path = url_or_path
        self._is_running = True

    def run(self):
        pixmap = QPixmap()
        try:
            if not self.url_or_path:
                self.loaded.emit(pixmap)
                return

            if os.path.exists(self.url_or_path):
                pixmap.load(self.url_or_path)
            else:
                response = requests.get(self.url_or_path, timeout=5)
                if response.status_code == 200:
                    pixmap.loadFromData(response.content)
        except:
            pass

        if self._is_running:
            self.loaded.emit(pixmap)

    def stop(self):
        self._is_running = False
        self.quit()
        self.wait()


class ClickableImage(QLabel):
    clicked = pyqtSignal(str)
    right_clicked = pyqtSignal(str)  # NEU: Signal für Rechtsklick

    def __init__(self, img_type, width, height):
        super().__init__()
        self.img_type = img_type
        self.w = width
        self.h = height
        self.loader = None

        self.setFixedSize(width, height)
        self.setStyleSheet("background-color: #222; border: 1px solid #444; border-radius: 4px;")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setScaledContents(True)

        self.setText(t(f'ui.game_details.gallery.{img_type}'))

    def load_image(self, url_or_path):
        if self.loader and self.loader.isRunning():
            self.loader.stop()

        self.setText("⏳")
        self.loader = ImageLoader(url_or_path)
        self.loader.loaded.connect(self._on_loaded)
        self.loader.start()

    def _on_loaded(self, pixmap):
        if not pixmap.isNull():
            self.setPixmap(pixmap)
        else:
            self.setText("❌")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.img_type)
        elif event.button() == Qt.MouseButton.RightButton:
            self.right_clicked.emit(self.img_type)  # NEU: Rechtsklick senden