#
# steam_library_manager/ui/dialogs/settings_dialog.py
# Tabbed settings dialog for language, paths, tags, backups, and API keys
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QFileDialog,
    QLineEdit,
    QTabWidget,
    QWidget,
    QSpinBox,
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QListWidget,
)

from steam_library_manager.config import config
from steam_library_manager.ui.widgets.base_dialog import BaseDialog
from steam_library_manager.ui.widgets.ui_helper import UIHelper
from steam_library_manager.utils.i18n import t
from steam_library_manager.utils.open_url import open_url

__all__ = ["SettingsDialog"]


class SettingsDialog(BaseDialog):
    """Two-tab settings dialog (General + Other)."""

    language_changed = pyqtSignal(str)
    settings_saved = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(
            parent,
            title_key="settings.title",
            min_width=600,
            show_title_label=False,
            buttons="custom",
        )
        self.resize(600, 700)
        self._load_current_settings()

    def _build_content(self, layout: QVBoxLayout) -> None:
        """Creates the tabbed UI with buttons."""
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # General tab
        tab_general = QWidget()
        self._init_general_tab(tab_general)
        self.tabs.addTab(tab_general, t("settings.tabs.general"))

        # Other tab
        tab_other = QWidget()
        self._init_other_tab(tab_other)
        self.tabs.addTab(tab_other, t("settings.tabs.other"))

        # Buttons (Save / Close)
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton(t("common.save"))
        self.btn_save.clicked.connect(self._on_save)

        self.btn_close = QPushButton(t("common.close"))
        self.btn_close.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_close)
        layout.addLayout(btn_layout)

    def _init_general_tab(self, parent: QWidget):
        """Build the General tab: language, Steam path, libraries."""
        layout = QVBoxLayout(parent)

        # Language group
        group_lang = QGroupBox(t("settings.general.language"))
        form_lang = QFormLayout(group_lang)

        # UI Language
        self.combo_ui_lang = QComboBox()
        self.lang_map = {
            "en": "🇬🇧 English",
            "de": "🇩🇪 Deutsch",
            "es": "🇪🇸 Español",
            "fr": "🇫🇷 Français",
            "it": "🇮🇹 Italiano",
            "pt": "🇵🇹 Português",
            "zh": "🇨🇳 中文",
            "ja": "🇯🇵 日本語",
            "ko": "🇰🇷 한국어",
        }
        for code, name in self.lang_map.items():
            self.combo_ui_lang.addItem(name, code)

        # noinspection PyUnresolvedReferences
        self.combo_ui_lang.currentIndexChanged.connect(self._on_language_changed)
        form_lang.addRow(t("settings.general.ui_language"), self.combo_ui_lang)

        # Tags Language
        self.combo_tags_lang = QComboBox()
        for code, name in self.lang_map.items():
            self.combo_tags_lang.addItem(name, code)
        form_lang.addRow(t("settings.general.tag_language"), self.combo_tags_lang)

        # Restart Hint
        hint = QLabel(t("settings.general.restart_required"))
        hint.setStyleSheet("color: gray; font-style: italic; font-size: 10px;")
        form_lang.addRow("", hint)

        layout.addWidget(group_lang)

        # Steam path
        group_path = QGroupBox(t("settings.general.steam_path"))
        path_layout = QHBoxLayout(group_path)

        self.path_edit = QLineEdit()
        self.btn_browse_path = QPushButton(t("settings.general.browse"))
        # noinspection PyUnresolvedReferences
        self.btn_browse_path.clicked.connect(self._browse_steam_path)

        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(self.btn_browse_path)
        layout.addWidget(group_path)

        # Steam libraries
        group_libs = QGroupBox(t("settings.libraries.title"))
        lib_main_layout = QVBoxLayout(group_libs)

        self.lib_list = QListWidget()
        lib_main_layout.addWidget(self.lib_list)

        lib_btn_layout = QHBoxLayout()
        self.btn_add_lib = QPushButton(t("common.add"))
        # noinspection PyUnresolvedReferences
        self.btn_add_lib.clicked.connect(self._add_library)

        self.btn_remove_lib = QPushButton(t("common.remove"))
        # noinspection PyUnresolvedReferences
        self.btn_remove_lib.clicked.connect(self._remove_library)

        lib_btn_layout.addStretch()
        lib_btn_layout.addWidget(self.btn_add_lib)
        lib_btn_layout.addWidget(self.btn_remove_lib)

        lib_main_layout.addLayout(lib_btn_layout)
        layout.addWidget(group_libs)

    def _init_other_tab(self, parent: QWidget):
        """Build the Other tab: tags, backups, API keys."""
        layout = QVBoxLayout(parent)

        # Tags
        group_tags = QGroupBox(t("settings.tags.title_group"))
        form_tags = QFormLayout(group_tags)

        self.spin_tags = QSpinBox()
        self.spin_tags.setRange(1, 50)
        form_tags.addRow(t("settings.tags.count"), self.spin_tags)

        self.check_common = QCheckBox(t("settings.tags.ignore_common"))
        form_tags.addRow("", self.check_common)
        layout.addWidget(group_tags)

        # Backups
        group_backup = QGroupBox(t("settings.backup.title_group"))
        form_backup = QFormLayout(group_backup)

        self.spin_backup = QSpinBox()
        self.spin_backup.setRange(1, 100)
        self.spin_backup.setSuffix(f" {t('settings.backup.files')}")
        form_backup.addRow(t("settings.backup.limit"), self.spin_backup)

        lbl_backup_help = QLabel(t("settings.backup.explanation"))
        lbl_backup_help.setStyleSheet("color: gray; font-size: 10px; font-style: italic;")
        lbl_backup_help.setWordWrap(True)
        form_backup.addRow(lbl_backup_help)

        layout.addWidget(group_backup)

        # API keys
        group_api = QGroupBox(t("settings.api.title_group"))
        api_layout = QVBoxLayout(group_api)

        # Steam Web API row
        api_layout.addWidget(QLabel(t("settings.api.steam_label")))
        steam_row = QHBoxLayout()
        self.steam_api_edit = QLineEdit()
        self.steam_api_edit.setPlaceholderText(t("settings.api.placeholder"))
        self.steam_api_edit.setEchoMode(QLineEdit.EchoMode.Password)
        steam_row.addWidget(self.steam_api_edit)
        btn_steam_key = QPushButton(t("settings.api.steam_get_key"))
        btn_steam_key.clicked.connect(lambda: open_url("https://steamcommunity.com/dev/apikey"))
        steam_row.addWidget(btn_steam_key)
        api_layout.addLayout(steam_row)

        # SteamGridDB API row
        api_layout.addWidget(QLabel(t("settings.api.sgdb_label")))
        sgdb_row = QHBoxLayout()
        self.sgdb_key_edit = QLineEdit()
        self.sgdb_key_edit.setPlaceholderText(t("settings.api.placeholder"))
        self.sgdb_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        sgdb_row.addWidget(self.sgdb_key_edit)
        btn_sgdb_key = QPushButton(t("settings.api.sgdb_get_key"))
        btn_sgdb_key.clicked.connect(lambda: open_url("https://www.steamgriddb.com/profile/preferences/api"))
        sgdb_row.addWidget(btn_sgdb_key)
        api_layout.addLayout(sgdb_row)

        # Help text
        lbl_help = QLabel(t("settings.api.help_text"))
        lbl_help.setStyleSheet("color: gray; font-size: 10px; font-style: italic;")
        lbl_help.setWordWrap(True)
        api_layout.addWidget(lbl_help)

        layout.addWidget(group_api)
        layout.addStretch()

    def _load_current_settings(self):
        """Populate form fields from current config."""
        idx_ui = self.combo_ui_lang.findData(config.UI_LANGUAGE)
        if idx_ui >= 0:
            self.combo_ui_lang.setCurrentIndex(idx_ui)

        idx_tags = self.combo_tags_lang.findData(config.TAGS_LANGUAGE)
        if idx_tags >= 0:
            self.combo_tags_lang.setCurrentIndex(idx_tags)

        self.path_edit.setText(str(config.STEAM_PATH) if config.STEAM_PATH else "")

        self.lib_list.clear()
        if config.STEAM_LIBRARIES:
            for lib in config.STEAM_LIBRARIES:
                self.lib_list.addItem(str(lib))

        self.spin_tags.setValue(config.TAGS_PER_GAME)
        self.check_common.setChecked(config.IGNORE_COMMON_TAGS)
        self.spin_backup.setValue(config.MAX_BACKUPS)
        self.steam_api_edit.setText(config.STEAM_API_KEY or "")
        self.sgdb_key_edit.setText(config.STEAMGRIDDB_API_KEY or "")

    def _browse_steam_path(self):
        path = QFileDialog.getExistingDirectory(self, t("settings.general.browse"), self.path_edit.text())
        if path:
            self.path_edit.setText(path)

    def _add_library(self):
        title = t("common.add")
        path = QFileDialog.getExistingDirectory(self, title)
        if path:
            current_items = [self.lib_list.item(i).text() for i in range(self.lib_list.count())]
            if path not in current_items:
                self.lib_list.addItem(path)

    def _remove_library(self):
        row = self.lib_list.currentRow()
        if row >= 0:
            if UIHelper.confirm(self, t("settings.libraries.confirm_msg"), t("settings.libraries.confirm_remove")):
                self.lib_list.takeItem(row)

    def _on_language_changed(self, index: int):
        code = self.combo_ui_lang.itemData(index)
        self.language_changed.emit(code)

    def _on_save(self) -> None:
        self.settings_saved.emit(self.get_settings())

    def get_settings(self) -> dict:
        """Return all settings as a dict."""
        libraries = []
        for i in range(self.lib_list.count()):
            libraries.append(self.lib_list.item(i).text())

        return {
            "ui_language": self.combo_ui_lang.currentData(),
            "tags_language": self.combo_tags_lang.currentData(),
            "steam_path": self.path_edit.text(),
            "tags_per_game": self.spin_tags.value(),
            "ignore_common_tags": self.check_common.isChecked(),
            "steam_api_key": self.steam_api_edit.text().strip(),
            "steamgriddb_api_key": self.sgdb_key_edit.text().strip(),
            "max_backups": self.spin_backup.value(),
            "steam_libraries": libraries,
        }
