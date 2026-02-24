"""Base class for Heroic Games Launcher parsers (Epic/GOG/Amazon).

Extracts shared logic: Flatpak detection, launch command building,
and JSON config loading. Subclasses set _RUNNER and implement
platform-specific game extraction.

Inheritance: BaseExternalParser -> BaseHeroicParser -> HeroicXxxParser
(2 levels, approved per Chris review).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from src.integrations.external_games.base_parser import BaseExternalParser

__all__ = ["BaseHeroicParser"]

logger = logging.getLogger("steamlibmgr.external_games.heroic")


class BaseHeroicParser(BaseExternalParser):
    """Shared logic for Heroic launcher parsers.

    Subclasses must set _RUNNER and implement platform_name(),
    get_config_paths(), and read_games().
    """

    _RUNNER: str  # Subclass must set: "legendary", "gog", or "nile"

    @staticmethod
    def _is_flatpak(config_path: Path) -> bool:
        """Checks if Heroic is installed via Flatpak.

        Args:
            config_path: Path to the Heroic config file.

        Returns:
            True if running as Flatpak.
        """
        return "/.var/app/" in str(config_path)

    def _build_heroic_launch_command(self, app_id: str, is_flatpak: bool) -> str:
        """Builds the launch command for a Heroic game.

        Args:
            app_id: The platform-specific app identifier.
            is_flatpak: Whether Heroic is a Flatpak install.

        Returns:
            Launch command string (URI or Flatpak wrapper).
        """
        uri = f"heroic://launch/{app_id}?runner={self._RUNNER}"
        if is_flatpak:
            return f'flatpak run com.heroicgameslauncher.hgl --no-gui --no-sandbox "{uri}"'
        return uri

    def _load_heroic_config(self) -> dict[str, Any] | list[Any] | None:
        """Loads and parses the Heroic JSON config file.

        Returns:
            Parsed JSON data, or None on failure.
        """
        config_path = self._find_config_file()
        if not config_path:
            return None
        try:
            return json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Failed to read Heroic %s config: %s", self._RUNNER, e)
            return None

    def _load_heroic_config_with_path(self) -> tuple[dict[str, Any] | list[Any] | None, Path | None]:
        """Loads config and returns both data and the config path.

        Returns:
            Tuple of (parsed data or None, config path or None).
        """
        config_path = self._find_config_file()
        if not config_path:
            return None, None
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            return data, config_path
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Failed to read Heroic %s config: %s", self._RUNNER, e)
            return None, None
