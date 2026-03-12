"""Background enrichment worker for PEGI age ratings.

Fetches age ratings from Steam Store API (with HTML fallback) for games
missing PEGI data. Results are cached via SteamStoreScraper's file cache
(30-day TTL).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from steam_library_manager.services.enrichment.base_enrichment_thread import BaseEnrichmentThread
from steam_library_manager.utils.i18n import t

logger = logging.getLogger("steamlibmgr.enrichment.pegi")

__all__ = ["PEGIEnrichmentThread"]


class PEGIEnrichmentThread(BaseEnrichmentThread):
    """Background thread for PEGI age rating enrichment.

    Uses SteamStoreScraper.fetch_age_rating() which tries the Steam API
    first, then falls back to HTML scraping. Results are file-cached
    (30-day TTL) by the scraper.

    Configure with configure() before starting.
    """

    def __init__(self, parent: Any = None) -> None:
        """Initializes the PEGI enrichment thread."""
        super().__init__(parent)
        self._games: list[tuple[int, str]] = []
        self._db_path: Path | None = None
        self._force_refresh: bool = False
        self._language: str = "en"
        self._db: Any = None
        self._scraper: Any = None

    def configure(
        self,
        games: list[tuple[int, str]],
        db_path: Path,
        language: str = "en",
        force_refresh: bool = False,
    ) -> None:
        """Configures the thread for PEGI enrichment.

        Args:
            games: List of (app_id, name) tuples to enrich.
            db_path: Path to the SQLite database file.
            language: Steam language code for store scraping.
            force_refresh: If True, skip cache and re-fetch all ratings.
        """
        self._games = games
        self._db_path = db_path
        self._language = language
        self._force_refresh = force_refresh

    def _setup(self) -> None:
        """Opens DB connection and initializes the Steam Store scraper."""
        from steam_library_manager.core.database import Database
        from steam_library_manager.integrations.steam_store import SteamStoreScraper

        self._db = Database(self._db_path)
        cache_dir = self._db_path.parent / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        self._scraper = SteamStoreScraper(cache_dir, self._language)

    def _cleanup(self) -> None:
        """Closes the database connection."""
        if self._db:
            self._db.close()
            self._db = None

    def _get_items(self) -> list:
        """Returns the list of games to enrich."""
        return self._games

    def _process_item(self, item: Any) -> bool:
        """Fetches the PEGI rating for a single game.

        Acts as a gap filler: skips games that already have a rating
        (filled by the batch Steam API enrichment pass).

        Args:
            item: Tuple of (app_id, name).

        Returns:
            True if a valid rating was found and stored.
        """
        app_id, name = item

        # Skip if already has a rating (filled by batch Steam API)
        if not self._force_refresh:
            cursor = self._db.conn.execute(
                "SELECT pegi_rating FROM games WHERE app_id = ? AND pegi_rating != ''",
                (app_id,),
            )
            if cursor.fetchone():
                return True  # Already done, count as success

        if self._force_refresh:
            cache_file = self._scraper.cache_dir.parent / "age_ratings" / f"{app_id}.json"
            if cache_file.exists():
                cache_file.unlink(missing_ok=True)

        rating = self._scraper.fetch_age_rating(str(app_id))

        if rating:
            self._db.conn.execute(
                "UPDATE games SET pegi_rating = ? WHERE app_id = ?",
                (rating, app_id),
            )
            self._db.conn.commit()
            return True

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
        """No delay needed — SteamStoreScraper has its own internal rate limit.

        Most games are skipped instantly (already rated by batch API).
        Only gap-fill HTTP requests are rate-limited by the scraper itself.
        """
