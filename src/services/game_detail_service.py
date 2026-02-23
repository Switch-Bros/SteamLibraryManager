# src/services/game_detail_service.py

"""Service for fetching detailed game data from external APIs.

Orchestrator that delegates data application and persistence to free
functions in game_detail_enrichers. Manages cache checking, API calls,
and "already checked" tracking for HLTB and achievements.

On-demand enrichment: When a user clicks a game, this service fetches
HLTB and achievement data automatically (if missing) alongside the
existing store/review/ProtonDB/Deck fetches. Results are cached locally
and persisted to the SQLite database.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import requests

from src.core.game import Game
from src.services.game_detail_enrichers import (
    apply_achievement_data,
    apply_hltb_data,
    apply_review_data,
    apply_store_data,
    fetch_last_update,
    fetch_proton_rating,
    fetch_steam_deck_status,
    persist_achievement_stats,
    persist_achievements,
    persist_hltb,
)

if TYPE_CHECKING:
    from src.integrations.hltb_api import HLTBClient

logger = logging.getLogger("steamlibmgr.game_detail_service")

__all__ = ["GameDetailService"]


class GameDetailService:
    """Fetches and caches detailed game data from external APIs.

    Operates on a shared games dict (by reference) so that mutations
    are immediately visible to GameManager and the rest of the app.

    Tracks which app_ids have already been checked for HLTB and
    achievement data to avoid redundant API calls on repeated clicks.

    Args:
        games: Shared reference to the GameManager's games dict.
        cache_dir: Directory for JSON cache files.
    """

    def __init__(self, games: dict[str, Game], cache_dir: Path) -> None:
        self._games = games
        self._cache_dir = cache_dir
        self._hltb_checked: set[str] = set()
        self._achievements_checked: set[str] = set()
        self._hltb_client: HLTBClient | None = None
        self._hltb_lock = threading.Lock()

    def needs_enrichment(self, app_id: str) -> bool:
        """Checks whether a game needs any on-demand data fetching.

        Returns True if the game is missing basic metadata, HLTB data,
        or achievement data that hasn't been checked yet.

        Args:
            app_id: The Steam app ID.

        Returns:
            True if background fetching should be triggered.
        """
        if app_id not in self._games:
            return False
        game = self._games[app_id]

        if not game.developer or not game.proton_db_rating or not game.steam_deck_status:
            return True
        if app_id not in self._hltb_checked and not any(
            (game.hltb_main_story, game.hltb_main_extras, game.hltb_completionist)
        ):
            return True
        if app_id not in self._achievements_checked and game.achievement_total == 0 and game.app_type in ("game", ""):
            return True
        return False

    def fetch_game_details(self, app_id: str) -> bool:
        """Fetches additional details for a game from external APIs.

        Fetches store data, review stats, ProtonDB ratings, Steam Deck status,
        last update info, HLTB completion times, and achievement data.
        Results are cached locally and persisted to the database.

        Args:
            app_id: The Steam app ID.

        Returns:
            True if the game exists, False otherwise.
        """
        if app_id not in self._games:
            return False
        game = self._games[app_id]
        self._fetch_store_data(app_id)
        self._fetch_review_stats(app_id)
        fetch_proton_rating(game)
        fetch_steam_deck_status(game, self._cache_dir)
        fetch_last_update(game, self._cache_dir)
        self._fetch_hltb_data(app_id)
        self._fetch_achievement_data(app_id)
        return True

    # ------------------------------------------------------------------
    # Store & Review (cache + API call, delegate apply to enrichers)
    # ------------------------------------------------------------------

    def _fetch_store_data(self, app_id: str) -> None:
        """Fetches and caches data from the Steam Store API.

        Args:
            app_id: The Steam app ID.
        """
        cache_file = self._cache_dir / "store_data" / f"{app_id}.json"
        if cache_file.exists():
            try:
                cache_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
                if cache_age < timedelta(days=7):
                    with open(cache_file, "r") as f:
                        data = json.load(f)
                        apply_store_data(self._games[app_id], data)
                    return
            except (OSError, json.JSONDecodeError):
                pass

        try:
            url = "https://store.steampowered.com/api/appdetails"
            params = {"appids": app_id}
            response = requests.get(url, params=params, timeout=5)
            data = response.json()
            if app_id in data and data[app_id]["success"]:
                game_data = data[app_id]["data"]
                cache_file.parent.mkdir(exist_ok=True)
                with open(cache_file, "w") as f:
                    json.dump(game_data, f)
                apply_store_data(self._games[app_id], game_data)
        except (requests.RequestException, ValueError, KeyError, OSError):
            pass

    def _fetch_review_stats(self, app_id: str) -> None:
        """Fetches and caches Steam review statistics.

        Args:
            app_id: The Steam app ID.
        """
        cache_file = self._cache_dir / "store_data" / f"{app_id}_reviews.json"
        if cache_file.exists():
            try:
                cache_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
                if cache_age < timedelta(hours=24):
                    with open(cache_file, "r") as f:
                        data = json.load(f)
                        apply_review_data(self._games[app_id], data)
                    return
            except (OSError, json.JSONDecodeError):
                pass

        try:
            url = f"https://store.steampowered.com/appreviews/{app_id}?json=1&language=german"
            response = requests.get(url, timeout=5)
            data = response.json()
            if "query_summary" in data:
                with open(cache_file, "w") as f:
                    json.dump(data, f)
                apply_review_data(self._games[app_id], data)
        except (requests.RequestException, ValueError, KeyError, OSError):
            pass

    # ------------------------------------------------------------------
    # HLTB on-demand enrichment
    # ------------------------------------------------------------------

    def _fetch_hltb_data(self, app_id: str) -> None:
        """Fetches HowLongToBeat completion times for a single game.

        Checks a local JSON cache first (7-day TTL). On cache miss,
        queries the HLTB API, updates the in-memory Game object, and
        persists the result to the database.

        Args:
            app_id: The Steam app ID.
        """
        if app_id in self._hltb_checked:
            return
        if app_id not in self._games:
            return

        game = self._games[app_id]

        if any((game.hltb_main_story, game.hltb_main_extras, game.hltb_completionist)):
            self._hltb_checked.add(app_id)
            return

        cache_file = self._cache_dir / "store_data" / f"{app_id}_hltb.json"
        if cache_file.exists():
            try:
                cache_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
                if cache_age < timedelta(days=7):
                    with open(cache_file, "r") as f:
                        data = json.load(f)
                    apply_hltb_data(game, data)
                    self._hltb_checked.add(app_id)
                    return
            except (OSError, json.JSONDecodeError):
                pass

        with self._hltb_lock:
            try:
                from src.integrations.hltb_api import HLTBClient

                if self._hltb_client is None:
                    self._hltb_client = HLTBClient()

                result = self._hltb_client.search_game(game.name, int(app_id))
                cache_file.parent.mkdir(exist_ok=True)

                if result:
                    data = {
                        "main_story": result.main_story,
                        "main_extras": result.main_extras,
                        "completionist": result.completionist,
                    }
                    with open(cache_file, "w") as f:
                        json.dump(data, f)
                    apply_hltb_data(game, data)
                    persist_hltb(int(app_id), result.main_story, result.main_extras, result.completionist)
                else:
                    with open(cache_file, "w") as f:
                        json.dump({"no_data": True}, f)
            except Exception as exc:
                logger.debug("HLTB on-demand fetch failed for %s: %s", app_id, exc)

        self._hltb_checked.add(app_id)

    # ------------------------------------------------------------------
    # Achievement on-demand enrichment
    # ------------------------------------------------------------------

    def _fetch_achievement_data(self, app_id: str) -> None:
        """Fetches achievement data for a single game from the Steam API.

        Checks a local JSON cache first (7-day TTL). On cache miss,
        queries the Steam Web API (schema + player + global percentages),
        updates the in-memory Game object, and persists to the database.

        Args:
            app_id: The Steam app ID.
        """
        if app_id in self._achievements_checked:
            return
        if app_id not in self._games:
            return

        game = self._games[app_id]

        if game.app_type and game.app_type not in ("game", ""):
            self._achievements_checked.add(app_id)
            return
        if game.achievement_total > 0:
            self._achievements_checked.add(app_id)
            return

        cache_file = self._cache_dir / "store_data" / f"{app_id}_achievements.json"
        if cache_file.exists():
            try:
                cache_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
                if cache_age < timedelta(days=7):
                    with open(cache_file, "r") as f:
                        data = json.load(f)
                    apply_achievement_data(game, data)
                    self._achievements_checked.add(app_id)
                    return
            except (OSError, json.JSONDecodeError):
                pass

        try:
            from src.config import config

            api_key = config.STEAM_API_KEY
            steam_id = config.STEAM_USER_ID
        except Exception:
            self._achievements_checked.add(app_id)
            return

        if not api_key or not steam_id:
            self._achievements_checked.add(app_id)
            return

        try:
            from src.integrations.steam_web_api import SteamWebAPI

            api = SteamWebAPI(api_key)
            int_app_id = int(app_id)

            schema = api.get_game_schema(int_app_id)
            schema_achievements = (schema or {}).get("achievements", [])
            cache_file.parent.mkdir(exist_ok=True)

            if not schema_achievements:
                data = {"total": 0, "unlocked": 0, "percentage": 0.0, "perfect": False}
                with open(cache_file, "w") as f:
                    json.dump(data, f)
                persist_achievement_stats(int_app_id, 0, 0, 0.0, False)
                self._achievements_checked.add(app_id)
                return

            total = len(schema_achievements)

            player_achievements = api.get_player_achievements(int_app_id, steam_id)
            player_map: dict[str, dict] = {}
            if player_achievements:
                for ach in player_achievements:
                    player_map[ach.get("apiname", "")] = ach

            global_pcts = SteamWebAPI.get_global_achievement_percentages(int_app_id)

            unlocked_count = 0
            achievement_records: list[dict] = []
            for schema_ach in schema_achievements:
                api_name = schema_ach.get("name", "")
                player_ach = player_map.get(api_name, {})
                is_unlocked = bool(player_ach.get("achieved", 0))
                if is_unlocked:
                    unlocked_count += 1
                achievement_records.append(
                    {
                        "achievement_id": api_name,
                        "name": schema_ach.get("displayName", api_name),
                        "description": schema_ach.get("description", ""),
                        "is_unlocked": is_unlocked,
                        "unlock_time": player_ach.get("unlocktime", 0) or 0,
                        "is_hidden": bool(schema_ach.get("hidden", 0)),
                        "rarity_percentage": global_pcts.get(api_name, 0.0),
                    }
                )

            completion_pct = (unlocked_count / total * 100) if total > 0 else 0.0
            perfect = unlocked_count == total and total > 0

            data = {
                "total": total,
                "unlocked": unlocked_count,
                "percentage": round(completion_pct, 1),
                "perfect": perfect,
            }
            with open(cache_file, "w") as f:
                json.dump(data, f)

            apply_achievement_data(game, data)
            persist_achievement_stats(int_app_id, total, unlocked_count, completion_pct, perfect)
            persist_achievements(int_app_id, achievement_records)

        except Exception as exc:
            logger.debug("Achievement on-demand fetch failed for %s: %s", app_id, exc)

        self._achievements_checked.add(app_id)
