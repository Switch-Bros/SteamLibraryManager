#
# steam_library_manager/services/enrichment/metadata_enrichment_service.py
# Enrichment service for game metadata from the Steam Store
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#


from __future__ import annotations

import json
import logging
from pathlib import Path

from typing import Final

from steam_library_manager.core.database import is_placeholder_name
from steam_library_manager.core.game import Game
from steam_library_manager.utils.date_utils import format_timestamp_to_date
from steam_library_manager.utils.i18n import t

logger = logging.getLogger("steamlibmgr.metadata_enrichment")

__all__ = ["MetadataEnrichmentService"]

# Language-independent identifiers for system collections.
# Matches Steam internal IDs + known EN/DE display names.
# TODO v1.2: Refactor to use ONLY collection IDs for system collection
# detection. Remove hardcoded name matching once all consumers use IDs.
FAVORITES_IDENTIFIERS: Final[frozenset[str]] = frozenset(
    {
        "favorite",
        "Favorites",
        "Favoriten",
    }
)
HIDDEN_IDENTIFIERS: Final[frozenset[str]] = frozenset(
    {
        "hidden",
        "Hidden",
        "Versteckt",
    }
)


class MetadataEnrichmentService:
    """Merges and enriches game metadata from multiple sources."""

    def __init__(self, games: dict[str, Game], cache_dir: Path) -> None:
        self._games = games
        self._cache_dir = cache_dir

    # merge categories and hidden status from parser
    def merge_with_localconfig(self, parser) -> None:
        logger.info(t("logs.manager.merging"))

        # Get favorites and hidden from collections (Depressurizer way!)
        # Display keys use current locale for game.categories labels
        fav_key = t("categories.favorites")
        hid_key = t("categories.hidden")

        favs = set()
        hid = set()

        # If using cloud_storage_parser, get favorites/hidden from collections
        if hasattr(parser, "collections"):
            for collection in parser.collections:
                col_name = collection.get("name", "")
                col_id = collection.get("id", "")
                added = collection.get("added", [])

                # Check if this is favorites collection (language-independent)
                if col_id in FAVORITES_IDENTIFIERS or col_name in FAVORITES_IDENTIFIERS:
                    favs.update(str(app_id) for app_id in added)

                # Check if this is hidden collection (language-independent)
                if col_id in HIDDEN_IDENTIFIERS or col_name in HIDDEN_IDENTIFIERS:
                    hid.update(str(app_id) for app_id in added)

        # Also check old hidden flag from localconfig (backwards compatibility)
        if hasattr(parser, "get_hidden_apps"):
            old_hidden = set(parser.get_hidden_apps())
            hid.update(old_hidden)

        # Apply to all games
        for app_id, game in self._games.items():
            # Set favorites
            if app_id in favs:
                if fav_key not in game.categories:
                    game.categories.append(fav_key)

            # Set hidden status
            if app_id in hid:
                game.hidden = True
                if hid_key not in game.categories:
                    game.categories.append(hid_key)

            # Apply other categories from parser
            if hasattr(parser, "get_app_categories"):
                try:
                    cats = parser.get_app_categories(app_id)
                    if cats:
                        for cat in cats:
                            # Skip special categories (already handled above)
                            if cat not in [fav_key, hid_key]:
                                if cat not in game.categories:
                                    game.categories.append(cat)
                except (KeyError, ValueError, TypeError):
                    pass  # Game not in parser

        # Add missing games from parser (if using cloud_storage)
        if hasattr(parser, "get_all_app_ids"):
            try:
                local_ids = set(parser.get_all_app_ids())
                api_ids = set(self._games.keys())
                missing = local_ids - api_ids

                if missing:
                    for app_id in missing:
                        cats = []

                        # Check favorites
                        if app_id in favs:
                            cats.append(fav_key)

                        # Check hidden
                        hidden = app_id in hid
                        if hidden:
                            cats.append(hid_key)

                        # Get other categories
                        if hasattr(parser, "get_app_categories"):
                            try:
                                parser_cats = parser.get_app_categories(app_id)
                                if parser_cats:
                                    cats.extend(parser_cats)
                            except (KeyError, ValueError, TypeError):
                                pass

                        # Skip if no categories
                        if not cats:
                            continue

                        # Create game entry
                        name = self._get_cached_name(app_id) or t("ui.game_details.game_fallback", id=app_id)
                        game = Game(app_id=app_id, name=name)
                        game.categories = cats
                        game.hidden = hidden
                        self._games[app_id] = game
            except (KeyError, ValueError, TypeError):
                pass  # Parser doesn't support get_all_app_ids

    def _get_cached_name(self, app_id: str) -> str | None:
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

    # find owned games missing from API response
    def discover_missing_games(
        self,
        localconfig_helper,
        appinfo_manager,
        packageinfo_ids: set[str] | None = None,
        *,
        db_type_lookup: dict[str, tuple[str, str]] | None = None,
    ) -> int:
        # Collect candidate IDs from all available sources
        cand_ids = set()

        if localconfig_helper:
            cand_ids.update(localconfig_helper.get_all_app_ids())

        if packageinfo_ids:
            cand_ids.update(packageinfo_ids)

        # Remove already-known games
        known_ids = set(self._games.keys())
        candidates = cand_ids - known_ids

        if not candidates:
            return 0

        count = 0
        fallback = set()

        for app_id in candidates:
            if db_type_lookup is not None:
                # Fast path: use pre-fetched DB data
                lookup = db_type_lookup.get(app_id)
                if not lookup:
                    fallback.add(app_id)
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

            # Use DB name only if it's a real name, otherwise try cache or fallback
            ename = db_name if not is_placeholder_name(db_name) else ""
            name = ename or self._get_cached_name(app_id) or t("ui.game_details.game_fallback", id=app_id)

            game = Game(app_id=app_id, name=name, app_type=app_type)
            self._games[app_id] = game
            count += 1

        # Fallback: resolve IDs not in DB via appinfo.vdf binary lookup
        if fallback and appinfo_manager:
            if not getattr(appinfo_manager, "appinfo", None):
                appinfo_manager.load_appinfo()
            for app_id in fallback:
                meta = appinfo_manager.get_app_metadata(app_id)
                app_type = meta.get("type", "").lower()
                name = meta.get("name", "")
                if app_type not in self._DISCOVERABLE_TYPES:
                    continue
                if not name or is_placeholder_name(name):
                    name = self._get_cached_name(app_id) or t("ui.game_details.game_fallback", id=app_id)
                game = Game(app_id=app_id, name=name, app_type=app_type)
                self._games[app_id] = game
                count += 1

        if count > 0:
            logger.info(t("logs.manager.discovered_missing", count=count))

        return count

    # set last_updated from appinfo.vdf
    def apply_appinfo_data(self, appinfo_data: dict) -> None:
        for app_id, data in appinfo_data.items():
            if app_id in self._games:
                if "common" in data and "last_updated" in data["common"]:
                    ts = data["common"]["last_updated"]
                    try:
                        # Centralised formatter handles int/str and locale automatically
                        self._games[app_id].last_updated = format_timestamp_to_date(ts)
                    except (ValueError, TypeError):
                        pass

    # apply binary appinfo + custom json overrides
    def apply_metadata_overrides(self, appinfo_manager) -> None:
        # Use already-loaded data; only load if not yet initialized
        if not appinfo_manager.steam_apps:
            appinfo_manager.load_appinfo()
        mods = appinfo_manager.modifications

        count = 0

        # Binary appinfo metadata
        for app_id, game in self._games.items():
            meta = appinfo_manager.get_app_metadata(app_id)

            # Set app_type from appinfo.vdf for all games
            if not game.app_type and meta.get("type"):
                game.app_type = meta["type"]

            # Fix placeholder names with real data from appinfo.vdf
            if is_placeholder_name(game.name) and meta.get("name"):
                game.name = meta["name"]
                if not game.name_overridden:
                    game.sort_name = game.name

            if not game.developer and meta.get("developer"):
                game.developer = meta["developer"]

            if not game.publisher and meta.get("publisher"):
                game.publisher = meta["publisher"]

            if not game.release_year and meta.get("release_date"):
                from steam_library_manager.utils.date_utils import to_timestamp

                ts = to_timestamp(meta["release_date"])
                if ts:
                    game.release_year = ts

            # Extract review percentage and metacritic score from appinfo.vdf
            if not game.review_percentage and meta.get("review_percentage"):
                game.review_percentage = int(meta["review_percentage"])

            if not game.metacritic_score and meta.get("metacritic_score"):
                game.metacritic_score = int(meta["metacritic_score"])

        # Custom overrides
        count += self._apply_overrides_to_games(mods)

        if count > 0:
            logger.info(t("logs.manager.applied_overrides", count=count))

    def apply_custom_overrides(self, modifications: dict[str, dict]) -> None:
        count = self._apply_overrides_to_games(modifications)
        if count > 0:
            logger.info(t("logs.manager.applied_overrides", count=count))

    # apply custom field overrides to games
    def _apply_overrides_to_games(self, modifications: dict[str, dict]) -> int:
        count = 0
        for app_id, md in modifications.items():
            if app_id in self._games:
                game = self._games[app_id]
                modified = md.get("modified", {})

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
                    from steam_library_manager.utils.date_utils import to_timestamp

                    ts = to_timestamp(modified["release_date"])
                    if ts:
                        game.release_year = ts
                if modified.get("pegi_rating"):
                    game.pegi_rating = modified["pegi_rating"]

                count += 1
        return count
