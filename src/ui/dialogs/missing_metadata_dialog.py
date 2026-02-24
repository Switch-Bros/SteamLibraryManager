# src/ui/dialogs/missing_metadata_dialog.py

"""Dialog for displaying and exporting games with missing metadata.

Shows a table of games that are missing metadata fields (developer,
publisher, release date) and allows exporting the list to a CSV file.
"""

from __future__ import annotations

import csv
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QLabel,
    QFileDialog,
    QHeaderView,
)

from src.core.game_manager import Game
from src.ui.theme import Theme
from src.ui.utils.font_helper import FontHelper
from src.ui.widgets.base_dialog import BaseDialog
from src.ui.widgets.ui_helper import UIHelper
from src.utils.date_utils import format_timestamp_to_date
from src.utils.i18n import t

__all__ = ["MissingMetadataDialog"]


class MissingMetadataDialog(BaseDialog):
    """Dialog for displaying games with missing metadata.

    Shows a table of games that are missing one or more metadata
    fields (developer, publisher, release date) and provides
    functionality to export the list to a CSV file.

    Attributes:
        games: List of games with missing metadata.
        table: Table widget displaying the games.
        stats_label: Label displaying statistics about missing fields.
    """

    def __init__(self, parent, games: list[Game]):
        """Initializes the missing metadata dialog.

        Args:
            parent: Parent widget.
            games: List of games with missing metadata.
        """
        self.games = games

        super().__init__(
            parent,
            title_key="ui.tools.missing_metadata.title",
            min_width=900,
            show_title_label=False,
            buttons="custom",
        )
        self.setMinimumHeight(600)
        self._populate_table()

    @staticmethod
    def _is_missing(value) -> bool:
        """Checks if a metadata value is considered missing.

        Args:
            value: The value to check.

        Returns:
            True if the value is missing, False otherwise.
        """
        if value is None:
            return True
        value_str = str(value).strip()
        if not value_str:
            return True
        if value_str.lower() in ["unknown", "unbekannt", "none", "n/a"]:
            return True
        return False

    def _build_content(self, layout: QVBoxLayout) -> None:
        """Creates the dialog content with header, table, stats, and buttons."""
        # Header
        header = QLabel(t("ui.tools.missing_metadata.header", count=len(self.games)))
        header.setFont(FontHelper.get_font(14, FontHelper.BOLD))
        layout.addWidget(header)

        # Info Text
        info = QLabel(t("ui.tools.missing_metadata.info"))
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {Theme.TEXT_MUTED}; padding: 10px 0;")
        layout.addWidget(info)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            [
                t("ui.tools.missing_metadata.col_appid"),
                t("ui.tools.missing_metadata.col_name"),
                t("ui.tools.missing_metadata.col_developer"),
                t("ui.tools.missing_metadata.col_publisher"),
                t("ui.tools.missing_metadata.col_release"),
            ]
        )

        # Column behavior: fixed widths with stretch for name column
        tbl_header = self.table.horizontalHeader()
        tbl_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        tbl_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        tbl_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        tbl_header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        tbl_header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)

        self.table.setColumnWidth(0, 70)
        self.table.setColumnWidth(2, 180)
        self.table.setColumnWidth(3, 130)
        self.table.setColumnWidth(4, 110)

        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        # Statistics Label
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 10px;")

        stats_layout = QHBoxLayout()
        stats_layout.addWidget(self.stats_label)
        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        export_btn = QPushButton(t("ui.tools.missing_metadata.export_csv"))
        export_btn.clicked.connect(self._export_csv)
        btn_layout.addWidget(export_btn)

        close_btn = QPushButton(t("common.close"))
        close_btn.setDefault(True)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    @staticmethod
    def _create_item(text: str) -> QTableWidgetItem:
        """Creates a read-only table item.

        Args:
            text: The text to display in the item.

        Returns:
            A read-only table item.
        """
        item = QTableWidgetItem(str(text))

        # Calculate flags as integer first to avoid PyCharm type confusion
        flags_val = Qt.ItemFlag.ItemIsEnabled.value | Qt.ItemFlag.ItemIsSelectable.value
        item.setFlags(Qt.ItemFlag(flags_val))

        return item

    def _populate_table(self):
        """Populates the table with games and their missing metadata."""
        self.table.setRowCount(len(self.games))

        missing_dev = 0
        missing_pub = 0
        missing_rel = 0

        for row, game in enumerate(self.games):
            self.table.setItem(row, 0, self._create_item(str(game.app_id)))
            self.table.setItem(row, 1, self._create_item(game.name))

            # Developer
            dev_val = game.developer if game.developer else ""
            if self._is_missing(dev_val):
                display_dev = f"{t('emoji.error')} {t('ui.tools.missing_metadata.missing_marked')}"
                missing_dev += 1
            else:
                display_dev = str(dev_val)
            self.table.setItem(row, 2, self._create_item(display_dev))

            # Publisher
            pub_val = game.publisher if game.publisher else ""
            if self._is_missing(pub_val):
                display_pub = f"{t('emoji.error')} {t('ui.tools.missing_metadata.missing_marked')}"
                missing_pub += 1
            else:
                display_pub = str(pub_val)
            self.table.setItem(row, 3, self._create_item(display_pub))

            # Release
            raw_rel = game.release_year if game.release_year else ""
            if self._is_missing(raw_rel):
                display_rel = f"{t('emoji.error')} {t('ui.tools.missing_metadata.missing_marked')}"
                missing_rel += 1
            else:
                display_rel = format_timestamp_to_date(raw_rel)
            self.table.setItem(row, 4, self._create_item(display_rel))

        # Update Statistics
        stats = t("ui.tools.missing_metadata.stats", count=len(self.games))
        self.stats_label.setText(stats)

    def _export_csv(self):
        """Exports the missing metadata list to a CSV file."""
        default_name = f"missing_metadata_{len(self.games)}_games.csv"

        file_path, _ = QFileDialog.getSaveFileName(
            self, t("ui.tools.missing_metadata.save_csv"), str(Path.home() / default_name), "CSV Files (*.csv)"
        )

        if not file_path:
            return

        try:
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)

                writer.writerow(
                    [
                        t("ui.tools.missing_metadata.col_appid"),
                        t("ui.tools.missing_metadata.col_name"),
                        t("ui.tools.missing_metadata.col_developer"),
                        t("ui.tools.missing_metadata.col_publisher"),
                        t("ui.tools.missing_metadata.col_release"),
                        t("ui.tools.missing_metadata.col_missing_fields"),
                    ]
                )

                for game in self.games:
                    missing_fields = []

                    dev_val = game.developer if game.developer else ""
                    if self._is_missing(dev_val):
                        dev_val = t("ui.tools.missing_metadata.missing")
                        missing_fields.append(t("ui.game_details.developer"))

                    pub_val = game.publisher if game.publisher else ""
                    if self._is_missing(pub_val):
                        pub_val = t("ui.tools.missing_metadata.missing")
                        missing_fields.append(t("ui.game_details.publisher"))

                    raw_rel = game.release_year if game.release_year else ""
                    if self._is_missing(raw_rel):
                        rel_val = t("ui.tools.missing_metadata.missing")
                        missing_fields.append(t("ui.game_details.release_year"))
                    else:
                        rel_val = format_timestamp_to_date(raw_rel)

                    writer.writerow(
                        [game.app_id, game.name, str(dev_val), str(pub_val), str(rel_val), ", ".join(missing_fields)]
                    )

            UIHelper.show_success(
                self,
                t("ui.tools.missing_metadata.export_success", count=len(self.games), path=file_path),
            )

        except OSError as e:
            UIHelper.show_error(self, t("ui.tools.missing_metadata.export_error", error=str(e)))
