"""Steam Deck compatibility utility functions.

Provides the shared API call logic for fetching deck compatibility
status from Valve's endpoint. Used by both the detail enricher and
the background enrichment thread.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import requests

logger = logging.getLogger("steamlibmgr.deck_utils")

__all__ = ["DECK_STATUS_MAP", "fetch_deck_compatibility"]

# Valve API: resolved_category values
DECK_STATUS_MAP: dict[int, str] = {
    0: "unknown",
    1: "unsupported",
    2: "playable",
    3: "verified",
}

_API_URL = "https://store.steampowered.com/saleaction/ajaxgetdeckappcompatibilityreport?nAppID={app_id}"
_USER_AGENT = "SteamLibraryManager/1.0"
_REQUEST_TIMEOUT = 5


def fetch_deck_compatibility(app_id: str | int, cache_dir: Path | None = None) -> str | None:
    """Fetches Steam Deck compatibility status from Valve's API.

    Makes a single request to Valve's deck compatibility endpoint,
    parses the resolved_category, and optionally writes a cache file.

    Args:
        app_id: Steam app ID.
        cache_dir: Optional directory for JSON cache files.

    Returns:
        Status string ("verified", "playable", "unsupported", "unknown"),
        or None on failure.
    """
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
        status = DECK_STATUS_MAP.get(resolved_category, "unknown")

        if cache_dir is not None:
            cache_file = cache_dir / f"{app_id}_deck.json"
            with open(cache_file, "w") as f:
                json.dump({"status": status, "category": resolved_category}, f)

        return status

    except (requests.RequestException, ValueError, KeyError, OSError) as exc:
        logger.debug("Deck API fetch failed for %s: %s", app_id, exc)
        return None
