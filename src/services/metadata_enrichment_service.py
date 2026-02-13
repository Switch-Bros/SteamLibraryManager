# src/services/metadata_enrichment_service.py

"""Service for merging and enriching game metadata from various sources.

Extracted from GameManager to separate the concern of metadata merging
(localconfig categories, appinfo.vdf data, custom overrides) from core
game management logic.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from src.core.game import Game
from src.utils.date_utils import format_timestamp_to_date
from src.utils.i18n import t

logger = logging.getLogger("steamlibmgr.metadata_enrichment")

__all__ = ["MetadataEnrichmentService"]


class MetadataEnrichmentService:
    """Merges and enriches game metadata from multiple sources.

    Operates on a shared games dict (by reference) so that mutations
    are immediately visible to GameManager and the rest of the app.

    Args:
        games: Shared reference to the GameManager's games dict.
        cache_dir: Directory for JSON cache files.
    """

    def __init__(self, games: dict[str, Game], cache_dir: Path) -> None:
        self._games = games
        self._cache_dir = cache_dir

    def merge_with_localconfig(self, parser) -> None:
        """Merges categories and hidden status from parser into loaded games.

        For cloud_storage_parser: loads favorites, hidden, and user collections.
        For localconfig_helper: loads only hidden status (old method).

        Args:
            parser: An instance of CloudStorageParser or LocalConfigHelper.
        """
        logger.info(t("logs.manager.merging"))

        # Get favorites and hidden from collections (Depressurizer way!)
        favorites_key = t("ui.categories.favorites")
        hidden_key = t("ui.categories.hidden")

        favorites_apps: set[str] = set()
        hidden_apps: set[str] = set()

        # If using cloud_storage_parser, get favorites/hidden from collections
        if hasattr(parser, "collections"):
            for collection in parser.collections:
                col_name = collection.get("name", "")
                col_id = collection.get("id", "")
                added = collection.get("added", [])

                # Check if this is favorites collection
                if col_id == "favorite" or col_name == favorites_key:
                    favorites_apps.update(str(app_id) for app_id in added)

                # Check if this is hidden collection
                if col_id == "hidden" or col_name == hidden_key:
                    hidden_apps.update(str(app_id) for app_id in added)

        # Also check old hidden flag from localconfig (backwards compatibility)
        if hasattr(parser, "get_hidden_apps"):
            old_hidden = set(parser.get_hidden_apps())
            hidden_apps.update(old_hidden)

        # Apply to all games
        for app_id, game in self._games.items():
            # Set favorites
            if app_id in favorites_apps:
                if favorites_key not in game.categories:
                    game.categories.append(favorites_key)

            # Set hidden status
            if app_id in hidden_apps:
                game.hidden = True
                if hidden_key not in game.categories:
                    game.categories.append(hidden_key)

            # Apply other categories from parser
            if hasattr(parser, "get_app_categories"):
                try:
                    other_cats = parser.get_app_categories(app_id)
                    if other_cats:
                        for cat in other_cats:
                            # Skip special categories (already handled above)
                            if cat not in [favorites_key, hidden_key]:
                                if cat not in game.categories:
                                    game.categories.append(cat)
                except (KeyError, ValueError, TypeError):
                    pass  # Game not in parser

        # Add missing games from parser (if using cloud_storage)
        if hasattr(parser, "get_all_app_ids"):
            try:
                local_app_ids = set(parser.get_all_app_ids())
                api_app_ids = set(self._games.keys())
                missing_ids = local_app_ids - api_app_ids

                if missing_ids:
                    for app_id in missing_ids:
                        categories: list[str] = []

                        # Check favorites
                        if app_id in favorites_apps:
                            categories.append(favorites_key)

                        # Check hidden
                        is_hidden = app_id in hidden_apps
                        if is_hidden:
                            categories.append(hidden_key)

                        # Get other categories
                        if hasattr(parser, "get_app_categories"):
                            try:
                                other_cats = parser.get_app_categories(app_id)
                                if other_cats:
                                    categories.extend(other_cats)
                            except (KeyError, ValueError, TypeError):
                                pass

                        # Skip if no categories
                        if not categories:
                            continue

                        # Create game entry
                        name = self._get_cached_name(app_id) or t("ui.game_details.game_fallback", id=app_id)
                        game = Game(app_id=app_id, name=name)
                        game.categories = categories
                        game.hidden = is_hidden
                        self._games[app_id] = game
            except (KeyError, ValueError, TypeError):
                pass  # Parser doesn't support get_all_app_ids

    def _get_cached_name(self, app_id: str) -> str | None:
        """Tries to retrieve a game name from the local JSON cache.

        Args:
            app_id: The app ID to look up.

        Returns:
            The cached game name, or None if not found.
        """
        cache_file = self._cache_dir / "store_data" / f"{app_id}.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r") as f:
                    data = json.load(f)
                    return data.get("name")
            except (OSError, json.JSONDecodeError):
                pass
        return None

    # Types that represent real content worth showing in the library
    _DISCOVERABLE_TYPES: frozenset[str] = frozenset({"game", "music", "tool", "application", "video"})

    def discover_missing_games(
        self,
        localconfig_helper,
        appinfo_manager,
        packageinfo_ids: set[str] | None = None,
        *,
        db_type_lookup: dict[str, tuple[str, str]] | None = None,
    ) -> int:
        """Discovers owned games missing from the API response.

        Collects candidate app IDs from multiple local sources (localconfig,
        packageinfo) and cross-references them with metadata.  When
        ``db_type_lookup`` is provided the fast DB-based path is used,
        otherwise falls back to per-app appinfo_manager lookups.

        Args:
            localconfig_helper: A loaded LocalConfigHelper instance.
            appinfo_manager: A loaded AppInfoManager instance.
            packageinfo_ids: Optional set of app IDs from packageinfo.vdf.
            db_type_lookup: Optional {app_id_str: (app_type, name)} from DB.

        Returns:
            Number of newly discovered games added.
        """
        # Collect candidate IDs from all available sources
        candidate_ids: set[str] = set()

        if localconfig_helper:
            candidate_ids.update(localconfig_helper.get_all_app_ids())

        if packageinfo_ids:
            candidate_ids.update(packageinfo_ids)

        # Remove already-known games
        known_ids = set(self._games.keys())
        candidates = candidate_ids - known_ids

        if not candidates:
            return 0

        count = 0
        for app_id in candidates:
            if db_type_lookup is not None:
                # Fast path: use pre-fetched DB data
                lookup = db_type_lookup.get(app_id)
                if not lookup:
                    continue
                app_type = (lookup[0] or "").lower()
                db_name = lookup[1] or ""
            else:
                # Legacy path: per-app binary lookup
                meta = appinfo_manager.get_app_metadata(app_id)
                app_type = meta.get("type", "").lower()
                db_name = meta.get("name", "")

            if app_type not in self._DISCOVERABLE_TYPES:
                continue

            name = db_name or self._get_cached_name(app_id) or t("ui.game_details.game_fallback", id=app_id)

            game = Game(app_id=app_id, name=name, app_type=app_type)
            self._games[app_id] = game
            count += 1

        if count > 0:
            logger.info(t("logs.manager.discovered_missing", count=count))

        return count

    def apply_appinfo_data(self, appinfo_data: dict) -> None:
        """Applies last_updated timestamp from appinfo.vdf data.

        Args:
            appinfo_data: A dictionary of app data from appinfo.vdf.
        """
        for app_id, data in appinfo_data.items():
            if app_id in self._games:
                if "common" in data and "last_updated" in data["common"]:
                    ts = data["common"]["last_updated"]
                    try:
                        # Centralised formatter handles int/str and locale automatically
                        self._games[app_id].last_updated = format_timestamp_to_date(ts)
                    except (ValueError, TypeError):
                        pass

    def apply_metadata_overrides(self, appinfo_manager) -> None:
        """Applies metadata overrides from AppInfoManager.

        This method first loads metadata from the binary appinfo.vdf (via AppInfoManager),
        then applies any custom user modifications stored in custom_metadata.json.

        Args:
            appinfo_manager: An instance of AppInfoManager with loaded appinfo.vdf data.

        Returns:
            The appinfo_manager instance (for caller to store if needed).
        """
        # Use already-loaded data; only load if not yet initialized
        if not appinfo_manager.steam_apps:
            appinfo_manager.load_appinfo()
        modifications = appinfo_manager.modifications

        count = 0

        # 1. BINARY APPINFO METADATA
        for app_id, game in self._games.items():
            steam_meta = appinfo_manager.get_app_metadata(app_id)

            # Set app_type from appinfo.vdf for all games
            if not game.app_type and steam_meta.get("type"):
                game.app_type = steam_meta["type"]

            # Check for fallback name usage
            fallback_name = t("ui.game_details.game_fallback", id=app_id)

            if (game.name == fallback_name or game.name.startswith("App ")) and steam_meta.get("name"):
                game.name = steam_meta["name"]
                if not game.name_overridden:
                    game.sort_name = game.name

            if not game.developer and steam_meta.get("developer"):
                game.developer = steam_meta["developer"]

            if not game.publisher and steam_meta.get("publisher"):
                game.publisher = steam_meta["publisher"]

            if not game.release_year and steam_meta.get("release_date"):
                game.release_year = steam_meta["release_date"]

            # Extract review percentage and metacritic score from appinfo.vdf
            if not game.review_percentage and steam_meta.get("review_percentage"):
                game.review_percentage = int(steam_meta["review_percentage"])

            if not game.metacritic_score and steam_meta.get("metacritic_score"):
                game.metacritic_score = int(steam_meta["metacritic_score"])

        # 2. CUSTOM OVERRIDES
        for app_id, meta_data in modifications.items():
            if app_id in self._games:
                game = self._games[app_id]
                modified = meta_data.get("modified", {})

                if modified.get("name"):
                    game.name = modified["name"]
                    game.name_overridden = True
                if modified.get("sort_as"):
                    game.sort_name = modified["sort_as"]
                elif game.name_overridden:
                    game.sort_name = game.name
                if modified.get("developer"):
                    game.developer = modified["developer"]
                if modified.get("publisher"):
                    game.publisher = modified["publisher"]
                if modified.get("release_date"):
                    game.release_year = modified["release_date"]
                if modified.get("pegi_rating"):
                    game.pegi_rating = modified["pegi_rating"]

                count += 1

        if count > 0:
            logger.info(t("logs.manager.applied_overrides", count=count))

    def apply_custom_overrides(self, modifications: dict[str, dict]) -> None:
        """Applies ONLY custom JSON overrides, skipping the binary appinfo phase.

        Identical to the second half of ``apply_metadata_overrides()`` but
        without needing a loaded binary.  Used during lazy-load startup
        where the DB already provides base metadata.

        Args:
            modifications: Dict of {app_id: {"original": ..., "modified": {...}}}.
        """
        count = 0
        for app_id, meta_data in modifications.items():
            if app_id in self._games:
                game = self._games[app_id]
                modified = meta_data.get("modified", {})

                if modified.get("name"):
                    game.name = modified["name"]
                    game.name_overridden = True
                if modified.get("sort_as"):
                    game.sort_name = modified["sort_as"]
                elif game.name_overridden:
                    game.sort_name = game.name
                if modified.get("developer"):
                    game.developer = modified["developer"]
                if modified.get("publisher"):
                    game.publisher = modified["publisher"]
                if modified.get("release_date"):
                    game.release_year = modified["release_date"]
                if modified.get("pegi_rating"):
                    game.pegi_rating = modified["pegi_rating"]

                count += 1

        if count > 0:
            logger.info(t("logs.manager.applied_overrides", count=count))
