#
# steam_library_manager/ui/handlers/selection_handler.py
# Handler for game selection and background details loading.
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QThread, pyqtSignal, Qt

from steam_library_manager.core.game_manager import Game
from steam_library_manager.utils.i18n import t

if TYPE_CHECKING:
    from steam_library_manager.ui.main_window import MainWindow

__all__ = ["SelectionHandler"]


class SelectionHandler:
    """Handles game selection events and background details loading.

    Only one fetch thread runs at a time. A new selection marks the
    old thread as stale so its result is silently discarded.
    """

    def __init__(self, main_window: "MainWindow") -> None:
        self.mw: "MainWindow" = main_window
        self._current_fetch: QThread | None = None

    def on_games_selected(self, games: list[Game]) -> None:
        """Handles multi-selection changes in the game tree."""
        self.mw.selected_games = games
        all_categories = list(self.mw.game_manager.get_all_categories().keys())

        if len(games) > 1:
            self.mw.set_status(t("ui.main_window.games_selected", count=len(games)))
            self.mw.details_widget.set_games(games, all_categories)
        elif len(games) == 1:
            self.mw.set_status(f"{games[0].name}")
            self.on_game_selected(games[0])

    def on_game_selected(self, game: Game) -> None:
        """Handles single game selection in the tree."""
        if len(self.mw.selected_games) > 1:
            return

        self.mw.selected_game = game
        all_categories = list(self.mw.game_manager.get_all_categories().keys())

        self._update_curator_overlap(game)
        self.mw.details_widget.set_game(game, all_categories)

        if self.mw.game_manager.detail_service.needs_enrichment(game.app_id):
            self.fetch_game_details_async(game.app_id, all_categories)

    def fetch_game_details_async(self, app_id: str, all_categories: list[str]) -> None:
        """Fetches game details in a background thread."""

        class FetchThread(QThread):

            finished_signal = pyqtSignal(bool)

            def __init__(self, game_manager, target_app_id):
                super().__init__()
                self.game_manager = game_manager
                self.target_app_id = target_app_id
                self.stale = False

            def run(self):
                success = self.game_manager.fetch_game_details(self.target_app_id)
                if not self.stale:
                    self.finished_signal.emit(success)

        if self._current_fetch is not None and self._current_fetch.isRunning():
            self._current_fetch.stale = True  # type: ignore[attr-defined]

        fetch_thread = FetchThread(self.mw.game_manager, app_id)

        def on_fetch_complete(success: bool):
            if success and self.mw.selected_game and self.mw.selected_game.app_id == app_id:
                game = self.mw.game_manager.get_game(app_id)
                if game:
                    self.mw.details_widget.set_game(game, all_categories)

        fetch_thread.finished_signal.connect(on_fetch_complete)
        self._current_fetch = fetch_thread
        fetch_thread.start()

        self._current_fetch = fetch_thread

    def restore_game_selection(self, app_ids: list[str]) -> None:
        """Re-selects games in the tree by app ID after a refresh."""
        if not app_ids:
            return

        self.mw.tree.blockSignals(True)

        for i in range(self.mw.tree.topLevelItemCount()):
            category_item = self.mw.tree.topLevelItem(i)
            for j in range(category_item.childCount()):
                game_item = category_item.child(j)
                item_app_id = game_item.data(0, Qt.ItemDataRole.UserRole)
                if item_app_id and item_app_id in app_ids:
                    game_item.setSelected(True)

        self.mw.tree.blockSignals(False)
        self.mw.selected_games = [self.mw.game_manager.get_game(aid) for aid in app_ids]
        self.mw.selected_games = [g for g in self.mw.selected_games if g is not None]

    def _update_curator_overlap(self, game: Game) -> None:
        try:
            fs = self.mw.filter_service
            cache = fs.curator_cache
            if not cache:
                game.curator_overlap = ""
                return
            numeric_id = int(game.app_id)
            recommending = sum(1 for recs in cache.values() if numeric_id in recs)
            total = len(cache)
            game.curator_overlap = f"{recommending}/{total}"
        except (ValueError, TypeError, AttributeError):
            game.curator_overlap = ""
