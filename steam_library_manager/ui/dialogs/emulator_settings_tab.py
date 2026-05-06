#
# steam_library_manager/ui/dialogs/emulator_settings_tab.py
# Settings tab for emulator detection + per-emulator user overrides
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from steam_library_manager.utils.i18n import t

__all__ = ["EmulatorSettingsTab"]

logger = logging.getLogger("steamlibmgr.ui.emulator_settings_tab")


class EmulatorSettingsTab(QWidget):
    """Settings tab showing detected emulators + their game directories.

    Layout: top half is a table of all known emulators (status, name, executable,
    enabled toggle). Bottom half is a details panel for the selected emulator
    with its game-dir list and add/remove buttons.
    """

    # emitted when a setting changes that the parent dialog should react to
    settings_changed = pyqtSignal()

    _COL_STATUS = 0
    _COL_NAME = 1
    _COL_EXEC = 2
    _COL_ENABLED = 3

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = None
        self._installed_cache: list = []
        self._build_ui()

    # ---- public API ----

    def set_service(self, service) -> None:
        """Inject the EmulatorService once it is available."""
        self._service = service
        self.refresh()

    def refresh(self) -> None:
        """Reload the emulator table from the service. Cheap if nothing changed."""
        if self._service is None:
            self._show_unavailable()
            return
        try:
            installed = self._service.detect_installed_emulators()
        except Exception:
            logger.exception("emulator detect failed")
            self._show_unavailable()
            return
        self._installed_cache = installed
        self._populate_table()
        self._populate_details(None)

    # ---- UI construction ----

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)

        intro = QLabel(t("settings.emulators.intro"))
        intro.setWordWrap(True)
        intro.setStyleSheet("color: gray; font-style: italic;")
        outer.addWidget(intro)

        splitter = QSplitter(Qt.Orientation.Vertical)
        outer.addWidget(splitter, 1)

        # --- top: emulator table ---
        top = QWidget()
        top_lyt = QVBoxLayout(top)
        top_lyt.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            [
                t("settings.emulators.col_status"),
                t("settings.emulators.col_name"),
                t("settings.emulators.col_executable"),
                t("settings.emulators.col_enabled"),
            ]
        )
        self.table.horizontalHeader().setSectionResizeMode(self._COL_NAME, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(self._COL_EXEC, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        # noinspection PyUnresolvedReferences
        self.table.itemSelectionChanged.connect(self._on_row_selected)
        top_lyt.addWidget(self.table)

        # action row
        actions = QHBoxLayout()
        self.btn_rescan = QPushButton(t("settings.emulators.rescan"))
        # noinspection PyUnresolvedReferences
        self.btn_rescan.clicked.connect(self._on_rescan)
        actions.addWidget(self.btn_rescan)
        actions.addStretch()
        top_lyt.addLayout(actions)

        splitter.addWidget(top)

        # --- bottom: details panel ---
        self.details = QGroupBox(t("settings.emulators.details_title"))
        det_lyt = QVBoxLayout(self.details)

        self.detail_label = QLabel(t("settings.emulators.select_hint"))
        self.detail_label.setStyleSheet("font-weight: bold;")
        det_lyt.addWidget(self.detail_label)

        self.dir_list = QListWidget()
        det_lyt.addWidget(self.dir_list)

        dir_btns = QHBoxLayout()
        self.btn_add_dir = QPushButton(t("settings.emulators.add_dir"))
        self.btn_remove_dir = QPushButton(t("settings.emulators.remove_dir"))
        # noinspection PyUnresolvedReferences
        self.btn_add_dir.clicked.connect(self._on_add_dir)
        # noinspection PyUnresolvedReferences
        self.btn_remove_dir.clicked.connect(self._on_remove_dir)
        dir_btns.addWidget(self.btn_add_dir)
        dir_btns.addWidget(self.btn_remove_dir)
        dir_btns.addStretch()

        self.btn_set_default = QPushButton(t("settings.emulators.set_default"))
        # noinspection PyUnresolvedReferences
        self.btn_set_default.clicked.connect(self._on_set_default)
        dir_btns.addWidget(self.btn_set_default)

        self.btn_set_exe = QPushButton(t("settings.emulators.set_executable"))
        # noinspection PyUnresolvedReferences
        self.btn_set_exe.clicked.connect(self._on_set_executable)
        dir_btns.addWidget(self.btn_set_exe)

        det_lyt.addLayout(dir_btns)

        self.btn_add_dir.setEnabled(False)
        self.btn_remove_dir.setEnabled(False)
        self.btn_set_default.setEnabled(False)
        self.btn_set_exe.setEnabled(False)

        splitter.addWidget(self.details)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

    # ---- table ----

    def _populate_table(self) -> None:
        self.table.setRowCount(0)
        for ie in sorted(self._installed_cache, key=lambda e: e.name):
            row = self.table.rowCount()
            self.table.insertRow(row)

            status_icon = self._status_icon(ie.source)
            status_item = QTableWidgetItem(status_icon)
            status_item.setToolTip(self._status_tooltip(ie.source))
            self.table.setItem(row, self._COL_STATUS, status_item)

            name_item = QTableWidgetItem(ie.name)
            self.table.setItem(row, self._COL_NAME, name_item)

            exe_item = QTableWidgetItem(self._format_executable(ie.executable))
            self.table.setItem(row, self._COL_EXEC, exe_item)

            settings = self._get_settings(ie.name)
            enabled = settings.get("enabled", True)
            enabled_item = QTableWidgetItem(t("common.yes") if enabled else t("common.no"))
            enabled_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, self._COL_ENABLED, enabled_item)

    def _status_icon(self, source: str) -> str:
        # plain ASCII, no emoji - readable in all terminals/themes
        if source == "flatpak":
            return "[FLATPAK]"
        if source == "system":
            return "[SYSTEM]"
        if source == "appimage":
            return "[APPIMAGE]"
        if source == "user_override":
            return "[CUSTOM]"
        if source == "config_only":
            return "[CONFIG]"
        return "[?]"

    @staticmethod
    def _status_tooltip(source: str) -> str:
        return {
            "flatpak": t("settings.emulators.tip_flatpak"),
            "system": t("settings.emulators.tip_system"),
            "appimage": t("settings.emulators.tip_appimage"),
            "user_override": t("settings.emulators.tip_override"),
            "config_only": t("settings.emulators.tip_config_only"),
        }.get(source, "")

    @staticmethod
    def _format_executable(p: Path) -> str:
        s = str(p)
        if s.startswith("/flatpak/"):
            return "flatpak: %s" % s[len("/flatpak/") :]
        if s.startswith("/missing/"):
            return t("settings.emulators.no_executable")
        return s

    # ---- selection / details ----

    def _on_row_selected(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            self._populate_details(None)
            return
        name_item = self.table.item(row, self._COL_NAME)
        if not name_item:
            return
        self._populate_details(name_item.text())

    def _populate_details(self, emulator_name: str | None) -> None:
        self.dir_list.clear()
        if not emulator_name:
            self.detail_label.setText(t("settings.emulators.select_hint"))
            self.btn_add_dir.setEnabled(False)
            self.btn_remove_dir.setEnabled(False)
            self.btn_set_default.setEnabled(False)
            return

        self.detail_label.setText(emulator_name)
        ie = self._lookup(emulator_name)
        # auto-detected dirs from emulator config (read-only)
        if ie is not None:
            for d in ie.game_dirs:
                item = QListWidgetItem("[%s] %s" % (t("settings.emulators.dir_auto"), d))
                item.setData(Qt.ItemDataRole.UserRole, ("auto", str(d)))
                self.dir_list.addItem(item)

        # user custom dirs
        settings = self._get_settings(emulator_name)
        for d in settings.get("custom_game_dirs", []):
            item = QListWidgetItem("[%s] %s" % (t("settings.emulators.dir_user"), d))
            item.setData(Qt.ItemDataRole.UserRole, ("user", str(d)))
            self.dir_list.addItem(item)

        self.btn_add_dir.setEnabled(True)
        self.btn_remove_dir.setEnabled(True)
        self.btn_set_default.setEnabled(ie is not None and len(ie.systems) >= 1)
        self.btn_set_exe.setEnabled(True)

    # ---- buttons ----

    def _on_rescan(self) -> None:
        if self._service is None:
            return
        try:
            self._service.discover_libraries()
        except Exception:
            logger.exception("rescan failed")
        self.refresh()
        self.settings_changed.emit()

    def _on_add_dir(self) -> None:
        emu = self._current_emulator()
        if not emu:
            return
        path = QFileDialog.getExistingDirectory(self, t("settings.emulators.add_dir"))
        if not path or self._service is None:
            return
        self._service.add_user_game_dir(emu, Path(path))
        self._populate_details(emu)
        self.settings_changed.emit()

    def _on_remove_dir(self) -> None:
        emu = self._current_emulator()
        if not emu:
            return
        item = self.dir_list.currentItem()
        if not item or self._service is None:
            return
        kind, path = item.data(Qt.ItemDataRole.UserRole)
        if kind != "user":
            # auto-detected dirs cannot be removed - they come from the emulator's own config
            return
        self._service.remove_user_game_dir(emu, Path(path))
        self._populate_details(emu)
        self.settings_changed.emit()

    def _on_set_default(self) -> None:
        emu = self._current_emulator()
        if not emu or self._service is None:
            return
        ie = self._lookup(emu)
        if ie is None or not ie.systems:
            return
        # for now: set as default for ALL its systems. Per-system picker can come later.
        for sys_id in ie.systems:
            self._service.set_default_emulator_for_system(sys_id, emu)
        self.settings_changed.emit()

    def _on_set_executable(self) -> None:
        emu = self._current_emulator()
        if not emu or self._service is None:
            return
        path, _ = QFileDialog.getOpenFileName(self, t("settings.emulators.set_executable"))
        if not path:
            return
        self._service.set_executable_override(emu, path)
        self.refresh()
        self.settings_changed.emit()

    # ---- helpers ----

    def _current_emulator(self) -> str | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, self._COL_NAME)
        return item.text() if item else None

    def _lookup(self, name: str):
        for ie in self._installed_cache:
            if ie.name == name:
                return ie
        return None

    def _get_settings(self, name: str) -> dict:
        if self._service is None:
            return {}
        try:
            s = self._service._db.get_emulator_settings(name)
            return s or {}
        except Exception:
            return {}

    def _show_unavailable(self) -> None:
        self.table.setRowCount(0)
        self.detail_label.setText(t("settings.emulators.unavailable"))
        self.btn_add_dir.setEnabled(False)
        self.btn_remove_dir.setEnabled(False)
        self.btn_set_default.setEnabled(False)
        self.btn_set_exe.setEnabled(False)
        self.btn_rescan.setEnabled(False)
