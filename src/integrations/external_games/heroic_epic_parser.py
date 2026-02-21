"""Parser for Epic Games installed via Heroic Games Launcher.

Reads Legendary's installed.json to detect Epic Games Store titles.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from src.integrations.external_games.base_parser import BaseExternalParser
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


class HeroicEpicParser(BaseExternalParser):
    """Parser for Epic Games installed through Heroic/Legendary."""

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
        config_path = self._find_config_file()
        if not config_path:
            return []

        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Failed to read Heroic Epic config: %s", e)
            return []

        if not isinstance(data, dict):
            return []

        is_flatpak = str(config_path).startswith(str(Path.home() / ".var"))
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

            launch_cmd = self._build_launch_command(app_name, is_flatpak)

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

    @staticmethod
    def _build_launch_command(app_name: str, is_flatpak: bool) -> str:
        """Build the Heroic launch URI for an Epic game.

        Args:
            app_name: Legendary app name / ID.
            is_flatpak: Whether Heroic is installed as Flatpak.

        Returns:
            Launch command string.
        """
        uri = f"heroic://launch/{app_name}?runner=legendary"
        if is_flatpak:
            return f'flatpak run com.heroicgameslauncher.hgl --no-gui --no-sandbox "{uri}"'
        return uri
