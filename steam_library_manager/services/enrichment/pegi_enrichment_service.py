#
# steam_library_manager/services/enrichment/pegi_enrichment_service.py
# PEGI age rating enrichment from Steam store data
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging

from steam_library_manager.services.enrichment.base_enrichment_thread import BaseEnrichmentThread
from steam_library_manager.utils.i18n import t

logger = logging.getLogger("steamlibmgr.enrichment.pegi")

__all__ = ["PEGIEnrichmentThread"]


class PEGIEnrichmentThread(BaseEnrichmentThread):
    """Fills in missing PEGI ratings from the Steam store.

    Runs as gap filler after the batch Steam API (which gets most ratings).
    Uses SteamStoreScraper to fetch individual store pages for the rest.
    """

    def __init__(self, p=None):
        super().__init__(p)
        self._games = []
        self._db_path = None
        self._force_refresh = False
        self._language = "en"
        self._db = None
        self._scraper = None

    def configure(self, games, db_path, language="en", force_refresh=False):
        self._games = games
        self._db_path = db_path
        self._language = language
        self._force_refresh = force_refresh

    def _setup(self):
        from steam_library_manager.core.database import Database
        from steam_library_manager.integrations.steam_store import SteamStoreScraper

        self._db = Database(self._db_path)
        cd = self._db_path.parent / "cache"
        cd.mkdir(parents=True, exist_ok=True)
        self._scraper = SteamStoreScraper(cd, self._language)

    def _cleanup(self):
        if self._db:
            self._db.close()
            self._db = None

    def _get_items(self):
        return self._games

    def _process_item(self, it):
        aid, nm = it

        # skip if already has rating
        if not self._force_refresh:
            cur = self._db.conn.execute("SELECT pegi_rating FROM games WHERE app_id = ? AND pegi_rating != ''", (aid,))
            if cur.fetchone():
                return True

        if self._force_refresh:
            cf = self._scraper.cache_dir.parent / "age_ratings" / ("%d.json" % aid)
            if cf.exists():
                cf.unlink(missing_ok=True)

        rt = self._scraper.fetch_age_rating(str(aid))

        if rt:
            self._db.conn.execute("UPDATE games SET pegi_rating = ? WHERE app_id = ?", (rt, aid))
            self._db.conn.commit()
            return True

        return False

    def _format_progress(self, it, cur, tot):
        _aid, nm = it
        return t("ui.enrichment.progress", name=nm, current=cur, total=tot)

    def _rate_limit(self):
        pass  # scraper handles it
