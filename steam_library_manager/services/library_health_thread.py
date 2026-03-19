#
# steam_library_manager/services/library_health_thread.py
# Background thread for library health checks
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
import time

import requests
from PyQt6.QtCore import QThread, pyqtSignal

from steam_library_manager.services.library_health_service import HealthReport, StoreCheckResult
from steam_library_manager.utils.timeouts import HTTP_TIMEOUT

logger = logging.getLogger("steamlibmgr.library_health")

__all__ = ["LibraryHealthThread"]

# geo-blocking keywords on store pages
_GEO_KW = (
    "not available in your country",
    "not available in your region",
    "unavailable in your region",
    "nicht in ihrem land",
    "dieses produkt steht in ihrem land",
    "currently unavailable",
    "error processing your request",
)

_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36" " (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
_BATCH = 50
_BATCH_WAIT = 1.0
_DETAIL_WAIT = 1.5


class LibraryHealthThread(QThread):
    """Runs full library health check in background.

    Pipeline: batch store check -> detail HTTP check
    -> missing metadata -> missing artwork -> stale cache.
    """

    progress = pyqtSignal(int, int, str)
    phase_changed = pyqtSignal(str)
    finished_report = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, games, api_key, db_path, parent=None):
        super().__init__(parent)
        self._games = games
        self._api_key = api_key
        self._db_path = db_path
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        from steam_library_manager.core.database import Database

        report = HealthReport(total_games=len(self._games))
        all_ids = [aid for aid, _ in self._games]
        names = {aid: nm for aid, nm in self._games}

        # 1. batch store check
        missing = []
        if self._api_key:
            self.phase_changed.emit("health_check.progress.store_batch")
            missing = self._check_store_batch(all_ids)

            if self._cancelled:
                return

            # 2. detail HTTP check
            if missing:
                self.phase_changed.emit("health_check.progress.store_detail")
                results = self._check_store_detail(missing, names)
                report.store_unavailable = [r for r in results if r.status != "available"]

                if self._cancelled:
                    return

        # 3-5. DB checks
        db = Database(self._db_path)
        try:
            self.phase_changed.emit("health_check.progress.metadata")
            report.missing_metadata = db.get_apps_missing_metadata()

            self.phase_changed.emit("health_check.progress.artwork")
            report.missing_artwork = db.get_games_missing_artwork()

            self.phase_changed.emit("health_check.progress.cache")
            report.stale_hltb = db.get_stale_hltb_count(ma_days=30)
            report.stale_protondb = db.get_stale_protondb_count(ma_days=7)
        finally:
            db.close()

        self.finished_report.emit(report)

    def _check_store_batch(self, all_ids):
        # store availability via GetItems in 50er batches
        from steam_library_manager.integrations.steam_web_api import SteamWebAPI

        try:
            api = SteamWebAPI(self._api_key)
        except ValueError:
            logger.warning("invalid API key for batch check")
            return []

        found = set()
        batches = [all_ids[i : i + _BATCH] for i in range(0, len(all_ids), _BATCH)]

        for bi, batch in enumerate(batches):
            if self._cancelled:
                return []

            self.progress.emit(bi + 1, len(batches), "health_check.progress.store_batch")

            try:
                for item in api._fetch_batch(batch):
                    found.add(item.get("appid", 0))
            except Exception as exc:
                logger.warning("batch %d failed: %s" % (bi + 1, exc))

            if bi < len(batches) - 1:
                time.sleep(_BATCH_WAIT)

        return [aid for aid in all_ids if aid not in found]

    def _check_store_detail(self, missing_ids, names):
        # HTTP check on potentially delisted games
        results = []

        for idx, aid in enumerate(missing_ids):
            if self._cancelled:
                return results

            self.progress.emit(idx + 1, len(missing_ids), "health_check.progress.store_detail")

            nm = names.get(aid, "App %d" % aid)

            try:
                url = "https://store.steampowered.com/app/%d/" % aid
                resp = requests.get(
                    url,
                    timeout=HTTP_TIMEOUT,
                    allow_redirects=True,
                    headers={"User-Agent": _UA},
                )

                status = "unknown"
                if resp.status_code in (404, 403):
                    status = "removed"
                elif resp.status_code == 200:
                    final = resp.url
                    txt = resp.text.lower()

                    if "agecheck" in final:
                        status = "age_gate"
                    elif any(kw in txt for kw in _GEO_KW):
                        status = "geo_locked"
                    elif "game_area_purchase" in txt or "app_header" in txt:
                        status = "available"
                    elif "/app/%d" % aid not in final:
                        status = "delisted"

                results.append(
                    StoreCheckResult(app_id=aid, name=nm, status=status, details="HTTP %d" % resp.status_code)
                )

            except Exception as ex:
                results.append(StoreCheckResult(app_id=aid, name=nm, status="unknown", details=str(ex)))

            if idx < len(missing_ids) - 1:
                time.sleep(_DETAIL_WAIT)

        return results
