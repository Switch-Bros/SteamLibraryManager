#
# steam_library_manager/ui/dialogs/curator_management_dialog.py
# Dialog for managing Steam Curators
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

import logging

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from steam_library_manager.ui.widgets.base_dialog import BaseDialog
from steam_library_manager.ui.widgets.ui_helper import UIHelper
from steam_library_manager.utils.i18n import t

__all__ = ["CuratorManagementDialog"]

logger = logging.getLogger("steamlibmgr.curator_management_dialog")

# column indices
_COL_ACT = 0
_COL_NAME = 1
_COL_CNT = 2
_COL_UPD = 3


class CuratorManagementDialog(BaseDialog):
    """Manage Steam Curators: add/remove, import/export,
    auto-discover from existing collections.

    TODO: refactor this mess, too many nested dialogs
    """

    def __init__(self, parent, db_path, existing_collection_names=None):
        self._db_path = db_path
        self._db = None
        self._existing = existing_collection_names or set()  # existing colls

        super().__init__(
            parent,
            title_key="ui.curator.title",
            min_width=700,
            buttons="custom",
        )

    def _build_content(self, lyt):
        self._open()

        # table
        self._tbl = QTableWidget(0, 4)
        self._tbl.setHorizontalHeaderLabels(
            [
                t("ui.curator.col_active"),
                t("ui.curator.col_name"),
                t("ui.curator.col_count"),
                t("ui.curator.col_updated"),
            ]
        )
        self._tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._tbl.setAlternatingRowColors(True)

        hdr = self._tbl.horizontalHeader()
        hdr.setSectionResizeMode(_COL_ACT, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(_COL_NAME, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(_COL_CNT, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(_COL_UPD, QHeaderView.ResizeMode.ResizeToContents)
        self._tbl.setColumnWidth(_COL_ACT, 60)
        self._tbl.setColumnWidth(_COL_CNT, 80)

        lyt.addWidget(self._tbl)

        # buttons
        row = QHBoxLayout()

        btn_add = QPushButton(t("ui.curator.add"))
        btn_add.clicked.connect(self._add)
        row.addWidget(btn_add)

        btn_pop = QPushButton(t("ui.curator.popular"))
        btn_pop.clicked.connect(self._pop)
        row.addWidget(btn_pop)

        btn_rm = QPushButton(t("ui.curator.remove"))
        btn_rm.clicked.connect(self._rm)
        row.addWidget(btn_rm)

        btn_exp = QPushButton(t("ui.curator.export"))
        btn_exp.clicked.connect(self._exp)
        row.addWidget(btn_exp)

        btn_imp = QPushButton(t("ui.curator.import_btn"))
        btn_imp.clicked.connect(self._imp)
        row.addWidget(btn_imp)

        btn_top = QPushButton(t("ui.curator.top_curators"))
        btn_top.clicked.connect(self._top)
        row.addWidget(btn_top)

        row.addStretch()

        close = QPushButton(t("common.close"))
        close.clicked.connect(self.accept)
        row.addWidget(close)

        lyt.addLayout(row)

        # auto-register curators whose collections already exist
        self._sync()
        self._refresh()

    # -- auto-sync --

    @staticmethod
    def _norm(n):
        import re

        cleaned = re.sub(r"\W", "", n, flags=re.UNICODE)
        cleaned = re.sub(r"[^a-zA-Z0-9]", "", cleaned)
        return cleaned.lower()

    def _matches(self, cname):
        # check if any existing collection matches this curator
        if cname in self._existing:
            return True
        norm = self._norm(cname)
        for cn in self._existing:
            if self._norm(cn) == norm:
                return True
        return False

    def _sync(self):
        # register known curators whose Steam collections already exist
        if not self._db or not self._existing:
            return

        from steam_library_manager.services.curator_presets import POPULAR_CURATORS

        known = {c["curator_id"] for c in self._db.get_all_curators()}
        n = 0

        for p in POPULAR_CURATORS:
            if p.curator_id in known:
                continue
            if self._matches(p.name):
                url = "https://store.steampowered.com/curator/%d/" % p.curator_id
                self._db.add_curator(p.curator_id, p.name, url, src="auto")
                n += 1

        if n:
            self._db.commit()
            logger.info("Auto-registered %d curators from existing collections", n)

    # -- table --

    def _refresh(self):
        if not self._db:
            return

        curs = self._db.get_all_curators()
        self._tbl.setRowCount(len(curs))

        for r, c in enumerate(curs):
            # active checkbox
            wrap = QWidget()
            wl = QHBoxLayout(wrap)
            wl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            wl.setContentsMargins(0, 0, 0, 0)
            cb = QCheckBox()
            cb.setChecked(bool(c["active"]))
            cid = c["curator_id"]
            cb.toggled.connect(lambda checked, x=cid: self._toggle(x, checked))
            wl.addWidget(cb)
            self._tbl.setCellWidget(r, _COL_ACT, wrap)

            # name
            it = QTableWidgetItem(c["name"])
            it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self._tbl.setItem(r, _COL_NAME, it)

            # count
            cnt = c.get("total_count", 0) or 0
            it = QTableWidgetItem(str(cnt))
            it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._tbl.setItem(r, _COL_CNT, it)

            # last updated
            upd = c.get("last_updated") or t("common.never")
            it = QTableWidgetItem(str(upd))
            it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self._tbl.setItem(r, _COL_UPD, it)

    # -- actions --

    def _toggle(self, cid, active):
        if self._db:
            self._db.toggle_curator_active(cid, active)

    def _add(self):
        from steam_library_manager.services.curator_client import CuratorClient

        txt, ok = QInputDialog.getText(
            self,
            t("ui.curator.add"),
            t("ui.curator.add_prompt"),
        )
        if not ok or not txt.strip():
            return

        txt = txt.strip()
        cid = CuratorClient.parse_id(txt)
        if not cid:
            UIHelper.show_warning(self, t("ui.curator.invalid_url"))
            return

        raw = CuratorClient.parse_name(txt)
        name = raw or "Curator %d" % cid
        url = txt if txt.startswith("http") else "https://store.steampowered.com/curator/%d/" % cid

        if self._db:
            self._db.add_curator(cid, name, url)
            self._refresh()

    def _pop(self):
        from steam_library_manager.services.curator_presets import POPULAR_CURATORS

        if not self._db:
            return

        known = {c["curator_id"] for c in self._db.get_all_curators()}

        dlg = QDialog(self)
        dlg.setWindowTitle(t("ui.curator.popular_title"))
        dlg.setMinimumWidth(500)
        dlg.setMaximumHeight(600)
        dlg.setModal(True)

        vl = QVBoxLayout(dlg)

        info = QLabel(t("ui.curator.popular_info"))
        info.setWordWrap(True)
        vl.addWidget(info)

        scr = QScrollArea()
        scr.setWidgetResizable(True)
        sw = QWidget()
        sl = QVBoxLayout(sw)

        cbs = []
        for p in POPULAR_CURATORS:
            lbl = "%s - %s" % (p.name, p.description)
            cb = QCheckBox(lbl)
            in_db = p.curator_id in known
            has_coll = self._matches(p.name)
            if in_db or has_coll:
                cb.setChecked(True)
                cb.setEnabled(False)
                cb.setToolTip(t("ui.curator.already_added"))
            sl.addWidget(cb)
            cbs.append((cb, p.curator_id, p.name))

        sl.addStretch()
        scr.setWidget(sw)
        vl.addWidget(scr)

        btns = QHBoxLayout()
        btns.addStretch()
        cancel = QPushButton(t("common.cancel"))
        cancel.clicked.connect(dlg.reject)
        btns.addWidget(cancel)
        ok = QPushButton(t("common.ok"))
        ok.clicked.connect(dlg.accept)
        ok.setDefault(True)
        btns.addWidget(ok)
        vl.addLayout(btns)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        n = 0
        for cb, cid, name in cbs:
            if cb.isChecked() and cid not in known:
                url = "https://store.steampowered.com/curator/%d/" % cid
                self._db.add_curator(cid, name, url, src="preset")
                n += 1

        if n > 0:
            self._refresh()

    def _rm(self):
        if not self._db:
            return

        sel = self._tbl.selectionModel().selectedRows()
        if not sel:
            UIHelper.show_warning(self, t("ui.curator.no_selection"))
            return

        r = sel[0].row()
        it = self._tbl.item(r, _COL_NAME)
        if not it:
            return

        cname = it.text()
        if not UIHelper.confirm(
            self,
            t("ui.curator.remove_confirm", name=cname),
            title=t("ui.curator.remove"),
        ):
            return

        curs = self._db.get_all_curators()
        if r < len(curs):
            self._db.remove_curator(curs[r]["curator_id"])
            self._refresh()

    # -- top curators --

    def _top(self):
        from steam_library_manager.services.curator_client import CuratorClient

        if not self._db:
            return

        try:
            top = CuratorClient.fetch_top(n=50)
        except ConnectionError as exc:
            UIHelper.show_warning(self, t("ui.curator.top_fetch_error", error=str(exc)))
            return

        if not top:
            UIHelper.show_info(self, t("ui.curator.top_empty"))
            return

        known = {c["curator_id"] for c in self._db.get_all_curators()}

        dlg = QDialog(self)
        dlg.setWindowTitle(t("ui.curator.top_title"))
        dlg.setMinimumWidth(500)
        dlg.setMaximumHeight(600)
        dlg.setModal(True)

        vl = QVBoxLayout(dlg)
        info = QLabel(t("ui.curator.top_info"))
        info.setWordWrap(True)
        vl.addWidget(info)

        scr = QScrollArea()
        scr.setWidgetResizable(True)
        sw = QWidget()
        sl = QVBoxLayout(sw)

        cbs = []
        for e in top:
            cid = e["curator_id"]
            name = str(e.get("name", "Curator %d" % cid))
            cb = QCheckBox(name)
            in_db = cid in known
            has_coll = self._matches(name)
            if in_db or has_coll:
                cb.setChecked(True)
                cb.setEnabled(False)
                cb.setToolTip(t("ui.curator.already_added"))
            sl.addWidget(cb)
            cbs.append((cb, int(cid), name))

        sl.addStretch()
        scr.setWidget(sw)
        vl.addWidget(scr)

        btns = QHBoxLayout()
        btns.addStretch()
        cancel = QPushButton(t("common.cancel"))
        cancel.clicked.connect(dlg.reject)
        btns.addWidget(cancel)
        ok = QPushButton(t("common.ok"))
        ok.clicked.connect(dlg.accept)
        ok.setDefault(True)
        btns.addWidget(ok)
        vl.addLayout(btns)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        n = 0
        for cb, cid, name in cbs:
            if cb.isChecked() and cid not in known:
                url = "https://store.steampowered.com/curator/%d/" % cid
                self._db.add_curator(cid, name, url, src="discovered")
                n += 1

        if n > 0:
            self._refresh()

    # -- export / import --

    def _exp(self):
        import json

        if not self._db:
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            t("ui.curator.export_title"),
            "curators.json",
            "JSON (*.json)",
        )
        if not path:
            return

        curs = self._db.get_all_curators()
        out = []
        for c in curs:
            recs = sorted(self._db.get_recommendations_for_curator(c["curator_id"]))
            out.append(
                {
                    "curator_id": c["curator_id"],
                    "name": c["name"],
                    "url": c.get("url", ""),
                    "source": c.get("source", "manual"),
                    "active": bool(c.get("active", True)),
                    "last_updated": c.get("last_updated"),
                    "recommendations": recs,
                }
            )

        with open(path, "w", encoding="utf-8") as f:
            json.dump({"version": 1, "curators": out}, f, indent=2, ensure_ascii=False)

        UIHelper.show_info(
            self,
            t("ui.curator.export_success", count=len(out)),
        )

    def _imp(self):
        import json

        if not self._db:
            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            t("ui.curator.import_title"),
            "",
            "JSON (*.json)",
        )
        if not path:
            return

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            UIHelper.show_warning(self, t("ui.curator.import_error", error=str(exc)))
            return

        entries = data.get("curators", [])
        if not entries:
            UIHelper.show_warning(self, t("ui.curator.import_empty"))
            return

        # merge: skip curators whose local data is newer
        existing = {c["curator_id"]: c for c in self._db.get_all_curators()}
        imp = 0

        for e in entries:
            cid = e.get("curator_id")
            if not isinstance(cid, int):
                continue

            loc = existing.get(cid)
            if loc and loc.get("last_updated") and e.get("last_updated"):
                if loc["last_updated"] >= e["last_updated"]:
                    continue

            name = e.get("name", "Curator %d" % cid)
            url = e.get("url", "")
            src = e.get("source", "manual")
            self._db.add_curator(cid, name, url, src)

            recs = e.get("recommendations", [])
            if recs:
                self._db.save_curator_recommendations(cid, recs)

            imp += 1

        self._refresh()
        UIHelper.show_info(
            self,
            t("ui.curator.import_success", count=imp),
        )

    # -- db lifecycle --

    def _open(self):
        from steam_library_manager.core.database import Database

        self._db = Database(self._db_path)

    def closeEvent(self, event):
        if self._db:
            self._db.close()
            self._db = None
        super().closeEvent(event)
