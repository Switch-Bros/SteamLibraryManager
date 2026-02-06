# src/ui/handlers/selection_handler.py

"""
Handler for game selection and details loading.

Extracts the following methods from MainWindow:
  - _on_games_selected(games)           (multi-selection handler)
  - on_game_selected(game)              (single selection handler)
  - _fetch_game_details_async(app_id)   (background details loading)
  - _restore_game_selection(app_ids)    (selection restoration after refresh)

All UI updates are delegated back to MainWindow.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, List

from PyQt6.QtCore import QThread, pyqtSignal, Qt

from src.core.game_manager import Game
from src.utils.i18n import t

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow


class SelectionHandler:
    """Handles game selection events and background details loading.

    Attributes:
        mw: Back-reference to the owning MainWindow instance.
        _fetch_threads: List of active fetch threads (for cleanup).
    """

    def __init__(self, main_window: 'MainWindow') -> None:
        """Initializes the selection handler.

        Args:
            main_window: The MainWindow instance that owns this handler.
        """
        self.mw: 'MainWindow' = main_window
        self._fetch_threads: List[QThread] = []

    def on_games_selected(self, games: List[Game]) -> None:
        """Handles multi-selection changes in the game tree.

        Updates the details widget to show either a single game view,
        a multi-select view, or clears the view if no selection.

        Args:
            games: List of currently selected games.
        """
        self.mw.selected_games = games
        all_categories = list(self.mw.game_manager.get_all_categories().keys())

        if len(games) > 1:
            # Show multi-select view in details widget
            self.mw.set_status(t('ui.main_window.games_selected', count=len(games)))
            self.mw.details_widget.set_games(games, all_categories)
        elif len(games) == 1:
            # Show single game view
            self.mw.set_status(f"{games[0].name}")
            self.on_game_selected(games[0])
        else:
            # No selection - could clear the details widget
            pass

    def on_game_selected(self, game: Game) -> None:
        """Handles single game selection in the tree.

        Shows the game details immediately in the UI, then fetches
        missing metadata in the background if needed.

        Args:
            game: The selected game object.
        """
        # Ignore if multiple games are selected (multi-select mode)
        if len(self.mw.selected_games) > 1:
            return

        self.mw.selected_game = game
        all_categories = list(self.mw.game_manager.get_all_categories().keys())

        # PERFORMANCE FIX: Show UI immediately, fetch details in background
        self.mw.details_widget.set_game(game, all_categories)

        # Fetch details asynchronously if missing (non-blocking)
        if not game.developer or not game.proton_db_rating or not game.steam_deck_status:
            self._fetch_game_details_async(game.app_id, all_categories)

    def _fetch_game_details_async(self, app_id: str, all_categories: List[str]) -> None:
        """Fetches game details in a background thread without blocking the UI.

        This method improves performance by loading missing metadata asynchronously,
        allowing the UI to remain responsive during API calls.

        Args:
            app_id: The Steam app ID to fetch details for.
            all_categories: List of all available categories for UI update.
        """

        class FetchThread(QThread):
            """Background thread for fetching game details."""
            finished_signal = pyqtSignal(bool)

            def __init__(self, game_manager, target_app_id):
                super().__init__()
                self.game_manager = game_manager
                self.target_app_id = target_app_id

            def run(self):
                """Executes the fetch operation in background."""
                success = self.game_manager.fetch_game_details(self.target_app_id)
                self.finished_signal.emit(success)

        # Create and start background thread
        fetch_thread = FetchThread(self.mw.game_manager, app_id)

        def on_fetch_complete(success: bool):
            """Updates UI when fetch completes."""
            if success and self.mw.selected_game and self.mw.selected_game.app_id == app_id:
                # Only update if this game is still selected
                game = self.mw.game_manager.get_game(app_id)
                if game:
                    self.mw.details_widget.set_game(game, all_categories)

        fetch_thread.finished_signal.connect(on_fetch_complete)
        fetch_thread.start()

        # Store reference to prevent garbage collection
        self._fetch_threads.append(fetch_thread)

        # Clean up finished threads
        self._fetch_threads = [thread for thread in self._fetch_threads if thread.isRunning()]

    def restore_game_selection(self, app_ids: List[str]) -> None:
        """Restores game selection in the tree widget after refresh.

        This method finds and re-selects games in the tree widget based on their
        app IDs. It's used to maintain the selection state after operations that
        refresh the tree (like category changes).

        Args:
            app_ids: List of Steam app IDs to select.
        """
        if not app_ids:
            return

        # Temporarily block signals to prevent triggering selection events
        self.mw.tree.blockSignals(True)

        # Find and select the game items in the tree
        for i in range(self.mw.tree.topLevelItemCount()):
            category_item = self.mw.tree.topLevelItem(i)
            for j in range(category_item.childCount()):
                game_item = category_item.child(j)
                item_app_id = game_item.data(0, Qt.ItemDataRole.UserRole)
                if item_app_id and item_app_id in app_ids:
                    game_item.setSelected(True)

        # Re-enable signals
        self.mw.tree.blockSignals(False)

        # Manually update selected_games list
        self.mw.selected_games = [self.mw.game_manager.get_game(aid) for aid in app_ids]
        self.mw.selected_games = [g for g in self.mw.selected_games if g is not None]