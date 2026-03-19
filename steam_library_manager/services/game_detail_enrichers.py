#
# steam_library_manager/services/game_detail_enrichers.py
# Source-specific enrichment functions for game details
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

# T06 condensation check: a field-map approach was evaluated but not applied
# because each field uses a different transformation (join, nested lookup,
# list comprehension, set merge). Only developer/publisher share the same
# pattern, which is too few to justify a mapping abstraction.

import json
import logging
import time
from contextlib import contextmanager
from datetime import datetime, timedelta

import requests

from steam_library_manager.utils.age_ratings import USK_TO_PEGI
from steam_library_manager.utils.date_utils import format_timestamp_to_date
from steam_library_manager.utils.deck_utils import fetch_deck_compatibility
from steam_library_manager.utils.i18n import t
from steam_library_manager.utils.timeouts import HTTP_TIMEOUT_SHORT

logger = logging.getLogger("steamlibmgr.game_detail_enrichers")

__all__ = [
    "apply_achievement_data",
    "apply_hltb_data",
    "apply_review_data",
    "apply_store_data",
    "fetch_last_update",
    "fetch_proton_rating",
    "fetch_steam_deck_status",
    "persist_achievement_stats",
    "persist_achievements",
    "persist_hltb",
]

# Map Steam's English review labels to i18n keys
_REVIEW_KEY_MAP = {
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


# Apply functions (transform API data -> Game attributes)


def apply_review_data(game, data):
    # Apply review data to a game
    summary = data.get("query_summary", {})
    score_en = summary.get("review_score_desc", "")
    key = _REVIEW_KEY_MAP.get(score_en)
    game.review_score = t(key) if key else (score_en or t("common.unknown"))
    game.review_count = summary.get("total_reviews", 0)


def apply_store_data(game, data):
    # Apply Steam Store metadata to a game
    if not game.name_overridden:
        game.developer = ", ".join(data.get("developers", []))
        game.publisher = ", ".join(data.get("publishers", []))
        release = data.get("release_date", {})
        if release.get("date"):
            from steam_library_manager.utils.date_utils import to_timestamp

            ts = to_timestamp(release["date"])
            if ts:
                game.release_year = ts
    genres = data.get("genres", [])
    game.genres = [g["description"] for g in genres]
    cats = data.get("categories", [])
    tags = [c["description"] for c in cats]
    game.tags = list(set(game.tags + tags))

    # Extract age ratings (PEGI, ESRB, USK)
    ratings = data.get("ratings") or {}
    if "pegi" in ratings:
        game.pegi_rating = ratings["pegi"].get("rating", "")
    elif "usk" in ratings:
        usk = ratings["usk"].get("rating", "")
        if usk in USK_TO_PEGI:
            game.pegi_rating = USK_TO_PEGI[usk]
    if "esrb" in ratings:
        game.esrb_rating = ratings["esrb"].get("rating", "")


def apply_hltb_data(game, data):
    # Apply cached HLTB data to a game
    if data.get("no_data"):
        return
    game.hltb_main_story = float(data.get("main_story", 0.0))
    game.hltb_main_extras = float(data.get("main_extras", 0.0))
    game.hltb_completionist = float(data.get("completionist", 0.0))


def apply_achievement_data(game, data):
    # Apply cached achievement stats to a game
    game.achievement_total = int(data.get("total", 0))
    game.achievement_unlocked = int(data.get("unlocked", 0))
    game.achievement_percentage = float(data.get("percentage", 0.0))
    game.achievement_perfect = bool(data.get("perfect", False))


# DB helper


@contextmanager
def _open_db():
    # Open the games database, yield it, close on exit
    from steam_library_manager.config import config
    from steam_library_manager.core.database import Database

    db_path = config.DATA_DIR / "games.db"
    if not db_path.exists():
        yield None
        return
    db = Database(db_path)
    try:
        yield db
    finally:
        db.close()


# Fetch functions (self-contained API calls with caching)


def fetch_proton_rating(game):
    # Fetch ProtonDB compatibility rating with 7-day DB cache
    app_id = game.app_id
    unk = "unknown"

    # DB cache lookup (7-day TTL)
    try:
        with _open_db() as db:
            if db is not None:
                cached = db.get_cached_protondb(int(app_id))
                if cached:
                    game.proton_db_rating = cached["tier"]
                    return
    except Exception as exc:
        logger.debug("ProtonDB DB lookup failed for %s: %s", app_id, exc)

    # API call + persist
    try:
        from steam_library_manager.integrations.protondb_api import ProtonDBClient, fetch_and_persist_protondb

        client = ProtonDBClient()
        try:
            with _open_db() as db:
                if db is not None:
                    tier = fetch_and_persist_protondb(int(app_id), db, client)
                    game.proton_db_rating = tier or unk
                    return
        except Exception as exc:
            logger.debug("ProtonDB DB persist failed for %s: %s", app_id, exc)

        # DB unavailable -- still try API for in-memory enrichment
        result = client.get_rating(int(app_id))
        game.proton_db_rating = result.tier if result else unk

    except Exception:
        game.proton_db_rating = unk


def fetch_steam_deck_status(game, cache_dir):
    # Fetch Steam Deck compatibility status with file cache
    app_id = game.app_id
    cache_file = cache_dir / "store_data" / ("%s_deck.json" % app_id)
    unk = "unknown"

    if cache_file.exists():
        try:
            age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
            if age < timedelta(days=7):
                with open(cache_file, "r") as f:
                    data = json.load(f)
                    game.steam_deck_status = data.get("status", unk)
                return
        except (OSError, json.JSONDecodeError):
            pass

    # Fetch from API (writes cache file automatically)
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    status = fetch_deck_compatibility(app_id, cache_file.parent)
    game.steam_deck_status = status or unk


def fetch_last_update(game, cache_dir):
    # Fetch the last developer update date from Steam News API
    app_id = game.app_id
    cache_file = cache_dir / "store_data" / ("%s_news.json" % app_id)

    if cache_file.exists():
        try:
            age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
            if age < timedelta(days=1):
                with open(cache_file, "r") as f:
                    data = json.load(f)
                    game.last_updated = data.get("last_update", "")
                return
        except (OSError, json.JSONDecodeError):
            pass

    try:
        url = "https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/"
        params = {"appid": app_id, "count": 10, "maxlength": 100, "format": "json"}
        resp = requests.get(url, params=params, timeout=HTTP_TIMEOUT_SHORT)

        if resp.status_code == 200:
            data = resp.json()
            items = data.get("appnews", {}).get("newsitems", [])
            if items:
                ts = items[0].get("date", 0)
                if ts:
                    date_str = format_timestamp_to_date(ts)
                    cache_file.parent.mkdir(exist_ok=True)
                    with open(cache_file, "w") as f:
                        json.dump({"last_update": date_str, "timestamp": ts}, f)
                    game.last_updated = date_str
                    return

        if not game.last_updated:
            game.last_updated = ""
    except (requests.RequestException, ValueError, KeyError, OSError):
        pass


# Persist functions (write enrichment data to SQLite)


def persist_hltb(app_id, main_story, main_extras, completionist):
    # Persist HLTB data to the SQLite database
    try:
        with _open_db() as db:
            if db is None:
                return
            db.conn.execute(
                """
                INSERT OR REPLACE INTO hltb_data
                (app_id, main_story, main_extras, completionist, last_updated)
                VALUES (?, ?, ?, ?, ?)
                """,
                (app_id, main_story, main_extras, completionist, int(time.time())),
            )
            db.conn.commit()
    except Exception as exc:
        logger.debug("Failed to persist HLTB data for %d: %s", app_id, exc)


def persist_achievement_stats(app_id, total, unlocked, percentage, perfect):
    # Persist achievement summary stats to the database
    try:
        with _open_db() as db:
            if db is None:
                return
            db.upsert_achievement_stats(app_id, total, unlocked, percentage, perfect)
            db.commit()
    except Exception as exc:
        logger.debug("Failed to persist achievement stats for %d: %s", app_id, exc)


def persist_achievements(app_id, records):
    # Persist individual achievement records to the database
    try:
        with _open_db() as db:
            if db is None:
                return
            db.upsert_achievements(app_id, records)
            db.commit()
    except Exception as exc:
        logger.debug("Failed to persist achievements for %d: %s", app_id, exc)
