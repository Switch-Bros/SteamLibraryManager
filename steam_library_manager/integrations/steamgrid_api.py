#
# steam_library_manager/integrations/steamgrid_api.py
# SteamGridDB API client for custom game artwork
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#
# FIXME: pagination logic is ugly

from __future__ import annotations

import logging

import requests

from steam_library_manager.config import config
from steam_library_manager.utils.i18n import t
from steam_library_manager.utils.timeouts import HTTP_TIMEOUT, HTTP_TIMEOUT_SHORT

logger = logging.getLogger("steamlibmgr.steamgrid")

__all__ = ["SteamGridDB"]


class SteamGridDB:
    """Client for SteamGridDB API."""

    BASE_URL = "https://www.steamgriddb.com/api/v2"

    def __init__(self):
        # read api key from config
        self.api_key = config.STEAMGRIDDB_API_KEY
        self.headers = {"Authorization": "Bearer %s" % self.api_key}

    def get_images_for_game(self, steam_app_id):
        # one image per type for quick access
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

    def get_images_by_type(self, steam_app_id, img_type: str):
        # fetch all images of one type, paginated
        if not self.api_key:
            return []

        game_id = self._get_game_id(steam_app_id)
        if not game_id:
            return []

        imgs = []  # short name
        page = 0

        while True:
            try:
                # nsfw='any' -> shows everything
                params = {"page": page, "nsfw": "any", "types": "static,animated"}

                if img_type == "grids":
                    params["dimensions"] = "600x900,342x482"

                url = "%s/%s/game/%s" % (self.BASE_URL, img_type, game_id)
                resp = requests.get(url, headers=self.headers, params=params, timeout=HTTP_TIMEOUT)

                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("success") and data.get("data"):
                        batch = data["data"]
                        imgs.extend(batch)

                        # steamgriddb does 20 per page
                        if len(batch) < 20:
                            break
                        page += 1
                    else:
                        break
                else:
                    logger.error(t("logs.steamgrid.api_error", code=resp.status_code, page=page))
                    break

            except (requests.RequestException, ValueError, KeyError) as e:
                logger.error(t("logs.steamgrid.exception", error=str(e)))
                break

        logger.info(t("logs.steamgrid.found", count=len(imgs)))
        return imgs

    def get_images_by_type_paged(self, steam_app_id: str | int, img_type, page=0, limit=24):
        # single page of images - used by grid view
        if not self.api_key:
            return []

        game_id = self._get_game_id(steam_app_id)
        if not game_id:
            return []

        try:
            params = {
                "page": page,
                "nsfw": "any",
                "types": "static,animated",
                "limit": limit,
            }

            if img_type == "grids":
                params["dimensions"] = "600x900,342x482"

            url = "%s/%s/game/%s" % (self.BASE_URL, img_type, game_id)
            resp = requests.get(url, headers=self.headers, params=params, timeout=HTTP_TIMEOUT)

            if resp.status_code == 200:
                data = resp.json()
                if data.get("success") and data.get("data"):
                    return data["data"]

            return []

        except (requests.RequestException, ValueError, KeyError) as e:
            logger.error(t("logs.steamgrid.exception", error=str(e)))
            return []

    def _get_game_id(self, steam_app_id: str | int) -> int | None:
        # steam app id -> steamgriddb game id
        # TODO: cache this lookup?
        try:
            url = "%s/games/steam/%s" % (self.BASE_URL, steam_app_id)
            response = requests.get(url, headers=self.headers, timeout=HTTP_TIMEOUT_SHORT)
            if response.status_code == 200:
                data = response.json()
                if data["success"]:
                    return data["data"]["id"]
        except (requests.RequestException, ValueError, KeyError):
            pass
        return None

    def _fetch_single_url(self, game_id: int, endpoint, params=None):
        # grab first image url for endpoint
        try:
            url = "%s/%s/game/%s" % (self.BASE_URL, endpoint, game_id)
            response = requests.get(url, headers=self.headers, params=params, timeout=HTTP_TIMEOUT_SHORT)
            if response.status_code == 200:
                data = response.json()
                if data["success"] and data["data"]:
                    return data["data"][0]["url"]
        except (requests.RequestException, ValueError, KeyError):
            pass
        return None
