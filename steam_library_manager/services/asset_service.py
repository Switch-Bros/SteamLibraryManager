#
# steam_library_manager/services/asset_service.py
# Game artwork fetching and caching
#
# Copyright 2025 SwitchBros
# MIT License
#

from __future__ import annotations

from steam_library_manager.core.steam_assets import SteamAssets
from steam_library_manager.integrations.steamgrid_api import SteamGridDB

__all__ = ["AssetService"]


class AssetService:
    """Asset svc wrapper."""

    def __init__(self):
        self.steamgrid = None
        try:
            self.steamgrid = SteamGridDB()
        except (ValueError, AttributeError):
            pass  # no key

    @staticmethod
    def get_asset_path(aid, at):
        return SteamAssets.get_asset_path(aid, at)

    @staticmethod
    def save_custom_image(aid, at, pth):
        return SteamAssets.save_custom_image(aid, at, pth)

    @staticmethod
    def delete_custom_image(aid, at):
        return SteamAssets.delete_custom_image(aid, at)

    @staticmethod
    def get_steam_grid_path():
        return SteamAssets.get_steam_grid_path()

    def fetch_images_from_steamgrid(self, aid, it):
        # TODO: this is ugly, refactor later
        if not self.steamgrid:
            return []
        return self.steamgrid.get_images_by_type(aid, it)

    def get_single_images_from_steamgrid(self, aid):
        if not self.steamgrid:
            return {}
        return self.steamgrid.get_images_for_game(aid)
