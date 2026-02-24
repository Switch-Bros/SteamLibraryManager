"""Parser for Epic Games installed via Heroic Games Launcher.

Reads Legendary's installed.json to detect Epic Games Store titles.
"""

from __future__ import annotations

import logging
from pathlib import Path

from src.integrations.external_games.base_heroic_parser import BaseHeroicParser
from src.integrations.external_games.models import ExternalGame

__all__ = ["HeroicEpicParser"]

logger = logging.getLogger("steamlibmgr.external_games.heroic_epic")

_NATIVE = Path.home() / ".config" / "heroic" / "legendaryConfig" / "legendary" / "installed.json"
_FLATPAK = (
    Path.home()
    / ".var"
    / "app"
    / "com.heroicgameslauncher.hgl"
    / "config"
    / "heroic"
    / "legendaryConfig"
    / "legendary"
    / "installed.json"
)


class HeroicEpicParser(BaseHeroicParser):
    """Parser for Epic Games installed through Heroic/Legendary."""

    _RUNNER = "legendary"

    def platform_name(self) -> str:
        """Return platform name.

        Returns:
            Platform identifier.
        """
        return "Heroic (Epic)"

    def is_available(self) -> bool:
        """Check if Heroic Epic config exists.

        Returns:
            True if installed.json is found.
        """
        return self._find_config_file() is not None

    def get_config_paths(self) -> list[Path]:
        """Return native and Flatpak config paths.

        Returns:
            List of possible installed.json paths.
        """
        return [_NATIVE, _FLATPAK]

    def read_games(self) -> list[ExternalGame]:
        """Read installed Epic games from Heroic's Legendary config.

        Returns:
            List of detected Epic games.
        """
        data, config_path = self._load_heroic_config_with_path()
        if not isinstance(data, dict):
            return []

        is_flatpak = self._is_flatpak(config_path) if config_path else False
        games: list[ExternalGame] = []

        for app_name, entry in data.items():
            if not isinstance(entry, dict):
                continue
            if entry.get("is_dlc", False):
                continue

            title = entry.get("title", app_name)
            install_path = entry.get("install_path")
            install_size = entry.get("install_size", 0)
            if isinstance(install_size, str):
                install_size = 0

            launch_cmd = self._build_heroic_launch_command(app_name, is_flatpak)

            games.append(
                ExternalGame(
                    platform=self.platform_name(),
                    platform_app_id=app_name,
                    name=title,
                    install_path=Path(install_path) if install_path else None,
                    executable=entry.get("executable"),
                    launch_command=launch_cmd,
                    install_size=install_size,
                    platform_metadata=(("platform", entry.get("platform", "")),),
                )
            )

        logger.info("Found %d Epic games via Heroic", len(games))
        return games
