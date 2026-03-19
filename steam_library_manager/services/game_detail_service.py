#
# steam_library_manager/services/game_detail_service.py
# Fetches and assembles full game detail data for the details panel
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

import json
import logging
import threading
from datetime import datetime, timedelta

import requests

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

logger = logging.getLogger("steamlibmgr.game_detail_service")

__all__ = ["GameDetailService"]


class GameDetailService:
    """Fetches and caches detailed game data from external APIs.
    Tracks which app_ids have been checked to avoid redundant calls.
    """

    def __init__(self, games, cache_dir):
        self._games = games
        self._cache_dir = cache_dir
        self._hltb_checked = set()
        self._achievements_checked = set()
        self._hltb_client = None
        self._hltb_lock = threading.Lock()

    def needs_enrichment(self, app_id):
        # Check whether a game needs on-demand data fetching
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

    def fetch_game_details(self, app_id):
        # Fetch store data, reviews, ProtonDB, Deck status, HLTB, achievements
        if app_id not in self._games:
            return False
        game = self._games[app_id]
        self._get_store(app_id)
        self._get_reviews(app_id)
        fetch_proton_rating(game)
        fetch_steam_deck_status(game, self._cache_dir)
        fetch_last_update(game, self._cache_dir)
        self._fetch_hltb_data(app_id)
        self._fetch_achievement_data(app_id)
        return True

    # ------------------------------------------------------------------
    # Store & Review
    # ------------------------------------------------------------------

    def _get_store(self, app_id):
        # Fetch and cache Steam Store API data
        cache_file = self._cache_dir / "store_data" / ("%s.json" % app_id)
        if cache_file.exists():
            try:
                age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
                if age < timedelta(days=7):
                    with open(cache_file, "r") as f:
                        data = json.load(f)
                        apply_store_data(self._games[app_id], data)
                    return
            except (OSError, json.JSONDecodeError):
                pass

        try:
            url = "https://store.steampowered.com/api/appdetails"
            params = {"appids": app_id}
            resp = requests.get(url, params=params, timeout=HTTP_TIMEOUT_SHORT)
            data = resp.json()
            if app_id in data and data[app_id]["success"]:
                gd = data[app_id]["data"]
                cache_file.parent.mkdir(exist_ok=True)
                with open(cache_file, "w") as f:
                    json.dump(gd, f)
                apply_store_data(self._games[app_id], gd)
        except (requests.RequestException, ValueError, KeyError, OSError):
            pass

    def _get_reviews(self, app_id):
        # Fetch and cache Steam review statistics
        cache_file = self._cache_dir / "store_data" / ("%s_reviews.json" % app_id)
        if cache_file.exists():
            try:
                age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
                if age < timedelta(hours=24):
                    with open(cache_file, "r") as f:
                        data = json.load(f)
                        apply_review_data(self._games[app_id], data)
                    return
            except (OSError, json.JSONDecodeError):
                pass

        try:
            url = "https://store.steampowered.com/appreviews/%s?json=1&language=german" % app_id
            resp = requests.get(url, timeout=HTTP_TIMEOUT_SHORT)
            data = resp.json()
            if "query_summary" in data:
                with open(cache_file, "w") as f:
                    json.dump(data, f)
                apply_review_data(self._games[app_id], data)
        except (requests.RequestException, ValueError, KeyError, OSError):
            pass

    # ------------------------------------------------------------------
    # HLTB on-demand enrichment
    # ------------------------------------------------------------------

    def _fetch_hltb_data(self, app_id):
        # Fetch HowLongToBeat times (JSON cache, 7-day TTL)
        if app_id in self._hltb_checked:
            return
        if app_id not in self._games:
            return

        game = self._games[app_id]

        if any((game.hltb_main_story, game.hltb_main_extras, game.hltb_completionist)):
            self._hltb_checked.add(app_id)
            return

        cache_file = self._cache_dir / "store_data" / ("%s_hltb.json" % app_id)
        if cache_file.exists():
            try:
                age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
                if age < timedelta(days=7):
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

    # ------------------------------------------------------------------
    # Achievement on-demand enrichment
    # ------------------------------------------------------------------

    def _fetch_achievement_data(self, app_id):
        # Fetch achievement data from Steam API (JSON cache, 7-day TTL)
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

        cache_file = self._cache_dir / "store_data" / ("%s_achievements.json" % app_id)
        if cache_file.exists():
            try:
                age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
                if age < timedelta(days=7):
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
            int_id = int(app_id)

            schema = api.get_game_schema(int_id)
            schema_achs = (schema or {}).get("achievements", [])
            cache_file.parent.mkdir(exist_ok=True)

            if not schema_achs:
                data = {"total": 0, "unlocked": 0, "percentage": 0.0, "perfect": False}
                with open(cache_file, "w") as f:
                    json.dump(data, f)
                persist_achievement_stats(int_id, 0, 0, 0.0, False)
                self._achievements_checked.add(app_id)
                return

            total = len(schema_achs)

            player_achs = api.get_player_achievements(int_id, steam_id)
            pmap = {}
            if player_achs:
                for ach in player_achs:
                    pmap[ach.get("apiname", "")] = ach

            global_pcts = SteamWebAPI.get_global_achievement_percentages(int_id)

            unlocked = 0
            records = []
            for sa in schema_achs:
                api_name = sa.get("name", "")
                pa = pmap.get(api_name, {})
                is_done = bool(pa.get("achieved", 0))
                if is_done:
                    unlocked += 1
                records.append(
                    {
                        "achievement_id": api_name,
                        "name": sa.get("displayName", api_name),
                        "description": sa.get("description", ""),
                        "is_unlocked": is_done,
                        "unlock_time": pa.get("unlocktime", 0) or 0,
                        "is_hidden": bool(sa.get("hidden", 0)),
                        "rarity_percentage": global_pcts.get(api_name, 0.0),
                    }
                )

            pct = (unlocked / total * 100) if total > 0 else 0.0
            perfect = unlocked == total and total > 0

            data = {
                "total": total,
                "unlocked": unlocked,
                "percentage": round(pct, 1),
                "perfect": perfect,
            }
            with open(cache_file, "w") as f:
                json.dump(data, f)

            apply_achievement_data(game, data)
            persist_achievement_stats(int_id, total, unlocked, pct, perfect)
            persist_achievements(int_id, records)

        except Exception as exc:
            logger.debug("Achievement on-demand fetch failed for %s: %s", app_id, exc)

        self._achievements_checked.add(app_id)
