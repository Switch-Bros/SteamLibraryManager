# src/core/steam_assets.py

"""
Manages Steam game assets (images) for the library.

This module handles retrieving, saving, and deleting local game assets such as
grids, heroes, logos, and icons. It supports custom images and various formats
including WebP and GIF.

IMPORTANT: Images are now saved directly in Steam's grid folder so they appear
in the Steam client!
"""
from __future__ import annotations

import logging
import os
import shutil
import requests
from pathlib import Path
from src.config import config
from src.utils.i18n import t


logger = logging.getLogger("steamlibmgr.steam_assets")

__all__ = ["SteamAssets"]


class SteamAssets:
    """
    Static manager class for Steam game assets (images).

    This class provides methods to locate, save, and delete game images. It
    searches for custom images first, then checks Steam's local cache, and
    finally falls back to Steam's CDN URLs.
    """

    @staticmethod
    def get_steam_grid_path() -> Path:
        """
        Returns the Steam grid directory path for the current user.

        Returns:
            Path: Path to Steam's grid directory (userdata/<user_id>/config/grid/)
        """
        if not config.STEAM_PATH:
            raise ValueError("Steam path not configured")

        short_id, _ = config.get_detected_user()
        if not short_id:
            raise ValueError("Steam user not detected")

        grid_dir = config.STEAM_PATH / "userdata" / short_id / "config" / "grid"
        grid_dir.mkdir(parents=True, exist_ok=True)

        return grid_dir

    @staticmethod
    def get_asset_path(app_id: str, asset_type: str) -> str:
        """
        Returns the path to a local asset or a URL as fallback.

        This method searches for assets in the following order:
        1. Local Steam user config/grid directory (where Steam looks!)
        2. Steam CDN URLs (fallback)

        Args:
            app_id (str): The Steam app ID.
            asset_type (str): Type of asset to retrieve. Valid values are:
                             'grids', 'heroes', 'logos', 'icons'.

        Returns:
            str: A local file path if the asset exists locally, or a Steam CDN URL
                as fallback. Returns an empty string if the asset type is invalid.
        """

        short_id, _ = config.get_detected_user()

        # Try to find local image in Steam user config
        if config.STEAM_PATH and short_id:
            grid_dir = config.STEAM_PATH / "userdata" / short_id / "config" / "grid"

            # Determine base filename based on asset type
            filename_base = ""
            if asset_type == "grids":
                filename_base = f"{app_id}p"  # Grid = <app_id>p
            elif asset_type == "heroes":
                filename_base = f"{app_id}_hero"
            elif asset_type == "logos":
                filename_base = f"{app_id}_logo"
            elif asset_type == "icons":
                filename_base = f"{app_id}_icon"
            elif asset_type == "capsules":
                filename_base = f"{app_id}"  # Horizontal grid (no suffix)

            if filename_base:
                # Check all possible extensions
                for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]:
                    local_path = grid_dir / (filename_base + ext)
                    if local_path.exists():
                        return str(local_path)

        # Web Fallbacks (Standard Steam URLs)
        if asset_type == "grids":
            return f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/library_600x900.jpg"
        elif asset_type == "heroes":
            return f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/library_hero.jpg"
        elif asset_type == "logos":
            return f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/logo.png"

        return ""

    @staticmethod
    def save_custom_image(app_id: str, asset_type: str, url_or_path: str) -> bool:
        """
        Saves a custom image for a game DIRECTLY in Steam's grid folder.

        This method downloads an image from a URL or copies it from a local path
        and saves it to Steam's grid directory with the correct filename so it
        appears in the Steam client!

        Args:
            app_id (str): The Steam app ID.
            asset_type (str): The type of asset ('grids', 'heroes', 'logos', 'icons').
            url_or_path (str): Source URL (http/https) or local file path.

        Returns:
            bool: True if the image was saved successfully, False otherwise.
        """
        try:
            # Get Steam grid directory
            grid_dir = SteamAssets.get_steam_grid_path()

            # Determine correct filename for Steam
            if asset_type == "grids":
                filename = f"{app_id}p.png"  # Grid = <app_id>p.png
            elif asset_type == "heroes":
                filename = f"{app_id}_hero.png"
            elif asset_type == "logos":
                filename = f"{app_id}_logo.png"
            elif asset_type == "icons":
                filename = f"{app_id}_icon.png"  # Icon (PNG for consistency)
            elif asset_type == "capsules":
                filename = f"{app_id}.png"  # Horizontal grid (Big Picture)
            else:
                logger.info(t("logs.assets.unknown_type", type=asset_type))
                return False

            target_file = grid_dir / filename

            # Download URL
            if str(url_or_path).startswith("http"):
                headers = {"User-Agent": "SteamLibraryManager/1.0"}
                response = requests.get(url_or_path, headers=headers, timeout=10)
                if response.status_code == 200:
                    with open(target_file, "wb") as f:
                        f.write(response.content)
                    logger.info(t("logs.steamgrid.saved", type=asset_type, app_id=app_id))
                    logger.info(t("logs.assets.saved_to", path=target_file))
                    return True

            # Copy local file
            elif os.path.exists(url_or_path):
                shutil.copy2(url_or_path, target_file)
                logger.info(t("logs.steamgrid.saved", type=asset_type, app_id=app_id))
                logger.info(t("logs.assets.saved_to", path=target_file))
                return True

        except (OSError, requests.RequestException, ValueError) as e:
            logger.error(t("logs.steamgrid.save_error", error=e))
            return False

        return False

    @staticmethod
    def delete_custom_image(app_id: str, asset_type: str) -> bool:
        """
        Deletes a custom image for a game from Steam's grid folder.

        This method removes the image file from Steam's grid directory. If the
        file doesn't exist, it returns True (idempotent behavior).

        Args:
            app_id (str): The Steam app ID.
            asset_type (str): The type of asset to delete ('grids', 'heroes', 'logos', 'icons').

        Returns:
            bool: True if the image was deleted or didn't exist, False if an error occurred.
        """
        try:
            # Get Steam grid directory
            grid_dir = SteamAssets.get_steam_grid_path()

            # Determine correct filename
            if asset_type == "grids":
                filename = f"{app_id}p.png"
            elif asset_type == "heroes":
                filename = f"{app_id}_hero.png"
            elif asset_type == "logos":
                filename = f"{app_id}_logo.png"
            elif asset_type == "icons":
                filename = f"{app_id}_icon.png"  # Changed to .png
            elif asset_type == "capsules":
                filename = f"{app_id}.png"  # New: horizontal grid
            else:
                return False

            target_file = grid_dir / filename

            if target_file.exists():
                os.remove(target_file)
                logger.info(t("logs.steamgrid.deleted", path=target_file.name))
                return True
            # Return True even if file didn't exist (idempotent)
            return True
        except (OSError, ValueError) as e:
            logger.error(t("logs.steamgrid.delete_error", error=e))
            return False
