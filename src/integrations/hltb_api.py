"""HowLongToBeat API client for game completion time data.

Queries the HLTB search API directly with automatic endpoint
discovery and auth-token handling. Matches results by exact name
or fuzzy name similarity using Levenshtein distance.
No external library dependency required.
"""

from __future__ import annotations

import logging
import random
import re
import time
import unicodedata
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("steamlibmgr.hltb_api")

__all__ = ["HLTBClient", "HLTBResult"]

_HLTB_BASE = "https://howlongtobeat.com"

# Realistic browser User-Agents for rotation
_USER_AGENTS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    " (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15"
    " (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
)

# Browser-like headers required to avoid 403 from HLTB's bot protection
_BROWSER_HEADERS: dict[str, str] = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

# Regex: fetch(`/api/<path>/init?...`)  — to identify the init+search pair
_INIT_PATTERN = re.compile(r"""/api/(\w+)/init""")

# Symbols to strip from game names (TM, (R), (C), also text forms)
# Uses a space replacement to avoid "Velocity®Ultra" → "VelocityUltra"
_SYMBOL_PATTERN = re.compile(r"[\u2122\u00AE\u00A9]|\(TM\)|\(R\)")

# Superscript digits → normal digits
_SUPERSCRIPT_MAP = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")

# Bare year at end of name without parentheses: "Game 2014" → "Game"
_BARE_YEAR_PATTERN = re.compile(r"\s+[12][09]\d\d$")

# Parenthetical noise to strip before search (year tags, Classic, etc.)
_PAREN_NOISE_PATTERN = re.compile(
    r"\s*\("
    r"(?:"
    r"[12][09]\d\d"  # Year: (2003), (1999), (2020)
    r"|Classic"  # (Classic)
    r"|CLASSIC"  # (CLASSIC)
    r"|Legacy"  # (Legacy)
    r"|\d+[Dd]\s*Remake"  # (3D Remake)
    r")\)"
    r"\s*",
)

# Edition/subtitle suffixes to strip for a fallback search.
# Inspired by hltb-millennium-plugin's simplify_game_name().
# Applied iteratively until no more changes.
_EDITION_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Anniversary patterns (longer first)
    re.compile(r"\s+\d+[snrt][tdh]\s+Anniversary\s+Edition$", re.IGNORECASE),
    re.compile(r"\s+[-:\u2013\u2014]\s*Anniversary\s+Edition$", re.IGNORECASE),
    re.compile(r"\s+Anniversary\s+Edition$", re.IGNORECASE),
    # Edition suffixes (with optional dash/colon prefix)
    re.compile(
        r"\s+[-:\u2013\u2014]\s*("
        r"Enhanced|Complete|Definitive|Ultimate|Special|Legacy|Maximum|"
        r"Deluxe|Premium|Premium\s+Online|Gold|Platinum|Steam|"
        r"GOTY|Game\s+of\s+the\s+Year"
        r")\s*Edition.*$",
        re.IGNORECASE,
    ),
    re.compile(
        r"\s+("
        r"Enhanced|Complete|Definitive|Ultimate|Special|Legacy|Maximum|"
        r"Deluxe|Premium|Premium\s+Online|Gold|Platinum|Steam|"
        r"GOTY|Game\s+of\s+the\s+Year"
        r")\s*Edition.*$",
        re.IGNORECASE,
    ),
    # Standalone GOTY / Game of the Year
    re.compile(r"\s+[-:\u2013\u2014]\s*GOTY$", re.IGNORECASE),
    re.compile(r"\s+GOTY$", re.IGNORECASE),
    re.compile(r"\s+[-:\u2013\u2014]\s*Game\s+of\s+the\s+Year$", re.IGNORECASE),
    re.compile(r"\s+Game\s+of\s+the\s+Year$", re.IGNORECASE),
    # Remastered / Remake
    re.compile(r"\s+[-:\u2013\u2014]\s*Remastered$", re.IGNORECASE),
    re.compile(r"\s+Remastered$", re.IGNORECASE),
    re.compile(r"\s+\(\d*[Dd]\s*Remake\)$"),
    re.compile(r"\s+[-:\u2013\u2014]\s*Remake$", re.IGNORECASE),
    re.compile(r"\s+Remake$", re.IGNORECASE),
    # Director's Cut
    re.compile(r"\s+[-:\u2013\u2014]\s*Director'?s?\s+Cut$", re.IGNORECASE),
    re.compile(r"\s+Director'?s?\s+Cut$", re.IGNORECASE),
    # Collection / Classic / HD / Enhanced standalone
    re.compile(r"\s+Collection$", re.IGNORECASE),
    re.compile(r"\s+\(Legacy\)$", re.IGNORECASE),
    re.compile(r"\s+[-:\u2013\u2014]\s*Classic$", re.IGNORECASE),
    re.compile(r"\s+Classic$", re.IGNORECASE),
    re.compile(r"\s+\(CLASSIC\)$"),
    re.compile(r"\s+HD$", re.IGNORECASE),
    re.compile(r"\s+Enhanced$", re.IGNORECASE),
    re.compile(r"\s+Redux$", re.IGNORECASE),
    re.compile(r"\s+Reloaded$", re.IGNORECASE),
    # Single Player / Online / Season N
    re.compile(r"\s+[-:\u2013\u2014]\s*Single\s+Player$", re.IGNORECASE),
    re.compile(r"\s+Single\s+Player$", re.IGNORECASE),
    re.compile(r"\s+[-:\u2013\u2014]\s*Season\s+\d+$", re.IGNORECASE),
    re.compile(r"\s+Season\s+\d+$", re.IGNORECASE),
    re.compile(r"\s+Online$", re.IGNORECASE),
    # Year tags at end: (2013), (2020), etc.
    re.compile(r"\s+\([12][09]\d\d\)$"),
    # Clean up trailing punctuation left after stripping
    re.compile(r"\s*[-:\u2013\u2014]\s*$"),
)

