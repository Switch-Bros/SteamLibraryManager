"""Parser for games installed in Lutris.

Reads the Lutris pga.db SQLite database (read-only) to detect
installed games, filtering out known launcher applications.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from src.integrations.external_games.base_parser import BaseExternalParser
from src.integrations.external_games.models import ExternalGame

__all__ = ["LutrisParser"]

logger = logging.getLogger("steamlibmgr.external_games.lutris")

_NATIVE = Path.home() / ".local" / "share" / "lutris" / "pga.db"
_LEGACY = Path.home() / ".config" / "lutris" / "pga.db"
_FLATPAK = Path.home() / ".var" / "app" / "net.lutris.Lutris" / "data" / "lutris" / "pga.db"

# Known launcher names to filter out (lowercase)
_LAUNCHER_NAMES: frozenset[str] = frozenset(
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
    """Parser for games installed through Lutris."""

    def platform_name(self) -> str:
        """Return platform name.

        Returns:
            Platform identifier.
        """
        return "Lutris"

    def is_available(self) -> bool:
        """Check if Lutris database exists.

        Returns:
            True if pga.db is found.
        """
        return self._find_config_file() is not None

    def get_config_paths(self) -> list[Path]:
        """Return native, legacy, and Flatpak database paths.

        Returns:
            List of possible pga.db paths.
        """
        return [_NATIVE, _LEGACY, _FLATPAK]

    def read_games(self) -> list[ExternalGame]:
        """Read installed games from Lutris database.

        Opens the database read-only and filters out known launchers.

        Returns:
            List of detected Lutris games.
        """
        db_path = self._find_config_file()
        if not db_path:
            return []

        conn = self._open_readonly_db(db_path)
        if not conn:
            return []

        games: list[ExternalGame] = []
        try:
            for row in conn.execute(_QUERY):
                name = row["name"] or ""
                if name.lower() in _LAUNCHER_NAMES:
                    continue
                if not row["service"] and name.lower() in _LAUNCHER_NAMES:
                    continue

                slug = row["slug"] or ""
                metadata: list[tuple[str, str]] = []
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
                        launch_command=f"lutris:rungame/{slug}" if slug else "",
                        platform_metadata=tuple(metadata),
                    )
                )
        except sqlite3.Error as e:
            logger.warning("Failed to query Lutris database: %s", e)
        finally:
            conn.close()

        logger.info("Found %d games in Lutris", len(games))
        return games
