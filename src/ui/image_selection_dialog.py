"""
Image Selection Dialog - Larger & Optimized
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

        # FIX: Größeres Fenster für viele Bilder
        self.resize(1000, 800)

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
        self.grid_layout.setSpacing(10)
        self.scroll.setWidget(self.grid_widget)

        layout.addWidget(self.scroll)

    def _start_search(self):
        self.searcher = SearchThread(self.app_id, self.img_type)
        self.searcher.results_found.connect(self._on_results)
        self.searcher.start()

    def _on_results(self, urls):
        self.status_label.hide()
        self.scroll.show()

        if not urls:
            self.status_label.setText(t('ui.status.no_results'))
            self.status_label.show()
            return

        # Grid füllen
        row, col = 0, 0
        cols = 4 if self.img_type == 'grid' else 3  # Mehr Spalten für bessere Übersicht

        for url in urls:
            # Größe für Vorschau
            w, h = (200, 300) if self.img_type == 'grid' else (300, 150)

            img = ClickableImage(self.img_type, w, h)
            img.load_image(url)
            # URL speichern für Auswahl
            img.setProperty("url", url)
            # Klick überschreiben: Wählt Bild aus
            img.mousePressEvent = lambda e, u=url: self._on_select(u)

            self.grid_layout.addWidget(img, row, col)
            col += 1
            if col >= cols:
                col = 0
                row += 1

    def _on_select(self, url):
        self.selected_url = url
        self.accept()

    def get_selected_url(self):
        return self.selected_url