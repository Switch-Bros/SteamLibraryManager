#
# steam_library_manager/services/enrichment/deck_enrichment_service.py
# Steam Deck compatibility enrichment
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
import time

from steam_library_manager.services.enrichment.base_enrichment_thread import BaseEnrichmentThread
from steam_library_manager.utils.deck_utils import fetch_deck_compatibility
from steam_library_manager.utils.i18n import t

logger = logging.getLogger("steamlibmgr.deck_enrichment")

__all__ = ["DeckEnrichmentThread"]

_DELAY = 1.0  # Valve rate limit


class DeckEnrichmentThread(BaseEnrichmentThread):
    """Fetches Steam Deck compat status for games via Valve's API.

    Iterates over games without deck status, hits the API for each,
    caches the result. Rate limited to 1 req/sec.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._games = []
        self._cdir = None
        self._sdir = None

    def configure(self, games, cache_dir, force_refresh=False):
        self._games = games
        self._cdir = cache_dir
        self._force_refresh = force_refresh

    def _setup(self):
        self._sdir = self._cdir / "store_data"
        self._sdir.mkdir(parents=True, exist_ok=True)

    def _get_items(self):
        return self._games

    def _process_item(self, game):
        # fetch and cache
        st = self._fetch(game.app_id, self._sdir)
        if st:
            game.steam_deck_status = st
            return True
        return False

    def _format_progress(self, game, current, total):
        return t("ui.enrichment.progress", name=game.name[:30], current=current, total=total)

    def _rate_limit(self):
        time.sleep(_DELAY)

    @staticmethod
    def _fetch(app_id, cache_dir):
        return fetch_deck_compatibility(app_id, cache_dir)
