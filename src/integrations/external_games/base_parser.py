"""Abstract base class for external game platform parsers.

All platform parsers inherit from BaseExternalParser and implement
platform_name(), is_available(), and read_games().
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path

from src.integrations.external_games.models import ExternalGame

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
