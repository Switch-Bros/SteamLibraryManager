#
# steam_library_manager/ui/dialogs/profile_dialog.py
# Dialog for viewing and switching between Steam user profiles
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
from datetime import datetime
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
)

from steam_library_manager.ui.widgets.base_dialog import BaseDialog
from steam_library_manager.ui.widgets.ui_helper import UIHelper
from steam_library_manager.utils.i18n import t

logger = logging.getLogger("steamlibmgr.profile_dialog")

__all__ = ["ProfileDialog"]


class ProfileDialog(BaseDialog):
    """Modal dialog for profile management."""

    def __init__(self, mgr, parent=None):
        self.mgr = mgr
        self.action = ""
        self.sel_name = ""

        super().__init__(
            parent,
            title_key="ui.profile.dialog_title",
            min_width=500,
            show_title_label=True,
            buttons="custom",
        )
        self.setMinimumHeight(420)
        self._refresh()

    def _build_content(self, layout):
        # info
        i = QLabel(t("ui.profile.info_text"))
        i.setWordWrap(True)
        layout.addWidget(i)

        # list
        self.lst = QListWidget()
        self.lst.setAlternatingRowColors(True)
        self.lst.itemDoubleClicked.connect(self._load)
        layout.addWidget(self.lst, stretch=1)

        # no profiles msg
        self.no = QLabel(t("ui.profile.no_profiles"))
        self.no.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.no.setStyleSheet("color: gray; padding: 20px;")
        self.no.setVisible(False)
        layout.addWidget(self.no)

        # row 1: Save, Load, Delete
        r1 = QHBoxLayout()
        self.bs = QPushButton(t("common.save"))
        self.bs.clicked.connect(self._save_cur)
        r1.addWidget(self.bs)

        self.bl = QPushButton(t("common.load"))
        self.bl.clicked.connect(self._load)
        r1.addWidget(self.bl)

        self.bd = QPushButton(t("common.delete"))
        self.bd.clicked.connect(self._del)
        r1.addWidget(self.bd)

        layout.addLayout(r1)

        # row 2: Rename, Export, Import
        r2 = QHBoxLayout()
        self.br = QPushButton(t("common.rename"))
        self.br.clicked.connect(self._ren)
        r2.addWidget(self.br)

        self.be = QPushButton(t("common.export"))
        self.be.clicked.connect(self._exp)
        r2.addWidget(self.be)

        self.bi = QPushButton(t("common.import"))
        self.bi.clicked.connect(self._imp)
        r2.addWidget(self.bi)

        layout.addLayout(r2)

        # close
        rc = QHBoxLayout()
        rc.addStretch()
        bc = QPushButton(t("common.close"))
        bc.clicked.connect(self.reject)
        rc.addWidget(bc)
        layout.addLayout(rc)

    def _refresh(self):
        self.lst.clear()
        ps = self.mgr.list_profiles()

        has = len(ps) > 0
        self.lst.setVisible(has)
        self.no.setVisible(not has)

        for n, cat in ps:
            ds = datetime.fromtimestamp(cat).strftime("%d.%m.%Y %H:%M") if cat else "-"
            d = "%s    (%s)" % (n, t("ui.profile.created_at", date=ds))
            it = QListWidgetItem(d)
            it.setData(Qt.ItemDataRole.UserRole, n)
            self.lst.addItem(it)

        self._upd_btns()
        self.lst.currentItemChanged.connect(lambda: self._upd_btns())

    def _upd_btns(self):
        sel = self.lst.currentItem() is not None
        self.bl.setEnabled(sel)
        self.bd.setEnabled(sel)
        self.br.setEnabled(sel)
        self.be.setEnabled(sel)

    def _sel(self):
        it = self.lst.currentItem()
        if it is None:
            return None
        return it.data(Qt.ItemDataRole.UserRole)

    def _save_cur(self):
        n, ok = UIHelper.ask_text(
            self,
            title=t("ui.profile.new_title"),
            label=t("ui.profile.new_prompt"),
        )
        if not ok or not n:
            return

        ex = [nm for nm, _ in self.mgr.list_profiles()]
        if n in ex:
            ov = UIHelper.confirm(
                self,
                t("ui.profile.error_duplicate_name", name=n),
                title=t("ui.profile.new_title"),
            )
            if not ov:
                return

        self.action = "save"
        self.sel_name = n
        self.accept()

    def _load(self):
        n = self._sel()
        if not n:
            return

        self.action = "load"
        self.sel_name = n
        self.accept()

    def _del(self):
        n = self._sel()
        if not n:
            return

        cf = UIHelper.confirm(
            self,
            t("ui.profile.delete_confirm", name=n),
            title=t("ui.profile.delete_confirm_title"),
        )
        if not cf:
            return

        self.mgr.delete_profile(n)
        UIHelper.show_success(self, t("ui.profile.delete_success", name=n))
        self._refresh()

    def _ren(self):
        n = self._sel()
        if not n:
            return

        nn, ok = UIHelper.ask_text(
            self,
            title=t("ui.profile.rename_title"),
            label=t("ui.profile.rename_prompt"),
            current_text=n,
        )
        if not ok or not nn or nn == n:
            return

        ok = self.mgr.rename_profile(n, nn)
        if ok:
            UIHelper.show_success(self, t("ui.profile.rename_success", name=nn))
            self._refresh()

    def _exp(self):
        from pathlib import Path
        from PyQt6.QtWidgets import QFileDialog

        n = self._sel()
        if not n:
            return

        fp, _ = QFileDialog.getSaveFileName(
            self,
            t("ui.profile.export_title"),
            "%s.json" % n,
            t("ui.profile.import_filter"),
        )
        if not fp:
            return

        ok = self.mgr.export_profile(n, Path(fp))
        if ok:
            UIHelper.show_success(self, t("ui.profile.export_success"))

    def _imp(self):
        from pathlib import Path
        from PyQt6.QtWidgets import QFileDialog

        fp, _ = QFileDialog.getOpenFileName(
            self,
            t("ui.profile.import_title"),
            "",
            t("ui.profile.import_filter"),
        )
        if not fp:
            return

        try:
            p = self.mgr.import_profile(Path(fp))
            UIHelper.show_success(self, t("ui.profile.import_success", name=p.name))
            self._refresh()
        except (FileNotFoundError, KeyError, Exception) as e:
            UIHelper.show_error(self, t("ui.profile.error_import_failed", error=str(e)))
