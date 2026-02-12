"""Service for managing game assets (images, icons, logos).

This module provides the AssetService class which wraps SteamAssets functionality
for loading, saving, and managing game assets from local storage and Steam CDN.
"""

from __future__ import annotations

from pathlib import Path

from src.core.steam_assets import SteamAssets
from src.integrations.steamgrid_api import SteamGridDB

__all__ = ['AssetService']

class AssetService:
    """Service for managing game assets.

    Wraps SteamAssets static methods and provides integration with SteamGridDB
    for fetching custom images.

    Attributes:
        steamgrid: Optional SteamGridDB instance for fetching assets.
    """

    def __init__(self):
        """Initializes the AssetService.

        Creates a SteamGridDB instance if API key is configured.
        """
        self.steamgrid: SteamGridDB | None = None

        try:
            self.steamgrid = SteamGridDB()
        except (ValueError, AttributeError):
            # No API key configured or config not available
            pass

    @staticmethod
    def get_asset_path(app_id: str, asset_type: str) -> str:
        """Gets the path to a local asset or a URL as fallback.

        Searches for assets in the following order:
        1. Local Steam user config/grid directory
        2. Steam CDN URLs (fallback)

        Args:
            app_id: Steam app ID.
            asset_type: Type of asset ('grids', 'heroes', 'logos', 'icons').

        Returns:
            Local file path if asset exists locally, or Steam CDN URL as fallback.
        """
        return SteamAssets.get_asset_path(app_id, asset_type)

    @staticmethod
    def save_custom_image(app_id: str, asset_type: str, url_or_path: str) -> bool:
        """Saves a custom image for a game directly in Steam's grid folder.

        Downloads an image from a URL or copies it from a local path and saves it
        to Steam's grid directory with the correct filename so it appears in the
        Steam client.

        Args:
            app_id: Steam app ID.
            asset_type: Type of asset ('grids', 'heroes', 'logos', 'icons').
            url_or_path: Source URL (http/https) or local file path.

        Returns:
            True if the image was saved successfully, False otherwise.
        """
        return SteamAssets.save_custom_image(app_id, asset_type, url_or_path)

    @staticmethod
    def delete_custom_image(app_id: str, asset_type: str) -> bool:
        """Deletes a custom image for a game from Steam's grid folder.

        Removes the image file from Steam's grid directory. If the file doesn't
        exist, returns True (idempotent behavior).

        Args:
            app_id: Steam app ID.
            asset_type: Type of asset to delete ('grids', 'heroes', 'logos', 'icons').

        Returns:
            True if the image was deleted or didn't exist, False if an error occurred.
        """
        return SteamAssets.delete_custom_image(app_id, asset_type)

    @staticmethod
    def get_steam_grid_path() -> Path:
        """Returns the Steam grid directory path for the current user.

        Returns:
            Path to Steam's grid directory (userdata/<user_id>/config/grid/).

        Raises:
            ValueError: If Steam path is not configured or user not detected.
        """
        return SteamAssets.get_steam_grid_path()

    def fetch_images_from_steamgrid(self, steam_app_id: str, img_type: str) -> list:
        """Fetches all images of a specific type from SteamGridDB.

        Args:
            steam_app_id: Steam app ID.
            img_type: Type of image ('grids', 'heroes', 'logos', 'icons').

        Returns:
            List of image data dictionaries with metadata (url, dimensions, etc.).
            Returns empty list if SteamGridDB is not initialized or no images found.
        """
        if not self.steamgrid:
            return []

        return self.steamgrid.get_images_by_type(steam_app_id, img_type)

    def get_single_images_from_steamgrid(self, steam_app_id: str) -> dict:
        """Fetches a single image URL for each image type from SteamGridDB.

        This is a convenience method that returns one image per type for quick access.

        Args:
            steam_app_id: Steam app ID.

        Returns:
            Dictionary mapping image types to URLs. Returns empty dict if
            SteamGridDB is not initialized or game not found.
        """
        if not self.steamgrid:
            return {}

        return self.steamgrid.get_images_for_game(steam_app_id)
