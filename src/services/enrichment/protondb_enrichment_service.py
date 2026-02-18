"""Background enrichment worker for ProtonDB ratings.

Provides ProtonDBEnrichmentThread that fetches compatibility ratings
from ProtonDB for games missing this data, with DB caching (7-day TTL)
and configurable force refresh.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from src.services.enrichment.base_enrichment_thread import BaseEnrichmentThread
from src.utils.i18n import t

logger = logging.getLogger("steamlibmgr.enrichment.protondb")

__all__ = ["ProtonDBEnrichmentThread"]


class ProtonDBEnrichmentThread(BaseEnrichmentThread):
    """Background thread for ProtonDB rating enrichment.

    Fetches compatibility tiers from the ProtonDB API, caches results
    in the protondb_ratings DB table (7-day TTL), and updates the
    in-memory game objects.

    Configure with configure() before starting.
    """

    def __init__(self, parent: Any = None) -> None:
        """Initializes the ProtonDB enrichment thread."""
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
        """Configures the thread for ProtonDB enrichment.

        Args:
            games: List of (app_id, name) tuples to enrich.
            db_path: Path to the SQLite database file.
            force_refresh: If True, skip cache and re-fetch all ratings.
        """
        self._games = games
        self._db_path = db_path
        self._force_refresh = force_refresh

    def _setup(self) -> None:
        """Opens DB connection and initializes the ProtonDB client."""
        from src.core.database import Database
        from src.integrations.protondb_api import ProtonDBClient

        self._db = Database(self._db_path)
        self._client = ProtonDBClient()

    def _cleanup(self) -> None:
        """Closes the database connection."""
        if self._db:
            self._db.close()
            self._db = None

    def _get_items(self) -> list:
        """Returns the list of games to enrich."""
        return self._games

    def _process_item(self, item: Any) -> bool:
        """Enriches a single game with ProtonDB data.

        Checks the DB cache first (7-day TTL). On cache miss or
        force_refresh, queries the ProtonDB API and persists the result.

        Args:
            item: Tuple of (app_id, name).

        Returns:
            True if a valid rating was found and stored.
        """
        app_id, name = item

        # Check DB cache unless force refresh
        if not self._force_refresh:
            cached = self._db.get_cached_protondb(app_id)
            if cached:
                logger.debug("ProtonDB cache hit for %d '%s'", app_id, name)
                return True

        # Fetch from API
        result = self._client.get_rating(app_id)

        if result:
            self._db.upsert_protondb(
                app_id,
                tier=result.tier,
                confidence=result.confidence,
                trending_tier=result.trending_tier,
                score=result.score,
                best_reported=result.best_reported,
            )
            self._db.conn.commit()
            return True

        # No data — store "unknown" so we don't retry immediately
        self._db.upsert_protondb(app_id, tier="unknown")
        self._db.conn.commit()
        logger.info("ProtonDB miss: %d '%s' (marked as unknown)", app_id, name)
        return False

    def _format_progress(self, item: Any, current: int, total: int) -> str:
        """Formats progress text with the game name.

        Args:
            item: Tuple of (app_id, name).
            current: 1-based current index.
            total: Total games count.

        Returns:
            Formatted progress string.
        """
        _app_id, name = item
        return t("ui.enrichment.progress", name=name, current=current, total=total)

    def _rate_limit(self) -> None:
        """Sleeps 500ms between ProtonDB requests."""
        time.sleep(0.5)
