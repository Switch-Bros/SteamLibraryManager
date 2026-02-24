# src/ui/dialogs/curator_management_dialog.py

"""Dialog for managing Steam Curators.

Provides a table view of configured curators with controls
for adding, removing, and refreshing curator data. Curators
and their recommendations are persisted in the SQLite database.
"""

from __future__ import annotations

__all__ = ["CuratorManagementDialog"]

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.ui.widgets.base_dialog import BaseDialog
from src.ui.widgets.ui_helper import UIHelper
from src.utils.i18n import t

if TYPE_CHECKING:
    from src.core.database import Database

logger = logging.getLogger("steamlibmgr.curator_management_dialog")

# Column indices
_COL_ACTIVE = 0
_COL_NAME = 1
_COL_COUNT = 2
_COL_UPDATED = 3


class CuratorManagementDialog(BaseDialog):
    """Dialog for managing Steam Curators and their recommendations.

    Displays a table of configured curators with active toggle,
    recommendation count, and last-updated timestamp. Provides
    Add, Popular, Remove, and Refresh actions.

    Attributes:
        db: Database instance for curator operations.
    """

    def __init__(self, parent: QWidget | None, db_path: Path) -> None:
        """Initialize the curator management dialog.

        Args:
            parent: Parent widget.
            db_path: Path to the SQLite database file.
        """
        self._db_path = db_path
        self._db: Database | None = None

        super().__init__(
            parent,
            title_key="ui.curator.title",
            min_width=700,
            buttons="custom",
        )

    def _build_content(self, layout: QVBoxLayout) -> None:
        """Build the dialog content with table and action buttons."""
        self._open_db()

        # Table
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(
            [
                t("ui.curator.col_active"),
                t("ui.curator.col_name"),
                t("ui.curator.col_count"),
                t("ui.curator.col_updated"),
            ]
        )
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(_COL_ACTIVE, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(_COL_NAME, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(_COL_COUNT, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(_COL_UPDATED, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setColumnWidth(_COL_ACTIVE, 60)
        self._table.setColumnWidth(_COL_COUNT, 80)

        layout.addWidget(self._table)

        # Buttons
        btn_layout = QHBoxLayout()

        add_btn = QPushButton(t("ui.curator.add"))
        add_btn.clicked.connect(self._on_add)
        btn_layout.addWidget(add_btn)

        popular_btn = QPushButton(t("ui.curator.popular"))
        popular_btn.clicked.connect(self._on_popular)
        btn_layout.addWidget(popular_btn)

        remove_btn = QPushButton(t("ui.curator.remove"))
        remove_btn.clicked.connect(self._on_remove)
        btn_layout.addWidget(remove_btn)

        btn_layout.addStretch()

        close_btn = QPushButton(t("common.close"))
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

        # Initial population
        self._refresh_table()

    # ------------------------------------------------------------------
    # Table population
    # ------------------------------------------------------------------

    def _refresh_table(self) -> None:
        """Reload curator data from DB into the table."""
        if not self._db:
            return

        curators = self._db.get_all_curators()
        self._table.setRowCount(len(curators))

        for row, curator in enumerate(curators):
            # Active checkbox
            active_widget = QWidget()
            active_layout = QHBoxLayout(active_widget)
            active_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            active_layout.setContentsMargins(0, 0, 0, 0)
            checkbox = QCheckBox()
            checkbox.setChecked(bool(curator["active"]))
            curator_id = curator["curator_id"]
            checkbox.toggled.connect(lambda checked, cid=curator_id: self._on_active_toggled(cid, checked))
            active_layout.addWidget(checkbox)
            self._table.setCellWidget(row, _COL_ACTIVE, active_widget)

            # Name
            name_item = QTableWidgetItem(curator["name"])
            name_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self._table.setItem(row, _COL_NAME, name_item)

            # Recommendation count
            count = curator.get("total_count", 0) or 0
            count_item = QTableWidgetItem(str(count))
            count_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, _COL_COUNT, count_item)

            # Last updated
            last_updated = curator.get("last_updated") or t("common.never")
            updated_item = QTableWidgetItem(str(last_updated))
            updated_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self._table.setItem(row, _COL_UPDATED, updated_item)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_active_toggled(self, curator_id: int, active: bool) -> None:
        """Toggle a curator's active state in the database.

        Args:
            curator_id: The curator's ID.
            active: New active state.
        """
        if self._db:
            self._db.toggle_curator_active(curator_id, active)

    def _on_add(self) -> None:
        """Add a curator by URL or numeric ID."""
        from src.services.curator_client import CuratorClient

        text, ok = QInputDialog.getText(
            self,
            t("ui.curator.add"),
            t("ui.curator.add_prompt"),
        )
        if not ok or not text.strip():
            return

        text = text.strip()
        curator_id = CuratorClient.parse_curator_id(text)
        if not curator_id:
            UIHelper.show_warning(self, t("ui.curator.invalid_url"))
            return

        # Use the raw name from URL or fall back to generic name
        raw_name = CuratorClient.parse_curator_name(text)
        name = raw_name or f"Curator {curator_id}"
        url = text if text.startswith("http") else f"https://store.steampowered.com/curator/{curator_id}/"

        if self._db:
            self._db.add_curator(curator_id, name, url)
            self._refresh_table()

    def _on_popular(self) -> None:
        """Show popular curator presets for quick adding."""
        from src.services.curator_presets import POPULAR_CURATORS

        if not self._db:
            return

        # Get already-added curator IDs
        existing_ids = {c["curator_id"] for c in self._db.get_all_curators()}

        # Build a simple selection dialog
        dialog = QDialog(self)
        dialog.setWindowTitle(t("ui.curator.popular_title"))
        dialog.setMinimumWidth(500)
        dialog.setModal(True)

        dlg_layout = QVBoxLayout(dialog)

        info_label = QLabel(t("ui.curator.popular_info"))
        info_label.setWordWrap(True)
        dlg_layout.addWidget(info_label)

        checkboxes: list[tuple[QCheckBox, int, str]] = []
        for preset in POPULAR_CURATORS:
            label = f"{preset.name} — {preset.description}"
            cb = QCheckBox(label)
            if preset.curator_id in existing_ids:
                cb.setChecked(True)
                cb.setEnabled(False)
                cb.setToolTip(t("ui.curator.already_added"))
            dlg_layout.addWidget(cb)
            checkboxes.append((cb, preset.curator_id, preset.name))

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton(t("common.cancel"))
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)
        ok_btn = QPushButton(t("common.ok"))
        ok_btn.clicked.connect(dialog.accept)
        ok_btn.setDefault(True)
        btn_layout.addWidget(ok_btn)
        dlg_layout.addLayout(btn_layout)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        added = 0
        for cb, curator_id, name in checkboxes:
            if cb.isChecked() and curator_id not in existing_ids:
                url = f"https://store.steampowered.com/curator/{curator_id}/"
                self._db.add_curator(curator_id, name, url, source="preset")
                added += 1

        if added > 0:
            self._refresh_table()

    def _on_remove(self) -> None:
        """Remove the selected curator after confirmation."""
        if not self._db:
            return

        selected_rows = self._table.selectionModel().selectedRows()
        if not selected_rows:
            UIHelper.show_warning(self, t("ui.curator.no_selection"))
            return

        row = selected_rows[0].row()
        name_item = self._table.item(row, _COL_NAME)
        if not name_item:
            return

        curator_name = name_item.text()
        if not UIHelper.confirm(
            self,
            t("ui.curator.remove_confirm", name=curator_name),
            title=t("ui.curator.remove"),
        ):
            return

        # Find curator_id from the all_curators list by matching row index
        curators = self._db.get_all_curators()
        if row < len(curators):
            self._db.remove_curator(curators[row]["curator_id"])
            self._refresh_table()

    # ------------------------------------------------------------------
    # DB lifecycle
    # ------------------------------------------------------------------

    def _open_db(self) -> None:
        """Open a database connection for the dialog's lifetime."""
        from src.core.database import Database

        self._db = Database(self._db_path)

    def closeEvent(self, event) -> None:
        """Close DB connection when dialog is closed."""
        if self._db:
            self._db.close()
            self._db = None
        super().closeEvent(event)
