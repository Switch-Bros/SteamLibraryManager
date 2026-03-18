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
        self._g = []
        self._dbp = None
        self._f = False
        self._l = "en"
        self._db = None
        self._s = None

    def configure(self, g, dbp, lang="en", fr=False):
        self._g = g
        self._dbp = dbp
        self._l = lang
        self._f = fr

    def _setup(self):
        from steam_library_manager.core.database import Database
        from steam_library_manager.integrations.steam_store import SteamStoreScraper

        self._db = Database(self._dbp)
        cd = self._dbp.parent / "cache"
        cd.mkdir(parents=True, exist_ok=True)
        self._s = SteamStoreScraper(cd, self._l)

    def _cleanup(self):
        if self._db:
            self._db.close()
            self._db = None

    def _get_items(self):
        return self._g

    def _process_item(self, it):
        aid, nm = it

        # skip if already has rating
        if not self._f:
            cur = self._db.conn.execute("SELECT pegi_rating FROM games WHERE app_id = ? AND pegi_rating != ''", (aid,))
            if cur.fetchone():
                return True

        if self._f:
            cf = self._s.cache_dir.parent / "age_ratings" / ("%d.json" % aid)
            if cf.exists():
                cf.unlink(missing_ok=True)

        rt = self._s.fetch_age_rating(str(aid))

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
