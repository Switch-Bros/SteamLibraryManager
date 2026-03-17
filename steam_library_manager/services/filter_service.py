#
# steam_library_manager/services/filter_service.py
# Game library filter engine
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
from dataclasses import dataclass

from steam_library_manager.services.filter_constants import (
    ALL_ACHIEVEMENT_KEYS,
    ALL_DECK_KEYS,
    ALL_LANGUAGE_KEYS,
    ALL_PEGI_KEYS,
    ALL_PLATFORM_KEYS,
    ALL_SORT_KEYS,
    ALL_STATUS_KEYS,
    ALL_TYPE_KEYS,
    SortKey,
    TYPE_APP_TYPE_MAP,
)

logger = logging.getLogger("steamlibmgr.filter_service")

__all__ = [
    "ALL_ACHIEVEMENT_KEYS",
    "ALL_DECK_KEYS",
    "ALL_LANGUAGE_KEYS",
    "ALL_PEGI_KEYS",
    "ALL_PLATFORM_KEYS",
    "ALL_SORT_KEYS",
    "ALL_STATUS_KEYS",
    "ALL_TYPE_KEYS",
    "FilterService",
    "FilterState",
    "SortKey",
    "TYPE_APP_TYPE_MAP",
]


@dataclass(frozen=True)
class FilterState:
    # snapshot of current filters for profiles
    enabled_types: frozenset[str] = ALL_TYPE_KEYS
    enabled_platforms: frozenset[str] = ALL_PLATFORM_KEYS
    active_statuses: frozenset[str] = frozenset()
    active_languages: frozenset[str] = frozenset()
    active_deck_statuses: frozenset[str] = frozenset()
    active_achievement_filters: frozenset[str] = frozenset()
    active_pegi_ratings: frozenset[str] = frozenset()
    active_curator_ids: frozenset[int] = frozenset()
    sort_key: SortKey = SortKey.NAME


