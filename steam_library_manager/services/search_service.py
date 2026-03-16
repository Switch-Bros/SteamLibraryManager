#
# steam_library_manager/services/search_service.py
# Search service with regex and tag-prefix support
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from steam_library_manager.core.game import Game

logger = logging.getLogger("steamlibmgr.search_service")

__all__ = ["SearchService"]

_REGEX_PREFIX = "/"


class SearchService:
    """Service handling game search logic including regex support."""

    @staticmethod
    def filter_games(games: list[Game], query: str) -> list[Game]:
        """Filter games by text substring or regex (prefix with ``/``)."""
        if not query:
            return games

        if query.startswith(_REGEX_PREFIX) and len(query) > 1:
            return SearchService._filter_regex(games, query[1:])

        lower_query = query.lower()
        return [g for g in games if lower_query in g.name.lower()]

    @staticmethod
    def _filter_regex(games: list[Game], pattern: str) -> list[Game]:
        try:
            compiled = re.compile(pattern, re.IGNORECASE)
        except re.error as exc:
            logger.warning("Invalid regex pattern '%s': %s", pattern, exc)
            return []

        return [g for g in games if compiled.search(g.name)]

    @staticmethod
    def validate_regex(pattern: str) -> bool:
        try:
            re.compile(pattern)
            return True
        except re.error:
            return False
