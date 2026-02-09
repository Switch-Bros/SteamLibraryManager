# src/ui/handlers/category_change_handler.py

"""
Handler for category change operations (toggle, drag/drop).

Extracts the following methods from MainWindow:
  - _apply_category_to_games(games, category, checked)
  - _on_category_changed_from_details(app_id, category, checked)
  - _on_games_dropped(games, target_category)

All persistence and UI updates are delegated back to MainWindow.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, List

from PyQt6.QtCore import QTimer

from src.core.game_manager import Game
from src.ui.handlers.empty_collection_handler import EmptyCollectionHandler

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow


class CategoryChangeHandler:
    """Handles category assignment changes from UI events.

    Supports category changes from:
    - Details widget checkboxes (single and multi-select)
    - Drag-and-drop operations

    Attributes:
        mw: Back-reference to the owning MainWindow instance.
    """

    def __init__(self, main_window: 'MainWindow') -> None:
        """Initializes the category change handler.

        Args:
            main_window: The MainWindow instance that owns this handler.
        """
        self.mw: 'MainWindow' = main_window
        self.empty_handler = EmptyCollectionHandler(main_window)

    def apply_category_to_games(self, games: List[Game], category: str, checked: bool) -> None:
        """Helper method to apply category changes to a list of games.

        Updates both the game objects and the parsers via category_service.

        Args:
            games: List of games to update.
            category: The category name.
            checked: Whether to add (True) or remove (False) the category.
        """
        if not self.mw.category_service:
            return

        for game in games:
            if checked:
                if category not in game.categories:
                    game.categories.append(category)
                    self.mw.category_service.add_app_to_category(game.app_id, category)
            else:
                if category in game.categories:
                    game.categories.remove(category)
                    self.mw.category_service.remove_app_from_category(game.app_id, category)

                    self.empty_handler.check_and_delete_if_empty(category)

    def on_category_changed_from_details(self, app_id: str, category: str, checked: bool) -> None:
        """Handles category toggle events from the details widget.

        Supports both single and multi-selection. If multiple games are selected,
        the category change is applied to all selected games.

        Includes batching logic to prevent multiple UI refreshes during rapid
        checkbox events.

        Args:
            app_id: The Steam app ID of the game (ignored for multi-select).
            category: The category name being toggled.
            checked: Whether the category should be added or removed.
        """
        if not self.mw.cloud_storage_parser:
            return

        # Prevent multiple refreshes during rapid checkbox events
        if hasattr(self.mw, 'in_batch_update') and self.mw.in_batch_update:
            # Just update data, skip UI refresh
            games_to_update = []
            if len(self.mw.selected_games) > 1:
                games_to_update = self.mw.selected_games
            else:
                game = self.mw.game_manager.get_game(app_id)
                if game:
                    games_to_update = [game]

            self.apply_category_to_games(games_to_update, category, checked)
            return

        # Set batch flag
        self.mw.in_batch_update = True

        # Determine which games to update
        games_to_update = []
        if len(self.mw.selected_games) > 1:
            # Multi-select mode: update all selected games
            games_to_update = self.mw.selected_games
        else:
            # Single game mode
            game = self.mw.game_manager.get_game(app_id)
            if game:
                games_to_update = [game]

        if not games_to_update:
            return

        # Apply category change to all games
        self.apply_category_to_games(games_to_update, category, checked)

        # Schedule save (batched with 100ms delay)
        # noinspection PyProtectedMember
        self.mw._schedule_save()

        # Save the current selection before refreshing
        selected_app_ids = [game.app_id for game in self.mw.selected_games]

        # If search is active, re-run the search instead of showing all categories
        if self.mw.current_search_query:
            self.mw.view_actions.on_search(self.mw.current_search_query)
        else:
            self.mw.populate_categories()

        # Restore the selection
        if selected_app_ids:
            self.mw.selection_handler.restore_game_selection(selected_app_ids)

        all_categories = list(self.mw.game_manager.get_all_categories().keys())

        # Refresh details widget
        if len(self.mw.selected_games) > 1:
            # Multi-select: refresh the multi-select view
            self.mw.details_widget.set_games(self.mw.selected_games, all_categories)
        elif len(self.mw.selected_games) == 1:
            # Single select: refresh single game view
            self.mw.details_widget.set_game(self.mw.selected_games[0], all_categories)

        # Reset batch flag after 500ms to allow next batch
        QTimer.singleShot(500, lambda: setattr(self.mw, 'in_batch_update', False))

    def on_games_dropped(self, games: List[Game], target_category: str) -> None:
        """Handles drag-and-drop of games onto a category.

        Updates the game categories in memory and persists changes.
        Refreshes the UI while maintaining active search if present.

        Args:
            games: List of games that were dropped.
            target_category: The category they were dropped onto.
        """
        if not self.mw.cloud_storage_parser or not self.mw.category_service:
            return

        for game in games:
            # Add to target category if not already there
            if target_category not in game.categories:
                game.categories.append(target_category)
                self.mw.category_service.add_app_to_category(game.app_id, target_category)

        # Save changes
        self.mw.save_collections()

        # Refresh the tree - maintain search if active
        if self.mw.current_search_query:
            self.mw.view_actions.on_search(self.mw.current_search_query)
        else:
            self.mw.populate_categories()

        # Update details widget if one of the dropped games is currently selected
        if games and self.mw.details_widget.current_game:
            dropped_app_ids = [g.app_id for g in games]
            if self.mw.details_widget.current_game.app_id in dropped_app_ids:
                all_categories = list(self.mw.game_manager.get_all_categories().keys())
                self.mw.details_widget.set_game(self.mw.details_widget.current_game, all_categories)