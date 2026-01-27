"""
Missing Metadata Detection Dialog - Clean Code & Optimized
Save as: src/ui/missing_metadata_dialog.py
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QFileDialog, QMessageBox, QHeaderView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from typing import List
from pathlib import Path
import csv
from datetime import datetime
from src.core.game_manager import Game
from src.utils.i18n import t


class MissingMetadataDialog(QDialog):
    """Dialog to display games with missing metadata"""

    def __init__(self, parent, games: List[Game]):
        super().__init__(parent)
        self.games = games

        self.setWindowTitle(t('ui.tools.missing_metadata.title'))
        self.setMinimumSize(900, 600)
        self.setModal(True)

        self._create_ui()
        self._populate_table()

    @staticmethod
    def _is_missing(value) -> bool:
        """Checks if a value is considered 'missing'"""
        if value is None:
            return True
        value_str = str(value).strip()
        if not value_str:
            return True
        if value_str.lower() in ["unknown", "unbekannt", "none", "n/a"]:
            return True
        return False

    @staticmethod
    def _format_date(value) -> str:
        """Converts Unix timestamps to readable date (YYYY-MM-DD)"""
        if not value:
            return ""

        value_str = str(value).strip()

        # Check if it is a number
        if value_str.isdigit():
            try:
                ts = int(value_str)
                # Plausibility check: Is number > 100,000,000 (approx year 1973)?
                if ts > 100000000:
                    dt = datetime.fromtimestamp(ts)
                    return dt.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                pass  # Return original on error

        return value_str

    def _create_ui(self):
        layout = QVBoxLayout(self)

        # Header
        header = QLabel(t('ui.tools.missing_metadata.header', count=len(self.games)))
        header.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(header)

        # Info Text
        info = QLabel(t('ui.tools.missing_metadata.info'))
        info.setWordWrap(True)
        info.setStyleSheet("color: #888; padding: 10px 0;")
        layout.addWidget(info)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            t('ui.tools.missing_metadata.col_appid'),
            t('ui.tools.missing_metadata.col_name'),
            t('ui.tools.missing_metadata.col_developer'),
            t('ui.tools.missing_metadata.col_publisher'),
            t('ui.tools.missing_metadata.col_release')
        ])

        # --- Column Behavior: Interactive ---
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(False)

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

        export_btn = QPushButton(t('ui.tools.missing_metadata.export_csv'))
        export_btn.clicked.connect(self._export_csv)
        btn_layout.addWidget(export_btn)

        close_btn = QPushButton(t('ui.dialogs.close'))
        close_btn.setDefault(True)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    @staticmethod
    def _create_item(text: str) -> QTableWidgetItem:
        """Helper to create a read-only table item to reduce code duplication"""
        item = QTableWidgetItem(str(text))

        # FIX: Calculate flags as integer first to avoid PyCharm type confusion
        flags_val = Qt.ItemFlag.ItemIsEnabled.value | Qt.ItemFlag.ItemIsSelectable.value
        item.setFlags(Qt.ItemFlag(flags_val))

        return item

    def _populate_table(self):
        """Populate table with games"""
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
                display_dev = f"❌ {t('ui.tools.missing_metadata.missing')}"
                missing_dev += 1
            else:
                display_dev = str(dev_val)

            self.table.setItem(row, 2, self._create_item(display_dev))

            # 4. Publisher
            pub_val = game.publisher if game.publisher else ""
            if self._is_missing(pub_val):
                display_pub = f"❌ {t('ui.tools.missing_metadata.missing')}"
                missing_pub += 1
            else:
                display_pub = str(pub_val)

            self.table.setItem(row, 3, self._create_item(display_pub))

            # 5. Release
            raw_rel = game.release_year if game.release_year else ""
            if self._is_missing(raw_rel):
                display_rel = f"❌ {t('ui.tools.missing_metadata.missing')}"
                missing_rel += 1
            else:
                display_rel = self._format_date(raw_rel)

            self.table.setItem(row, 4, self._create_item(display_rel))

        # Update Statistics
        stats = t('ui.tools.missing_metadata.stats',
                  dev=missing_dev, pub=missing_pub, rel=missing_rel)
        self.stats_label.setText(stats)

        # Initial size adjustment
        self.table.resizeColumnsToContents()

        # Minimum width for Name
        current_width = self.table.columnWidth(1)
        if current_width < 200:
            self.table.setColumnWidth(1, 200)
        elif current_width > 600:
            self.table.setColumnWidth(1, 600)

    def _export_csv(self):
        """Export list as CSV"""
        default_name = f"missing_metadata_{len(self.games)}_games.csv"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            t('ui.tools.missing_metadata.save_csv'),
            str(Path.home() / default_name),
            "CSV Files (*.csv)"
        )

        if not file_path:
            return

        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # Header (Localized)
                writer.writerow([
                    t('ui.tools.missing_metadata.col_appid'),
                    t('ui.tools.missing_metadata.col_name'),
                    t('ui.tools.missing_metadata.col_developer'),
                    t('ui.tools.missing_metadata.col_publisher'),
                    t('ui.tools.missing_metadata.col_release'),
                    t('ui.tools.missing_metadata.col_missing_fields')
                ])

                # Data
                for game in self.games:
                    missing_fields = []

                    # Developer
                    dev_val = game.developer if game.developer else ""
                    if self._is_missing(dev_val):
                        dev_val = t('ui.tools.missing_metadata.missing')
                        missing_fields.append(t('ui.game_details.developer'))

                    # Publisher
                    pub_val = game.publisher if game.publisher else ""
                    if self._is_missing(pub_val):
                        pub_val = t('ui.tools.missing_metadata.missing')
                        missing_fields.append(t('ui.game_details.publisher'))

                    # Release
                    raw_rel = game.release_year if game.release_year else ""
                    if self._is_missing(raw_rel):
                        rel_val = t('ui.tools.missing_metadata.missing')
                        missing_fields.append(t('ui.game_details.release_year'))
                    else:
                        rel_val = self._format_date(raw_rel)

                    writer.writerow([
                        game.app_id,
                        game.name,
                        str(dev_val),
                        str(pub_val),
                        str(rel_val),
                        ", ".join(missing_fields)
                    ])

            QMessageBox.information(
                self,
                t('ui.dialogs.success'),
                t('ui.tools.missing_metadata.export_success',
                  count=len(self.games), path=file_path)
            )

        except OSError as e:
            QMessageBox.critical(
                self,
                t('ui.dialogs.error'),
                t('ui.tools.missing_metadata.export_error', error=str(e))
            )