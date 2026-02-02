"""
Metadata Service for Steam Library Manager.

This service handles all metadata-related operations including:
- Single game metadata editing
- Bulk metadata editing with name modifications
- Finding games with missing metadata
- Restoring metadata modifications

The service acts as a bridge between the UI and AppInfoManager,
providing a clean API for metadata operations.
"""
from typing import Dict, Any, List, Optional

from src.core.game_manager import Game, GameManager
from src.core.appinfo_manager import AppInfoManager


class MetadataService:
    """Service for managing game metadata operations."""

    def __init__(self, appinfo_manager: AppInfoManager, game_manager: GameManager):
        """
        Initialize the MetadataService.

        Args:
            appinfo_manager: Manager for reading/writing appinfo metadata.
            game_manager: Manager for accessing game data.
        """
        self.appinfo_manager = appinfo_manager
        self.game_manager = game_manager

    # === SINGLE GAME METADATA ===

    def get_game_metadata(self, app_id: str, game: Optional[Game] = None) -> Dict[str, Any]:
        """
        Get metadata for a single game with defaults from game object.

        Args:
            app_id: Steam app ID.
            game: Optional game object to use for defaults.

        Returns:
            Dictionary containing metadata with defaults filled in.
        """
        meta = self.appinfo_manager.get_app_metadata(app_id)

        # Fill defaults from game object if provided
        if game:
            defaults = {
                'name': game.name,
                'developer': game.developer,
                'publisher': game.publisher,
                'release_date': game.release_year
            }
            for key, val in defaults.items():
                if not meta.get(key):
                    meta[key] = val

        return meta

    def set_game_metadata(self, app_id: str, metadata: Dict[str, Any]) -> None:
        """
        Set metadata for a single game.

        Args:
            app_id: Steam app ID.
            metadata: Dictionary containing metadata fields to set.
        """
        self.appinfo_manager.set_app_metadata(app_id, metadata)
        self.appinfo_manager.save_appinfo()

    def get_original_metadata(self, app_id: str, fallback: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get original (unmodified) metadata for a game.

        Args:
            app_id: Steam app ID.
            fallback: Optional fallback metadata if no original exists.

        Returns:
            Original metadata or fallback if not modified.
        """
        modifications = self.appinfo_manager.modifications.get(app_id, {})
        original = modifications.get('original', {})

        if not original and fallback:
            return fallback.copy()

        return original

    # === BULK METADATA ===

    def apply_bulk_metadata(
            self,
            games: List[Game],
            metadata: Dict[str, Any],
            name_modifications: Optional[Dict[str, str]] = None
    ) -> int:
        """
        Apply metadata changes to multiple games.

        Args:
            games: List of games to modify.
            metadata: Metadata fields to set (without name_modifications).
            name_modifications: Optional dict with 'prefix', 'suffix', 'remove'.

        Returns:
            Number of games modified.
        """
        if not games:
            return 0

        modified_count = 0

        for game in games:
            # Apply name modifications if provided
            new_name = game.name
            if name_modifications:
                new_name = self._apply_name_modifications(game.name, name_modifications)

            # Create metadata dict for this game
            meta = metadata.copy()
            if new_name != game.name:
                meta['name'] = new_name

            # Set metadata
            self.appinfo_manager.set_app_metadata(game.app_id, meta)
            modified_count += 1

        # Save once after all modifications
        self.appinfo_manager.save_appinfo()

        return modified_count

    @staticmethod
    def _apply_name_modifications(name: str, mods: Dict[str, str]) -> str:
        """
        Apply prefix, suffix, and remove modifications to a name.

        Args:
            name: Original name.
            mods: Dictionary with optional 'prefix', 'suffix', 'remove' keys.

        Returns:
            Modified name.
        """
        result = name

        # Apply prefix
        if mods.get('prefix'):
            result = mods['prefix'] + result

        # Apply suffix
        if mods.get('suffix'):
            result = result + mods['suffix']

        # Apply remove
        if mods.get('remove'):
            result = result.replace(mods['remove'], '')

        return result

    # === MISSING METADATA ===

    def find_missing_metadata(self) -> List[Game]:
        """
        Find games with incomplete metadata.

        A game is considered to have missing metadata if it lacks:
        - Developer
        - Publisher
        - Release year

        Returns:
            List of games missing at least one metadata field.
        """
        affected = []

        for game in self.game_manager.get_real_games():
            if not game.developer or not game.publisher or not game.release_year:
                affected.append(game)

        return affected

    # === RESTORE ===

    def get_modification_count(self) -> int:
        """
        Get number of games with modified metadata.

        Returns:
            Count of games with metadata modifications.
        """
        return self.appinfo_manager.get_modification_count()

    def restore_modifications(self) -> int:
        """
        Restore all metadata modifications to original values.

        Returns:
            Number of games restored.
        """
        return self.appinfo_manager.restore_modifications()
