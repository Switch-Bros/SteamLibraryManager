#
# steam_library_manager/integrations/protondb_api.py
# ProtonDB API client
#
# Copyright 2025 SwitchBros
# MIT License
#

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import requests

from steam_library_manager.utils.timeouts import HTTP_TIMEOUT

logger = logging.getLogger("steamlibmgr.protondb_api")

__all__ = ["ProtonDBClient", "ProtonDBResult", "fetch_and_persist_protondb"]


@dataclass(frozen=True)
class ProtonDBResult:
    # rating from protondb
    tier: str
    confidence: str = ""
    trending_tier: str = ""
    score: float = 0.0
    best_reported: str = ""


class ProtonDBClient:
    """Fetches Linux compat ratings from protondb.com.

    No auth needed but be nice with rate limiting.
    """

    BASE_URL = "https://www.protondb.com/api/v1/reports/summaries/"

    def __init__(self):
        self._s = requests.Session()
        self._s.headers.update({"User-Agent": "SteamLibraryManager/1.0"})

    def get_rating(self, aid):
        try:
            u = "%s%d.json" % (self.BASE_URL, aid)
            r = self._s.get(u, timeout=HTTP_TIMEOUT)

            if r.status_code == 404:
                logger.debug("ProtonDB: no data for app %d", aid)
                return None

            if r.status_code != 200:
                logger.warning("ProtonDB: status %d for app %d", r.status_code, aid)
                return None

            d = r.json()
            return ProtonDBResult(
                tier=d.get("tier", "unknown"),
                confidence=d.get("confidence", ""),
                trending_tier=d.get("trendingTier", ""),
                score=float(d.get("score", 0.0)),
                best_reported=d.get("bestReportedTier", ""),
            )

        except requests.RequestException as e:
            logger.warning("ProtonDB: net error for app %d: %s", aid, e)
            return None
        except (ValueError, KeyError) as e:
            logger.warning("ProtonDB: parse error for app %d: %s", aid, e)
            return None

    def get_ratings_batch(self, aids, delay=0.5):
        # rate limited batch fetch
        res = {}
        for i, x in enumerate(aids):
            rt = self.get_rating(x)
            if rt:
                res[x] = rt
            if i < len(aids) - 1:
                time.sleep(delay)
        return res


def fetch_and_persist_protondb(aid, d, c):
    # fetch and save
    rt = c.get_rating(aid)
    if rt:
        d.upsert_protondb(
            aid,
            tier=rt.tier,
            confidence=rt.confidence,
            trending_tier=rt.trending_tier,
            score=rt.score,
            best_reported=rt.best_reported,
        )
        d.commit()
        return rt.tier
    return None
