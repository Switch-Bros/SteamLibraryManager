"""
Steam Assets Manager (WebP/Gif Support)
Speichern als: src/core/steam_assets.py
"""
import os
import requests
from src.config import config
from src.utils.i18n import t


class SteamAssets:

    @staticmethod
    def get_asset_path(app_id: str, asset_type: str) -> str:
        """Gibt den Pfad zum lokalen Asset zurück oder die URL als Fallback"""
        short_id, _ = config.get_detected_user()

        # 1. Versuche lokales Bild zu finden
        if config.STEAM_PATH and short_id:
            grid_dir = config.STEAM_PATH / 'userdata' / short_id / 'config' / 'grid'

            # Bestimme den Basis-Dateinamen
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
                # Prüfe alle möglichen Endungen
                for ext in ['.png', '.jpg', '.jpeg', '.webp', '.gif']:
                    local_path = grid_dir / (filename_base + ext)
                    if local_path.exists():
                        return str(local_path)

        # 2. Web Fallbacks (Standard Steam URLs)
        if asset_type == 'grids':
            return f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/library_600x900.jpg"
        elif asset_type == 'heroes':
            return f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/library_hero.jpg"
        elif asset_type == 'logos':
            return f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/logo.png"
        elif asset_type == 'icons':
            return ""

        return ""

    @staticmethod
    def save_custom_image(app_id: str, asset_type: str, image_path: str) -> bool:
        """Speichert ein Custom Image in den Steam Grid Ordner"""
        short_id, _ = config.get_detected_user()
        if not config.STEAM_PATH or not short_id:
            return False

        grid_dir = config.STEAM_PATH / 'userdata' / short_id / 'config' / 'grid'
        grid_dir.mkdir(parents=True, exist_ok=True)

        # Bestimme Ziel-Dateinamen
        filename_base = ""
        if asset_type == 'grids':
            filename_base = f"p_{app_id}"
        elif asset_type == 'heroes':
            filename_base = f"{app_id}_hero"
        elif asset_type == 'logos':
            filename_base = f"{app_id}_logo"
        elif asset_type == 'icons':
            filename_base = f"{app_id}_icon"

        if not filename_base:
            return False

        # Extension ermitteln
        if 'steamstatic' in image_path or 'steamgriddb' in image_path:
            # Bei URLs raten wir oder nehmen .jpg als default
            ext = os.path.splitext(image_path)[1]
            if not ext: ext = '.jpg'
        else:
            # Lokale Datei
            ext = os.path.splitext(image_path)[1]

        final_path = grid_dir / (filename_base + ext)

        try:
            # Fall 1: Lokale Datei kopieren
            if os.path.exists(image_path):
                with open(image_path, 'rb') as f_src:
                    content = f_src.read()
                with open(final_path, 'wb') as f_dst:
                    f_dst.write(content)
                print(t('logs.steamgrid.saved', type=asset_type, app_id=app_id))
                return True

            # Fall 2: Download von URL
            elif image_path.startswith('http'):
                response = requests.get(image_path, stream=True, timeout=10)
                if response.status_code == 200:
                    with open(final_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    print(t('logs.steamgrid.saved', type=asset_type, app_id=app_id))
                    return True

        except (OSError, requests.RequestException) as e:
            print(t('logs.steamgrid.save_error', error=e))
            return False

        return False

    @staticmethod
    def delete_custom_image(app_id: str, asset_type: str) -> bool:
        short_id, _ = config.get_detected_user()
        if not config.STEAM_PATH or not short_id:
            return False

        grid_dir = config.STEAM_PATH / 'userdata' / short_id / 'config' / 'grid'

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
                        os.remove(path)
                        deleted = True
                        print(t('logs.steamgrid.deleted', path=path.name))
                    except OSError as e:
                        print(f"Error deleting {path.name}: {e}")

        return deleted