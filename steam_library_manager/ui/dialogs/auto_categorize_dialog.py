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
        self.all_games_count = all_games_count
        self.on_start = on_start
        self.category_name = category_name
        self.result = None
        self._preset_mgr = AutoCatPresetManager()

        super().__init__(
            parent,
            title_key="auto_categorize.title",
            min_width=550,
            show_title_label=False,
            buttons="custom",
        )
        self._center()

    def _center(self):
        # Center dialog on parent window
        if self.parent():
            pg = self.parent().geometry()
            self.move(
                pg.x() + (pg.width() - self.width()) // 2,
                pg.y() + (pg.height() - self.height()) // 2,
            )

    def _build_content(self, layout):
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetMinAndMaxSize)

        # Title
        title = QLabel(t("auto_categorize.header"))
        title.setFont(FontHelper.get_font(16, FontHelper.BOLD))
        layout.addWidget(title)

        # Preset section
        self._build_presets(layout)

        # Method selector widget
        self.selector = AutoCatMethodSelector(self, len(self.games), self.all_games_count, self.category_name)
        self.selector.methods_changed.connect(self._on_methods_changed)
        layout.addWidget(self.selector)

        # Curator settings
        self._build_curator(layout)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep)

        # Warning
        warn = QLabel(t("auto_categorize.warning_backup"))
        warn.setStyleSheet("color: orange;")
        layout.addWidget(warn)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton(t("common.cancel"))
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        start_btn = QPushButton(t("auto_categorize.start"))
        start_btn.setDefault(True)
        start_btn.clicked.connect(self._start)
        btn_row.addWidget(start_btn)

        layout.addLayout(btn_row)

    def _on_methods_changed(self):
        self.curator_group.setVisible(self.selector.is_curator_selected())
        self.adjustSize()

    # -- Presets --

    def _build_presets(self, parent_layout):
        grp = QGroupBox(t("auto_categorize.preset_section"))
        row = QHBoxLayout()

        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(200)
        self._reload_presets()
        row.addWidget(self.preset_combo)

        load_btn = QPushButton(t("auto_categorize.preset_load"))
        load_btn.clicked.connect(self._load_preset)
        row.addWidget(load_btn)

        save_btn = QPushButton(t("auto_categorize.preset_save"))
        save_btn.clicked.connect(self._save_preset)
        row.addWidget(save_btn)

        del_btn = QPushButton(t("auto_categorize.preset_delete"))
        del_btn.clicked.connect(self._del_preset)
        row.addWidget(del_btn)

        row.addStretch()
        grp.setLayout(row)
        parent_layout.addWidget(grp)

    def _reload_presets(self):
        # Refresh preset combo from disk
        self.preset_combo.clear()
        presets = self._preset_mgr.load_presets()
        if not presets:
            self.preset_combo.addItem(t("auto_categorize.preset_no_presets"))
            self.preset_combo.setEnabled(False)
        else:
            self.preset_combo.setEnabled(True)
            for p in presets:
                self.preset_combo.addItem(p.name)

    def _load_preset(self):
        presets = self._preset_mgr.load_presets()
        if not presets:
            return

        idx = self.preset_combo.currentIndex()
        if idx < 0 or idx >= len(presets):
            return

        self._apply_preset(presets[idx])

    def _apply_preset(self, preset):
        self.selector.apply_preset(
            set(preset.methods),
            preset.tags_count,
            preset.ignore_common,
        )

    def _save_preset(self):
        name, ok = QInputDialog.getText(self, t("auto_categorize.preset_save"), t("auto_categorize.preset_name_prompt"))
        if not ok or not name.strip():
            return

        name = name.strip()

        existing = self._preset_mgr.load_presets()
        if any(p.name == name for p in existing):
            if not UIHelper.confirm(
                self,
                t("auto_categorize.preset_overwrite_msg", name=name),
                title=t("auto_categorize.preset_overwrite_title"),
            ):
                return

        settings = self.selector.get_settings()
        preset = AutoCatPreset(
            name=name,
            methods=tuple(settings["methods"]),
            tags_count=settings["tags_count"],
            ignore_common=settings["ignore_common"],
        )

        self._preset_mgr.save_preset(preset)
        self._reload_presets()

        idx = self.preset_combo.findText(name)
        if idx >= 0:
            self.preset_combo.setCurrentIndex(idx)

    def _del_preset(self):
        presets = self._preset_mgr.load_presets()
        if not presets:
            return

        idx = self.preset_combo.currentIndex()
        if idx < 0 or idx >= len(presets):
            return

        self._preset_mgr.delete_preset(presets[idx].name)
        self._reload_presets()

    # -- Curator --

    def _build_curator(self, parent_layout):
        # Curator info section (curators managed via Tools menu now)
        self.curator_group = QGroupBox(t("auto_categorize.by_curator"))
        cl = QVBoxLayout()

        info = QLabel(t("auto_categorize.curator_info"))
        info.setWordWrap(True)
        cl.addWidget(info)

        self.curator_group.setLayout(cl)
        self.curator_group.setVisible(False)
        parent_layout.addWidget(self.curator_group)

    # -- Start --

    def _start(self):
        settings = self.selector.get_settings()
        methods = settings["methods"]

        if not methods:
            UIHelper.show_warning(
                self, t("auto_categorize.error_no_method"), title=t("auto_categorize.no_method_title")
            )
            return

        self.result = dict(settings)

        self.accept()
        if self.on_start:
            self.on_start(self.result)

    def get_result(self):
        return self.result
