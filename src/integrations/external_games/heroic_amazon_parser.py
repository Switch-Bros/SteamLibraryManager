"""Parser for Amazon Games installed via Heroic Games Launcher.

Reads Heroic's nile_config/nile/installed.json to detect Amazon titles.
Note: Amazon format is a plain JSON array (not wrapped in a dict),
and uses 'id' and 'path' instead of 'app_name' and 'install_path'.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from src.integrations.external_games.base_parser import BaseExternalParser
from src.integrations.external_games.models import ExternalGame

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


class HeroicAmazonParser(BaseExternalParser):
    """Parser for Amazon Games installed through Heroic/Nile."""

    def platform_name(self) -> str:
        """Return platform name.

        Returns:
            Platform identifier.
        """
        return "Heroic (Amazon)"

    def is_available(self) -> bool:
        """Check if Heroic Amazon/Nile config exists.

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
        """Read installed Amazon games from Heroic's Nile config.

        Returns:
            List of detected Amazon games.
        """
        config_path = self._find_config_file()
        if not config_path:
            return []

        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Failed to read Heroic Amazon config: %s", e)
            return []

        # Amazon format is a plain array (not wrapped in dict)
        if not isinstance(data, list):
            return []

        is_flatpak = str(config_path).startswith(str(Path.home() / ".var"))
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

            launch_cmd = self._build_launch_command(app_id, is_flatpak)

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

    @staticmethod
    def _build_launch_command(app_id: str, is_flatpak: bool) -> str:
        """Build the Heroic launch URI for an Amazon game.

        Args:
            app_id: Amazon/Nile app ID.
            is_flatpak: Whether Heroic is installed as Flatpak.

        Returns:
            Launch command string.
        """
        uri = f"heroic://launch/{app_id}?runner=nile"
        if is_flatpak:
            return f'flatpak run com.heroicgameslauncher.hgl --no-gui --no-sandbox "{uri}"'
        return uri