class FilterService:
    """View-menu filter state + applies filters to game lists."""

    def __init__(self):
        self._types = set(ALL_TYPE_KEYS)
        self._platforms = set(ALL_PLATFORM_KEYS)
        self._statuses = set()
        self._languages = set()
        self._deck = set()
        self._achievements = set()
        self._pegi = set()
        self._sort_key = SortKey.NAME

        # curator_id -> set of recommended app_ids
        self._curator_cache = {}
        self._cur_ids = set()

    @property
    def sort_key(self):
        return self._sort_key

    @property
    def curator_cache(self):
        return self._curator_cache

    @property
    def state(self):
        # snapshot for profile save/restore
        return FilterState(
            enabled_types=frozenset(self._types),
            enabled_platforms=frozenset(self._platforms),
            active_statuses=frozenset(self._statuses),
            active_languages=frozenset(self._languages),
            active_deck_statuses=frozenset(self._deck),
            active_achievement_filters=frozenset(self._achievements),
            active_pegi_ratings=frozenset(self._pegi),
            active_curator_ids=frozenset(self._cur_ids),
            sort_key=self._sort_key,
        )

    def restore_state(self, st):
        self._types = set(st.enabled_types)
        self._platforms = set(st.enabled_platforms)
        self._statuses = set(st.active_statuses)
        self._languages = set(st.active_languages)
        self._deck = set(st.active_deck_statuses)
        self._achievements = set(st.active_achievement_filters)
        self._pegi = set(st.active_pegi_ratings)
        self._cur_ids = set(st.active_curator_ids)
        self._sort_key = st.sort_key

    def set_sort_key(self, key):
        try:
            self._sort_key = SortKey(key)
        except ValueError:
            logger.warning("unknown sort key: %s, using NAME", key)
            self._sort_key = SortKey.NAME

    def sort_games(self, games):
        if self._sort_key == SortKey.PLAYTIME:
            return sorted(games, key=lambda g: g.playtime_minutes, reverse=True)
        if self._sort_key == SortKey.LAST_PLAYED:
            return sorted(games, key=lambda g: (g.last_played is not None, g.last_played or ""), reverse=True)
        if self._sort_key == SortKey.RELEASE_DATE:
            return sorted(games, key=lambda g: g.release_year if g.release_year else 0, reverse=True)
        # default: name A-Z
        return sorted(games, key=lambda g: g.sort_name.lower())

    # toggle methods called from view menu checkboxes

    def _toggle(self, key, on, valid, target, lbl):
        if key not in valid:
            logger.warning("unknown %s key: %s", lbl, key)
            return
        target.add(key) if on else target.discard(key)

    def toggle_type(self, key, on):
        self._toggle(key, on, ALL_TYPE_KEYS, self._types, "type")

    def toggle_platform(self, key, on):
        self._toggle(key, on, ALL_PLATFORM_KEYS, self._platforms, "platform")

    def toggle_status(self, key, on):
        self._toggle(key, on, ALL_STATUS_KEYS, self._statuses, "status")

    def toggle_language(self, key, on):
        self._toggle(key, on, ALL_LANGUAGE_KEYS, self._languages, "lang")

    def toggle_deck_status(self, key, on):
        self._toggle(key, on, ALL_DECK_KEYS, self._deck, "deck")

    def toggle_pegi_rating(self, key, on):
        self._toggle(key, on, ALL_PEGI_KEYS, self._pegi, "pegi")

    def toggle_achievement_filter(self, key, on):
        self._toggle(key, on, ALL_ACHIEVEMENT_KEYS, self._achievements, "achv")

    def set_curator_cache(self, cache):
        self._curator_cache = cache

    def toggle_curator_filter(self, cur_id, on):
        if cur_id not in self._curator_cache:
            logger.warning("unknown curator id: %d", cur_id)
            return
        self._cur_ids.add(cur_id) if on else self._cur_ids.discard(cur_id)

    def is_type_category_visible(self, type_key):
        return type_key in self._types

    def has_active_filters(self):
        # true if anything deviates from defaults
        return bool(
            self._types != ALL_TYPE_KEYS
            or self._platforms != ALL_PLATFORM_KEYS
            or self._statuses
            or self._languages
            or self._deck
            or self._achievements
            or self._pegi
            or self._cur_ids
        )

    # main filter logic

    def apply(self, games):
        # run all active filters
        if not self.has_active_filters():
            return games

        out = []
        for g in games:
            if not self._chk_type(g):
                continue
            if not self._chk_platform(g):
                continue
            if not self._chk_status(g):
                continue
            if not self._chk_lang(g):
                continue
            if not self._chk_deck(g):
                continue
            if not self._chk_achv(g):
                continue
            if not self._chk_pegi(g):
                continue
            if not self._chk_curator(g):
                continue
            out.append(g)
        return out

    def _chk_type(self, game):
        if self._types == ALL_TYPE_KEYS:
            return True
        app_type = game.app_type.lower() if game.app_type else ""
        for tk in self._types:
            if app_type in TYPE_APP_TYPE_MAP.get(tk, frozenset()):
                return True
        return False

    def _chk_platform(self, game):
        if self._platforms == ALL_PLATFORM_KEYS:
            return True
        if not game.platforms:
            return True
        plats = {p.lower() for p in game.platforms}
        for pk in self._platforms:
            if pk in plats:
                return True
        return False

    def _chk_status(self, game):
        if not self._statuses:
            return True
        for s in self._statuses:
            if s == "installed" and game.installed:
                return True
            if s == "not_installed" and not game.installed:
                return True
            if s == "hidden" and game.hidden:
                return True
            if s == "with_playtime" and game.playtime_minutes > 0:
                return True
            if s == "favorites" and game.is_favorite():
                return True
        return False

    def _chk_lang(self, game):
        if not self._languages:
            return True
        if not game.languages:
            return True
        langs = {lg.lower().replace(" ", "_") for lg in game.languages}
        return bool(langs & self._languages)

    def _chk_deck(self, game):
        if not self._deck:
            return True
        status = game.steam_deck_status.lower() if game.steam_deck_status else "unknown"
        return status in self._deck

    def _chk_achv(self, game):
        if not self._achievements:
            return True
        pct = game.achievement_percentage
        total = game.achievement_total
        for k in self._achievements:
            if k == "perfect" and game.achievement_perfect:
                return True
            if k == "almost" and 75 <= pct < 100:
                return True
            if k == "progress" and 25 <= pct < 75:
                return True
            if k == "started" and 0 < pct < 25:
                return True
            if k == "none" and total == 0:
                return True
        return False

    def _chk_pegi(self, game):
        if not self._pegi:
            return True
        pegi_map = {"pegi_3": "3", "pegi_7": "7", "pegi_12": "12", "pegi_16": "16", "pegi_18": "18"}
        rating = game.pegi_rating or ""
        if not rating:
            return "pegi_none" in self._pegi
        allowed = {pegi_map[k] for k in self._pegi if k in pegi_map}
        return rating in allowed

    def _chk_curator(self, game):
        if not self._cur_ids:
            return True
        try:
            num_id = int(game.app_id)
        except (ValueError, TypeError):
            return False
        for cid in self._cur_ids:
            if num_id in self._curator_cache.get(cid, set()):
                return True
        return False
