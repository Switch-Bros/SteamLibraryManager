#
# steam_library_manager/integrations/steam_web_api.py
# Steam Web API client for library, player, and app data
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
    """Frozen dataclass for Steam app metadata."""

    app_id: int
    name: str
    developers: tuple[str, ...] = ()
    publishers: tuple[str, ...] = ()
    steam_release_date: int = 0
    original_release_date: int = 0
    genres: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    tag_ids: tuple[tuple[int, str], ...] = ()  # (tagid, name) pairs from API
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
    """Batched Steam Web API client with retry logic."""

    def __init__(self, api_key: str) -> None:
        if not api_key or not api_key.strip():
            raise ValueError("Steam API key must not be empty")
        self.api_key: str = api_key.strip()

    # GET with retry on 429, exponential backoff
    def _request_with_retry(
        self,
        url: str,
        params: dict[str, Any],
        *,
        bail_on: frozenset[int] = frozenset(),
    ) -> requests.Response | None:
        for attempt in range(_MAX_RETRIES):
            response = requests.get(url, params=params, timeout=HTTP_TIMEOUT_API)
            if response.status_code == 429:
                delay = _BASE_DELAY * (2**attempt)
                logger.warning("Rate limited (429), retrying in %.1fs..." % delay)
                time.sleep(delay)
                continue
            if response.status_code in bail_on:
                return None
            response.raise_for_status()
            return response
        return None

    # fetch metadata for multiple apps in chunks
    def get_app_details_batch(self, app_ids: list[int]) -> dict[int, SteamAppDetails]:
        if not app_ids:
            return {}

        out = {}
        chunks = [app_ids[i : i + _BATCH_SIZE] for i in range(0, len(app_ids), _BATCH_SIZE)]

        for idx, chunk in enumerate(chunks):
            try:
                batch = self._fetch_batch(chunk)
                for item in batch:
                    details = self._parse_item(item)
                    out[details.app_id] = details
            except requests.ConnectionError:
                logger.error("Network error fetching batch %d/%d" % (idx + 1, len(chunks)))
                raise
            except requests.RequestException as exc:
                logger.warning("Failed batch %d/%d: %s" % (idx + 1, len(chunks), exc))

            # Rate limit between batches (skip after last)
            if idx < len(chunks) - 1:
                time.sleep(_BASE_DELAY)

        return out

    # fetch single batch from API
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

        params = {"input_json": input_json}
        if self.api_key:
            params["key"] = self.api_key

        response = self._request_with_retry(_API_URL, params)
        if response is None:
            logger.error("Exhausted retries for batch of %d apps" % len(app_ids))
            return []
        data = response.json()
        return data.get("response", {}).get("store_items", [])

    # achievement endpoints

    # fetch achievement schema for game
    def get_game_schema(self, app_id: int) -> dict | None:
        url = "https://api.steampowered.com/ISteamUserStats/GetSchemaForGame/v2"
        params = {"appid": app_id, "key": self.api_key}

        try:
            response = self._request_with_retry(url, params, bail_on=frozenset({400}))
            if response is None:
                return None
            data = response.json()
            return data.get("game", {}).get("availableGameStats", {})
        except requests.RequestException as exc:
            logger.debug("GetSchemaForGame failed for %d: %s" % (app_id, exc))
            return None

    # fetch player achievement status
    def get_player_achievements(self, app_id: int, steam_id: str) -> list[dict] | None:
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
            logger.debug("GetPlayerAchievements failed for %d: %s" % (app_id, exc))
            return None

    # global unlock percentages (no API key needed)
    @staticmethod
    def get_global_achievement_percentages(app_id: int) -> dict[str, float]:
        url = "https://api.steampowered.com/ISteamUserStats/GetGlobalAchievementPercentagesForApp/v2"
        params = {"gameid": app_id}

        try:
            response = requests.get(url, params=params, timeout=HTTP_TIMEOUT_API)
            if response.status_code != 200:
                return {}
            data = response.json()
            achievements = data.get("achievementpercentages", {}).get("achievements", [])
            return {ach["name"]: float(ach["percent"]) for ach in achievements if "name" in ach}
        except (requests.RequestException, ValueError, KeyError) as exc:
            logger.debug("GetGlobalAchievementPercentages failed for %d: %s" % (app_id, exc))
            return {}

    # FIXME: _parse_item is way too long
    @staticmethod
    def _parse_item(raw: dict[str, Any]) -> SteamAppDetails:
        # raw API dict -> SteamAppDetails
        app_id = raw.get("id", raw.get("appid", 0))
        name = raw.get("name", "")

        # Basic info
        basic = raw.get("basic_info", {})
        devs = [d.get("name", "") for d in basic.get("developers", []) if d.get("name")]
        pubs = [p.get("name", "") for p in basic.get("publishers", []) if p.get("name")]
        is_free = basic.get("is_free", False)

        # Release dates (Unix timestamps from IStoreBrowseService)
        rel = basic.get("release_date", {})
        if isinstance(rel, dict):
            steam_release_date = rel.get("steam_release_date", 0) or 0
            original_release_date = rel.get("original_release_date", 0) or 0
        else:
            steam_release_date = 0
            original_release_date = 0

        # Genres
        gens = [g.get("description", "") for g in basic.get("genres", []) if g.get("description")]

        # Tags - names and (tagid, name) pairs
        raw_tags = raw.get("tags", [])
        tlist = [t.get("name", "") for t in raw_tags if t.get("name")]
        tid_pairs = [(int(t["tagid"]), t.get("name", "")) for t in raw_tags if t.get("tagid") and t.get("name")]

        # Platforms
        pinfo = raw.get("platforms", {})
        plats = []
        if pinfo.get("windows"):
            plats.append("windows")
        if pinfo.get("mac"):
            plats.append("mac")
        if pinfo.get("linux") or pinfo.get("steamos_linux"):
            plats.append("linux")

        # Languages (from supported_languages string)
        lang_str = basic.get("supported_languages", "")
        langs = []
        if lang_str:
            # Steam returns HTML like "English<strong>*</strong>, German, ..."
            cleaned = re.sub(r"<[^>]+>", "", lang_str)
            cleaned = cleaned.replace("*", "")
            langs = [lang.strip() for lang in cleaned.split(",") if lang.strip()]

        # Reviews
        reviews = raw.get("reviews", {})
        rscore = reviews.get("summary_filtered", {}).get("review_score", 0)
        rdesc = reviews.get("summary_filtered", {}).get("review_score_label", "")

        # Description
        full_desc = raw.get("full_description", "")
        short_desc = raw.get("short_description", "")

        # Age Ratings
        ratings = []
        rr = raw.get("ratings", [])
        if isinstance(rr, list):
            for re_ in rr:
                system = re_.get("rating_system", "")
                rv = re_.get("rating", "")
                if system and rv:
                    ratings.append((system, str(rv)))
        elif isinstance(rr, dict):
            for system, data in rr.items():
                if isinstance(data, dict):
                    rv = data.get("rating", "")
                    if rv:
                        ratings.append((system.upper(), str(rv)))

        # DLC / Included Items
        dlcs = []
        items = raw.get("included_items", [])
        if isinstance(items, list):
            for item in items:
                item_id = item.get("appid", 0)
                if item_id:
                    dlcs.append(item_id)

        # Asset URLs
        aurls = []
        assets = raw.get("assets", {})
        if isinstance(assets, dict):
            for asset_type, asset_url in assets.items():
                if isinstance(asset_url, str) and asset_url:
                    aurls.append((asset_type, asset_url))

        return SteamAppDetails(
            app_id=app_id,
            name=name,
            developers=tuple(devs),
            publishers=tuple(pubs),
            steam_release_date=steam_release_date,
            original_release_date=original_release_date,
            genres=tuple(gens),
            tags=tuple(tlist),
            tag_ids=tuple(tid_pairs),
            platforms=tuple(plats),
            languages=tuple(langs),
            review_score=rscore,
            review_desc=rdesc,
            is_free=is_free,
            description=full_desc,
            short_description=short_desc,
            age_ratings=tuple(ratings),
            dlc_ids=tuple(dlcs),
            asset_urls=tuple(aurls),
        )
