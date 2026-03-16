#
# steam_library_manager/integrations/external_games/base_heroic_parser.py
# Base class for Heroic Games Launcher parsers (Epic/GOG/Amazon)
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from steam_library_manager.integrations.external_games.base_parser import BaseExternalParser

__all__ = ["BaseHeroicParser"]

logger = logging.getLogger("steamlibmgr.external_games.heroic")


class BaseHeroicParser(BaseExternalParser):
    """Shared logic for Heroic launcher parsers."""

    _RUNNER: str  # Subclass must set: "legendary", "gog", or "nile"

    @staticmethod
    def _is_flatpak(config_path: Path) -> bool:
        return "/.var/app/" in str(config_path)

    def _build_heroic_launch_command(self, app_id: str, is_flatpak: bool) -> str:
        """Build the launch command for a Heroic game."""
        uri = f"heroic://launch/{app_id}?runner={self._RUNNER}"
        if is_flatpak:
            return f'flatpak run com.heroicgameslauncher.hgl --no-gui --no-sandbox "{uri}"'
        return uri

    def _load_heroic_config(self) -> dict[str, Any] | list[Any] | None:
        """Load and parse the Heroic JSON config file."""
        config_path = self._find_config_file()
        if not config_path:
            return None
        try:
            return json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Failed to read Heroic %s config: %s", self._RUNNER, e)
            return None

    def _load_heroic_config_with_path(self) -> tuple[dict[str, Any] | list[Any] | None, Path | None]:
        """Load config and return both data and the config path."""
        config_path = self._find_config_file()
        if not config_path:
            return None, None
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            return data, config_path
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Failed to read Heroic %s config: %s", self._RUNNER, e)
            return None, None
