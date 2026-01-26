"""
Missing Metadata Detection Dialog - CSV Export
Speichern als: src/ui/missing_metadata_dialog.py
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
from src.core.game_manager import Game
from src.utils.i18n import t


class MissingMetadataDialog(QDialog):
    """Dialog zum Anzeigen von Spielen mit fehlenden Metadaten"""

    def __init__(self, parent, games: List[Game]):
        super().__init__(parent)
        self.games = games

        self.setWindowTitle(t('ui.tools.missing_metadata.title'))
        self.setMinimumSize(900, 600)
        self.setModal(True)

        self._create_ui()
        self._populate_table()

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

        # Auto-resize columns
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        # Alternating row colors
        self.table.setAlternatingRowColors(True)

        layout.addWidget(self.table)

        # Statistics
        stats_layout = QHBoxLayout()

        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("color: #888; font-size: 10px;")
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

    def _populate_table(self):
        """Befülle Tabelle mit Spielen"""
        self.table.setRowCount(len(self.games))

        missing_dev = 0
        missing_pub = 0
        missing_rel = 0

        # Helper function to check if a field is really missing
        def is_missing(value: str) -> bool:
            if not value:
                return True
            value_stripped = value.strip()
            if not value_stripped:
                return True
            # Check for "Unknown" in both EN and DE
            if value_stripped in ["Unknown", "Unbekannt"]:
                return True
            return False

        for row, game in enumerate(self.games):
            # AppID
            item = QTableWidgetItem(game.app_id)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row, 0, item)

            # Name
            item = QTableWidgetItem(game.name)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row, 1, item)

            # Developer
            dev = game.developer if game.developer else ""
            if is_missing(dev):
                dev = "❌ " + t('ui.tools.missing_metadata.missing')
                missing_dev += 1
            item = QTableWidgetItem(dev)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row, 2, item)

            # Publisher
            pub = game.publisher if game.publisher else ""
            if is_missing(pub):
                pub = "❌ " + t('ui.tools.missing_metadata.missing')
                missing_pub += 1
            item = QTableWidgetItem(pub)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row, 3, item)

            # Release
            rel = game.release_year if game.release_year else ""
            if is_missing(rel):
                rel = "❌ " + t('ui.tools.missing_metadata.missing')
                missing_rel += 1
            item = QTableWidgetItem(rel)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row, 4, item)

        # Update Statistics
        stats = t('ui.tools.missing_metadata.stats',
                  dev=missing_dev, pub=missing_pub, rel=missing_rel)
        self.stats_label.setText(stats)

    def _export_csv(self):
        """Exportiere Liste als CSV"""
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

                # Header
                writer.writerow([
                    'AppID',
                    'Game Name',
                    'Developer',
                    'Publisher',
                    'Release Date',
                    'Missing Fields'
                ])

                # Helper function
                def is_missing(value: str) -> bool:
                    if not value:
                        return True
                    value_stripped = value.strip()
                    if not value_stripped:
                        return True
                    if value_stripped in ["Unknown", "Unbekannt"]:
                        return True
                    return False

                # Data
                for game in self.games:
                    missing_fields = []

                    dev = game.developer if game.developer else ""
                    if is_missing(dev):
                        dev = "[MISSING]"
                        missing_fields.append("Developer")

                    pub = game.publisher if game.publisher else ""
                    if is_missing(pub):
                        pub = "[MISSING]"
                        missing_fields.append("Publisher")

                    rel = game.release_year if game.release_year else ""
                    if is_missing(rel):
                        rel = "[MISSING]"
                        missing_fields.append("Release")

                    writer.writerow([
                        game.app_id,
                        game.name,
                        dev,
                        pub,
                        rel,
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