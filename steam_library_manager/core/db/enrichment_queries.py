#
# steam_library_manager/core/db/enrichment_queries.py
# DB queries for enrichment data (HLTB, ProtonDB, achievements, health)
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
import time

from steam_library_manager.utils.i18n import t

logger = logging.getLogger("steamlibmgr.database")

__all__ = ["EnrichmentQueryMixin"]


class EnrichmentQueryMixin:
    """Enrichment and data quality queries.

    HLTB times, ProtonDB ratings, achievements, health checks.
    Needs conn from ConnectionBase.
    """

    # shared helpers

    def _apps_without(self, tbl):
        # apps without entry
        cur = self.conn.execute(
            "SELECT g.app_id, g.name FROM games g"
            " LEFT JOIN %s t ON g.app_id = t.app_id"
            " WHERE t.app_id IS NULL AND g.app_type IN ('game', '')" % tbl
        )
        return [(r[0], r[1]) for r in cur.fetchall()]

    def _stale_count(self, tbl, days):
        cut = int(time.time()) - (days * 86400)
        cur = self.conn.execute("SELECT COUNT(*) FROM %s WHERE last_updated < ?" % tbl, (cut,))
        return cur.fetchone()[0]

    # metadata

    def upsert_game_metadata(self, app_id, **flds):
        if not flds:
            return

        cols = {
            "name",
            "sort_as",
            "app_type",
            "developer",
            "publisher",
            "original_release_date",
            "steam_release_date",
            "release_date",
            "review_score",
            "review_percentage",
            "review_count",
            "is_free",
            "is_early_access",
            "vr_support",
            "controller_support",
            "cloud_saves",
            "workshop",
            "trading_cards",
            "achievements_total",
            "platforms",
        }
        ok = {k: v for k, v in flds.items() if k in cols}
        if not ok:
            return

        st = ", ".join("%s = ?" % c for c in ok)
        vs = list(ok.values()) + [int(time.time()), app_id]
        self.conn.execute("UPDATE games SET %s, updated_at = ? WHERE app_id = ?" % st, vs)

    def upsert_languages(self, app_id, langs):
        if not langs:
            return
        self.conn.execute("DELETE FROM game_languages WHERE app_id = ?", (app_id,))
        rows = [
            (app_id, lang, sup.get("interface", False), sup.get("audio", False), sup.get("subtitles", False))
            for lang, sup in langs.items()
        ]
        self.conn.executemany(
            "INSERT OR REPLACE INTO game_languages"
            " (app_id, language, interface, audio, subtitles) VALUES (?, ?, ?, ?, ?)",
            rows,
        )

    def get_all_game_ids(self):
        cur = self.conn.execute("SELECT app_id, name FROM games WHERE app_type IN ('game', '')")
        return [(r[0], r[1]) for r in cur.fetchall()]

    def get_apps_missing_metadata(self):
        cur = self.conn.execute(
            "SELECT app_id, name FROM games"
            " WHERE (developer IS NULL OR developer = '')"
            " OR (publisher IS NULL OR publisher = '')"
            " OR ((original_release_date IS NULL OR original_release_date = 0)"
            "     AND (steam_release_date IS NULL OR steam_release_date = 0))"
        )
        return [(r[0], r[1]) for r in cur.fetchall()]

    def get_apps_without_hltb(self):
        return self._apps_without("hltb_data")

    # hltb cache

    _HLTB_TTL = 30  # days

    def load_hltb_id_cache(self):
        cut = int(time.time()) - (self._HLTB_TTL * 86400)
        cur = self.conn.execute("SELECT steam_app_id, hltb_game_id FROM hltb_id_cache WHERE cached_at > ?", (cut,))
        return {r[0]: r[1] for r in cur.fetchall()}

    def save_hltb_id_cache(self, maps):
        if not maps:
            return 0
        now = int(time.time())
        rows = [(sid, hid, now) for sid, hid in maps.items()]
        self.conn.executemany(
            "INSERT OR REPLACE INTO hltb_id_cache (steam_app_id, hltb_game_id, cached_at) VALUES (?, ?, ?)", rows
        )
        self.conn.commit()
        return len(rows)

    def clear_expired_hltb_cache(self):
        cut = int(time.time()) - (self._HLTB_TTL * 86400)
        cur = self.conn.execute("DELETE FROM hltb_id_cache WHERE cached_at <= ?", (cut,))
        self.conn.commit()
        return cur.rowcount

    # protondb

    _PDB_TTL = 7  # days

    def get_cached_protondb(self, app_id):
        cut = int(time.time()) - (self._PDB_TTL * 86400)
        cur = self.conn.execute(
            "SELECT tier, confidence, trending_tier, score, best_reported, last_updated"
            " FROM protondb_ratings WHERE app_id = ? AND last_updated > ?",
            (app_id, cut),
        )
        r = cur.fetchone()
        if not r:
            return None
        return {
            "tier": r[0],
            "confidence": r[1],
            "trending_tier": r[2],
            "score": float(r[3]),
            "best_reported": r[4],
            "last_updated": int(r[5]),
        }

    def upsert_protondb(self, app_id, tier, confidence="", trending_tier="", score=0.0, best_reported=""):
        self.conn.execute(
            "INSERT OR REPLACE INTO protondb_ratings"
            " (app_id, tier, confidence, trending_tier, score, best_reported, last_updated)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (app_id, tier, confidence, trending_tier, score, best_reported, int(time.time())),
        )

    def get_apps_without_protondb(self):
        return self._apps_without("protondb_ratings")

    def get_apps_without_pegi(self):
        cur = self.conn.execute(
            "SELECT app_id, name FROM games"
            " WHERE (pegi_rating IS NULL OR pegi_rating = '')"
            " AND app_type IN ('game', '')"
        )
        return [(r[0], r[1]) for r in cur.fetchall()]

    def batch_get_protondb(self, aids):
        if not aids:
            return {}
        ph = ",".join("?" * len(aids))
        cur = self.conn.execute("SELECT app_id, tier FROM protondb_ratings WHERE app_id IN (%s)" % ph, aids)
        return {r[0]: r[1] for r in cur.fetchall()}

    # achievements

    def upsert_achievement_stats(self, app_id, total, unlocked, pct, perfect):
        self.conn.execute(
            "INSERT OR REPLACE INTO achievement_stats"
            " (app_id, total_achievements, unlocked_achievements, completion_percentage, perfect_game)"
            " VALUES (?, ?, ?, ?, ?)",
            (app_id, total, unlocked, round(pct, 2), perfect),
        )

    def upsert_achievements(self, app_id, achs):
        if not achs:
            return
        rows = [
            (
                app_id,
                a.get("achievement_id", ""),
                a.get("name", ""),
                a.get("description", ""),
                a.get("is_unlocked", False),
                a.get("unlock_time", 0),
                a.get("is_hidden", False),
                a.get("rarity_percentage", 0.0),
            )
            for a in achs
        ]
        self.conn.executemany(
            "INSERT OR REPLACE INTO achievements"
            " (app_id, achievement_id, name, description, is_unlocked, unlock_time, is_hidden, rarity_percentage)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )

    def get_apps_without_achievements(self):
        return self._apps_without("achievement_stats")

    # health check

    def get_games_missing_artwork(self):
        return self._apps_without("custom_artwork")

    def get_stale_hltb_count(self, ma_days=30):
        return self._stale_count("hltb_data", ma_days)

    def get_stale_protondb_count(self, ma_days=7):
        return self._stale_count("protondb_ratings", ma_days)

    # import recording

    def record_import(self, stats):
        self.conn.execute(
            "INSERT INTO import_history"
            " (import_time, source, games_imported, games_updated, games_failed, notes)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (
                int(time.time()),
                stats.source,
                stats.games_imported,
                stats.games_updated,
                stats.games_failed,
                t("logs.db.import_duration", duration="%.2f" % stats.duration_seconds),
            ),
        )
        self.conn.commit()

    # data quality

    def repair_placeholder_names(self):
        cur = self.conn.execute(
            "SELECT COUNT(*) FROM games"
            " WHERE name GLOB 'App [0-9]*' OR name GLOB 'Unknown App [0-9]*' OR name GLOB 'Unbekannte App [0-9]*'"
        )
        cnt = cur.fetchone()[0]
        if cnt > 0:
            self.conn.execute(
                "UPDATE games SET name = '', updated_at = ?"
                " WHERE name GLOB 'App [0-9]*' OR name GLOB 'Unknown App [0-9]*' OR name GLOB 'Unbekannte App [0-9]*'",
                (int(time.time()),),
            )
            self.conn.commit()
            logger.info(t("logs.db.repaired_placeholders", count=cnt))
        return cnt
