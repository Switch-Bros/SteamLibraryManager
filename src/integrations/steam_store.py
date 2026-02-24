# src/integrations/steam_store.py

"""
Steam Store integration for fetching tags and age ratings.

This module provides functionality to scrape game tags from the Steam Store
in the user's preferred language and detect game franchises based on name patterns.

FIXED: Age rating fetching now uses Steam Store API instead of unreliable HTML scraping.
"""

from __future__ import annotations

import logging
import time
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any

import requests
from bs4 import BeautifulSoup
from src.utils.age_ratings import ESRB_TO_PEGI, USK_TO_PEGI
from src.utils.i18n import t

logger = logging.getLogger("steamlibmgr.steam_store")


__all__ = ["SteamStoreScraper"]


class SteamStoreScraper:
    """
    Fetches game tags and age ratings from the Steam Store.

    This class scrapes the Steam Store page for a game to extract user-defined
    tags and age ratings. It supports multiple languages, implements rate limiting,
    and caches results for 30 days.
    """

    # Language mapping (ISO Code -> Steam Internal Name)
    STEAM_LANGUAGES = {
        "en": "english",
        "de": "german",
        "fr": "french",
        "es": "spanish",
        "it": "italian",
        "pt": "portuguese",
        "ru": "russian",
        "zh": "schinese",
        "ja": "japanese",
        "ko": "koreana",
    }

    def __init__(self, cache_dir: Path, language: str = "en"):
        """
        Initializes the SteamStoreScraper.

        Args:
            cache_dir (Path): Directory to store cached tag data.
            language (str): Language code ('en', 'de', etc.). Defaults to 'en'.
        """
        self.cache_dir = cache_dir / "store_tags"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.language_code = language
        self.steam_language = self.STEAM_LANGUAGES.get(language, "english")
        self.last_request_time = 0.0
        self.min_request_interval = 1.5  # Rate limit: 1.5 seconds between requests

        # Tag blacklist (common but unhelpful tags)
        self.tag_blacklist = {
            "Singleplayer",
            "Multiplayer",
            "Online Co-Op",
            "Local Co-Op",
            "Steam Achievements",
            "Full controller support",
            "Steam Trading Cards",
            "Steam Cloud",
            "Stats",
            "Includes level editor",
            "Steam Workshop",
            "Partial Controller Support",
            "Remote Play on Tablet",
            "Remote Play on TV",
            "Remote Play Together",
            "In-App Purchases",
            "Valve Anti-Cheat enabled",
            "Steam Leaderboards",
        }

    def _check_cache(self, cache_file: Path, max_age_days: int = 30) -> Any | None:
        """Returns cached JSON data if the file exists and is fresh enough.

        Args:
            cache_file: Path to the cache JSON file.
            max_age_days: Maximum age in days before cache is considered stale.

        Returns:
            Parsed JSON data if valid, None if stale or missing.
        """
        if not cache_file.exists():
            return None
        try:
            mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
            if datetime.now() - mtime < timedelta(days=max_age_days):
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except (OSError, json.JSONDecodeError, ValueError):
            pass
        return None

    def _rate_limit(self) -> None:
        """Enforces minimum interval between API requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)

    def fetch_tags(self, app_id: str) -> list[str]:
        """
        Fetches tags for a game from the Steam Store page.

        This method first checks the cache for existing data (valid for 30 days).
        If not cached, it scrapes the Steam Store page, filters out blacklisted
        tags, and caches the result.

        Args:
            app_id (str): The Steam app ID.

        Returns:
            list[str]: A list of tag names in the selected language, or an empty
                      list if fetching failed.
        """
        cache_file = self.cache_dir / f"{app_id}_{self.language_code}.json"

        # 1. Check Cache
        cached = self._check_cache(cache_file)
        if cached is not None:
            return cached

        # 2. Rate Limiting
        self._rate_limit()

        # 3. Fetch from Steam
        try:
            self.last_request_time = time.time()
            cookies = {"Steam_Language": self.steam_language}

            # Secure HTTPS link
            url = f"https://store.steampowered.com/app/{app_id}/"

            response = requests.get(url, cookies=cookies, timeout=10)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")

                # Find tags
                tags = []

                # Selector for tags
                tag_elements = soup.select(".app_tag")
                for tag_elem in tag_elements:
                    tag_text = tag_elem.get_text().strip()
                    if tag_text and tag_text not in self.tag_blacklist and tag_text != "+":
                        tags.append(tag_text)

                # Save (create directory if needed)
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(tags, f)

                return tags

        except (requests.RequestException, AttributeError) as e:
            logger.error(t("logs.steam_store.fetch_error", app_id=app_id, error=str(e)))

        return []

    def fetch_age_rating(self, app_id: str) -> str | None:
        """
        Fetches age rating from Steam Store.

        Priority: HTML scraping FIRST (most reliable!), then API fallback.
        HTML scraping reads directly from Steam Store page and is more accurate
        than the API. Results are cached for 30 days.

        Args:
            app_id (str): The Steam app ID.

        Returns:
            str | None: PEGI rating (e.g., "18", "16", "12", "7", "3") or None if not found.
        """
        cache_file = self.cache_dir.parent / "age_ratings" / f"{app_id}.json"
        cache_file.parent.mkdir(exist_ok=True, parents=True)

        # 1. Check Cache
        cached = self._check_cache(cache_file)
        if cached is not None:
            return cached.get("pegi_rating")

        # 2. Rate Limiting
        self._rate_limit()

        # 3. Try HTML scraping FIRST (most reliable!)
        pegi_rating = self._fetch_age_rating_from_html(app_id)

        # 4. Fallback to API if HTML fails
        if not pegi_rating:
            pegi_rating = self._fetch_age_rating_from_api(app_id)

        # 5. Cache result
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "pegi_rating": pegi_rating,
                        "fetched_at": datetime.now().isoformat(),
                        "method": "api" if pegi_rating else "html_fallback",
                    },
                    f,
                )
        except OSError:
            pass

        return pegi_rating

    def _fetch_age_rating_from_api(self, app_id: str) -> str | None:
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

            if not app_data.get("success"):
                return None

            game_data = app_data.get("data", {})

            # Get required_age from API
            required_age = game_data.get("required_age", 0)

            # ⚠️ FIX: Convert to int (API sometimes returns string!)
            if isinstance(required_age, str):
                try:
                    required_age = int(required_age)
                except ValueError:
                    required_age = 0

            # Convert to PEGI rating
            if required_age >= 18:
                return "18"
            elif required_age >= 16:
                return "16"
            elif required_age >= 12:
                return "12"
            elif required_age >= 6:
                return "7"
            elif required_age > 0:
                return "3"
            else:
                # required_age = 0 means API has no reliable info
                # Return None (HTML was already tried first)
                return None

        except (requests.RequestException, ValueError, KeyError) as e:
            logger.error(t("logs.steam_store.api_fetch_failed", app_id=app_id, error=e))
            return None

    def _fetch_age_rating_from_html(self, app_id: str) -> str | None:
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
            birthtime = "631152000"  # Unix timestamp for 1990-01-01
            cookies = {
                "Steam_Language": self.steam_language,
                "wants_mature_content": "1",
                "birthtime": birthtime,  # FIXED: Now uses proper timestamp!
                "mature_content": "1",
            }

            url = f"https://store.steampowered.com/app/{app_id}/"
            response = requests.get(url, cookies=cookies, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Try multiple methods to find age rating

            # Method 0: Look for age rating using CSS classes and img src (language-independent!)
            # Steam uses consistent class names across all languages

            # Check for "no age restriction" div (class="game_rating_allages")
            allages_div = soup.find("div", class_="game_rating_allages")
            if allages_div:
                # Any text in this div means "no age restriction" regardless of language
                return "3"  # PEGI 3

            # Check for age rating images (class="game_rating_icon" or similar)
            # Look for img with src containing age numbers
            rating_divs = soup.find_all("div", class_=lambda x: x and "rating" in x.lower())
            for div in rating_divs:
                img = div.find("img")
                if img:
                    # Check img src for age numbers (e.g., "/6.png", "/12.png", etc.)
                    src = str(img.get("src", ""))
                    if "/18.png" in src or "/18_" in src:
                        return "18"
                    elif "/16.png" in src or "/16_" in src:
                        return "16"
                    elif "/12.png" in src or "/12_" in src:
                        return "12"
                    elif "/6.png" in src or "/6_" in src:
                        return "7"  # Age 6 = PEGI 7
                    elif "/0.png" in src or "/0_" in src:
                        return "3"  # Age 0 = PEGI 3

                    # Also check alt text (fallback)
                    alt_text = str(img.get("alt", "")).strip()
                    if alt_text in ["18+", "18"]:
                        return "18"
                    elif alt_text in ["16+", "16"]:
                        return "16"
                    elif alt_text in ["12+", "12"]:
                        return "12"
                    elif alt_text in ["6+", "6"]:
                        return "7"
                    elif alt_text in ["0+", "0"]:
                        return "3"

            # Method 1: Look for PEGI image
            pegi_elem = soup.find("img", alt=lambda x: x and "PEGI" in x)
            if pegi_elem:
                alt_text = str(pegi_elem.get("alt", ""))
                for age in ["18", "16", "12", "7", "3"]:
                    if age in alt_text:
                        return age

            # Method 2: Look for USK rating (Germany)
            usk_elem = soup.find("img", alt=lambda x: x and "USK" in x)
            if usk_elem:
                alt_text = str(usk_elem.get("alt", ""))
                for usk_age, pegi_age in USK_TO_PEGI.items():
                    if usk_age in alt_text:
                        return pegi_age

            # Method 3: Look for ESRB rating (USA) — use shared ESRB_TO_PEGI dict
            esrb_elem = soup.find("img", alt=lambda x: x and "ESRB" in x)
            if esrb_elem:
                alt_text = str(esrb_elem.get("alt", "")).lower()
                for esrb_name, pegi_age in ESRB_TO_PEGI.items():
                    if esrb_name in alt_text:
                        return pegi_age

            # Method 4: Check for age gate div (fallback)
            age_divs = soup.find_all("div", class_=lambda x: x and "age" in x.lower())
            for div in age_divs:
                text = div.get_text().lower()
                if "18" in text:
                    return "18"
                elif "16" in text:
                    return "16"
                elif "12" in text:
                    return "12"

            return None

        except (requests.RequestException, AttributeError) as e:
            logger.error(t("logs.steam_store.html_scrape_failed", app_id=app_id, error=e))
            return None

    def get_cache_coverage(self, app_ids: list[str]) -> dict:
        """
        Check how many games have cached tag data.

        This method checks the cache directory to determine how many of the
        provided app IDs already have cached tag data (valid for 30 days).

        Args:
            app_ids: List of Steam app IDs to check.

        Returns:
            dict with keys:
                - 'total': Total number of app IDs checked
                - 'cached': Number of apps with valid cache
                - 'missing': Number of apps without cache
                - 'percentage': Percentage of cached apps (0-100)
        """
        total = len(app_ids)
        cached = 0

        for app_id in app_ids:
            cache_file = self.cache_dir / f"{app_id}_{self.language_code}.json"
            if self._check_cache(cache_file) is not None:
                cached += 1

        missing = total - cached
        percentage = (cached / total * 100) if total > 0 else 0.0

        return {"total": total, "cached": cached, "missing": missing, "percentage": round(percentage, 1)}

    @staticmethod
    def detect_franchise(game_name: str) -> str | None:
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
            str | None: The detected franchise name, or None if not detected.
        """
        if not game_name:
            return None

        # Remove trademark symbols
        name = game_name.replace("™", "").replace("®", "").strip()

        # Split on common delimiters
        for delimiter in [":", " - ", " – "]:
            if delimiter in name:
                parts = name.split(delimiter)
                # Return first part if it looks like a franchise name
                # (not too short, not all numbers)
                potential = parts[0].strip()
                if len(potential) > 3 and not potential.isdigit():
                    return potential

        # Check for numbered sequels (e.g., "Half-Life 2")
        import re

        match = re.match(r"^([A-Za-z\s]+?)\s+\d+", name)
        if match:
            return match.group(1).strip()

        return None
