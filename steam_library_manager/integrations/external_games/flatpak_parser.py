#
# steam_library_manager/integrations/external_games/flatpak_parser.py
# Parser for Flatpak-installed games detected via desktop files
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

import logging
import shutil
import subprocess

from steam_library_manager.integrations.external_games.base_parser import BaseExternalParser
from steam_library_manager.integrations.external_games.models import ExternalGame

__all__ = ["FlatpakParser"]

logger = logging.getLogger("steamlibmgr.external_games.flatpak")

# Known non-game application ID prefixes to filter out
_NON_GAME_PREFIXES = (
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
    """Detects Flatpak-installed games by querying the flatpak CLI
    and filtering out known non-game app IDs.
    """

    def platform_name(self):
        return "Flatpak"

    def is_available(self):
        return shutil.which("flatpak") is not None

    def read_games(self):
        if not self.is_available():
            return []

        try:
            result = subprocess.run(
                ["flatpak", "list", "--app", "--columns=application,name,version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            logger.warning("Failed to run flatpak list: %s", exc)
            return []

        if result.returncode != 0:
            return []

        games = []
        for line in result.stdout.strip().splitlines():
            parts = line.split("\t")
            if len(parts) < 2:
                continue

            app_id = parts[0].strip()
            name = parts[1].strip()
            ver = parts[2].strip() if len(parts) > 2 else ""

            if _check_non_game(app_id):
                continue

            meta = []
            if ver:
                meta.append(("version", ver))

            games.append(
                ExternalGame(
                    platform=self.platform_name(),
                    platform_app_id=app_id,
                    name=name,
                    launch_command="flatpak run %s" % app_id,
                    platform_metadata=tuple(meta),
                )
            )

        logger.info("Found %d potential game Flatpaks", len(games))
        return games


def _check_non_game(app_id):
    # Check if a Flatpak app ID belongs to a known non-game
    return any(app_id.startswith(prefix) for prefix in _NON_GAME_PREFIXES)
