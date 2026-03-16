#
# steam_library_manager/services/game_detail_service.py
# On-demand fetching and caching of external game data (store, HLTB, achievements)
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import requests

from steam_library_manager.core.game import Game
from steam_library_manager.utils.timeouts import HTTP_TIMEOUT_SHORT
from steam_library_manager.services.game_detail_enrichers import (
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
    from steam_library_manager.integrations.hltb_api import HLTBClient

logger = logging.getLogger("steamlibmgr.game_detail_service")

__all__ = ["GameDetailService"]


class GameDetailService:
    """Fetches and caches detailed game data from external APIs.

    Operates on a shared games dict so mutations are visible app-wide.
    Tracks already-checked app_ids to skip redundant API calls.
    """

    def __init__(self, games: dict[str, Game], cache_dir: Path) -> None:
        self._games = games
        self._cache_dir = cache_dir
        self._hltb_checked: set[str] = set()
        self._achievements_checked: set[str] = set()
        self._hltb_client: HLTBClient | None = None
        self._hltb_lock = threading.Lock()

    def needs_enrichment(self, app_id: str) -> bool:
        """True if the game is missing metadata, HLTB, or achievements."""
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
        """Fetch all external data for a game. Returns False if unknown."""
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

    # Store & Review

    def _fetch_store_data(self, app_id: str) -> None:
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
            response = requests.get(url, params=params, timeout=HTTP_TIMEOUT_SHORT)
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
            response = requests.get(url, timeout=HTTP_TIMEOUT_SHORT)
            data = response.json()
            if "query_summary" in data:
                with open(cache_file, "w") as f:
                    json.dump(data, f)
                apply_review_data(self._games[app_id], data)
        except (requests.RequestException, ValueError, KeyError, OSError):
            pass

    # HLTB

    def _fetch_hltb_data(self, app_id: str) -> None:
        """Fetch HLTB times (cached 7 days, then API fallback)."""
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
                from steam_library_manager.integrations.hltb_api import HLTBClient

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

    # Achievements

    def _fetch_achievement_data(self, app_id: str) -> None:
        """Fetch achievement stats (cached 7 days, then Steam Web API)."""
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
            from steam_library_manager.config import config

            api_key = config.STEAM_API_KEY
            steam_id = config.STEAM_USER_ID
        except Exception:
            self._achievements_checked.add(app_id)
            return

        if not api_key or not steam_id:
            self._achievements_checked.add(app_id)
            return

        try:
            from steam_library_manager.integrations.steam_web_api import SteamWebAPI

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
