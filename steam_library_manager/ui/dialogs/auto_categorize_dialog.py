#
# steam_library_manager/ui/dialogs/auto_categorize_dialog.py
# Dialog for configuring and running auto-categorization
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

__all__ = ["AutoCategorizeDialog"]

import logging

from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from steam_library_manager.services.autocat_preset_manager import AutoCatPreset, AutoCatPresetManager
from steam_library_manager.ui.utils.font_helper import FontHelper
from steam_library_manager.ui.widgets.autocat_method_selector import AutoCatMethodSelector
from steam_library_manager.ui.widgets.base_dialog import BaseDialog
from steam_library_manager.ui.widgets.ui_helper import UIHelper
from steam_library_manager.utils.i18n import t

logger = logging.getLogger("steamlibmgr.auto_categorize_dialog")


class AutoCategorizeDialog(BaseDialog):
    """Configure auto-categorization methods, presets and curator
    settings, then kick off the categorization run.
    """

    def __init__(self, parent, games, all_games_count, on_start, category_name=None):
        self.games = games
        self._total = all_games_count
        self.on_start = on_start
        self._cat = category_name
        self.result = None
        self._mgr = AutoCatPresetManager()

        super().__init__(
            parent,
            title_key="auto_categorize.title",
            min_width=550,
            show_title_label=False,
            buttons="custom",
        )
        self._center()

    def _center(self):
        # center dialog on parent window
        if self.parent():
            pg = self.parent().geometry()
            self.move(
                pg.x() + (pg.width() - self.width()) // 2,
                pg.y() + (pg.height() - self.height()) // 2,
            )

    def _build_content(self, lyt):
        lyt.setSpacing(10)
        lyt.setContentsMargins(20, 20, 20, 20)
        lyt.setSizeConstraint(QVBoxLayout.SizeConstraint.SetMinAndMaxSize)

        # title header
        hdr = QLabel(t("auto_categorize.header"))
        hdr.setFont(FontHelper.get_font(16, FontHelper.BOLD))
        lyt.addWidget(hdr)

        # preset section
        self._mk_presets(lyt)

        # method selector widget
        self._sel = AutoCatMethodSelector(self, len(self.games), self._total, self._cat)
        self._sel.methods_changed.connect(self._on_change)
        lyt.addWidget(self._sel)

        # curator settings
        self._mk_curator(lyt)

        # separator
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setFrameShadow(QFrame.Shadow.Sunken)
        lyt.addWidget(div)

        # warning
        w = QLabel(t("auto_categorize.warning_backup"))
        w.setStyleSheet("color: orange;")
        lyt.addWidget(w)

        # buttons
        row = QHBoxLayout()
        row.addStretch()

        cancel = QPushButton(t("common.cancel"))
        cancel.clicked.connect(self.reject)
        row.addWidget(cancel)

        start = QPushButton(t("auto_categorize.start"))
        start.setDefault(True)
        start.clicked.connect(self._start)
        row.addWidget(start)

        lyt.addLayout(row)

    def _on_change(self):
        self._grp_cur.setVisible(self._sel.is_curator_selected())
        self.adjustSize()

    # -- presets --

    def _mk_presets(self, lyt):
        g = QGroupBox(t("auto_categorize.preset_section"))
        h = QHBoxLayout()

        self._combo = QComboBox()
        self._combo.setMinimumWidth(200)
        self._reload()
        h.addWidget(self._combo)

        btn_load = QPushButton(t("auto_categorize.preset_load"))
        btn_load.clicked.connect(self._load)
        h.addWidget(btn_load)

        btn_save = QPushButton(t("auto_categorize.preset_save"))
        btn_save.clicked.connect(self._save)
        h.addWidget(btn_save)

        btn_del = QPushButton(t("auto_categorize.preset_delete"))
        btn_del.clicked.connect(self._delete)
        h.addWidget(btn_del)

        h.addStretch()
        g.setLayout(h)
        lyt.addWidget(g)

    def _reload(self):
        # refresh preset combo from disk
        self._combo.clear()
        pres = self._mgr.load_presets()
        if not pres:
            self._combo.addItem(t("auto_categorize.preset_no_presets"))
            self._combo.setEnabled(False)
        else:
            self._combo.setEnabled(True)
            for p in pres:
                self._combo.addItem(p.name)

    def _load(self):
        pres = self._mgr.load_presets()
        if not pres:
            return

        i = self._combo.currentIndex()
        if i < 0 or i >= len(pres):
            return

        self._apply(pres[i])

    def _apply(self, pr):
        self._sel.apply_preset(
            set(pr.methods),
            pr.tags_count,
            pr.ignore_common,
        )

    def _save(self):
        name, ok = QInputDialog.getText(self, t("auto_categorize.preset_save"), t("auto_categorize.preset_name_prompt"))
        if not ok or not name.strip():
            return

        name = name.strip()

        existing = self._mgr.load_presets()
        if any(x.name == name for x in existing):
            if not UIHelper.confirm(
                self,
                t("auto_categorize.preset_overwrite_msg", name=name),
                title=t("auto_categorize.preset_overwrite_title"),
            ):
                return

        cfg = self._sel.get_settings()
        preset = AutoCatPreset(
            name=name,
            methods=tuple(cfg["methods"]),
            tags_count=cfg["tags_count"],
            ignore_common=cfg["ignore_common"],
        )

        self._mgr.save_preset(preset)
        self._reload()

        idx = self._combo.findText(name)
        if idx >= 0:
            self._combo.setCurrentIndex(idx)

    def _delete(self):
        pres = self._mgr.load_presets()
        if not pres:
            return

        i = self._combo.currentIndex()
        if i < 0 or i >= len(pres):
            return

        self._mgr.delete_preset(pres[i].name)
        self._reload()

    # -- curator --

    def _mk_curator(self, lyt):
        # curator info section (curators managed via Tools menu now)
        self._grp_cur = QGroupBox(t("auto_categorize.by_curator"))
        v = QVBoxLayout()

        lbl = QLabel(t("auto_categorize.curator_info"))
        lbl.setWordWrap(True)
        v.addWidget(lbl)

        self._grp_cur.setLayout(v)
        self._grp_cur.setVisible(False)
        lyt.addWidget(self._grp_cur)

    # -- start --

    def _start(self):
        cfg = self._sel.get_settings()
        m = cfg["methods"]

        if not m:
            UIHelper.show_warning(
                self, t("auto_categorize.error_no_method"), title=t("auto_categorize.no_method_title")
            )
            return

        self.result = dict(cfg)

        self.accept()
        if self.on_start:
            self.on_start(self.result)

    def get_result(self):
        return self.result
