# src/ui/handlers/category_populator.py

"""Populates the sidebar category tree from game data.

Extracted from MainWindow to reduce its line count and isolate
the category-tree-building logic into a single, testable unit.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING

from src.core.game import Game
from src.utils.i18n import t

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow

__all__ = ["CategoryPopulator"]

# Maps app_type values from appinfo.vdf to i18n category keys
_TYPE_TO_CATEGORY_KEY: dict[str, str] = {
    "music": "categories.soundtracks",
    "tool": "categories.tools",
    "application": "categories.software",
    "video": "categories.videos",
}


class CategoryPopulator:
    """Builds and populates the sidebar category tree.

    Uses the same back-reference pattern as all other MainWindow handlers.

    Args:
        main_window: The MainWindow instance that owns this populator.
    """

    def __init__(self, main_window: MainWindow) -> None:
        self._mw = main_window

    @staticmethod
    def german_sort_key(text: str) -> str:
        """Sort key for German text with umlauts and special characters.

        Replaces German umlauts with their base letters for proper alphabetical sorting:
        A/a -> a, O/o -> o, U/u -> u, ss -> ss

        This ensures that "Ubernatuerlich" comes after "Uhr" (not at the end),
        and "NIEDLICH", "Niedlich", "niedlich" appear together.

        Args:
            text: The text to create a sort key for.

        Returns:
            Normalized lowercase string for sorting.
        """
        # Map umlauts to come AFTER their base letter:
        # a < ae, o < oe, u < ue (German alphabetical order)
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
        """Groups non-game apps by their app_type into virtual type categories.

        Only includes visible (non-hidden) apps. Empty categories are omitted.

        Args:
            all_apps: All apps including non-games.

        Returns:
            Ordered dict mapping localised category name to sorted game list.
        """
        buckets: dict[str, list[Game]] = {}
        for app in all_apps:
            if app.hidden:
                continue
            type_lower = app.app_type.lower() if app.app_type else ""
            cat_key = _TYPE_TO_CATEGORY_KEY.get(type_lower)
            if cat_key:
                cat_name = t(cat_key)
                buckets.setdefault(cat_name, []).append(app)

        # Sort games inside each bucket and return only non-empty ones
        result: dict[str, list[Game]] = {}
        for cat_name in sorted(buckets.keys()):
            result[cat_name] = sorted(buckets[cat_name], key=lambda g: g.sort_name.lower())
        return result

    def populate(self) -> None:
        """Refreshes the sidebar tree with current game data.

        Builds category data including All Games, Favorites (if non-empty),
        user categories, Uncategorized (if non-empty), and Hidden (if non-empty).

        Steam-compatible order:
        1. All Games (always shown)
        2. Favorites (only if non-empty)
        3. User Collections (alphabetically)
        4. Uncategorized (only if non-empty)
        5. Hidden (only if non-empty)

        No caching: the tree is cheap to rebuild (~50 ms for 2 500 games)
        and a cache only adds invisible staleness bugs.
        """
        mw = self._mw
        if not mw.game_manager:
            return

        # Apply view-menu filters (type, platform, status)
        all_games_raw = mw.game_manager.get_real_games()
        filtered_games = mw.filter_service.apply(all_games_raw)
        filtered_ids: set[str] = {g.app_id for g in filtered_games}

        # Separate hidden and visible games (within filtered set)
        visible_games = sorted([g for g in filtered_games if not g.hidden], key=lambda g: g.sort_name.lower())
        hidden_games = sorted([g for g in filtered_games if g.hidden], key=lambda g: g.sort_name.lower())

        # Favorites (sorted, non-hidden, within filtered set)
        favorites = sorted(
            [g for g in mw.game_manager.get_favorites() if not g.hidden and g.app_id in filtered_ids],
            key=lambda g: g.sort_name.lower(),
        )

        # Uncategorized games (within filtered set)
        uncategorized = sorted(
            [g for g in mw.game_manager.get_uncategorized_games() if not g.hidden and g.app_id in filtered_ids],
            key=lambda g: g.sort_name.lower(),
        )

        # Build categories_data in correct Steam order
        categories_data: OrderedDict[str, list[Game]] = OrderedDict()

        # 1. All Games (always shown)
        categories_data[t("categories.all_games")] = visible_games

        # 2. Favorites (only if non-empty)
        if favorites:
            categories_data[t("categories.favorites")] = favorites

        # 3. User categories (alphabetically sorted)
        cats: dict[str, int] = mw.game_manager.get_all_categories()

        # Merge in parser-owned collections that GameManager cannot see.
        # GameManager builds its list from game.categories only; an empty
        # collection has no games so it never appears there.  The parser is
        # the single source of truth for which collections actually exist.
        active_parser = mw.cloud_storage_parser or mw.localconfig_helper
        if active_parser:
            for parser_cat in active_parser.get_all_categories():
                if parser_cat not in cats:
                    cats[parser_cat] = 0  # empty collection — count is zero

        # Detect duplicate collection names from the parser
        duplicate_groups: dict[str, list[dict]] = {}
        if mw.cloud_storage_parser:
            duplicate_groups = mw.cloud_storage_parser.get_duplicate_groups()

        # Sort with German umlaut support
        # Skip special categories (Favorites, Uncategorized, Hidden, All Games, Type categories)
        special_categories = {
            t("categories.favorites"),
            t("categories.uncategorized"),
            t("categories.hidden"),
            t("categories.all_games"),
            t("categories.soundtracks"),
            t("categories.tools"),
            t("categories.software"),
            t("categories.videos"),
        }

        # duplicate_display_info maps internal key -> (real_name, index, total)
        duplicate_display_info: dict[str, tuple[str, int, int]] = {}

        for cat_name in sorted(cats.keys(), key=self.german_sort_key):
            if cat_name in special_categories:
                continue

            if cat_name in duplicate_groups:
                # Show each duplicate collection individually
                colls = duplicate_groups[cat_name]
                total = len(colls)
                for idx, coll in enumerate(colls):
                    apps = coll.get("added", coll.get("apps", []))
                    if not isinstance(apps, list):
                        apps = []
                    # Build game list from this specific collection's app IDs
                    app_id_set = set(apps)
                    coll_games: list[Game] = sorted(
                        [
                            g
                            for g in mw.game_manager.games.values()
                            if not g.hidden and int(g.app_id) in app_id_set and g.app_id in filtered_ids
                        ],
                        key=lambda g: g.sort_name.lower(),
                    )
                    dup_key = f"__dup__{cat_name}__{idx}"
                    categories_data[dup_key] = coll_games
                    duplicate_display_info[dup_key] = (cat_name, idx + 1, total)
            else:
                cat_games: list[Game] = sorted(
                    [
                        g
                        for g in mw.game_manager.get_games_by_category(cat_name)
                        if not g.hidden and g.app_id in filtered_ids
                    ],
                    key=lambda g: g.sort_name.lower(),
                )
                # Always add — empty collections must stay visible as "Name (0)"
                categories_data[cat_name] = cat_games

        # 4. Type categories (Soundtracks, Tools, Software, Videos)
        # Respect type filter: only show type categories whose filter is enabled
        _type_to_filter_key: dict[str, str] = {
            "music": "soundtracks",
            "tool": "tools",
            "application": "software",
            "video": "videos",
        }
        type_cats = self._get_type_categories(list(mw.game_manager.games.values()))
        for cat_name, cat_games_list in type_cats.items():
            # Find the filter key for this type category
            filter_key = None
            for app_type_val, fk in _type_to_filter_key.items():
                if t(_TYPE_TO_CATEGORY_KEY[app_type_val]) == cat_name:
                    filter_key = fk
                    break
            if filter_key and not mw.filter_service.is_type_category_visible(filter_key):
                continue
            # Also apply filtered_ids to type category games
            filtered_type_games = [g for g in cat_games_list if g.app_id in filtered_ids]
            if filtered_type_games:
                categories_data[cat_name] = filtered_type_games

        # 5. Uncategorized (only if non-empty)
        if uncategorized:
            categories_data[t("categories.uncategorized")] = uncategorized

        # 5. Hidden (only if non-empty)
        if hidden_games:
            categories_data[t("categories.hidden")] = hidden_games

        # Identify dynamic collections (have filterSpec)
        dynamic_collections: set[str] = set()
        if mw.cloud_storage_parser:
            for collection in mw.cloud_storage_parser.collections:
                if "filterSpec" in collection:
                    dynamic_collections.add(collection["name"])

        # Pass dynamic collections and duplicate info to tree
        mw.tree.populate_categories(categories_data, dynamic_collections, duplicate_display_info)
