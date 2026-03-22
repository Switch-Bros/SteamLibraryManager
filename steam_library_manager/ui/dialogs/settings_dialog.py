#
# steam_library_manager/ui/dialogs/settings_dialog.py
# Application settings dialog with tabbed configuration sections
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#
# TODO: add reset-to-defaults button?

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
    """Settings dialog with General and Other tabs."""

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
        # tabbed UI with save/close buttons
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # --- TAB 1: GENERAL ---
        tab_general = QWidget()
        self._init_general_tab(tab_general)
        self.tabs.addTab(tab_general, t("settings.tabs.general"))

        # --- TAB 2: OTHER ---
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
        # language, steam path, libraries
        layout = QVBoxLayout(parent)

        # 1. LANGUAGE GROUP
        grp_lang = QGroupBox(t("settings.general.language"))
        flang = QFormLayout(grp_lang)

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
        flang.addRow(t("settings.general.ui_language"), self.combo_ui_lang)

        # Tags Language
        self.combo_tags_lang = QComboBox()
        for code, name in self.lang_map.items():
            self.combo_tags_lang.addItem(name, code)
        flang.addRow(t("settings.general.tag_language"), self.combo_tags_lang)

        # Restart Hint
        hint = QLabel(t("settings.general.restart_required"))
        hint.setStyleSheet("color: gray; font-style: italic; font-size: 10px;")
        flang.addRow("", hint)

        layout.addWidget(grp_lang)

        # 2. STEAM PATH GROUP
        grp_path = QGroupBox(t("settings.general.steam_path"))
        playout = QHBoxLayout(grp_path)

        self.path_edit = QLineEdit()
        self.btn_browse_path = QPushButton(t("settings.general.browse"))
        # noinspection PyUnresolvedReferences
        self.btn_browse_path.clicked.connect(self._browse_steam_path)

        playout.addWidget(self.path_edit)
        playout.addWidget(self.btn_browse_path)
        layout.addWidget(grp_path)

        # 3. STEAM LIBRARIES GROUP
        grp_libs = QGroupBox(t("settings.libraries.title"))
        lib_layout = QVBoxLayout(grp_libs)

        self.lib_list = QListWidget()
        lib_layout.addWidget(self.lib_list)

        lib_btns = QHBoxLayout()
        self.btn_add_lib = QPushButton(t("common.add"))
        # noinspection PyUnresolvedReferences
        self.btn_add_lib.clicked.connect(self._add_library)

        self.btn_remove_lib = QPushButton(t("common.remove"))
        # noinspection PyUnresolvedReferences
        self.btn_remove_lib.clicked.connect(self._remove_library)

        lib_btns.addStretch()
        lib_btns.addWidget(self.btn_add_lib)
        lib_btns.addWidget(self.btn_remove_lib)

        lib_layout.addLayout(lib_btns)
        layout.addWidget(grp_libs)

    def _init_other_tab(self, parent: QWidget):
        # tags, backup, api keys
        layout = QVBoxLayout(parent)

        # 1. TAGS GROUP
        grp_tags = QGroupBox(t("settings.tags.title_group"))
        ftags = QFormLayout(grp_tags)

        self.spin_tags = QSpinBox()
        self.spin_tags.setRange(1, 50)
        ftags.addRow(t("settings.tags.count"), self.spin_tags)

        self.check_common = QCheckBox(t("settings.tags.ignore_common"))
        ftags.addRow("", self.check_common)
        layout.addWidget(grp_tags)

        # 2. BACKUP GROUP
        grp_bak = QGroupBox(t("settings.backup.title_group"))
        fbak = QFormLayout(grp_bak)

        self.spin_backup = QSpinBox()
        self.spin_backup.setRange(1, 100)
        self.spin_backup.setSuffix(" %s" % t("settings.backup.files"))
        fbak.addRow(t("settings.backup.limit"), self.spin_backup)

        bak_hint = QLabel(t("settings.backup.explanation"))
        bak_hint.setStyleSheet("color: gray; font-size: 10px; font-style: italic;")
        bak_hint.setWordWrap(True)
        fbak.addRow(bak_hint)

        layout.addWidget(grp_bak)

        # 3. API GROUP
        grp_api = QGroupBox(t("settings.api.title_group"))
        api_lay = QVBoxLayout(grp_api)

        # Steam Web API row
        api_lay.addWidget(QLabel(t("settings.api.steam_label")))
        srow = QHBoxLayout()
        self.steam_api_edit = QLineEdit()
        self.steam_api_edit.setPlaceholderText(t("settings.api.placeholder"))
        self.steam_api_edit.setEchoMode(QLineEdit.EchoMode.Password)
        srow.addWidget(self.steam_api_edit)
        btn_skey = QPushButton(t("settings.api.steam_get_key"))
        btn_skey.clicked.connect(lambda: open_url("https://steamcommunity.com/dev/apikey"))
        srow.addWidget(btn_skey)
        api_lay.addLayout(srow)

        # SteamGridDB API row
        api_lay.addWidget(QLabel(t("settings.api.sgdb_label")))
        sgrow = QHBoxLayout()
        self.sgdb_key_edit = QLineEdit()
        self.sgdb_key_edit.setPlaceholderText(t("settings.api.placeholder"))
        self.sgdb_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        sgrow.addWidget(self.sgdb_key_edit)
        btn_sgkey = QPushButton(t("settings.api.sgdb_get_key"))
        btn_sgkey.clicked.connect(lambda: open_url("https://www.steamgriddb.com/profile/preferences/api"))
        sgrow.addWidget(btn_sgkey)
        api_lay.addLayout(sgrow)

        # Help text
        api_hint = QLabel(t("settings.api.help_text"))
        api_hint.setStyleSheet("color: gray; font-size: 10px; font-style: italic;")
        api_hint.setWordWrap(True)
        api_lay.addWidget(api_hint)

        layout.addWidget(grp_api)
        layout.addStretch()

    def _load_current_settings(self):
        # fill form from config
        idx_ui = self.combo_ui_lang.findData(config.UI_LANGUAGE)
        if idx_ui >= 0:
            self.combo_ui_lang.setCurrentIndex(idx_ui)

        idx_tags = self.combo_tags_lang.findData(config.TAGS_LANGUAGE)
        if idx_tags >= 0:
            self.combo_tags_lang.setCurrentIndex(idx_tags)

        self.path_edit.setText(str(config.STEAM_PATH) if config.STEAM_PATH else "")

        # Libraries
        self.lib_list.clear()
        if config.STEAM_LIBRARIES:
            for lib in config.STEAM_LIBRARIES:
                self.lib_list.addItem(str(lib))

        # Other
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
            existing = [self.lib_list.item(i).text() for i in range(self.lib_list.count())]
            if path not in existing:
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
        # collect all settings into dict
        libs = []
        for i in range(self.lib_list.count()):
            libs.append(self.lib_list.item(i).text())

        return {
            "ui_language": self.combo_ui_lang.currentData(),
            "tags_language": self.combo_tags_lang.currentData(),
            "steam_path": self.path_edit.text(),
            "tags_per_game": self.spin_tags.value(),
            "ignore_common_tags": self.check_common.isChecked(),
            "steam_api_key": self.steam_api_edit.text().strip(),
            "steamgriddb_api_key": self.sgdb_key_edit.text().strip(),
            "max_backups": self.spin_backup.value(),
            "steam_libraries": libs,
        }
