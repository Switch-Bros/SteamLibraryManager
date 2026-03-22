#
# steam_library_manager/integrations/external_games/lutris_parser.py
# Parser for Lutris game manager installed games
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from steam_library_manager.integrations.external_games.base_parser import BaseExternalParser
from steam_library_manager.integrations.external_games.models import ExternalGame

__all__ = ["LutrisParser"]

logger = logging.getLogger("steamlibmgr.external_games.lutris")

# common install locations
_NATIVE = Path.home() / ".local" / "share" / "lutris" / "pga.db"
_LEGACY = Path.home() / ".config" / "lutris" / "pga.db"
_FLATPAK = Path.home() / ".var" / "app" / "net.lutris.Lutris" / "data" / "lutris" / "pga.db"

# launchers we don't want to show as games
_LAUNCHER_NAMES = frozenset(
    {
        "epic games store",
        "ea app",
        "ubisoft connect",
        "steam",
        "gog galaxy",
        "origin",
        "battle.net",
        "amazon games",
    }
)

_QUERY = """
    SELECT id, name, slug, runner, executable, directory,
           service, service_id, year, platform
    FROM games
    WHERE installed = 1
      AND runner IS NOT NULL
      AND runner != ''
"""


class LutrisParser(BaseExternalParser):
    """Parser for lutris games."""

    def platform_name(self):
        # return identifier for this platform
        return "Lutris"

    def is_available(self):
        # check if we can find the database file
        return self._find_config_file() is not None

    def get_config_paths(self):
        # list of possible db locations
        return [_NATIVE, _LEGACY, _FLATPAK]

    def read_games(self):
        # read installed games from sqlite
        db_path = self._find_config_file()
        if not db_path:
            return []

        conn = self._open_readonly_db(db_path)
        if not conn:
            return []

        games = []
        try:
            for row in conn.execute(_QUERY):
                name = row["name"] or ""
                if name.lower() in _LAUNCHER_NAMES:
                    continue  # skip store launchers

                # some games have no service but are still launchers
                if not row["service"] and name.lower() in _LAUNCHER_NAMES:
                    continue

                slug = row["slug"] or ""
                metadata = []
                if row["runner"]:
                    metadata.append(("runner", row["runner"]))
                if row["service"]:
                    metadata.append(("service", row["service"]))
                if row["year"]:
                    metadata.append(("year", str(row["year"])))

                games.append(
                    ExternalGame(
                        platform=self.platform_name(),
                        platform_app_id=str(row["id"]),
                        name=name,
                        install_path=Path(row["directory"]) if row["directory"] else None,
                        executable=row["executable"],
                        launch_command="lutris:rungame/%s" % slug if slug else "",
                        platform_metadata=tuple(metadata),
                    )
                )
        except sqlite3.Error as e:
            logger.warning("Failed to query Lutris database: %s", e)
        finally:
            conn.close()

        logger.info("Found %d games in Lutris", len(games))
        return games
