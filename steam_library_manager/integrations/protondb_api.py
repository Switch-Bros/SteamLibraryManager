#
# steam_library_manager/integrations/protondb_api.py
# ProtonDB API client for Linux compatibility ratings
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import requests

from steam_library_manager.utils.timeouts import HTTP_TIMEOUT

logger = logging.getLogger("steamlibmgr.protondb_api")

__all__ = ["ProtonDBClient", "ProtonDBResult", "fetch_and_persist_protondb"]


@dataclass(frozen=True)
class ProtonDBResult:
    """Immutable result from a ProtonDB rating lookup."""

    tier: str
    confidence: str = ""
    trending_tier: str = ""
    score: float = 0.0
    best_reported: str = ""


class ProtonDBClient:
    """Client for the ProtonDB public API with rate-limited lookups."""

    BASE_URL = "https://www.protondb.com/api/v1/reports/summaries/"

    def __init__(self) -> None:
        """Set up HTTP session with custom user-agent."""
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "SteamLibraryManager/1.0"})

    def get_rating(self, app_id: int) -> ProtonDBResult | None:
        """Fetch a single ProtonDB rating, or None on error/404."""
        try:
            url = f"{self.BASE_URL}{app_id}.json"
            response = self._session.get(url, timeout=HTTP_TIMEOUT)

            if response.status_code == 404:
                logger.debug("ProtonDB: no data for app %d", app_id)
                return None

            if response.status_code != 200:
                logger.warning(
                    "ProtonDB: unexpected status %d for app %d",
                    response.status_code,
                    app_id,
                )
                return None

            data = response.json()
            return ProtonDBResult(
                tier=data.get("tier", "unknown"),
                confidence=data.get("confidence", ""),
                trending_tier=data.get("trendingTier", ""),
                score=float(data.get("score", 0.0)),
                best_reported=data.get("bestReportedTier", ""),
            )

        except requests.RequestException as exc:
            logger.warning("ProtonDB: network error for app %d: %s", app_id, exc)
            return None
        except (ValueError, KeyError) as exc:
            logger.warning("ProtonDB: parse error for app %d: %s", app_id, exc)
            return None

    def get_ratings_batch(self, app_ids: list[int], delay: float = 0.5) -> dict[int, ProtonDBResult]:
        """Fetch ratings for multiple apps with rate limiting between requests."""
        results: dict[int, ProtonDBResult] = {}

        for i, app_id in enumerate(app_ids):
            result = self.get_rating(app_id)
            if result is not None:
                results[app_id] = result

            # Rate limit between requests (skip after last)
            if i < len(app_ids) - 1:
                time.sleep(delay)

        return results


def fetch_and_persist_protondb(app_id: int, db: Any, client: ProtonDBClient) -> str | None:
    """Fetch a ProtonDB rating and persist it to the database.

    Returns the tier string if found, None otherwise.
    """
    result = client.get_rating(app_id)
    if result:
        db.upsert_protondb(
            app_id,
            tier=result.tier,
            confidence=result.confidence,
            trending_tier=result.trending_tier,
            score=result.score,
            best_reported=result.best_reported,
        )
        db.commit()
        return result.tier
    return None
