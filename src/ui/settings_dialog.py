"""
Settings Dialog - Final Version (Dynamic Languages & Clean Code)
Save as: src/ui/settings_dialog.py
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QPushButton, QFileDialog, QLineEdit,
    QTabWidget, QWidget, QSpinBox, QCheckBox,
    QFormLayout, QGroupBox, QListWidget, QMessageBox
)
from PyQt6.QtCore import pyqtSignal
from pathlib import Path
import platform
import os
import vdf

# Import winreg only on Windows
if platform.system() == "Windows":
    import winreg

from src.config import config
from src.utils.i18n import t


class SettingsDialog(QDialog):
    """
    Settings Dialog providing configuration for Language, Paths, and APIs.
    """
    language_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t('ui.settings.title'))
        # Slightly taller for the backup section
        self.resize(600, 700)

        self._create_ui()
        self._load_current_settings()

    def _create_ui(self):
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()

        # --- TAB 1: GENERAL ---
        tab_general = QWidget()
        layout_gen = QVBoxLayout(tab_general)

        # 1. Language Section
        lang_group = QGroupBox(t('ui.settings.language'))
        lang_layout = QFormLayout()

        # UI Language
        self.combo_ui_lang = QComboBox()

        # List of supported languages matches the keys in de.json/en.json
        supported_langs = ["en", "de", "es", "pt", "fr", "it", "zh", "ja", "ko"]

        for code in supported_langs:
            # Fetches "🇬🇧 English", "🇩🇪 Deutsch" etc. from locales JSON
            label = t(f'ui.settings.languages.{code}')
            # Fallback if translation is missing
            if "Key not found" in label:
                label = code.upper()
            self.combo_ui_lang.addItem(label, code)

        lang_layout.addRow(t('ui.settings.ui_language'), self.combo_ui_lang)

        # Tags Language
        self.combo_tags_lang = QComboBox()
        # Mapping: API Value (Backend) -> Locale Code (Display)
        tags_mapping = [
            ("english", "en"),
            ("german", "de"),
            ("french", "fr"),
            ("spanish", "es"),
            ("italian", "it"),
            ("chinese", "zh"),
            ("japanese", "ja"),
            ("koreana", "ko"),
            ("portuguese", "pt")
        ]

        for api_val, lang_code in tags_mapping:
            label = t(f'ui.settings.languages.{lang_code}')
            if "Key not found" in label:
                label = api_val.title()
            self.combo_tags_lang.addItem(label, api_val)

        lang_layout.addRow(t('ui.settings.tags_language'), self.combo_tags_lang)

        lang_group.setLayout(lang_layout)
        layout_gen.addWidget(lang_group)

        # 2. Paths Section
        path_group = QGroupBox(t('ui.settings.paths'))
        path_layout = QVBoxLayout()

        path_layout.addWidget(QLabel(t('ui.settings.steam_path')))
        path_sub = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("/home/user/.steam/steam")
        btn_browse = QPushButton(t('ui.settings.browse'))
        btn_browse.clicked.connect(self._browse_steam_path)
        path_sub.addWidget(self.path_edit)
        path_sub.addWidget(btn_browse)
        path_layout.addLayout(path_sub)

        # Auto-Detect Button
        btn_auto = QPushButton(t('ui.settings.auto_detect'))
        btn_auto.clicked.connect(self._auto_detect_paths)
        path_layout.addWidget(btn_auto)

        path_group.setLayout(path_layout)
        layout_gen.addWidget(path_group)

        # 3. Libraries List
        lib_group = QGroupBox(t('ui.settings.libraries'))
        lib_layout = QVBoxLayout()

        self.lib_list = QListWidget()
        self.lib_list.setMaximumHeight(100)
        lib_layout.addWidget(self.lib_list)

        btn_lib_layout = QHBoxLayout()
        btn_add_lib = QPushButton(t('ui.settings.add_lib'))
        btn_add_lib.clicked.connect(self._add_library_path)
        btn_rem_lib = QPushButton(t('ui.settings.remove_lib'))
        btn_rem_lib.clicked.connect(self._remove_library_path)

        btn_lib_layout.addWidget(btn_add_lib)
        btn_lib_layout.addWidget(btn_rem_lib)
        lib_layout.addLayout(btn_lib_layout)

        lib_group.setLayout(lib_layout)
        layout_gen.addWidget(lib_group)

        layout_gen.addStretch()
        self.tabs.addTab(tab_general, t('ui.settings.tab_general'))

        # --- TAB 2: AUTOMATION ---
        tab_auto = QWidget()
        layout_auto = QVBoxLayout(tab_auto)

        auto_group = QGroupBox(t('ui.settings.automation_options'))
        auto_layout = QFormLayout()

        self.spin_tags = QSpinBox()
        self.spin_tags.setRange(1, 20)
        auto_layout.addRow(t('ui.settings.max_tags'), self.spin_tags)

        self.check_common = QCheckBox(t('ui.settings.ignore_common'))
        self.check_common.setToolTip(t('ui.auto_categorize.tooltip_ignore_common'))
        auto_layout.addRow("", self.check_common)

        auto_group.setLayout(auto_layout)
        layout_auto.addWidget(auto_group)

        # API Keys
        api_group = QGroupBox(t('ui.settings.api_keys'))
        api_layout = QFormLayout()

        self.sgdb_key_edit = QLineEdit()
        self.sgdb_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.sgdb_key_edit.setPlaceholderText(t('ui.settings.api_key_placeholder'))
        api_layout.addRow(t('ui.settings.api_key_sgdb'), self.sgdb_key_edit)

        # Link to get key
        link_text = t('ui.settings.get_api_key')
        lbl_sgdb_help = QLabel(f"<a href='https://www.steamgriddb.com/profile/preferences/api'>{link_text}</a>")
        lbl_sgdb_help.setOpenExternalLinks(True)
        api_layout.addRow("", lbl_sgdb_help)

        self.steam_key_edit = QLineEdit()
        self.steam_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        api_layout.addRow(t('ui.settings.api_key_steam'), self.steam_key_edit)

        api_group.setLayout(api_layout)
        layout_auto.addWidget(api_group)

        layout_auto.addStretch()
        self.tabs.addTab(tab_auto, t('ui.settings.tab_automation'))

        layout.addWidget(self.tabs)

        # Bottom Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        self.btn_cancel = QPushButton(t('ui.dialogs.cancel'))
        self.btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(self.btn_cancel)

        self.btn_save = QPushButton(t('ui.settings.save'))
        self.btn_save.setDefault(True)
        self.btn_save.clicked.connect(self._save_settings)
        btn_box.addWidget(self.btn_save)

        layout.addLayout(btn_box)

    def _load_current_settings(self):
        """Load values from config into UI."""
        # Language
        idx = self.combo_ui_lang.findData(config.get('ui_language', 'en'))
        if idx >= 0: self.combo_ui_lang.setCurrentIndex(idx)

        idx_tags = self.combo_tags_lang.findData(config.get('tags_language', 'english'))
        if idx_tags >= 0: self.combo_tags_lang.setCurrentIndex(idx_tags)

        # Paths
        self.path_edit.setText(config.get('steam_path', ''))

        # Libraries
        self.lib_list.clear()
        for lib in config.get('library_folders', []):
            self.lib_list.addItem(lib)

        # Automation
        self.spin_tags.setValue(config.get('max_tags_per_game', 3))
        self.check_common.setChecked(config.get('ignore_common_tags', True))

        # APIs
        self.sgdb_key_edit.setText(config.get('steamgriddb_api_key', ''))
        self.steam_key_edit.setText(config.get('steam_api_key', ''))

    def _save_settings(self):
        """Save values from UI to config."""
        new_ui_lang = self.combo_ui_lang.currentData()
        old_ui_lang = config.get('ui_language')

        config.set('ui_language', new_ui_lang)
        config.set('tags_language', self.combo_tags_lang.currentData())
        config.set('steam_path', self.path_edit.text().strip())
        config.set('max_tags_per_game', self.spin_tags.value())
        config.set('ignore_common_tags', self.check_common.isChecked())
        config.set('steamgriddb_api_key', self.sgdb_key_edit.text().strip())
        config.set('steam_api_key', self.steam_key_edit.text().strip())

        # Save libraries
        libs = [self.lib_list.item(i).text() for i in range(self.lib_list.count())]
        config.set('library_folders', libs)

        if config.save():
            QMessageBox.information(self, t('ui.dialogs.success'), t('ui.settings.saved'))

            # Emit signal if language changed
            if new_ui_lang != old_ui_lang:
                self.language_changed.emit(new_ui_lang)

            self.accept()
        else:
            QMessageBox.critical(self, t('ui.dialogs.error'), t('ui.settings.save_error'))

    def _auto_detect_paths(self):
        """Try to find Steam paths automatically."""
        found_path = None
        home = Path.home()

        # Common Linux paths
        possible_paths = [
            home / ".steam/steam",
            home / ".local/share/Steam",
            home / ".var/app/com.valvesoftware.Steam/.steam/steam"  # Flatpak
        ]

        # Windows paths
        if platform.system() == "Windows":
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
                steam_path, _ = winreg.QueryValueEx(key, "SteamPath")
                possible_paths.insert(0, Path(steam_path))
            except OSError:
                pass

        for p in possible_paths:
            if p.exists():
                found_path = p
                break

        if found_path:
            self.path_edit.setText(str(found_path))
            # Try to load libraries from libraryfolders.vdf
            self._scan_library_folders(found_path)
        else:
            QMessageBox.warning(self, t('ui.dialogs.error'), t('ui.settings.auto_detect_failed'))

    def _scan_library_folders(self, steam_path: Path):
        """Read libraryfolders.vdf to find other libraries."""
        vdf_path = steam_path / "steamapps" / "libraryfolders.vdf"
        if not vdf_path.exists():
            return

        try:
            with open(vdf_path, 'r', encoding='utf-8') as f:
                data = vdf.load(f)

            self.lib_list.clear()
            # Default library
            self.lib_list.addItem(str(steam_path / "steamapps"))

            # Additional libraries
            if 'libraryfolders' in data:
                for key, value in data['libraryfolders'].items():
                    if 'path' in value:
                        lib_path = Path(value['path']) / "steamapps"
                        # Avoid duplicates
                        existing = [self.lib_list.item(i).text() for i in range(self.lib_list.count())]
                        # Use os.path.normpath to safely compare paths
                        if os.path.normpath(lib_path) != os.path.normpath(str(steam_path / "steamapps")):
                            if str(lib_path) not in existing:
                                self.lib_list.addItem(str(lib_path))

        except (OSError, ValueError, KeyError) as e:
            # Usually logged, here printed as fallback
            print(t('ui.settings.library_read_error', error=e))

    def _browse_steam_path(self):
        """Open file dialog to select Steam path."""
        path = QFileDialog.getExistingDirectory(self, t('ui.settings.select_steam_dir'))
        if path:
            self.path_edit.setText(path)
            self._scan_library_folders(Path(path))

    def _add_library_path(self):
        """Add custom library path."""
        path = QFileDialog.getExistingDirectory(self, t('ui.settings.select_steam_dir'))
        if path:
            current_items = [self.lib_list.item(i).text() for i in range(self.lib_list.count())]
            if path not in current_items:
                self.lib_list.addItem(path)

    def _remove_library_path(self):
        """Remove selected path."""
        row = self.lib_list.currentRow()
        if row >= 0:
            reply = QMessageBox.question(
                self,
                t('ui.settings.confirm_remove_lib'),
                t('ui.settings.confirm_remove_lib_msg'),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.lib_list.takeItem(row)

    def get_settings(self) -> dict:
        """Returns the dictionary with all settings."""
        libraries = []
        for i in range(self.lib_list.count()):
            libraries.append(self.lib_list.item(i).text())

        return {
            'ui_language': self.combo_ui_lang.currentData(),
            'tags_language': self.combo_tags_lang.currentData(),
            'steam_path': self.path_edit.text(),
            'tags_per_game': self.spin_tags.value(),
            'ignore_common_tags': self.check_common.isChecked(),
            'steamgriddb_api_key': self.sgdb_key_edit.text().strip(),
            'steam_api_key': self.steam_key_edit.text().strip(),
            'library_folders': libraries
        }