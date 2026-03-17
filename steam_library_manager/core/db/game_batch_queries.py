#
# steam_library_manager/core/db/game_batch_queries.py
# Batch game queries for bulk import/export
#
# Copyright 2025 SwitchBros
# MIT License
#

from __future__ import annotations

import json
import logging
import sqlite3

from steam_library_manager.core.db.models import DatabaseEntry
from steam_library_manager.utils.i18n import t

logger = logging.getLogger("steamlibmgr.database")

__all__ = ["GameBatchQueryMixin"]


class GameBatchQueryMixin:
    """Batch queries for games."""

    def batch_insert_games(self, ents):
        ins = 0
        for e in ents:
            try:
                self.insert_game(e)
                ins += 1
            except sqlite3.Error as err:
                logger.warning(t("logs.db.import_failed_app", app_id=e.app_id, error=str(err)))
        self.conn.commit()
        return ins

    def get_all_games(self, gtypes=None):
        # bulk load
        if gtypes:
            ph = ",".join("?" * len(gtypes))
            q = "SELECT * FROM games WHERE app_type IN (%s)" % ph
            cur = self.conn.execute(q, tuple(gtypes))
        else:
            cur = self.conn.execute("SELECT * FROM games")

        rows = cur.fetchall()
        if not rows:
            return []

        ids = [r["app_id"] for r in rows]

        # load related
        gr = self._batch_rel("game_genres", "genre", ids)
        tg = self._batch_rel("game_tags", "tag", ids)
        tids = self._batch_tids(ids)
        fr = self._batch_rel("game_franchises", "franchise", ids)
        ln = self._batch_lng(ids)
        mt = self._batch_mt(ids)
        ach = self._batch_ach(ids)

        games = []
        for r in rows:
            d = dict(r)
            aid = d["app_id"]

            d["genres"] = gr.get(aid, [])
            d["tags"] = tg.get(aid, [])
            d["tag_ids"] = tids.get(aid, [])
            d["franchises"] = fr.get(aid, [])
            d["languages"] = ln.get(aid, {})
            d["custom_meta"] = mt.get(aid, {})
            d["platforms"] = json.loads(d["platforms"]) if d["platforms"] else []

            st = ach.get(aid)
            if st:
                tot, unl, pct, perf = st
                d["achievements_total"] = tot
                d["achievement_unlocked"] = unl
                d["achievement_percentage"] = pct
                d["achievement_perfect"] = perf

            for k in ("created_at", "updated_at"):
                d.pop(k, None)

            games.append(DatabaseEntry(**d))

        return games

    def _batch_tids(self, ids):
        if not ids:
            return {}
        ph = ",".join("?" * len(ids))
        cur = self.conn.execute(
            "SELECT app_id, tag_id FROM game_tags WHERE app_id IN (%s) AND tag_id IS NOT NULL" % ph, ids
        )
        out = {}
        for r in cur.fetchall():
            out.setdefault(r[0], []).append(r[1])
        return out

    def _batch_rel(self, tb, cl, ids):
        # loader
        if not ids:
            return {}
        ph = ",".join("?" * len(ids))
        cur = self.conn.execute("SELECT app_id, %s FROM %s WHERE app_id IN (%s)" % (cl, tb, ph), ids)
        out = {}
        for r in cur.fetchall():
            out.setdefault(r[0], []).append(r[1])
        return out

    def _batch_lng(self, ids):
        if not ids:
            return {}
        ph = ",".join("?" * len(ids))
        cur = self.conn.execute(
            "SELECT app_id, language, interface, audio, subtitles FROM game_languages WHERE app_id IN (%s)" % ph, ids
        )
        out = {}
        for r in cur.fetchall():
            out.setdefault(r[0], {})[r[1]] = {
                "interface": bool(r[2]),
                "audio": bool(r[3]),
                "subtitles": bool(r[4]),
            }
        return out

    def _batch_mt(self, ids):
        if not ids:
            return {}
        ph = ",".join("?" * len(ids))
        cur = self.conn.execute("SELECT app_id, key, value FROM game_custom_meta WHERE app_id IN (%s)" % ph, ids)
        out = {}
        for r in cur.fetchall():
            out.setdefault(r[0], {})[r[1]] = r[2]
        return out

    def _batch_get_hltb(self, ids):
        if not ids:
            return {}
        ph = ",".join("?" * len(ids))
        cur = self.conn.execute(
            "SELECT app_id, main_story, main_extras, completionist"
            " FROM hltb_data WHERE app_id IN (%s)"
            " AND main_story IS NOT NULL" % ph,
            ids,
        )
        return {r[0]: (float(r[1]), float(r[2] or 0), float(r[3] or 0)) for r in cur.fetchall()}

    def _batch_ach(self, ids):
        if not ids:
            return {}
        ph = ",".join("?" * len(ids))
        cur = self.conn.execute(
            "SELECT app_id, total_achievements, unlocked_achievements, completion_percentage, perfect_game"
            " FROM achievement_stats WHERE app_id IN (%s)" % ph,
            ids,
        )
        return {r[0]: (int(r[1]), int(r[2]), float(r[3]), bool(r[4])) for r in cur.fetchall()}
