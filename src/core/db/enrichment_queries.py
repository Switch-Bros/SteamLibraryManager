"""Enrichment, HLTB, ProtonDB, achievement, and health check queries.

Handles all data enrichment operations: metadata updates, HLTB cache,
ProtonDB ratings, achievement stats, import recording, data quality,
and library health checks.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from src.core.db.models import ImportStats
from src.utils.i18n import t

logger = logging.getLogger("steamlibmgr.database")

__all__ = ["EnrichmentQueryMixin"]


class EnrichmentQueryMixin:
    """Mixin providing enrichment and data quality operations.

    Requires ConnectionBase attributes: conn.
    """

    # ── Metadata enrichment ──────────────────────────────────────────────

    def upsert_game_metadata(self, app_id: int, **fields: Any) -> None:
        """Updates specific metadata fields for an existing game.

        Only updates the provided fields; other columns remain unchanged.
        Silently does nothing if the game does not exist.

        Args:
            app_id: Steam app ID.
            **fields: Column name/value pairs to update (e.g. developer="Valve").
        """
        if not fields:
            return

        valid_columns = {
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
        safe_fields = {k: v for k, v in fields.items() if k in valid_columns}
        if not safe_fields:
            return

        set_clause = ", ".join(f"{col} = ?" for col in safe_fields)
        values = list(safe_fields.values()) + [int(time.time()), app_id]

        self.conn.execute(
            f"UPDATE games SET {set_clause}, updated_at = ? WHERE app_id = ?",
            values,
        )

    def upsert_languages(self, app_id: int, languages: dict[str, dict[str, bool]]) -> None:
        """Replaces language support data for a game.

        Args:
            app_id: Steam app ID.
            languages: Dict mapping language name to support flags.
        """
        if not languages:
            return

        self.conn.execute("DELETE FROM game_languages WHERE app_id = ?", (app_id,))

        rows = [
            (
                app_id,
                lang,
                support.get("interface", False),
                support.get("audio", False),
                support.get("subtitles", False),
            )
            for lang, support in languages.items()
        ]
        self.conn.executemany(
            "INSERT OR REPLACE INTO game_languages"
            " (app_id, language, interface, audio, subtitles)"
            " VALUES (?, ?, ?, ?, ?)",
            rows,
        )

    def get_all_game_ids(self) -> list[tuple[int, str]]:
        """Returns all game-type apps from the database.

        Returns:
            List of (app_id, name) tuples for all games.
        """
        cursor = self.conn.execute("SELECT app_id, name FROM games WHERE app_type IN ('game', '')")
        return [(row[0], row[1]) for row in cursor.fetchall()]

    def get_apps_missing_metadata(self) -> list[tuple[int, str]]:
        """Returns apps with missing developer, publisher, or release date.

        Returns:
            List of (app_id, name) tuples.
        """
        cursor = self.conn.execute(
            "SELECT app_id, name FROM games"
            " WHERE (developer IS NULL OR developer = '')"
            " OR (publisher IS NULL OR publisher = '')"
            " OR ("
            "   (original_release_date IS NULL OR original_release_date = 0)"
            "   AND (steam_release_date IS NULL OR steam_release_date = 0)"
            " )"
        )
        return [(row[0], row[1]) for row in cursor.fetchall()]

    def get_apps_without_hltb(self) -> list[tuple[int, str]]:
        """Returns game-type apps that have no HLTB data.

        Returns:
            List of (app_id, name) tuples.
        """
        cursor = self.conn.execute("""
            SELECT g.app_id, g.name FROM games g
            LEFT JOIN hltb_data h ON g.app_id = h.app_id
            WHERE h.app_id IS NULL AND g.app_type IN ('game', '')
            """)
        return [(row[0], row[1]) for row in cursor.fetchall()]

    # ── HLTB ID cache ────────────────────────────────────────────────────

    _HLTB_CACHE_TTL_DAYS = 30

    def load_hltb_id_cache(self) -> dict[int, int]:
        """Loads the steam_app_id -> hltb_game_id cache from database.

        Only returns entries younger than 30 days.

        Returns:
            Dict mapping steam_app_id to hltb_game_id.
        """
        cutoff = int(time.time()) - (self._HLTB_CACHE_TTL_DAYS * 86400)
        cursor = self.conn.execute(
            "SELECT steam_app_id, hltb_game_id FROM hltb_id_cache WHERE cached_at > ?",
            (cutoff,),
        )
        return {row[0]: row[1] for row in cursor.fetchall()}

    def save_hltb_id_cache(self, mappings: dict[int, int]) -> int:
        """Saves steam_app_id -> hltb_game_id mappings to the cache table.

        Args:
            mappings: Dict mapping steam_app_id to hltb_game_id.

        Returns:
            Number of mappings saved.
        """
        if not mappings:
            return 0

        now = int(time.time())
        rows = [(steam_id, hltb_id, now) for steam_id, hltb_id in mappings.items()]
        self.conn.executemany(
            "INSERT OR REPLACE INTO hltb_id_cache (steam_app_id, hltb_game_id, cached_at) VALUES (?, ?, ?)",
            rows,
        )
        self.conn.commit()
        return len(rows)

    def clear_expired_hltb_cache(self) -> int:
        """Removes expired entries from the HLTB ID cache.

        Returns:
            Number of entries removed.
        """
        cutoff = int(time.time()) - (self._HLTB_CACHE_TTL_DAYS * 86400)
        cursor = self.conn.execute("DELETE FROM hltb_id_cache WHERE cached_at <= ?", (cutoff,))
        self.conn.commit()
        return cursor.rowcount

    # ── ProtonDB ─────────────────────────────────────────────────────────

    _PROTONDB_TTL_DAYS = 7

    def get_cached_protondb(self, app_id: int) -> dict | None:
        """Returns cached ProtonDB rating if fresh enough.

        Args:
            app_id: Steam app ID.

        Returns:
            Dict with tier/confidence/trending/score/best_reported/last_updated,
            or None if not cached or expired.
        """
        cutoff = int(time.time()) - (self._PROTONDB_TTL_DAYS * 86400)
        cursor = self.conn.execute(
            "SELECT tier, confidence, trending_tier, score, best_reported, last_updated"
            " FROM protondb_ratings WHERE app_id = ? AND last_updated > ?",
            (app_id, cutoff),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "tier": row[0],
            "confidence": row[1],
            "trending_tier": row[2],
            "score": float(row[3]),
            "best_reported": row[4],
            "last_updated": int(row[5]),
        }

    def upsert_protondb(
        self,
        app_id: int,
        tier: str,
        confidence: str = "",
        trending_tier: str = "",
        score: float = 0.0,
        best_reported: str = "",
    ) -> None:
        """Inserts or updates a ProtonDB rating.

        Args:
            app_id: Steam app ID.
            tier: Compatibility tier.
            confidence: Confidence level.
            trending_tier: Trending tier direction.
            score: Numeric score.
            best_reported: Best reported tier.
        """
        self.conn.execute(
            """
            INSERT OR REPLACE INTO protondb_ratings
            (app_id, tier, confidence, trending_tier, score, best_reported, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (app_id, tier, confidence, trending_tier, score, best_reported, int(time.time())),
        )

    def get_apps_without_protondb(self) -> list[tuple[int, str]]:
        """Returns game-type apps that have no ProtonDB rating.

        Returns:
            List of (app_id, name) tuples.
        """
        cursor = self.conn.execute("""
            SELECT g.app_id, g.name FROM games g
            LEFT JOIN protondb_ratings p ON g.app_id = p.app_id
            WHERE p.app_id IS NULL AND g.app_type IN ('game', '')
            """)
        return [(row[0], row[1]) for row in cursor.fetchall()]

    def get_apps_without_pegi(self) -> list[tuple[int, str]]:
        """Returns game-type apps that have no PEGI age rating.

        Returns:
            List of (app_id, name) tuples.
        """
        cursor = self.conn.execute("""
            SELECT app_id, name FROM games
            WHERE (pegi_rating IS NULL OR pegi_rating = '')
            AND app_type IN ('game', '')
            """)
        return [(row[0], row[1]) for row in cursor.fetchall()]

    def batch_get_protondb(self, app_ids: list[int]) -> dict[int, str]:
        """Batch load ProtonDB tiers for multiple app_ids.

        Args:
            app_ids: List of app IDs.

        Returns:
            Dict mapping app_id to tier string.
        """
        if not app_ids:
            return {}

        placeholders = ",".join("?" * len(app_ids))
        cursor = self.conn.execute(
            f"SELECT app_id, tier FROM protondb_ratings WHERE app_id IN ({placeholders})",
            app_ids,
        )
        return {row[0]: row[1] for row in cursor.fetchall()}

    # ── Achievement operations ───────────────────────────────────────────

    def upsert_achievement_stats(
        self, app_id: int, total: int, unlocked: int, completion_pct: float, perfect: bool
    ) -> None:
        """Inserts or updates achievement statistics for a game.

        Args:
            app_id: Steam app ID.
            total: Total number of achievements.
            unlocked: Number of unlocked achievements.
            completion_pct: Completion percentage (0.0-100.0).
            perfect: Whether all achievements are unlocked.
        """
        self.conn.execute(
            """
            INSERT OR REPLACE INTO achievement_stats
            (app_id, total_achievements, unlocked_achievements, completion_percentage, perfect_game)
            VALUES (?, ?, ?, ?, ?)
            """,
            (app_id, total, unlocked, round(completion_pct, 2), perfect),
        )

    def upsert_achievements(self, app_id: int, achievements: list[dict]) -> None:
        """Batch inserts or updates individual achievements for a game.

        Args:
            app_id: Steam app ID.
            achievements: List of achievement dicts.
        """
        if not achievements:
            return

        rows = [
            (
                app_id,
                ach.get("achievement_id", ""),
                ach.get("name", ""),
                ach.get("description", ""),
                ach.get("is_unlocked", False),
                ach.get("unlock_time", 0),
                ach.get("is_hidden", False),
                ach.get("rarity_percentage", 0.0),
            )
            for ach in achievements
        ]
        self.conn.executemany(
            """
            INSERT OR REPLACE INTO achievements
            (app_id, achievement_id, name, description,
             is_unlocked, unlock_time, is_hidden, rarity_percentage)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

    def get_apps_without_achievements(self) -> list[tuple[int, str]]:
        """Returns game-type apps that have no achievement_stats entry.

        Returns:
            List of (app_id, name) tuples.
        """
        cursor = self.conn.execute("""
            SELECT g.app_id, g.name FROM games g
            LEFT JOIN achievement_stats a ON g.app_id = a.app_id
            WHERE a.app_id IS NULL AND g.app_type IN ('game', '')
            """)
        return [(row[0], row[1]) for row in cursor.fetchall()]

    # ── Health check queries ─────────────────────────────────────────────

    def get_games_missing_artwork(self) -> list[tuple[int, str]]:
        """Returns games that have no custom artwork entry.

        Returns:
            List of (app_id, name) tuples.
        """
        cursor = self.conn.execute("""
            SELECT g.app_id, g.name FROM games g
            LEFT JOIN custom_artwork ca ON g.app_id = ca.app_id
            WHERE ca.app_id IS NULL AND g.app_type IN ('game', '')
        """)
        return [(row[0], row[1]) for row in cursor.fetchall()]

    def get_stale_hltb_count(self, max_age_days: int = 30) -> int:
        """Counts games with HLTB cache older than max_age_days.

        Args:
            max_age_days: Maximum cache age in days.

        Returns:
            Number of games with stale HLTB data.
        """
        cutoff = int(time.time()) - (max_age_days * 86400)
        cursor = self.conn.execute(
            "SELECT COUNT(*) FROM hltb_data WHERE last_updated < ?",
            (cutoff,),
        )
        return cursor.fetchone()[0]

    def get_stale_protondb_count(self, max_age_days: int = 7) -> int:
        """Counts games with ProtonDB cache older than max_age_days.

        Args:
            max_age_days: Maximum cache age in days.

        Returns:
            Number of games with stale ProtonDB data.
        """
        cutoff = int(time.time()) - (max_age_days * 86400)
        cursor = self.conn.execute(
            "SELECT COUNT(*) FROM protondb_ratings WHERE last_updated < ?",
            (cutoff,),
        )
        return cursor.fetchone()[0]

    # ── Import recording ─────────────────────────────────────────────────

    def record_import(self, stats: ImportStats) -> None:
        """Record import statistics.

        Args:
            stats: Import statistics.
        """
        self.conn.execute(
            """
            INSERT INTO import_history
            (import_time, source, games_imported, games_updated, games_failed, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                int(time.time()),
                stats.source,
                stats.games_imported,
                stats.games_updated,
                stats.games_failed,
                t("logs.db.import_duration", duration=f"{stats.duration_seconds:.2f}"),
            ),
        )
        self.conn.commit()

    # ── Data quality ─────────────────────────────────────────────────────

    def repair_placeholder_names(self) -> int:
        """Replace placeholder names with empty strings in the database.

        Returns:
            Number of names cleaned.
        """
        cursor = self.conn.execute("""
            SELECT COUNT(*) FROM games
            WHERE name GLOB 'App [0-9]*'
               OR name GLOB 'Unknown App [0-9]*'
               OR name GLOB 'Unbekannte App [0-9]*'
            """)
        count = cursor.fetchone()[0]

        if count > 0:
            self.conn.execute(
                """
                UPDATE games SET name = '', updated_at = ?
                WHERE name GLOB 'App [0-9]*'
                   OR name GLOB 'Unknown App [0-9]*'
                   OR name GLOB 'Unbekannte App [0-9]*'
                """,
                (int(time.time()),),
            )
            self.conn.commit()
            logger.info(t("logs.db.repaired_placeholders", count=count))

        return count
