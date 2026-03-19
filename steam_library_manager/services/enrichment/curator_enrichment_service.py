#
# steam_library_manager/services/enrichment/curator_enrichment_service.py
# Enrichment service for curator recommendations and overlap scoring
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
import time

from steam_library_manager.services.enrichment.base_enrichment_thread import BaseEnrichmentThread
from steam_library_manager.utils.i18n import t

logger = logging.getLogger("steamlibmgr.curator_enrichment")

__all__ = ["CuratorEnrichmentThread"]


class CuratorEnrichmentThread(BaseEnrichmentThread):
    """Fetches recommendations for all configured curators."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._curators = []
        self._db_path = None
        self._force_refresh = False
        self._db = None
        self._client = None

    def configure(self, curators, db_path, force_refresh=False):
        # set up curator list, DB path, refresh mode
        self._curators = curators
        self._db_path = db_path
        self._force_refresh = force_refresh
        self._db = None

    def _setup(self):
        # lazy imports - only when thread runs
        from steam_library_manager.core.db import Database
        from steam_library_manager.services.curator_client import CuratorClient

        self._db = Database(self._db_path)
        self._client = CuratorClient()

    def _cleanup(self):
        if self._db:
            self._db.close()
            self._db = None

    def _get_items(self):
        return self._curators

    def _process_item(self, item):
        # fetch recs for single curator
        from steam_library_manager.services.curator_client import CuratorRecommendation

        cid = item["curator_id"]
        nm = item["name"]

        # fallback to standard store page
        url = item.get("url") or "https://store.steampowered.com/curator/%d/" % cid

        try:
            recs = self._client.fetch_recs(url)

            # only positive recommendations
            ids = [aid for aid, rt in recs.items() if rt == CuratorRecommendation.RECOMMENDED]

            self._db.save_curator_recommendations(cid, ids)
            logger.info(t("logs.curator.fetch_success", name=nm, count=len(ids)))
            return True

        except (ConnectionError, ValueError, OSError) as exc:
            logger.warning(t("logs.curator.fetch_failed", name=nm, error=str(exc)))
            return False

    def _format_progress(self, item, current, total):
        nm = item.get("name", "?")
        return t("ui.enrichment.curator_progress", current=current, total=total, name=nm)

    def _rate_limit(self):
        time.sleep(2.0)  # stay under Steam rate limit
