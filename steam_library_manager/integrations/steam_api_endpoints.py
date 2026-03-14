#
# steam_library_manager/integrations/steam_api_endpoints.py
# Steam Web API endpoint methods (tags, achievements, DLC, privacy, wishlist)
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import json
import logging
from typing import Any

import requests

logger = logging.getLogger("steamlibmgr.steam_web_api")

__all__ = ["SteamAPIEndpoints"]


class SteamAPIEndpoints:
    """Base class providing Steam Web API endpoint methods.

    Subclassed by SteamWebAPI which sets ``api_key`` in its ``__init__``.
    """

    api_key: str

    def _call_api(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        *,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Makes a Steam API request with standard error handling."""
        try:
            if method == "POST":
                response = requests.post(url, data=data, timeout=30)
            else:
                response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError, KeyError) as exc:
            endpoint_name = url.rsplit("/", 2)[-2] if "/" in url else url
            logger.warning("%s failed: %s", endpoint_name, exc)
            return None

    # Tag endpoints

    def fetch_tag_list(self, language: str = "german") -> dict[int, str]:
        """Fetches the complete tag list via IStoreService/GetTagList."""
        url = "https://api.steampowered.com/IStoreService/GetTagList/v1/"
        params = {"key": self.api_key, "language": language}

        data = self._call_api(url, params)
        if data is None:
            return {}
        tags = data.get("response", {}).get("tags", [])
        return {int(t.get("tagid", 0)): t.get("name", "") for t in tags if t.get("tagid")}

    def fetch_localized_tag_names(self, tag_ids: list[int], language: str = "german") -> dict[int, str]:
        """Resolves tag IDs to localized names via GetLocalizedNameForTags."""
        url = "https://api.steampowered.com/IStoreService/GetLocalizedNameForTags/v1/"
        params: dict[str, Any] = {"key": self.api_key, "language": language}
        for i, tid in enumerate(tag_ids):
            params[f"tagids[{i}]"] = tid

        data = self._call_api(url, params)
        if data is None:
            return {}
        tags = data.get("response", {}).get("tags", [])
        return {int(t.get("tagid", 0)): t.get("name", "") for t in tags if t.get("tagid")}

    def fetch_popular_tags(self, language: str = "german") -> list[dict]:
        """Fetches most popular tags via IStoreService/GetMostPopularTags."""
        url = "https://api.steampowered.com/IStoreService/GetMostPopularTags/v1/"
        params = {"key": self.api_key, "language": language}

        data = self._call_api(url, params)
        return data.get("response", {}).get("tags", []) if data else []

    # Achievement endpoint

    def fetch_achievements_progress(self, steam_id: int, app_ids: list[int]) -> dict[int, dict]:
        """Fetches achievement progress for multiple apps via GetAchievementsProgress."""
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

    # DLC endpoint

    def fetch_dlc_for_apps(self, app_ids: list[int]) -> dict[int, list[int]]:
        """Fetches DLC app IDs for multiple games via GetDLCForApps."""
        url = "https://api.steampowered.com/IStoreBrowseService/GetDLCForApps/v1/"
        input_data = json.dumps({"appids": [{"appid": aid} for aid in app_ids]})
        params = {"key": self.api_key, "input_json": input_data}

        data = self._call_api(url, params)
        if data is None:
            return {}
        dlc_data = data.get("response", {}).get("dlc_data", [])
        result: dict[int, list[int]] = {}
        for entry in dlc_data:
            parent_id = entry.get("appid", 0)
            dlc_list = [d.get("appid", 0) for d in entry.get("dlc", []) if d.get("appid")]
            if parent_id and dlc_list:
                result[parent_id] = dlc_list
        return result

    # Private apps endpoints

    def fetch_private_app_list(self) -> list[int]:
        """Fetches the list of private (hidden) apps via GetPrivateAppList."""
        url = "https://api.steampowered.com/IAccountPrivateAppsService/GetPrivateAppList/v1/"
        params = {"key": self.api_key}

        data = self._call_api(url, params)
        if data is None:
            return []
        apps = data.get("response", {}).get("apps", [])
        return [a.get("appid", 0) for a in apps if a.get("appid")]

    def toggle_app_privacy(self, app_ids: list[int], private: bool) -> bool:
        """Toggles privacy status for apps via ToggleAppPrivacy."""
        url = "https://api.steampowered.com/IAccountPrivateAppsService/ToggleAppPrivacy/v1/"
        post_data: dict[str, Any] = {
            "key": self.api_key,
            "private": private,
        }
        for i, aid in enumerate(app_ids):
            post_data[f"appids[{i}]"] = aid

        result = self._call_api(url, method="POST", data=post_data)
        return result is not None

    # Client communication endpoints

    def fetch_client_app_list(
        self,
        fields: str = "games",
        filters: str = "installed",
        language: str = "german",
    ) -> list[dict]:
        """Fetches the client's app list via GetClientAppList."""
        url = "https://api.steampowered.com/IClientCommService/GetClientAppList/v1/"
        params = {
            "key": self.api_key,
            "fields": fields,
            "filters": filters,
            "language": language,
        }

        data = self._call_api(url, params)
        return data.get("response", {}).get("apps", []) if data else []

    def fetch_client_info(self) -> dict:
        """Fetches info about the running Steam client via GetClientInfo."""
        url = "https://api.steampowered.com/IClientCommService/GetClientInfo/v1/"
        params = {"key": self.api_key}

        data = self._call_api(url, params)
        return data.get("response", {}) if data else {}

    # Wishlist endpoint

    def fetch_wishlist(self, steam_id: int) -> list[dict]:
        """Fetches the user's Steam wishlist via GetWishlist."""
        url = "https://api.steampowered.com/IWishlistService/GetWishlist/v1/"
        params: dict[str, Any] = {"key": self.api_key, "steamid": steam_id}

        data = self._call_api(url, params)
        return data.get("response", {}).get("items", []) if data else []

    # Stubs for future use

    def fetch_game_notes(self, steam_id: int, app_id: int) -> list[dict]:
        """Stub for IUserGameNotesService - not yet implemented."""
        logger.debug("fetch_game_notes: stub called for user %d, app %d", steam_id, app_id)
        return []

    def fetch_player_count(self, app_id: int) -> int:
        """Stub for ISteamChartsService - not yet implemented."""
        logger.debug("fetch_player_count: stub called for app %d", app_id)
        return 0

    def fetch_family_group_info(self) -> dict:
        """Stub for IFamilyGroupsService - not yet implemented."""
        logger.debug("fetch_family_group_info: stub called")
        return {}

    def fetch_cloud_files(self, app_id: int) -> list[dict]:
        """Stub for ICloudService/EnumerateUserFiles - not yet implemented."""
        logger.debug("fetch_cloud_files: stub called for app %d", app_id)
        return []
