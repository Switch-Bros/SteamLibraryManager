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
