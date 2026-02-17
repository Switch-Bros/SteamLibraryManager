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

from src.services.enrichment.base_enrichment_thread import BaseEnrichmentThread
from src.utils.i18n import t

logger = logging.getLogger("steamlibmgr.achievement_enrichment")

__all__ = ["AchievementEnrichmentThread"]


class AchievementEnrichmentThread(BaseEnrichmentThread):
    """Background thread for fetching Steam achievement data.

    Iterates over games without achievement data, fetches schema + player
    progress + global rarity from Steam Web API, and writes results to the
    database.
    """

    def __init__(self, parent: Any = None) -> None:
        """Initializes the AchievementEnrichmentThread."""
        super().__init__(parent)
        self._games: list[tuple[int, str]] = []
        self._db_path: Path | None = None
        self._api_key: str = ""
        self._steam_id: str = ""
        self._db: Any = None
        self._api: Any = None

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

    # ── BaseEnrichmentThread hooks ──────────────────────

    def _setup(self) -> None:
        """Opens database and API connections.

        Raises:
            ValueError: If required configuration is missing.
        """
        from src.core.database import Database
        from src.integrations.steam_web_api import SteamWebAPI

        if not self._db_path or not self._api_key or not self._steam_id:
            msg = "Missing configuration (db_path, api_key, or steam_id)"
            raise ValueError(msg)

        self._db = Database(self._db_path)
        self._api = SteamWebAPI(self._api_key)

    def _cleanup(self) -> None:
        """Commits and closes the database connection."""
        if self._db:
            try:
                self._db.commit()
            except Exception:
                pass
            self._db.close()
            self._db = None

    def _get_items(self) -> list:
        """Returns the list of games to enrich."""
        return self._games

    def _process_item(self, item: Any) -> bool:
        """Fetches and stores achievement data for a single game.

        Args:
            item: Tuple of (app_id, name).

        Returns:
            True if data was successfully fetched and stored.
        """
        app_id, _name = item
        return self._enrich_game(self._api, self._db, app_id)

    def _format_progress(self, item: Any, current: int, total: int) -> str:
        """Formats progress text with the game name.

        Args:
            item: Tuple of (app_id, name).
            current: 1-based current index.
            total: Total games count.

        Returns:
            Formatted progress string.
        """
        _app_id, name = item
        return t("ui.enrichment.progress", name=name[:30], current=current, total=total)

    def _rate_limit(self) -> None:
        """Sleeps 1 second between games."""
        time.sleep(1.0)

    # ── Internal ────────────────────────────────────────

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
