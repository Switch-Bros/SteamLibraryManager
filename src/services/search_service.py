from __future__ import annotations

import re
from src.core.game_manager import Game

__all__ = ['SearchService']

class SearchService:
    """Service handling complex game search logic including Regex support."""

    @staticmethod
    def filter_games(games: list[Game], query: str) -> list[Game]:
        """Filters a list of games based on a search query.

        Supports standard text search (case-insensitive).
        Future implementation can include regex support.

        Args:
            games: List of Game objects to filter.
            query: The search string.

        Returns:
            list[Game]: The filtered list of games.
        """
        if not query:
            return games

        # Simple case-insensitive substring search
        # This can be expanded later to support Regex or Tags (e.g. "tag:RPG")
        return [
            g for g in games
            if query.lower() in g.name.lower()
        ]

    @staticmethod
    def validate_regex(pattern: str) -> bool:
        """Checks if a regex pattern is valid.

        Args:
            pattern: The regex pattern string to check.

        Returns:
            bool: True if valid regex, False otherwise.
        """
        try:
            re.compile(pattern)
            return True
        except re.error:
            return False