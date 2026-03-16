#
# steam_library_manager/services/asset_service.py
# Game asset management - local grid files, Steam CDN, and SteamGridDB
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from pathlib import Path

from steam_library_manager.core.steam_assets import SteamAssets
from steam_library_manager.integrations.steamgrid_api import SteamGridDB

__all__ = ["AssetService"]


class AssetService:
    """Wraps SteamAssets and SteamGridDB for asset loading and saving."""

    def __init__(self):

        self.steamgrid: SteamGridDB | None = None

        try:
            self.steamgrid = SteamGridDB()
        except (ValueError, AttributeError):
            # No API key configured or config not available
            pass

    @staticmethod
    def get_asset_path(app_id: str, asset_type: str) -> str:
        """Return local asset path, falling back to Steam CDN URL."""
        return SteamAssets.get_asset_path(app_id, asset_type)

    @staticmethod
    def save_custom_image(app_id: str, asset_type: str, url_or_path: str) -> bool:
        """Save a custom image to Steam's grid folder from URL or local path."""
        return SteamAssets.save_custom_image(app_id, asset_type, url_or_path)

    @staticmethod
    def delete_custom_image(app_id: str, asset_type: str) -> bool:
        """Delete a custom image from Steam's grid folder (idempotent)."""
        return SteamAssets.delete_custom_image(app_id, asset_type)

    @staticmethod
    def get_steam_grid_path() -> Path:
        """Return Steam's grid directory path. Raises ValueError if unconfigured."""
        return SteamAssets.get_steam_grid_path()

    def fetch_images_from_steamgrid(self, steam_app_id: str, img_type: str) -> list:
        """Fetch all images of a given type from SteamGridDB."""
        if not self.steamgrid:
            return []

        return self.steamgrid.get_images_by_type(steam_app_id, img_type)

    def get_single_images_from_steamgrid(self, steam_app_id: str) -> dict:
        """Fetch one image URL per type from SteamGridDB."""
        if not self.steamgrid:
            return {}

        return self.steamgrid.get_images_for_game(steam_app_id)
