#
# steam_library_manager/integrations/external_games/itch_parser.py
# Parser for itch.io desktop client installed games
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

import logging
import os
import sqlite3
from pathlib import Path

from steam_library_manager.integrations.external_games.base_parser import BaseExternalParser
from steam_library_manager.integrations.external_games.models import ExternalGame

__all__ = ["ItchParser"]

logger = logging.getLogger("steamlibmgr.external_games.itch")

# Allowed game classifications (skip comics, books, soundtracks, etc.)
_ALLOWED_CLASSIFICATIONS = frozenset({"game", "tool"})

_QUERY = """
    SELECT
        c.id            AS cave_id,
        g.id            AS game_id,
        g.title,
        g.short_text,
        g.cover_url,
        g.classification,
        g.url,
        c.installed_size,
        c.seconds_run,
        c.installed_at,
        c.install_folder_name,
        c.custom_install_folder,
        il.path         AS location_path
    FROM caves c
    JOIN games g ON c.game_id = g.id
    LEFT JOIN install_locations il ON c.install_location_id = il.id
"""


def _get_db_path():
    # Return the butler.db path using XDG conventions
    xdg = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    return Path(xdg) / "itch" / "db" / "butler.db"


class ItchParser(BaseExternalParser):
    """Reads installed itch.io games from butler's SQLite database
    and filters by classification (game/tool only).
    """

    def platform_name(self):
        return "itch.io"

    def is_available(self):
        return _get_db_path().exists()

    def get_config_paths(self):
        return [_get_db_path()]

    def read_games(self):
        db_path = _get_db_path()
        if not db_path.exists():
            return []

        conn = self._open_readonly_db(db_path)
        if not conn:
            return []

        games = []
        try:
            for row in conn.execute(_QUERY):
                cls = (row["classification"] or "").lower()
                if cls and cls not in _ALLOWED_CLASSIFICATIONS:
                    continue

                title = row["title"] or ""
                cave_id = row["cave_id"] or ""
                inst_path = _resolve_path(row)

                meta = []
                if row["url"]:
                    meta.append(("url", row["url"]))
                if row["seconds_run"]:
                    meta.append(("seconds_run", str(row["seconds_run"])))

                games.append(
                    ExternalGame(
                        platform=self.platform_name(),
                        platform_app_id=str(row["game_id"]),
                        name=title,
                        install_path=Path(inst_path) if inst_path else None,
                        launch_command="itch://caves/%s/launch" % cave_id,
                        install_size=row["installed_size"] or 0,
                        platform_metadata=tuple(meta),
                    )
                )
        except sqlite3.Error as exc:
            logger.warning("Failed to query itch.io database: %s", exc)
        finally:
            conn.close()

        logger.info("Found %d games in itch.io", len(games))
        return games


def _resolve_path(row):
    # Resolve install path from cave data
    custom = row["custom_install_folder"]
    if custom:
        return str(custom)

    location = row["location_path"] or ""
    folder = row["install_folder_name"] or ""
    if location and folder:
        return str(Path(location) / folder)
    return ""
