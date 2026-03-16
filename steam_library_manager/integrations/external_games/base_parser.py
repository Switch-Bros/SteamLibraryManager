#
# steam_library_manager/integrations/external_games/base_parser.py
# Abstract base class for all external game library parsers
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path

from steam_library_manager.integrations.external_games.models import ExternalGame

__all__ = ["BaseExternalParser"]

logger = logging.getLogger("steamlibmgr.external_games")


class BaseExternalParser(ABC):
    """Abstract base class for external game platform parsers.

    Provides common path-detection logic and error handling.
    Subclasses implement platform-specific game reading.
    """

    @abstractmethod
    def platform_name(self) -> str:
        """Return human-readable platform name.

        Returns:
            Platform identifier string.
        """

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this platform is installed/accessible.

        Returns:
            True if the platform's data files or commands are available.
        """

    @abstractmethod
    def read_games(self) -> list[ExternalGame]:
        """Read all installed games from this platform.

        Returns:
            List of detected games, empty if none found or unavailable.
        """

    def get_config_paths(self) -> list[Path]:
        """Return all possible config paths (native + Flatpak).

        Override in subclasses to provide platform-specific paths.
        Order by priority (native first, then Flatpak).

        Returns:
            List of paths to check.
        """
        return []

    def _find_config_file(self) -> Path | None:
        """Find the first existing config file from get_config_paths().

        Returns:
            Path to the first existing config file, or None.
        """
        for path in self.get_config_paths():
            if path.exists():
                logger.debug("Found %s config: %s", self.platform_name(), path)
                return path
        return None

    def _open_readonly_db(self, db_path: Path) -> sqlite3.Connection | None:
        """Opens a SQLite database in read-only mode with Row factory.

        Args:
            db_path: Path to the SQLite database file.

        Returns:
            Connection with Row factory set, or None on error.
        """
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            logger.warning("Failed to open %s database: %s", self.platform_name(), e)
            return None
