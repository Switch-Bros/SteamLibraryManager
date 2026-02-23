# src/services/game_detail_service.py

"""Service for fetching detailed game data from external APIs.

Extracted from GameManager to separate the concern of fetching and caching
store data, reviews, ProtonDB ratings, Steam Deck status, news, HLTB
completion times, and achievement data from core game management logic.

On-demand enrichment: When a user clicks a game, this service fetches
HLTB and achievement data automatically (if missing) alongside the
existing store/review/ProtonDB/Deck fetches. Results are cached locally
and persisted to the SQLite database.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import requests

from src.utils.age_ratings import USK_TO_PEGI

from src.core.game import Game
from src.utils.date_utils import format_timestamp_to_date
from src.utils.i18n import t

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

        # Basic metadata (existing checks)
        if not game.developer or not game.proton_db_rating or not game.steam_deck_status:
            return True

        # HLTB: not yet checked and no data present
        if app_id not in self._hltb_checked and not any(
            (game.hltb_main_story, game.hltb_main_extras, game.hltb_completionist)
        ):
            return True

        # Achievements: not yet checked, game type is "game" or unknown, no data present
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
        self._fetch_store_data(app_id)
        self._fetch_review_stats(app_id)
        self._fetch_proton_rating(app_id)
        self._fetch_steam_deck_status(app_id)
        self._fetch_last_update(app_id)
        self._fetch_hltb_data(app_id)
        self._fetch_achievement_data(app_id)
        return True

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
                        self._apply_store_data(app_id, data)
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
                self._apply_store_data(app_id, game_data)
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
                        self._apply_review_data(app_id, data)
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
                self._apply_review_data(app_id, data)
        except (requests.RequestException, ValueError, KeyError, OSError):
            pass

    def _fetch_proton_rating(self, app_id: str) -> None:
        """Fetches ProtonDB compatibility rating.

        Checks the DB cache first (7-day TTL), then falls back to the
        ProtonDB API via ProtonDBClient. Persists results to the database.

        Args:
            app_id: The Steam app ID.
        """
        unknown_status = "unknown"

        if app_id not in self._games:
            return

        # 1. DB cache lookup (7-day TTL)
        try:
            from src.core.database import Database
            from src.config import config

            db_path = config.DATA_DIR / "games.db"
            if db_path.exists():
                db = Database(db_path)
                cached = db.get_cached_protondb(int(app_id))
                if cached:
                    self._games[app_id].proton_db_rating = cached["tier"]
                    db.close()
                    return
                db.close()
        except Exception as exc:
            logger.debug("ProtonDB DB lookup failed for %s: %s", app_id, exc)

        # 2. API call via ProtonDBClient
        try:
            from src.core.database import Database as DB
            from src.integrations.protondb_api import ProtonDBClient

            client = ProtonDBClient()
            result = client.get_rating(int(app_id))

            if result:
                self._games[app_id].proton_db_rating = result.tier

                # Persist to DB
                try:
                    from src.config import config as cfg

                    db_path = cfg.DATA_DIR / "games.db"
                    if db_path.exists():
                        db = DB(db_path)
                        db.upsert_protondb(
                            int(app_id),
                            tier=result.tier,
                            confidence=result.confidence,
                            trending_tier=result.trending_tier,
                            score=result.score,
                            best_reported=result.best_reported,
                        )
                        db.commit()
                        db.close()
                except Exception as exc:
                    logger.debug("ProtonDB DB persist failed for %s: %s", app_id, exc)
            else:
                self._games[app_id].proton_db_rating = unknown_status

        except Exception:
            self._games[app_id].proton_db_rating = unknown_status

    def _fetch_steam_deck_status(self, app_id: str) -> None:
        """Fetches Steam Deck compatibility status from Valve's Deck API.

        Args:
            app_id: The Steam app ID.
        """
        cache_file = self._cache_dir / "store_data" / f"{app_id}_deck.json"
        unknown_status = "unknown"

        if cache_file.exists():
            try:
                cache_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
                if cache_age < timedelta(days=7):
                    with open(cache_file, "r") as f:
                        data = json.load(f)
                        if app_id in self._games:
                            self._games[app_id].steam_deck_status = data.get("status", unknown_status)
                    return
            except (OSError, json.JSONDecodeError):
                pass

        try:
            # Use Valve's Steam Deck compatibility API
            url = f"https://store.steampowered.com/saleaction/ajaxgetdeckappcompatibilityreport?nAppID={app_id}"
            headers = {"User-Agent": "SteamLibraryManager/1.0"}
            response = requests.get(url, timeout=5, headers=headers)

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", {})

                # API sometimes returns a list instead of dict - handle both cases
                if isinstance(results, list):
                    results = results[0] if results else {}

                resolved_category = results.get("resolved_category", 0) if isinstance(results, dict) else 0

                # Steam Deck compatibility categories:
                # 0 = Unknown, 1 = Unsupported, 2 = Playable, 3 = Verified
                status_map = {0: "unknown", 1: "unsupported", 2: "playable", 3: "verified"}
                status = status_map.get(resolved_category, unknown_status)

                with open(cache_file, "w") as f:
                    json.dump({"status": status, "category": resolved_category}, f)
                if app_id in self._games:
                    self._games[app_id].steam_deck_status = status
                return

            if app_id in self._games:
                self._games[app_id].steam_deck_status = unknown_status
        except (requests.RequestException, ValueError, KeyError, OSError):
            if app_id in self._games:
                self._games[app_id].steam_deck_status = unknown_status

    def _fetch_last_update(self, app_id: str) -> None:
        """Fetches the last developer update date from Steam News API.

        Args:
            app_id: The Steam app ID.
        """
        cache_file = self._cache_dir / "store_data" / f"{app_id}_news.json"

        if cache_file.exists():
            try:
                cache_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
                if cache_age < timedelta(days=1):
                    with open(cache_file, "r") as f:
                        data = json.load(f)
                        if app_id in self._games:
                            self._games[app_id].last_updated = data.get("last_update", "")
                    return
            except (OSError, json.JSONDecodeError):
                pass

        try:
            # Steam News API - get recent news/updates
            url = "https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/"
            params = {
                "appid": app_id,
                "count": 10,
                "maxlength": 100,
                "format": "json",
            }
            response = requests.get(url, params=params, timeout=5)

            if response.status_code == 200:
                data = response.json()
                news_items = data.get("appnews", {}).get("newsitems", [])

                if news_items:
                    latest_date = news_items[0].get("date", 0)
                    if latest_date:
                        # Use centralised formatter — picks DE/EN style automatically
                        date_str: str = format_timestamp_to_date(latest_date)

                        # Cache the result
                        cache_file.parent.mkdir(exist_ok=True)
                        with open(cache_file, "w") as f:
                            json.dump({"last_update": date_str, "timestamp": latest_date}, f)

                        if app_id in self._games:
                            self._games[app_id].last_updated = date_str
                        return

            # No news found
            if app_id in self._games and not self._games[app_id].last_updated:
                self._games[app_id].last_updated = ""

        except (requests.RequestException, ValueError, KeyError, OSError):
            pass

    def _apply_review_data(self, app_id: str, data: dict) -> None:
        """Parses and applies review data to a game.

        Args:
            app_id: The Steam app ID.
            data: The review data from the Steam API.
        """
        if app_id not in self._games:
            return
        game = self._games[app_id]
        summary = data.get("query_summary", {})

        review_score_en = summary.get("review_score_desc", "")

        # Map Steam's English review labels to i18n keys for localisation
        _REVIEW_KEY_MAP: dict[str, str] = {
            "Overwhelmingly Positive": "ui.reviews.overwhelmingly_positive",
            "Very Positive": "ui.reviews.very_positive",
            "Positive": "ui.reviews.positive",
            "Mostly Positive": "ui.reviews.mostly_positive",
            "Mixed": "ui.reviews.mixed",
            "Mostly Negative": "ui.reviews.mostly_negative",
            "Negative": "ui.reviews.negative",
            "Very Negative": "ui.reviews.very_negative",
            "Overwhelmingly Negative": "ui.reviews.overwhelmingly_negative",
            "No user reviews": "ui.reviews.no_reviews",
        }

        # Translate via i18n — falls back to English label if key missing
        i18n_key: str | None = _REVIEW_KEY_MAP.get(review_score_en)
        game.review_score = t(i18n_key) if i18n_key else (review_score_en or t("common.unknown"))
        game.review_count = summary.get("total_reviews", 0)

    def _apply_store_data(self, app_id: str, data: dict) -> None:
        """Parses and applies store data to a game.

        Args:
            app_id: The Steam app ID.
            data: The store data from the Steam API.
        """
        game = self._games[app_id]
        if not game.name_overridden:
            game.developer = ", ".join(data.get("developers", []))
            game.publisher = ", ".join(data.get("publishers", []))
            release = data.get("release_date", {})
            if release.get("date"):
                game.release_year = release["date"]
        genres = data.get("genres", [])
        game.genres = [g["description"] for g in genres]
        categories = data.get("categories", [])
        tags = [c["description"] for c in categories]
        game.tags = list(set(game.tags + tags))

        # Extract age ratings (PEGI, ESRB, USK)
        ratings = data.get("ratings") or {}

        # Priority 1: PEGI (used in most of Europe)
        if "pegi" in ratings:
            pegi_data = ratings["pegi"]
            game.pegi_rating = pegi_data.get("rating", "")

        # Priority 2: USK (Germany) -> Convert to PEGI
        elif "usk" in ratings:
            usk_data = ratings["usk"]
            usk_rating = usk_data.get("rating", "")

            if usk_rating in USK_TO_PEGI:
                game.pegi_rating = USK_TO_PEGI[usk_rating]

        # Priority 3: ESRB (USA) - store for fallback display
        if "esrb" in ratings:
            esrb_data = ratings["esrb"]
            game.esrb_rating = esrb_data.get("rating", "")

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

        # Skip if data is already present (loaded from DB)
        if any((game.hltb_main_story, game.hltb_main_extras, game.hltb_completionist)):
            self._hltb_checked.add(app_id)
            return

        # Check cache
        cache_file = self._cache_dir / "store_data" / f"{app_id}_hltb.json"
        if cache_file.exists():
            try:
                cache_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
                if cache_age < timedelta(days=7):
                    with open(cache_file, "r") as f:
                        data = json.load(f)
                    self._apply_hltb_data(app_id, data)
                    self._hltb_checked.add(app_id)
                    return
            except (OSError, json.JSONDecodeError):
                pass

        # Fetch from HLTB API (locked to prevent concurrent endpoint discovery)
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
                    self._apply_hltb_data(app_id, data)
                    self._persist_hltb(int(app_id), result.main_story, result.main_extras, result.completionist)
                else:
                    # Cache "no data" to avoid re-fetching
                    with open(cache_file, "w") as f:
                        json.dump({"no_data": True}, f)
            except Exception as exc:
                logger.debug("HLTB on-demand fetch failed for %s: %s", app_id, exc)

        self._hltb_checked.add(app_id)

    def _apply_hltb_data(self, app_id: str, data: dict) -> None:
        """Applies cached HLTB data to a game object.

        Args:
            app_id: The Steam app ID.
            data: Dict with main_story, main_extras, completionist keys.
        """
        if app_id not in self._games or data.get("no_data"):
            return
        game = self._games[app_id]
        game.hltb_main_story = float(data.get("main_story", 0.0))
        game.hltb_main_extras = float(data.get("main_extras", 0.0))
        game.hltb_completionist = float(data.get("completionist", 0.0))

    @staticmethod
    def _persist_hltb(app_id: int, main_story: float, main_extras: float, completionist: float) -> None:
        """Persists HLTB data to the SQLite database.

        Opens a short-lived DB connection to write the data,
        following the same pattern as batch enrichment threads.

        Args:
            app_id: Steam app ID (int).
            main_story: Hours to complete main story.
            main_extras: Hours to complete main + extras.
            completionist: Hours for 100% completion.
        """
        try:
            from src.core.database import Database
            from src.config import config

            db_path = config.DATA_DIR / "games.db"
            if not db_path.exists():
                return
            db = Database(db_path)
            db.conn.execute(
                """
                INSERT OR REPLACE INTO hltb_data
                (app_id, main_story, main_extras, completionist, last_updated)
                VALUES (?, ?, ?, ?, ?)
                """,
                (app_id, main_story, main_extras, completionist, int(time.time())),
            )
            db.conn.commit()
            db.close()
        except Exception as exc:
            logger.debug("Failed to persist HLTB data for %d: %s", app_id, exc)

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

        # Skip non-game types
        if game.app_type and game.app_type not in ("game", ""):
            self._achievements_checked.add(app_id)
            return

        # Skip if data is already present (loaded from DB)
        if game.achievement_total > 0:
            self._achievements_checked.add(app_id)
            return

        # Check cache
        cache_file = self._cache_dir / "store_data" / f"{app_id}_achievements.json"
        if cache_file.exists():
            try:
                cache_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
                if cache_age < timedelta(days=7):
                    with open(cache_file, "r") as f:
                        data = json.load(f)
                    self._apply_achievement_data(app_id, data)
                    self._achievements_checked.add(app_id)
                    return
            except (OSError, json.JSONDecodeError):
                pass

        # Check config for API key + Steam ID
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

        # Fetch from Steam Web API
        try:
            from src.integrations.steam_web_api import SteamWebAPI

            api = SteamWebAPI(api_key)
            int_app_id = int(app_id)

            # 1. Get achievement schema
            schema = api.get_game_schema(int_app_id)
            schema_achievements = (schema or {}).get("achievements", [])

            cache_file.parent.mkdir(exist_ok=True)

            if not schema_achievements:
                # Game has no achievements — cache and persist total=0
                data = {"total": 0, "unlocked": 0, "percentage": 0.0, "perfect": False}
                with open(cache_file, "w") as f:
                    json.dump(data, f)
                self._persist_achievement_stats(int_app_id, 0, 0, 0.0, False)
                self._achievements_checked.add(app_id)
                return

            total = len(schema_achievements)

            # 2. Get player progress
            player_achievements = api.get_player_achievements(int_app_id, steam_id)
            player_map: dict[str, dict] = {}
            if player_achievements:
                for ach in player_achievements:
                    player_map[ach.get("apiname", "")] = ach

            # 3. Get global rarity (no auth needed)
            global_pcts = SteamWebAPI.get_global_achievement_percentages(int_app_id)

            # 4. Merge and count
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

            # 5. Calculate stats
            completion_pct = (unlocked_count / total * 100) if total > 0 else 0.0
            perfect = unlocked_count == total and total > 0

            # 6. Cache + apply + persist
            data = {
                "total": total,
                "unlocked": unlocked_count,
                "percentage": round(completion_pct, 1),
                "perfect": perfect,
            }
            with open(cache_file, "w") as f:
                json.dump(data, f)

            self._apply_achievement_data(app_id, data)
            self._persist_achievement_stats(int_app_id, total, unlocked_count, completion_pct, perfect)
            self._persist_achievements(int_app_id, achievement_records)

        except Exception as exc:
            logger.debug("Achievement on-demand fetch failed for %s: %s", app_id, exc)

        self._achievements_checked.add(app_id)

    def _apply_achievement_data(self, app_id: str, data: dict) -> None:
        """Applies cached achievement stats to a game object.

        Args:
            app_id: The Steam app ID.
            data: Dict with total, unlocked, percentage, perfect keys.
        """
        if app_id not in self._games:
            return
        game = self._games[app_id]
        game.achievement_total = int(data.get("total", 0))
        game.achievement_unlocked = int(data.get("unlocked", 0))
        game.achievement_percentage = float(data.get("percentage", 0.0))
        game.achievement_perfect = bool(data.get("perfect", False))

    @staticmethod
    def _persist_achievement_stats(app_id: int, total: int, unlocked: int, percentage: float, perfect: bool) -> None:
        """Persists achievement summary stats to the database.

        Args:
            app_id: Steam app ID (int).
            total: Total number of achievements.
            unlocked: Number of unlocked achievements.
            percentage: Completion percentage (0-100).
            perfect: Whether all achievements are unlocked.
        """
        try:
            from src.core.database import Database
            from src.config import config

            db_path = config.DATA_DIR / "games.db"
            if not db_path.exists():
                return
            db = Database(db_path)
            db.upsert_achievement_stats(app_id, total, unlocked, percentage, perfect)
            db.commit()
            db.close()
        except Exception as exc:
            logger.debug("Failed to persist achievement stats for %d: %s", app_id, exc)

    @staticmethod
    def _persist_achievements(app_id: int, records: list[dict]) -> None:
        """Persists individual achievement records to the database.

        Args:
            app_id: Steam app ID (int).
            records: List of achievement dicts.
        """
        try:
            from src.core.database import Database
            from src.config import config

            db_path = config.DATA_DIR / "games.db"
            if not db_path.exists():
                return
            db = Database(db_path)
            db.upsert_achievements(app_id, records)
            db.commit()
            db.close()
        except Exception as exc:
            logger.debug("Failed to persist achievements for %d: %s", app_id, exc)
