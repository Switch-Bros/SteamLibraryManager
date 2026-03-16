#
# steam_library_manager/services/enrichment/deck_enrichment_service.py
# Background thread for Steam Deck compatibility status enrichment
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, TYPE_CHECKING

from steam_library_manager.services.enrichment.base_enrichment_thread import BaseEnrichmentThread
from steam_library_manager.utils.deck_utils import fetch_deck_compatibility
from steam_library_manager.utils.i18n import t

if TYPE_CHECKING:
    from steam_library_manager.core.game import Game

logger = logging.getLogger("steamlibmgr.deck_enrichment")

__all__ = ["DeckEnrichmentThread"]

_RATE_LIMIT_DELAY = 1.0


class DeckEnrichmentThread(BaseEnrichmentThread):
    """Background thread for fetching Steam Deck compatibility statuses.

    Iterates over games without a deck status, calls Valve's API for each,
    and caches the result. Emits progress signals for UI feedback.
    """

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._games: list[Game] = []
        self._cache_dir: Path = Path()
        self._store_cache_dir: Path = Path()

    def configure(
        self,
        games: list[Game],
        cache_dir: Path,
        force_refresh: bool = False,
    ) -> None:
        """Configure the thread with games and cache directory."""
        self._games = games
        self._cache_dir = cache_dir
        self._force_refresh = force_refresh

    def _setup(self) -> None:
        self._store_cache_dir = self._cache_dir / "store_data"
        self._store_cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_items(self) -> list:
        return self._games

    def _process_item(self, item: Any) -> bool:
        game: Game = item
        status = self._fetch_deck_status(game.app_id, self._store_cache_dir)
        if status:
            game.steam_deck_status = status
            return True
        return False

    def _format_progress(self, item: Any, current: int, total: int) -> str:
        game: Game = item
        return t("ui.enrichment.progress", name=game.name[:30], current=current, total=total)

    def _rate_limit(self) -> None:
        time.sleep(_RATE_LIMIT_DELAY)

    @staticmethod
    def _fetch_deck_status(app_id: str, cache_dir: Path) -> str | None:
        return fetch_deck_compatibility(app_id, cache_dir)
