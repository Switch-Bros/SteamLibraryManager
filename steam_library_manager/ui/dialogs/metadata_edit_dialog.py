#
# steam_library_manager/ui/dialogs/metadata_edit_dialog.py
# Single-game metadata editing dialog
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

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
    """Metadata editor for a single game with live change highlighting."""

    def __init__(self, parent, game_name: str, current_metadata: dict, original_metadata: dict | None = None):
        self.game_name = game_name
        self.current_metadata = current_metadata
        self.original_metadata = original_metadata or {}
        self.result_metadata = None
        super().__init__(
            parent,
            title_text=t("ui.metadata_editor.editing_title", game=game_name),
            min_width=600,
            buttons="custom",
        )
        self._populate_fields()

    def _build_content(self, layout: QVBoxLayout) -> None:
        info = QLabel(t("ui.metadata_editor.info_tracking"))
        info.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(info)

        form = QFormLayout()

        self.name_edit = QLineEdit()
        self.sort_as_edit = QLineEdit()
        self.developer_edit = QLineEdit()
        self.publisher_edit = QLineEdit()
        self.release_date_edit = QLineEdit()

        form.addRow(t("ui.metadata_editor.game_name_label"), self.name_edit)
        form.addRow(t("ui.metadata_editor.sort_as_label"), self.sort_as_edit)

        sort_help = QLabel(t("ui.metadata_editor.sort_as_help"))
        sort_help.setStyleSheet("color: gray; font-size: 9px;")
        form.addRow("", sort_help)

        form.addRow(t("ui.game_details.developer") + ":", self.developer_edit)
        form.addRow(t("ui.game_details.publisher") + ":", self.publisher_edit)
        form.addRow(t("ui.game_details.release_year") + ":", self.release_date_edit)

        date_help = QLabel(t("ui.metadata_editor.date_help"))
        date_help.setStyleSheet("color: gray; font-size: 9px;")
        form.addRow("", date_help)

        layout.addLayout(form)

        original_group = QGroupBox(t("ui.metadata_editor.original_values_group"))
        original_layout = QVBoxLayout()
        self.original_text = QTextEdit()
        self.original_text.setReadOnly(True)
        self.original_text.setMaximumHeight(100)
        original_layout.addWidget(self.original_text)
        original_group.setLayout(original_layout)
        layout.addWidget(original_group)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        revert_btn = QPushButton(t("ui.metadata_editor.revert_to_original"))
        revert_btn.setStyleSheet("background-color: #6c757d; color: white;")
        revert_btn.clicked.connect(self._revert_to_original)
        btn_layout.addWidget(revert_btn)

        cancel_btn = QPushButton(t("common.cancel"))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton(t("common.save"))
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _populate_fields(self):
        m = self.current_metadata
        o = self.original_metadata

        self._original_display: dict[str, str] = {
            "name": str(o.get("name", "")),
            "developer": str(o.get("developer", "")),
            "publisher": str(o.get("publisher", "")),
            "release_date": format_timestamp_to_date(o.get("release_date", "")),
        }

        self.name_edit.setText(m.get("name", ""))
        self.sort_as_edit.setText(m.get("sort_as", ""))
        self.developer_edit.setText(m.get("developer", ""))
        self.publisher_edit.setText(m.get("publisher", ""))
        self.release_date_edit.setText(format_timestamp_to_date(m.get("release_date", "")))

        self.name_edit.textChanged.connect(self._update_highlighting)
        self.developer_edit.textChanged.connect(self._update_highlighting)
        self.publisher_edit.textChanged.connect(self._update_highlighting)
        self.release_date_edit.textChanged.connect(self._update_highlighting)

        self._update_highlighting()

        na = t("ui.game_details.value_unknown")
        rel_display = self._original_display["release_date"] or na
        lines = [
            f"{t('ui.game_details.name')}: {o.get('name', na)}",
            f"{t('ui.game_details.developer')}: {o.get('developer', na)}",
            f"{t('ui.game_details.publisher')}: {o.get('publisher', na)}",
            f"{t('ui.game_details.release_year')}: {rel_display}",
        ]

        self.original_text.setPlainText("\n".join(lines))

    def _update_highlighting(self):
        modified_style = Theme.modified_field()
        na = t("ui.game_details.value_unknown")

        fields = [
            (self.name_edit, "name"),
            (self.developer_edit, "developer"),
            (self.publisher_edit, "publisher"),
            (self.release_date_edit, "release_date"),
        ]

        for widget, key in fields:
            original_val = self._original_display.get(key, "")
            if widget.text().strip() != original_val.strip():
                widget.setStyleSheet(modified_style)
                widget.setToolTip(t("ui.metadata_editor.modified_tooltip", original=original_val or na))
            else:
                widget.setStyleSheet("")
                widget.setToolTip("")

    def _revert_to_original(self):
        if not self.original_metadata:
            UIHelper.show_info(
                self, t("ui.metadata_editor.revert_no_original"), title=t("ui.metadata_editor.revert_title")
            )
            return

        if not UIHelper.confirm(self, t("ui.metadata_editor.revert_confirm"), t("ui.metadata_editor.revert_title")):
            return

        self.name_edit.setText(self._original_display["name"])
        self.developer_edit.setText(self._original_display["developer"])
        self.publisher_edit.setText(self._original_display["publisher"])
        self.release_date_edit.setText(self._original_display["release_date"])

    def _save(self):
        """Validates fields and stores result_metadata. VDF write happens on app exit."""
        name = self.name_edit.text().strip()
        if not name:
            UIHelper.show_warning(self, t("ui.metadata_editor.error_empty_name"))
            return

        self.result_metadata = {
            "name": name,
            "sort_as": self.sort_as_edit.text().strip() or name,
            "developer": self.developer_edit.text().strip(),
            "publisher": self.publisher_edit.text().strip(),
            "release_date": parse_date_to_timestamp(self.release_date_edit.text().strip()),
        }
        self.accept()

    def get_metadata(self) -> dict | None:
        return self.result_metadata
