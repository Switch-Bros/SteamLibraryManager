#
# steam_library_manager/services/curator_client.py
# HTTP client for Steam curator feeds
#
# Copyright 2025 SwitchBros
# MIT License
#

from __future__ import annotations

import logging
import re
from enum import Enum
from urllib.error import URLError
from urllib.request import Request, urlopen

from steam_library_manager.utils.timeouts import HTTP_TIMEOUT_LONG

logger = logging.getLogger("steamlibmgr.curator_client")

__all__ = ["CuratorClient", "CuratorRecommendation"]


class CuratorRecommendation(Enum):
    RECOMMENDED = "recommended"
    NOT_RECOMMENDED = "not_recommended"
    INFORMATIONAL = "informational"


# regex for curator pages
_ID_RE = re.compile(r"/curator/(\d+)")
_NAME_RE = re.compile(r"/curator/\d+-([^/?]+)")
_APP_RE = re.compile(r'data-ds-appid="(\d+)"')
_BLOCK_RE = re.compile(
    r'class="recommendation[^"]*\s(color_recommended|color_not_recommended|color_informational)'
    r'[^"]*"[^>]*>.*?data-ds-appid="(\d+)"',
    re.DOTALL,
)
_BLOCK_ALT_RE = re.compile(
    r'data-ds-appid="(\d+)".*?(color_recommended|color_not_recommended|color_informational)',
    re.DOTALL,
)

_COLOR_MAP = {
    "color_recommended": CuratorRecommendation.RECOMMENDED,
    "color_not_recommended": CuratorRecommendation.NOT_RECOMMENDED,
    "color_informational": CuratorRecommendation.INFORMATIONAL,
}

_PAGE_SZ = 50
_API_TPL = (
    "https://store.steampowered.com/curator/{cid}"
    "/ajaxgetfilteredrecommendations/render/"
    "?query=&start={start}&count={count}"
)


class CuratorClient:
    """Fetches and parses Steam Curator recommendation feeds.

    Paginates through the store API (50 per page), parses the HTML
    response to extract app IDs and recommendation types.
    """

    @staticmethod
    def parse_id(u):
        m = _ID_RE.search(u)
        if m:
            return int(m.group(1))
        s = u.strip().rstrip("/")
        if s.isdigit():
            return int(s)
        return None

    @staticmethod
    def parse_name(u):
        m = _NAME_RE.search(u)
        if not m:
            return None
        return m.group(1).rstrip("/").replace("-", " ")

    @staticmethod
    def parse_html(h):
        # extract app ids + types
        res = {}
        # appid-first
        for m in _BLOCK_ALT_RE.finditer(h):
            aid, c = int(m.group(1)), m.group(2)
            if aid not in res:
                res[aid] = _COLOR_MAP.get(c, CuratorRecommendation.RECOMMENDED)
        # color-first fallback
        if not res:
            for m in _BLOCK_RE.finditer(h):
                c, aid = m.group(1), int(m.group(2))
                if aid not in res:
                    res[aid] = _COLOR_MAP.get(c, CuratorRecommendation.RECOMMENDED)
        # last resort: just ids
        if not res:
            for m in _APP_RE.finditer(h):
                aid = int(m.group(1))
                if aid not in res:
                    res[aid] = CuratorRecommendation.RECOMMENDED
        return res

    def fetch_recs(self, url, cb=None):
        cid = self.parse_id(url)
        if cid is None:
            raise ValueError("Invalid URL: %s" % url)
        all_r = {}
        off = 0
        pg = 1
        while True:
            if cb:
                cb(pg)
            u = _API_TPL.format(cid=cid, start=off, count=_PAGE_SZ)
            try:
                import json

                req = Request(u)
                req.add_header("Accept", "application/json")
                with urlopen(req, timeout=HTTP_TIMEOUT_LONG) as r:
                    d = json.loads(r.read().decode("utf-8"))
            except (URLError, TimeoutError, OSError) as e:
                raise ConnectionError("Failed: %s" % e) from e
            if not d.get("success"):
                break
            h = d.get("results_html", "")
            if not h or not h.strip():
                break
            p_recs = self.parse_html(h)
            if not p_recs:
                break
            all_r.update(p_recs)
            tot = d.get("total_count", 0)
            off += _PAGE_SZ
            pg += 1
            if off >= tot:
                break
        logger.info("Fetched %d recs for %d", len(all_r), cid)
        return all_r

    @staticmethod
    def fetch_top(n=50):
        import json

        u = "https://store.steampowered.com/curators/ajaxgetcurators/render/?start=0&count=%d" % min(n, 50)
        try:
            req = Request(u)
            req.add_header("Accept", "application/json")
            with urlopen(req, timeout=HTTP_TIMEOUT_LONG) as r:
                d = json.loads(r.read().decode("utf-8"))
        except (URLError, TimeoutError, OSError) as e:
            raise ConnectionError("Failed: %s" % e) from e
        out = []
        h = d.get("results_html", "")
        if not h:
            return out
        # data is in JS var
        js_m = re.search(r"g_rgTopCurators\s*=\s*(\[.*?]);", h, re.DOTALL)
        if js_m:
            try:
                for cur in json.loads(js_m.group(1)):
                    cid = cur.get("clanID")
                    nm = cur.get("name", "").strip()
                    if cid and nm:
                        out.append({"curator_id": int(cid), "name": nm})
            except (json.JSONDecodeError, ValueError):
                logger.warning("Failed to parse g_rgTopCurators JSON")
        logger.info("Fetched %d top curators", len(out))
        return out

    @staticmethod
    def discover_subscribed(ck):
        u = "https://store.steampowered.com/curators/mycurators/"
        try:
            req = Request(u)
            req.add_header("Cookie", ck)
            with urlopen(req, timeout=HTTP_TIMEOUT_LONG) as r:
                h = r.read().decode("utf-8", errors="replace")
        except (URLError, TimeoutError, OSError) as e:
            raise ConnectionError("Failed: %s" % e) from e
        # extract gFollowedCuratorIDs = [123, 456, ...]
        ids_m = re.search(r"gFollowedCuratorIDs\s*=\s*\[([^]]*)]", h)
        if not ids_m:
            logger.warning("Could not find gFollowedCuratorIDs")
            return []
        raw = ids_m.group(1).strip()
        if not raw:
            return []
        out = []
        for ch in raw.split(","):
            ch = ch.strip()
            if ch.isdigit():
                out.append({"curator_id": int(ch), "name": ""})
        # get names
        nm_re = re.compile(r'data-clanid="(\d+)"[^>]*>.*?curator_name[^>]*>([^<]+)<', re.DOTALL)
        nm_map = {int(m.group(1)): m.group(2).strip() for m in nm_re.finditer(h)}
        for e in out:
            cid = e["curator_id"]
            if isinstance(cid, int) and cid in nm_map:
                e["name"] = nm_map[cid]
        logger.info("Discovered %d subscribed curators", len(out))
        return out
