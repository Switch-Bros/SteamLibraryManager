#
# steam_library_manager/integrations/external_games/heroic_sideload_parser.py
# Heroic Launcher parser for sideloaded (manually added) apps
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
from pathlib import Path

from steam_library_manager.integrations.external_games.base_heroic_parser import BaseHeroicParser
from steam_library_manager.integrations.external_games.models import ExternalGame

__all__ = ["HeroicSideloadParser"]

logger = logging.getLogger("steamlibmgr.external_games.heroic_sideload")

# config file locations - sideload library lives under sideload_apps/library.json
_NATIVE = Path.home() / ".config" / "heroic" / "sideload_apps" / "library.json"
_FLATPAK = (
    Path.home()
    / ".var"
    / "app"
    / "com.heroicgameslauncher.hgl"
    / "config"
    / "heroic"
    / "sideload_apps"
    / "library.json"
)


class HeroicSideloadParser(BaseHeroicParser):
    """Parser for manually added (sideloaded) apps in Heroic Games Launcher.

    Sideload apps are .exe files the user added to Heroic by hand
    (Heroic UI: 'Add Game'). They live in a separate library.json
    with a different schema than GOG/Epic/Amazon - top-level 'games'
    array, runner field = 'sideload'.
    """

    _RUNNER = "sideload"

    def platform_name(self):
        return "Heroic (Sideload)"

    def is_available(self):
        return self._find_config_file() is not None

    def get_config_paths(self):
        return [_NATIVE, _FLATPAK]

    def read_games(self):
        data, cfg_path = self._load_heroic_config_with_path()

        # Sideload schema uses top-level 'games' array, unlike GOG's 'installed'.
        entries = data.get("games", []) if isinstance(data, dict) else []
        if not isinstance(entries, list):
            return []

        is_flatpak = self._is_flatpak(cfg_path) if cfg_path else False
        games = []

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            if not entry.get("is_installed", False):
                continue

            install = entry.get("install", {})
            if not isinstance(install, dict):
                continue
            executable = install.get("executable", "")
            if not executable:
                continue  # no executable, skip

            app_name = entry.get("app_name", "")
            if not app_name:
                continue  # no id, skip

            title = entry.get("title", "") or app_name  # title fallback
            folder_name = entry.get("folder_name", "")
            art_cover = entry.get("art_cover", "") or None

            meta = []
            platform_val = install.get("platform")
            if platform_val:
                meta.append(("platform", str(platform_val)))
            if entry.get("canRunOffline"):
                meta.append(("can_run_offline", "true"))

            games.append(
                ExternalGame(
                    platform=self.platform_name(),
                    platform_app_id=app_name,
                    name=title,
                    install_path=Path(folder_name) if folder_name else None,
                    executable=executable,
                    launch_command=self._build_heroic_launch_command(app_name, is_flatpak),
                    cover_url_hint=art_cover if art_cover else None,
                    platform_metadata=tuple(meta),
                )
            )

        logger.info("Found %d sideload games via Heroic", len(games))
        return games
