#
# steam_library_manager/integrations/steam_web_api.py
# Batched Steam Web API client with rate limiting and retry logic
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Any

import requests

from steam_library_manager.integrations.steam_api_endpoints import SteamAPIEndpoints
from steam_library_manager.utils.timeouts import HTTP_TIMEOUT_API

logger = logging.getLogger("steamlibmgr.steam_web_api")

__all__ = ["SteamAppDetails", "SteamWebAPI"]

_BATCH_SIZE = 50
_BASE_DELAY = 1.0
_MAX_RETRIES = 3
_API_URL = "https://api.steampowered.com/IStoreBrowseService/GetItems/v1"


@dataclass(frozen=True)
class SteamAppDetails:
    """Frozen record of Steam app metadata from the Web API."""

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
    description: str = ""
    short_description: str = ""
    age_ratings: tuple[tuple[str, str], ...] = ()
    dlc_ids: tuple[int, ...] = ()
    asset_urls: tuple[tuple[str, str], ...] = ()


class SteamWebAPI(SteamAPIEndpoints):
    """Batched Steam Web API client for metadata retrieval."""

    def __init__(self, api_key: str) -> None:
        if not api_key or not api_key.strip():
            raise ValueError("Steam API key must not be empty")
        self.api_key: str = api_key.strip()

    def _request_with_retry(
        self,
        url: str,
        params: dict[str, Any],
        *,
        bail_on: frozenset[int] = frozenset(),
    ) -> requests.Response | None:
        """GET with exponential backoff on 429. Does not catch exceptions."""
        for attempt in range(_MAX_RETRIES):
            response = requests.get(url, params=params, timeout=HTTP_TIMEOUT_API)
            if response.status_code == 429:
                delay = _BASE_DELAY * (2**attempt)
                logger.warning("Rate limited (429), retrying in %.1fs...", delay)
                time.sleep(delay)
                continue
            if response.status_code in bail_on:
                return None
            response.raise_for_status()
            return response
        return None

    def get_app_details_batch(self, app_ids: list[int]) -> dict[int, SteamAppDetails]:
        """Fetch metadata for multiple apps in chunks of 50."""
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

            if idx < len(chunks) - 1:
                time.sleep(_BASE_DELAY)

        return result

    def _fetch_batch(self, app_ids: list[int]) -> list[dict[str, Any]]:
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
                    "include_release": True,
                    "include_supported_languages": True,
                    "include_ratings": True,
                    "include_full_description": True,
                    "include_included_items": True,
                },
            }
        )

        params: dict[str, str] = {"input_json": input_json}
        if self.api_key:
            params["key"] = self.api_key

        response = self._request_with_retry(_API_URL, params)
        if response is None:
            logger.error("Exhausted retries for batch of %d apps", len(app_ids))
            return []
        data = response.json()
        return data.get("response", {}).get("store_items", [])

    # Achievement API

    def get_game_schema(self, app_id: int) -> dict | None:
        """Fetch the achievement schema for a game, or None on failure."""
        url = "https://api.steampowered.com/ISteamUserStats/GetSchemaForGame/v2"
        params = {"appid": app_id, "key": self.api_key}

        try:
            response = self._request_with_retry(url, params, bail_on=frozenset({400}))
            if response is None:
                return None
            data = response.json()
            return data.get("game", {}).get("availableGameStats", {})
        except requests.RequestException as exc:
            logger.debug("GetSchemaForGame failed for %d: %s", app_id, exc)
            return None

    def get_player_achievements(self, app_id: int, steam_id: str) -> list[dict] | None:
        """Fetch which achievements the player has unlocked for a game."""
        url = "https://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v1"
        params = {"appid": app_id, "steamid": steam_id, "key": self.api_key}

        try:
            response = self._request_with_retry(url, params, bail_on=frozenset({400}))
            if response is None:
                return None
            data = response.json()
            playerstats = data.get("playerstats", {})
            if not playerstats.get("success", False):
                return None
            return playerstats.get("achievements", [])
        except requests.RequestException as exc:
            logger.debug("GetPlayerAchievements failed for %d: %s", app_id, exc)
            return None

    @staticmethod
    def get_global_achievement_percentages(app_id: int) -> dict[str, float]:
        """Fetch global unlock percentages. No API key required."""
        url = "https://api.steampowered.com/ISteamUserStats/GetGlobalAchievementPercentagesForApp/v2"
        params: dict[str, int] = {"gameid": app_id}

        try:
            response = requests.get(url, params=params, timeout=HTTP_TIMEOUT_API)
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
        """Parse a raw API item dict into a SteamAppDetails."""
        app_id = raw.get("id", raw.get("appid", 0))
        name = raw.get("name", "")

        basic = raw.get("basic_info", {})
        developers_list = [d.get("name", "") for d in basic.get("developers", []) if d.get("name")]
        publishers_list = [p.get("name", "") for p in basic.get("publishers", []) if p.get("name")]
        is_free = basic.get("is_free", False)

        release_info = basic.get("release_date", {})
        if isinstance(release_info, dict):
            steam_release_date = release_info.get("steam_release_date", 0) or 0
            original_release_date = release_info.get("original_release_date", 0) or 0
        else:
            steam_release_date = 0
            original_release_date = 0

        genres_list = [g.get("description", "") for g in basic.get("genres", []) if g.get("description")]
        tags_list = [t.get("name", "") for t in raw.get("tags", []) if t.get("name")]

        platforms_info = raw.get("platforms", {})
        platforms_list: list[str] = []
        if platforms_info.get("windows"):
            platforms_list.append("windows")
        if platforms_info.get("mac"):
            platforms_list.append("mac")
        if platforms_info.get("linux") or platforms_info.get("steamos_linux"):
            platforms_list.append("linux")

        languages_str = basic.get("supported_languages", "")
        languages_list: list[str] = []
        if languages_str:
            # Steam returns HTML like "English<strong>*</strong>, German, ..."
            cleaned = re.sub(r"<[^>]+>", "", languages_str)
            cleaned = cleaned.replace("*", "")
            languages_list = [lang.strip() for lang in cleaned.split(",") if lang.strip()]

        reviews = raw.get("reviews", {})
        review_score = reviews.get("summary_filtered", {}).get("review_score", 0)
        review_desc = reviews.get("summary_filtered", {}).get("review_score_label", "")

        full_desc = raw.get("full_description", "")
        short_desc = raw.get("short_description", "")

        age_ratings_list: list[tuple[str, str]] = []
        raw_ratings = raw.get("ratings", [])
        if isinstance(raw_ratings, list):
            for rating_entry in raw_ratings:
                system = rating_entry.get("rating_system", "")
                rating_val = rating_entry.get("rating", "")
                if system and rating_val:
                    age_ratings_list.append((system, str(rating_val)))
        elif isinstance(raw_ratings, dict):
            for system, data in raw_ratings.items():
                if isinstance(data, dict):
                    rating_val = data.get("rating", "")
                    if rating_val:
                        age_ratings_list.append((system.upper(), str(rating_val)))

        dlc_ids_list: list[int] = []
        included_items = raw.get("included_items", [])
        if isinstance(included_items, list):
            for item in included_items:
                item_id = item.get("appid", 0)
                if item_id:
                    dlc_ids_list.append(item_id)

        asset_urls_list: list[tuple[str, str]] = []
        assets = raw.get("assets", {})
        if isinstance(assets, dict):
            for asset_type, asset_url in assets.items():
                if isinstance(asset_url, str) and asset_url:
                    asset_urls_list.append((asset_type, asset_url))

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
            description=full_desc,
            short_description=short_desc,
            age_ratings=tuple(age_ratings_list),
            dlc_ids=tuple(dlc_ids_list),
            asset_urls=tuple(asset_urls_list),
        )
