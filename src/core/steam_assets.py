"""
Steam Assets Manager - Finds, Saves, and Deletes Custom Images
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
        # ... (Identisch zum vorherigen Code) ...
        # Damit ich nicht alles wiederholen muss:
        # Der obere Teil dieser Funktion bleibt exakt wie vorher.
        # Prüft erst lokal, dann Web.

        short_id, _ = config.get_detected_user()
        if config.STEAM_PATH and short_id:
            grid_dir = config.STEAM_PATH / 'userdata' / short_id / 'config' / 'grid'
            local_filename = ""
            if asset_type == 'grid':
                local_filename = f"p_{app_id}.jpg"
            elif asset_type == 'hero':
                local_filename = f"{app_id}_hero.jpg"
            elif asset_type == 'logo':
                local_filename = f"{app_id}_logo.png"
            elif asset_type == 'icon':
                local_filename = f"{app_id}_icon.jpg"

            if local_filename:
                local_path = grid_dir / local_filename
                if local_path.exists(): return str(local_path)
                if local_path.with_suffix('.png').exists(): return str(local_path.with_suffix('.png'))

        if asset_type == 'grid':
            return f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/library_600x900.jpg"
        elif asset_type == 'hero':
            return f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/library_hero.jpg"
        elif asset_type == 'logo':
            return f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/logo.png"
        elif asset_type == 'icon':
            return f"https://cdn.cloudflare.steamstatic.com/steamcommunity/public/images/apps/{app_id}/clienticon.jpg"
        return ""

    @staticmethod
    def save_custom_image(app_id: str, asset_type: str, image_url: str) -> bool:
        # ... (Identisch zum vorherigen Code) ...
        short_id, _ = config.get_detected_user()
        if not config.STEAM_PATH or not short_id: return False
        grid_dir = config.STEAM_PATH / 'userdata' / short_id / 'config' / 'grid'
        grid_dir.mkdir(parents=True, exist_ok=True)
        filename = ""
        if asset_type == 'grid':
            filename = f"p_{app_id}"
        elif asset_type == 'hero':
            filename = f"{app_id}_hero"
        elif asset_type == 'logo':
            filename = f"{app_id}_logo"
        elif asset_type == 'icon':
            filename = f"{app_id}_icon"
        else:
            return False
        try:
            response = requests.get(image_url, stream=True, timeout=10)
            if response.status_code == 200:
                ext = ".jpg"
                if "png" in image_url.lower() or asset_type == 'logo': ext = ".png"
                final_path = grid_dir / (filename + ext)
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
        """Löscht das benutzerdefinierte Bild, damit Steam das Original nutzt"""
        short_id, _ = config.get_detected_user()
        if not config.STEAM_PATH or not short_id: return False

        grid_dir = config.STEAM_PATH / 'userdata' / short_id / 'config' / 'grid'

        filenames = []
        # Wir müssen JPG und PNG prüfen und löschen
        if asset_type == 'grid':
            filenames = [f"p_{app_id}.jpg", f"p_{app_id}.png"]
        elif asset_type == 'hero':
            filenames = [f"{app_id}_hero.jpg", f"{app_id}_hero.png"]
        elif asset_type == 'logo':
            filenames = [f"{app_id}_logo.jpg", f"{app_id}_logo.png"]
        elif asset_type == 'icon':
            filenames = [f"{app_id}_icon.jpg", f"{app_id}_icon.png"]

        deleted = False
        for fname in filenames:
            path = grid_dir / fname
            if path.exists():
                try:
                    os.remove(path)
                    deleted = True
                except:
                    pass

        return deleted