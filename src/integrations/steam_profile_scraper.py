"""Steam Community Profile games page scraper.

Fetches the complete game list from the user's Steam Community profile
page. Works even without Steam Client running. Catches games that
GetOwnedGames sometimes misses (F2P, recently added, gifted, etc.).

The profile page embeds ALL owned games as a React Query SSR cache
in the initial HTML response (~10MB for large libraries).
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

import requests

from src.utils.i18n import t

logger = logging.getLogger("steamlibmgr.profile_scraper")

__all__ = ["SteamProfileScraper", "ProfileGame"]


@dataclass(frozen=True)
class ProfileGame:
    """A game entry from the Steam Community profile page.

    Args:
        app_id: Steam application ID.
        name: Game display name.
        playtime_forever: Total playtime in minutes.
    """

    app_id: int
    name: str
    playtime_forever: int = 0


class SteamProfileScraper:
    """Fetches game lists from Steam Community profile pages.

    Uses the public profile page which contains ALL owned games as
    server-side rendered data. No API key required for public profiles.
    """

    PROFILE_URL_BY_ID = "https://steamcommunity.com/profiles/{steamid}/games?tab=all"

    _HEADERS: dict[str, str] = {
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 " "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
    }

    # Regex to extract game objects from the SSR HTML.
    # The profile page embeds game data in a React Query dehydrated state
    # as JSON arrays.  The data may be double-escaped depending on where
    # it appears in the HTML (inside <script> vs attribute).
    #
    # We look for the characteristic triple: appid, name, playtime_forever
    # which uniquely identifies a game object in the SSR cache.
    _GAME_PATTERN: re.Pattern[str] = re.compile(
        r'"appid"\s*:\s*(\d+)\s*,'  # "appid": 12345,
        r'\s*"name"\s*:\s*"((?:[^"\\]|\\.)*)"'  # "name": "Game Name"
        r'.*?"playtime_forever"\s*:\s*(\d+)',  # "playtime_forever": 42
        re.DOTALL,
    )

    def __init__(self, session_cookie: str | None = None) -> None:
        """Initialize the scraper.

        Args:
            session_cookie: Optional steamLoginSecure cookie for private profiles.
        """
        self._session = requests.Session()
        self._session.headers.update(self._HEADERS)
        if session_cookie:
            self._session.cookies.set(
                "steamLoginSecure",
                session_cookie,
                domain="steamcommunity.com",
            )

    def fetch_games(self, steamid64: str) -> list[ProfileGame]:
        """Fetch all games from a user's profile by SteamID64.

        Args:
            steamid64: The user's 64-bit Steam ID.

        Returns:
            List of ProfileGame objects, empty on failure.
        """
        url = self.PROFILE_URL_BY_ID.format(steamid=steamid64)
        return self._fetch_and_parse(url)

    def _fetch_and_parse(self, url: str) -> list[ProfileGame]:
        """Fetch profile page and extract game data.

        Args:
            url: Full URL to the games page.

        Returns:
            List of ProfileGame objects.
        """
        try:
            # timeout=(connect, read) per Alex annotation 5
            response = self._session.get(url, timeout=(10, 60))
            response.raise_for_status()

            # Use .content.decode() to avoid slow charset auto-detection
            # on the ~10MB response (Alex annotation 5)
            html = response.content.decode("utf-8")
            return self._parse_games_from_html(html)

        except requests.RequestException as e:
            logger.warning(t("logs.profile_scraper.request_error", error=str(e)))
            return []

    def _parse_games_from_html(self, html: str) -> list[ProfileGame]:
        """Parse game objects from the SSR HTML.

        The Steam community profile page embeds all game data in a React
        Query SSR cache.  We extract game objects using regex since parsing
        the full 10MB HTML with a DOM parser is impractical.

        Falls back to JSON array extraction if regex finds nothing.

        Args:
            html: The full HTML content of the games page.

        Returns:
            List of ProfileGame objects.
        """
        games: dict[int, ProfileGame] = {}

        # Strategy 1: Direct regex on unescaped JSON in <script> tags
        for match in self._GAME_PATTERN.finditer(html):
            app_id = int(match.group(1))
            name = match.group(2).replace('\\"', '"').replace("\\\\", "\\")
            playtime = int(match.group(3))

            if app_id > 0 and app_id not in games:
                games[app_id] = ProfileGame(
                    app_id=app_id,
                    name=name,
                    playtime_forever=playtime,
                )

        # Strategy 2: Try to find JSON arrays with game objects
        # (handles double-escaped variants in React dehydrated state)
        if not games:
            games = self._try_json_extraction(html)

        if games:
            logger.info(t("logs.profile_scraper.parsed_games", count=len(games)))
        else:
            logger.warning(t("logs.profile_scraper.no_games_found"))

        return list(games.values())

    @staticmethod
    def _try_json_extraction(html: str) -> dict[int, ProfileGame]:
        """Try to extract games from JSON arrays embedded in the HTML.

        Some profile pages embed the data as escaped JSON strings within
        a dehydrated React Query state object.

        Args:
            html: The full HTML content.

        Returns:
            Dict mapping app_id to ProfileGame.
        """
        games: dict[int, ProfileGame] = {}

        # Look for arrays of game objects (e.g., [{appid:10,...},{appid:20,...}])
        for match in re.finditer(r'\[(\{[^]]*"appid"[^]]*\})\]', html):
            try:
                array_str = f"[{match.group(1)}]"
                data = json.loads(array_str)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and "appid" in item:
                            app_id = int(item["appid"])
                            name = str(item.get("name", ""))
                            playtime = int(item.get("playtime_forever", 0))
                            if app_id > 0 and name and app_id not in games:
                                games[app_id] = ProfileGame(
                                    app_id=app_id,
                                    name=name,
                                    playtime_forever=playtime,
                                )
            except (json.JSONDecodeError, ValueError, TypeError):
                continue

        return games
