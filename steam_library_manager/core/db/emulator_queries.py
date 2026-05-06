#
# steam_library_manager/core/db/emulator_queries.py
# Emulator settings + emulator_games CRUD (Schema v12)
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import datetime
import json
import logging
from typing import Any

logger = logging.getLogger("steamlibmgr.database")

__all__ = ["EmulatorQueriesMixin"]


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class EmulatorQueriesMixin:
    """Emulator detection queries.

    Reads/writes emulator_settings (one row per known emulator) and
    emulator_games (cached ROM library per emulator). Needs `conn` from
    ConnectionBase via multiple inheritance.
    """

    # ---------- emulator_settings ----------

    def upsert_emulator_settings(
        self,
        emulator_name: str,
        enabled: bool = True,
        default_for_system: str = "",
        custom_game_dirs: list[str] | None = None,
        appimage_search_dirs: list[str] | None = None,
        executable_override: str = "",
    ) -> None:
        # full upsert; callers that want partial updates should use the helpers below
        self.conn.execute(
            "INSERT INTO emulator_settings"
            " (emulator_name, enabled, default_for_system, custom_game_dirs,"
            "  appimage_search_dirs, executable_override, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(emulator_name) DO UPDATE SET"
            "   enabled = excluded.enabled,"
            "   default_for_system = excluded.default_for_system,"
            "   custom_game_dirs = excluded.custom_game_dirs,"
            "   appimage_search_dirs = excluded.appimage_search_dirs,"
            "   executable_override = excluded.executable_override,"
            "   updated_at = excluded.updated_at",
            (
                emulator_name,
                1 if enabled else 0,
                default_for_system,
                json.dumps(custom_game_dirs or []),
                json.dumps(appimage_search_dirs or []),
                executable_override,
                _now_iso(),
            ),
        )
        self.conn.commit()

    def get_emulator_settings(self, emulator_name: str) -> dict[str, Any] | None:
        cur = self.conn.execute(
            "SELECT emulator_name, enabled, default_for_system, custom_game_dirs,"
            " appimage_search_dirs, executable_override, updated_at"
            " FROM emulator_settings WHERE emulator_name = ?",
            (emulator_name,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return self._row_to_settings(row)

    def get_all_emulator_settings(self) -> list[dict[str, Any]]:
        cur = self.conn.execute(
            "SELECT emulator_name, enabled, default_for_system, custom_game_dirs,"
            " appimage_search_dirs, executable_override, updated_at"
            " FROM emulator_settings ORDER BY emulator_name"
        )
        return [self._row_to_settings(r) for r in cur.fetchall()]

    def set_emulator_enabled(self, emulator_name: str, enabled: bool) -> None:
        self.conn.execute(
            "INSERT INTO emulator_settings (emulator_name, enabled, updated_at) VALUES (?, ?, ?)"
            " ON CONFLICT(emulator_name) DO UPDATE SET enabled = excluded.enabled, updated_at = excluded.updated_at",
            (emulator_name, 1 if enabled else 0, _now_iso()),
        )
        self.conn.commit()

    def set_default_emulator_for_system(self, system: str, emulator_name: str) -> None:
        # clear any existing default for this system, then set the new one
        self.conn.execute(
            "UPDATE emulator_settings SET default_for_system = '', updated_at = ?" " WHERE default_for_system = ?",
            (_now_iso(), system),
        )
        self.conn.execute(
            "INSERT INTO emulator_settings (emulator_name, default_for_system, updated_at) VALUES (?, ?, ?)"
            " ON CONFLICT(emulator_name) DO UPDATE SET"
            "   default_for_system = excluded.default_for_system, updated_at = excluded.updated_at",
            (emulator_name, system, _now_iso()),
        )
        self.conn.commit()

    def get_default_emulator_for_system(self, system: str) -> str | None:
        cur = self.conn.execute(
            "SELECT emulator_name FROM emulator_settings WHERE default_for_system = ? AND enabled = 1 LIMIT 1",
            (system,),
        )
        row = cur.fetchone()
        return row[0] if row else None

    def add_custom_game_dir(self, emulator_name: str, path: str) -> None:
        existing = self.get_emulator_settings(emulator_name)
        dirs = list(existing["custom_game_dirs"]) if existing else []
        if path in dirs:
            return
        dirs.append(path)
        self.conn.execute(
            "INSERT INTO emulator_settings (emulator_name, custom_game_dirs, updated_at) VALUES (?, ?, ?)"
            " ON CONFLICT(emulator_name) DO UPDATE SET"
            "   custom_game_dirs = excluded.custom_game_dirs, updated_at = excluded.updated_at",
            (emulator_name, json.dumps(dirs), _now_iso()),
        )
        self.conn.commit()

    def remove_custom_game_dir(self, emulator_name: str, path: str) -> None:
        existing = self.get_emulator_settings(emulator_name)
        if not existing:
            return
        dirs = [d for d in existing["custom_game_dirs"] if d != path]
        self.conn.execute(
            "UPDATE emulator_settings SET custom_game_dirs = ?, updated_at = ? WHERE emulator_name = ?",
            (json.dumps(dirs), _now_iso(), emulator_name),
        )
        self.conn.commit()

    def set_executable_override(self, emulator_name: str, executable_path: str) -> None:
        self.conn.execute(
            "INSERT INTO emulator_settings (emulator_name, executable_override, updated_at) VALUES (?, ?, ?)"
            " ON CONFLICT(emulator_name) DO UPDATE SET"
            "   executable_override = excluded.executable_override, updated_at = excluded.updated_at",
            (emulator_name, executable_path, _now_iso()),
        )
        self.conn.commit()

    # ---------- emulator_games ----------

    def upsert_emulator_game(
        self,
        emulator_name: str,
        system: str,
        rom_path: str,
        game_name: str,
    ) -> None:
        # log emulator change for the same ROM (helps debug auto-detect surprises)
        cur = self.conn.execute("SELECT emulator_name FROM emulator_games WHERE rom_path = ?", (rom_path,))
        row = cur.fetchone()
        if row and row[0] != emulator_name:
            logger.info("rom %s: emulator changed %s -> %s" % (rom_path, row[0], emulator_name))

        self.conn.execute(
            "INSERT INTO emulator_games (emulator_name, system, rom_path, game_name, last_seen)"
            " VALUES (?, ?, ?, ?, ?)"
            " ON CONFLICT(rom_path) DO UPDATE SET"
            "   emulator_name = excluded.emulator_name,"
            "   system = excluded.system,"
            "   game_name = excluded.game_name,"
            "   last_seen = excluded.last_seen",
            (emulator_name, system, rom_path, game_name, _now_iso()),
        )
        self.conn.commit()

    def bulk_upsert_emulator_games(self, games: list[tuple[str, str, str, str]]) -> None:
        # games: [(emulator_name, system, rom_path, game_name), ...]
        if not games:
            return
        now = _now_iso()
        params = [(emu, sys_id, rom, name, now) for emu, sys_id, rom, name in games]
        self.conn.executemany(
            "INSERT INTO emulator_games (emulator_name, system, rom_path, game_name, last_seen)"
            " VALUES (?, ?, ?, ?, ?)"
            " ON CONFLICT(rom_path) DO UPDATE SET"
            "   emulator_name = excluded.emulator_name,"
            "   system = excluded.system,"
            "   game_name = excluded.game_name,"
            "   last_seen = excluded.last_seen",
            params,
        )
        self.conn.commit()

    def get_emulator_games(
        self,
        system: str | None = None,
        emulator_name: str | None = None,
    ) -> list[dict[str, Any]]:
        sql = "SELECT id, emulator_name, system, rom_path, game_name, last_seen, added_to_steam" " FROM emulator_games"
        params: list[Any] = []
        clauses: list[str] = []
        if system:
            clauses.append("system = ?")
            params.append(system)
        if emulator_name:
            clauses.append("emulator_name = ?")
            params.append(emulator_name)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY game_name"
        cur = self.conn.execute(sql, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    def mark_emulator_game_added_to_steam(self, rom_path: str) -> None:
        self.conn.execute(
            "UPDATE emulator_games SET added_to_steam = 1 WHERE rom_path = ?",
            (rom_path,),
        )
        self.conn.commit()

    def clear_emulator_games(self, emulator_name: str | None = None) -> None:
        if emulator_name:
            self.conn.execute("DELETE FROM emulator_games WHERE emulator_name = ?", (emulator_name,))
        else:
            self.conn.execute("DELETE FROM emulator_games")
        self.conn.commit()

    # ---------- helpers ----------

    @staticmethod
    def _row_to_settings(row: tuple) -> dict[str, Any]:
        return {
            "emulator_name": row[0],
            "enabled": bool(row[1]),
            "default_for_system": row[2] or "",
            "custom_game_dirs": _safe_json_list(row[3]),
            "appimage_search_dirs": _safe_json_list(row[4]),
            "executable_override": row[5] or "",
            "updated_at": row[6] or "",
        }


def _safe_json_list(s: str) -> list[str]:
    if not s:
        return []
    try:
        v = json.loads(s)
        return [str(x) for x in v] if isinstance(v, list) else []
    except (ValueError, TypeError):
        return []
