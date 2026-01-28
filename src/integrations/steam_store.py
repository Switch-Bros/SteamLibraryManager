"""
Steam Store Integration - Fetches Tags & Franchises
"""
import time
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional

import requests
from bs4 import BeautifulSoup


class SteamStoreScraper:
    """Fetches tags from Steam Store - in selected language"""

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
        Args:
            cache_dir: Cache directory
            language: Language code ('en', 'de', etc.)
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
        """Sets the language for Store requests"""
        self.language_code = language_code
        self.steam_language = self.STEAM_LANGUAGES.get(language_code, 'english')

    def fetch_tags(self, app_id: str) -> List[str]:
        """Fetches tags from the Steam Store page"""
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

                # Save
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(tags, f)

                return tags

        except (requests.RequestException, AttributeError) as e:
            print(f"Store Error {app_id}: {e}")

        return []

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
    }

    @classmethod
    def detect_franchise(cls, game_name: str) -> Optional[str]:
        """Detect franchise from game name"""
        name_lower = game_name.lower()

        for franchise, patterns in cls.FRANCHISES.items():
            for pattern in patterns:
                if pattern in name_lower:
                    return franchise
        return None