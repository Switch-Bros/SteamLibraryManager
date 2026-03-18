#
# steam_library_manager/services/enrichment/protondb_enrichment_service.py
# ProtonDB Linux compat ratings
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
import time

from steam_library_manager.services.enrichment.base_enrichment_thread import BaseEnrichmentThread
from steam_library_manager.utils.i18n import t

logger = logging.getLogger("steamlibmgr.enrichment.protondb")

__all__ = ["ProtonDBEnrichmentThread"]


class ProtonDBEnrichmentThread(BaseEnrichmentThread):
    """Background worker for ProtonDB rating lookups.

    Fetches tier ratings (platinum/gold/silver/bronze/borked)
    from protondb.com API, caches in local DB.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._games = []
        self._dbpath = None
        self._force_refresh = False
        self._db = None
        self._cli = None

    def configure(self, games, db_path, force_refresh=False):
        # setup before run
        self._games = games
        self._dbpath = db_path
        self._force_refresh = force_refresh

    def _setup(self):
        # init db + api client
        from steam_library_manager.core.database import Database
        from steam_library_manager.integrations.protondb_api import ProtonDBClient, fetch_and_persist_protondb

        self._db = Database(self._dbpath)
        self._cli = ProtonDBClient()
        self._fetch = fetch_and_persist_protondb

    def _cleanup(self):
        if self._db:
            self._db.close()
            self._db = None

    def _get_items(self):
        return self._games

    def _process_item(self, item):
        # get rating for one game
        app_id, name = item

        # check cache
        if not self._force_refresh:
            cached = self._db.get_cached_protondb(app_id)
            if cached:
                logger.debug("cache hit: %d '%s'" % (app_id, name))
                return True

        # fetch from api
        tier = self._fetch(app_id, self._db, self._cli)
        if tier:
            return True

        # mark unknown to avoid hammering
        self._db.upsert_protondb(app_id, tier="unknown")
        self._db.commit()
        logger.info("miss: %d '%s' (unknown)" % (app_id, name))
        return False

    def _format_progress(self, item, current, total):
        _id, name = item
        return t("ui.enrichment.progress", name=name, current=current, total=total)

    def _rate_limit(self):
        # protondb is rate limited - 200ms delay
        time.sleep(0.2)
