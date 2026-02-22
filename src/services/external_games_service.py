"""Orchestrator for external game scanning and Steam integration.

Manages all platform parsers and coordinates adding non-Steam
game shortcuts to Steam's shortcuts.vdf.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.core.shortcuts_manager import SteamShortcut, generate_shortcut_id
from src.integrations.external_games.bottles_parser import BottlesParser
from src.integrations.external_games.flatpak_parser import FlatpakParser
from src.integrations.external_games.heroic_amazon_parser import HeroicAmazonParser
from src.integrations.external_games.heroic_epic_parser import HeroicEpicParser
from src.integrations.external_games.heroic_gog_parser import HeroicGOGParser
from src.integrations.external_games.itch_parser import ItchParser
from src.integrations.external_games.lutris_parser import LutrisParser
from src.integrations.external_games.models import ExternalGame
from src.integrations.external_games.rom_parser import RomParser
from src.integrations.external_games.shortcuts_vdf_parser import ShortcutsVDFParser

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.core.shortcuts_manager import ShortcutsManager
    from src.integrations.external_games.base_parser import BaseExternalParser

__all__ = ["ExternalGamesService"]

logger = logging.getLogger("steamlibmgr.external_games_service")


class ExternalGamesService:
    """Orchestrate external game scanning and Steam integration.

    Args:
        shortcuts_manager: ShortcutsManager for shortcuts.vdf operations.
    """

    def __init__(self, shortcuts_manager: ShortcutsManager) -> None:
        """Initializes the service.

        Args:
            shortcuts_manager: Configured ShortcutsManager instance.
        """
        self._shortcuts_mgr = shortcuts_manager
        self._parsers: dict[str, BaseExternalParser] = self._init_parsers()

    def _init_parsers(self) -> dict[str, BaseExternalParser]:
        """Initialize all platform parsers.

        Returns:
            Dict mapping platform name to parser instance.
        """
        parsers: list[BaseExternalParser] = [
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

    def get_available_platforms(self) -> list[str]:
        """Return list of platforms that are installed on this system.

        Returns:
            Platform names with available data sources.
        """
        return [name for name, parser in self._parsers.items() if parser.is_available()]

    def scan_all_platforms(self) -> dict[str, list[ExternalGame]]:
        """Scan all available platforms for installed games.

        Returns:
            Dict mapping platform name to list of found games.
        """
        results: dict[str, list[ExternalGame]] = {}
        for name, parser in self._parsers.items():
            if parser.is_available():
                try:
                    games = parser.read_games()
                    if games:
                        results[name] = games
                except Exception:
                    logger.exception("Error scanning %s", name)
        return results

    def scan_platform(self, platform: str) -> list[ExternalGame]:
        """Scan a single platform for installed games.

        Args:
            platform: Platform name to scan.

        Returns:
            List of found games, empty if platform unavailable.
        """
        parser = self._parsers.get(platform)
        if not parser or not parser.is_available():
            return []
        return parser.read_games()

    def get_existing_shortcuts(self) -> set[str]:
        """Get set of app names already in shortcuts.vdf.

        Case-insensitive for duplicate detection.

        Returns:
            Set of lowercase app names from shortcuts.vdf.
        """
        vdf_parser = ShortcutsVDFParser(self._shortcuts_mgr)
        return {g.name.lower() for g in vdf_parser.read_games()}

    def add_to_steam(
        self,
        game: ExternalGame,
        category_tag: str | None = None,
    ) -> bool:
        """Add single game to Steam as Non-Steam shortcut.

        Args:
            game: External game to add.
            category_tag: Optional Steam category (e.g. "GOG Games").

        Returns:
            True if added successfully, False if duplicate or error.
        """
        exe = self._build_exe(game)
        start_dir = self._build_start_dir(game)
        appid = generate_shortcut_id(exe, game.name)

        tags: dict[str, str] = {}
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

    def batch_add_to_steam(
        self,
        games: list[ExternalGame],
        progress_callback: Callable[[int, int, str], None] | None = None,
        category_tag: str | None = None,
    ) -> dict[str, int]:
        """Batch-add multiple games to Steam.

        Args:
            games: List of games to add.
            progress_callback: Optional callback(current, total, game_name).
            category_tag: Optional category tag for all games.

        Returns:
            Dict with keys "added", "skipped", "errors".
        """
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

    def remove_from_steam(self, app_name: str) -> bool:
        """Remove non-Steam game shortcut.

        Args:
            app_name: Name of the game to remove.

        Returns:
            True if removed successfully.
        """
        return self._shortcuts_mgr.remove_shortcut(app_name)

    @staticmethod
    def _build_exe(game: ExternalGame) -> str:
        """Build the quoted exe string for shortcuts.vdf.

        Args:
            game: External game.

        Returns:
            Quoted executable path or launch command.
        """
        if game.launch_command:
            # For URI-based launchers (heroic://, lutris:, itch://)
            cmd = game.launch_command
            if "://" in cmd or cmd.startswith("flatpak run"):
                return f'"{cmd}"'
            return cmd
        if game.executable:
            return f'"{game.executable}"'
        return '""'

    @staticmethod
    def _build_start_dir(game: ExternalGame) -> str:
        """Build the start directory for shortcuts.vdf.

        Args:
            game: External game.

        Returns:
            Quoted start directory path.
        """
        if game.install_path:
            return f'"{game.install_path}"'
        return '"./"'

    @staticmethod
    def _build_launch_options(game: ExternalGame) -> str:
        """Build launch options string.

        Args:
            game: External game.

        Returns:
            Launch options (empty for most games).
        """
        # Flatpak games have complex launch options
        if game.platform == "Flatpak" and game.launch_command.startswith("flatpak run"):
            return ""
        return ""
