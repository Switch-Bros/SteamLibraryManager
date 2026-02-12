# src/ui/missing_metadata_dialog.py

"""
Dialog for displaying and exporting games with missing metadata.

This module provides a dialog that shows a table of games that are missing
metadata fields (developer, publisher, release date) and allows exporting
the list to a CSV file.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QLabel,
    QFileDialog,
    QMessageBox,
    QHeaderView,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from pathlib import Path
import csv
from src.utils.date_utils import format_timestamp_to_date
from src.core.game_manager import Game
from src.utils.i18n import t


class MissingMetadataDialog(QDialog):
    """
    Dialog for displaying games with missing metadata.

    This dialog shows a table of games that are missing one or more metadata
    fields (developer, publisher, release date) and provides functionality to
    export the list to a CSV file.

    Attributes:
        games (list[Game]): List of games with missing metadata.
        table (QTableWidget): Table widget displaying the games.
        stats_label (QLabel): Label displaying statistics about missing fields.
    """

    def __init__(self, parent, games: list[Game]):
        """
        Initializes the missing metadata dialog.

        Args:
            parent: Parent widget.
            games (list[Game]): List of games with missing metadata.
        """
        super().__init__(parent)
        self.games = games

        self.setWindowTitle(t("ui.tools.missing_metadata.title"))
        self.setMinimumSize(900, 600)
        self.setModal(True)

        self._create_ui()
        self._populate_table()

    @staticmethod
    def _is_missing(value) -> bool:
        """
        Checks if a metadata value is considered missing.

        Args:
            value: The value to check.

        Returns:
            bool: True if the value is missing, False otherwise.
        """
        if value is None:
            return True
        value_str = str(value).strip()
        if not value_str:
            return True
        if value_str.lower() in ["unknown", "unbekannt", "none", "n/a"]:
            return True
        return False

    def _create_ui(self):
        """Creates the user interface for the dialog."""
        layout = QVBoxLayout(self)

        # Header
        header = QLabel(t("ui.tools.missing_metadata.header", count=len(self.games)))
        header.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(header)

        # Info Text
        info = QLabel(t("ui.tools.missing_metadata.info"))
        info.setWordWrap(True)
        info.setStyleSheet("color: #888; padding: 10px 0;")
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

        # --- Column Behavior: Fixed widths with stretch for name column ---
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # App ID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Name (stretches)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # Developer
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)  # Publisher
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)  # Release

        # Set fixed column widths
        self.table.setColumnWidth(0, 70)  # App ID
        self.table.setColumnWidth(2, 180)  # Developer
        self.table.setColumnWidth(3, 130)  # Publisher
        self.table.setColumnWidth(4, 110)  # Release

        # Alternating row colors
        self.table.setAlternatingRowColors(True)

        layout.addWidget(self.table)

        # Statistics Label
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("color: #888; font-size: 10px;")

        # Stats Layout
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
        """
        Creates a read-only table item.

        Args:
            text (str): The text to display in the item.

        Returns:
            QTableWidgetItem: A read-only table item.
        """
        item = QTableWidgetItem(str(text))

        # FIX: Calculate flags as integer first to avoid PyCharm type confusion
        flags_val = Qt.ItemFlag.ItemIsEnabled.value | Qt.ItemFlag.ItemIsSelectable.value
        item.setFlags(Qt.ItemFlag(flags_val))

        return item

    def _populate_table(self):
        """
        Populates the table with games and their missing metadata.

        This method fills the table with game information and marks missing
        fields with an ❌ emoji. It also updates the statistics label.
        """
        self.table.setRowCount(len(self.games))

        missing_dev = 0
        missing_pub = 0
        missing_rel = 0

        for row, game in enumerate(self.games):
            # 1. AppID
            self.table.setItem(row, 0, self._create_item(str(game.app_id)))

            # 2. Name
            self.table.setItem(row, 1, self._create_item(game.name))

            # 3. Developer
            dev_val = game.developer if game.developer else ""
            if self._is_missing(dev_val):
                # Emoji prefix assembled here — locale string is plain text
                display_dev = f"{t('emoji.error')} {t('ui.tools.missing_metadata.missing_marked')}"
                missing_dev += 1
            else:
                display_dev = str(dev_val)

            self.table.setItem(row, 2, self._create_item(display_dev))

            # 4. Publisher
            pub_val = game.publisher if game.publisher else ""
            if self._is_missing(pub_val):
                display_pub = f"{t('emoji.error')} {t('ui.tools.missing_metadata.missing_marked')}"
                missing_pub += 1
            else:
                display_pub = str(pub_val)

            self.table.setItem(row, 3, self._create_item(display_pub))

            # 5. Release
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
        """
        Exports the missing metadata list to a CSV file.

        This method opens a file dialog for the user to choose a save location,
        then writes the game data with missing metadata information to a CSV file.
        """
        default_name = f"missing_metadata_{len(self.games)}_games.csv"

        file_path, _ = QFileDialog.getSaveFileName(
            self, t("ui.tools.missing_metadata.save_csv"), str(Path.home() / default_name), "CSV Files (*.csv)"
        )

        if not file_path:
            return

        try:
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)

                # Header (Localized)
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

                # Data
                for game in self.games:
                    missing_fields = []

                    # Developer
                    dev_val = game.developer if game.developer else ""
                    if self._is_missing(dev_val):
                        dev_val = t("ui.tools.missing_metadata.missing")
                        missing_fields.append(t("ui.game_details.developer"))

                    # Publisher
                    pub_val = game.publisher if game.publisher else ""
                    if self._is_missing(pub_val):
                        pub_val = t("ui.tools.missing_metadata.missing")
                        missing_fields.append(t("ui.game_details.publisher"))

                    # Release
                    raw_rel = game.release_year if game.release_year else ""
                    if self._is_missing(raw_rel):
                        rel_val = t("ui.tools.missing_metadata.missing")
                        missing_fields.append(t("ui.game_details.release_year"))
                    else:
                        rel_val = format_timestamp_to_date(raw_rel)

                    writer.writerow(
                        [game.app_id, game.name, str(dev_val), str(pub_val), str(rel_val), ", ".join(missing_fields)]
                    )

            QMessageBox.information(
                self,
                t("common.success"),
                t("ui.tools.missing_metadata.export_success", count=len(self.games), path=file_path),
            )

        except OSError as e:
            QMessageBox.critical(self, t("common.error"), t("ui.tools.missing_metadata.export_error", error=str(e)))
