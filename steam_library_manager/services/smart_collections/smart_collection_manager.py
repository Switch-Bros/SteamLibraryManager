#
# steam_library_manager/services/smart_collections/smart_collection_manager.py
# Smart Collection lifecycle manager: CRUD, evaluate, sync.
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#
# FIXME: this class is way too big, needs splitting

from __future__ import annotations

import logging

from steam_library_manager.services.smart_collections.evaluator import SmartCollectionEvaluator
from steam_library_manager.services.smart_collections.models import (
    SmartCollection,
    collection_from_json,
    collection_to_json,
)

logger = logging.getLogger("steamlibmgr.smart_collections.manager")

__all__ = ["SmartCollectionManager"]


class SmartCollectionManager:
    """Manages smart collections: CRUD, evaluate, sync."""

    def __init__(self, database, game_manager, category_service=None):
        # init manager
        self.database = database
        self.game_manager = game_manager
        self.category_service = category_service
        self.evaluator = SmartCollectionEvaluator()

    def create(self, collection: SmartCollection) -> int:
        # create new smart collection
        if not collection.name or not collection.name.strip():
            raise ValueError("name must not be empty")

        rules_json = collection_to_json(collection)
        cid = self.database.create_smart_collection(
            name=collection.name,
            description=collection.description,
            icon=collection.icon,
            rules_json=rules_json,
        )
        collection.collection_id = cid

        # evaluate and populate
        matching = self.evaluate_collection(collection)
        app_ids = [int(g.app_id) for g in matching]
        self.database.populate_smart_collection(cid, app_ids)
        self.database.commit()

        # sync to steam
        if collection.auto_sync:
            self.sync_to_steam(collection, [g.app_id for g in matching])

        logger.info("Created smart collection '%s' (id=%d) with %d games" % (collection.name, cid, len(matching)))
        self._save_sidecar()
        return cid

    def update(self, sc: SmartCollection) -> int:
        # update existing collection
        old_row = self.database.get_smart_collection(sc.collection_id)
        old_name = old_row["name"] if old_row else None

        rules_json = collection_to_json(sc)
        self.database.update_smart_collection(
            collection_id=sc.collection_id,
            name=sc.name,
            description=sc.description,
            icon=sc.icon,
            rules_json=rules_json,
        )

        # if name changed, cleanup old category
        if old_name and old_name != sc.name:
            self._remove_from_steam(old_name)

        # re-evaluate
        matching = self.evaluate_collection(sc)
        app_ids = [int(g.app_id) for g in matching]
        self.database.populate_smart_collection(sc.collection_id, app_ids)
        self.database.commit()

        if sc.auto_sync:
            self.sync_to_steam(sc, [g.app_id for g in matching])

        logger.info("Updated smart collection '%s' (id=%d) with %d games" % (sc.name, sc.collection_id, len(matching)))
        self._save_sidecar()
        return len(matching)

    def delete(self, collection_id: int) -> None:
        # delete collection
        row = self.database.get_smart_collection(collection_id)
        self.database.delete_smart_collection(collection_id)
        self.database.commit()

        if row and self.category_service:
            name = row["name"]
            self._remove_from_steam(name)

        logger.info("Deleted smart collection id=%d" % collection_id)
        self._save_sidecar()

    def get_all(self):
        # get all collections
        return [self._hydrate_row(row) for row in self.database.get_all_smart_collections()]

    def get_by_name(self, name: str):
        # find by name
        row = self.database.get_smart_collection_by_name(name)
        return self._hydrate_row(row) if row else None

    def exclude_game(self, collection_id: int, app_id: int) -> None:
        # exclude game from collection (survives re-eval)
        row = self.database.get_smart_collection(collection_id)
        if not row:
            return

        sc = self._hydrate_row(row)
        sc.excluded_app_ids.add(app_id)

        rules_json = collection_to_json(sc)
        self.database.update_smart_collection(
            collection_id=sc.collection_id,
            name=sc.name,
            description=sc.description,
            icon=sc.icon,
            rules_json=rules_json,
        )
        self.database.commit()

        if sc.auto_sync and self.category_service:
            self.category_service.remove_app_from_category(str(app_id), sc.name)

        logger.info("excluded app %d from '%s'" % (app_id, sc.name))
        self._save_sidecar()

    def include_game(self, collection_id, app_id):
        # remove exclusion
        row = self.database.get_smart_collection(collection_id)
        if not row:
            return

        sc = self._hydrate_row(row)
        sc.excluded_app_ids.discard(app_id)

        rules_json = collection_to_json(sc)
        self.database.update_smart_collection(
            collection_id=sc.collection_id,
            name=sc.name,
            description=sc.description,
            icon=sc.icon,
            rules_json=rules_json,
        )
        self.database.commit()
        logger.info("un-excluded app %d from '%s'" % (app_id, sc.name))
        self._save_sidecar()

    def evaluate_collection(self, collection):
        # evaluate rules against games
        all_games = self.game_manager.get_real_games()
        return self.evaluator.evaluate_batch(all_games, collection)

    def evaluate_all(self):
        # evaluate all active collections
        result = {}
        for sc in self.get_all():
            if sc.is_active:
                result[sc.name] = self.evaluate_collection(sc)
        return result

    def sync_to_steam(self, collection, matching_app_ids):
        # sync matching games to steam category
        if not self.category_service:
            return

        matching_set = set(matching_app_ids)
        current_games = self.game_manager.get_games_by_category(collection.name)
        current_ids = {g.app_id for g in current_games}

        # add new matches
        for aid in matching_set - current_ids:
            self.category_service.add_app_to_category(aid, collection.name)

        # remove non-matches
        for aid in current_ids - matching_set:
            self.category_service.remove_app_from_category(aid, collection.name)

    def sync_all_to_steam(self):
        # sync all active collections
        for sc in self.get_all():
            if sc.is_active and sc.auto_sync:
                matching = self.evaluate_collection(sc)
                app_ids = [int(g.app_id) for g in matching]
                self.database.populate_smart_collection(sc.collection_id, app_ids)
                self.sync_to_steam(sc, [g.app_id for g in matching])
        self.database.commit()

    def refresh(self):
        # refresh all collections
        result = {}
        for sc in self.get_all():
            if not sc.is_active:
                continue
            matching = self.evaluate_collection(sc)
            app_ids = [int(g.app_id) for g in matching]
            self.database.populate_smart_collection(sc.collection_id, app_ids)

            if sc.auto_sync:
                self.sync_to_steam(sc, [g.app_id for g in matching])

            result[sc.name] = len(matching)

        if result:
            self.database.commit()
            self._save_sidecar()
            logger.info("Refreshed %d smart collections: %s" % (len(result), result))
        return result

    @staticmethod
    def _sidecar_path():
        # get sidecar file path
        from steam_library_manager.config import config

        return config.DATA_DIR / "smart_collections.json"

    def _save_sidecar(self):
        # backup to json
        collections = self.get_all()
        path = self._sidecar_path()

        if not collections:
            if path.exists():
                path.unlink()
            return

        try:
            from steam_library_manager.utils.smart_collection_exporter import SmartCollectionExporter

            SmartCollectionExporter.export(collections, path)
        except Exception as exc:
            logger.warning("Failed to save sidecar: %s" % exc)

    def recover_from_sidecar(self):
        # restore from json if db empty
        if self.get_all():
            return 0

        path = self._sidecar_path()
        if not path.exists():
            return 0

        try:
            from steam_library_manager.utils.smart_collection_importer import SmartCollectionImporter

            collections = SmartCollectionImporter.import_collections(path)
        except (ValueError, FileNotFoundError) as exc:
            logger.warning("Sidecar recovery failed: %s" % exc)
            return 0

        if not collections:
            return 0

        recovered = 0
        for sc in collections:
            if self.database.get_smart_collection_by_name(sc.name):
                continue
            self.create(sc)
            recovered += 1

        if recovered:
            logger.info("Recovered %d smart collections from sidecar" % recovered)

        return recovered

    @staticmethod
    def _hydrate_row(row):
        # db row -> SmartCollection object
        sc = SmartCollection(
            collection_id=row["collection_id"],
            name=row["name"],
            description=row.get("description", ""),
            icon=row.get("icon", "\U0001f9e0"),
            created_at=row.get("created_at", 0),
        )
        rules_json = row.get("rules", "")
        if rules_json:
            collection_from_json(rules_json, sc)
        return sc

    def _remove_from_steam(self, category_name: str) -> None:
        # cleanup steam category
        if not self.category_service:
            return
        games = self.game_manager.get_games_by_category(category_name)
        for game in games:
            self.category_service.remove_app_from_category(game.app_id, category_name)