# Retry threshold: retry with simplified name if Levenshtein distance
# exceeds 20% of name length (minimum 5 edits)
_RETRY_DISTANCE_RATIO = 0.2
_RETRY_DISTANCE_MIN = 5

# Cache TTL for discovered endpoint and auth token (5 minutes, like Millennium plugin)
_CACHE_TTL = 300


@dataclass(frozen=True)
class HLTBResult:
    """Frozen dataclass for HowLongToBeat completion time data.

    Attributes:
        game_name: Name of the game as returned by HLTB.
        main_story: Hours to complete the main story.
        main_extras: Hours to complete main story + extras.
        completionist: Hours for 100% completion.
    """

    game_name: str
    main_story: float
    main_extras: float
    completionist: float


class HLTBClient:
    """Client for searching HowLongToBeat game data.

    Automatically discovers the current API endpoint and obtains
    auth tokens. Matches search results by exact name first,
    then by Levenshtein distance with popularity tiebreaker.

    Supports Steam Import API for bulk ID mapping (steam_app_id → hltb_game_id)
    and direct game-by-ID fetching via Next.js data routes.
    """

    def __init__(self) -> None:
        """Initializes the HLTBClient with empty endpoint cache."""
        self._session = requests.Session()
        self._session.headers.update(_BROWSER_HEADERS)
        self._api_path: str = ""
        self._auth_token: str = ""
        self._build_id: str = ""
        self._cache_time: float = 0.0
        self._id_cache: dict[int, int] = {}  # steam_app_id → hltb_game_id

    @staticmethod
    def is_available() -> bool:
        """Always available — uses direct HTTP API, no external library needed.

        Returns:
            True always.
        """
        return True

    def set_id_cache(self, mappings: dict[int, int]) -> None:
        """Populates the steam_app_id → hltb_game_id cache.

        Called by the enrichment service after loading from DB + API.

        Args:
            mappings: Dict mapping Steam app IDs to HLTB game IDs.
        """
        self._id_cache = dict(mappings)
        logger.info("HLTB ID cache loaded with %d mappings", len(self._id_cache))

    def get_id_cache(self) -> dict[int, int]:
        """Returns the current steam_app_id → hltb_game_id cache.

        Returns:
            Copy of the ID cache dict.
        """
        return dict(self._id_cache)

    def fetch_steam_import(self, steam_user_id: str) -> dict[int, int]:
        """Fetches HLTB game ID mappings for a Steam user's entire library.

        Uses the HLTB Steam Import endpoint to get a bulk mapping of
        steam_app_id → hltb_game_id for all games the user owns.

        Args:
            steam_user_id: 64-bit Steam ID as string.

        Returns:
            Dict mapping steam_app_id to hltb_game_id.
        """
        if not self._ensure_api_ready():
            return {}

        url = f"{_HLTB_BASE}/api/steam/getSteamImportData"

        try:
            resp = self._session.post(
                url,
                json={
                    "steamUserId": steam_user_id,
                    "steamOmitData": 0,
                },
                headers={
                    "Content-Type": "application/json",
                    "Origin": _HLTB_BASE,
                    "Referer": f"{_HLTB_BASE}/",
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("HLTB Steam Import failed: %s", exc)
            return {}

        games = data.get("games", [])
        mappings: dict[int, int] = {}
        for entry in games:
            steam_id = entry.get("steam_id")
            hltb_id = entry.get("hltb_id")
            if steam_id and hltb_id:
                mappings[int(steam_id)] = int(hltb_id)

        logger.info("HLTB Steam Import: %d mappings from %d entries", len(mappings), len(games))
        return mappings

    def fetch_game_by_id(self, hltb_game_id: int) -> HLTBResult | None:
        """Fetches HLTB completion times for a game by its HLTB game ID.

        Uses the Next.js data route to get game details directly,
        bypassing the search API entirely.

        Args:
            hltb_game_id: The HLTB game ID.

        Returns:
            HLTBResult with completion times, or None on failure.
        """
        if not self._ensure_api_ready():
            return None

        if not self._build_id:
            logger.warning("No buildId available for HLTB game-by-ID fetch")
            return None

        url = f"{_HLTB_BASE}/_next/data/{self._build_id}/game/{hltb_game_id}.json"

        try:
            resp = self._session.get(
                url,
                headers={
                    "Referer": f"{_HLTB_BASE}/",
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("HLTB game-by-ID fetch failed for %d: %s", hltb_game_id, exc)
            return None

        # Navigate: pageProps.game.data.game[0]
        try:
            game_list = data["pageProps"]["game"]["data"]["game"]
            if not game_list:
                return None
            game_data = game_list[0]
        except (KeyError, IndexError, TypeError):
            logger.warning("HLTB game-by-ID: unexpected response structure for %d", hltb_game_id)
            return None

        return self._to_result(game_data)

    def search_game(self, name: str, app_id: int = 0) -> HLTBResult | None:
        """Searches HLTB for a game and returns the best match.

        Uses a three-level strategy:
        1. ID cache lookup (steam_app_id → hltb_game_id → fetch by ID).
        2. Name search with the full sanitized name.
        3. If match is poor or missing, retry with edition suffixes stripped.

        Matching priority per name search pass:
        1. Exact sanitized name match.
        2. Levenshtein distance (sorted by distance, then popularity).

        Args:
            name: Game name to search for.
            app_id: Steam AppID for cache lookup (0 to skip).

        Returns:
            HLTBResult with completion times, or None if not found.
        """
        # Level 1: ID cache lookup
        if app_id and app_id in self._id_cache:
            hltb_id = self._id_cache[app_id]
            result = self.fetch_game_by_id(hltb_id)
            if result:
                logger.debug("HLTB cache hit: app_id=%d → hltb_id=%d", app_id, hltb_id)
                return result
            logger.debug("HLTB cache hit but fetch failed: app_id=%d → hltb_id=%d", app_id, hltb_id)

        sanitized = self._normalize_name(name)
        if not sanitized:
            return None

        if not self._ensure_api_ready():
            return None

        # Level 2: search with full sanitized name
        match, distance = self._search_and_find(sanitized)
        if match is not None and distance == 0:
            return self._to_result(match)

        # Level 3: retry with simplified name
        simplified = _simplify_name(sanitized)
        threshold = max(_RETRY_DISTANCE_MIN, int(len(sanitized) * _RETRY_DISTANCE_RATIO))
        should_retry = simplified != sanitized and (match is None or distance > threshold)

        if should_retry:
            logger.debug("HLTB fallback search: '%s' → '%s'", sanitized, simplified)
            retry_match, retry_distance = self._search_and_find(simplified)
            if retry_match is not None and (match is None or retry_distance < distance):
                match = retry_match

        if match is not None:
            return self._to_result(match)
        return None

    def _search_and_find(self, search_name: str) -> tuple[dict | None, int]:
        """Performs an HLTB API search and returns the best match with distance.

        Args:
            search_name: Cleaned game name to search for.

        Returns:
            Tuple of (best_match_dict, levenshtein_distance) or (None, 0).
        """
        payload = {
            "searchType": "games",
            "searchTerms": search_name.split(),
            "searchPage": 1,
            "size": 20,
            "searchOptions": {
                "games": {
                    "userId": 0,
                    "platform": "",
                    "sortCategory": "popular",
                    "rangeCategory": "main",
                    "rangeTime": {"min": 0, "max": 0},
                    "gameplay": {
                        "perspective": "",
                        "flow": "",
                        "genre": "",
                        "difficulty": "",
                    },
                    "rangeYear": {"max": "", "min": ""},
                    "modifier": "hide_dlc",
                },
                "users": {"sortCategory": "postcount"},
                "lists": {"sortCategory": "follows"},
                "filter": "",
                "sort": 0,
                "randomizer": 0,
            },
            "useCache": True,
        }

        search_url = f"{_HLTB_BASE}/api/{self._api_path}"

        try:
            resp = self._session.post(
                search_url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Origin": _HLTB_BASE,
                    "Referer": f"{_HLTB_BASE}/",
                    "x-auth-token": self._auth_token,
                },
                timeout=15,
            )
            # If 404 or 403, invalidate cache and retry once
            if resp.status_code in (403, 404):
                logger.info("HLTB endpoint returned %d, refreshing...", resp.status_code)
                self._cache_time = 0.0
                if not self._ensure_api_ready():
                    return None, 0
                search_url = f"{_HLTB_BASE}/api/{self._api_path}"
                resp = self._session.post(
                    search_url,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Origin": _HLTB_BASE,
                        "Referer": f"{_HLTB_BASE}/",
                        "x-auth-token": self._auth_token,
                    },
                    timeout=15,
                )

            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("HLTB search failed for '%s': %s", search_name, exc)
            return None, 0

        results = data.get("data", [])
        if not results:
            return None, 0

        return self._find_best_match(results, search_name)

    def _ensure_api_ready(self) -> bool:
        """Discovers the API endpoint and obtains an auth token if needed.

        Also extracts the Next.js buildId for game-by-ID fetching.

        Returns:
            True if the API endpoint and token are ready.
        """
        now = time.time()
        if self._api_path and self._auth_token and (now - self._cache_time) < _CACHE_TTL:
            return True

        # Rotate User-Agent
        self._session.headers["User-Agent"] = random.choice(_USER_AGENTS)

        try:
            homepage_html = self._fetch_homepage()
            if not homepage_html:
                return False

            api_path = self._discover_endpoint(homepage_html)
            if not api_path:
                logger.error("Failed to discover HLTB API endpoint")
                return False

            auth_token = self._get_auth_token(api_path)
            if not auth_token:
                logger.error("Failed to obtain HLTB auth token")
                return False

            build_id = self._discover_build_id(homepage_html)

            self._api_path = api_path
            self._auth_token = auth_token
            self._build_id = build_id
            self._cache_time = now
            logger.info("HLTB API ready: /api/%s (buildId=%s)", api_path, build_id or "N/A")
            return True

        except Exception as exc:
            logger.error("HLTB API initialization failed: %s", exc)
            return False

    def _fetch_homepage(self) -> str:
        """Fetches the HLTB homepage HTML.

        Returns:
            Homepage HTML string, or empty string on failure.
        """
        try:
            resp = self._session.get(f"{_HLTB_BASE}/", timeout=15)
            resp.raise_for_status()
            return resp.text
        except Exception as exc:
            logger.warning("Failed to fetch HLTB homepage: %s", exc)
            return ""

    def _discover_endpoint(self, homepage_html: str) -> str:
        """Discovers the current HLTB search API path from the website JS.

        Scans all JS chunks for fetch("/api/<path>/init") patterns
        to find the search endpoint.

        Args:
            homepage_html: The HLTB homepage HTML.

        Returns:
            The API path suffix (e.g. 'finder'), or empty string on failure.
        """
        soup = BeautifulSoup(homepage_html, "html.parser")
        scripts = soup.find_all("script", src=True)

        # Collect all _next/static/chunks/*.js URLs
        chunk_urls: list[str] = []
        for tag in scripts:
            src = str(tag.get("src", ""))
            if "/_next/static/chunks/" in src and not src.endswith("Manifest.js"):
                url = src if src.startswith("http") else f"{_HLTB_BASE}{src}"
                chunk_urls.append(url)

        for url in chunk_urls:
            try:
                js_resp = self._session.get(url, timeout=15)
                js_resp.raise_for_status()
                js_text = js_resp.text
            except Exception:
                continue

            # Look for /api/<path>/init pattern — this identifies the search endpoint
            for match in _INIT_PATTERN.finditer(js_text):
                path = match.group(1)
                # Skip non-search endpoints
                if path in ("user", "logout", "error", "game", "find"):
                    continue
                logger.debug("Found HLTB endpoint via init pattern: /api/%s", path)
                return path

        logger.warning("Could not discover HLTB endpoint from JS bundles")
        return ""

    @staticmethod
    def _discover_build_id(homepage_html: str) -> str:
        """Extracts the Next.js buildId from the homepage HTML.

        Looks for the _buildManifest.js script tag which contains
        the buildId in its URL path.

        Args:
            homepage_html: The HLTB homepage HTML.

        Returns:
            Build ID string, or empty string if not found.
        """
        soup = BeautifulSoup(homepage_html, "html.parser")
        for tag in soup.find_all("script", src=True):
            src = str(tag.get("src", ""))
            if "_buildManifest.js" in src:
                # URL format: /_next/static/<buildId>/_buildManifest.js
                parts = src.split("/")
                try:
                    manifest_idx = parts.index("_buildManifest.js")
                    if manifest_idx >= 1:
                        build_id = parts[manifest_idx - 1]
                        logger.debug("Discovered HLTB buildId: %s", build_id)
                        return build_id
                except (ValueError, IndexError):
                    pass
        logger.debug("Could not discover HLTB buildId from homepage")
        return ""

    def _get_auth_token(self, api_path: str) -> str:
        """Obtains an auth token from the HLTB init endpoint.

        Args:
            api_path: The discovered API path suffix.

        Returns:
            Auth token string, or empty string on failure.
        """
        timestamp_ms = int(time.time() * 1000)
        init_url = f"{_HLTB_BASE}/api/{api_path}/init?t={timestamp_ms}"

        try:
            resp = self._session.get(
                init_url,
                headers={
                    "Referer": f"{_HLTB_BASE}/",
                    "Origin": _HLTB_BASE,
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            token = data.get("token", "")
            if token:
                logger.debug("Obtained HLTB auth token")
            return token
        except Exception as exc:
            logger.warning("Failed to get HLTB auth token: %s", exc)
            return ""

    @staticmethod
    def _find_best_match(
        results: list[dict],
        search_name: str,
    ) -> tuple[dict | None, int]:
        """Finds the best matching game from HLTB search results.

        Uses a two-tier approach:
        1. Exact sanitized name match (distance 0).
        2. Levenshtein distance, with popularity (comp_all_count) as tiebreaker.

        Args:
            results: List of game data dicts from the HLTB API.
            search_name: Cleaned game name for comparison.

        Returns:
            Tuple of (best_match, distance) or (None, 0) if no match.
        """
        sanitized_query = _normalize_for_compare(search_name)

        # 1. Exact name match
        for r in results:
            if _normalize_for_compare(r.get("game_name", "")) == sanitized_query:
                return r, 0

        # 2. Levenshtein distance with popularity tiebreaker
        candidates: list[tuple[int, int, dict]] = []
        for r in results:
            r_name = _normalize_for_compare(r.get("game_name", ""))
            dist = _levenshtein(sanitized_query, r_name)
            popularity = r.get("comp_all_count", 0)
            candidates.append((dist, -popularity, r))

        if not candidates:
            return None, 0

        # Sort by distance ASC, then by popularity DESC (negative = more popular first)
        candidates.sort(key=lambda c: (c[0], c[1]))
        best_dist, _, best_match = candidates[0]

        return best_match, best_dist

    @staticmethod
    def _normalize_name(name: str) -> str:
        """Strips trademark and copyright symbols for cleaner search terms.

        Does NOT strip edition suffixes — that is handled as a fallback
        in search_game() when the first search attempt has a poor match.

        Args:
            name: Raw game name.

        Returns:
            Cleaned name suitable for HLTB search.
        """
        # Replace symbols with space (keeps word boundaries: "Velocity®Ultra" → "Velocity Ultra")
        cleaned = _SYMBOL_PATTERN.sub(" ", name).strip()
        # Normalize superscript digits: ² → 2
        cleaned = cleaned.translate(_SUPERSCRIPT_MAP)
        # Normalize backtick to apostrophe
        cleaned = cleaned.replace("`", "'")
        # Strip special unicode chars: ∞, etc.
        cleaned = re.sub(r"[∞]", "", cleaned)
        # Strip parenthetical noise: (2003), (Classic), etc.
        cleaned = _PAREN_NOISE_PATTERN.sub("", cleaned).strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned

    @staticmethod
    def _to_result(match: dict) -> HLTBResult:
        """Converts an HLTB API result dict to an HLTBResult.

        Args:
            match: Raw game data dict from the HLTB API.

        Returns:
            HLTBResult with hours converted from seconds.
        """
        return HLTBResult(
            game_name=match.get("game_name", ""),
            main_story=match.get("comp_main", 0) / 3600,
            main_extras=match.get("comp_plus", 0) / 3600,
            completionist=match.get("comp_100", 0) / 3600,
        )


def _simplify_name(name: str) -> str:
    """Strips common edition/remaster/year suffixes for fallback search.

    Iterates _EDITION_PATTERNS in a loop until no more changes occur,
    handling stacked suffixes like "Enhanced Edition Director's Cut".

    Args:
        name: Sanitized game name.

    Returns:
        Simplified name with edition suffixes removed.
    """
    # Normalize Unicode dashes to ASCII hyphen with spaces for pattern matching
    name = re.sub(r"[\u2013\u2014]", " - ", name)
    name = re.sub(r"\s+", " ", name).strip()

    prev = ""
    while prev != name:
        prev = name
        for pattern in _EDITION_PATTERNS:
            name = pattern.sub("", name).strip()
        # Also strip bare year at end: "Lords Of The Fallen 2014" → "Lords Of The Fallen"
        name = _BARE_YEAR_PATTERN.sub("", name).strip()
    return re.sub(r"\s+", " ", name).strip()


def _normalize_for_compare(name: str) -> str:
    """Normalizes a name for comparison (lowercase, no accents, no special chars).

    Args:
        name: Name to normalize.

    Returns:
        Lowercased name with accents and special characters removed.
    """
    result = name.lower()
    result = unicodedata.normalize("NFD", result)
    result = re.sub(r"[\u0300-\u036f]", "", result)
    result = re.sub(r"[^a-z0-9\s\-/]", "", result)
    return result.strip()


def _levenshtein(s1: str, s2: str) -> int:
    """Calculates the Levenshtein (edit) distance between two strings.

    Args:
        s1: First string.
        s2: Second string.

    Returns:
        Minimum number of single-character edits to transform s1 into s2.
    """
    if s1 == s2:
        return 0
    len1, len2 = len(s1), len(s2)
    if len1 == 0:
        return len2
    if len2 == 0:
        return len1

    # Use two-row optimization for O(min(m,n)) space
    if len1 > len2:
        s1, s2 = s2, s1
        len1, len2 = len2, len1

    prev_row = list(range(len1 + 1))
    for j in range(1, len2 + 1):
        curr_row = [j] + [0] * len1
        for i in range(1, len1 + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            curr_row[i] = min(
                curr_row[i - 1] + 1,  # insertion
                prev_row[i] + 1,  # deletion
                prev_row[i - 1] + cost,  # substitution
            )
        prev_row = curr_row

    return prev_row[len1]
