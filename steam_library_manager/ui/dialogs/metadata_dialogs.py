#
# steam_library_manager/ui/dialogs/metadata_dialogs.py
# Bulk metadata edit and restore dialogs
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
)

from steam_library_manager.ui.theme import Theme
from steam_library_manager.ui.widgets.base_dialog import BaseDialog
from steam_library_manager.ui.widgets.ui_helper import UIHelper
from steam_library_manager.utils.date_utils import format_timestamp_to_date, parse_date_to_timestamp
from steam_library_manager.utils.i18n import t

__all__ = ["BulkMetadataEditDialog", "MetadataRestoreDialog"]


class BulkMetadataEditDialog(BaseDialog):
    """Edit metadata for multiple games at once.

    Supports setting developer, publisher, release date, and name mods
    (prefix, suffix, remove text). Also has a "revert to original" mode.
    """

    def __init__(self, parent, games, game_names):
        self.games = games
        self.games_count = len(games)
        self.game_names = game_names
        self.result_metadata = None
        super().__init__(
            parent,
            title_text=t("ui.metadata_editor.bulk_title", count=self.games_count),
            min_width=600,
            buttons="custom",
        )

    @staticmethod
    def _add_field(lay, label, placeholder=""):
        row = QHBoxLayout()
        cb = QCheckBox(label)
        inp = QLineEdit()
        if placeholder:
            inp.setPlaceholderText(placeholder)
        inp.setEnabled(False)
        cb.toggled.connect(inp.setEnabled)
        row.addWidget(cb)
        row.addWidget(inp)
        lay.addLayout(row)
        return cb, inp

    def _build_content(self, layout):
        info = QLabel("%s %s" % (t("emoji.warning"), t("ui.metadata_editor.bulk_info", count=self.games_count)))
        info.setStyleSheet("color: orange; font-size: 11px;")
        layout.addWidget(info)

        # preview
        grp = QGroupBox(t("ui.metadata_editor.bulk_preview", count=self.games_count))
        gl = QVBoxLayout()
        self.game_list = QListWidget()
        self.game_list.setMaximumHeight(120)

        names = self.game_names[:20]
        if len(self.game_names) > 20:
            names.append(t("ui.metadata_editor.bulk_more", count=len(self.game_names) - 20))
        for nm in names:
            self.game_list.addItem(nm)
        self.game_list.currentItemChanged.connect(self._on_click)

        gl.addWidget(self.game_list)
        grp.setLayout(gl)
        layout.addWidget(grp)

        # fields
        fg = QGroupBox(t("ui.metadata_editor.fields_group"))
        fl = QVBoxLayout()

        self.cb_dev, self.ed_dev = self._add_field(
            fl, t("ui.metadata_editor.set_field", field=t("ui.game_details.developer"))
        )
        self.cb_pub, self.ed_pub = self._add_field(
            fl, t("ui.metadata_editor.set_field", field=t("ui.game_details.publisher"))
        )
        self.cb_date, self.ed_date = self._add_field(
            fl,
            t("ui.metadata_editor.set_field", field=t("ui.game_details.release_year")),
            t("ui.metadata_editor.date_help"),
        )
        self.cb_pre, self.ed_pre = self._add_field(fl, t("ui.metadata_editor.add_prefix"))
        self.cb_suf, self.ed_suf = self._add_field(fl, t("ui.metadata_editor.add_suffix"))
        self.cb_rem, self.ed_rem = self._add_field(fl, t("ui.metadata_editor.remove_text"))

        # live preview
        for w in (self.ed_pre, self.ed_suf, self.ed_rem):
            w.textChanged.connect(self._preview)
        for cb in (self.cb_pre, self.cb_suf, self.cb_rem):
            cb.toggled.connect(self._preview)

        fg.setLayout(fl)
        layout.addWidget(fg)

        # revert
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep)

        self.cb_revert = QCheckBox(t("ui.metadata_editor.bulk_revert_label"))
        self.cb_revert.toggled.connect(self._on_revert)
        layout.addWidget(self.cb_revert)

        hlp = QLabel(t("ui.metadata_editor.bulk_revert_help"))
        hlp.setStyleSheet("color: %s; font-size: 11px; margin-left: 24px;" % Theme.TXT_MUTED)
        hlp.setWordWrap(True)
        layout.addWidget(hlp)

        warn = QLabel("%s %s" % (t("emoji.warning"), t("auto_categorize.warning_backup")))
        warn.setStyleSheet("color: orange;")
        layout.addWidget(warn)

        btns = QHBoxLayout()
        btns.addStretch()

        b = QPushButton(t("common.cancel"))
        b.clicked.connect(self.reject)
        btns.addWidget(b)

        b = QPushButton(t("ui.metadata_editor.apply_button", count=self.games_count))
        b.setDefault(True)
        b.clicked.connect(self._apply)
        btns.addWidget(b)

        layout.addLayout(btns)

    def _on_click(self, cur, _prev):
        if not cur:
            return
        idx = self.game_list.row(cur)
        if idx < 0 or idx >= len(self.games):
            return
        g = self.games[idx]
        self.ed_dev.setPlaceholderText(g.developer or "-")
        self.ed_pub.setPlaceholderText(g.publisher or "-")
        self.ed_date.setPlaceholderText(format_timestamp_to_date(g.release_year) if g.release_year else "-")

    def _preview(self):
        mods = {}
        if self.cb_pre.isChecked() and self.ed_pre.text():
            mods["prefix"] = self.ed_pre.text()
        if self.cb_suf.isChecked() and self.ed_suf.text():
            mods["suffix"] = self.ed_suf.text()
        if self.cb_rem.isChecked() and self.ed_rem.text():
            mods["remove"] = self.ed_rem.text()

        for i in range(min(self.game_list.count(), len(self.game_names))):
            item = self.game_list.item(i)
            if not item:
                continue
            orig = self.game_names[i]
            if mods:
                mod = self._apply_mods(orig, mods)
                if mod != orig:
                    item.setText(mod)
                    item.setForeground(QColor(Theme.MOD_BORDER))
                else:
                    item.setText(orig)
                    item.setForeground(QColor(Theme.TXT_PRI))
            else:
                item.setText(orig)
                item.setForeground(QColor(Theme.TXT_PRI))

    @staticmethod
    def _apply_mods(name, mods):
        from steam_library_manager.utils.name_utils import apply_name_modifications

        return apply_name_modifications(name, mods)

    def _on_revert(self, checked):
        for cb, inp in (
            (self.cb_dev, self.ed_dev),
            (self.cb_pub, self.ed_pub),
            (self.cb_date, self.ed_date),
            (self.cb_pre, self.ed_pre),
            (self.cb_suf, self.ed_suf),
            (self.cb_rem, self.ed_rem),
        ):
            cb.setEnabled(not checked)
            inp.setEnabled(not checked and cb.isChecked())

    def _apply(self):
        cbs = [self.cb_dev, self.cb_pub, self.cb_date, self.cb_pre, self.cb_suf, self.cb_rem]
        if not self.cb_revert.isChecked() and not any(c.isChecked() for c in cbs):
            UIHelper.show_warning(self, t("ui.dialogs.no_selection"), title=t("ui.dialogs.no_changes"))
            return

        if not UIHelper.confirm(
            self, t("ui.dialogs.confirm_bulk", count=self.games_count), t("ui.dialogs.confirm_bulk_title")
        ):
            return

        if self.cb_revert.isChecked():
            self.result_metadata = {"__revert_to_original__": True}
            self.accept()
            return

        self.result_metadata = {}
        if self.cb_dev.isChecked():
            self.result_metadata["developer"] = self.ed_dev.text().strip()
        if self.cb_pub.isChecked():
            self.result_metadata["publisher"] = self.ed_pub.text().strip()
        if self.cb_date.isChecked():
            self.result_metadata["release_date"] = parse_date_to_timestamp(self.ed_date.text().strip())

        mods = {}
        if self.cb_pre.isChecked():
            mods["prefix"] = self.ed_pre.text()
        if self.cb_suf.isChecked():
            mods["suffix"] = self.ed_suf.text()
        if self.cb_rem.isChecked():
            mods["remove"] = self.ed_rem.text()
        if mods:
            self.result_metadata["name_modifications"] = mods

        self.accept()

    def get_metadata(self):
        return self.result_metadata


class MetadataRestoreDialog(BaseDialog):
    """Confirm restore dialog."""

    def __init__(self, parent, modified_count):
        self.modified_count = modified_count
        self.do_restore = False
        super().__init__(parent, title_key="menu.edit.reset_metadata", buttons="custom")

    def _build_content(self, layout):
        info = QLabel(t("ui.metadata_editor.restore_info", count=self.modified_count))
        info.setWordWrap(True)
        layout.addWidget(info)

        warn = QLabel("%s %s" % (t("emoji.warning"), t("auto_categorize.warning_backup")))
        warn.setStyleSheet("color: orange;")
        layout.addWidget(warn)

        btns = QHBoxLayout()
        btns.addStretch()

        b = QPushButton(t("common.cancel"))
        b.clicked.connect(self.reject)
        btns.addWidget(b)

        b = QPushButton(t("ui.metadata_editor.restore_button", count=self.modified_count))
        b.setDefault(True)
        b.clicked.connect(self._restore)
        btns.addWidget(b)

        layout.addLayout(btns)

    def _restore(self):
        self.do_restore = True
        self.accept()

    def should_restore(self):
        return self.do_restore
