#
# steam_library_manager/utils/deck_utils.py
# Steam Deck compatibility API utilities
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import json
import logging
from pathlib import Path

import requests

from steam_library_manager.utils.timeouts import HTTP_TIMEOUT_SHORT

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


def fetch_deck_compatibility(app_id: str | int, cache_dir: Path | None = None) -> str | None:
    """Fetch Deck compatibility from Valve's API, optionally caching the result."""
    try:
        url = _API_URL.format(app_id=app_id)
        response = requests.get(
            url,
            timeout=HTTP_TIMEOUT_SHORT,
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
