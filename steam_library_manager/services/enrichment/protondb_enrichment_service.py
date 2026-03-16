#
# steam_library_manager/services/enrichment/protondb_enrichment_service.py
# Background enrichment worker for ProtonDB ratings.
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from steam_library_manager.services.enrichment.base_enrichment_thread import BaseEnrichmentThread
from steam_library_manager.utils.i18n import t

logger = logging.getLogger("steamlibmgr.enrichment.protondb")

__all__ = ["ProtonDBEnrichmentThread"]


class ProtonDBEnrichmentThread(BaseEnrichmentThread):
    """Background thread for ProtonDB rating enrichment."""

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._games: list[tuple[int, str]] = []
        self._db_path: Path | None = None
        self._force_refresh: bool = False
        self._db: Any = None
        self._client: Any = None

    def configure(
        self,
        games: list[tuple[int, str]],
        db_path: Path,
        force_refresh: bool = False,
    ) -> None:
        """Configures the thread for ProtonDB enrichment."""
        self._games = games
        self._db_path = db_path
        self._force_refresh = force_refresh

    def _setup(self) -> None:
        """Opens DB connection and initializes the ProtonDB client."""
        from steam_library_manager.core.database import Database
        from steam_library_manager.integrations.protondb_api import ProtonDBClient, fetch_and_persist_protondb

        self._db = Database(self._db_path)
        self._client = ProtonDBClient()
        self._fetch_and_persist = fetch_and_persist_protondb

    def _cleanup(self) -> None:
        """Closes the database connection."""
        if self._db:
            self._db.close()
            self._db = None

    def _get_items(self) -> list:
        """Returns the list of games to enrich."""
        return self._games

    def _process_item(self, item: Any) -> bool:
        """Enriches a single game with ProtonDB data."""
        app_id, name = item

        # Check DB cache unless force refresh
        if not self._force_refresh:
            cached = self._db.get_cached_protondb(app_id)
            if cached:
                logger.debug("ProtonDB cache hit for %d '%s'", app_id, name)
                return True

        # Fetch from API and persist
        tier = self._fetch_and_persist(app_id, self._db, self._client)
        if tier:
            return True

        # No data - store "unknown" so we don't retry immediately
        self._db.upsert_protondb(app_id, tier="unknown")
        self._db.commit()
        logger.info("ProtonDB miss: %d '%s' (marked as unknown)", app_id, name)
        return False

    def _format_progress(self, item: Any, current: int, total: int) -> str:
        """Formats progress text with the game name."""
        _app_id, name = item
        return t("ui.enrichment.progress", name=name, current=current, total=total)

    def _rate_limit(self) -> None:
        """Sleeps 200ms between ProtonDB requests."""
        time.sleep(0.2)
