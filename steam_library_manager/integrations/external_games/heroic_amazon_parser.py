#
# steam_library_manager/integrations/external_games/heroic_amazon_parser.py
# Heroic Launcher parser for Amazon Games Prime
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
    """Parser for Amazon Games via Heroic/Nile."""

    _RUNNER = "nile"

    def platform_name(self):
        return "Heroic (Amazon)"

    def is_available(self):
        return self._find_config_file() is not None

    def get_config_paths(self):
        return [_NATIVE, _FLATPAK]

    def read_games(self):
        # read installed Amazon games from nile config
        data, cfg_path = self._load_heroic_config_with_path()

        # amazon format is a plain array
        if not isinstance(data, list):
            return []

        fp = self._is_flatpak(cfg_path) if cfg_path else False
        games = []

        for entry in data:
            if not isinstance(entry, dict):
                continue

            aid = entry.get("id", "")
            ipath = entry.get("path", "")
            isize = entry.get("size", 0)
            if isinstance(isize, str):
                isize = 0

            # name from path since theres no title field
            nm = Path(ipath).name if ipath else aid

            cmd = self._build_heroic_launch_command(aid, fp)

            games.append(
                ExternalGame(
                    platform=self.platform_name(),
                    platform_app_id=aid,
                    name=nm,
                    install_path=Path(ipath) if ipath else None,
                    launch_command=cmd,
                    install_size=isize,
                )
            )

        logger.info("found %d Amazon games via Heroic" % len(games))
        return games
