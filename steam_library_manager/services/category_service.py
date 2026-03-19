#
# steam_library_manager/services/category_service.py
# Service layer for creating, renaming, and deleting categories
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from steam_library_manager.utils.i18n import t

__all__ = ["CategoryService"]


class CategoryService:
    """Manages category CRUD, merging, and dedup operations.
    Wraps CloudStorageParser and keeps in-memory games in sync.
    """

    def __init__(self, localconfig_helper, cloud_parser, game_manager):
        self.localconfig_helper = localconfig_helper
        self.cloud_parser = cloud_parser
        self.game_manager = game_manager

    def get_active_parser(self):
        # Return the currently active parser
        return self.cloud_parser

    def rename_category(self, old_name, new_name):
        # Rename a category across all parsers
        parser = self.get_active_parser()
        if not parser:
            return False

        if new_name in parser.get_all_categories():
            raise ValueError(t("ui.main_window.collection_exists", name=new_name))

        parser.rename_category(old_name, new_name)

        for game in self.game_manager.games.values():
            if old_name in game.categories:
                game.categories.remove(old_name)
                game.categories.append(new_name)

        return True

    def delete_category(self, category_name):
        # Delete a single category
        parser = self.get_active_parser()
        if not parser:
            return False

        parser.delete_category(category_name)

        for game in self.game_manager.games.values():
            if category_name in game.categories:
                game.categories.remove(category_name)

        return True

    def delete_multiple_categories(self, categories):
        # Delete multiple categories at once
        parser = self.get_active_parser()
        if not parser or not categories:
            return False

        for cat in categories:
            parser.delete_category(cat)
            for game in self.game_manager.games.values():
                if cat in game.categories:
                    game.categories.remove(cat)

        return True

    def is_collection_empty(self, category_name):
        # Check if a collection has no games
        return len(self.game_manager.get_games_by_category(category_name)) == 0

    def merge_categories(self, categories, target_category):
        # Merge multiple categories into one target
        parser = self.get_active_parser()
        if not parser or len(categories) < 2:
            return False

        sources = [c for c in categories if c != target_category]

        for src in sources:
            games_in_src = self.game_manager.get_games_by_category(src)
            for game in games_in_src:
                if target_category not in game.categories:
                    game.categories.append(target_category)
                    parser.add_app_category(game.app_id, target_category)
                if src in game.categories:
                    game.categories.remove(src)
                    parser.remove_app_category(game.app_id, src)
            parser.delete_category(src)

        return True

    def create_collection(self, name):
        # Create a new empty collection
        parser = self.get_active_parser()
        if not parser:
            return False

        if name in parser.get_all_categories():
            raise ValueError(t("ui.main_window.collection_exists", name=name))

        parser.create_empty_collection(name)
        return True

    def remove_duplicate_collections(self):
        # Remove duplicate collections WITHOUT merging games (Cloud Storage only).
        # WARNING: silently drops games from dupes. For user-facing ops,
        # use merge_duplicate_collections() with MergeDuplicatesDialog.
        if not self.cloud_parser:
            raise RuntimeError(t("ui.main_window.cloud_storage_only"))

        return self.cloud_parser.remove_duplicate_collections()

    def merge_duplicate_collections(self, merge_plan):
        # Merge duplicate collections based on user-selected plan
        if not self.cloud_parser:
            raise RuntimeError(t("ui.main_window.cloud_storage_only"))

        dup_groups = self.cloud_parser.get_duplicate_groups()
        merged = 0

        for name, keep_idx in merge_plan:
            if name not in dup_groups:
                continue

            colls = dup_groups[name]
            if keep_idx < 0 or keep_idx >= len(colls):
                continue

            keep = colls[keep_idx]
            keep_apps = keep.get("added", keep.get("apps", []))
            if not isinstance(keep_apps, list):
                keep_apps = []

            # Collect all app IDs from non-selected collections
            all_ids = set(keep_apps)
            for idx, coll in enumerate(colls):
                if idx == keep_idx:
                    continue
                apps = coll.get("added", coll.get("apps", []))
                if isinstance(apps, list):
                    all_ids.update(apps)

            keep["added"] = sorted(all_ids)

            # Remove non-selected collections from parser
            for idx, coll in enumerate(colls):
                if idx != keep_idx and coll in self.cloud_parser.collections:
                    col_id = coll.get("id", "")
                    if col_id:
                        self.cloud_parser._deleted_keys.add("user-collections.%s" % col_id)
                    self.cloud_parser.collections.remove(coll)

            self.cloud_parser.modified = True
            merged += 1

        if merged > 0:
            self._resync_cats()

        return merged

    def _resync_cats(self):
        # Rebuild in-memory game.categories from parser collections
        if not self.cloud_parser:
            return

        cat_map = {}
        for coll in self.cloud_parser.collections:
            cname = coll.get("name", "")
            if not cname:
                continue
            apps = coll.get("added", coll.get("apps", []))
            if not isinstance(apps, list):
                continue
            for aid_raw in apps:
                try:
                    aid = int(aid_raw)
                except (ValueError, TypeError):
                    continue
                cat_map.setdefault(aid, [])
                if cname not in cat_map[aid]:
                    cat_map[aid].append(cname)

        for game in self.game_manager.games.values():
            try:
                aid = int(game.app_id)
            except (ValueError, TypeError):
                continue
            game.categories = cat_map.get(aid, [])

    def get_all_categories(self):
        # Get all categories with game counts
        return self.game_manager.get_all_categories()

    def add_app_to_category(self, app_id, category):
        # Add an app to a category
        parser = self.get_active_parser()
        if not parser:
            return False

        parser.add_app_category(app_id, category)

        if app_id in self.game_manager.games:
            game = self.game_manager.games[app_id]
            if category not in game.categories:
                game.categories.append(category)

        return True

    def remove_app_from_category(self, app_id, category):
        # Remove an app from a category
        parser = self.get_active_parser()
        if not parser:
            return False

        parser.remove_app_category(app_id, category)

        if app_id in self.game_manager.games:
            game = self.game_manager.games[app_id]
            if category in game.categories:
                game.categories.remove(category)

        return True
