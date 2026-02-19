"""Background thread for performing library health checks.

Runs a 2-stage store availability check (batch API + detail HTTP),
then queries the database for missing metadata, artwork, and stale caches.
Emits progress signals for the UI and a final HealthReport.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

import requests
from PyQt6.QtCore import QThread, pyqtSignal

from src.services.library_health_service import HealthReport, StoreCheckResult

logger = logging.getLogger("steamlibmgr.library_health")

__all__ = ["LibraryHealthThread"]

# Keywords indicating geo-blocking / region restriction on the store page.
# Shared with StoreCheckThread in tools_actions.py.
_GEO_KEYWORDS = (
    "not available in your country",
    "not available in your region",
    "unavailable in your region",
    "nicht in ihrem land",
    "dieses produkt steht in ihrem land",
    "currently unavailable",
    "error processing your request",
)

_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36" " (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
_HTTP_TIMEOUT = 10
_BATCH_SIZE = 50
_BATCH_DELAY = 1.0
_DETAIL_DELAY = 1.5


class LibraryHealthThread(QThread):
    """Background thread that performs the full library health check.

    Signals:
        progress: Emitted with (current_step, total_steps, i18n_key).
        phase_changed: Emitted with (phase_name_key,) when switching phases.
        finished_report: Emitted with the completed HealthReport.
        error: Emitted with an error message string.
    """

    progress = pyqtSignal(int, int, str)
    phase_changed = pyqtSignal(str)
    finished_report = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(
        self,
        games: list[tuple[int, str]],
        api_key: str,
        db_path: Path,
        parent: Any = None,
    ) -> None:
        """Initializes the LibraryHealthThread.

        Args:
            games: List of (app_id, name) tuples to check.
            api_key: Steam Web API key (may be empty for DB-only checks).
            db_path: Path to the SQLite database file.
            parent: Optional QObject parent.
        """
        super().__init__(parent)
        self._games = games
        self._api_key = api_key
        self._db_path = db_path
        self._cancelled = False

    def cancel(self) -> None:
        """Requests cancellation of the health check."""
        self._cancelled = True

    def run(self) -> None:
        """Executes the full health check pipeline.

        Pipeline:
            1. Batch store check via GetItems (50er batches, 1s pause).
            2. Detail HTTP check for missing app IDs (1.5s pause).
            3. Missing metadata check (DB query).
            4. Missing artwork check (DB query).
            5. Stale cache check (DB query).
        """
        from src.core.database import Database

        report = HealthReport(total_games=len(self._games))
        all_app_ids = [app_id for app_id, _ in self._games]
        name_map = {app_id: name for app_id, name in self._games}

        # Stage 1: Batch store check via GetItems API
        missing_ids: list[int] = []
        if self._api_key:
            self.phase_changed.emit("health_check.progress.store_batch")
            missing_ids = self._check_store_batch(all_app_ids)

            if self._cancelled:
                return

            # Stage 2: Detail HTTP check for missing IDs
            if missing_ids:
                self.phase_changed.emit("health_check.progress.store_detail")
                results = self._check_store_detail(missing_ids, name_map)
                report.store_unavailable = [r for r in results if r.status != "available"]

                if self._cancelled:
                    return

        # Stage 3-5: DB-based checks
        db = Database(self._db_path)
        try:
            self.phase_changed.emit("health_check.progress.metadata")
            report.missing_metadata = db.get_apps_missing_metadata()

            self.phase_changed.emit("health_check.progress.artwork")
            report.missing_artwork = db.get_games_missing_artwork()

            self.phase_changed.emit("health_check.progress.cache")
            report.stale_hltb = db.get_stale_hltb_count(max_age_days=30)
            report.stale_protondb = db.get_stale_protondb_count(max_age_days=7)
        finally:
            db.close()

        self.finished_report.emit(report)

    def _check_store_batch(self, all_app_ids: list[int]) -> list[int]:
        """Checks store availability via GetItems API in 50er batches.

        Args:
            all_app_ids: All app IDs to check.

        Returns:
            List of app IDs that returned NO data (potentially delisted).
        """
        from src.integrations.steam_web_api import SteamWebAPI

        try:
            api = SteamWebAPI(self._api_key)
        except ValueError:
            logger.warning("Invalid API key for store batch check")
            return []

        found_app_ids: set[int] = set()
        batches = [all_app_ids[i : i + _BATCH_SIZE] for i in range(0, len(all_app_ids), _BATCH_SIZE)]

        for batch_idx, batch in enumerate(batches):
            if self._cancelled:
                return []

            self.progress.emit(
                batch_idx + 1,
                len(batches),
                "health_check.progress.store_batch",
            )

            try:
                results = api._fetch_batch(batch)
                for item in results:
                    found_app_ids.add(item.get("appid", 0))
            except Exception as exc:
                logger.warning("Store batch %d failed: %s", batch_idx + 1, exc)

            if batch_idx < len(batches) - 1:
                time.sleep(_BATCH_DELAY)

        return [app_id for app_id in all_app_ids if app_id not in found_app_ids]

    def _check_store_detail(
        self,
        missing_app_ids: list[int],
        name_map: dict[int, str],
    ) -> list[StoreCheckResult]:
        """Performs detailed HTTP checks on potentially delisted games.

        Uses the same logic as StoreCheckThread but in batch.
        Rate limited to 1 request per 1.5 seconds.

        Args:
            missing_app_ids: App IDs that returned no data from GetItems.
            name_map: Mapping of app_id to game name.

        Returns:
            List of StoreCheckResult with exact status per game.
        """
        results: list[StoreCheckResult] = []

        for idx, app_id in enumerate(missing_app_ids):
            if self._cancelled:
                return results

            self.progress.emit(
                idx + 1,
                len(missing_app_ids),
                "health_check.progress.store_detail",
            )

            name = name_map.get(app_id, f"App {app_id}")

            try:
                url = f"https://store.steampowered.com/app/{app_id}/"
                response = requests.get(
                    url,
                    timeout=_HTTP_TIMEOUT,
                    allow_redirects=True,
                    headers={"User-Agent": _USER_AGENT},
                )

                status = "unknown"
                if response.status_code in (404, 403):
                    status = "removed"
                elif response.status_code == 200:
                    final_url = response.url
                    text_lower = response.text.lower()

                    if "agecheck" in final_url:
                        status = "age_gate"
                    elif any(kw in text_lower for kw in _GEO_KEYWORDS):
                        status = "geo_locked"
                    elif "game_area_purchase" in text_lower or "app_header" in text_lower:
                        status = "available"
                    elif f"/app/{app_id}" not in final_url:
                        status = "delisted"

                results.append(
                    StoreCheckResult(
                        app_id=app_id,
                        name=name,
                        status=status,
                        details=f"HTTP {response.status_code}",
                    )
                )

            except Exception as ex:
                results.append(
                    StoreCheckResult(
                        app_id=app_id,
                        name=name,
                        status="unknown",
                        details=str(ex),
                    )
                )

            if idx < len(missing_app_ids) - 1:
                time.sleep(_DETAIL_DELAY)

        return results
