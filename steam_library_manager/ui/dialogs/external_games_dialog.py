#
# steam_library_manager/ui/dialogs/external_games_dialog.py
# Dialog for discovering and importing external game sources
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#


import logging
from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
)

from steam_library_manager.config import config
from steam_library_manager.core.shortcuts_manager import ShortcutsManager
from steam_library_manager.services.external_games_service import ExternalGamesService
from steam_library_manager.ui.widgets.base_dialog import BaseDialog
from steam_library_manager.ui.widgets.ui_helper import UIHelper
from steam_library_manager.utils.i18n import t
from steam_library_manager.utils.timeouts import THREAD_WAIT_LONG_MS

__all__ = ["ExternalGamesDialog"]

logger = logging.getLogger("steamlibmgr.external_games_dialog")


class _ScanThread(QThread):
    """Background thread that scans platforms for external games."""

    finished_scan = pyqtSignal(dict)

    def __init__(self, svc):
        super().__init__()
        self._svc = svc

    def run(self):
        try:
            res = self._svc.scan_all_platforms()
            self.finished_scan.emit(res)
        except Exception:
            logger.exception("Platform scan failed")
            self.finished_scan.emit({})


class _AddThread(QThread):
    """Background thread that batch-adds games to Steam shortcuts."""

    progress = pyqtSignal(int, int, str)
    finished_add = pyqtSignal(dict)

    def __init__(self, svc, games, cat_tag):
        super().__init__()
        self._svc = svc
        self._games = games
        self._cat_tag = cat_tag

    def run(self):
        try:
            tag = None
            stats = self._svc.batch_add_to_steam(
                self._games,
                progress_callback=self._emit_progress,
                category_tag=tag,
            )
            self.finished_add.emit(stats)
        except Exception:
            logger.exception("Batch add failed")
            self.finished_add.emit({"added": 0, "skipped": 0, "errors": len(self._games)})

    def _emit_progress(self, current, total, name):
        self.progress.emit(current, total, name)


