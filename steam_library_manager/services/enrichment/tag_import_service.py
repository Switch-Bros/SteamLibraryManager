#
# steam_library_manager/services/enrichment/tag_import_service.py
# Service to import Steam tags in bulk from the store API
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QThread, pyqtSignal

from steam_library_manager.utils.i18n import t

logger = logging.getLogger("steamlibmgr.tag_import_service")

__all__ = ["TagImportThread"]


class TagImportThread(QThread):
    """Background thread to slurp Steam tags into the DB.

    Reads appinfo.vdf (huge!), filters for games we actually own,
    then resolves tag IDs to localized names. Emits progress signals.
    """

    progress = pyqtSignal(str, int, int)
    finished_import = pyqtSignal(int, int)
    error = pyqtSignal(str)

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._cancelled: bool = False
        self._steam_path: Path | None = None
        self._db_path: Path | None = None
        self._language: str = "en"

    def configure(
        self,
        steam_path: Path,
        db_path: Path,
        language: str = "en",
    ) -> None:
        # setup paths before start()
        self._steam_path = steam_path
        self._db_path = db_path
        self._language = language

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        # main thread entry
        if not self._steam_path or not self._db_path:
            self.error.emit("Tag import not configured")
            return

        try:
            self._run_import()
        except Exception as exc:
            logger.exception("Tag import failed: %s", exc)
            self.error.emit(str(exc))

    def _run_import(self) -> None:
        # heavy lifting - parses vdf and writes to sqlite
        from steam_library_manager.core.appinfo_manager import AppInfoManager
        from steam_library_manager.core.database import Database
        from steam_library_manager.utils.tag_resolver import TagResolver

        self.progress.emit(t("ui.tag_import.loading_appinfo"), 0, 0)

        mgr = AppInfoManager(self._steam_path)
        mgr.load_appinfo()  # slow as hell on HDDs

        if not mgr.appinfo or not mgr.appinfo.apps:
            self.error.emit(t("ui.tag_import.no_appinfo"))
            return

        apps = mgr.appinfo.apps
        total = len(apps)
        self.progress.emit(t("ui.tag_import.extracting", total=total), 0, total)

        db = Database(self._db_path)
        try:
            res = TagResolver(db)
            res.ensure_loaded()

            # appinfo.vdf lists every app Valve knows about, but we only
            # care about games the user actually has in the library
            known_ids = db.get_all_app_ids()
            logger.info(
                "Filtering tags: %d apps in appinfo, %d in games table",
                total,
                len(known_ids),
            )

            batch = []
            rev_batch = []
            tagged = 0
            done = 0

            for app_id, app_data in apps.items():
                if self._cancelled:
                    break
                done += 1

                # throttle UI updates
                if done % 500 == 0:
                    self.progress.emit(
                        t("ui.tag_import.progress", current=done, total=total),
                        done,
                        total,
                    )

                if app_id not in known_ids:
                    continue  # skip - we don't own this

                vdf_data = app_data.get("data", {})
                common = AppInfoManager._find_common_section(vdf_data)
                if not common:
                    continue

                review_pct = common.get("review_percentage")
                if review_pct is not None:
                    try:
                        rev_batch.append((int(review_pct), app_id))
                    except (ValueError, TypeError):
                        pass  # whatever, corrupted data

                store_tags = common.get("store_tags", {})
                if not store_tags or not isinstance(store_tags, dict):
                    continue

                # values can be str or int depending on vdf version
                tag_ids = self._extract_tag_ids(store_tags)
                if not tag_ids:
                    continue

                tagged += 1
                for tag_id in tag_ids:
                    name = res.resolve_tag_id(tag_id, self._language)
                    if name:
                        batch.append((app_id, tag_id, name))

                # flush periodically to avoid giant transactions
                if len(batch) >= 5000:
                    db.bulk_insert_game_tags_by_id(batch)
                    db.commit()
                    batch.clear()

            if batch:
                db.bulk_insert_game_tags_by_id(batch)
                db.commit()

            if rev_batch:
                db.bulk_update_review_percentages(rev_batch)
                db.commit()
                logger.info("Updated review percentages for %d games" % len(rev_batch))

            total_tags = db.get_game_tag_count()
            logger.info(
                "Tag import done: %d games, %d tag associations",
                tagged,
                total_tags,
            )
            self.finished_import.emit(tagged, total_tags)

        finally:
            db.close()

    @staticmethod
    def _extract_tag_ids(store_tags: dict) -> list[int]:
        # pull numeric tag IDs out of store_tags
        # vdf quirk: tags can be str or int depending on version
        tag_ids: list[int] = []
        for value in store_tags.values():
            try:
                tag_ids.append(int(value))
            except (ValueError, TypeError):
                continue  # garbage data, skip
        return tag_ids
