#
# steam_library_manager/ui/dialogs/metadata_edit_dialog.py
# Dialog for manually editing game metadata fields
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from PyQt6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from steam_library_manager.ui.theme import Theme
from steam_library_manager.ui.widgets.base_dialog import BaseDialog
from steam_library_manager.ui.widgets.ui_helper import UIHelper
from steam_library_manager.utils.date_utils import format_timestamp_to_date, parse_date_to_timestamp
from steam_library_manager.utils.i18n import t

__all__ = ["MetadataEditDialog"]


class MetadataEditDialog(BaseDialog):
    """Form dialog for editing game metadata.

    FIXME: way too many fields, should split into tabs
    """

    def __init__(self, parent, game_name, current, original=None):
        self._game = game_name
        self._cur = current
        self._orig = original or {}
        self.result = None
        super().__init__(
            parent,
            title_text=t("ui.metadata_editor.editing_title", game=game_name),
            min_width=600,
            buttons="custom",
        )
        self._fill()

    def _build_content(self, lyt):
        # info text
        info = QLabel(t("ui.metadata_editor.info_tracking"))
        info.setStyleSheet("color: gray; font-size: 10px;")
        lyt.addWidget(info)

        # form fields
        frm = QFormLayout()

        self._nm = QLineEdit()
        self._sort = QLineEdit()
        self._dev = QLineEdit()
        self._pub = QLineEdit()
        self._rel = QLineEdit()

        frm.addRow(t("ui.metadata_editor.game_name_label"), self._nm)
        frm.addRow(t("ui.metadata_editor.sort_as_label"), self._sort)

        hlp = QLabel(t("ui.metadata_editor.sort_as_help"))
        hlp.setStyleSheet("color: gray; font-size: 9px;")
        frm.addRow("", hlp)

        frm.addRow(t("ui.game_details.developer") + ":", self._dev)
        frm.addRow(t("ui.game_details.publisher") + ":", self._pub)
        frm.addRow(t("ui.game_details.release_year") + ":", self._rel)

        dt_hlp = QLabel(t("ui.metadata_editor.date_help"))
        dt_hlp.setStyleSheet("color: gray; font-size: 9px;")
        frm.addRow("", dt_hlp)

        lyt.addLayout(frm)

        # original values group
        grp = QGroupBox(t("ui.metadata_editor.original_values_group"))
        vl = QVBoxLayout()
        self._orig_txt = QTextEdit()
        self._orig_txt.setReadOnly(True)
        self._orig_txt.setMaximumHeight(100)
        vl.addWidget(self._orig_txt)
        grp.setLayout(vl)
        lyt.addWidget(grp)

        # buttons
        row = QHBoxLayout()
        row.addStretch()

        rev = QPushButton(t("ui.metadata_editor.revert_to_original"))
        rev.setStyleSheet("background-color: #6c757d; color: white;")
        rev.clicked.connect(self._rev)
        row.addWidget(rev)

        cancel = QPushButton(t("common.cancel"))
        cancel.clicked.connect(self.reject)
        row.addWidget(cancel)

        save = QPushButton(t("common.save"))
        save.setDefault(True)
        save.clicked.connect(self._save)
        row.addWidget(save)

        lyt.addLayout(row)

    def _fill(self):
        # populate form with current metadata
        m = self._cur
        o = self._orig

        # store formatted originals for comparison
        self._ov = {
            "name": str(o.get("name", "")),
            "developer": str(o.get("developer", "")),
            "publisher": str(o.get("publisher", "")),
            "release_date": format_timestamp_to_date(o.get("release_date", "")),
        }

        self._nm.setText(m.get("name", ""))
        self._sort.setText(m.get("sort_as", ""))
        self._dev.setText(m.get("developer", ""))
        self._pub.setText(m.get("publisher", ""))
        self._rel.setText(format_timestamp_to_date(m.get("release_date", "")))

        # connect textChanged for live highlighting
        self._nm.textChanged.connect(self._hl)
        self._dev.textChanged.connect(self._hl)
        self._pub.textChanged.connect(self._hl)
        self._rel.textChanged.connect(self._hl)

        self._hl()

        # show original values
        na = t("ui.game_details.value_unknown")
        rel = self._ov["release_date"] or na
        lines = [
            "%s: %s" % (t("ui.game_details.name"), o.get("name", na)),
            "%s: %s" % (t("ui.game_details.developer"), o.get("developer", na)),
            "%s: %s" % (t("ui.game_details.publisher"), o.get("publisher", na)),
            "%s: %s" % (t("ui.game_details.release_year"), rel),
        ]

        self._orig_txt.setPlainText("\n".join(lines))

    def _hl(self):
        # highlight modified fields
        mod = Theme.mod_field()
        na = t("ui.game_details.value_unknown")

        flds = [
            (self._nm, "name"),
            (self._dev, "developer"),
            (self._pub, "publisher"),
            (self._rel, "release_date"),
        ]

        for w, key in flds:
            orig = self._ov.get(key, "")
            if w.text().strip() != orig.strip():
                w.setStyleSheet(mod)
                w.setToolTip(t("ui.metadata_editor.modified_tooltip", original=orig or na))
            else:
                w.setStyleSheet("")
                w.setToolTip("")

    def _rev(self):
        # restore original values
        if not self._orig:
            UIHelper.show_info(
                self, t("ui.metadata_editor.revert_no_original"), title=t("ui.metadata_editor.revert_title")
            )
            return

        if not UIHelper.confirm(self, t("ui.metadata_editor.revert_confirm"), t("ui.metadata_editor.revert_title")):
            return

        self._nm.setText(self._ov["name"])
        self._dev.setText(self._ov["developer"])
        self._pub.setText(self._ov["publisher"])
        self._rel.setText(self._ov["release_date"])

    def _save(self):
        # validate and store
        nm = self._nm.text().strip()
        if not nm:
            UIHelper.show_warning(self, t("ui.metadata_editor.error_empty_name"))
            return

        self.result = {
            "name": nm,
            "sort_as": self._sort.text().strip() or nm,
            "developer": self._dev.text().strip(),
            "publisher": self._pub.text().strip(),
            "release_date": parse_date_to_timestamp(self._rel.text().strip()),
        }
        self.accept()

    def get_metadata(self):
        return self.result
