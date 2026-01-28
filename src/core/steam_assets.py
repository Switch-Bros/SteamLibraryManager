# src/core/steam_assets.py

"""
Manages Steam game assets (images) for the library.

This module handles retrieving, saving, and deleting local game assets such as
grids, heroes, logos, and icons. It supports custom images and various formats
including WebP and GIF.
"""
import os
import shutil
import requests
from src.config import config
from src.utils.i18n import t


class SteamAssets:
    """
    Static manager class for Steam game assets (images).

    This class provides methods to locate, save, and delete game images. It
    searches for custom images first, then checks Steam's local cache, and
    finally falls back to Steam's CDN URLs.
    """

    @staticmethod
    def get_asset_path(app_id: str, asset_type: str) -> str:
        """
        Returns the path to a local asset or a URL as fallback.

        This method searches for assets in the following order:
        1. Custom images in the cache directory
        2. Local Steam user config/grid directory
        3. Steam CDN URLs (fallback)

        Args:
            app_id (str): The Steam app ID.
            asset_type (str): Type of asset to retrieve. Valid values are:
                             'grids', 'heroes', 'logos', 'icons'.

        Returns:
            str: A local file path if the asset exists locally, or a Steam CDN URL
                as fallback. Returns an empty string if the asset type is invalid.
        """

        # 1. Custom Image Check
        custom_dir = config.CACHE_DIR / 'images' / 'custom' / app_id
        custom_file = custom_dir / f'{asset_type}.png'
        if custom_file.exists():
            return str(custom_file)

        short_id, _ = config.get_detected_user()

        # 2. Try to find local image in Steam user config
        if config.STEAM_PATH and short_id:
            grid_dir = config.STEAM_PATH / 'userdata' / short_id / 'config' / 'grid'

            # Determine base filename based on asset type
            filename_base = ""
            if asset_type == 'grids':
                filename_base = f"p_{app_id}"
            elif asset_type == 'heroes':
                filename_base = f"{app_id}_hero"
            elif asset_type == 'logos':
                filename_base = f"{app_id}_logo"
            elif asset_type == 'icons':
                filename_base = f"{app_id}_icon"

            if filename_base:
                # Check all possible extensions
                for ext in ['.png', '.jpg', '.jpeg', '.webp', '.gif']:
                    local_path = grid_dir / (filename_base + ext)
                    if local_path.exists():
                        return str(local_path)

        # 3. Web Fallbacks (Standard Steam URLs)
        if asset_type == 'grids':
            return f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/library_600x900.jpg"
        elif asset_type == 'heroes':
            return f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/library_hero.jpg"
        elif asset_type == 'logos':
            return f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/logo.png"

        return ""

    @staticmethod
    def save_custom_image(app_id: str, asset_type: str, url_or_path: str) -> bool:
        """
        Saves a custom image for a game.

        This method downloads an image from a URL or copies it from a local path
        and saves it to the custom images directory. The image is always saved
        as a PNG file.

        Args:
            app_id (str): The Steam app ID.
            asset_type (str): The type of asset ('grids', 'heroes', 'logos', 'icons').
            url_or_path (str): Source URL (http/https) or local file path.

        Returns:
            bool: True if the image was saved successfully, False otherwise.
        """
        try:
            target_dir = config.CACHE_DIR / 'images' / 'custom' / app_id
            target_dir.mkdir(parents=True, exist_ok=True)
            target_file = target_dir / f'{asset_type}.png'

            # Download URL
            if str(url_or_path).startswith('http'):
                headers = {'User-Agent': 'SteamLibraryManager/1.0'}
                response = requests.get(url_or_path, headers=headers, timeout=10)
                if response.status_code == 200:
                    with open(target_file, 'wb') as f:
                        f.write(response.content)
                    print(t('logs.steamgrid.saved', type=asset_type, app_id=app_id))
                    return True

            # Copy local file
            elif os.path.exists(url_or_path):
                shutil.copy2(url_or_path, target_file)
                print(t('logs.steamgrid.saved', type=asset_type, app_id=app_id))
                return True

        except (OSError, requests.RequestException) as e:
            print(t('logs.steamgrid.save_error', error=e))
            return False

        return False

    @staticmethod
    def delete_custom_image(app_id: str, asset_type: str) -> bool:
        """
        Deletes a custom image for a game.

        This method removes the custom image file from the cache directory. If the
        file doesn't exist, it returns True (idempotent behavior).

        Args:
            app_id (str): The Steam app ID.
            asset_type (str): The type of asset to delete ('grids', 'heroes', 'logos', 'icons').

        Returns:
            bool: True if the image was deleted or didn't exist, False if an error occurred.
        """
        try:
            target_file = config.CACHE_DIR / 'images' / 'custom' / app_id / f'{asset_type}.png'
            if target_file.exists():
                os.remove(target_file)
                print(t('logs.steamgrid.deleted', path=target_file.name))
                return True
            # Return True even if file didn't exist (idempotent)
            return True
        except OSError as e:
            print(t('logs.steamgrid.delete_error', error=e))
            return False
