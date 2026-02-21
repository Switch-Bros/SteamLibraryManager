"""Parser for itch.io games installed via butler.

Reads the butler.db SQLite database to detect installed games
by joining caves and games tables.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path

from src.integrations.external_games.base_parser import BaseExternalParser
from src.integrations.external_games.models import ExternalGame

__all__ = ["ItchParser"]

logger = logging.getLogger("steamlibmgr.external_games.itch")

# Allowed game classifications (skip comics, books, soundtracks, etc.)
_ALLOWED_CLASSIFICATIONS: frozenset[str] = frozenset({"game", "tool"})

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


def _get_db_path() -> Path:
    """Return the butler.db path using XDG conventions.

    Returns:
        Path to butler.db.
    """
    xdg = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    return Path(xdg) / "itch" / "db" / "butler.db"


class ItchParser(BaseExternalParser):
    """Parser for itch.io games installed through butler."""

    def platform_name(self) -> str:
        """Return platform name.

        Returns:
            Platform identifier.
        """
        return "itch.io"

    def is_available(self) -> bool:
        """Check if itch.io butler database exists.

        Returns:
            True if butler.db is found.
        """
        return _get_db_path().exists()

    def get_config_paths(self) -> list[Path]:
        """Return butler.db path.

        Returns:
            List containing the single database path.
        """
        return [_get_db_path()]

    def read_games(self) -> list[ExternalGame]:
        """Read installed games from itch.io butler database.

        Opens the database read-only and filters by classification.

        Returns:
            List of detected itch.io games.
        """
        db_path = _get_db_path()
        if not db_path.exists():
            return []

        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
        except sqlite3.Error as e:
            logger.warning("Failed to open itch.io database: %s", e)
            return []

        games: list[ExternalGame] = []
        try:
            for row in conn.execute(_QUERY):
                classification = (row["classification"] or "").lower()
                if classification and classification not in _ALLOWED_CLASSIFICATIONS:
                    continue

                title = row["title"] or ""
                cave_id = row["cave_id"] or ""
                install_path = self._resolve_install_path(row)

                metadata: list[tuple[str, str]] = []
                if row["url"]:
                    metadata.append(("url", row["url"]))
                if row["seconds_run"]:
                    metadata.append(("seconds_run", str(row["seconds_run"])))

                games.append(
                    ExternalGame(
                        platform=self.platform_name(),
                        platform_app_id=str(row["game_id"]),
                        name=title,
                        install_path=Path(install_path) if install_path else None,
                        launch_command=f"itch://caves/{cave_id}/launch",
                        install_size=row["installed_size"] or 0,
                        platform_metadata=tuple(metadata),
                    )
                )
        except sqlite3.Error as e:
            logger.warning("Failed to query itch.io database: %s", e)
        finally:
            conn.close()

        logger.info("Found %d games in itch.io", len(games))
        return games

    @staticmethod
    def _resolve_install_path(row: sqlite3.Row) -> str:
        """Resolve install path from cave data.

        Uses custom_install_folder if set, otherwise combines
        location_path with install_folder_name.

        Args:
            row: Database row with cave and location data.

        Returns:
            Resolved install path string.
        """
        custom = row["custom_install_folder"]
        if custom:
            return str(custom)

        location = row["location_path"] or ""
        folder = row["install_folder_name"] or ""
        if location and folder:
            return str(Path(location) / folder)
        return ""
