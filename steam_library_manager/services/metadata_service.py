#
# steam_library_manager/services/metadata_service.py
# Service for managing game metadata operations
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from typing import Any

from steam_library_manager.core.game_manager import Game, GameManager
from steam_library_manager.core.appinfo_manager import AppInfoManager

__all__ = ["MetadataService"]


class MetadataService:
    """Service for managing game metadata operations."""

    def __init__(self, appinfo_manager: AppInfoManager, game_manager: GameManager):
        self.appinfo_manager = appinfo_manager
        self.game_manager = game_manager

    def get_game_metadata(self, app_id: str, game: Game | None = None) -> dict[str, Any]:
        """Get metadata for a single game with defaults from game object."""
        meta = self.appinfo_manager.get_app_metadata(app_id)

        if game:
            defaults = {
                "name": game.name,
                "developer": game.developer,
                "publisher": game.publisher,
                "release_date": game.release_year,
            }
            for key, val in defaults.items():
                if not meta.get(key):
                    meta[key] = val

        return meta

    def set_game_metadata(self, app_id: str, metadata: dict[str, Any]) -> None:
        """Set metadata for a single game."""
        self.appinfo_manager.set_app_metadata(app_id, metadata)
        self.appinfo_manager.save_appinfo()

    def get_original_metadata(self, app_id: str, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
        """Get original (unmodified) metadata for a game."""
        modifications = self.appinfo_manager.modifications.get(app_id, {})
        original = modifications.get("original", {})

        if not original and fallback:
            return fallback.copy()

        return original

    def apply_bulk_metadata(
        self, games: list[Game], metadata: dict[str, Any], name_modifications: dict[str, str] | None = None
    ) -> int:
        """Apply metadata changes to multiple games."""
        if not games:
            return 0

        modified_count = 0

        for game in games:
            new_name = game.name
            if name_modifications:
                new_name = self._apply_name_modifications(game.name, name_modifications)

            meta = metadata.copy()
            if new_name != game.name:
                meta["name"] = new_name
                meta["sort_as"] = new_name

            self.appinfo_manager.set_app_metadata(game.app_id, meta)
            modified_count += 1

        self.appinfo_manager.save_appinfo()

        return modified_count

    @staticmethod
    def _apply_name_modifications(name: str, mods: dict[str, str]) -> str:
        from steam_library_manager.utils.name_utils import apply_name_modifications

        return apply_name_modifications(name, mods)

    def restore_games_to_original(self, games: list[Game]) -> int:
        """Restore metadata to original values for specific games."""
        restored = 0
        for game in games:
            app_id = game.app_id
            if app_id in self.appinfo_manager.modifications:
                del self.appinfo_manager.modifications[app_id]
                if app_id in self.appinfo_manager.modified_apps:
                    self.appinfo_manager.modified_apps.remove(app_id)
                restored += 1

        if restored > 0:
            self.appinfo_manager.save_appinfo()

        return restored

    def find_missing_metadata(self) -> list[Game]:
        """Find games missing developer, publisher, or release year."""
        affected = []

        for game in self.game_manager.get_real_games():
            if not game.developer or not game.publisher or not game.release_year:
                affected.append(game)

        return affected

    def get_modification_count(self) -> int:
        """Get number of games with modified metadata."""
        return self.appinfo_manager.get_modification_count()

    def restore_modifications(self) -> int:
        """Restore all metadata modifications to original values."""
        return self.appinfo_manager.restore_modifications()
