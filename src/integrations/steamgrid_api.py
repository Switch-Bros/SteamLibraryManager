"""
SteamGridDB API Client
Speichern als: src/integrations/steamgrid_api.py
"""
import requests
from typing import Dict, List, Optional
from src.config import config
from src.utils.i18n import t


class SteamGridDB:
    BASE_URL = "https://www.steamgriddb.com/api/v2"

    def __init__(self):
        self.api_key = config.STEAMGRIDDB_API_KEY
        self.headers = {'Authorization': f'Bearer {self.api_key}'}

    def get_images_for_game(self, steam_app_id: str) -> Dict[str, str]:
        """Holt das beste Bild pro Typ (für Vorschau)"""
        # ... (wie vorher, code gekürzt zur übersicht) ...
        # Wichtig: Dieser Teil bleibt gleich wie im vorherigen Step
        if not self.api_key:
            print(t('logs.steamgrid.missing_key'))
            return {}
        game_id = self._get_game_id(steam_app_id)
        if not game_id: return {}
        images = {}
        images['grid'] = self._fetch_image(game_id, 'grids', {'dimensions': ['600x900', '342x482']})
        images['hero'] = self._fetch_image(game_id, 'heroes')
        images['logo'] = self._fetch_image(game_id, 'logos')
        images['icon'] = self._fetch_image(game_id, 'icons')
        return images

    def get_images_by_type(self, steam_app_id: str, img_type: str) -> List[str]:
        """
        Holt eine LISTE von Bild-URLs für einen bestimmten Typ (für den Auswahl-Dialog)
        """
        if not self.api_key: return []

        game_id = self._get_game_id(steam_app_id)
        if not game_id: return []

        # Mapping unserer Typen zu SteamGridDB Endpoints
        endpoint = f"{img_type}s"  # grid -> grids, hero -> heroes

        params = {}
        if img_type == 'grid':
            params = {'dimensions': ['600x900', '342x482']}

        try:
            url = f"{self.BASE_URL}/{endpoint}/game/{game_id}"
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data['success']:
                    # Gib Liste von URLs zurück (Thumbnail URLs sind kleiner & schneller)
                    return [item['thumb'] for item in data['data']]
        except Exception as e:
            print(f"SGDB Fetch Error: {e}")

        return []

    def _get_game_id(self, steam_app_id: str) -> Optional[int]:
        try:
            url = f"{self.BASE_URL}/games/steam/{steam_app_id}"
            response = requests.get(url, headers=self.headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data['success']:
                    return data['data']['id']
        except Exception as e:
            print(t('logs.steamgrid.id_error', app_id=steam_app_id, error=e))
        return None

    def _fetch_image(self, game_id: int, endpoint: str, params: Dict = None) -> Optional[str]:
        try:
            url = f"{self.BASE_URL}/{endpoint}/game/{game_id}"
            response = requests.get(url, headers=self.headers, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data['success'] and data['data']:
                    return data['data'][0]['url']
        except:
            pass
        return None