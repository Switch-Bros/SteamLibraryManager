"""ProtonDB API client for Linux compatibility ratings.

Queries the ProtonDB public API to retrieve compatibility tiers and
related metadata for Steam games. Supports single and batch lookups
with rate limiting to avoid overloading the service.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import requests

logger = logging.getLogger("steamlibmgr.protondb_api")

__all__ = ["ProtonDBClient", "ProtonDBResult", "fetch_and_persist_protondb"]


@dataclass(frozen=True)
class ProtonDBResult:
    """Immutable result from a ProtonDB rating lookup.

    Attributes:
        tier: Compatibility tier (platinum, gold, silver, bronze, borked, native, pending).
        confidence: Confidence level of the rating (good, strong, weak).
        trending_tier: Trending tier direction if available.
        score: Numeric score if available.
        best_reported: Best tier reported by users.
    """

    tier: str
    confidence: str = ""
    trending_tier: str = ""
    score: float = 0.0
    best_reported: str = ""


class ProtonDBClient:
    """Client for the ProtonDB public API.

    Fetches compatibility ratings for Steam games. The API has no
    authentication but should be queried respectfully with rate limiting.
    """

    BASE_URL = "https://www.protondb.com/api/v1/reports/summaries/"

    def __init__(self) -> None:
        """Initializes the ProtonDB client with a configured session."""
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "SteamLibraryManager/1.0"})

    def get_rating(self, app_id: int) -> ProtonDBResult | None:
        """Fetches a single ProtonDB rating.

        Args:
            app_id: Steam app ID.

        Returns:
            ProtonDBResult with all available fields, or None on error/404.
        """
        try:
            url = f"{self.BASE_URL}{app_id}.json"
            response = self._session.get(url, timeout=10)

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
        """Fetches ratings for multiple apps sequentially with rate limiting.

        ProtonDB has no batch endpoint, so requests are made one at a time
        with a configurable delay between each.

        Args:
            app_ids: List of Steam app IDs to query.
            delay: Seconds to wait between requests.

        Returns:
            Dict mapping app_id to ProtonDBResult (only successful lookups).
        """
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
    """Fetches a ProtonDB rating and persists it to the database.

    Shared logic used by both the game detail enricher and the
    background ProtonDB enrichment thread.

    Args:
        app_id: Steam app ID.
        db: Database instance with upsert_protondb() and commit().
        client: ProtonDBClient instance.

    Returns:
        The tier string if a rating was found and persisted, None otherwise.
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
