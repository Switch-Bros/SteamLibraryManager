# src/services/game_query_service.py

"""Read-only query service for game data.

Provides filtering, grouping, and statistical queries over the shared
game dictionary without mutating any data.  Extracted from GameManager
to keep that class focused on loading and enrichment.
"""

from __future__ import annotations

import logging

from src.core.game import Game, is_real_game
from src.utils.i18n import t

logger = logging.getLogger("steamlibmgr.game_query")

__all__ = ["GameQueryService"]


class GameQueryService:
    """Stateless query facade over the shared ``games`` dictionary.

    All methods are pure reads — they never modify the underlying data.
    The ``games`` dict is shared *by reference* with ``GameManager`` so
    queries always reflect the latest state.

    Attributes:
        _games: Shared reference to ``GameManager.games``.
        _filter_non_games: Whether to exclude non-game apps (Proton, etc.).
    """

    def __init__(self, games: dict[str, Game], filter_non_games: bool) -> None:
        """Initializes the GameQueryService.

        Args:
            games: Shared reference to the game dictionary (not a copy).
            filter_non_games: When True, ``get_real_games`` filters tools/runtimes.
        """
        self._games = games
        self._filter_non_games = filter_non_games

    # ------------------------------------------------------------------
    # Core queries
    # ------------------------------------------------------------------

    def get_real_games(self) -> list[Game]:
        """Returns only real games (excludes Proton/Steam runtime tools).

        On Linux, Proton and Steam Runtime are automatically filtered.
        On Windows, all games are returned.

        Returns:
            List of real games.
        """
        if self._filter_non_games:
            return [g for g in self._games.values() if is_real_game(g)]
        return list(self._games.values())

    def get_all_games(self) -> list[Game]:
        """Returns ALL games (including tools).

        This method always returns all games, regardless of the filter.
        For most purposes, use ``get_real_games()`` instead.

        Returns:
            List of all games.
        """
        return list(self._games.values())

    def get_games_by_category(self, category: str) -> list[Game]:
        """Gets all games belonging to a specific category.

        Args:
            category: The category name.

        Returns:
            A sorted list of games in this category.
        """
        games = [g for g in self.get_real_games() if g.has_category(category)]
        return sorted(games, key=lambda g: g.sort_name.lower())

    def get_uncategorized_games(self) -> list[Game]:
        """Gets games that have no user collections (system categories don't count).

        Only actual games (``app_type == "game"`` or unknown) are considered.
        Non-game visible types (music, tool, application, video) are already
        served by their own type categories and are therefore NOT uncategorized.

        Returns:
            A sorted list of uncategorized games.
        """
        system_categories = {
            t("categories.favorites"),
            t("categories.hidden"),
        }

        uncategorized = []
        for game in self._games.values():
            # Non-game types have their own type categories
            if game.app_type and game.app_type.lower() != "game":
                continue

            # Filter ghost entries and non-games
            if not is_real_game(game):
                continue

            # Filter out system categories
            user_categories = [cat for cat in game.categories if cat not in system_categories]

            if not user_categories:
                uncategorized.append(game)

        return sorted(uncategorized, key=lambda g: g.sort_name.lower())

    def get_favorites(self) -> list[Game]:
        """Gets all favorite games.

        Returns:
            A sorted list of favorite games.
        """
        games = [g for g in self.get_real_games() if g.is_favorite()]
        return sorted(games, key=lambda g: g.sort_name.lower())

    def get_all_categories(self) -> dict[str, int]:
        """Gets all categories and their game counts.

        Returns:
            A dictionary mapping category names to game counts.
        """
        categories: dict[str, int] = {}
        for game in self.get_real_games():
            for category in game.categories:
                categories[category] = categories.get(category, 0) + 1
        return categories

    def get_game_statistics(self) -> dict[str, int]:
        """Returns game statistics for the status bar.

        Returns:
            Dict containing total_games, games_in_categories,
            category_count, and uncategorized_games.
        """
        real_games = self.get_real_games()

        games_in_categories: set[str] = set()
        for game in real_games:
            if game.categories:
                games_in_categories.add(game.app_id)

        all_categories = self.get_all_categories()
        category_count = len(all_categories)
        uncategorized = len(real_games) - len(games_in_categories)

        return {
            "total_games": len(real_games),
            "games_in_categories": len(games_in_categories),
            "category_count": category_count,
            "uncategorized_games": uncategorized,
        }
