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
        description: Full game description text.
        short_description: Short description / tagline.
        age_ratings: Tuple of (rating_system, rating) pairs (e.g. ("PEGI", "16")).
        dlc_ids: Tuple of DLC app IDs included with this game.
        asset_urls: Tuple of (asset_type, url) pairs for library assets.
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
    description: str = ""
    short_description: str = ""
    age_ratings: tuple[tuple[str, str], ...] = ()
    dlc_ids: tuple[int, ...] = ()
    asset_urls: tuple[tuple[str, str], ...] = ()


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
            cleaned = cleaned.replace("*", "")
            languages_list = [lang.strip() for lang in cleaned.split(",") if lang.strip()]

        # Reviews
        reviews = raw.get("reviews", {})
        review_score = reviews.get("summary_filtered", {}).get("review_score", 0)
        review_desc = reviews.get("summary_filtered", {}).get("review_score_label", "")

        # Description
        full_desc = raw.get("full_description", "")
        short_desc = raw.get("short_description", "")

        # Age Ratings
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

        # DLC / Included Items
        dlc_ids_list: list[int] = []
        included_items = raw.get("included_items", [])
        if isinstance(included_items, list):
            for item in included_items:
                item_id = item.get("appid", 0)
                if item_id:
                    dlc_ids_list.append(item_id)

        # Asset URLs
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

    # ------------------------------------------------------------------
    # Tag Service Endpoints (Phase 6.2)
    # ------------------------------------------------------------------

    def fetch_tag_list(self, language: str = "german") -> dict[int, str]:
        """Fetches the complete tag list from Steam.

        Uses IStoreService/GetTagList/v1 to retrieve all known tags
        with localized names.

        Args:
            language: Language for tag names (e.g. "german", "english").

        Returns:
            Dict mapping tag_id to localized tag name.
        """
        url = "https://api.steampowered.com/IStoreService/GetTagList/v1/"
        params = {"key": self.api_key, "language": language}

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            tags = data.get("response", {}).get("tags", [])
            return {int(t.get("tagid", 0)): t.get("name", "") for t in tags if t.get("tagid")}
        except (requests.RequestException, ValueError, KeyError) as exc:
            logger.warning("GetTagList failed: %s", exc)
            return {}

    def fetch_localized_tag_names(self, tag_ids: list[int], language: str = "german") -> dict[int, str]:
        """Fetches localized names for specific tag IDs.

        Uses IStoreService/GetLocalizedNameForTags/v1.

        Args:
            tag_ids: List of tag IDs to resolve.
            language: Language for tag names.

        Returns:
            Dict mapping tag_id to localized name.
        """
        url = "https://api.steampowered.com/IStoreService/GetLocalizedNameForTags/v1/"
        params: dict[str, Any] = {"key": self.api_key, "language": language}
        for i, tid in enumerate(tag_ids):
            params[f"tagids[{i}]"] = tid

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            tags = data.get("response", {}).get("tags", [])
            return {int(t.get("tagid", 0)): t.get("name", "") for t in tags if t.get("tagid")}
        except (requests.RequestException, ValueError, KeyError) as exc:
            logger.warning("GetLocalizedNameForTags failed: %s", exc)
            return {}

    # ------------------------------------------------------------------
    # Achievement Progress Endpoint (Phase 6.2)
    # ------------------------------------------------------------------

    def fetch_achievements_progress(self, steam_id: int, app_ids: list[int]) -> dict[int, dict]:
        """Fetches achievement progress for multiple apps.

        Uses IPlayerService/GetAchievementsProgress/v1 with array params.

        Args:
            steam_id: 64-bit Steam user ID.
            app_ids: List of app IDs to query.

        Returns:
            Dict mapping app_id to progress dict with 'unlocked' and 'total'.
        """
        url = "https://api.steampowered.com/IPlayerService/GetAchievementsProgress/v1/"
        params: dict[str, Any] = {"key": self.api_key, "steamid": steam_id}
        for i, aid in enumerate(app_ids):
            params[f"appids[{i}]"] = aid

        try:
            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 404:
                logger.debug("GetAchievementsProgress: endpoint not available")
                return {}
            response.raise_for_status()
            data = response.json()
            progress_list = data.get("response", {}).get("achievement_progress", [])
            result: dict[int, dict] = {}
            for entry in progress_list:
                aid = entry.get("appid", 0)
                if aid:
                    result[aid] = {
                        "unlocked": entry.get("unlocked", 0),
                        "total": entry.get("total", 0),
                        "percentage": entry.get("percentage", 0.0),
                    }
            return result
        except (requests.RequestException, ValueError, KeyError) as exc:
            logger.warning("GetAchievementsProgress failed: %s", exc)
            return {}

    # ------------------------------------------------------------------
    # DLC Endpoint (Phase 6.2)
    # ------------------------------------------------------------------

    def fetch_dlc_for_apps(self, app_ids: list[int]) -> dict[int, list[int]]:
        """Fetches DLC app IDs for multiple games.

        Uses IStoreBrowseService/GetDLCForApps/v1.

        Args:
            app_ids: List of base game app IDs.

        Returns:
            Dict mapping base app_id to list of DLC app IDs.
        """
        url = "https://api.steampowered.com/IStoreBrowseService/GetDLCForApps/v1/"
        input_data = json.dumps({"appids": [{"appid": aid} for aid in app_ids]})
        params = {"key": self.api_key, "input_json": input_data}

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            dlc_data = data.get("response", {}).get("dlc_data", [])
            result: dict[int, list[int]] = {}
            for entry in dlc_data:
                parent_id = entry.get("appid", 0)
                dlc_list = [d.get("appid", 0) for d in entry.get("dlc", []) if d.get("appid")]
                if parent_id and dlc_list:
                    result[parent_id] = dlc_list
            return result
        except (requests.RequestException, ValueError, KeyError) as exc:
            logger.warning("GetDLCForApps failed: %s", exc)
            return {}

    # ------------------------------------------------------------------
    # Popular Tags Endpoint (Phase 6.2)
    # ------------------------------------------------------------------

    def fetch_popular_tags(self, language: str = "german") -> list[dict]:
        """Fetches the most popular tags from Steam.

        Uses IStoreService/GetMostPopularTags/v1.

        Args:
            language: Language for tag names.

        Returns:
            List of dicts with 'tagid' and 'name' keys.
        """
        url = "https://api.steampowered.com/IStoreService/GetMostPopularTags/v1/"
        params = {"key": self.api_key, "language": language}

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get("response", {}).get("tags", [])
        except (requests.RequestException, ValueError, KeyError) as exc:
            logger.warning("GetMostPopularTags failed: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Private Apps Endpoints (Phase 6.2)
    # ------------------------------------------------------------------

    def fetch_private_app_list(self) -> list[int]:
        """Fetches the list of private (hidden) apps for the user.

        Uses IAccountPrivateAppsService/GetPrivateAppList/v1.

        Returns:
            List of app IDs that are set as private.
        """
        url = "https://api.steampowered.com/IAccountPrivateAppsService/GetPrivateAppList/v1/"
        params = {"key": self.api_key}

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            apps = data.get("response", {}).get("apps", [])
            return [a.get("appid", 0) for a in apps if a.get("appid")]
        except (requests.RequestException, ValueError, KeyError) as exc:
            logger.warning("GetPrivateAppList failed: %s", exc)
            return []

    def toggle_app_privacy(self, app_ids: list[int], private: bool) -> bool:
        """Toggles privacy status for apps.

        Uses IAccountPrivateAppsService/ToggleAppPrivacy/v1.

        Args:
            app_ids: List of app IDs to toggle.
            private: True to make private, False to make public.

        Returns:
            True on success, False on failure.
        """
        url = "https://api.steampowered.com/IAccountPrivateAppsService/ToggleAppPrivacy/v1/"
        data: dict[str, Any] = {
            "key": self.api_key,
            "private": private,
        }
        for i, aid in enumerate(app_ids):
            data[f"appids[{i}]"] = aid

        try:
            response = requests.post(url, data=data, timeout=30)
            response.raise_for_status()
            return True
        except (requests.RequestException, ValueError) as exc:
            logger.warning("ToggleAppPrivacy failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Client Communication Endpoints (Phase 6.2)
    # ------------------------------------------------------------------

    def fetch_client_app_list(
        self,
        fields: str = "games",
        filters: str = "installed",
        language: str = "german",
    ) -> list[dict]:
        """Fetches the client's app list.

        Uses IClientCommService/GetClientAppList/v1.

        Args:
            fields: Fields to include (e.g. "games").
            filters: Filter type (e.g. "installed").
            language: Language for localized data.

        Returns:
            List of app dicts from the client.
        """
        url = "https://api.steampowered.com/IClientCommService/GetClientAppList/v1/"
        params = {
            "key": self.api_key,
            "fields": fields,
            "filters": filters,
            "language": language,
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get("response", {}).get("apps", [])
        except (requests.RequestException, ValueError, KeyError) as exc:
            logger.warning("GetClientAppList failed: %s", exc)
            return []

    def fetch_client_info(self) -> dict:
        """Fetches information about the running Steam client.

        Uses IClientCommService/GetClientInfo/v1.

        Returns:
            Dict with client info, or empty dict on failure.
        """
        url = "https://api.steampowered.com/IClientCommService/GetClientInfo/v1/"
        params = {"key": self.api_key}

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get("response", {})
        except (requests.RequestException, ValueError, KeyError) as exc:
            logger.warning("GetClientInfo failed: %s", exc)
            return {}

    # ------------------------------------------------------------------
    # Wishlist Endpoint (Phase 6.2)
    # ------------------------------------------------------------------

    def fetch_wishlist(self, steam_id: int) -> list[dict]:
        """Fetches the user's Steam wishlist.

        Uses IWishlistService/GetWishlist/v1.

        Args:
            steam_id: 64-bit Steam user ID.

        Returns:
            List of wishlist item dicts with 'appid', 'priority', etc.
        """
        url = "https://api.steampowered.com/IWishlistService/GetWishlist/v1/"
        params: dict[str, Any] = {"key": self.api_key, "steamid": steam_id}

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get("response", {}).get("items", [])
        except (requests.RequestException, ValueError, KeyError) as exc:
            logger.warning("GetWishlist failed: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Reference Endpoints — Stubs for future use (Phase 6.2)
    # ------------------------------------------------------------------

    def fetch_game_notes(self, steam_id: int, app_id: int) -> list[dict]:
        """Stub: Fetches user game notes via IUserGameNotesService.

        Args:
            steam_id: 64-bit Steam user ID.
            app_id: Steam app ID.

        Returns:
            Empty list (not yet implemented).
        """
        logger.debug("fetch_game_notes: stub called for user %d, app %d", steam_id, app_id)
        return []

    def fetch_player_count(self, app_id: int) -> int:
        """Stub: Fetches current player count via ISteamChartsService.

        Args:
            app_id: Steam app ID.

        Returns:
            0 (not yet implemented).
        """
        logger.debug("fetch_player_count: stub called for app %d", app_id)
        return 0

    def fetch_family_group_info(self) -> dict:
        """Stub: Fetches family sharing info via IFamilyGroupsService.

        Returns:
            Empty dict (not yet implemented).
        """
        logger.debug("fetch_family_group_info: stub called")
        return {}

    def fetch_cloud_files(self, app_id: int) -> list[dict]:
        """Stub: Enumerates cloud save files via ICloudService/EnumerateUserFiles.

        Args:
            app_id: Steam app ID.

        Returns:
            Empty list (not yet implemented).
        """
        logger.debug("fetch_cloud_files: stub called for app %d", app_id)
        return []
