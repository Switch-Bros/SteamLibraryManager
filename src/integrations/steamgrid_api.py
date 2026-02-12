# src/integrations/steamgrid_api.py

"""
SteamGridDB API client with full pagination support.

This module provides a client for the SteamGridDB API to fetch game images
(grids, heroes, logos, icons) with support for paginated results and NSFW content.
"""
from __future__ import annotations

import logging
import requests
from typing import Dict, List, Optional, Any
from src.config import config
from src.utils.i18n import t



logger = logging.getLogger("steamlibmgr.steamgrid")

class SteamGridDB:
    """
    Client for the SteamGridDB API.

    This class provides methods to fetch game images from SteamGridDB, including
    support for pagination, multiple image types, and NSFW content filtering.
    """

    # Secure HTTPS URL
    BASE_URL = "https://www.steamgriddb.com/api/v2"

    def __init__(self):
        """
        Initializes the SteamGridDB client.

        Reads the API key from the config and sets up authentication headers.
        """
        self.api_key = config.STEAMGRIDDB_API_KEY
        self.headers = {'Authorization': f'Bearer {self.api_key}'}

    def get_images_for_game(self, steam_app_id: str | int) -> Dict[str, Optional[str]]:
        """
        Fetches a single image URL for each image type.

        This is a convenience method that returns one image per type (grids, heroes,
        logos, icons) for quick access.

        Args:
            steam_app_id (str | int): The Steam app ID.

        Returns:
            Dict[str, Optional[str]]: A dictionary mapping image types to URLs.
                                     Returns an empty dict if no API key is configured
                                     or if the game is not found.
        """
        if not self.api_key: return {}
        game_id = self._get_game_id(steam_app_id)
        if not game_id: return {}

        return {
            'grids': self._fetch_single_url(game_id, 'grids', {'dimensions': '600x900,342x482'}),
            'heroes': self._fetch_single_url(game_id, 'heroes'),
            'logos': self._fetch_single_url(game_id, 'logos'),
            'icons': self._fetch_single_url(game_id, 'icons')
        }

    def get_images_by_type(self, steam_app_id: str | int, img_type: str) -> List[Dict[str, Any]]:
        """
        Fetches all images of a specific type across all pages.

        This method implements pagination to retrieve all available images for
        a game. It includes both static and animated images, and NSFW content.

        Args:
            steam_app_id (str | int): The Steam app ID.
            img_type (str): The type of image to fetch ('grids', 'heroes', 'logos', 'icons').

        Returns:
            List[Dict[str, Any]]: A list of image data dictionaries. Each dictionary
                                 contains image metadata (url, dimensions, etc.).
                                 Returns an empty list if no API key is configured,
                                 the game is not found, or an error occurs.
        """
        if not self.api_key: return []

        game_id = self._get_game_id(steam_app_id)
        if not game_id: return []

        all_images = []
        page = 0

        while True:
            try:
                # nsfw='any' -> Shows EVERYTHING (Standard + Adult)
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

                        # If less than 20 results, it was the last page
                        if len(new_images) < 20:
                            break
                        page += 1
                    else:
                        break
                else:
                    logger.error(t('logs.steamgrid.api_error', code=response.status_code, page=page))
                    break

            except (requests.RequestException, ValueError, KeyError) as e:
                logger.error(t('logs.steamgrid.exception', error=str(e)))
                break

        logger.info(t('logs.steamgrid.found', count=len(all_images)))
        return all_images

    def _get_game_id(self, steam_app_id: str | int) -> Optional[int]:
        """
        Resolves a Steam app ID to a SteamGridDB game ID.

        Args:
            steam_app_id (str | int): The Steam app ID.

        Returns:
            Optional[int]: The SteamGridDB game ID, or None if not found or an error occurs.
        """
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
        """
        Fetches a single image URL for a specific endpoint.

        This is a helper method used by get_images_for_game to retrieve one image
        per type.

        Args:
            game_id (int): The SteamGridDB game ID.
            endpoint (str): The API endpoint ('grids', 'heroes', 'logos', 'icons').
            params (Optional[Dict[str, Any]]): Optional query parameters (e.g., dimensions).

        Returns:
            Optional[str]: The URL of the first image, or None if not found or an error occurs.
        """
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
