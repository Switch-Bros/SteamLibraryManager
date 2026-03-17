#
# steam_library_manager/integrations/steam_profile_scraper.py
# Scrapes Steam community profile for game data
#
# Copyright 2025 SwitchBros
# MIT License
#

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

import requests

from steam_library_manager.utils.i18n import t
from steam_library_manager.utils.timeouts import HTTP_TIMEOUT_SCRAPE

logger = logging.getLogger("steamlibmgr.profile_scraper")

__all__ = ["SteamProfileScraper", "ProfileGame"]


@dataclass(frozen=True)
class ProfileGame:
    # game from profile page
    app_id: int
    name: str
    playtime_forever: int = 0


class SteamProfileScraper:
    """Fetches game lists from Steam Community profiles.

    Uses the public profile page which has ALL owned games as
    server-rendered data. No API key needed for public profiles.
    """

    PROFILE_URL_BY_ID = "https://steamcommunity.com/profiles/{steamid}/games?tab=all"

    _HEADERS = {
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36" " (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
    }

    _GAME_RE = re.compile(
        r'"appid"\s*:\s*(\d+)\s*,' r'\s*"name"\s*:\s*"((?:[^"\\]|\\.)*)"' r'.*?"playtime_forever"\s*:\s*(\d+)',
        re.DOTALL,
    )

    def __init__(self, ck=None):
        self._s = requests.Session()
        self._s.headers.update(self._HEADERS)
        if ck:
            self._s.cookies.set("steamLoginSecure", ck, domain="steamcommunity.com")

    def fetch_games(self, sid):
        u = self.PROFILE_URL_BY_ID.format(steamid=sid)
        return self._get(u)

    def _get(self, u):
        try:
            r = self._s.get(u, timeout=HTTP_TIMEOUT_SCRAPE)
            r.raise_for_status()
            h = r.content.decode("utf-8")
            return self._parse(h)
        except requests.RequestException as e:
            logger.warning(t("logs.profile_scraper.request_error", error=str(e)))
            return []

    def _parse(self, h):
        gs = {}
        for m in self._GAME_RE.finditer(h):
            aid = int(m.group(1))
            n = m.group(2).replace('\\"', '"').replace("\\\\", "\\")
            pt = int(m.group(3))
            if aid > 0 and aid not in gs:
                gs[aid] = ProfileGame(app_id=aid, name=n, playtime_forever=pt)
        if not gs:
            gs = self._json(h)
        if gs:
            logger.info(t("logs.profile_scraper.parsed_games", count=len(gs)))
        else:
            logger.warning(t("logs.profile_scraper.no_games_found"))
        return list(gs.values())

    @staticmethod
    def _json(h):
        gs = {}
        for m in re.finditer(r'\[(\{[^]]*"appid"[^]]*})]', h):
            try:
                a = json.loads("[%s]" % m.group(1))
                if isinstance(a, list):
                    for it in a:
                        if isinstance(it, dict) and "appid" in it:
                            aid = int(it["appid"])
                            nm = str(it.get("name", ""))
                            pt = int(it.get("playtime_forever", 0))
                            if aid > 0 and nm and aid not in gs:
                                gs[aid] = ProfileGame(app_id=aid, name=nm, playtime_forever=pt)
            except (json.JSONDecodeError, ValueError, TypeError):
                continue
        return gs
