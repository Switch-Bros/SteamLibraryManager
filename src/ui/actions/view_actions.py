from __future__ import annotations

from typing import TYPE_CHECKING
from src.utils.i18n import t

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow


class ViewActions:
    """Handles actions related to the view, like searching and tree expansion."""

    def __init__(self, main_window: "MainWindow"):
        self.main_window = main_window

    def expand_all(self):
        """Expands all categories in the game tree."""
        if self.main_window.tree:
            self.main_window.tree.expandAll()

    def collapse_all(self):
        """Collapses all categories in the game tree."""
        if self.main_window.tree:
            self.main_window.tree.collapseAll()

    def on_search(self, query: str):
        """Filters the game tree based on search query using SearchService.

        Args:
            query: The search string.
        """
        self.main_window.current_search_query = query

        if not query:
            self.main_window.populate_categories()
            return

        if not self.main_window.game_manager or not self.main_window.search_service:
            return

        # Use the Service for logic
        all_games = self.main_window.game_manager.get_real_games()
        results = self.main_window.search_service.filter_games(all_games, query)

        if results:
            cat_name = t("ui.search.results_category", count=len(results))
            # Sort for display
            sorted_results = sorted(results, key=lambda g: g.name.lower())

            self.main_window.tree.populate_categories({cat_name: sorted_results})
            self.main_window.tree.expandAll()
            self.main_window.set_status(t("ui.search.status_found", count=len(results)))
        else:
            self.main_window.tree.clear()
            self.main_window.set_status(t("ui.search.status_none"))

    def clear_search(self):
        """Clears the search field and restores the full category view."""
        self.main_window.current_search_query = ""
        if self.main_window.search_entry:
            self.main_window.search_entry.clear()
        self.main_window.populate_categories()
