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
    """Parser for Amazon Games."""

    _RUNNER = "nile"

    def platform_name(self):
        return "Heroic (Amazon)"

    def is_available(self):
        return self._find_config_file() is not None

    def get_config_paths(self):
        return [_NATIVE, _FLATPAK]

    def read_games(self):
        # parse nile config
        data, cp = self._load_heroic_config_with_path()

        if not isinstance(data, list):
            return []

        fp = self._is_flatpak(cp) if cp else False
        gs = []

        for e in data:
            if not isinstance(e, dict):
                continue

            aid = e.get("id", "")
            ipath = e.get("path", "")
            sz = e.get("size", 0)
            if isinstance(sz, str):
                sz = 0

            # name from path (no title field)
            nm = Path(ipath).name if ipath else aid

            cmd = self._build_heroic_launch_command(aid, fp)

            gs.append(
                ExternalGame(
                    platform=self.platform_name(),
                    platform_app_id=aid,
                    name=nm,
                    install_path=Path(ipath) if ipath else None,
                    launch_command=cmd,
                    install_size=sz,
                )
            )

        logger.info("found %d Amazon games" % len(gs))
        return gs
