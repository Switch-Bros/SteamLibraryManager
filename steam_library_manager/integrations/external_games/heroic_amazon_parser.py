#
# steam_library_manager/integrations/external_games/heroic_amazon_parser.py
# Parser for Amazon Games installed via Heroic Games Launcher
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
from pathlib import Path

from steam_library_manager.integrations.external_games.base_heroic_parser import BaseHeroicParser
from steam_library_manager.integrations.external_games.models import ExternalGame

__all__ = ["HeroicAmazonParser"]

logger = logging.getLogger("steamlibmgr.external_games.heroic_amazon")

_NATIVE = Path.home() / ".config" / "heroic" / "nile_config" / "nile" / "installed.json"
_FLATPAK = (
    Path.home()
    / ".var"
    / "app"
    / "com.heroicgameslauncher.hgl"
    / "config"
    / "heroic"
    / "nile_config"
    / "nile"
    / "installed.json"
)


class HeroicAmazonParser(BaseHeroicParser):
    """Parser for Amazon Games installed through Heroic/Nile."""

    _RUNNER = "nile"

    def platform_name(self) -> str:
        return "Heroic (Amazon)"

    def is_available(self) -> bool:
        return self._find_config_file() is not None

    def get_config_paths(self) -> list[Path]:
        return [_NATIVE, _FLATPAK]

    def read_games(self) -> list[ExternalGame]:
        """Read installed Amazon games from Heroic's Nile config."""
        data, config_path = self._load_heroic_config_with_path()

        # Amazon format is a plain array (not wrapped in dict)
        if not isinstance(data, list):
            return []

        is_flatpak = self._is_flatpak(config_path) if config_path else False
        games: list[ExternalGame] = []

        for entry in data:
            if not isinstance(entry, dict):
                continue

            app_id = entry.get("id", "")
            install_path = entry.get("path", "")
            install_size = entry.get("size", 0)
            if isinstance(install_size, str):
                install_size = 0

            # Name from path (last component) since there's no title field
            name = Path(install_path).name if install_path else app_id

            launch_cmd = self._build_heroic_launch_command(app_id, is_flatpak)

            games.append(
                ExternalGame(
                    platform=self.platform_name(),
                    platform_app_id=app_id,
                    name=name,
                    install_path=Path(install_path) if install_path else None,
                    launch_command=launch_cmd,
                    install_size=install_size,
                )
            )

        logger.info("Found %d Amazon games via Heroic", len(games))
        return games
