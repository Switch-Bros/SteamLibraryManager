#
# steam_library_manager/ui/handlers/category_populator.py
# Populates the sidebar category tree from game data
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING

from steam_library_manager.core.game import Game
from steam_library_manager.integrations.external_games.models import get_collection_emoji
from steam_library_manager.utils.i18n import t

if TYPE_CHECKING:
    from steam_library_manager.ui.main_window import MainWindow

__all__ = ["CategoryPopulator"]

# Maps app_type values from appinfo.vdf to i18n category keys
_TYPE_TO_CATEGORY_KEY: dict[str, str] = {
    "music": "categories.soundtracks",
    "tool": "categories.tools",
    "application": "categories.software",
    "video": "categories.videos",
}


class CategoryPopulator:
    """Builds and populates the sidebar category tree."""

    def __init__(self, main_window: MainWindow) -> None:
        self._mw = main_window

    @staticmethod
    def german_sort_key(text: str) -> str:
        """Sort key that maps German umlauts to their base letter for alphabetical order."""
        replacements = {
            "\u00e4": "a~",
            "\u00c4": "a~",
            "\u00f6": "o~",
            "\u00d6": "o~",
            "\u00fc": "u~",
            "\u00dc": "u~",
            "\u00df": "ss",
        }
        result = text.lower()
        for old, new in replacements.items():
            result = result.replace(old, new)
        return result

    @staticmethod
    def _get_type_categories(all_apps: list[Game]) -> dict[str, list[Game]]:
        """Groups visible non-game apps by app_type (soundtracks, tools, etc.)."""
        buckets: dict[str, list[Game]] = {}
        for app in all_apps:
            if app.hidden:
                continue
            type_lower = app.app_type.lower() if app.app_type else ""
            cat_key = _TYPE_TO_CATEGORY_KEY.get(type_lower)
            if cat_key:
                cat_name = t(cat_key)
                buckets.setdefault(cat_name, []).append(app)

        result: dict[str, list[Game]] = {}
        for cat_name in sorted(buckets.keys()):
            result[cat_name] = sorted(buckets[cat_name], key=lambda g: g.sort_name.lower())
        return result

    def populate(self) -> None:
        """Refreshes the sidebar tree with current game data.

        Steam-compatible order: All Games, Favorites, User Collections,
        Uncategorized, Hidden. No caching - rebuild is ~50ms for 2500 games.
        """
        mw = self._mw
        if not mw.game_manager:
            return

        all_games_raw = mw.game_manager.get_real_games()
        filtered_games = mw.filter_service.apply(all_games_raw)
        filtered_ids: set[str] = {g.app_id for g in filtered_games}

        sort_fn = mw.filter_service.sort_games

        visible_games = sort_fn([g for g in filtered_games if not g.hidden])
        hidden_games = sort_fn([g for g in filtered_games if g.hidden])

        favorites = sort_fn(
            [g for g in mw.game_manager.get_favorites() if not g.hidden and g.app_id in filtered_ids],
        )

        # Smart Collections are SLM-local, so their games count as "uncategorized"
        # from Steam's perspective. Collect names before the uncategorized check.
        smart_collections: set[str] = set()
        if hasattr(mw, "smart_collection_manager") and mw.smart_collection_manager:
            for sc in mw.smart_collection_manager.get_all():
                smart_collections.add(sc.name)

        uncategorized = sort_fn(
            [
                g
                for g in mw.game_manager.get_uncategorized_games(smart_collections)
                if not g.hidden and g.app_id in filtered_ids
            ],
        )

        categories_data: OrderedDict[str, list[Game]] = OrderedDict()

        # All Games (always shown)
        categories_data[t("categories.all_games")] = visible_games

        # Favorites
        if favorites:
            categories_data[t("categories.favorites")] = favorites

        # User categories (alphabetically sorted)
        cats: dict[str, int] = mw.game_manager.get_all_categories()

        # Merge in parser-owned collections that GameManager cannot see.
        # GameManager builds its list from game.categories only; an empty
        # collection has no games so it never appears there.  The parser is
        # the single source of truth for which collections actually exist.
        active_parser = mw.cloud_storage_parser or mw.localconfig_helper
        if active_parser:
            for parser_cat in active_parser.get_all_categories():
                if parser_cat not in cats:
                    cats[parser_cat] = 0

        # Detect duplicate collection names from the parser
        duplicate_groups: dict[str, list[dict]] = {}
        if mw.cloud_storage_parser:
            duplicate_groups = mw.cloud_storage_parser.get_duplicate_groups()

        from steam_library_manager.ui.constants import get_protected_collection_names

        special_categories = get_protected_collection_names() | {
            t("categories.soundtracks"),
            t("categories.tools"),
            t("categories.software"),
            t("categories.videos"),
        }

        duplicate_display_info: dict[str, tuple[str, int, int]] = {}

        for cat_name in sorted(cats.keys(), key=self.german_sort_key):
            if cat_name in special_categories:
                continue

            if cat_name in duplicate_groups:
                colls = duplicate_groups[cat_name]
                total = len(colls)
                for idx, coll in enumerate(colls):
                    apps = coll.get("added", coll.get("apps", []))
                    if not isinstance(apps, list):
                        apps = []
                    app_id_set = set(apps)
                    coll_games: list[Game] = sort_fn(
                        [
                            g
                            for g in mw.game_manager.games.values()
                            if not g.hidden and int(g.app_id) in app_id_set and g.app_id in filtered_ids
                        ],
                    )
                    dup_key = f"__dup__{cat_name}__{idx}"
                    categories_data[dup_key] = coll_games
                    duplicate_display_info[dup_key] = (cat_name, idx + 1, total)
            else:
                cat_games: list[Game] = sort_fn(
                    [
                        g
                        for g in mw.game_manager.get_games_by_category(cat_name)
                        if not g.hidden and g.app_id in filtered_ids
                    ],
                )
                # Empty collections stay visible as "Name (0)"
                categories_data[cat_name] = cat_games

        # Type categories - only show if their filter is enabled
        _type_to_filter_key: dict[str, str] = {
            "music": "soundtracks",
            "tool": "tools",
            "application": "software",
            "video": "videos",
        }
        type_cats = self._get_type_categories(list(mw.game_manager.games.values()))
        for cat_name, cat_games_list in type_cats.items():
            filter_key = None
            for app_type_val, fk in _type_to_filter_key.items():
                if t(_TYPE_TO_CATEGORY_KEY[app_type_val]) == cat_name:
                    filter_key = fk
                    break
            if filter_key and not mw.filter_service.is_type_category_visible(filter_key):
                continue
            filtered_type_games = [g for g in cat_games_list if g.app_id in filtered_ids]
            if filtered_type_games:
                categories_data[cat_name] = filtered_type_games

        # Uncategorized
        if uncategorized:
            categories_data[t("categories.uncategorized")] = uncategorized

        # Hidden
        if hidden_games:
            categories_data[t("categories.hidden")] = hidden_games

        # Dynamic collections (have filterSpec)
        dynamic_collections: set[str] = set()
        if mw.cloud_storage_parser:
            for collection in mw.cloud_storage_parser.collections:
                if "filterSpec" in collection:
                    dynamic_collections.add(collection["name"])

        # External platform collections (ROM systems, platform parsers)
        external_platform_collections: set[str] = set()
        for cat_name_check in categories_data:
            if get_collection_emoji(cat_name_check):
                external_platform_collections.add(cat_name_check)

        mw.tree.populate_categories(
            categories_data,
            dynamic_collections,
            duplicate_display_info,
            smart_collections,
            external_platform_collections,
        )
