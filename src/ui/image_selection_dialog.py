"""
Image Selection Dialog - With Integrated API Key Setup
Speichern als: src/ui/image_selection_dialog.py
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QScrollArea, QWidget, QGridLayout, QLabel,
                             QPushButton, QLineEdit, QFormLayout, QHBoxLayout)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices, QFont
from src.utils.i18n import t
from src.config import config
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
        self._check_api_and_start()

    def _create_ui(self):
        self.main_layout = QVBoxLayout(self)

        self.status_label = QLabel(t('ui.dialogs.image_picker_loading'))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.status_label)

        # Grid Area (Standard)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.hide()

        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(15)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.grid_widget)

        self.main_layout.addWidget(self.scroll)

        # Setup Area (Falls API Key fehlt)
        self.setup_widget = QWidget()
        self.setup_widget.hide()
        setup_layout = QVBoxLayout(self.setup_widget)
        setup_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        setup_layout.setSpacing(20)

        # Title
        title_lbl = QLabel(t('ui.steamgrid_setup.title'))
        title_lbl.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        setup_layout.addWidget(title_lbl)

        # Info Text
        info_lbl = QLabel(t('ui.steamgrid_setup.info') + "\n\n" +
                          t('ui.steamgrid_setup.step_1') + "\n" +
                          t('ui.steamgrid_setup.step_2') + "\n" +
                          t('ui.steamgrid_setup.step_3'))
        info_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        setup_layout.addWidget(info_lbl)

        # Action Buttons
        btn_layout = QHBoxLayout()
        get_key_btn = QPushButton(t('ui.steamgrid_setup.get_key_btn'))
        get_key_btn.setMinimumHeight(40)
        # Link zur API Seite
        get_key_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://www.steamgriddb.com/profile/preferences/api")))
        btn_layout.addWidget(get_key_btn)
        setup_layout.addLayout(btn_layout)

        # Input Field
        input_layout = QHBoxLayout()
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText(t('ui.steamgrid_setup.key_placeholder'))
        self.key_input.setMinimumHeight(35)
        input_layout.addWidget(self.key_input)

        save_btn = QPushButton(t('ui.steamgrid_setup.save_btn'))
        save_btn.setMinimumHeight(35)
        save_btn.clicked.connect(self._save_key_and_reload)
        input_layout.addWidget(save_btn)

        setup_layout.addLayout(input_layout)

        # Container Style
        self.setup_widget.setStyleSheet("background-color: #222; border-radius: 8px; padding: 20px;")
        # Zentriert anzeigen im Dialog
        wrapper_layout = QVBoxLayout()
        wrapper_layout.addStretch()
        wrapper_layout.addWidget(self.setup_widget)
        wrapper_layout.addStretch()

        # Wir fügen das Wrapper-Layout nicht direkt hinzu, sondern switchen visibility
        self.main_layout.addWidget(self.setup_widget)  # Add to main layout

    def _check_api_and_start(self):
        # Check ob Key da ist
        api = SteamGridDB()
        if not api.api_key:
            self.status_label.hide()
            self.scroll.hide()
            self.setup_widget.show()
        else:
            self.setup_widget.hide()
            self._start_search()

    def _save_key_and_reload(self):
        key = self.key_input.text().strip()
        if key:
            # Speichern
            config.STEAMGRIDDB_API_KEY = key

            # Persistent speichern via Settings Logic (Mini-Hack: wir laden settings, updaten, speichern)
            try:
                import json
                settings_file = config.DATA_DIR / 'settings.json'
                current_settings = {}
                if settings_file.exists():
                    with open(settings_file, 'r') as f:
                        current_settings = json.load(f)

                current_settings['steamgriddb_api_key'] = key

                with open(settings_file, 'w') as f:
                    json.dump(current_settings, f, indent=2)
            except Exception as e:
                print(f"Error saving key: {e}")

            # Reload View
            self._check_api_and_start()

    def _start_search(self):
        self.status_label.show()
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

        # Grid Logic (Row/Col)
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

        # Alten Inhalt löschen (falls Reload)
        # (Hier vereinfacht: Wir nehmen an, dass es beim ersten Mal leer ist)

        for item in items:
            img_widget = ClickableImage(self.img_type, w, h, metadata=item)

            load_url = item['thumb']
            mime = item.get('mime', '')
            if 'webp' in mime or 'gif' in mime:
                load_url = item['url']

            img_widget.load_image(load_url)

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