"""
Missing Metadata Detection Dialog - Date Formatter Edition
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
from datetime import datetime  # <--- WICHTIG: Für Datumsumrechnung
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

        # --- SPALTEN-VERHALTEN: Interaktiv ---
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(False)

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

    def _format_date(self, value) -> str:
        """Wandelt Unix-Timestamps in lesbares Datum um"""
        if not value:
            return ""

        value_str = str(value).strip()

        # Prüfen ob es eine Zahl ist
        if value_str.isdigit():
            try:
                ts = int(value_str)
                # Einfache Prüfung: Ist die Zahl größer als 19900101?
                # Ein Timestamp für das Jahr 2000 ist schon 946684800.
                # Ein Jahr wie "2004" ist viel kleiner.
                # Grenze: Alles über 100.000.000 behandeln wir als Timestamp (ca. Jahr 1973)
                if ts > 100000000:
                    dt = datetime.fromtimestamp(ts)
                    return dt.strftime("%Y-%m-%d")
            except Exception:
                pass  # Falls Fehler, gib Original zurück

        return value_str

    def _populate_table(self):
        """Befülle Tabelle mit Spielen"""
        self.table.setRowCount(len(self.games))

        missing_dev = 0
        missing_pub = 0
        missing_rel = 0

        # Helper function
        def is_missing(value) -> bool:
            if value is None:
                return True
            value_str = str(value).strip()
            if not value_str:
                return True
            if value_str in ["Unknown", "Unbekannt", "None"]:
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
            item = QTableWidgetItem(str(dev))
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row, 2, item)

            # Publisher
            pub = game.publisher if game.publisher else ""
            if is_missing(pub):
                pub = "❌ " + t('ui.tools.missing_metadata.missing')
                missing_pub += 1
            item = QTableWidgetItem(str(pub))
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row, 3, item)

            # Release (JETZT MIT FORMATIERUNG)
            raw_rel = game.release_year if game.release_year else ""

            # Prüfen ob es fehlt (auf Basis des Rohwertes)
            if is_missing(raw_rel):
                display_rel = "❌ " + t('ui.tools.missing_metadata.missing')
                missing_rel += 1
            else:
                # Formatieren für Anzeige
                display_rel = self._format_date(raw_rel)

            item = QTableWidgetItem(display_rel)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row, 4, item)

        # Update Statistics
        stats = t('ui.tools.missing_metadata.stats',
                  dev=missing_dev, pub=missing_pub, rel=missing_rel)
        self.stats_label.setText(stats)

        # Initiale Größenanpassung
        self.table.resizeColumnsToContents()

        # Mindestbreite für Name
        current_width = self.table.columnWidth(1)
        if current_width < 200:
            self.table.setColumnWidth(1, 200)
        elif current_width > 600:
            self.table.setColumnWidth(1, 600)

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

                def is_missing(value) -> bool:
                    if value is None:
                        return True
                    value_str = str(value).strip()
                    if not value_str:
                        return True
                    if value_str in ["Unknown", "Unbekannt", "None"]:
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

                    raw_rel = game.release_year if game.release_year else ""
                    if is_missing(raw_rel):
                        rel = "[MISSING]"
                        missing_fields.append("Release")
                    else:
                        # Auch im CSV schön formatieren
                        rel = self._format_date(raw_rel)

                    writer.writerow([
                        game.app_id,
                        game.name,
                        str(dev),
                        str(pub),
                        str(rel),
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