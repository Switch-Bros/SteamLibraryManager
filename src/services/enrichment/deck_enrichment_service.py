"""Background thread for Steam Deck compatibility status enrichment.

Fetches deck compatibility data from Valve's API for games that are
missing a deck status. Rate-limited to ~1 request/second.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, TYPE_CHECKING

import requests

from src.services.enrichment.base_enrichment_thread import BaseEnrichmentThread
from src.utils.i18n import t

if TYPE_CHECKING:
    from src.core.game import Game

logger = logging.getLogger("steamlibmgr.deck_enrichment")

__all__ = ["DeckEnrichmentThread"]

# Valve API: resolved_category values
_DECK_STATUS_MAP: dict[int, str] = {
    0: "unknown",
    1: "unsupported",
    2: "playable",
    3: "verified",
}

_API_URL = "https://store.steampowered.com/saleaction/ajaxgetdeckappcompatibilityreport?nAppID={app_id}"
_USER_AGENT = "SteamLibraryManager/1.0"
_REQUEST_TIMEOUT = 5
_RATE_LIMIT_DELAY = 1.0


class DeckEnrichmentThread(BaseEnrichmentThread):
    """Background thread for fetching Steam Deck compatibility statuses.

    Iterates over games without a deck status, calls Valve's API for each,
    and caches the result. Emits progress signals for UI feedback.
    """

    def __init__(self, parent: Any = None) -> None:
        """Initializes the DeckEnrichmentThread."""
        super().__init__(parent)
        self._games: list[Game] = []
        self._cache_dir: Path = Path()
        self._store_cache_dir: Path = Path()

    def configure(self, games: list[Game], cache_dir: Path) -> None:
        """Configures the thread with games and cache directory.

        Args:
            games: List of games to enrich (should be pre-filtered to those missing status).
            cache_dir: Base cache directory (store_data subdirectory will be used).
        """
        self._games = games
        self._cache_dir = cache_dir

    # ── BaseEnrichmentThread hooks ──────────────────────

    def _setup(self) -> None:
        """Creates the store_data cache directory."""
        self._store_cache_dir = self._cache_dir / "store_data"
        self._store_cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_items(self) -> list:
        """Returns the list of games to enrich."""
        return self._games

    def _process_item(self, item: Any) -> bool:
        """Fetches the Steam Deck status for a single game.

        Args:
            item: A Game instance.

        Returns:
            True if a valid status was fetched and applied.
        """
        game: Game = item
        status = self._fetch_deck_status(game.app_id, self._store_cache_dir)
        if status:
            game.steam_deck_status = status
            return True
        return False

    def _format_progress(self, item: Any, current: int, total: int) -> str:
        """Formats progress text with the game name.

        Args:
            item: A Game instance.
            current: 1-based current index.
            total: Total games count.

        Returns:
            Formatted progress string.
        """
        game: Game = item
        return t("ui.enrichment.progress", name=game.name[:30], current=current, total=total)

    def _rate_limit(self) -> None:
        """Sleeps 1 second between API requests."""
        time.sleep(_RATE_LIMIT_DELAY)

    # ── Internal ────────────────────────────────────────

    @staticmethod
    def _fetch_deck_status(app_id: str, cache_dir: Path) -> str | None:
        """Fetches the Steam Deck status for a single game from Valve's API.

        Args:
            app_id: The Steam app ID.
            cache_dir: Directory for storing JSON cache files.

        Returns:
            The deck status string ("verified", "playable", etc.), or None on failure.
        """
        cache_file = cache_dir / f"{app_id}_deck.json"

        try:
            url = _API_URL.format(app_id=app_id)
            response = requests.get(
                url,
                timeout=_REQUEST_TIMEOUT,
                headers={"User-Agent": _USER_AGENT},
            )

            if response.status_code != 200:
                logger.debug("Deck API returned %d for %s", response.status_code, app_id)
                return None

            data = response.json()
            results = data.get("results", {})

            if isinstance(results, list):
                results = results[0] if results else {}

            resolved_category = results.get("resolved_category", 0) if isinstance(results, dict) else 0
            status = _DECK_STATUS_MAP.get(resolved_category, "unknown")

            with open(cache_file, "w") as f:
                json.dump({"status": status, "category": resolved_category}, f)

            return status

        except (requests.RequestException, ValueError, KeyError, OSError) as exc:
            logger.debug("Deck API fetch failed for %s: %s", app_id, exc)
            return None
