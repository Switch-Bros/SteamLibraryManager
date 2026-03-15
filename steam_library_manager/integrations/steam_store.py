#
# steam_library_manager/integrations/steam_store.py
# Steam Store integration for fetching tags and age ratings.
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
import time
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any

import requests
from bs4 import BeautifulSoup
from steam_library_manager.utils.age_ratings import ESRB_TO_PEGI, USK_TO_PEGI
from steam_library_manager.utils.i18n import t
from steam_library_manager.utils.timeouts import HTTP_TIMEOUT

logger = logging.getLogger("steamlibmgr.steam_store")


__all__ = ["SteamStoreScraper"]


class SteamStoreScraper:
    """Fetches game tags and age ratings from the Steam Store."""

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
        """Initializes the SteamStoreScraper."""
        self.cache_dir = cache_dir / "store_tags"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.language_code = language
        self.steam_language = self.STEAM_LANGUAGES.get(language, "english")
        self.last_request_time = 0.0
        self.min_request_interval = 1.0  # Reduced from 1.5 - Steam tolerates 1.0

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
        """Returns cached JSON data if the file exists and is fresh enough."""
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
        """Fetches tags for a game from the Steam Store page."""
        cache_file = self.cache_dir / f"{app_id}_{self.language_code}.json"

        # Check Cache
        cached = self._check_cache(cache_file)
        if cached is not None:
            return cached

        # Rate Limiting
        self._rate_limit()

        # Fetch from Steam
        try:
            self.last_request_time = time.time()
            cookies = {"Steam_Language": self.steam_language}

            # Secure HTTPS link
            url = f"https://store.steampowered.com/app/{app_id}/"

            response = requests.get(url, cookies=cookies, timeout=HTTP_TIMEOUT)

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
        """Fetches age rating from Steam Store (API first, HTML fallback)."""
        cache_file = self.cache_dir.parent / "age_ratings" / f"{app_id}.json"
        cache_file.parent.mkdir(exist_ok=True, parents=True)

        # Check Cache
        cached = self._check_cache(cache_file)
        if cached is not None:
            return cached.get("pegi_rating")

        # Rate Limiting
        self._rate_limit()

        # Try API first (fast JSON parse, no age-gate issues)
        pegi_rating = self._fetch_age_rating_from_api(app_id)

        # Fallback to HTML scraping if API has no data
        if not pegi_rating:
            pegi_rating = self._fetch_age_rating_from_html(app_id)

        # Cache result
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
        """Fetches age rating using Steam Store API."""
        try:
            self.last_request_time = time.time()

            # Steam Store API endpoint
            url = f"https://store.steampowered.com/api/appdetails?appids={app_id}"

            response = requests.get(url, timeout=HTTP_TIMEOUT)
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

            # Convert to int (API sometimes returns string)
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
                return None

        except (requests.RequestException, ValueError, KeyError) as e:
            logger.error(t("logs.steam_store.api_fetch_failed", app_id=app_id, error=e))
            return None

    def _fetch_age_rating_from_html(self, app_id: str) -> str | None:
        """Fetches age rating via HTML scraping (fallback method)."""
        try:
            self.last_request_time = time.time()

            # Age-Gate bypass with Unix timestamp
            birthtime = "631152000"  # Unix timestamp for 1990-01-01
            cookies = {
                "Steam_Language": self.steam_language,
                "wants_mature_content": "1",
                "birthtime": birthtime,
                "mature_content": "1",
            }

            url = f"https://store.steampowered.com/app/{app_id}/"
            response = requests.get(url, cookies=cookies, timeout=HTTP_TIMEOUT)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Try multiple methods to find age rating

            # Look for age rating using CSS classes and img src (language-independent)

            # Check for "no age restriction" div (class="game_rating_allages")
            allages_div = soup.find("div", class_="game_rating_allages")
            if allages_div:
                return "3"  # PEGI 3

            # Check for age rating images
            rating_divs = soup.find_all("div", class_=lambda x: x and "rating" in x.lower())
            for div in rating_divs:
                img = div.find("img")
                if img:
                    # Check img src for age numbers (e.g., "/18.png", "/18_" in src)
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

            # Look for PEGI image
            pegi_elem = soup.find("img", alt=lambda x: x and "PEGI" in x)
            if pegi_elem:
                alt_text = str(pegi_elem.get("alt", ""))
                for age in ["18", "16", "12", "7", "3"]:
                    if age in alt_text:
                        return age

            # Look for USK rating (Germany)
            usk_elem = soup.find("img", alt=lambda x: x and "USK" in x)
            if usk_elem:
                alt_text = str(usk_elem.get("alt", ""))
                for usk_age, pegi_age in USK_TO_PEGI.items():
                    if usk_age in alt_text:
                        return pegi_age

            # Look for ESRB rating (USA) - use shared ESRB_TO_PEGI dict
            esrb_elem = soup.find("img", alt=lambda x: x and "ESRB" in x)
            if esrb_elem:
                alt_text = str(esrb_elem.get("alt", "")).lower()
                for esrb_name, pegi_age in ESRB_TO_PEGI.items():
                    if esrb_name in alt_text:
                        return pegi_age

            # Check for age gate div (fallback)
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
        """Check how many games have cached tag data."""
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
        """Detects game franchise from the game name."""
        if not game_name:
            return None

        # Remove trademark symbols
        name = game_name.replace("\u2122", "").replace("\u00ae", "").strip()

        # Split on common delimiters
        for delimiter in [":", " - ", " - "]:
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
