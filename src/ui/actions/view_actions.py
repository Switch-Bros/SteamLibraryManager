from __future__ import annotations

from typing import TYPE_CHECKING

from src.utils.i18n import t

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow


class ViewActions:
    """Handles actions related to the view, like searching, tree expansion, and filters."""

    def __init__(self, main_window: "MainWindow"):
        self.main_window = main_window

    def on_sort_changed(self, key: str) -> None:
        """Handles sort key change from the View menu.

        Updates the FilterService sort key and refreshes the view.

        Args:
            key: The sort key string ("name", "playtime", "last_played", "release_date").
        """
        self.main_window.filter_service.set_sort_key(key)

        if self.main_window.current_search_query:
            self.on_search(self.main_window.current_search_query)
        else:
            self.main_window.populate_categories()

    def on_filter_toggled(self, group: str, key: str, checked: bool) -> None:
        """Handles View menu filter checkbox toggle.

        Dispatches to the appropriate FilterService toggle method
        based on the filter group, then refreshes the view.

        Args:
            group: The filter group ("type", "platform", or "status").
            key: The specific filter key within the group.
            checked: Whether the checkbox is now checked.
        """
        fs = self.main_window.filter_service
        if group == "type":
            fs.toggle_type(key, checked)
        elif group == "platform":
            fs.toggle_platform(key, checked)
        elif group == "status":
            fs.toggle_status(key, checked)
        elif group == "language":
            fs.toggle_language(key, checked)
        elif group == "deck_status":
            fs.toggle_deck_status(key, checked)
        elif group == "achievement":
            fs.toggle_achievement_filter(key, checked)

        # Re-run search if active, otherwise repopulate full tree
        if self.main_window.current_search_query:
            self.on_search(self.main_window.current_search_query)
        else:
            self.main_window.populate_categories()

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

        # Easter egg: "switchbros" triggers community tribute
        if query.strip().lower() == "switchbros":
            from src.utils.enigma import load_easter_egg

            egg = load_easter_egg("searchbar")
            if egg:
                from src.ui.helpers.ui_helper import UIHelper

                UIHelper.show_info(
                    self.main_window,
                    egg.get("message", ""),
                    title=egg.get("title", ""),
                )
            return

        if not self.main_window.game_manager or not self.main_window.search_service:
            return

        # Apply view filters first, then search within the filtered set
        all_games = self.main_window.game_manager.get_real_games()
        filtered_games = self.main_window.filter_service.apply(all_games)
        results = self.main_window.search_service.filter_games(filtered_games, query)

        if results:
            cat_name = t("ui.search.results_category", count=len(results))
            # Sort for display using current sort key
            sorted_results = self.main_window.filter_service.sort_games(results)

            self.main_window.tree.populate_categories({cat_name: sorted_results})
            self.main_window.tree.expandAll()
            self.main_window.set_status(t("ui.search.status_found", count=len(results)))
        else:
            self.main_window.tree.clear()
            self.main_window.set_status(t("ui.search.status_none"))

    def show_statistics(self) -> None:
        """Opens the statistics dialog."""
        from src.ui.dialogs.statistics_dialog import StatisticsDialog

        dialog = StatisticsDialog(self.main_window)
        dialog.exec()

    def clear_search(self):
        """Clears the search field and restores the full category view."""
        self.main_window.current_search_query = ""
        if self.main_window.search_entry:
            self.main_window.search_entry.clear()
        self.main_window.populate_categories()
