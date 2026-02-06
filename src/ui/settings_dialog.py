# src/ui/settings_dialog.py

"""
Settings dialog for application configuration.

This module provides a tabbed settings dialog where users can configure
language preferences, Steam paths, library locations, tag settings, backup
limits, and API keys.
"""

from typing import Dict
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QPushButton, QFileDialog, QLineEdit,
    QTabWidget, QWidget, QSpinBox, QCheckBox,
    QFormLayout, QGroupBox, QListWidget
)
from PyQt6.QtCore import pyqtSignal

from src.config import config
from src.utils.i18n import t
from src.ui.widgets.ui_helper import UIHelper


class SettingsDialog(QDialog):
    """
    Dialog for application settings configuration.

    This dialog provides two tabs (General and Other) for configuring various
    application settings including language, paths, APIs, and backup options.

    Signals:
        language_changed (str): Emitted when the UI language is changed, passes the language code.

    Attributes:
        tabs (QTabWidget): The tab widget containing General and Other tabs.
        combo_ui_lang (QComboBox): Dropdown for UI language selection.
        combo_tags_lang (QComboBox): Dropdown for tags language selection.
        path_edit (QLineEdit): Input field for Steam installation path.
        lib_list (QListWidget): List of additional Steam library folders.
        spin_tags (QSpinBox): Spinner for tags per game setting.
        check_common (QCheckBox): Checkbox for ignoring common tags.
        spin_backup (QSpinBox): Spinner for maximum backup files.
        steam_api_edit (QLineEdit): Input field for Steam Web API key.
        sgdb_key_edit (QLineEdit): Input field for SteamGridDB API key.
    """

    language_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        """
        Initializes the settings dialog.

        Args:
            parent: Parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.setWindowTitle(t('ui.settings.title'))
        # Slightly taller for the backup section
        self.resize(600, 700)
        self.setModal(True)

        self._create_ui()
        self._load_current_settings()

    def _create_ui(self):
        """Creates the user interface with tabs and buttons."""
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # --- TAB 1: GENERAL ---
        tab_general = QWidget()
        self._init_general_tab(tab_general)
        self.tabs.addTab(tab_general, t('ui.settings.tabs.general'))

        # --- TAB 2: OTHER ---
        tab_other = QWidget()
        self._init_other_tab(tab_other)
        self.tabs.addTab(tab_other, t('ui.settings.tabs.other'))

        # Buttons (Save / Cancel)
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton(t('common.save'))
        # noinspection PyUnresolvedReferences
        self.btn_save.clicked.connect(self.accept)

        self.btn_cancel = QPushButton(t('common.cancel'))
        # noinspection PyUnresolvedReferences
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def _init_general_tab(self, parent: QWidget):
        """
        Initializes the General tab with language, Steam path, and library settings.

        Args:
            parent (QWidget): The parent widget for this tab.
        """
        layout = QVBoxLayout(parent)

        # 1. LANGUAGE GROUP
        group_lang = QGroupBox(t('ui.settings.general.language'))
        form_lang = QFormLayout(group_lang)

        # UI Language
        self.combo_ui_lang = QComboBox()
        self.lang_map = {
            'en': '🇬🇧 English',
            'de': '🇩🇪 Deutsch',
            'es': '🇪🇸 Español',
            'fr': '🇫🇷 Français',
            'it': '🇮🇹 Italiano',
            'pt': '🇵🇹 Português',
            'zh': '🇨🇳 中文',
            'ja': '🇯🇵 日本語',
            'ko': '🇰🇷 한국어'
        }
        for code, name in self.lang_map.items():
            self.combo_ui_lang.addItem(name, code)

        # noinspection PyUnresolvedReferences
        self.combo_ui_lang.currentIndexChanged.connect(self._on_language_changed)
        form_lang.addRow(t('ui.settings.general.ui_language'), self.combo_ui_lang)

        # Tags Language
        self.combo_tags_lang = QComboBox()
        for code, name in self.lang_map.items():
            self.combo_tags_lang.addItem(name, code)
        form_lang.addRow(t('ui.settings.general.tag_language'), self.combo_tags_lang)

        # Restart Hint
        hint = QLabel(t('ui.settings.general.restart_required'))
        hint.setStyleSheet("color: gray; font-style: italic; font-size: 10px;")
        form_lang.addRow("", hint)

        layout.addWidget(group_lang)

        # 2. STEAM PATH GROUP
        group_path = QGroupBox(t('ui.settings.general.steam_path'))
        path_layout = QHBoxLayout(group_path)

        self.path_edit = QLineEdit()
        self.btn_browse_path = QPushButton(t('ui.settings.general.browse'))
        # noinspection PyUnresolvedReferences
        self.btn_browse_path.clicked.connect(self._browse_steam_path)

        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(self.btn_browse_path)
        layout.addWidget(group_path)

        # 3. STEAM LIBRARIES GROUP
        group_libs = QGroupBox(t('ui.settings.libraries.title'))
        lib_main_layout = QVBoxLayout(group_libs)

        self.lib_list = QListWidget()
        lib_main_layout.addWidget(self.lib_list)

        lib_btn_layout = QHBoxLayout()
        self.btn_add_lib = QPushButton(t('ui.settings.libraries.add'))
        # noinspection PyUnresolvedReferences
        self.btn_add_lib.clicked.connect(self._add_library)

        self.btn_remove_lib = QPushButton(t('ui.settings.libraries.remove'))
        # noinspection PyUnresolvedReferences
        self.btn_remove_lib.clicked.connect(self._remove_library)

        lib_btn_layout.addStretch()
        lib_btn_layout.addWidget(self.btn_add_lib)
        lib_btn_layout.addWidget(self.btn_remove_lib)

        lib_main_layout.addLayout(lib_btn_layout)
        layout.addWidget(group_libs)

    def _init_other_tab(self, parent: QWidget):
        """
        Initializes the Other tab with tags, backup, and API settings.

        Args:
            parent (QWidget): The parent widget for this tab.
        """
        layout = QVBoxLayout(parent)

        # 1. TAGS GROUP
        group_tags = QGroupBox(t('ui.settings.tags.title_group'))
        form_tags = QFormLayout(group_tags)

        self.spin_tags = QSpinBox()
        self.spin_tags.setRange(1, 50)
        form_tags.addRow(t('ui.settings.tags.count'), self.spin_tags)

        self.check_common = QCheckBox(t('ui.settings.tags.ignore_common'))
        form_tags.addRow("", self.check_common)
        layout.addWidget(group_tags)

        # 2. BACKUP GROUP
        group_backup = QGroupBox(t('ui.settings.backup.title_group'))
        form_backup = QFormLayout(group_backup)

        self.spin_backup = QSpinBox()
        self.spin_backup.setRange(1, 100)
        self.spin_backup.setSuffix(f" {t('ui.settings.backup.files')}")
        form_backup.addRow(t('ui.settings.backup.limit'), self.spin_backup)

        # Explanation text
        lbl_backup_help = QLabel(t('ui.settings.backup.explanation'))
        lbl_backup_help.setStyleSheet("color: gray; font-size: 10px; font-style: italic;")
        lbl_backup_help.setWordWrap(True)
        form_backup.addRow(lbl_backup_help)

        layout.addWidget(group_backup)

        # 3. API GROUP
        group_api = QGroupBox(t('ui.settings.api.title_group'))
        form_api = QFormLayout(group_api)

        # Steam Web API
        self.steam_api_edit = QLineEdit()
        self.steam_api_edit.setPlaceholderText(t('ui.settings.api.placeholder'))
        self.steam_api_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form_api.addRow(t('ui.settings.api.steam_label'), self.steam_api_edit)

        # SteamGridDB API
        self.sgdb_key_edit = QLineEdit()
        self.sgdb_key_edit.setPlaceholderText(t('ui.settings.api.placeholder'))
        self.sgdb_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form_api.addRow(t('ui.settings.api.sgdb_label'), self.sgdb_key_edit)

        layout.addWidget(group_api)
        layout.addStretch()

    def _load_current_settings(self):
        """Loads the current settings from config and populates the UI fields."""
        # General
        idx_ui = self.combo_ui_lang.findData(config.UI_LANGUAGE)
        if idx_ui >= 0: self.combo_ui_lang.setCurrentIndex(idx_ui)

        idx_tags = self.combo_tags_lang.findData(config.TAGS_LANGUAGE)
        if idx_tags >= 0: self.combo_tags_lang.setCurrentIndex(idx_tags)

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
        """Opens a directory browser for selecting the Steam installation path."""
        path = QFileDialog.getExistingDirectory(self, t('ui.settings.general.browse'), self.path_edit.text())
        if path:
            self.path_edit.setText(path)

    def _add_library(self):
        """Opens a directory browser for adding a new Steam library folder."""
        title = t('ui.settings.libraries.add')
        path = QFileDialog.getExistingDirectory(self, title)
        if path:
            # Avoid duplicates
            current_items = [self.lib_list.item(i).text() for i in range(self.lib_list.count())]
            if path not in current_items:
                self.lib_list.addItem(path)

    def _remove_library(self):
        """Removes the currently selected library folder from the list."""
        row = self.lib_list.currentRow()
        if row >= 0:
            if UIHelper.confirm(self, t('ui.settings.libraries.confirm_msg'),
                                t('ui.settings.libraries.confirm_remove')):
                self.lib_list.takeItem(row)

    def _on_language_changed(self, index: int):
        """
        Handles UI language changes.

        Args:
            index (int): The index of the selected language in the combo box.
        """
        code = self.combo_ui_lang.itemData(index)
        self.language_changed.emit(code)

    def get_settings(self) -> Dict:
        """
        Collects all settings from the dialog.

        Returns:
            Dict: A dictionary containing all configured settings.
        """
        libraries = []
        for i in range(self.lib_list.count()):
            libraries.append(self.lib_list.item(i).text())

        return {
            'ui_language': self.combo_ui_lang.currentData(),
            'tags_language': self.combo_tags_lang.currentData(),
            'steam_path': self.path_edit.text(),
            'tags_per_game': self.spin_tags.value(),
            'ignore_common_tags': self.check_common.isChecked(),
            'steam_api_key': self.steam_api_edit.text().strip(),
            'steamgriddb_api_key': self.sgdb_key_edit.text().strip(),
            'max_backups': self.spin_backup.value(),
            'steam_libraries': libraries
        }
