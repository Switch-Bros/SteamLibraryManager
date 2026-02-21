"""Parser for Flatpak-installed game applications.

Uses the flatpak CLI to list installed applications and filters
out known non-game prefixes.
"""

from __future__ import annotations

import logging
import shutil
import subprocess

from src.integrations.external_games.base_parser import BaseExternalParser
from src.integrations.external_games.models import ExternalGame

__all__ = ["FlatpakParser"]

logger = logging.getLogger("steamlibmgr.external_games.flatpak")

# Known non-game application ID prefixes to filter out
_NON_GAME_PREFIXES: tuple[str, ...] = (
    "com.usebottles",
    "com.heroicgameslauncher",
    "net.lutris",
    "com.valvesoftware",
    "org.mozilla",
    "com.google.Chrome",
    "org.libreoffice",
    "org.gnome",
    "org.kde",
    "org.freedesktop",
    "com.github",
    "io.github",
    "org.signal",
    "com.spotify",
    "com.discordapp",
    "com.slack",
    "org.telegram",
    "com.visualstudio",
    "org.videolan",
    "org.audacityteam",
    "org.gimp",
    "org.inkscape",
    "org.blender",
)


class FlatpakParser(BaseExternalParser):
    """Parser for Flatpak-installed game applications."""

    def platform_name(self) -> str:
        """Return platform name.

        Returns:
            Platform identifier.
        """
        return "Flatpak"

    def is_available(self) -> bool:
        """Check if the flatpak command is available.

        Returns:
            True if flatpak CLI is found.
        """
        return shutil.which("flatpak") is not None

    def read_games(self) -> list[ExternalGame]:
        """Read installed Flatpak applications, filtering non-games.

        Returns:
            List of Flatpak apps that might be games.
        """
        if not self.is_available():
            return []

        try:
            result = subprocess.run(
                ["flatpak", "list", "--app", "--columns=application,name,version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (subprocess.TimeoutExpired, OSError) as e:
            logger.warning("Failed to run flatpak list: %s", e)
            return []

        if result.returncode != 0:
            return []

        games: list[ExternalGame] = []
        for line in result.stdout.strip().splitlines():
            parts = line.split("\t")
            if len(parts) < 2:
                continue

            app_id = parts[0].strip()
            name = parts[1].strip()
            version = parts[2].strip() if len(parts) > 2 else ""

            if self._is_non_game(app_id):
                continue

            metadata: list[tuple[str, str]] = []
            if version:
                metadata.append(("version", version))

            games.append(
                ExternalGame(
                    platform=self.platform_name(),
                    platform_app_id=app_id,
                    name=name,
                    launch_command=f"flatpak run {app_id}",
                    platform_metadata=tuple(metadata),
                )
            )

        logger.info("Found %d potential game Flatpaks", len(games))
        return games

    @staticmethod
    def _is_non_game(app_id: str) -> bool:
        """Check if a Flatpak app ID belongs to a known non-game.

        Args:
            app_id: Flatpak application identifier.

        Returns:
            True if the app is a known non-game.
        """
        return any(app_id.startswith(prefix) for prefix in _NON_GAME_PREFIXES)
