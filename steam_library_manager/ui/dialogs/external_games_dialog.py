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
    # bg thread that scans platforms

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
    # bg thread for batch adding

    progress = pyqtSignal(int, int, str)
    finished_add = pyqtSignal(dict)

    def __init__(self, svc, games, cat_tag):
        super().__init__()
        self._svc = svc
        self._games = games
        self._tag = cat_tag  # TODO: unused? cleanup later

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

    def _emit_progress(self, cur, tot, name):
        self.progress.emit(cur, tot, name)


class ExternalGamesDialog(BaseDialog):
    """Scan external launchers (Heroic, Lutris, etc.) and import
    discovered games into Steam as non-Steam shortcuts.

    Yeah, this dialog is a bit messy but it works. The batch adding
    runs either threaded or chunked via QTimer depending on whether
    platform tags are enabled.
    """

    _COL_PLATFORM = 0
    _COL_NAME = 1
    _COL_PATH = 2
    _COL_STATUS = 3

    def __init__(self, parent=None):
        self._games = []  # all found games
        self._have_names = set()  # existing shortcut names
        self._svc = None  # ExternalGamesService
        self._thr_scan = None  # scan thread
        self._thr_add = None  # add thread

        super().__init__(
            parent=parent,
            title_key="ui.external.title",
            min_width=800,
            buttons="custom",
        )

        self._init_svc()

    def _init_svc(self):
        # hook up service from Steam config
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
            self._svc = ExternalGamesService(mgr)
        except Exception:
            logger.exception("Failed to initialize ExternalGamesService")

    def _build_content(self, layout):
        # top row: scan button + platform filter
        top = QHBoxLayout()

        self._scan_btn = QPushButton(t("ui.external.scan"))
        self._scan_btn.clicked.connect(self._on_scan)
        top.addWidget(self._scan_btn)

        top.addStretch()

        lbl = QLabel(t("ui.external.filter_all") + ":")
        top.addWidget(lbl)

        self._combo = QComboBox()
        self._combo.addItem(t("ui.external.filter_all"), "")
        self._combo.currentIndexChanged.connect(self._on_filter)
        self._combo.setMinimumWidth(160)
        self._combo.setMaxVisibleItems(10)
        top.addWidget(self._combo)

        layout.addLayout(top)

        # game table (4 columns)
        self._tbl = QTableWidget(0, 4)
        self._tbl.setHorizontalHeaderLabels(
            [
                t("ui.external.col_platform"),
                t("ui.external.col_name"),
                t("ui.external.col_path"),
                t("ui.external.col_status"),
            ]
        )
        self._tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._tbl.setAlternatingRowColors(True)

        hdr = self._tbl.horizontalHeader()
        if hdr:
            hdr.setSectionResizeMode(self._COL_PLATFORM, QHeaderView.ResizeMode.ResizeToContents)
            hdr.setSectionResizeMode(self._COL_NAME, QHeaderView.ResizeMode.Stretch)
            hdr.setSectionResizeMode(self._COL_PATH, QHeaderView.ResizeMode.Stretch)
            hdr.setSectionResizeMode(self._COL_STATUS, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self._tbl)

        # status
        self._status = QLabel("")
        layout.addWidget(self._status)

        # options
        opts = QHBoxLayout()
        self._chk_tag = QCheckBox(t("ui.external.platform_tag"))
        self._chk_tag.setChecked(True)
        opts.addWidget(self._chk_tag)
        opts.addStretch()
        layout.addLayout(opts)

        # progress
        self._prog = QProgressBar()
        self._prog.setVisible(False)
        layout.addWidget(self._prog)

        self._prog_lbl = QLabel("")
        self._prog_lbl.setVisible(False)
        layout.addWidget(self._prog_lbl)

        # action buttons
        btns = QHBoxLayout()
        btns.addStretch()

        self._btn_sel = QPushButton(t("ui.external.add_selected"))
        self._btn_sel.clicked.connect(self._on_add_sel)
        self._btn_sel.setEnabled(False)
        btns.addWidget(self._btn_sel)

        self._btn_all = QPushButton(t("ui.external.add_all"))
        self._btn_all.clicked.connect(self._on_add_all)
        self._btn_all.setEnabled(False)
        btns.addWidget(self._btn_all)

        self._close_btn = QPushButton(t("common.close"))
        self._close_btn.clicked.connect(self.reject)
        btns.addWidget(self._close_btn)

        layout.addLayout(btns)

    def closeEvent(self, event):
        # wait for bg threads before closing
        for thr in (self._thr_scan, self._thr_add):
            if thr and thr.isRunning():
                thr.wait(THREAD_WAIT_LONG_MS)
        super().closeEvent(event)

    # -- scanning --

    def _on_scan(self):
        if not self._svc:
            UIHelper.show_warning(self, t("ui.external.no_games"))
            return

        self._scan_btn.setEnabled(False)
        self._status.setText(t("ui.external.scanning"))
        self._tbl.setRowCount(0)
        self._games.clear()

        self._have_names = self._svc.get_existing_shortcuts()

        self._thr_scan = _ScanThread(self._svc)
        self._thr_scan.finished_scan.connect(self._scan_done)
        self._thr_scan.start()

    def _scan_done(self, res):
        self._scan_btn.setEnabled(True)

        # flatten results across all parsers
        self._games.clear()
        for lst in res.values():
            self._games.extend(lst)
        plats = {g.platform for g in self._games}

        if not self._games:
            self._status.setText(t("ui.external.no_games"))
            self._btn_sel.setEnabled(False)
            self._btn_all.setEnabled(False)
            return

        # rebuild filter combo with emulation sub-groups
        self._combo.blockSignals(True)
        self._combo.clear()
        self._combo.addItem(t("ui.external.filter_all"), "")

        emu_pfx = "Emulation ("
        emu_plats = sorted(p for p in plats if p.startswith(emu_pfx))
        other_plats = sorted(p for p in plats if not p.startswith(emu_pfx))

        if emu_plats:
            self._combo.addItem("Emulation (ROMs)", "emulation_all")
            for pf in emu_plats:
                system = pf[len(emu_pfx) : -1]
                self._combo.addItem("    %s" % system, pf)

        for pf in other_plats:
            self._combo.addItem(pf, pf)

        self._combo.blockSignals(False)

        self._fill(self._games)

        exist_ct = sum(1 for g in self._games if g.name.lower() in self._have_names)
        self._status.setText(t("ui.external.found_games", count=len(self._games), existing=exist_ct))

        has_new = exist_ct < len(self._games)
        self._btn_sel.setEnabled(has_new)
        self._btn_all.setEnabled(has_new)

    def _fill(self, games):
        # populate table rows from game list
        self._tbl.setRowCount(len(games))

        for r, gm in enumerate(games):
            exist = gm.name.lower() in self._have_names

            plat_item = QTableWidgetItem(gm.platform)
            plat_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self._tbl.setItem(r, self._COL_PLATFORM, plat_item)

            name_item = QTableWidgetItem(gm.name)
            name_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self._tbl.setItem(r, self._COL_NAME, name_item)

            path_txt = str(gm.install_path) if gm.install_path else ""
            path_item = QTableWidgetItem(path_txt)
            path_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self._tbl.setItem(r, self._COL_PATH, path_item)

            if exist:
                st_item = QTableWidgetItem(t("ui.external.already_exists"))
                st_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self._tbl.setItem(r, self._COL_STATUS, st_item)
            else:
                chk = QTableWidgetItem()
                chk.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
                chk.setCheckState(Qt.CheckState.Checked)
                self._tbl.setItem(r, self._COL_STATUS, chk)

    def _filtered(self):
        # return games matching current platform filter
        pf = self._combo.currentData()
        if not pf:
            return self._games
        if pf == "emulation_all":
            return [g for g in self._games if g.platform.startswith("Emulation (")]
        return [g for g in self._games if g.platform == pf]

    def _on_filter(self, _idx):
        self._fill(self._filtered())

    # -- adding games --

    def _checked(self):
        # collect checked games from visible table rows
        picked = []
        visible = self._filtered()

        for r in range(self._tbl.rowCount()):
            item = self._tbl.item(r, self._COL_STATUS)
            if not item:
                continue
            if item.checkState() == Qt.CheckState.Checked:
                if r < len(visible):
                    picked.append(visible[r])
        return picked

    def _new_games(self):
        return [g for g in self._games if g.name.lower() not in self._have_names]

    def _on_add_sel(self):
        lst = self._checked()
        if not lst:
            UIHelper.show_info(
                self,
                t("ui.external.select_games_first"),
                t("ui.external.no_selection"),
            )
            return
        self._start_add(lst)

    def _on_add_all(self):
        lst = self._new_games()
        if not lst:
            return

        if not UIHelper.confirm(
            self,
            t("ui.external.confirm_add", count=len(lst)),
            t("ui.external.title"),
        ):
            return

        self._start_add(lst)

    def _start_add(self, games):
        if not self._svc:
            return

        self._busy(True)
        self._prog.setMaximum(len(games))
        self._prog.setValue(0)

        use_tag = self._chk_tag.isChecked()

        if use_tag:
            self._add_tagged(games)
        else:
            self._thr_add = _AddThread(self._svc, games, False)
            self._thr_add.progress.connect(self._on_progress)
            self._thr_add.finished_add.connect(self._add_done)
            self._thr_add.start()

    def _add_tagged(self, games):
        # add games one-by-one with per-platform collection tags
        self._prog.setVisible(True)
        self._prog_lbl.setVisible(True)
        self._prog.setMaximum(len(games))

        self._batch_stats = {"added": 0, "skipped": 0, "errors": 0}
        self._batch_games = games
        self._run_chunk(0)

    def _run_chunk(self, idx):
        # process a chunk of games, then yield back to event loop
        if idx >= len(self._batch_games):
            self._add_done(self._batch_stats)
            return

        end = min(idx + 5, len(self._batch_games))
        for i in range(idx, end):
            gm = self._batch_games[i]
            self._prog.setValue(i + 1)
            self._prog_lbl.setText(
                t("ui.external.adding_game", name=gm.name, current=i + 1, total=len(self._batch_games))
            )
            try:
                tag = self._collection_name_for_platform(gm.platform)
                if self._svc and self._svc.add_to_steam(gm, category_tag=tag):
                    self._batch_stats["added"] += 1
                else:
                    self._batch_stats["skipped"] += 1
            except Exception:
                logger.exception("Error adding %s", gm.name)
                self._batch_stats["errors"] += 1

        QTimer.singleShot(0, lambda: self._run_chunk(end))

    @staticmethod
    def _collection_name_for_platform(platform):
        # strip "Emulation (...)" wrapper to get clean collection name
        if platform.startswith("Emulation (") and platform.endswith(")"):
            return platform[len("Emulation (") : -1]
        return platform

    def _on_progress(self, cur, tot, name):
        self._prog.setValue(cur)
        self._prog_lbl.setText(t("ui.external.adding_game", name=name, current=cur, total=tot))

    def _add_done(self, stats):
        self._busy(False)

        # refresh existing names for accurate display
        if self._svc:
            self._have_names = self._svc.get_existing_shortcuts()

        self._fill(self._filtered())

        exist_ct = sum(1 for g in self._games if g.name.lower() in self._have_names)
        self._status.setText(t("ui.external.found_games", count=len(self._games), existing=exist_ct))

        msg = t(
            "ui.external.complete_message",
            added=stats["added"],
            skipped=stats["skipped"],
            errors=stats["errors"],
        )
        if stats["added"] > 0:
            msg += "\n\n" + t("ui.external.restart_hint")

        UIHelper.show_success(self, msg, t("ui.external.complete"))

        has_new = exist_ct < len(self._games)
        self._btn_sel.setEnabled(has_new)
        self._btn_all.setEnabled(has_new)

    def _busy(self, flag):
        # toggle UI elements during long operations
        self._scan_btn.setEnabled(not flag)
        self._btn_sel.setEnabled(not flag)
        self._btn_all.setEnabled(not flag)
        self._combo.setEnabled(not flag)
        self._prog.setVisible(flag)
        self._prog_lbl.setVisible(flag)
