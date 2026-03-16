#
# steam_library_manager/ui/dialogs/profile_dialog.py
# Dialog for managing categorization profiles
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from steam_library_manager.ui.widgets.base_dialog import BaseDialog
from steam_library_manager.ui.widgets.ui_helper import UIHelper
from steam_library_manager.utils.i18n import t

if TYPE_CHECKING:
    from steam_library_manager.core.profile_manager import ProfileManager

logger = logging.getLogger("steamlibmgr.profile_dialog")

__all__ = ["ProfileDialog"]


class ProfileDialog(BaseDialog):
    """Modal dialog for profile management.

    After exec() returns Accepted, check self.action and self.selected_name.
    """

    def __init__(self, manager: ProfileManager, parent: QWidget | None = None) -> None:
        self.manager: ProfileManager = manager
        self.action: str = ""
        self.selected_name: str = ""

        super().__init__(
            parent,
            title_key="ui.profile.dialog_title",
            min_width=500,
            show_title_label=True,
            buttons="custom",
        )
        self.setMinimumHeight(420)
        self._refresh_list()

    def _build_content(self, layout: QVBoxLayout) -> None:
        info = QLabel(t("ui.profile.info_text"))
        info.setWordWrap(True)
        layout.addWidget(info)

        self.profile_list = QListWidget()
        self.profile_list.setAlternatingRowColors(True)
        self.profile_list.itemDoubleClicked.connect(self._on_load)
        layout.addWidget(self.profile_list, stretch=1)

        self.no_profiles_label = QLabel(t("ui.profile.no_profiles"))
        self.no_profiles_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.no_profiles_label.setStyleSheet("color: gray; padding: 20px;")
        self.no_profiles_label.setVisible(False)
        layout.addWidget(self.no_profiles_label)

        row1 = QHBoxLayout()
        self.btn_save = QPushButton(t("common.save"))
        self.btn_save.clicked.connect(self._on_save_current)
        row1.addWidget(self.btn_save)

        self.btn_load = QPushButton(t("common.load"))
        self.btn_load.clicked.connect(self._on_load)
        row1.addWidget(self.btn_load)

        self.btn_delete = QPushButton(t("common.delete"))
        self.btn_delete.clicked.connect(self._on_delete)
        row1.addWidget(self.btn_delete)

        layout.addLayout(row1)

        row2 = QHBoxLayout()
        self.btn_rename = QPushButton(t("common.rename"))
        self.btn_rename.clicked.connect(self._on_rename)
        row2.addWidget(self.btn_rename)

        self.btn_export = QPushButton(t("common.export"))
        self.btn_export.clicked.connect(self._on_export)
        row2.addWidget(self.btn_export)

        self.btn_import = QPushButton(t("common.import"))
        self.btn_import.clicked.connect(self._on_import)
        row2.addWidget(self.btn_import)

        layout.addLayout(row2)

        close_layout = QHBoxLayout()
        close_layout.addStretch()
        btn_close = QPushButton(t("common.close"))
        btn_close.clicked.connect(self.reject)
        close_layout.addWidget(btn_close)
        layout.addLayout(close_layout)

    def _refresh_list(self) -> None:
        self.profile_list.clear()
        profiles = self.manager.list_profiles()

        has_profiles = len(profiles) > 0
        self.profile_list.setVisible(has_profiles)
        self.no_profiles_label.setVisible(not has_profiles)

        for name, created_at in profiles:
            date_str = datetime.fromtimestamp(created_at).strftime("%d.%m.%Y %H:%M") if created_at else "-"
            display = f"{name}    ({t('ui.profile.created_at', date=date_str)})"
            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.profile_list.addItem(item)

        self._update_button_states()
        self.profile_list.currentItemChanged.connect(lambda: self._update_button_states())

    def _update_button_states(self) -> None:
        has_selection = self.profile_list.currentItem() is not None
        self.btn_load.setEnabled(has_selection)
        self.btn_delete.setEnabled(has_selection)
        self.btn_rename.setEnabled(has_selection)
        self.btn_export.setEnabled(has_selection)

    def _get_selected_name(self) -> str | None:
        item = self.profile_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _on_save_current(self) -> None:
        name, ok = UIHelper.ask_text(
            self,
            title=t("ui.profile.new_title"),
            label=t("ui.profile.new_prompt"),
        )
        if not ok or not name:
            return

        existing = [n for n, _ in self.manager.list_profiles()]
        if name in existing:
            overwrite = UIHelper.confirm(
                self,
                t("ui.profile.error_duplicate_name", name=name),
                title=t("ui.profile.new_title"),
            )
            if not overwrite:
                return

        self.action = "save"
        self.selected_name = name
        self.accept()

    def _on_load(self) -> None:
        name = self._get_selected_name()
        if not name:
            return

        self.action = "load"
        self.selected_name = name
        self.accept()

    def _on_delete(self) -> None:
        name = self._get_selected_name()
        if not name:
            return

        confirmed = UIHelper.confirm(
            self,
            t("ui.profile.delete_confirm", name=name),
            title=t("ui.profile.delete_confirm_title"),
        )
        if not confirmed:
            return

        self.manager.delete_profile(name)
        UIHelper.show_success(self, t("ui.profile.delete_success", name=name))
        self._refresh_list()

    def _on_rename(self) -> None:
        name = self._get_selected_name()
        if not name:
            return

        new_name, ok = UIHelper.ask_text(
            self,
            title=t("ui.profile.rename_title"),
            label=t("ui.profile.rename_prompt"),
            current_text=name,
        )
        if not ok or not new_name or new_name == name:
            return

        success = self.manager.rename_profile(name, new_name)
        if success:
            UIHelper.show_success(self, t("ui.profile.rename_success", name=new_name))
            self._refresh_list()

    def _on_export(self) -> None:
        from pathlib import Path

        from PyQt6.QtWidgets import QFileDialog

        name = self._get_selected_name()
        if not name:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            t("ui.profile.export_title"),
            f"{name}.json",
            t("ui.profile.import_filter"),
        )
        if not file_path:
            return

        success = self.manager.export_profile(name, Path(file_path))
        if success:
            UIHelper.show_success(self, t("ui.profile.export_success"))

    def _on_import(self) -> None:
        from pathlib import Path

        from PyQt6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            t("ui.profile.import_title"),
            "",
            t("ui.profile.import_filter"),
        )
        if not file_path:
            return

        try:
            profile = self.manager.import_profile(Path(file_path))
            UIHelper.show_success(self, t("ui.profile.import_success", name=profile.name))
            self._refresh_list()
        except (FileNotFoundError, KeyError, Exception) as exc:
            UIHelper.show_error(self, t("ui.profile.error_import_failed", error=str(exc)))
