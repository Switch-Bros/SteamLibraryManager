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
from PyQt6.QtCore import QThread, pyqtSignal

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


class DeckEnrichmentThread(QThread):
    """Background thread for fetching Steam Deck compatibility statuses.

    Iterates over games without a deck status, calls Valve's API for each,
    and caches the result. Emits progress signals for UI feedback.

    Signals:
        progress: Emitted per game (status_text, current_index, total_count).
        finished_enrichment: Emitted on completion (success_count, failed_count).
        error: Emitted on fatal errors (error_message).
    """

    progress = pyqtSignal(str, int, int)
    finished_enrichment = pyqtSignal(int, int)
    error = pyqtSignal(str)

    def __init__(self, parent: Any = None) -> None:
        """Initializes the DeckEnrichmentThread."""
        super().__init__(parent)
        self._cancelled: bool = False
        self._games: list[Game] = []
        self._cache_dir: Path = Path()

    def configure(self, games: list[Game], cache_dir: Path) -> None:
        """Configures the thread with games and cache directory.

        Args:
            games: List of games to enrich (should be pre-filtered to those missing status).
            cache_dir: Base cache directory (store_data subdirectory will be used).
        """
        self._games = games
        self._cache_dir = cache_dir

    def cancel(self) -> None:
        """Requests cancellation of the enrichment."""
        self._cancelled = True

    def run(self) -> None:
        """Executes the deck status enrichment in the background thread."""
        self._cancelled = False
        total = len(self._games)
        success = 0
        failed = 0

        store_cache_dir = self._cache_dir / "store_data"
        store_cache_dir.mkdir(parents=True, exist_ok=True)

        for idx, game in enumerate(self._games):
            if self._cancelled:
                break

            self.progress.emit(
                t("ui.enrichment.progress", name=game.name[:30], current=idx + 1, total=total),
                idx + 1,
                total,
            )

            status = self._fetch_deck_status(game.app_id, store_cache_dir)
            if status:
                game.steam_deck_status = status
                success += 1
            else:
                failed += 1

            if idx < total - 1:
                time.sleep(_RATE_LIMIT_DELAY)

        self.finished_enrichment.emit(success, failed)

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