class ExternalGamesDialog(BaseDialog):
    """Scan external launchers (Heroic, Lutris, etc.) and import
    discovered games into Steam as non-Steam shortcuts.
    """

    _COL_PLATFORM = 0
    _COL_NAME = 1
    _COL_PATH = 2
    _COL_STATUS = 3

    def __init__(self, parent=None):
        self._all_games = []
        self._existing_names = set()
        self._service = None
        self._scan_thread = None
        self._add_thread = None

        super().__init__(
            parent=parent,
            title_key="ui.external.title",
            min_width=800,
            buttons="custom",
        )

        self._init_svc()

    def _init_svc(self):
        # Hook up ExternalGamesService from Steam config
        steam_path = config.STEAM_PATH
        if not steam_path:
            logger.warning("No Steam path configured")
            return

        userdata = steam_path / "userdata"
        acct_id, _ = config.get_detected_user()
        if not acct_id:
            logger.warning("No Steam user detected")
            return

        try:
            mgr = ShortcutsManager(userdata, acct_id)
            self._service = ExternalGamesService(mgr)
        except Exception:
            logger.exception("Failed to initialize ExternalGamesService")

    def _build_content(self, layout):
        # Top row: scan button + platform filter
        top = QHBoxLayout()

        self._btn_scan = QPushButton(t("ui.external.scan"))
        self._btn_scan.clicked.connect(self._on_scan)
        top.addWidget(self._btn_scan)

        top.addStretch()

        lbl = QLabel(t("ui.external.filter_all") + ":")
        top.addWidget(lbl)

        self._filter_combo = QComboBox()
        self._filter_combo.addItem(t("ui.external.filter_all"), "")
        self._filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        self._filter_combo.setMinimumWidth(160)
        self._filter_combo.setMaxVisibleItems(10)
        top.addWidget(self._filter_combo)

        layout.addLayout(top)

        # Game table (4 columns)
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(
            [
                t("ui.external.col_platform"),
                t("ui.external.col_name"),
                t("ui.external.col_path"),
                t("ui.external.col_status"),
            ]
        )
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)

        hdr = self._table.horizontalHeader()
        if hdr:
            hdr.setSectionResizeMode(self._COL_PLATFORM, QHeaderView.ResizeMode.ResizeToContents)
            hdr.setSectionResizeMode(self._COL_NAME, QHeaderView.ResizeMode.Stretch)
            hdr.setSectionResizeMode(self._COL_PATH, QHeaderView.ResizeMode.Stretch)
            hdr.setSectionResizeMode(self._COL_STATUS, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self._table)

        # Status
        self._status_label = QLabel("")
        layout.addWidget(self._status_label)

        # Options
        opts = QHBoxLayout()
        self._chk_platform_tag = QCheckBox(t("ui.external.platform_tag"))
        self._chk_platform_tag.setChecked(True)
        opts.addWidget(self._chk_platform_tag)
        opts.addStretch()
        layout.addLayout(opts)

        # Progress
        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)

        self._progress_label = QLabel("")
        self._progress_label.setVisible(False)
        layout.addWidget(self._progress_label)

        # Action buttons
        btns = QHBoxLayout()
        btns.addStretch()

        self._btn_add_selected = QPushButton(t("ui.external.add_selected"))
        self._btn_add_selected.clicked.connect(self._on_add_selected)
        self._btn_add_selected.setEnabled(False)
        btns.addWidget(self._btn_add_selected)

        self._btn_add_all = QPushButton(t("ui.external.add_all"))
        self._btn_add_all.clicked.connect(self._on_add_all)
        self._btn_add_all.setEnabled(False)
        btns.addWidget(self._btn_add_all)

        self._btn_close = QPushButton(t("common.close"))
        self._btn_close.clicked.connect(self.reject)
        btns.addWidget(self._btn_close)

        layout.addLayout(btns)

    def closeEvent(self, event):  # type: ignore[override]
        # Wait for background threads before closing
        for thr in (self._scan_thread, self._add_thread):
            if thr and thr.isRunning():
                thr.wait(THREAD_WAIT_LONG_MS)
        super().closeEvent(event)

    # -- Scanning --

    def _on_scan(self):
        if not self._service:
            UIHelper.show_warning(self, t("ui.external.no_games"))
            return

        self._btn_scan.setEnabled(False)
        self._status_label.setText(t("ui.external.scanning"))
        self._table.setRowCount(0)
        self._all_games.clear()

        self._existing_names = self._service.get_existing_shortcuts()

        self._scan_thread = _ScanThread(self._service)
        self._scan_thread.finished_scan.connect(self._on_scan_done)
        self._scan_thread.start()

    def _on_scan_done(self, results):
        self._btn_scan.setEnabled(True)

        # Flatten results across all parsers
        self._all_games.clear()
        for games in results.values():
            self._all_games.extend(games)
        platforms = {g.platform for g in self._all_games}

        if not self._all_games:
            self._status_label.setText(t("ui.external.no_games"))
            self._btn_add_selected.setEnabled(False)
            self._btn_add_all.setEnabled(False)
            return

        # Rebuild filter combo with emulation sub-groups
        self._filter_combo.blockSignals(True)
        self._filter_combo.clear()
        self._filter_combo.addItem(t("ui.external.filter_all"), "")

        emu_pfx = "Emulation ("
        emu_plats = sorted(p for p in platforms if p.startswith(emu_pfx))
        other_plats = sorted(p for p in platforms if not p.startswith(emu_pfx))

        if emu_plats:
            self._filter_combo.addItem("Emulation (ROMs)", "emulation_all")
            for plat in emu_plats:
                system = plat[len(emu_pfx) : -1]
                self._filter_combo.addItem("    %s" % system, plat)

        for plat in other_plats:
            self._filter_combo.addItem(plat, plat)

        self._filter_combo.blockSignals(False)

        self._fill_table(self._all_games)

        exist_ct = sum(1 for g in self._all_games if g.name.lower() in self._existing_names)
        self._status_label.setText(t("ui.external.found_games", count=len(self._all_games), existing=exist_ct))

        has_new = exist_ct < len(self._all_games)
        self._btn_add_selected.setEnabled(has_new)
        self._btn_add_all.setEnabled(has_new)

    def _fill_table(self, games):
        # Populate table rows from game list
        self._table.setRowCount(len(games))

        for row, game in enumerate(games):
            exists = game.name.lower() in self._existing_names

            plat_item = QTableWidgetItem(game.platform)
            plat_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self._table.setItem(row, self._COL_PLATFORM, plat_item)

            name_item = QTableWidgetItem(game.name)
            name_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self._table.setItem(row, self._COL_NAME, name_item)

            path_txt = str(game.install_path) if game.install_path else ""
            path_item = QTableWidgetItem(path_txt)
            path_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self._table.setItem(row, self._COL_PATH, path_item)

            if exists:
                st_item = QTableWidgetItem(t("ui.external.already_exists"))
                st_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self._table.setItem(row, self._COL_STATUS, st_item)
            else:
                chk = QTableWidgetItem()
                chk.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
                chk.setCheckState(Qt.CheckState.Checked)
                self._table.setItem(row, self._COL_STATUS, chk)

    def _get_filtered_games(self):
        # Return games matching current platform filter
        pf = self._filter_combo.currentData()
        if not pf:
            return self._all_games
        if pf == "emulation_all":
            return [g for g in self._all_games if g.platform.startswith("Emulation (")]
        return [g for g in self._all_games if g.platform == pf]

    def _on_filter_changed(self, _idx):
        self._fill_table(self._get_filtered_games())

    # -- Adding games --

    def _get_checked(self):
        # Collect checked games from visible table rows
        picked = []
        visible = self._get_filtered_games()

        for row in range(self._table.rowCount()):
            item = self._table.item(row, self._COL_STATUS)
            if not item:
                continue
            if item.checkState() == Qt.CheckState.Checked:
                if row < len(visible):
                    picked.append(visible[row])
        return picked

    def _get_new_games(self):
        return [g for g in self._all_games if g.name.lower() not in self._existing_names]

    def _on_add_selected(self):
        games = self._get_checked()
        if not games:
            UIHelper.show_info(
                self,
                t("ui.external.select_games_first"),
                t("ui.external.no_selection"),
            )
            return
        self._start_add(games)

    def _on_add_all(self):
        games = self._get_new_games()
        if not games:
            return

        if not UIHelper.confirm(
            self,
            t("ui.external.confirm_add", count=len(games)),
            t("ui.external.title"),
        ):
            return

        self._start_add(games)

    def _start_add(self, games):
        if not self._service:
            return

        self._set_busy(True)
        self._progress_bar.setMaximum(len(games))
        self._progress_bar.setValue(0)

        use_tag = self._chk_platform_tag.isChecked()

        if use_tag:
            self._add_tagged(games)
        else:
            self._add_thread = _AddThread(self._service, games, False)
            self._add_thread.progress.connect(self._on_add_progress)
            self._add_thread.finished_add.connect(self._on_add_done)
            self._add_thread.start()

    def _add_tagged(self, games):
        # Add games one-by-one with per-platform collection tags
        self._progress_bar.setVisible(True)
        self._progress_label.setVisible(True)
        self._progress_bar.setMaximum(len(games))

        self._batch_stats = {"added": 0, "skipped": 0, "errors": 0}
        self._batch_games = games
        self._run_batch(0)

    def _run_batch(self, idx):
        # Process a chunk of games, then yield back to the event loop
        if idx >= len(self._batch_games):
            self._on_add_done(self._batch_stats)
            return

        end = min(idx + 5, len(self._batch_games))
        for i in range(idx, end):
            game = self._batch_games[i]
            self._progress_bar.setValue(i + 1)
            self._progress_label.setText(
                t("ui.external.adding_game", name=game.name, current=i + 1, total=len(self._batch_games))
            )
            try:
                tag = self._collection_name_for_platform(game.platform)
                if self._service and self._service.add_to_steam(game, category_tag=tag):
                    self._batch_stats["added"] += 1
                else:
                    self._batch_stats["skipped"] += 1
            except Exception:
                logger.exception("Error adding %s", game.name)
                self._batch_stats["errors"] += 1

        QTimer.singleShot(0, lambda: self._run_batch(end))

    @staticmethod
    def _collection_name_for_platform(platform):
        # Strip "Emulation (...)" wrapper to get clean collection name
        if platform.startswith("Emulation (") and platform.endswith(")"):
            return platform[len("Emulation (") : -1]
        return platform

    def _on_add_progress(self, current, total, name):
        self._progress_bar.setValue(current)
        self._progress_label.setText(t("ui.external.adding_game", name=name, current=current, total=total))

    def _on_add_done(self, stats):
        self._set_busy(False)

        # Refresh existing names for accurate display
        if self._service:
            self._existing_names = self._service.get_existing_shortcuts()

        self._fill_table(self._get_filtered_games())

        exist_ct = sum(1 for g in self._all_games if g.name.lower() in self._existing_names)
        self._status_label.setText(t("ui.external.found_games", count=len(self._all_games), existing=exist_ct))

        msg = t(
            "ui.external.complete_message",
            added=stats["added"],
            skipped=stats["skipped"],
            errors=stats["errors"],
        )
        if stats["added"] > 0:
            msg += "\n\n" + t("ui.external.restart_hint")

        UIHelper.show_success(self, msg, t("ui.external.complete"))

        has_new = exist_ct < len(self._all_games)
        self._btn_add_selected.setEnabled(has_new)
        self._btn_add_all.setEnabled(has_new)

    def _set_busy(self, busy):
        # Toggle UI elements during long operations
        self._btn_scan.setEnabled(not busy)
        self._btn_add_selected.setEnabled(not busy)
        self._btn_add_all.setEnabled(not busy)
        self._filter_combo.setEnabled(not busy)
        self._progress_bar.setVisible(busy)
        self._progress_label.setVisible(busy)
