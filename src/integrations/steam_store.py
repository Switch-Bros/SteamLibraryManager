# src/integrations/steam_store.py

"""
Steam Store integration for fetching tags and age ratings.

This module provides functionality to scrape game tags from the Steam Store
in the user's preferred language and detect game franchises based on name patterns.

FIXED: Age rating fetching now uses Steam Store API instead of unreliable HTML scraping.
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
    Fetches game tags and age ratings from the Steam Store.

    This class scrapes the Steam Store page for a game to extract user-defined
    tags and age ratings. It supports multiple languages, implements rate limiting,
    and caches results for 30 days.
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
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.language_code = language
        self.steam_language = self.STEAM_LANGUAGES.get(language, 'english')
        self.last_request_time = 0.0
        self.min_request_interval = 1.5  # Rate limit: 1.5 seconds between requests

        # Tag blacklist (common but unhelpful tags)
        self.tag_blacklist = {
            'Singleplayer', 'Multiplayer', 'Online Co-Op', 'Local Co-Op',
            'Steam Achievements', 'Full controller support', 'Steam Trading Cards',
            'Steam Cloud', 'Stats', 'Includes level editor', 'Steam Workshop',
            'Partial Controller Support', 'Remote Play on Tablet', 'Remote Play on TV',
            'Remote Play Together', 'In-App Purchases', 'Valve Anti-Cheat enabled',
            'Steam Leaderboards'
        }

    def fetch_tags(self, app_id: str) -> List[str]:
        """
        Fetches tags for a game from the Steam Store page.

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
        Fetches age rating from Steam Store API (with HTML fallback).

        FIXED: This method now uses the official Steam Store API to fetch age ratings,
        which is much more reliable than HTML scraping. Falls back to HTML scraping
        (with fixed Age-Gate handling) if the API fails. Results are cached for 30 days.

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

        # 3. Try Steam Store API FIRST (RECOMMENDED!)
        pegi_rating = self._fetch_age_rating_from_api(app_id)
        
        # 4. Fallback to HTML scraping if API fails
        if not pegi_rating:
            pegi_rating = self._fetch_age_rating_from_html(app_id)

        # 5. Cache result
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'pegi_rating': pegi_rating,
                    'fetched_at': datetime.now().isoformat(),
                    'method': 'api' if pegi_rating else 'html_fallback'
                }, f)
        except OSError:
            pass

        return pegi_rating

    def _fetch_age_rating_from_api(self, app_id: str) -> Optional[str]:
        """
        Fetches age rating using Steam Store API (NEW METHOD!).
        
        This is the RECOMMENDED way to get age ratings. No Age-Gate problems!
        
        Args:
            app_id: Steam app ID
            
        Returns:
            PEGI rating string or None
        """
        try:
            self.last_request_time = time.time()
            
            # Steam Store API endpoint
            url = f"https://store.steampowered.com/api/appdetails?appids={app_id}"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Check if request was successful
            if not data or str(app_id) not in data:
                return None
                
            app_data = data[str(app_id)]
            
            if not app_data.get('success'):
                return None
                
            game_data = app_data.get('data', {})

            # Get required_age from API
            required_age = game_data.get('required_age', 0)

            # ⚠️ FIX: Convert to int (API sometimes returns string!)
            if isinstance(required_age, str):
                try:
                    required_age = int(required_age)
                except ValueError:
                    required_age = 0
            
            # Convert to PEGI rating
            if required_age >= 18:
                return '18'
            elif required_age >= 16:
                return '16'
            elif required_age >= 12:
                return '12'
            elif required_age >= 6:
                return '7'
            elif required_age > 0:
                return '3'
            else:
                # Check if game has mature content descriptor
                content_descriptors = game_data.get('content_descriptors', {})
                if content_descriptors.get('ids'):
                    # Has content warnings → probably PEGI 12 or higher
                    return '12'
                    
                # Default for games without age restriction
                return '3'
                
        except (requests.RequestException, ValueError, KeyError) as e:
            print(f"Steam API fetch failed for {app_id}: {e}")
            return None

    def _fetch_age_rating_from_html(self, app_id: str) -> Optional[str]:
        """
        Fetches age rating via HTML scraping (FALLBACK METHOD).
        
        FIXED: Proper Age-Gate bypass with Unix timestamp!
        This is the old method with FIXED Age-Gate handling.
        Only used if API fails.
        
        Args:
            app_id: Steam app ID
            
        Returns:
            PEGI rating string or None
        """
        try:
            self.last_request_time = time.time()
            
            # FIXED: Proper Age-Gate bypass with Unix timestamp!
            birthtime = '631152000'  # Unix timestamp for 1990-01-01
            cookies = {
                'Steam_Language': self.steam_language,
                'wants_mature_content': '1',
                'birthtime': birthtime,  # FIXED: Now uses proper timestamp!
                'mature_content': '1'
            }
            
            url = f"https://store.steampowered.com/app/{app_id}/"
            response = requests.get(url, cookies=cookies, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Try multiple methods to find age rating
            
            # Method 1: Look for PEGI image
            pegi_elem = soup.find('img', alt=lambda x: x and 'PEGI' in x)
            if pegi_elem:
                alt_text = pegi_elem.get('alt', '')
                for age in ['18', '16', '12', '7', '3']:
                    if age in alt_text:
                        return age

            # Method 2: Look for USK rating (Germany)
            usk_elem = soup.find('img', alt=lambda x: x and 'USK' in x)
            if usk_elem:
                alt_text = usk_elem.get('alt', '')
                usk_to_pegi = {'18': '18', '16': '16', '12': '12', '6': '7', '0': '3'}
                for usk_age, pegi_age in usk_to_pegi.items():
                    if usk_age in alt_text:
                        return pegi_age

            # Method 3: Look for ESRB rating (USA)
            esrb_elem = soup.find('img', alt=lambda x: x and 'ESRB' in x)
            if esrb_elem:
                alt_text = esrb_elem.get('alt', '').lower()
                if 'adults only' in alt_text or 'mature' in alt_text:
                    return '18'
                elif 'teen' in alt_text:
                    return '16'
                elif 'everyone 10+' in alt_text:
                    return '12'
                elif 'everyone' in alt_text:
                    return '3'

            # Method 4: Check for age gate div (fallback)
            age_divs = soup.find_all('div', class_=lambda x: x and 'age' in x.lower())
            for div in age_divs:
                text = div.get_text().lower()
                if '18' in text:
                    return '18'
                elif '16' in text:
                    return '16'
                elif '12' in text:
                    return '12'

            return None

        except (requests.RequestException, AttributeError) as e:
            print(f"HTML scraping failed for {app_id}: {e}")
            return None

    @staticmethod
    def _convert_to_pegi(rating: str, system: str) -> Optional[str]:
        """
        Converts age ratings from different systems to PEGI.

        Note: This method is kept for backward compatibility but is no longer
        actively used since the new API method handles conversions internally.

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
            Dict with keys:
                - 'total': Total number of app IDs checked
                - 'cached': Number of apps with valid cache
                - 'missing': Number of apps without cache
                - 'percentage': Percentage of cached apps (0-100)
        """
        total = len(app_ids)
        cached = 0
        missing = 0

        for app_id in app_ids:
            cache_file = self.cache_dir / f"{app_id}_{self.language_code}.json"

            if cache_file.exists():
                try:
                    mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
                    if datetime.now() - mtime < timedelta(days=30):
                        cached += 1
                    else:
                        missing += 1
                except OSError:
                    missing += 1
            else:
                missing += 1

        percentage = (cached / total * 100) if total > 0 else 0.0

        return {
            'total': total,
            'cached': cached,
            'missing': missing,
            'percentage': round(percentage, 1)
        }

    @staticmethod
    def detect_franchise(game_name: str) -> Optional[str]:
        """
        Detects game franchise from the game name.

        Tries to extract franchise names from common patterns:
        - "Franchise: Subtitle"
        - "Franchise - Subtitle"
        - "Franchise™"
        - "Franchise®"

        Args:
            game_name (str): The full name of the game.

        Returns:
            Optional[str]: The detected franchise name, or None if not detected.
        """
        if not game_name:
            return None

        # Remove trademark symbols
        name = game_name.replace('™', '').replace('®', '').strip()

        # Split on common delimiters
        for delimiter in [':', ' - ', ' – ']:
            if delimiter in name:
                parts = name.split(delimiter)
                # Return first part if it looks like a franchise name
                # (not too short, not all numbers)
                potential = parts[0].strip()
                if len(potential) > 3 and not potential.isdigit():
                    return potential

        # Check for numbered sequels (e.g., "Half-Life 2")
        import re
        match = re.match(r'^([A-Za-z\s]+?)\s+\d+', name)
        if match:
            return match.group(1).strip()

        return None
