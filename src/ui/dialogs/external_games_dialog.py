"""Dialog for managing external (non-Steam) games.

Provides a UI to scan installed platforms, view found games,
and add them to Steam as Non-Steam shortcuts.
"""

from __future__ import annotations

import logging
from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.config import config
from src.core.shortcuts_manager import ShortcutsManager
from src.integrations.external_games.models import ExternalGame
from src.services.external_games_service import ExternalGamesService
from src.ui.widgets.base_dialog import BaseDialog
from src.ui.widgets.ui_helper import UIHelper
from src.utils.i18n import t

__all__ = ["ExternalGamesDialog"]

logger = logging.getLogger("steamlibmgr.external_games_dialog")


class _ScanThread(QThread):
    """Background thread for platform scanning."""

    finished_scan = pyqtSignal(dict)

    def __init__(self, service: ExternalGamesService) -> None:
        super().__init__()
        self._service = service

    def run(self) -> None:
        """Scans all platforms and emits results."""
        try:
            results = self._service.scan_all_platforms()
            self.finished_scan.emit(results)
        except Exception:
            logger.exception("Platform scan failed")
            self.finished_scan.emit({})


class _AddThread(QThread):
    """Background thread for batch-adding games to Steam."""

    progress = pyqtSignal(int, int, str)
    finished_add = pyqtSignal(dict)

    def __init__(
        self,
        service: ExternalGamesService,
        games: list[ExternalGame],
        category_tag: bool,
    ) -> None:
        super().__init__()
        self._service = service
        self._games = games
        self._category_tag = category_tag

    def run(self) -> None:
        """Adds games and emits progress."""
        try:
            tag = None
            stats = self._service.batch_add_to_steam(
                self._games,
                progress_callback=self._on_progress,
                category_tag=tag,
            )
            self.finished_add.emit(stats)
        except Exception:
            logger.exception("Batch add failed")
            self.finished_add.emit({"added": 0, "skipped": 0, "errors": len(self._games)})

    def _on_progress(self, current: int, total: int, name: str) -> None:
        """Relays progress to the main thread."""
        self.progress.emit(current, total, name)


