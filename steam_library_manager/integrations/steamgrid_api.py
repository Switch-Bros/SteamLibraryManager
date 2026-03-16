#
# steam_library_manager/integrations/steamgrid_api.py
# SteamGridDB API client with pagination support
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
from typing import Any

import requests

from steam_library_manager.config import config
from steam_library_manager.utils.i18n import t
from steam_library_manager.utils.timeouts import HTTP_TIMEOUT, HTTP_TIMEOUT_SHORT

logger = logging.getLogger("steamlibmgr.steamgrid")

__all__ = ["SteamGridDB"]


class SteamGridDB:
    """Client for the SteamGridDB API."""

    BASE_URL = "https://www.steamgriddb.com/api/v2"

    def __init__(self):
        self.api_key = config.STEAMGRIDDB_API_KEY
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    def get_images_for_game(self, steam_app_id: str | int) -> dict[str, str | None]:
        """Fetch a single image URL for each image type (grids, heroes, logos, icons)."""
        if not self.api_key:
            return {}
        game_id = self._get_game_id(steam_app_id)
        if not game_id:
            return {}

        return {
            "grids": self._fetch_single_url(game_id, "grids", {"dimensions": "600x900,342x482"}),
            "heroes": self._fetch_single_url(game_id, "heroes"),
            "logos": self._fetch_single_url(game_id, "logos"),
            "icons": self._fetch_single_url(game_id, "icons"),
        }

    def get_images_by_type(self, steam_app_id: str | int, img_type: str) -> list[dict[str, Any]]:
        """Fetch all images of a specific type across all pages."""
        if not self.api_key:
            return []

        game_id = self._get_game_id(steam_app_id)
        if not game_id:
            return []

        all_images = []
        page = 0

        while True:
            try:
                params: dict[str, Any] = {"page": page, "nsfw": "any", "types": "static,animated"}

                if img_type == "grids":
                    params["dimensions"] = "600x900,342x482"

                url = f"{self.BASE_URL}/{img_type}/game/{game_id}"
                response = requests.get(url, headers=self.headers, params=params, timeout=HTTP_TIMEOUT)

                if response.status_code == 200:
                    data = response.json()
                    if data.get("success") and data.get("data"):
                        new_images = data["data"]
                        all_images.extend(new_images)

                        # If less than 20 results, it was the last page
                        if len(new_images) < 20:
                            break
                        page += 1
                    else:
                        break
                else:
                    logger.error(t("logs.steamgrid.api_error", code=response.status_code, page=page))
                    break

            except (requests.RequestException, ValueError, KeyError) as e:
                logger.error(t("logs.steamgrid.exception", error=str(e)))
                break

        logger.info(t("logs.steamgrid.found", count=len(all_images)))
        return all_images

    def get_images_by_type_paged(
        self,
        steam_app_id: str | int,
        img_type: str,
        page: int = 0,
        limit: int = 24,
    ) -> list[dict[str, Any]]:
        """Fetch one page of images from SteamGridDB."""
        if not self.api_key:
            return []

        game_id = self._get_game_id(steam_app_id)
        if not game_id:
            return []

        try:
            params: dict[str, Any] = {
                "page": page,
                "nsfw": "any",
                "types": "static,animated",
                "limit": limit,
            }

            if img_type == "grids":
                params["dimensions"] = "600x900,342x482"

            url = f"{self.BASE_URL}/{img_type}/game/{game_id}"
            response = requests.get(url, headers=self.headers, params=params, timeout=HTTP_TIMEOUT)

            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("data"):
                    return data["data"]

            return []

        except (requests.RequestException, ValueError, KeyError) as e:
            logger.error(t("logs.steamgrid.exception", error=str(e)))
            return []

    def _get_game_id(self, steam_app_id: str | int) -> int | None:
        """Resolve a Steam app ID to a SteamGridDB game ID."""
        try:
            url = f"{self.BASE_URL}/games/steam/{steam_app_id}"
            response = requests.get(url, headers=self.headers, timeout=HTTP_TIMEOUT_SHORT)
            if response.status_code == 200:
                data = response.json()
                if data["success"]:
                    return data["data"]["id"]
        except (requests.RequestException, ValueError, KeyError):
            pass
        return None

    def _fetch_single_url(self, game_id: int, endpoint: str, params: dict[str, Any] | None = None) -> str | None:
        """Fetch a single image URL for a specific endpoint."""
        try:
            url = f"{self.BASE_URL}/{endpoint}/game/{game_id}"
            response = requests.get(url, headers=self.headers, params=params, timeout=HTTP_TIMEOUT_SHORT)
            if response.status_code == 200:
                data = response.json()
                if data["success"] and data["data"]:
                    return data["data"][0]["url"]
        except (requests.RequestException, ValueError, KeyError):
            pass
        return None
