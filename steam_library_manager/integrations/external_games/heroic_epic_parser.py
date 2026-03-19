#
# steam_library_manager/integrations/external_games/heroic_epic_parser.py
# Heroic Launcher parser for Epic Games Store
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
from pathlib import Path

from steam_library_manager.integrations.external_games.base_heroic_parser import BaseHeroicParser
from steam_library_manager.integrations.external_games.models import ExternalGame

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
    """Parser for Epic Games."""

    _RUNNER = "legendary"

    def platform_name(self):
        return "Heroic (Epic)"

    def is_available(self):
        return self._find_config_file() is not None

    def get_config_paths(self):
        return [_NATIVE, _FLATPAK]

    def read_games(self):
        # parse legendary config
        d, cp = self._load_heroic_config_with_path()
        if not isinstance(d, dict):
            return []

        fp = self._is_flatpak(cp) if cp else False
        gs = []

        for aid, e in d.items():
            if not isinstance(e, dict):
                continue
            if e.get("is_dlc", False):
                continue

            nm = e.get("title", aid)
            p = e.get("install_path")
            sz = e.get("install_size", 0)
            if isinstance(sz, str):
                sz = 0

            c = self._build_heroic_launch_command(aid, fp)

            gs.append(
                ExternalGame(
                    platform=self.platform_name(),
                    platform_app_id=aid,
                    name=nm,
                    install_path=Path(p) if p else None,
                    executable=e.get("executable"),
                    launch_command=c,
                    install_size=sz,
                    platform_metadata=(("platform", e.get("platform", "")),),
                )
            )

        logger.info("found %d Epic games" % len(gs))
        return gs
