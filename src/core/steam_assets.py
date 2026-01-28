"""
Steam Assets Manager
Handles retrieving, saving, and deleting local game assets (Grids, Heroes, Logos, Icons).
Supports custom images and WebP/Gif formats.
"""
import os
import shutil
import requests
from src.config import config
from src.utils.i18n import t


class SteamAssets:
    """
    Static manager class for Steam assets (images).
    """

    @staticmethod
    def get_asset_path(app_id: str, asset_type: str) -> str:
        """
        Returns path to local asset (custom or Steam cache) or URL as fallback.

        Args:
            app_id (str): The AppID of the game.
            asset_type (str): Type of asset ('grids', 'heroes', 'logos', 'icons').

        Returns:
            str: File path or URL.
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

        Args:
            app_id (str): The AppID.
            asset_type (str): Asset type.
            url_or_path (str): Source URL or local file path.

        Returns:
            bool: True on success.
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
        Deletes a custom image.

        Args:
            app_id (str): The AppID.
            asset_type (str): Asset type.
        """
        try:
            target_file = config.CACHE_DIR / 'images' / 'custom' / app_id / f'{asset_type}.png'
            if target_file.exists():
                os.remove(target_file)
                print(t('logs.steamgrid.deleted', path=target_file.name))
                return True
        except OSError as e:
            print(t('logs.steamgrid.delete_error', error=e))
        return False