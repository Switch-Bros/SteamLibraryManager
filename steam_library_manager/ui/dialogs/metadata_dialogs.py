#
# steam_library_manager/ui/dialogs/metadata_dialogs.py
# Bulk metadata editing and metadata restore dialogs
#
# Copyright (c) 2025-2026 SwitchBros
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
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from steam_library_manager.core.game_manager import Game
from steam_library_manager.ui.theme import Theme
from steam_library_manager.ui.widgets.base_dialog import BaseDialog
from steam_library_manager.ui.widgets.ui_helper import UIHelper
from steam_library_manager.utils.date_utils import format_timestamp_to_date, parse_date_to_timestamp
from steam_library_manager.utils.i18n import t

__all__ = ["BulkMetadataEditDialog", "MetadataRestoreDialog"]


class BulkMetadataEditDialog(BaseDialog):
    """Dialog for editing metadata across multiple games at once."""

    def __init__(self, parent, games: list[Game], game_names: list[str]):
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
    def _add_bulk_field(layout, label_text: str, placeholder: str = ""):
        """Create a checkbox + input field row, return (checkbox, line_edit)."""
        row_layout = QHBoxLayout()
        checkbox = QCheckBox(label_text)
        line_edit = QLineEdit()
        if placeholder:
            line_edit.setPlaceholderText(placeholder)
        line_edit.setEnabled(False)
        checkbox.toggled.connect(line_edit.setEnabled)
        row_layout.addWidget(checkbox)
        row_layout.addWidget(line_edit)
        layout.addLayout(row_layout)
        return checkbox, line_edit

    def _build_content(self, layout: QVBoxLayout) -> None:
        info = QLabel(f"{t('emoji.warning')} {t('ui.metadata_editor.bulk_info', count=self.games_count)}")
        info.setStyleSheet("color: orange; font-size: 11px;")
        layout.addWidget(info)

        preview_group = QGroupBox(t("ui.metadata_editor.bulk_preview", count=self.games_count))
        preview_layout = QVBoxLayout()
        self.game_list = QListWidget()
        self.game_list.setMaximumHeight(120)

        names = self.game_names[:20]
        if len(self.game_names) > 20:
            names.append(t("ui.metadata_editor.bulk_more", count=len(self.game_names) - 20))
        for name in names:
            self.game_list.addItem(name)
        self.game_list.currentItemChanged.connect(self._on_game_clicked)

        preview_layout.addWidget(self.game_list)
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)

        fields_group = QGroupBox(t("ui.metadata_editor.fields_group"))
        f_layout = QVBoxLayout()

        self.cb_dev, self.edit_dev = self._add_bulk_field(
            f_layout, t("ui.metadata_editor.set_field", field=t("ui.game_details.developer"))
        )
        self.cb_pub, self.edit_pub = self._add_bulk_field(
            f_layout, t("ui.metadata_editor.set_field", field=t("ui.game_details.publisher"))
        )
        self.cb_date, self.edit_date = self._add_bulk_field(
            f_layout,
            t("ui.metadata_editor.set_field", field=t("ui.game_details.release_year")),
            t("ui.metadata_editor.date_help"),
        )
        self.cb_pre, self.edit_pre = self._add_bulk_field(f_layout, t("ui.metadata_editor.add_prefix"))
        self.cb_suf, self.edit_suf = self._add_bulk_field(f_layout, t("ui.metadata_editor.add_suffix"))
        self.cb_rem, self.edit_rem = self._add_bulk_field(f_layout, t("ui.metadata_editor.remove_text"))

        self.edit_pre.textChanged.connect(self._update_name_preview)
        self.edit_suf.textChanged.connect(self._update_name_preview)
        self.edit_rem.textChanged.connect(self._update_name_preview)
        self.cb_pre.toggled.connect(self._update_name_preview)
        self.cb_suf.toggled.connect(self._update_name_preview)
        self.cb_rem.toggled.connect(self._update_name_preview)

        fields_group.setLayout(f_layout)
        layout.addWidget(fields_group)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        self.cb_revert = QCheckBox(t("ui.metadata_editor.bulk_revert_label"))
        self.cb_revert.toggled.connect(self._on_revert_toggled)
        layout.addWidget(self.cb_revert)

        revert_help = QLabel(t("ui.metadata_editor.bulk_revert_help"))
        revert_help.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 11px; margin-left: 24px;")
        revert_help.setWordWrap(True)
        layout.addWidget(revert_help)

        warn_lbl = QLabel(f"{t('emoji.warning')} {t('auto_categorize.warning_backup')}")
        warn_lbl.setStyleSheet("color: orange;")
        layout.addWidget(warn_lbl)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton(t("common.cancel"))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        apply_btn = QPushButton(t("ui.metadata_editor.apply_button", count=self.games_count))
        apply_btn.setDefault(True)
        apply_btn.clicked.connect(self._apply)
        btn_layout.addWidget(apply_btn)

        layout.addLayout(btn_layout)

    def _on_game_clicked(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        if not current:
            return

        idx = self.game_list.row(current)
        if idx < 0 or idx >= len(self.games):
            return
        game = self.games[idx]

        self.edit_dev.setPlaceholderText(game.developer or "-")
        self.edit_pub.setPlaceholderText(game.publisher or "-")
        self.edit_date.setPlaceholderText(format_timestamp_to_date(game.release_year) if game.release_year else "-")

    def _update_name_preview(self) -> None:
        mods: dict[str, str] = {}
        if self.cb_pre.isChecked() and self.edit_pre.text():
            mods["prefix"] = self.edit_pre.text()
        if self.cb_suf.isChecked() and self.edit_suf.text():
            mods["suffix"] = self.edit_suf.text()
        if self.cb_rem.isChecked() and self.edit_rem.text():
            mods["remove"] = self.edit_rem.text()

        for i in range(min(self.game_list.count(), len(self.game_names))):
            item = self.game_list.item(i)
            if not item:
                continue
            original_name = self.game_names[i]

            if mods:
                preview_name = self._preview_name_modification(original_name, mods)
                if preview_name != original_name:
                    item.setText(preview_name)
                    item.setForeground(QColor(Theme.MODIFIED_FIELD_BORDER))
                else:
                    item.setText(original_name)
                    item.setForeground(QColor(Theme.TEXT_PRIMARY))
            else:
                item.setText(original_name)
                item.setForeground(QColor(Theme.TEXT_PRIMARY))

    @staticmethod
    def _preview_name_modification(name: str, mods: dict[str, str]) -> str:
        from steam_library_manager.utils.name_utils import apply_name_modifications

        return apply_name_modifications(name, mods)

    def _on_revert_toggled(self, checked: bool) -> None:
        field_widgets = [
            (self.cb_dev, self.edit_dev),
            (self.cb_pub, self.edit_pub),
            (self.cb_date, self.edit_date),
            (self.cb_pre, self.edit_pre),
            (self.cb_suf, self.edit_suf),
            (self.cb_rem, self.edit_rem),
        ]
        for checkbox, line_edit in field_widgets:
            checkbox.setEnabled(not checked)
            line_edit.setEnabled(not checked and checkbox.isChecked())

    def _apply(self):
        checks = [self.cb_dev, self.cb_pub, self.cb_date, self.cb_pre, self.cb_suf, self.cb_rem]
        if not self.cb_revert.isChecked() and not any(c.isChecked() for c in checks):
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
            self.result_metadata["developer"] = self.edit_dev.text().strip()
        if self.cb_pub.isChecked():
            self.result_metadata["publisher"] = self.edit_pub.text().strip()
        if self.cb_date.isChecked():
            self.result_metadata["release_date"] = parse_date_to_timestamp(self.edit_date.text().strip())  # ← FIX!

        mods = {}
        if self.cb_pre.isChecked():
            mods["prefix"] = self.edit_pre.text()
        if self.cb_suf.isChecked():
            mods["suffix"] = self.edit_suf.text()
        if self.cb_rem.isChecked():
            mods["remove"] = self.edit_rem.text()
        if mods:
            self.result_metadata["name_modifications"] = mods

        self.accept()

    def get_metadata(self) -> dict | None:
        return self.result_metadata


class MetadataRestoreDialog(BaseDialog):
    """Confirmation dialog for restoring modified game metadata to original values."""

    def __init__(self, parent, modified_count: int):
        self.modified_count = modified_count
        self.do_restore = False
        super().__init__(parent, title_key="menu.edit.reset_metadata", buttons="custom")

    def _build_content(self, layout: QVBoxLayout) -> None:
        info_lbl = QLabel(t("ui.metadata_editor.restore_info", count=self.modified_count))
        info_lbl.setWordWrap(True)
        layout.addWidget(info_lbl)

        warn_lbl = QLabel(f"{t('emoji.warning')} {t('auto_categorize.warning_backup')}")
        warn_lbl.setStyleSheet("color: orange;")
        layout.addWidget(warn_lbl)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton(t("common.cancel"))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        restore_btn = QPushButton(t("ui.metadata_editor.restore_button", count=self.modified_count))
        restore_btn.setDefault(True)
        restore_btn.clicked.connect(self._restore)
        btn_layout.addWidget(restore_btn)

        layout.addLayout(btn_layout)

    def _restore(self):
        self.do_restore = True
        self.accept()

    def should_restore(self) -> bool:
        return self.do_restore
