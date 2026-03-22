#
# steam_library_manager/services/search_service.py
# Full-text game search with scoring and ranking
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#
# TODO: add fuzzy matching for typos?

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
    """Handles game search logic."""

    @staticmethod
    def filter_games(games: list[Game], query: str) -> list[Game]:
        # filter games by query string
        # supports regex if query starts with /
        if not query:
            return games

        if query.startswith(_REGEX_PREFIX) and len(query) > 1:
            return SearchService._filter_regex(games, query[1:])

        q = query.lower()
        return [g for g in games if q in g.name.lower()]

    @staticmethod
    def _filter_regex(games: list[Game], pat: str) -> list[Game]:
        # filter using regex pattern
        try:
            rx = re.compile(pat, re.IGNORECASE)
        except re.error as e:
            logger.warning("Invalid regex pattern '%s': %s" % (pat, e))
            return []

        return [g for g in games if rx.search(g.name)]

    @staticmethod
    def validate_regex(pat: str) -> bool:
        # check if regex is valid
        try:
            re.compile(pat)
            return True
        except re.error:
            return False
