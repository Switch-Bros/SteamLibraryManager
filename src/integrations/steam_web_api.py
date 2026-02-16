"""Steam Web API client for batched metadata retrieval.

Uses the IStoreBrowseService/GetItems/v1 endpoint to fetch game metadata
in chunks of 50, with rate limiting and exponential backoff on 429s.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any

import requests

logger = logging.getLogger("steamlibmgr.steam_web_api")

__all__ = ["SteamAppDetails", "SteamWebAPI"]

_BATCH_SIZE = 50
_BASE_DELAY = 1.0
_MAX_RETRIES = 3
_API_URL = "https://api.steampowered.com/IStoreBrowseService/GetItems/v1"


@dataclass(frozen=True)
class SteamAppDetails:
    """Frozen dataclass for Steam app metadata from the Web API.

    Attributes:
        app_id: Steam application ID.
        name: Display name of the application.
        developers: Tuple of developer names.
        publishers: Tuple of publisher names.
        steam_release_date: Steam release date as Unix timestamp.
        original_release_date: Original release date as Unix timestamp.
        genres: Tuple of genre names.
        tags: Tuple of user-defined tag names.
        platforms: Tuple of supported platform names.
        languages: Tuple of supported language names.
        review_score: Aggregate review score (0-100).
        review_desc: Human-readable review description.
        is_free: Whether the app is free to play.
    """

    app_id: int
    name: str
    developers: tuple[str, ...] = ()
    publishers: tuple[str, ...] = ()
    steam_release_date: int = 0
    original_release_date: int = 0
    genres: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    platforms: tuple[str, ...] = ()
    languages: tuple[str, ...] = ()
    review_score: int = 0
    review_desc: str = ""
    is_free: bool = False


class SteamWebAPI:
    """Batched Steam Web API client for metadata retrieval.

    Fetches game metadata via IStoreBrowseService/GetItems/v1 in configurable
    batch sizes with rate limiting and retry logic.

    Attributes:
        api_key: Steam Web API key for authentication.
    """

    def __init__(self, api_key: str) -> None:
        """Initializes the SteamWebAPI client.

        Args:
            api_key: Steam Web API key. Must not be empty.

        Raises:
            ValueError: If api_key is empty or whitespace-only.
        """
        if not api_key or not api_key.strip():
            raise ValueError("Steam API key must not be empty")
        self.api_key: str = api_key.strip()

    def get_app_details_batch(self, app_ids: list[int]) -> dict[int, SteamAppDetails]:
        """Fetches metadata for multiple apps in chunked batches.

        Splits the input into chunks of 50 and calls the API for each.
        Pauses 1 second between batches for rate limiting.

        Args:
            app_ids: List of Steam app IDs to fetch.

        Returns:
            Dict mapping app_id to SteamAppDetails for successfully fetched apps.
        """
        if not app_ids:
            return {}

        result: dict[int, SteamAppDetails] = {}
        chunks = [app_ids[i : i + _BATCH_SIZE] for i in range(0, len(app_ids), _BATCH_SIZE)]

        for idx, chunk in enumerate(chunks):
            try:
                batch_result = self._fetch_batch(chunk)
                for item in batch_result:
                    details = self._parse_item(item)
                    result[details.app_id] = details
            except requests.ConnectionError:
                logger.error("Network error fetching batch %d/%d", idx + 1, len(chunks))
                raise
            except requests.RequestException as exc:
                logger.warning("Failed batch %d/%d: %s", idx + 1, len(chunks), exc)

            # Rate limit between batches (skip after last)
            if idx < len(chunks) - 1:
                time.sleep(_BASE_DELAY)

        return result

    def _fetch_batch(self, app_ids: list[int]) -> list[dict[str, Any]]:
        """Fetches a single batch of app details from the API.

        Implements exponential backoff on HTTP 429 (rate limit).

        Args:
            app_ids: List of app IDs for this batch (max 50).

        Returns:
            List of raw item dicts from the API response.

        Raises:
            requests.ConnectionError: On network failure.
            requests.HTTPError: On non-retryable HTTP errors.
        """
        input_json = json.dumps(
            {
                "ids": [{"appid": aid} for aid in app_ids],
                "context": {"language": "english", "country_code": "US"},
                "data_request": {
                    "include_basic_info": True,
                    "include_tag_count": 20,
                    "include_reviews": True,
                    "include_platforms": True,
                    "include_assets": True,
                },
            }
        )

        params: dict[str, str] = {"input_json": input_json}
        if self.api_key:
            params["key"] = self.api_key

        for attempt in range(_MAX_RETRIES):
            response = requests.get(_API_URL, params=params, timeout=30)

            if response.status_code == 429:
                delay = _BASE_DELAY * (2**attempt)
                logger.warning("Rate limited (429), retrying in %.1fs...", delay)
                time.sleep(delay)
                continue

            response.raise_for_status()
            data = response.json()
            return data.get("response", {}).get("store_items", [])

        # Exhausted retries
        logger.error("Exhausted retries for batch of %d apps", len(app_ids))
        return []

    # ------------------------------------------------------------------
    # Achievement API endpoints (Phase 5.2)
    # ------------------------------------------------------------------

    def get_game_schema(self, app_id: int) -> dict | None:
        """Fetches the achievement schema for a game.

        Uses ISteamUserStats/GetSchemaForGame/v2 to get the list of
        possible achievements including display names and hidden flags.

        Args:
            app_id: Steam app ID.

        Returns:
            Dict with 'achievements' list, or None on failure.
        """
        url = "https://api.steampowered.com/ISteamUserStats/GetSchemaForGame/v2"
        params = {"appid": app_id, "key": self.api_key}

        for attempt in range(_MAX_RETRIES):
            try:
                response = requests.get(url, params=params, timeout=30)
                if response.status_code == 429:
                    delay = _BASE_DELAY * (2**attempt)
                    logger.warning("Rate limited (429), retrying in %.1fs...", delay)
                    time.sleep(delay)
                    continue
                if response.status_code == 400:
                    # Game has no stats/achievements
                    return None
                response.raise_for_status()
                data = response.json()
                return data.get("game", {}).get("availableGameStats", {})
            except requests.RequestException as exc:
                logger.debug("GetSchemaForGame failed for %d: %s", app_id, exc)
                if attempt == _MAX_RETRIES - 1:
                    return None
        return None

    def get_player_achievements(self, app_id: int, steam_id: str) -> list[dict] | None:
        """Fetches the player's achievement status for a game.

        Uses ISteamUserStats/GetPlayerAchievements/v1 to get which
        achievements the player has unlocked and when.

        Args:
            app_id: Steam app ID.
            steam_id: 64-bit Steam user ID.

        Returns:
            List of achievement dicts with 'apiname', 'achieved', 'unlocktime',
            or None on failure.
        """
        url = "https://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v1"
        params = {"appid": app_id, "steamid": steam_id, "key": self.api_key}

        for attempt in range(_MAX_RETRIES):
            try:
                response = requests.get(url, params=params, timeout=30)
                if response.status_code == 429:
                    delay = _BASE_DELAY * (2**attempt)
                    logger.warning("Rate limited (429), retrying in %.1fs...", delay)
                    time.sleep(delay)
                    continue
                if response.status_code == 400:
                    # Game has no achievements or profile is private
                    return None
                response.raise_for_status()
                data = response.json()
                playerstats = data.get("playerstats", {})
                if not playerstats.get("success", False):
                    return None
                return playerstats.get("achievements", [])
            except requests.RequestException as exc:
                logger.debug("GetPlayerAchievements failed for %d: %s", app_id, exc)
                if attempt == _MAX_RETRIES - 1:
                    return None
        return None

    @staticmethod
    def get_global_achievement_percentages(app_id: int) -> dict[str, float]:
        """Fetches global achievement unlock percentages for a game.

        Uses ISteamUserStats/GetGlobalAchievementPercentagesForApp/v2.
        This endpoint does NOT require an API key.

        Args:
            app_id: Steam app ID.

        Returns:
            Dict mapping achievement API name to unlock percentage (0-100).
        """
        url = "https://api.steampowered.com/ISteamUserStats/GetGlobalAchievementPercentagesForApp/v2"
        params: dict[str, int] = {"gameid": app_id}

        try:
            response = requests.get(url, params=params, timeout=30)
            if response.status_code != 200:
                return {}
            data = response.json()
            achievements = data.get("achievementpercentages", {}).get("achievements", [])
            return {ach["name"]: float(ach["percent"]) for ach in achievements if "name" in ach}
        except (requests.RequestException, ValueError, KeyError) as exc:
            logger.debug("GetGlobalAchievementPercentages failed for %d: %s", app_id, exc)
            return {}

    @staticmethod
    def _parse_item(raw: dict[str, Any]) -> SteamAppDetails:
        """Parses a raw API item dict into a frozen SteamAppDetails.

        Args:
            raw: Single item dict from the API response.

        Returns:
            Populated SteamAppDetails dataclass.
        """
        app_id = raw.get("id", raw.get("appid", 0))
        name = raw.get("name", "")

        # Basic info
        basic = raw.get("basic_info", {})
        developers_list = [d.get("name", "") for d in basic.get("developers", []) if d.get("name")]
        publishers_list = [p.get("name", "") for p in basic.get("publishers", []) if p.get("name")]
        is_free = basic.get("is_free", False)

        # Release dates (Unix timestamps from IStoreBrowseService)
        release_info = basic.get("release_date", {})
        if isinstance(release_info, dict):
            steam_release_date = release_info.get("steam_release_date", 0) or 0
            original_release_date = release_info.get("original_release_date", 0) or 0
        else:
            steam_release_date = 0
            original_release_date = 0

        # Genres
        genres_list = [g.get("description", "") for g in basic.get("genres", []) if g.get("description")]

        # Tags
        tags_list = [t.get("name", "") for t in raw.get("tags", []) if t.get("name")]

        # Platforms
        platforms_info = raw.get("platforms", {})
        platforms_list: list[str] = []
        if platforms_info.get("windows"):
            platforms_list.append("windows")
        if platforms_info.get("mac"):
            platforms_list.append("mac")
        if platforms_info.get("linux") or platforms_info.get("steamos_linux"):
            platforms_list.append("linux")

        # Languages (from supported_languages string)
        languages_str = basic.get("supported_languages", "")
        languages_list: list[str] = []
        if languages_str:
            # Steam returns HTML like "English<strong>*</strong>, German, ..."
            import re

            cleaned = re.sub(r"<[^>]+>", "", languages_str)
            languages_list = [lang.strip() for lang in cleaned.split(",") if lang.strip()]

        # Reviews
        reviews = raw.get("reviews", {})
        review_score = reviews.get("summary_filtered", {}).get("review_score", 0)
        review_desc = reviews.get("summary_filtered", {}).get("review_score_label", "")

        return SteamAppDetails(
            app_id=app_id,
            name=name,
            developers=tuple(developers_list),
            publishers=tuple(publishers_list),
            steam_release_date=steam_release_date,
            original_release_date=original_release_date,
            genres=tuple(genres_list),
            tags=tuple(tags_list),
            platforms=tuple(platforms_list),
            languages=tuple(languages_list),
            review_score=review_score,
            review_desc=review_desc,
            is_free=is_free,
        )
