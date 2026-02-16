"""Background thread for Steam Achievement enrichment.

Fetches achievement data (schema, player progress, global rarity) from
the Steam Web API for games without achievement data. Rate-limited to
~1 request per second (3 API calls per game = ~3 seconds per game).
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QThread, pyqtSignal

from src.utils.i18n import t

logger = logging.getLogger("steamlibmgr.achievement_enrichment")

__all__ = ["AchievementEnrichmentThread"]


class AchievementEnrichmentThread(QThread):
    """Background thread for fetching Steam achievement data.

    Iterates over games without achievement data, fetches schema + player
    progress + global rarity from Steam Web API, and writes results to the
    database.

    Signals:
        progress: Emitted per game (status_text, current_index, total_count).
        finished_enrichment: Emitted on completion (success_count, failed_count).
        error: Emitted on fatal errors (error_message).
    """

    progress = pyqtSignal(str, int, int)
    finished_enrichment = pyqtSignal(int, int)
    error = pyqtSignal(str)

    def __init__(self, parent: Any = None) -> None:
        """Initializes the AchievementEnrichmentThread."""
        super().__init__(parent)
        self._cancelled: bool = False
        self._games: list[tuple[int, str]] = []
        self._db_path: Path | None = None
        self._api_key: str = ""
        self._steam_id: str = ""

    def configure(
        self,
        games: list[tuple[int, str]],
        db_path: Path,
        api_key: str,
        steam_id: str,
    ) -> None:
        """Configures the thread with games and API credentials.

        Args:
            games: List of (app_id, name) tuples for games to enrich.
            db_path: Path to the SQLite database file.
            api_key: Steam Web API key.
            steam_id: 64-bit Steam user ID.
        """
        self._games = games
        self._db_path = db_path
        self._api_key = api_key
        self._steam_id = steam_id

    def cancel(self) -> None:
        """Requests cancellation of the enrichment."""
        self._cancelled = True

    def run(self) -> None:
        """Executes the achievement enrichment in the background thread."""
        from src.core.database import Database
        from src.integrations.steam_web_api import SteamWebAPI

        self._cancelled = False
        total = len(self._games)
        success = 0
        failed = 0

        if not self._db_path or not self._api_key or not self._steam_id:
            self.error.emit("Missing configuration (db_path, api_key, or steam_id)")
            return

        try:
            db = Database(self._db_path)
            api = SteamWebAPI(self._api_key)
        except Exception as exc:
            self.error.emit(str(exc))
            return

        try:
            for idx, (app_id, name) in enumerate(self._games):
                if self._cancelled:
                    break

                self.progress.emit(
                    t("ui.enrichment.progress", name=name[:30], current=idx + 1, total=total),
                    idx + 1,
                    total,
                )

                try:
                    enriched = self._enrich_game(api, db, app_id)
                    if enriched:
                        success += 1
                    else:
                        failed += 1
                except Exception as exc:
                    logger.warning("Achievement enrichment failed for %d: %s", app_id, exc)
                    failed += 1

                # Rate limiting: ~1 second between games
                if idx < total - 1:
                    time.sleep(1.0)

            db.commit()
        except Exception as exc:
            self.error.emit(str(exc))
            return
        finally:
            db.close()

        self.finished_enrichment.emit(success, failed)

    def _enrich_game(
        self,
        api: Any,
        db: Any,
        app_id: int,
    ) -> bool:
        """Fetches and stores achievement data for a single game.

        Args:
            api: SteamWebAPI instance.
            db: Database instance.
            app_id: Steam app ID to enrich.

        Returns:
            True if data was successfully fetched and stored.
        """
        # 1. Get achievement schema (list of possible achievements)
        schema = api.get_game_schema(app_id)
        schema_achievements = (schema or {}).get("achievements", [])

        if not schema_achievements:
            # Game has no achievements — record total=0 to avoid re-fetching
            db.upsert_achievement_stats(app_id, 0, 0, 0.0, False)
            return True

        total = len(schema_achievements)

        # 2. Get player's achievement progress
        player_achievements = api.get_player_achievements(app_id, self._steam_id)
        player_map: dict[str, dict] = {}
        if player_achievements:
            for ach in player_achievements:
                player_map[ach.get("apiname", "")] = ach

        # 3. Get global rarity percentages (no auth needed)
        global_pcts = api.get_global_achievement_percentages(app_id)

        # 4. Merge and build achievement records
        achievement_records: list[dict] = []
        unlocked_count = 0

        for schema_ach in schema_achievements:
            api_name = schema_ach.get("name", "")
            display_name = schema_ach.get("displayName", api_name)
            description = schema_ach.get("description", "")
            is_hidden = bool(schema_ach.get("hidden", 0))

            # Player progress
            player_ach = player_map.get(api_name, {})
            is_unlocked = bool(player_ach.get("achieved", 0))
            unlock_time = player_ach.get("unlocktime", 0) or 0

            if is_unlocked:
                unlocked_count += 1

            # Global rarity
            rarity = global_pcts.get(api_name, 0.0)

            achievement_records.append(
                {
                    "achievement_id": api_name,
                    "name": display_name,
                    "description": description,
                    "is_unlocked": is_unlocked,
                    "unlock_time": unlock_time,
                    "is_hidden": is_hidden,
                    "rarity_percentage": rarity,
                }
            )

        # 5. Calculate stats
        completion_pct = (unlocked_count / total * 100) if total > 0 else 0.0
        perfect = unlocked_count == total and total > 0

        # 6. Write to DB
        db.upsert_achievements(app_id, achievement_records)
        db.upsert_achievement_stats(app_id, total, unlocked_count, completion_pct, perfect)

        return True
