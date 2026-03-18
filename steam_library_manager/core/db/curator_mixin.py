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

logger = logging.getLogger("steamlibmgr.database")

__all__ = ["CuratorMixin"]


class CuratorMixin:
    """Curator queries - add/remove curators, save recommendations, overlap scores.

    Needs conn from ConnectionBase.
    """

    def get_all_curators(self):
        cur = self.conn.execute(
            "SELECT curator_id, name, url, source, active, last_updated, total_count FROM curators ORDER BY name"
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    def get_active_curators(self):
        cur = self.conn.execute(
            "SELECT curator_id, name, url, source, active, last_updated, total_count"
            " FROM curators WHERE active = 1 ORDER BY name"
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    def add_curator(self, cid, nm, u="", src="manual"):
        self.conn.execute(
            "INSERT INTO curators (curator_id, name, url, source) VALUES (?, ?, ?, ?)"
            " ON CONFLICT(curator_id) DO UPDATE SET name = excluded.name, url = excluded.url",
            (cid, nm, u, src),
        )
        self.conn.commit()

    def remove_curator(self, cid):
        self.conn.execute("DELETE FROM curators WHERE curator_id = ?", (cid,))
        self.conn.commit()

    def toggle_curator_active(self, cid, act):
        self.conn.execute(
            "UPDATE curators SET active = ? WHERE curator_id = ?",
            (1 if act else 0, cid),
        )
        self.conn.commit()

    def save_curator_recommendations(self, cid, aids):
        # atomic replace
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with self.conn:
            self.conn.execute("DELETE FROM curator_recommendations WHERE curator_id = ?", (cid,))
            self.conn.executemany(
                "INSERT INTO curator_recommendations (curator_id, app_id) VALUES (?, ?)",
                [(cid, aid) for aid in aids],
            )
            self.conn.execute(
                "UPDATE curators SET total_count = ?, last_updated = ? WHERE curator_id = ?",
                (len(aids), now, cid),
            )

    def get_recommendations_for_curator(self, cid):
        cur = self.conn.execute("SELECT app_id FROM curator_recommendations WHERE curator_id = ?", (cid,))
        return {r[0] for r in cur.fetchall()}

    def get_curators_for_app(self, aid):
        cur = self.conn.execute(
            "SELECT c.curator_id, c.name FROM curator_recommendations cr"
            " JOIN curators c ON c.curator_id = cr.curator_id"
            " WHERE cr.app_id = ? AND c.active = 1 ORDER BY c.name",
            (aid,),
        )
        return cur.fetchall()

    def get_curator_overlap_score(self, aid):
        tot = self.conn.execute("SELECT COUNT(*) FROM curators WHERE active = 1").fetchone()[0]
        rec = self.conn.execute(
            "SELECT COUNT(*) FROM curator_recommendations cr"
            " JOIN curators c ON c.curator_id = cr.curator_id"
            " WHERE cr.app_id = ? AND c.active = 1",
            (aid,),
        ).fetchone()[0]
        return rec, tot

    def get_curators_needing_refresh(self, max_days=7):
        cut = (datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=max_days)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        cur = self.conn.execute(
            "SELECT curator_id, name, url FROM curators WHERE last_updated IS NULL OR last_updated < ?",
            (cut,),
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