class ExternalGamesDialog(BaseDialog):
    """Dialog for scanning and importing external games into Steam.

    Provides platform scanning, game selection, and batch import
    with progress feedback.
    """

    _COL_PLATFORM = 0
    _COL_NAME = 1
    _COL_PATH = 2
    _COL_STATUS = 3

    def __init__(self, parent: QWidget | None = None) -> None:
        self._all_games: list[ExternalGame] = []
        self._existing_names: set[str] = set()
        self._service: ExternalGamesService | None = None
        self._scan_thread: _ScanThread | None = None
        self._add_thread: _AddThread | None = None

        super().__init__(
            parent=parent,
            title_key="ui.external.title",
            min_width=800,
            buttons="custom",
        )

        self._init_service()

    def _init_service(self) -> None:
        """Initializes the ExternalGamesService from config."""
        steam_path = config.STEAM_PATH
        if not steam_path:
            logger.warning("No Steam path configured")
            return

        userdata = steam_path / "userdata"
        account_id, _ = config.get_detected_user()
        if not account_id:
            logger.warning("No Steam user detected")
            return

        try:
            mgr = ShortcutsManager(userdata, account_id)
            self._service = ExternalGamesService(mgr)
        except Exception:
            logger.exception("Failed to initialize ExternalGamesService")

    def _build_content(self, layout: QVBoxLayout) -> None:
        """Builds the dialog UI.

        Args:
            layout: Main vertical layout from BaseDialog.
        """
        # Top row: Scan button + filter
        top_row = QHBoxLayout()

        self._btn_scan = QPushButton(t("ui.external.scan"))
        self._btn_scan.clicked.connect(self._on_scan)
        top_row.addWidget(self._btn_scan)

        top_row.addStretch()

        filter_label = QLabel(t("ui.external.filter_all") + ":")
        top_row.addWidget(filter_label)

        self._filter_combo = QComboBox()
        self._filter_combo.addItem(t("ui.external.filter_all"), "")
        self._filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        self._filter_combo.setMinimumWidth(160)
        self._filter_combo.setMaxVisibleItems(10)
        top_row.addWidget(self._filter_combo)

        layout.addLayout(top_row)

        # Game table
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(
            [
                t("ui.external.col_platform"),
                t("ui.external.col_name"),
                t("ui.external.col_path"),
                t("ui.external.col_status"),
            ]
        )
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)

        header = self._table.horizontalHeader()
        if header:
            header.setSectionResizeMode(self._COL_PLATFORM, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(self._COL_NAME, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(self._COL_PATH, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(self._COL_STATUS, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self._table)

        # Status label
        self._status_label = QLabel("")
        layout.addWidget(self._status_label)

        # Options row
        options_row = QHBoxLayout()

        self._chk_platform_tag = QCheckBox(t("ui.external.platform_tag"))
        self._chk_platform_tag.setChecked(True)
        options_row.addWidget(self._chk_platform_tag)

        options_row.addStretch()
        layout.addLayout(options_row)

        # Progress bar + label
        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)

        self._progress_label = QLabel("")
        self._progress_label.setVisible(False)
        layout.addWidget(self._progress_label)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._btn_add_selected = QPushButton(t("ui.external.add_selected"))
        self._btn_add_selected.clicked.connect(self._on_add_selected)
        self._btn_add_selected.setEnabled(False)
        btn_layout.addWidget(self._btn_add_selected)

        self._btn_add_all = QPushButton(t("ui.external.add_all"))
        self._btn_add_all.clicked.connect(self._on_add_all)
        self._btn_add_all.setEnabled(False)
        btn_layout.addWidget(self._btn_add_all)

        self._btn_close = QPushButton(t("common.close"))
        self._btn_close.clicked.connect(self.reject)
        btn_layout.addWidget(self._btn_close)

        layout.addLayout(btn_layout)

    # ------------------------------------------------------------------
    # Scanning
    # ------------------------------------------------------------------

    def _on_scan(self) -> None:
        """Starts platform scanning in a background thread."""
        if not self._service:
            UIHelper.show_warning(self, t("ui.external.no_games"))
            return

        self._btn_scan.setEnabled(False)
        self._status_label.setText(t("ui.external.scanning"))
        self._table.setRowCount(0)
        self._all_games.clear()

        self._existing_names = self._service.get_existing_shortcuts()

        self._scan_thread = _ScanThread(self._service)
        self._scan_thread.finished_scan.connect(self._on_scan_finished)
        self._scan_thread.start()

    def _on_scan_finished(self, results: dict[str, list[ExternalGame]]) -> None:
        """Handles scan completion.

        Args:
            results: Dict mapping platform name to list of found games.
        """
        self._btn_scan.setEnabled(True)

        # Flatten results — use actual game platforms for the filter
        # (RomParser creates per-system platforms like "Emulation (Nintendo Switch)")
        self._all_games.clear()
        for games in results.values():
            self._all_games.extend(games)
        platforms = {g.platform for g in self._all_games}

        if not self._all_games:
            self._status_label.setText(t("ui.external.no_games"))
            self._btn_add_selected.setEnabled(False)
            self._btn_add_all.setEnabled(False)
            return

        # Update filter combo — group emulation sub-platforms under one header
        self._filter_combo.blockSignals(True)
        self._filter_combo.clear()
        self._filter_combo.addItem(t("ui.external.filter_all"), "")

        emu_prefix = "Emulation ("
        emu_platforms = sorted(p for p in platforms if p.startswith(emu_prefix))
        other_platforms = sorted(p for p in platforms if not p.startswith(emu_prefix))

        if emu_platforms:
            # Group header — filters ALL emulation games
            self._filter_combo.addItem("Emulation (ROMs)", "emulation_all")
            # Sub-entries with indent
            for plat in emu_platforms:
                system = plat[len(emu_prefix) : -1]  # "Nintendo Switch"
                self._filter_combo.addItem(f"    {system}", plat)

        for plat in other_platforms:
            self._filter_combo.addItem(plat, plat)

        self._filter_combo.blockSignals(False)

        # Populate table
        self._populate_table(self._all_games)

        # Update status
        existing_count = sum(1 for g in self._all_games if g.name.lower() in self._existing_names)
        self._status_label.setText(t("ui.external.found_games", count=len(self._all_games), existing=existing_count))

        has_new = existing_count < len(self._all_games)
        self._btn_add_selected.setEnabled(has_new)
        self._btn_add_all.setEnabled(has_new)

    def _populate_table(self, games: list[ExternalGame]) -> None:
        """Fills the table with game data.

        Args:
            games: List of games to display.
        """
        self._table.setRowCount(len(games))

        for row, game in enumerate(games):
            is_existing = game.name.lower() in self._existing_names

            # Platform
            platform_item = QTableWidgetItem(game.platform)
            platform_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self._table.setItem(row, self._COL_PLATFORM, platform_item)

            # Name
            name_item = QTableWidgetItem(game.name)
            name_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self._table.setItem(row, self._COL_NAME, name_item)

            # Path
            path_text = str(game.install_path) if game.install_path else ""
            path_item = QTableWidgetItem(path_text)
            path_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self._table.setItem(row, self._COL_PATH, path_item)

            # Status (checkbox for new games, text for existing)
            if is_existing:
                status_item = QTableWidgetItem(t("ui.external.already_exists"))
                status_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self._table.setItem(row, self._COL_STATUS, status_item)
            else:
                chk_item = QTableWidgetItem()
                chk_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
                chk_item.setCheckState(Qt.CheckState.Checked)
                self._table.setItem(row, self._COL_STATUS, chk_item)

    def _get_filtered_games(self) -> list[ExternalGame]:
        """Return games matching the current platform filter.

        Returns:
            Filtered game list (all games if no filter active).
        """
        platform_filter = self._filter_combo.currentData()
        if not platform_filter:
            return self._all_games
        if platform_filter == "emulation_all":
            return [g for g in self._all_games if g.platform.startswith("Emulation (")]
        return [g for g in self._all_games if g.platform == platform_filter]

    def _on_filter_changed(self, _index: int) -> None:
        """Handles platform filter changes."""
        self._populate_table(self._get_filtered_games())

    # ------------------------------------------------------------------
    # Adding games
    # ------------------------------------------------------------------

    def _get_selected_games(self) -> list[ExternalGame]:
        """Returns list of checked games from the table.

        Returns:
            Games that are checked and not already in Steam.
        """
        selected: list[ExternalGame] = []
        visible_games = self._get_filtered_games()

        for row in range(self._table.rowCount()):
            status_item = self._table.item(row, self._COL_STATUS)
            if not status_item:
                continue
            if status_item.checkState() == Qt.CheckState.Checked:
                if row < len(visible_games):
                    selected.append(visible_games[row])

        return selected

    def _get_new_games(self) -> list[ExternalGame]:
        """Returns all games not already in Steam.

        Returns:
            Games whose names are not in existing shortcuts.
        """
        return [g for g in self._all_games if g.name.lower() not in self._existing_names]

    def _on_add_selected(self) -> None:
        """Adds checked games to Steam."""
        games = self._get_selected_games()
        if not games:
            UIHelper.show_info(
                self,
                t("ui.external.select_games_first"),
                t("ui.external.no_selection"),
            )
            return
        self._start_add(games)

    def _on_add_all(self) -> None:
        """Adds all new games to Steam."""
        games = self._get_new_games()
        if not games:
            return

        if not UIHelper.confirm(
            self,
            t("ui.external.confirm_add", count=len(games)),
            t("ui.external.title"),
        ):
            return

        self._start_add(games)

    def _start_add(self, games: list[ExternalGame]) -> None:
        """Starts the batch-add operation in a background thread.

        Args:
            games: Games to add to Steam.
        """
        if not self._service:
            return

        self._set_ui_busy(True)
        self._progress_bar.setMaximum(len(games))
        self._progress_bar.setValue(0)

        use_tag = self._chk_platform_tag.isChecked()

        # When using platform tags, add each game with its platform name
        # The _AddThread uses batch_add_to_steam which applies one tag to all.
        # For per-platform tags, we handle it differently.
        if use_tag:
            self._add_with_platform_tags(games)
        else:
            self._add_thread = _AddThread(self._service, games, False)
            self._add_thread.progress.connect(self._on_add_progress)
            self._add_thread.finished_add.connect(self._on_add_finished)
            self._add_thread.start()

    def _add_with_platform_tags(self, games: list[ExternalGame]) -> None:
        """Adds games with per-platform category tags using non-blocking batching.

        Uses QTimer.singleShot to yield to the event loop between batches,
        keeping the dialog responsive without resorting to processEvents().

        Args:
            games: Games to add.
        """
        self._progress_bar.setVisible(True)
        self._progress_label.setVisible(True)
        self._progress_bar.setMaximum(len(games))

        self._batch_stats = {"added": 0, "skipped": 0, "errors": 0}
        self._batch_games = games
        self._add_batch(0)

    def _add_batch(self, index: int) -> None:
        """Processes a batch of games and schedules the next batch.

        Args:
            index: Current index in the game list.
        """
        if index >= len(self._batch_games):
            self._on_add_finished(self._batch_stats)
            return

        batch_end = min(index + 5, len(self._batch_games))
        for i in range(index, batch_end):
            game = self._batch_games[i]
            self._progress_bar.setValue(i + 1)
            self._progress_label.setText(
                t("ui.external.adding_game", name=game.name, current=i + 1, total=len(self._batch_games))
            )
            try:
                tag = self._collection_name_for_platform(game.platform)
                if self._service and self._service.add_to_steam(game, category_tag=tag):
                    self._batch_stats["added"] += 1
                else:
                    self._batch_stats["skipped"] += 1
            except Exception:
                logger.exception("Error adding %s", game.name)
                self._batch_stats["errors"] += 1

        QTimer.singleShot(0, lambda: self._add_batch(batch_end))

    @staticmethod
    def _collection_name_for_platform(platform: str) -> str:
        """Extract clean collection name from platform string.

        Converts "Emulation (Nintendo Switch)" to "Nintendo Switch" so that
        Steam collections use clean system names instead of the wrapper format.

        Args:
            platform: Platform string from ExternalGame.

        Returns:
            Clean collection name for Steam category tag.
        """
        if platform.startswith("Emulation (") and platform.endswith(")"):
            return platform[len("Emulation (") : -1]
        return platform

    def _on_add_progress(self, current: int, total: int, name: str) -> None:
        """Updates progress UI during adding.

        Args:
            current: Current game index.
            total: Total game count.
            name: Current game name.
        """
        self._progress_bar.setValue(current)
        self._progress_label.setText(t("ui.external.adding_game", name=name, current=current, total=total))

    def _on_add_finished(self, stats: dict[str, int]) -> None:
        """Handles completion of the add operation.

        Args:
            stats: Dict with "added", "skipped", "errors" counts.
        """
        self._set_ui_busy(False)

        # Refresh existing names for accurate display
        if self._service:
            self._existing_names = self._service.get_existing_shortcuts()

        # Re-populate table to show updated status
        self._populate_table(self._get_filtered_games())

        # Update status
        existing_count = sum(1 for g in self._all_games if g.name.lower() in self._existing_names)
        self._status_label.setText(t("ui.external.found_games", count=len(self._all_games), existing=existing_count))

        # Show result
        msg = t(
            "ui.external.complete_message",
            added=stats["added"],
            skipped=stats["skipped"],
            errors=stats["errors"],
        )
        if stats["added"] > 0:
            msg += "\n\n" + t("ui.external.restart_hint")

        UIHelper.show_success(self, msg, t("ui.external.complete"))

        # Disable buttons if no new games remain
        has_new = existing_count < len(self._all_games)
        self._btn_add_selected.setEnabled(has_new)
        self._btn_add_all.setEnabled(has_new)

    def _set_ui_busy(self, busy: bool) -> None:
        """Toggles UI elements during operations.

        Args:
            busy: True to disable controls, False to re-enable.
        """
        self._btn_scan.setEnabled(not busy)
        self._btn_add_selected.setEnabled(not busy)
        self._btn_add_all.setEnabled(not busy)
        self._filter_combo.setEnabled(not busy)
        self._progress_bar.setVisible(busy)
        self._progress_label.setVisible(busy)
