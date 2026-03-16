#
# steam_library_manager/core/database_importer.py
# Imports game metadata from appinfo.vdf into the SQLite database
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from steam_library_manager.core.appinfo_manager import extract_associations
from steam_library_manager.core.database import Database, DatabaseEntry, ImportStats
from steam_library_manager.utils.i18n import t

if TYPE_CHECKING:
    from steam_library_manager.core.appinfo_manager import AppInfoManager

logger = logging.getLogger("steamlibmgr.database_importer")

__all__ = ["DatabaseImporter", "create_initial_database"]


class DatabaseImporter:
    """Imports game metadata from appinfo.vdf into SQLite."""

    def __init__(self, database: Database, appinfo_manager: AppInfoManager):
        self.db = database
        self.appinfo_manager = appinfo_manager

    def needs_initial_import(self) -> bool:
        """True if the database is empty."""
        return self.db.get_game_count() == 0

    def import_from_appinfo(
        self,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> ImportStats:
        """One-time full import of all games from appinfo.vdf."""
        start_time = time.time()

        logger.info(t("logs.db.import_started"))
        logger.info(t("logs.db.import_one_time"))

        logger.info(t("logs.db.parsing"))
        if progress_callback:
            progress_callback(0, 100, t("logs.db.parsing"))

        all_apps = self.appinfo_manager.steam_apps
        total_apps = len(all_apps)

        logger.info(t("logs.db.found_apps", count=total_apps))

        app_items = list(all_apps.items())

        imported = 0
        updated = 0
        failed = 0
        batch_size = 100

        for i in range(0, total_apps, batch_size):
            batch = app_items[i : i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total_apps + batch_size - 1) // batch_size

            logger.debug(t("logs.db.importing_batch", current=batch_num, total=total_batches))
            if progress_callback:
                progress_callback(i, total_apps, t("logs.db.importing_batch", current=batch_num, total=total_batches))

            entries: list[DatabaseEntry] = []
            for app_id, app_data in batch:
                try:
                    entry = self._convert_to_database_entry(app_id, app_data)
                    entries.append(entry)
                except (ValueError, KeyError, TypeError) as e:
                    logger.warning(t("logs.db.import_failed_app", app_id=app_id, error=str(e)))
                    failed += 1

            count = self.db.batch_insert_games(entries)
            imported += count

        duration = time.time() - start_time

        stats = ImportStats(
            games_imported=imported,
            games_updated=updated,
            games_failed=failed,
            duration_seconds=duration,
            source="appinfo.vdf",
        )

        self.db.record_import(stats)

        logger.info(
            t(
                "logs.db.import_complete",
                imported=imported,
                updated=updated,
                failed=failed,
            )
        )
        logger.info(t("logs.db.import_duration", duration=f"{duration:.2f}"))

        if progress_callback:
            progress_callback(
                total_apps, total_apps, t("logs.db.import_complete", imported=imported, updated=updated, failed=failed)
            )

        return stats

    def incremental_update(
        self,
        changed_app_ids: set[int],
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> ImportStats:
        """Re-import only the given app IDs (changed since last sync)."""
        start_time = time.time()
        total = len(changed_app_ids)

        logger.info(t("logs.db.update_started", count=total))

        updated = 0
        imported = 0
        failed = 0

        for i, app_id in enumerate(changed_app_ids):
            if progress_callback and i % 10 == 0:
                progress_callback(i, total, t("logs.db.importing_batch", current=i, total=total))

            try:
                app_data = self.appinfo_manager.steam_apps.get(app_id)
                if not app_data:
                    continue

                entry = self._convert_to_database_entry(app_id, app_data)

                existing = self.db.get_game(app_id)
                if existing:
                    self.db.update_game(entry)
                    updated += 1
                else:
                    self.db.insert_game(entry)
                    imported += 1

            except (ValueError, KeyError, TypeError) as e:
                logger.warning(t("logs.db.import_failed_app", app_id=app_id, error=str(e)))
                failed += 1

        self.db.commit()

        duration = time.time() - start_time

        stats = ImportStats(
            games_imported=imported,
            games_updated=updated,
            games_failed=failed,
            duration_seconds=duration,
            source="incremental_update",
        )

        self.db.record_import(stats)

        logger.info(t("logs.db.update_complete", duration=f"{duration:.2f}"))

        if progress_callback:
            progress_callback(total, total, t("logs.db.update_complete", duration=f"{duration:.2f}"))

        return stats

    def _convert_to_database_entry(self, app_id: int, app_data: dict) -> DatabaseEntry:
        """Convert raw appinfo dict to a DatabaseEntry."""
        vdf_data = app_data.get("data", app_data)

        common = self.appinfo_manager._find_common_section(vdf_data)

        name = common.get("name", "") or ""
        app_type = common.get("type", "game")
        if isinstance(app_type, str):
            app_type = app_type.lower()

        associations = common.get("associations", {})
        developer = ", ".join(extract_associations(associations, "developer"))
        publisher = ", ".join(extract_associations(associations, "publisher"))

        if not developer:
            dev_raw = common.get("developers", {})
            if isinstance(dev_raw, dict):
                developer = ", ".join(str(v) for v in dev_raw.values())
            elif isinstance(dev_raw, (list, tuple)):
                developer = ", ".join(str(v) for v in dev_raw)

        if not publisher:
            pub_raw = common.get("publishers", {})
            if isinstance(pub_raw, dict):
                publisher = ", ".join(str(v) for v in pub_raw.values())
            elif isinstance(pub_raw, (list, tuple)):
                publisher = ", ".join(str(v) for v in pub_raw)

        release_date = self._parse_release_date(common)
        genres = self._extract_genres(common)
        platforms = self._extract_platforms(common)
        controller_support = common.get("controller_support", "none") or "none"

        return DatabaseEntry(
            app_id=app_id,
            name=name,
            app_type=app_type,
            developer=developer or None,
            publisher=publisher or None,
            release_date=release_date,
            genres=genres,
            platforms=platforms,
            controller_support=controller_support,
            last_updated=int(time.time()),
        )

    @staticmethod
    def _parse_release_date(common: dict) -> int | None:
        for key in ("steam_release_date", "original_release_date", "release_date"):
            val = common.get(key)
            if isinstance(val, (int, float)) and val > 0:
                return int(val)
            if isinstance(val, str) and val.isdigit() and int(val) > 0:
                return int(val)

        return None

    @staticmethod
    def _extract_genres(common: dict) -> list[str]:
        genres_raw = common.get("genres", {})
        genres: list[str] = []

        if isinstance(genres_raw, dict):
            for v in genres_raw.values():
                if isinstance(v, dict):
                    desc = v.get("description")
                    if isinstance(desc, str):
                        genres.append(desc)
                elif isinstance(v, str):
                    genres.append(v)

        return genres

    @staticmethod
    def _extract_platforms(common: dict) -> list[str]:
        platforms: list[str] = []
        oslist = common.get("oslist", "")
        if not isinstance(oslist, str):
            return platforms

        oslist_lower = oslist.lower()
        if "windows" in oslist_lower:
            platforms.append("windows")
        if "linux" in oslist_lower:
            platforms.append("linux")
        if "mac" in oslist_lower or "osx" in oslist_lower:
            platforms.append("mac")

        return platforms


def create_initial_database(
    db_path: Path,
    appinfo_manager: AppInfoManager,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> Database:
    """Create and populate the database on first run."""
    logger.info(t("logs.db.initializing"))

    db = Database(db_path)

    importer = DatabaseImporter(db, appinfo_manager)

    if not importer.needs_initial_import():
        count = db.get_game_count()
        logger.info(t("logs.db.already_initialized"))
        logger.info(t("logs.db.ready", count=count, duration="0.00"))
        return db

    logger.info(t("logs.db.import_one_time"))
    stats = importer.import_from_appinfo(progress_callback)

    total = stats.games_imported + stats.games_updated
    logger.info(t("logs.db.ready", count=total, duration=f"{stats.duration_seconds:.2f}"))

    return db
