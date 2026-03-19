#
# steam_library_manager/services/external_games_service.py
# Service layer for discovering and importing external game sources
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

import logging

from steam_library_manager.core.shortcuts_manager import SteamShortcut, generate_shortcut_id
from steam_library_manager.integrations.external_games.bottles_parser import BottlesParser
from steam_library_manager.integrations.external_games.flatpak_parser import FlatpakParser
from steam_library_manager.integrations.external_games.heroic_amazon_parser import HeroicAmazonParser
from steam_library_manager.integrations.external_games.heroic_epic_parser import HeroicEpicParser
from steam_library_manager.integrations.external_games.heroic_gog_parser import HeroicGOGParser
from steam_library_manager.integrations.external_games.itch_parser import ItchParser
from steam_library_manager.integrations.external_games.lutris_parser import LutrisParser
from steam_library_manager.integrations.external_games.rom_parser import RomParser
from steam_library_manager.integrations.external_games.shortcuts_vdf_parser import ShortcutsVDFParser

__all__ = ["ExternalGamesService"]

logger = logging.getLogger("steamlibmgr.external_games_service")


class ExternalGamesService:
    """Orchestrates scanning external launchers and importing
    discovered games into Steam as non-Steam shortcuts.
    """

    def __init__(self, shortcuts_manager):
        self._shortcuts_mgr = shortcuts_manager
        self._parsers = self._init_parsers()

    def _init_parsers(self):
        # One parser per supported external platform
        parsers = [
            HeroicEpicParser(),
            HeroicGOGParser(),
            HeroicAmazonParser(),
            LutrisParser(),
            ItchParser(),
            BottlesParser(),
            FlatpakParser(),
            RomParser(),
        ]
        return {p.platform_name(): p for p in parsers}

    def get_available_platforms(self):
        # Platforms that are actually installed on this system
        return [name for name, parser in self._parsers.items() if parser.is_available()]

    def scan_all_platforms(self):
        # Scan every available platform, return {name: [games]}
        results = {}
        for name, parser in self._parsers.items():
            if parser.is_available():
                try:
                    games = parser.read_games()
                    if games:
                        results[name] = games
                except Exception:
                    logger.exception("Error scanning %s", name)
        return results

    def scan_platform(self, platform):
        # Scan a single platform by name
        parser = self._parsers.get(platform)
        if not parser or not parser.is_available():
            return []
        return parser.read_games()

    def get_existing_shortcuts(self):
        # Lowercase set of app names already in shortcuts.vdf
        vdf = ShortcutsVDFParser(self._shortcuts_mgr)
        return {g.name.lower() for g in vdf.read_games()}

    def add_to_steam(self, game, category_tag=None):
        # Add single game as non-Steam shortcut, returns True on success
        exe = self._build_exe(game)
        start_dir = self._build_start_dir(game)
        appid = generate_shortcut_id(exe, game.name)

        tags = {}
        if category_tag:
            tags["0"] = category_tag

        shortcut = SteamShortcut(
            appid=appid,
            app_name=game.name,
            exe=exe,
            start_dir=start_dir,
            icon=str(game.icon_path) if game.icon_path else "",
            launch_options=self._build_launch_options(game),
            tags=tags,
        )

        return self._shortcuts_mgr.add_shortcut(shortcut)

    def batch_add_to_steam(self, games, progress_callback=None, category_tag=None):
        # Batch-add games, returns {"added": N, "skipped": N, "errors": N}
        stats = {"added": 0, "skipped": 0, "errors": 0}
        total = len(games)

        for i, game in enumerate(games):
            if progress_callback:
                progress_callback(i + 1, total, game.name)
            try:
                if self.add_to_steam(game, category_tag=category_tag):
                    stats["added"] += 1
                else:
                    stats["skipped"] += 1
            except Exception:
                logger.exception("Error adding %s to Steam", game.name)
                stats["errors"] += 1

        logger.info(
            "Batch add complete: %d added, %d skipped, %d errors",
            stats["added"],
            stats["skipped"],
            stats["errors"],
        )
        return stats

    def remove_from_steam(self, app_name):
        return self._shortcuts_mgr.remove_shortcut(app_name)

    @staticmethod
    def _build_exe(game):
        # Build quoted exe string for shortcuts.vdf
        if game.launch_command:
            cmd = game.launch_command
            if "://" in cmd or cmd.startswith("flatpak run"):
                return '"%s"' % cmd
            return cmd
        if game.executable:
            return '"%s"' % game.executable
        return '""'

    @staticmethod
    def _build_start_dir(game):
        if game.install_path:
            return '"%s"' % game.install_path
        return '"./"'

    @staticmethod
    def _build_launch_options(game):
        # Flatpak games get their options via the launch command
        if game.platform == "Flatpak" and game.launch_command.startswith("flatpak run"):
            return ""
        return ""
