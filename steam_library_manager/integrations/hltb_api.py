#
# steam_library_manager/integrations/hltb_api.py
# HowLongToBeat API client for fetching game completion times
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#


from __future__ import annotations

import logging
import random
import re
import threading
import time

import requests
from bs4 import BeautifulSoup

from steam_library_manager.utils.timeouts import HTTP_TIMEOUT_API, HTTP_TIMEOUT_LONG

from steam_library_manager.integrations.hltb_models import (
    HLTBResult,
    find_best_match,
    normalize_name,
    simplify_name,
    to_result,
)

logger = logging.getLogger("steamlibmgr.hltb_api")

__all__ = ["HLTBClient", "HLTBResult"]

_BASE = "https://howlongtobeat.com"

# Realistic browser User-Agents for rotation
_UAS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    " (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15"
    " (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
)

# Browser-like headers required to avoid 403 from HLTB's bot protection
_HDRS = {
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

# Regex: fetch(`/api/<path>/init?...`) - identifies the init+search pair
_INIT_RE = re.compile(r"""/api/(\w+)/init""")

# Retry threshold: retry with simplified name if distance
# exceeds 20% of name length (minimum 5 edits)
_RETRY_RATIO = 0.2
_RETRY_MIN = 5

# Cache TTL for discovered endpoint and auth token (5 min)
_TTL = 300


class HLTBClient:
    """Client for searching HowLongToBeat game data."""

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update(_HDRS)
        self._api_path = ""
        self._token = ""
        self._build_id = ""
        self._cached_at = 0.0
        self._id_cache = {}  # steam_app_id -> hltb_game_id
        self._lock = threading.Lock()

    @staticmethod
    def is_available():
        # Always available - uses direct HTTP, no external library needed
        return True

    def set_id_cache(self, mappings):
        # Populate the steam_app_id -> hltb_game_id cache
        self._id_cache = dict(mappings)
        logger.info("HLTB ID cache loaded with %d mappings", len(self._id_cache))

    def get_id_cache(self):
        return dict(self._id_cache)

    def fetch_steam_import(self, steam_user_id):
        # Fetch HLTB game ID mappings for a Steam user's library
        if not self._ensure_ready():
            return {}

        url = "%s/api/steam/getSteamImportData" % _BASE

        try:
            resp = self._session.post(
                url,
                json={
                    "steamUserId": steam_user_id,
                    "steamOmitData": 0,
                },
                headers={
                    "Content-Type": "application/json",
                    "Origin": _BASE,
                    "Referer": "%s/" % _BASE,
                },
                timeout=HTTP_TIMEOUT_API,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("HLTB Steam Import failed: %s", exc)
            return {}

        games = data.get("games", [])
        mappings = {}
        for entry in games:
            sid = entry.get("steam_id")
            hid = entry.get("hltb_id")
            if sid and hid:
                mappings[int(sid)] = int(hid)

        logger.info("HLTB Steam Import: %d mappings from %d entries", len(mappings), len(games))
        return mappings

    def fetch_game_by_id(self, hltb_game_id):
        # Fetch completion times for a game by its HLTB game ID
        if not self._ensure_ready():
            return None

        if not self._build_id:
            logger.warning("No buildId available for HLTB game-by-ID fetch")
            return None

        url = "%s/_next/data/%s/game/%d.json" % (_BASE, self._build_id, hltb_game_id)

        try:
            resp = self._session.get(
                url,
                headers={"Referer": "%s/" % _BASE},
                timeout=HTTP_TIMEOUT_LONG,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("HLTB game-by-ID fetch failed for %d: %s", hltb_game_id, exc)
            return None

        # Navigate: pageProps.game.data.game[0]
        try:
            glist = data["pageProps"]["game"]["data"]["game"]
            if not glist:
                return None
            gdata = glist[0]
        except (KeyError, IndexError, TypeError):
            logger.warning("HLTB game-by-ID: unexpected response structure for %d", hltb_game_id)
            return None

        return to_result(gdata)

    def search_game(self, name, app_id=0):
        # Search HLTB for a game and return the best match

        # ID cache lookup
        if app_id and app_id in self._id_cache:
            hid = self._id_cache[app_id]
            result = self.fetch_game_by_id(hid)
            if result:
                logger.debug("HLTB cache hit: app_id=%d -> hltb_id=%d", app_id, hid)
                return result
            logger.debug("HLTB cache hit but fetch failed: app_id=%d -> hltb_id=%d", app_id, hid)

        clean = normalize_name(name)
        if not clean:
            return None

        if not self._ensure_ready():
            return None

        # Search with full sanitized name
        match, dist = self._search(clean)
        if match is not None and dist == 0:
            return to_result(match)

        # Retry with simplified name if distance is too high
        simple = simplify_name(clean)
        thresh = max(_RETRY_MIN, int(len(clean) * _RETRY_RATIO))
        should_retry = simple != clean and (match is None or dist > thresh)

        if should_retry:
            logger.debug("HLTB fallback search: '%s' -> '%s'", clean, simple)
            retry_match, retry_dist = self._search(simple)
            if retry_match is not None and (match is None or retry_dist < dist):
                match = retry_match

        if match is not None:
            return to_result(match)
        return None

    def _post(self, payload):
        # Send search POST to the HLTB API
        return self._session.post(
            "%s/api/%s" % (_BASE, self._api_path),
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Origin": _BASE,
                "Referer": "%s/" % _BASE,
                "x-auth-token": self._token,
            },
            timeout=HTTP_TIMEOUT_LONG,
        )

    def _search(self, query):
        # Perform HLTB API search and return (best_match_dict, distance)
        payload = {
            "searchType": "games",
            "searchTerms": query.split(),
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

        try:
            resp = self._post(payload)
            # If 404 or 403, invalidate cache and retry once
            if resp.status_code in (403, 404):
                logger.info("HLTB endpoint returned %d, refreshing...", resp.status_code)
                self._cached_at = 0.0
                if not self._ensure_ready():
                    return None, 0
                resp = self._post(payload)

            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("HLTB search failed for '%s': %s", query, exc)
            return None, 0

        results = data.get("data", [])
        if not results:
            return None, 0

        return find_best_match(results, query)

    def _ensure_ready(self):
        # Discover API endpoint and obtain auth token if needed
        now = time.time()
        if self._api_path and self._token and (now - self._cached_at) < _TTL:
            return True

        with self._lock:
            # Double-check after acquiring lock
            now = time.time()
            if self._api_path and self._token and (now - self._cached_at) < _TTL:
                return True

            # Rotate User-Agent
            self._session.headers["User-Agent"] = random.choice(_UAS)

            try:
                html = self._get_homepage()
                if not html:
                    return False

                path = self._find_endpoint(html)
                if not path:
                    logger.error("Failed to discover HLTB API endpoint")
                    return False

                token = self._get_token(path)
                if not token:
                    logger.error("Failed to obtain HLTB auth token")
                    return False

                bid = self._find_build_id(html)

                self._api_path = path
                self._token = token
                self._build_id = bid
                self._cached_at = now
                logger.info("HLTB API ready: /api/%s (buildId=%s)", path, bid or "N/A")
                return True

            except Exception as exc:
                logger.error("HLTB API initialization failed: %s", exc)
                return False

    def _get_homepage(self):
        # Fetch HLTB homepage HTML
        try:
            resp = self._session.get("%s/" % _BASE, timeout=HTTP_TIMEOUT_LONG)
            resp.raise_for_status()
            return resp.text
        except Exception as exc:
            logger.warning("Failed to fetch HLTB homepage: %s", exc)
            return ""

    def _find_endpoint(self, html):
        # Discover current HLTB search API path from the website JS
        soup = BeautifulSoup(html, "html.parser")
        scripts = soup.find_all("script", src=True)

        # Collect all _next/static/chunks/*.js URLs
        chunk_urls = []
        for tag in scripts:
            src = str(tag.get("src", ""))
            if "/_next/static/chunks/" in src and not src.endswith("Manifest.js"):
                url = src if src.startswith("http") else "%s%s" % (_BASE, src)
                chunk_urls.append(url)

        for url in chunk_urls:
            try:
                js_resp = self._session.get(url, timeout=HTTP_TIMEOUT_LONG)
                js_resp.raise_for_status()
                js_text = js_resp.text
            except Exception as exc:
                logger.debug("Failed to fetch HLTB JS chunk: %s", type(exc).__name__)
                continue

            # Look for /api/<path>/init pattern
            for m in _INIT_RE.finditer(js_text):
                p = m.group(1)
                # Skip non-search endpoints
                if p in ("user", "logout", "error", "game", "find"):
                    continue
                logger.debug("Found HLTB endpoint via init pattern: /api/%s", p)
                return p

        logger.warning("Could not discover HLTB endpoint from JS bundles")
        return ""

    @staticmethod
    def _find_build_id(html):
        # Extract the Next.js buildId from the homepage HTML
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup.find_all("script", src=True):
            src = str(tag.get("src", ""))
            if "_buildManifest.js" in src:
                # URL format: /_next/static/<buildId>/_buildManifest.js
                parts = src.split("/")
                try:
                    idx = parts.index("_buildManifest.js")
                    if idx >= 1:
                        bid = parts[idx - 1]
                        logger.debug("Discovered HLTB buildId: %s", bid)
                        return bid
                except (ValueError, IndexError):
                    pass
        logger.debug("Could not discover HLTB buildId from homepage")
        return ""

    def _get_token(self, api_path):
        # Obtain auth token from the HLTB init endpoint
        ts = int(time.time() * 1000)
        url = "%s/api/%s/init?t=%d" % (_BASE, api_path, ts)

        try:
            resp = self._session.get(
                url,
                headers={
                    "Referer": "%s/" % _BASE,
                    "Origin": _BASE,
                },
                timeout=HTTP_TIMEOUT_LONG,
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
