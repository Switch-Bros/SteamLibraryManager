# src/services/search_service.py

"""Search service with regex and tag-prefix support.

Provides game filtering by text search (case-insensitive substring),
regex patterns (prefixed with ``/``), and future tag-based queries.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.game import Game

logger = logging.getLogger("steamlibmgr.search_service")

__all__ = ["SearchService"]

_REGEX_PREFIX = "/"


class SearchService:
    """Service handling game search logic including regex support."""

    @staticmethod
    def filter_games(games: list[Game], query: str) -> list[Game]:
        """Filters a list of games based on a search query.

        Supports three modes:
        - Empty query: returns all games.
        - Regex mode: query starts with ``/`` (e.g. ``/^Half.*``).
        - Plain text: case-insensitive substring match on name.

        Args:
            games: List of Game objects to filter.
            query: The search string.

        Returns:
            The filtered list of games.
        """
        if not query:
            return games

        if query.startswith(_REGEX_PREFIX) and len(query) > 1:
            return SearchService._filter_regex(games, query[1:])

        lower_query = query.lower()
        return [g for g in games if lower_query in g.name.lower()]

    @staticmethod
    def _filter_regex(games: list[Game], pattern: str) -> list[Game]:
        """Filters games using a regex pattern against the game name.

        Invalid regex patterns fall back to empty results with a warning.

        Args:
            games: Games to filter.
            pattern: Regex pattern string (without leading ``/``).

        Returns:
            Games whose name matches the pattern.
        """
        try:
            compiled = re.compile(pattern, re.IGNORECASE)
        except re.error as exc:
            logger.warning("Invalid regex pattern '%s': %s", pattern, exc)
            return []

        return [g for g in games if compiled.search(g.name)]

    @staticmethod
    def validate_regex(pattern: str) -> bool:
        """Checks if a regex pattern is valid.

        Args:
            pattern: The regex pattern string to check.

        Returns:
            True if valid regex, False otherwise.
        """
        try:
            re.compile(pattern)
            return True
        except re.error:
            return False
