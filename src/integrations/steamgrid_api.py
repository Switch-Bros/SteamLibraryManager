"""
SteamGridDB API Client (Full Pagination)
Speichern als: src/integrations/steamgrid_api.py
"""
import requests
from typing import Dict, List, Optional, Any
from src.config import config
from src.utils.i18n import t


class SteamGridDB:
    BASE_URL = "https://www.steamgriddb.com/api/v2"

    def __init__(self):
        self.api_key = config.STEAMGRIDDB_API_KEY
        self.headers = {'Authorization': f'Bearer {self.api_key}'}

    def get_images_for_game(self, steam_app_id: str) -> Dict[str, Optional[str]]:
        if not self.api_key: return {}
        game_id = self._get_game_id(steam_app_id)
        if not game_id: return {}

        return {
            'grids': self._fetch_single_url(game_id, 'grids', {'dimensions': '600x900,342x482'}),
            'heroes': self._fetch_single_url(game_id, 'heroes'),
            'logos': self._fetch_single_url(game_id, 'logos'),
            'icons': self._fetch_single_url(game_id, 'icons')
        }

    def get_images_by_type(self, steam_app_id: str, img_type: str) -> List[Dict[str, Any]]:
        """
        Holt ALLE Bilder über ALLE Seiten.
        """
        if not self.api_key: return []

        game_id = self._get_game_id(steam_app_id)
        if not game_id: return []

        all_images = []
        page = 0

        while True:
            try:
                # nsfw='any' -> Zeigt ALLES (Standard + Adult)
                params: Dict[str, Any] = {
                    'page': page,
                    'nsfw': 'any',
                    'types': 'static,animated'
                }

                if img_type == 'grids':
                    params['dimensions'] = '600x900,342x482'

                url = f"{self.BASE_URL}/{img_type}/game/{game_id}"
                response = requests.get(url, headers=self.headers, params=params, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    if data.get('success') and data.get('data'):
                        new_images = data['data']
                        all_images.extend(new_images)

                        # Wenn weniger als 20 Ergebnisse, war es die letzte Seite
                        if len(new_images) < 20:
                            break
                        page += 1
                    else:
                        break
                else:
                    print(t('logs.steamgrid.api_error', code=response.status_code, page=page))
                    break

            except (requests.RequestException, ValueError, KeyError) as e:
                print(t('logs.steamgrid.exception', error=e))
                break

        print(t('logs.steamgrid.found', count=len(all_images)))
        return all_images

    def _get_game_id(self, steam_app_id: str) -> Optional[int]:
        try:
            url = f"{self.BASE_URL}/games/steam/{steam_app_id}"
            response = requests.get(url, headers=self.headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data['success']:
                    return data['data']['id']
        except (requests.RequestException, ValueError, KeyError):
            pass
        return None

    def _fetch_single_url(self, game_id: int, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[str]:
        try:
            url = f"{self.BASE_URL}/{endpoint}/game/{game_id}"
            response = requests.get(url, headers=self.headers, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data['success'] and data['data']:
                    return data['data'][0]['url']
        except (requests.RequestException, ValueError, KeyError):
            pass
        return None