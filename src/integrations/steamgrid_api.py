"""
SteamGridDB API Client (Pagination & Full Results)
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

    def get_images_for_game(self, steam_app_id: str) -> Dict[str, str]:
        if not self.api_key: return {}
        game_id = self._get_game_id(steam_app_id)
        if not game_id: return {}

        images = {}
        images['grids'] = self._fetch_single_url(game_id, 'grids', {'dimensions': ['600x900', '342x482']})
        images['heroes'] = self._fetch_single_url(game_id, 'heroes')
        images['logos'] = self._fetch_single_url(game_id, 'logos')
        images['icons'] = self._fetch_single_url(game_id, 'icons')
        return images

    def get_images_by_type(self, steam_app_id: str, img_type: str) -> List[Dict[str, Any]]:
        """
        Holt ALLE Bilder mit METADATEN über MEHRERE SEITEN.
        """
        if not self.api_key: return []
        game_id = self._get_game_id(steam_app_id)
        if not game_id: return []

        endpoint = img_type
        all_images = []
        page = 0  # Start bei 0 oder 1? API docs sagen meist page=0 oder 1. Wir testen dynamisch.

        # Basis-Parameter
        params = {
            'nsfw': 'any',
            'humor': 'any',
            'epilepsy': 'any',
            'types': 'static,animated',
            'page': page
        }

        if img_type == 'grids':
            params['dimensions'] = '600x900,342x482'

        print(f"DEBUG: Start fetching {img_type} for game {game_id}...")

        while True:
            try:
                url = f"{self.BASE_URL}/{endpoint}/game/{game_id}"
                params['page'] = page

                response = requests.get(url, headers=self.headers, params=params, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    if data['success'] and data['data']:
                        batch = data['data']
                        all_images.extend(batch)
                        print(f"  -> Page {page}: Found {len(batch)} images.")

                        # Nächste Seite vorbereiten
                        page += 1

                        # Sicherheits-Break falls API unendlich liefert oder leer ist
                        if len(batch) < 10:  # Wenn weniger als ein volles Dutzend kommt, sind wir wohl am Ende
                            # Hinweis: Manchmal ist das Limit 20. Wenn 20 kommen, könnte es weitergehen.
                            # Besser: Wir machen weiter, bis 'data' leer ist.
                            pass
                    else:
                        # Keine Daten mehr -> Fertig
                        break
                else:
                    print(f"API Error {response.status_code} on page {page}")
                    break

                # Notbremse (max 10 Seiten, das sind >200 Bilder)
                if page > 10: break

            except Exception as e:
                print(f"API Exception: {e}")
                break

        print(f"Total images found: {len(all_images)}")
        return all_images

    def _get_game_id(self, steam_app_id: str) -> Optional[int]:
        try:
            url = f"{self.BASE_URL}/games/steam/{steam_app_id}"
            response = requests.get(url, headers=self.headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data['success']:
                    return data['data']['id']
        except Exception as e:
            pass
        return None

    def _fetch_single_url(self, game_id: int, endpoint: str, params: Dict = None) -> Optional[str]:
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