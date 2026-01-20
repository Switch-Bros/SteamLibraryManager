"""
Steam Store Integration - MIT LANGUAGE SUPPORT! 🌍

Updated: Holt Tags in der eingestellten Sprache
Speichern als: src/integrations/steam_store.py
"""

import requests
import time
from bs4 import BeautifulSoup
from typing import List, Optional, Dict
from pathlib import Path
import json
from datetime import datetime, timedelta
from src.utils.i18n import t


class SteamStoreScraper:
    """Holt Tags von Steam Store - in gewählter Sprache"""

    # Language mapping
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

        # Set language
        self.set_language(language)

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.5

        # Tag blacklist (both English and German)
        self.tag_blacklist = {
            # English
            'Singleplayer', 'Multiplayer', 'Co-op', 'Online Co-Op',
            'Local Co-Op', 'Shared/Split Screen', 'Cross-Platform Multiplayer',
            'Controller Support', 'Full controller support', 'Partial Controller Support',
            'Great Soundtrack', 'Atmospheric', 'Story Rich',
            'VR Support', 'VR Only', 'Tracked Controller Support',
            'Steam Achievements', 'Steam Cloud', 'Steam Trading Cards',
            'Steam Workshop', 'In-App Purchases', 'Includes level editor',
            # German
            'Einzelspieler', 'Mehrspieler', 'Koop', 'Online-Koop',
            'Lokaler Koop', 'Geteilter Bildschirm', 'Plattformübergreifender Mehrspieler',
            'Controller-Unterstützung', 'Volle Controller-Unterstützung',
            'Großartiger Soundtrack', 'Atmosphärisch', 'Handlungsintensiv',
            'VR-Unterstützung', 'Nur VR',
            'Steam-Errungenschaften', 'Steam Cloud', 'Steam-Sammelkarten',
            'Steam Workshop', 'Käufe im Spiel'
        }

    def set_language(self, language: str):
        """Set language for tag fetching"""
        self.language_code = language
        self.steam_language = self.STEAM_LANGUAGES.get(language, 'english')

    def get_game_tags(self, app_id: str, max_tags: int = 13,
                     ignore_common: bool = True) -> List[str]:
        """
        Get tags for a game in the set language
        """
        # Cache key includes language
        cache_file = self.cache_dir / f'{app_id}_{self.language_code}.json'

        # Check cache
        if cache_file.exists():
            cache_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
            if cache_age < timedelta(days=30):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                    tags = cached_data.get('tags', [])
                    return self._filter_tags(tags, max_tags, ignore_common)

        # Fetch from Steam Store
        tags = self._fetch_tags_from_store(app_id)

        if tags:
            # Cache with language
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'tags': tags,
                    'language': self.language_code,
                    'fetched_at': datetime.now().isoformat()
                }, f, ensure_ascii=False)

        return self._filter_tags(tags, max_tags, ignore_common)

    def _fetch_tags_from_store(self, app_id: str) -> List[str]:
        """Fetch tags from Steam Store in set language"""
        # Rate limiting
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)

        try:
            # URL with language parameter
            url = f'https://store.steampowered.com/app/{app_id}'
            params = {'l': self.steam_language}

            headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
                'Accept-Language': f'{self.steam_language},en;q=0.9'
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)
            self.last_request_time = time.time()

            if response.status_code != 200:
                return []

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find tags
            tags = []
            tag_elements = soup.find_all('a', class_='app_tag')

            for tag_elem in tag_elements:
                tag_text = tag_elem.text.strip()
                if tag_text:
                    tags.append(tag_text)

            return tags

        except Exception as e:
            print(t('logs.steam_store.fetch_error', app_id=app_id, error=e))
            return []

    def _filter_tags(self, tags: List[str], max_tags: int,
                    ignore_common: bool) -> List[str]:
        """Filter and limit tags"""
        filtered = []

        for tag in tags:
            # Skip blacklist
            if ignore_common and tag in self.tag_blacklist:
                continue

            filtered.append(tag)

            # Limit
            if len(filtered) >= max_tags:
                break

        return filtered

    def fetch_multiple_games(self, app_ids: List[str], max_tags: int = 13,
                            ignore_common: bool = True,
                            progress_callback = None) -> Dict[str, List[str]]:
        """Fetch tags for multiple games"""
        results = {}
        total = len(app_ids)

        for i, app_id in enumerate(app_ids):
            if progress_callback:
                progress_callback(i + 1, total, app_id)

            tags = self.get_game_tags(app_id, max_tags, ignore_common)
            results[app_id] = tags

        return results


class FranchiseDetector:
    """Detect franchises from game names"""

    FRANCHISES = {
        'LEGO': ['lego'],
        'Assassin\'s Creed': ['assassin\'s creed', 'assassins creed'],
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
        'Civilization': ['civilization', 'sid meier\'s civilization'],
        'DOOM': ['doom'],
        'Wolfenstein': ['wolfenstein'],
        'Hitman': ['hitman'],
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