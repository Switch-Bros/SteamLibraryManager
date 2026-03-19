#
# steam_library_manager/services/enrichment/achievement_enrichment_service.py
# Achievement data fetcher and storer
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
import time

from steam_library_manager.services.enrichment.base_enrichment_thread import BaseEnrichmentThread
from steam_library_manager.utils.i18n import t

logger = logging.getLogger("steamlibmgr.achievement_enrichment")

__all__ = ["AchievementEnrichmentThread"]


class AchievementEnrichmentThread(BaseEnrichmentThread):
    """Fetches Steam achievement data in background."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._games = []
        self._db_path = None
        self._api_key = ""
        self._steam_id = ""
        self._db = None
        self._api = None

    def configure(self, games, db_path, api_key, steam_id, force_refresh=False):
        # setup before run
        self._games = games
        self._db_path = db_path
        self._api_key = api_key
        self._steam_id = steam_id
        self._force_refresh = force_refresh

    def _setup(self):
        from steam_library_manager.core.database import Database
        from steam_library_manager.integrations.steam_web_api import SteamWebAPI

        if not self._db_path or not self._api_key or not self._steam_id:
            raise ValueError("missing config")

        self._db = Database(self._db_path)
        self._api = SteamWebAPI(self._api_key)

    def _cleanup(self):
        if self._db:
            try:
                self._db.commit()
            except Exception as e:
                logger.warning("commit failed: %s" % e)
            self._db.close()
            self._db = None

    def _get_items(self):
        return self._games

    def _process_item(self, item):
        aid, _ = item
        return self._enrich(aid)

    def _format_progress(self, item, current, total):
        _, name = item
        return t("ui.enrichment.progress", name=name[:30], current=current, total=total)

    def _rate_limit(self):
        time.sleep(1.0)

    def _enrich(self, aid):
        # get schema + progress + rarity
        sch = self._api.get_game_schema(aid)
        achs = (sch or {}).get("achievements", [])

        if not achs:
            # no achievements
            self._db.upsert_achievement_stats(aid, 0, 0, 0.0, False)
            self._db.commit()
            return True

        tot = len(achs)

        # player progress
        pl = self._api.get_player_achievements(aid, self._steam_id)
        pmap = {}
        if pl:
            for a in pl:
                pmap[a.get("apiname", "")] = a

        # global rarity
        gpct = self._api.get_global_achievement_percentages(aid)

        # merge
        recs = []
        ul = 0  # unlocked count

        for sa in achs:
            aname = sa.get("name", "")
            dname = sa.get("displayName", aname)
            desc = sa.get("description", "")
            hid = bool(sa.get("hidden", 0))

            pa = pmap.get(aname, {})
            got = bool(pa.get("achieved", 0))
            ut = pa.get("unlocktime", 0) or 0

            if got:
                ul += 1

            rare = gpct.get(aname, 0.0)

            recs.append(
                {
                    "achievement_id": aname,
                    "name": dname,
                    "description": desc,
                    "is_unlocked": got,
                    "unlock_time": ut,
                    "is_hidden": hid,
                    "rarity_percentage": rare,
                }
            )

        pct = (ul / tot * 100) if tot > 0 else 0.0
        perf = ul == tot and tot > 0

        self._db.upsert_achievements(aid, recs)
        self._db.upsert_achievement_stats(aid, tot, ul, pct, perf)
        self._db.commit()

        return True
