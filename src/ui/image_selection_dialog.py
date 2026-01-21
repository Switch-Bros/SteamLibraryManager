"""
Image Selection Dialog - Force Full URL for Animations
Speichern als: src/ui/image_selection_dialog.py
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QScrollArea, QWidget, QGridLayout, QLabel)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from src.utils.i18n import t
from src.integrations.steamgrid_api import SteamGridDB
from src.ui.components.clickable_image import ClickableImage


class SearchThread(QThread):
    results_found = pyqtSignal(list)

    def __init__(self, app_id, img_type):
        super().__init__()
        self.app_id = app_id
        self.img_type = img_type
        self.api = SteamGridDB()

    def run(self):
        urls = self.api.get_images_by_type(self.app_id, self.img_type)
        self.results_found.emit(urls)


class ImageSelectionDialog(QDialog):
    def __init__(self, parent, game_name, app_id, img_type):
        super().__init__(parent)
        self.setWindowTitle(
            t('ui.dialogs.image_picker_title', type=t(f'ui.game_details.gallery.{img_type}'), game=game_name))
        self.resize(1100, 800)

        self.app_id = app_id
        self.img_type = img_type
        self.selected_url = None

        self._create_ui()
        self._start_search()

    def _create_ui(self):
        layout = QVBoxLayout(self)

        self.status_label = QLabel(t('ui.dialogs.image_picker_loading'))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.hide()

        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(15)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.grid_widget)

        layout.addWidget(self.scroll)

    def _start_search(self):
        self.searcher = SearchThread(self.app_id, self.img_type)
        self.searcher.results_found.connect(self._on_results)
        self.searcher.start()

    def _on_results(self, items):
        self.status_label.hide()
        self.scroll.show()

        if not items:
            self.status_label.setText(t('ui.status.no_results'))
            self.status_label.show()
            return

        row, col = 0, 0

        if self.img_type == 'grids':
            cols = 4
            w, h = 220, 330
        elif self.img_type == 'heroes':
            cols = 2
            w, h = 460, 150
        elif self.img_type == 'logos':
            cols = 3
            w, h = 300, 150
        elif self.img_type == 'icons':
            cols = 6
            w, h = 162, 162
        else:
            cols = 3
            w, h = 250, 250

        for item in items:
            img_widget = ClickableImage(self.img_type, w, h, metadata=item)

            # FIX: URL Auswahl Logik
            # Standard: Thumb (schneller)
            load_url = item['thumb']

            # Wenn Animation (WebP/GIF) -> Nimm FULL URL
            # (Die Thumbnails sind oft kaputt oder statisch bei SGDB)
            mime = item.get('mime', '')
            if 'webp' in mime or 'gif' in mime:
                load_url = item['url']

            img_widget.load_image(load_url)

            # Klick -> Volle URL speichern
            full_url = item['url']
            img_widget.mousePressEvent = lambda e, u=full_url: self._on_select(u)

            self.grid_layout.addWidget(img_widget, row, col)
            col += 1
            if col >= cols:
                col = 0
                row += 1

    def _on_select(self, url):
        self.selected_url = url
        self.accept()

    def get_selected_url(self):
        return self.selected_url