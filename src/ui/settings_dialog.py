"""
Settings Dialog - User API Keys & .env Aware
Speichern als: src/ui/settings_dialog.py
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QComboBox, QPushButton, QFileDialog, QLineEdit,
                             QTabWidget, QWidget, QSpinBox, QCheckBox,
                             QFormLayout, QGroupBox)
from PyQt6.QtCore import pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices
from src.config import config
from src.utils.i18n import t


class SettingsDialog(QDialog):
    language_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t('ui.settings.title'))
        self.resize(600, 500)
        self._create_ui()
        self._load_current_settings()

    def _create_ui(self):
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()

        # --- TAB 1: GENERAL ---
        tab_general = QWidget()
        layout_gen = QVBoxLayout(tab_general)

        # Language
        lang_group = QGroupBox(t('ui.settings.language'))
        lang_layout = QFormLayout()

        self.combo_ui_lang = QComboBox()
        self.combo_ui_lang.addItem(t('ui.settings.languages.en'), "en")
        self.combo_ui_lang.addItem(t('ui.settings.languages.de'), "de")
        lang_layout.addRow(t('ui.settings.ui_language_label'), self.combo_ui_lang)

        self.combo_tags_lang = QComboBox()
        self.combo_tags_lang.addItem(t('ui.settings.languages.en'), "en")
        self.combo_tags_lang.addItem(t('ui.settings.languages.de'), "de")
        lang_layout.addRow(t('ui.settings.tags_language_label'), self.combo_tags_lang)
        lang_group.setLayout(lang_layout)
        layout_gen.addWidget(lang_group)

        # Steam Path
        path_group = QGroupBox(t('ui.settings.steam_path'))
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.browse_btn = QPushButton(t('ui.settings.browse'))
        self.browse_btn.clicked.connect(self._browse_path)
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(self.browse_btn)
        path_group.setLayout(path_layout)
        layout_gen.addWidget(path_group)

        layout_gen.addStretch()
        self.tabs.addTab(tab_general, t('ui.settings.general'))

        # --- TAB 2: API KEYS (NEU!) ---
        tab_api = QWidget()
        layout_api = QVBoxLayout(tab_api)

        # SteamGridDB
        sgdb_group = QGroupBox(t('ui.settings.steamgrid_api'))
        sgdb_layout = QVBoxLayout()

        sgdb_layout.addWidget(QLabel(t('ui.settings.steamgrid_help')))

        # Link Button
        get_key_btn = QPushButton(t('ui.settings.steamgrid_get_key'))
        get_key_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://www.steamgriddb.com/profile/preferences/api")))
        sgdb_layout.addWidget(get_key_btn)

        # Input Field
        self.sgdb_key_edit = QLineEdit()
        self.sgdb_key_edit.setPlaceholderText(t('ui.settings.steamgrid_key_placeholder'))
        # Wenn Key aus .env kommt (Dev Mode), Feld deaktivieren oder markieren
        if config.STEAMGRIDDB_API_KEY and not config.SETTINGS_FILE.exists():
            # Simpler Check: Wenn Key da ist, aber noch keine Settings gespeichert wurden, ist es wohl .env
            pass

        form_sgdb = QFormLayout()
        form_sgdb.addRow(t('ui.settings.steamgrid_key_label'), self.sgdb_key_edit)
        sgdb_layout.addLayout(form_sgdb)

        sgdb_group.setLayout(sgdb_layout)
        layout_api.addWidget(sgdb_group)

        layout_api.addStretch()
        self.tabs.addTab(tab_api, t('ui.settings.api_keys'))

        # --- TAB 3: AUTO-CATEGORIZATION ---
        tab_auto = QWidget()
        layout_auto = QVBoxLayout(tab_auto)

        self.spin_tags = QSpinBox()
        self.spin_tags.setRange(1, 20)
        self.check_common = QCheckBox(t('ui.settings.ignore_common_tags'))

        form_auto = QFormLayout()
        form_auto.addRow(t('ui.settings.tags_per_game'), self.spin_tags)
        form_auto.addRow("", self.check_common)

        layout_auto.addLayout(form_auto)
        layout_auto.addStretch()
        self.tabs.addTab(tab_auto, t('ui.settings.auto_categorization'))

        layout.addWidget(self.tabs)

        # Footer Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton(t('ui.settings.save'))
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton(t('ui.dialogs.cancel'))
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _load_current_settings(self):
        # UI Lang
        idx = self.combo_ui_lang.findData(config.UI_LANGUAGE)
        if idx >= 0: self.combo_ui_lang.setCurrentIndex(idx)

        # Tags Lang
        idx = self.combo_tags_lang.findData(config.TAGS_LANGUAGE)
        if idx >= 0: self.combo_tags_lang.setCurrentIndex(idx)

        if config.STEAM_PATH:
            self.path_edit.setText(str(config.STEAM_PATH))

        self.spin_tags.setValue(config.TAGS_PER_GAME)
        self.check_common.setChecked(config.IGNORE_COMMON_TAGS)

        # API Key laden (zeigt auch .env Key an, falls vorhanden, User kann ihn überschreiben)
        self.sgdb_key_edit.setText(config.STEAMGRIDDB_API_KEY)

    def _browse_path(self):
        path = QFileDialog.getExistingDirectory(self, t('ui.settings.select_steam_dir'))
        if path:
            self.path_edit.setText(path)

    def get_settings(self):
        return {
            'ui_language': self.combo_ui_lang.currentData(),
            'tags_language': self.combo_tags_lang.currentData(),
            'steam_path': self.path_edit.text(),
            'tags_per_game': self.spin_tags.value(),
            'ignore_common_tags': self.check_common.isChecked(),
            'steamgriddb_api_key': self.sgdb_key_edit.text().strip(),
            'max_backups': config.MAX_BACKUPS  # Wird hier nicht geändert, aber muss mit
        }

    def accept(self):
        new_lang = self.combo_ui_lang.currentData()
        if new_lang != config.UI_LANGUAGE:
            self.language_changed.emit(new_lang)
        super().accept()