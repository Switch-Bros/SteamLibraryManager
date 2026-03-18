#
# steam_library_manager/services/game_query_service.py
# Query interface for games
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging

from steam_library_manager.core.game import is_real_game
from steam_library_manager.utils.i18n import t

logger = logging.getLogger("steamlibmgr.game_query")

__all__ = ["GameQueryService"]


class GameQueryService:
    """Query facade."""

    def __init__(self, gs, filter_non_games):
        self._g = gs
        self._f = filter_non_games

    def get_real_games(self):
        if not self._f:
            return list(self._g.values())
        res = []
        for x in self._g.values():
            if is_real_game(x):
                res.append(x)
        return res

    def get_all_games(self):
        tmp = self._g.values()
        return list(tmp)

    def get_games_by_category(self, c):
        all_g = self.get_real_games()
        gs = []
        for x in all_g:
            if x.has_category(c):
                gs.append(x)

        gs.sort(key=lambda g: g.sort_name.lower())
        return gs

    def get_uncategorized_games(self, smart=None):
        # FIXME: hardcoded
        sk = {
            "favorite",
            "hidden",
            "Favorites",
            "Favoriten",
            "Hidden",
            "Versteckt",
            t("categories.favorites"),
            t("categories.hidden"),
        }
        if smart:
            sk = sk | smart
        res = []
        vals = self._g.values()
        for x in vals:
            at = x.app_type
            if at and at.lower() != "game":
                continue
            if not is_real_game(x):
                continue
            # filter cats old style
            rl = []
            cats = x.categories
            for k in cats:
                if k not in sk:
                    rl.append(k)
            if len(rl) == 0:
                res.append(x)

        res.sort(key=lambda g: g.sort_name.lower())
        return res

    def get_favorites(self):
        rl = self.get_real_games()
        gs = []
        for x in rl:
            if x.is_favorite():
                gs.append(x)

        gs.sort(key=lambda g: g.sort_name.lower())
        return gs

    def get_all_categories(self):
        ct = {}
        rl = self.get_real_games()
        for x in rl:
            cats = x.categories
            for k in cats:
                ct[k] = ct.get(k, 0) + 1
        return ct

    def get_game_statistics(self):
        # stats
        rl = self.get_real_games()
        ic = set()
        for x in rl:
            if x.categories:
                ic.add(x.app_id)
        nc = len(self.get_all_categories())
        return {
            "total_games": len(rl),
            "games_in_categories": len(ic),
            "category_count": nc,
            "uncategorized_games": len(rl) - len(ic),
        }
