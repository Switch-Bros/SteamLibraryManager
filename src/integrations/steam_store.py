# src/integrations/steam_store.py

"""
Steam Store integration for fetching tags and franchise detection.

This module provides functionality to scrape game tags from the Steam Store
in the user's preferred language and detect game franchises based on name patterns.
"""
import time
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional

import requests
from bs4 import BeautifulSoup
from src.utils.i18n import t


class SteamStoreScraper:
    """
    Fetches game tags from the Steam Store in the selected language.

    This class scrapes the Steam Store page for a game to extract user-defined
    tags. It supports multiple languages, implements rate limiting, and caches
    results for 30 days.
    """

    # Language mapping (ISO Code -> Steam Internal Name)
    STEAM_LANGUAGES = {
        'en': 'english',
        'de': 'german',
        'fr': 'french',
        'es': 'spanish',
        'it': 'italian',
        'pt': 'portuguese',
        'ru': 'russian',
        'zh': 'schinese',
        'ja': 'japanese',
        'ko': 'koreana'
    }

    def __init__(self, cache_dir: Path, language: str = 'en'):
        """
        Initializes the SteamStoreScraper.

        Args:
            cache_dir (Path): Directory to store cached tag data.
            language (str): Language code ('en', 'de', etc.). Defaults to 'en'.
        """
        self.cache_dir = cache_dir / 'store_tags'
        self.cache_dir.mkdir(exist_ok=True, parents=True)

        # Pre-initialize attributes
        self.language_code = 'en'
        self.steam_language = 'english'

        # Set language
        self.set_language(language)

        # Rate limiting
        self.last_request_time = 0.0
        self.min_request_interval = 1.5

        # Tag blacklist (English & German mixed)
        self.tag_blacklist = {
            # English
            'Singleplayer', 'Multiplayer', 'Co-op', 'Shared/Split Screen',
            'Full controller support', 'Partial Controller Support',
            'Steam Cloud', 'Steam Achievements', 'Remote Play',
            'Captions available', 'Commentary available',
            'Includes level editor', 'Includes Source SDK',
            'VR Support', 'Steam Trading Cards', 'Stats',
            'Steam Leaderboards', 'Steam Workshop',
            'Cross-Platform Multiplayer', 'Remote Play on Phone',
            'Remote Play on Tablet', 'Remote Play on TV',
            'Remote Play Together', 'HDR available',
            # German
            'Einzelspieler', 'Mehrspieler', 'Koop', 'Geteilter/Split Screen',
            'Volle Controllerunterstützung', 'Teilweise Controllerunterstützung',
            'Steam Cloud', 'Steam-Errungenschaften', 'Remote Play',
            'Untertitel verfügbar', 'Kommentar verfügbar',
            'Enthält Level-Editor', 'Enthält Source SDK',
            'VR-Unterstützung', 'Steam-Sammelkarten', 'Statistiken',
            'Steam-Bestenlisten', 'Steam Workshop',
            'Plattformübergreifender Mehrspieler', 'Remote Play auf Smartphones',
            'Remote Play auf Tablets', 'Remote Play auf Fernsehern',
            'Remote Play Together', 'HDR verfügbar'
        }

    def set_language(self, language_code: str):
        """
        Sets the language for Steam Store requests.

        Args:
            language_code (str): ISO language code (e.g., 'en', 'de').
        """
        self.language_code = language_code
        self.steam_language = self.STEAM_LANGUAGES.get(language_code, 'english')

    def fetch_tags(self, app_id: str) -> List[str]:
        """
        Fetches user-defined tags from the Steam Store page.

        This method first checks the cache for existing data (valid for 30 days).
        If not cached, it scrapes the Steam Store page, filters out blacklisted
        tags, and caches the result.

        Args:
            app_id (str): The Steam app ID.

        Returns:
            List[str]: A list of tag names in the selected language, or an empty
                      list if fetching failed.
        """
        cache_file = self.cache_dir / f"{app_id}_{self.language_code}.json"

        # 1. Check Cache
        if cache_file.exists():
            try:
                # Cache validation (30 days)
                mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
                if datetime.now() - mtime < timedelta(days=30):
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        return json.load(f)
            except (OSError, json.JSONDecodeError):
                pass

        # 2. Rate Limiting
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)

        # 3. Fetch from Steam
        try:
            self.last_request_time = time.time()
            cookies = {'Steam_Language': self.steam_language}

            # Secure HTTPS link
            url = f"https://store.steampowered.com/app/{app_id}/"

            response = requests.get(url, cookies=cookies, timeout=10)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Find tags
                tags = []

                # Selector for tags
                tag_elements = soup.select('.app_tag')
                for tag_elem in tag_elements:
                    tag_text = tag_elem.get_text().strip()
                    if tag_text and tag_text not in self.tag_blacklist and tag_text != '+':
                        tags.append(tag_text)

                # Save (create directory if needed)
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(tags, f)

                return tags

        except (requests.RequestException, AttributeError) as e:
            print(t('logs.steam_store.fetch_error', app_id=app_id, error=str(e)))

        return []

    def fetch_age_rating(self, app_id: str) -> Optional[str]:
        """
        Fetches age rating from the Steam Store page and converts to PEGI.

        This method scrapes the Steam Store page to extract the age rating
        (Steam age gate, PEGI, ESRB, USK, etc.) and converts it to a PEGI rating.
        Results are cached for 30 days.

        Args:
            app_id (str): The Steam app ID.

        Returns:
            Optional[str]: PEGI rating (e.g., "18", "16", "12", "7", "3") or None if not found.
        """
        cache_file = self.cache_dir.parent / 'age_ratings' / f"{app_id}.json"
        cache_file.parent.mkdir(exist_ok=True, parents=True)

        # 1. Check Cache
        if cache_file.exists():
            try:
                mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
                if datetime.now() - mtime < timedelta(days=30):
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        return data.get('pegi_rating')
            except (OSError, ValueError, json.JSONDecodeError):
                pass

        # 2. Rate Limiting
        time_since_last = time.time() - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)

        # 3. Fetch from Steam
        try:
            self.last_request_time = time.time()
            cookies = {'Steam_Language': self.steam_language, 'wants_mature_content': '1', 'birthtime': '0'}
            url = f"https://store.steampowered.com/app/{app_id}/"

            response = requests.get(url, cookies=cookies, timeout=10 )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            pegi_rating = None

            # Try to find age rating in various formats
            # 1. Steam age gate (e.g., "18+", "16+")
            age_gate = soup.find('div', class_='game_rating_icon')
            if age_gate and age_gate.get('data-rating'):
                steam_age = age_gate['data-rating'].replace('+', '')
                pegi_rating = self._convert_to_pegi(steam_age, 'steam')

            # 2. PEGI rating
            if not pegi_rating:
                pegi_elem = soup.find('img', alt=lambda x: x and 'PEGI' in x)
                if pegi_elem:
                    alt_text = pegi_elem.get('alt', '')
                    for age in ['18', '16', '12', '7', '3']:
                        if age in alt_text:
                            pegi_rating = age
                            break

            # 3. ESRB rating
            if not pegi_rating:
                esrb_elem = soup.find('img', alt=lambda x: x and 'ESRB' in x)
                if esrb_elem:
                    alt_text = esrb_elem.get('alt', '').lower()
                    if 'adults only' in alt_text or 'ao' in alt_text:
                        pegi_rating = '18'
                    elif 'mature' in alt_text or 'm' in alt_text:
                        pegi_rating = '18'
                    elif 'teen' in alt_text or 't' in alt_text:
                        pegi_rating = '16'
                    elif 'everyone 10+' in alt_text or 'e10+' in alt_text:
                        pegi_rating = '12'
                    elif 'everyone' in alt_text or 'e' in alt_text:
                        pegi_rating = '3'

            # 4. USK rating (German)
            if not pegi_rating:
                usk_elem = soup.find('img', alt=lambda x: x and 'USK' in x)
                if usk_elem:
                    alt_text = usk_elem.get('alt', '')
                    for usk_age, pegi_age in [('18', '18'), ('16', '16'), ('12', '12'), ('6', '7'), ('0', '3')]:
                        if usk_age in alt_text:
                            pegi_rating = pegi_age
                            break

            # Cache result
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({'pegi_rating': pegi_rating, 'fetched_at': datetime.now().isoformat()}, f)

            return pegi_rating

        except (requests.RequestException, AttributeError) as e:
            print(f"Failed to fetch age rating for {app_id}: {e}")

        return None

    @staticmethod
    def _convert_to_pegi(rating: str, system: str) -> Optional[str]:
        """
        Converts age ratings from different systems to PEGI.

        Args:
            rating (str): The rating value (e.g., "18", "Mature").
            system (str): The rating system ('steam', 'esrb', 'usk').

        Returns:
            Optional[str]: PEGI rating or None.
        """
        if system == 'steam':
            # Steam age gate: 18+ → PEGI 18, 16+ → PEGI 16, etc.
            age_map = {'18': '18', '16': '16', '12': '12', '7': '7', '3': '3', '0': '3'}
            return age_map.get(rating)

        elif system == 'esrb':
            esrb_map = {
                'AO': '18', 'Adults Only': '18',
                'M': '18', 'Mature': '18',
                'T': '16', 'Teen': '16',
                'E10+': '12', 'Everyone 10+': '12',
                'E': '3', 'Everyone': '3'
            }
            return esrb_map.get(rating)

        elif system == 'usk':
            usk_map = {'18': '18', '16': '16', '12': '12', '6': '7', '0': '3'}
            return usk_map.get(rating)

        return None

    def get_cache_coverage(self, app_ids: List[str]) -> dict:
        """
        Check how many games have cached tag data.

        This method checks the cache directory to determine how many of the
        provided app IDs already have cached tag data (valid for 30 days).

        Args:
            app_ids: List of Steam app IDs to check.

        Returns:
            dict: Dictionary with:
                - 'total': Total number of app IDs checked
                - 'cached': Number of app IDs with valid cache
                - 'missing': Number of app IDs without cache
                - 'percentage': Percentage of cached apps (0-100)
        """
        total = len(app_ids)
        cached = 0

        for app_id in app_ids:
            cache_file = self.cache_dir / f"{app_id}_{self.language_code}.json"

            if cache_file.exists():
                try:
                    # Cache validation (30 days)
                    mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
                    if datetime.now() - mtime < timedelta(days=30):
                        cached += 1
                except (OSError, ValueError):
                    pass

        missing = total - cached
        percentage = (cached / total * 100) if total > 0 else 0

        return {
            'total': total,
            'cached': cached,
            'missing': missing,
            'percentage': percentage
        }

    # --- Franchise Detection (Static) ---

    FRANCHISES = {
        'LEGO': ['lego'],
        "Assassin's Creed": ["assassin's creed", "assassins creed"],
        'Dark Souls': ['dark souls'],
        'The Elder Scrolls': ['elder scrolls', 'skyrim', 'oblivion', 'morrowind'],
        'Fallout': ['fallout'],
        'Far Cry': ['far cry'],
        'Call of Duty': ['call of duty'],
        'Tomb Raider': ['tomb raider', 'lara croft'],
        'Grand Theft Auto': ['grand theft auto', 'gta'],
        'The Witcher': ['witcher'],
        'Batman Arkham': ['batman arkham', 'batman: arkham'],
        'Borderlands': ['borderlands'],
        'BioShock': ['bioshock'],
        'Metro': ['metro 2033', 'metro last light', 'metro exodus'],
        'Dishonored': ['dishonored'],
        'Deus Ex': ['deus ex'],
        'Mass Effect': ['mass effect'],
        'Dragon Age': ['dragon age'],
        'Resident Evil': ['resident evil'],
        'Total War': ['total war'],
        'Civilization': ['civilization', "sid meier's civilization"],
        'DOOM': ['doom'],
        'Wolfenstein': ['wolfenstein'],
        'Hitman': ['hitman'],
        'Final Fantasy': ['final fantasy'],
        'Yakuza': ['yakuza', 'like a dragon'],
        'Need for Speed': ['need for speed'],
        'Star Wars': ['star wars'],
        'Prince of Persia': ['prince of persia'],
    }

    @classmethod
    def detect_franchise(cls, game_name: str) -> Optional[str]:
        """
        Detects the franchise a game belongs to based on its name.

        This method uses pattern matching against a predefined list of franchises.

        Args:
            game_name (str): The name of the game.

        Returns:
            Optional[str]: The franchise name if detected, or None if no match is found.
        """
        name_lower = game_name.lower()

        for franchise, patterns in cls.FRANCHISES.items():
            for pattern in patterns:
                if pattern in name_lower:
                    return franchise
        return None
