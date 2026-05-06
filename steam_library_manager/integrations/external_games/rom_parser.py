#
# steam_library_manager/integrations/external_games/rom_parser.py
# Thin facade that exposes EmulatorService results as ExternalGame objects
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
from pathlib import Path

from steam_library_manager.integrations.external_games.base_parser import BaseExternalParser
from steam_library_manager.integrations.external_games.models import ExternalGame

__all__ = ["RomParser"]

logger = logging.getLogger("steamlibmgr.external_games.rom_parser")


class RomParser(BaseExternalParser):
    """ExternalGame producer for emulator-based games.

    All detection and discovery logic now lives in EmulatorService.
    This parser is a thin adapter that turns service results into
    ExternalGame objects for the existing ExternalGamesDialog table.
    """

    def __init__(self, emulator_service=None) -> None:
        # service is optional so the parser still imports cleanly when no
        # database is wired up (older callsites). Without a service we return
        # an empty list - the alternative is hardcoded paths and we explicitly
        # killed those off in v1.5.0.
        self._svc = emulator_service

    def platform_name(self):
        return "Emulation (ROMs)"

    def is_available(self):
        if self._svc is None:
            return False
        try:
            installed = self._svc.detect_installed_emulators()
        except Exception:
            logger.exception("emulator detection failed")
            return False
        return bool(installed)

    def get_config_paths(self):
        # union of game_dirs across all installed emulators
        if self._svc is None:
            return []
        try:
            installed = self._svc.detect_installed_emulators()
        except Exception:
            return []
        seen: set[Path] = set()
        for ie in installed:
            for d in ie.game_dirs:
                if d.is_dir():
                    seen.add(d)
        return sorted(seen)

    def read_games(self):
        if self._svc is None:
            logger.info("RomParser: no EmulatorService wired, returning []")
            return []

        # ensure cache is populated; cheap if already discovered this session
        try:
            self._svc.discover_libraries()
        except Exception:
            logger.exception("discover_libraries failed")
            return []

        try:
            entries = self._svc.get_games_for_steam_export(only_unexported=False)
        except Exception:
            logger.exception("get_games_for_steam_export failed")
            return []

        games: list[ExternalGame] = []
        for e in entries:
            games.append(
                ExternalGame(
                    platform="Emulation (%s)" % e.system_display,
                    platform_app_id="rom:%s:%s" % (e.system, Path(e.rom_path).name),
                    name=e.name,
                    install_path=Path(e.rom_path).parent,
                    executable=e.emulator_name,
                    launch_command=e.launch_command,
                    platform_metadata=(
                        ("emulator", e.emulator_name),
                        ("system", e.system),
                        ("rom_file", Path(e.rom_path).name),
                        ("rom_extension", Path(e.rom_path).suffix.lower()),
                    ),
                )
            )

        logger.info("RomParser: %d games via EmulatorService" % len(games))
        return games
