#
# steam_library_manager/core/db/curator_mixin.py
# Curator CRUD, recommendations, and overlap scoring
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import datetime
import logging
import time
from typing import Any

logger = logging.getLogger("steamlibmgr.database")

__all__ = ["CuratorMixin"]


class CuratorMixin:
    """Curator CRUD and recommendation queries. Requires ``conn``."""

    def get_all_curators(self) -> list[dict[str, Any]]:
        """Returns all curators as list of dicts."""
        cursor = self.conn.execute(
            "SELECT curator_id, name, url, source, active, last_updated, total_count " "FROM curators ORDER BY name"
        )
        columns = [d[0] for d in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_active_curators(self) -> list[dict[str, Any]]:
        """Returns only active curators."""
        cursor = self.conn.execute(
            "SELECT curator_id, name, url, source, active, last_updated, total_count "
            "FROM curators WHERE active = 1 ORDER BY name"
        )
        columns = [d[0] for d in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def add_curator(
        self,
        curator_id: int,
        name: str,
        url: str = "",
        source: str = "manual",
    ) -> None:
        """Insert or update a curator (upsert)."""
        self.conn.execute(
            """INSERT INTO curators (curator_id, name, url, source)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(curator_id) DO UPDATE SET
                   name = excluded.name,
                   url = excluded.url""",
            (curator_id, name, url, source),
        )
        self.conn.commit()

    def remove_curator(self, curator_id: int) -> None:
        """Delete curator and all recommendations (CASCADE)."""
        self.conn.execute("DELETE FROM curators WHERE curator_id = ?", (curator_id,))
        self.conn.commit()

    def toggle_curator_active(self, curator_id: int, active: bool) -> None:
        self.conn.execute(
            "UPDATE curators SET active = ? WHERE curator_id = ?",
            (1 if active else 0, curator_id),
        )
        self.conn.commit()

    def save_curator_recommendations(self, curator_id: int, app_ids: list[int]) -> None:
        """Atomic replace of all recommendations for a curator."""
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with self.conn:
            self.conn.execute(
                "DELETE FROM curator_recommendations WHERE curator_id = ?",
                (curator_id,),
            )
            self.conn.executemany(
                "INSERT INTO curator_recommendations (curator_id, app_id) " "VALUES (?, ?)",
                [(curator_id, aid) for aid in app_ids],
            )
            self.conn.execute(
                "UPDATE curators SET total_count = ?, last_updated = ? " "WHERE curator_id = ?",
                (len(app_ids), now, curator_id),
            )

    def get_recommendations_for_curator(self, curator_id: int) -> set[int]:
        """Returns app_ids recommended by this curator."""
        cursor = self.conn.execute(
            "SELECT app_id FROM curator_recommendations WHERE curator_id = ?",
            (curator_id,),
        )
        return {row[0] for row in cursor.fetchall()}

    def get_curators_for_app(self, app_id: int) -> list[tuple[int, str]]:
        """Active curators recommending this app as (curator_id, name) tuples."""
        cursor = self.conn.execute(
            """SELECT c.curator_id, c.name
               FROM curator_recommendations cr
               JOIN curators c ON c.curator_id = cr.curator_id
               WHERE cr.app_id = ? AND c.active = 1
               ORDER BY c.name""",
            (app_id,),
        )
        return cursor.fetchall()

    def get_curator_overlap_score(self, app_id: int) -> tuple[int, int]:
        """Returns (recommending_count, total_active_curators)."""
        total = self.conn.execute("SELECT COUNT(*) FROM curators WHERE active = 1").fetchone()[0]
        recommending = self.conn.execute(
            """SELECT COUNT(*) FROM curator_recommendations cr
               JOIN curators c ON c.curator_id = cr.curator_id
               WHERE cr.app_id = ? AND c.active = 1""",
            (app_id,),
        ).fetchone()[0]
        return (recommending, total)

    def get_curators_needing_refresh(self, max_age_days: int = 7) -> list[dict[str, Any]]:
        """Curators whose data is older than max_age_days."""
        cutoff = (datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=max_age_days)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        cursor = self.conn.execute(
            """SELECT curator_id, name, url FROM curators
               WHERE last_updated IS NULL OR last_updated < ?""",
            (cutoff,),
        )
        columns = [d[0] for d in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
