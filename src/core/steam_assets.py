"""
Steam Assets Manager (WebP/Gif Support)
Speichern als: src/core/steam_assets.py
"""
from pathlib import Path
import requests
import shutil
import os
from src.config import config
from src.utils.i18n import t


class SteamAssets:

    @staticmethod
    def get_asset_path(app_id: str, asset_type: str) -> str:
        short_id, _ = config.get_detected_user()
        if config.STEAM_PATH and short_id:
            grid_dir = config.STEAM_PATH / 'userdata' / short_id / 'config' / 'grid'
            local_filename_base = ""

            if asset_type == 'grids':
                local_filename_base = f"p_{app_id}"
            elif asset_type == 'heroes':
                local_filename_base = f"{app_id}_hero"
            elif asset_type == 'logos':
                local_filename_base = f"{app_id}_logo"
            elif asset_type == 'icons':
                local_filename_base = f"{app_id}_icon"

            if local_filename_base:
                # Wir prüfen alle möglichen Extensions, Priorität auf Custom Formate
                for ext in ['.jpg', '.png', '.webp', '.gif']:
                    local_path = grid_dir / (local_filename_base + ext)
                    if local_path.exists():
                        return str(local_path)

        # Web Fallbacks (Standard Steam URLS sind meist JPG oder PNG)
        if asset_type == 'grids':
            return f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/library_600x900.jpg"
        elif asset_type == 'heroes':
            return f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/library_hero.jpg"
        elif asset_type == 'logos':
            return f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/logo.png"
        elif asset_type == 'icons':
            return f"https://cdn.cloudflare.steamstatic.com/steamcommunity/public/images/apps/{app_id}/clienticon.jpg"
        return ""

    @staticmethod
    def save_custom_image(app_id: str, asset_type: str, image_url: str) -> bool:
        short_id, _ = config.get_detected_user()
        if not config.STEAM_PATH or not short_id: return False
        grid_dir = config.STEAM_PATH / 'userdata' / short_id / 'config' / 'grid'
        grid_dir.mkdir(parents=True, exist_ok=True)

        filename_base = ""
        if asset_type == 'grids':
            filename_base = f"p_{app_id}"
        elif asset_type == 'heroes':
            filename_base = f"{app_id}_hero"
        elif asset_type == 'logos':
            filename_base = f"{app_id}_logo"
        elif asset_type == 'icons':
            filename_base = f"{app_id}_icon"
        else:
            return False

        # WICHTIG: Vorher alte Dateien löschen (damit nicht JPG und PNG gleichzeitig existieren)
        SteamAssets.delete_custom_image(app_id, asset_type)

        try:
            response = requests.get(image_url, stream=True, timeout=15)
            if response.status_code == 200:
                # Extension bestimmen
                url_lower = image_url.lower()
                ext = ".jpg"  # Default

                if ".png" in url_lower:
                    ext = ".png"
                elif ".webp" in url_lower:
                    ext = ".webp"  # NEU
                elif ".gif" in url_lower:
                    ext = ".gif"  # NEU
                # Sonderfall Logo: Steam bevorzugt PNG, aber wir speichern was wir kriegen

                final_path = grid_dir / (filename_base + ext)
                with open(final_path, 'wb') as f:
                    response.raw.decode_content = True
                    shutil.copyfileobj(response.raw, f)
                print(t('logs.steamgrid.saved', type=asset_type, app_id=app_id))
                return True
        except Exception as e:
            print(t('logs.steamgrid.save_error', error=e))
            return False
        return False

    @staticmethod
    def delete_custom_image(app_id: str, asset_type: str) -> bool:
        short_id, _ = config.get_detected_user()
        if not config.STEAM_PATH or not short_id: return False
        grid_dir = config.STEAM_PATH / 'userdata' / short_id / 'config' / 'grid'

        # Alle möglichen Extensions prüfen
        bases = []
        if asset_type == 'grids':
            bases = [f"p_{app_id}"]
        elif asset_type == 'heroes':
            bases = [f"{app_id}_hero"]
        elif asset_type == 'logos':
            bases = [f"{app_id}_logo"]
        elif asset_type == 'icons':
            bases = [f"{app_id}_icon"]

        extensions = ['.jpg', '.png', '.webp', '.gif', '.jpeg']

        deleted = False
        for base in bases:
            for ext in extensions:
                path = grid_dir / (base + ext)
                if path.exists():
                    try:
                        os.remove(path); deleted = True
                    except:
                        pass
        return deleted