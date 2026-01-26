"""
Settings Dialog - Sarah's Clean & Corrected Edition
Speichern als: src/ui/settings_dialog.py
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

# Nur bei Windows importieren wir winreg
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
        self.resize(600, 700)  # Etwas höher für die Backup-Sektion

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
        supported_langs = ["de", "en", "es", "pt", "fr", "it", "zh", "ja", "ko"]
        for code in supported_langs:
            label = t(f'ui.settings.languages.{code}')
            if "Key not found" in label:
                label = code.upper()
            self.combo_ui_lang.addItem(label, code)

        # KORREKTUR: Hier nutzen wir jetzt den richtigen Key 'ui.settings.language'
        lang_layout.addRow(t('ui.settings.language'), self.combo_ui_lang)

        # Tags Language
        self.combo_tags_lang = QComboBox()
        tags_mapping = [
            ("english", "en"),
            ("german", "de"),
            ("french", "fr"),
            ("spanish", "es"),
            ("italian", "it"),
            ("chinese", "zh"),
            ("japanese", "ja"),
            ("koreana", "ko")
        ]
        for api_val, lang_code in tags_mapping:
            label = t(f'ui.settings.languages.{lang_code}')
            self.combo_tags_lang.addItem(label, api_val)

        lang_layout.addRow(t('ui.settings.tags_language'), self.combo_tags_lang)

        lang_group.setLayout(lang_layout)
        layout_gen.addWidget(lang_group)

        # 2. Steam Path & Libraries Section
        path_group = QGroupBox(t('ui.settings.steam_path'))
        path_layout = QVBoxLayout()

        # Main Path
        main_path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        main_path_layout.addWidget(self.path_edit)

        btn_browse = QPushButton(t('ui.settings.select_steam_dir'))  # Falls Key fehlt: 'browse' nutzen
        btn_browse.clicked.connect(self._browse_path)
        main_path_layout.addWidget(btn_browse)

        btn_detect = QPushButton(t('ui.settings.auto_detect'))
        btn_detect.clicked.connect(self._auto_detect_libraries)
        main_path_layout.addWidget(btn_detect)

        path_layout.addLayout(main_path_layout)

        # Library List
        path_layout.addWidget(QLabel(t('ui.settings.libraries_label')))

        self.lib_list = QListWidget()
        self.lib_list.setAlternatingRowColors(True)
        self.lib_list.setMaximumHeight(150)
        path_layout.addWidget(self.lib_list)

        # Library Controls (+/- Buttons)
        lib_btn_layout = QHBoxLayout()
        lib_btn_layout.addStretch()

        btn_add_lib = QPushButton("+")
        btn_add_lib.setToolTip(t('ui.settings.add_lib'))
        btn_add_lib.setFixedWidth(30)
        btn_add_lib.clicked.connect(self._add_library_path)
        lib_btn_layout.addWidget(btn_add_lib)

        btn_remove_lib = QPushButton("-")
        btn_remove_lib.setToolTip(t('ui.settings.remove_lib'))
        btn_remove_lib.setFixedWidth(30)
        btn_remove_lib.clicked.connect(self._remove_library_path)
        lib_btn_layout.addWidget(btn_remove_lib)

        path_layout.addLayout(lib_btn_layout)

        path_group.setLayout(path_layout)
        layout_gen.addWidget(path_group)

        # 3. Backup Section (Verschoben von eigenem Tab hierher)
        backup_group = QGroupBox(t('ui.settings.tab_backup'))
        backup_layout = QFormLayout()

        self.backup_spin = QSpinBox()
        self.backup_spin.setRange(1, 50)
        backup_layout.addRow(t('ui.settings.backup_label'), self.backup_spin)

        backup_group.setLayout(backup_layout)
        layout_gen.addWidget(backup_group)

        # Filler
        layout_gen.addStretch()
        self.tabs.addTab(tab_general, t('ui.settings.tab_general'))

        # --- TAB 2: TAGS ---
        tab_tags = QWidget()
        layout_tags = QFormLayout(tab_tags)

        self.spin_tags = QSpinBox()
        self.spin_tags.setRange(1, 50)
        layout_tags.addRow(t('ui.settings.tags_count'), self.spin_tags)

        self.check_common = QCheckBox()
        layout_tags.addRow(t('ui.settings.ignore_common'), self.check_common)

        self.tabs.addTab(tab_tags, t('ui.settings.tab_tags'))

        # --- TAB 3: API ---
        tab_api = QWidget()
        layout_api = QFormLayout(tab_api)

        self.sgdb_key_edit = QLineEdit()
        layout_api.addRow(t('ui.settings.steamgriddb_label'), self.sgdb_key_edit)

        self.steam_api_edit = QLineEdit()
        self.steam_api_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout_api.addRow(t('ui.settings.steam_api_label'), self.steam_api_edit)

        info_lbl = QLabel(t('ui.settings.api_info'))
        info_lbl.setStyleSheet("color: gray; font-size: 0.9em;")
        layout_api.addRow("", info_lbl)

        self.tabs.addTab(tab_api, t('ui.settings.tab_api'))

        layout.addWidget(self.tabs)

        # --- FOOTER BUTTONS ---
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_save = QPushButton(t('ui.menu.save'))
        btn_save.clicked.connect(self.accept)
        btn_layout.addWidget(btn_save)

        btn_cancel = QPushButton(t('ui.dialogs.cancel'))
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        layout.addLayout(btn_layout)

    def _load_current_settings(self):
        """Loads settings from config into UI elements."""
        idx = self.combo_ui_lang.findData(config.UI_LANGUAGE)
        if idx >= 0: self.combo_ui_lang.setCurrentIndex(idx)

        idx = self.combo_tags_lang.findData(config.TAGS_LANGUAGE)
        if idx >= 0: self.combo_tags_lang.setCurrentIndex(idx)

        if config.STEAM_PATH:
            self.path_edit.setText(str(config.STEAM_PATH))
            self._parse_library_folders(Path(config.STEAM_PATH))

        self.spin_tags.setValue(config.TAGS_PER_GAME)
        self.check_common.setChecked(config.IGNORE_COMMON_TAGS)
        self.sgdb_key_edit.setText(config.STEAMGRIDDB_API_KEY or "")
        self.steam_api_edit.setText(config.STEAM_API_KEY or "")
        self.backup_spin.setValue(config.MAX_BACKUPS)

    def _browse_path(self):
        """Opens file dialog for Steam Main Path"""
        path = QFileDialog.getExistingDirectory(self, t('ui.settings.select_steam_dir'))
        if path:
            self.path_edit.setText(path)
            self._auto_detect_libraries()

    def _auto_detect_libraries(self):
        """
        Detects Steam path via Registry (Windows) or Standard Paths (Linux).
        """
        system = platform.system()
        base_path = None

        if system == "Windows":
            # Registry Check! Findet auch S:/ oder Z:/
            try:
                # KORREKTUR: Spezifisch OSError fangen, kein bare Exception
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
                val, _ = winreg.QueryValueEx(key, "SteamPath")
                if val:
                    # Windows paths in Registry sind oft mit forward slashes
                    base_path = Path(val)
            except OSError:
                # Fallback falls Registry Zugriff fehlschlägt (z.B. Berechtigungen)
                pass

        elif system == "Linux":
            home = Path.home()
            candidates = [
                home / ".local/share/Steam",
                home / ".steam/steam",
                home / ".steam/debian-installation"
            ]
            for c in candidates:
                if c.exists():
                    base_path = c
                    break

        if base_path and base_path.exists():
            self.path_edit.setText(str(base_path))
            self._parse_library_folders(base_path)
        else:
            # Fallback: Versuche aktuellen Text im Feld zu nutzen
            current = self.path_edit.text()
            if current:
                self._parse_library_folders(Path(current))

    def _parse_library_folders(self, steam_path: Path):
        """Reads libraryfolders.vdf and populates the list."""
        self.lib_list.clear()

        self.lib_list.addItem(str(steam_path))

        vdf_path = steam_path / 'steamapps' / 'libraryfolders.vdf'

        if not vdf_path.exists():
            vdf_path = steam_path / 'steamapps' / 'libraryfolders.vdf'

        if vdf_path.exists():
            try:
                with open(vdf_path, 'r', encoding='utf-8') as f:
                    data = vdf.load(f)

                folders = data.get('libraryfolders', {})
                for key, value in folders.items():
                    if isinstance(value, dict) and 'path' in value:
                        lib_path = value['path']
                        # Verhindert Duplikate
                        if os.path.normpath(lib_path) != os.path.normpath(str(steam_path)):
                            self.lib_list.addItem(lib_path)
            except (OSError, ValueError, KeyError):
                pass

    def _add_library_path(self):
        """Manually add a path."""
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
            'steam_api_key': self.steam_api_edit.text().strip(),
            'max_backups': self.backup_spin.value(),
            'steam_libraries': libraries
        }