#
# steam_library_manager/core/database_importer.py
# Imports game metadata from appinfo.vdf into the SQLite database
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

import logging
import time

from steam_library_manager.core.appinfo_manager import extract_associations
from steam_library_manager.core.database import Database, DatabaseEntry, ImportStats
from steam_library_manager.utils.i18n import t

logger = logging.getLogger("steamlibmgr.database_importer")

__all__ = ["DatabaseImporter", "create_initial_database"]


class DatabaseImporter:
    """Reads game metadata from appinfo.vdf, converts it to DatabaseEntry
    objects, and batch-inserts them into the SQLite database."""

    def __init__(self, database, appinfo_manager):
        self.db = database
        self.appinfo_manager = appinfo_manager

    def needs_initial_import(self):
        # true if database is empty
        return self.db.get_game_count() == 0

    def import_from_appinfo(self, progress_callback=None):
        # one-time import of all games from appinfo.vdf
        t0 = time.time()

        logger.info(t("logs.db.import_started"))
        logger.info(t("logs.db.import_one_time"))

        # parse appinfo.vdf
        logger.info(t("logs.db.parsing"))
        if progress_callback:
            progress_callback(0, 100, t("logs.db.parsing"))

        all_apps = self.appinfo_manager.steam_apps
        total = len(all_apps)

        logger.info(t("logs.db.found_apps", count=total))

        items = list(all_apps.items())

        imported = 0
        updated = 0
        failed = 0
        batch_sz = 100

        for i in range(0, total, batch_sz):
            batch = items[i : i + batch_sz]
            bnum = i // batch_sz + 1
            btotal = (total + batch_sz - 1) // batch_sz

            logger.debug(t("logs.db.importing_batch", current=bnum, total=btotal))
            if progress_callback:
                progress_callback(i, total, t("logs.db.importing_batch", current=bnum, total=btotal))

            entries = []
            for app_id, app_data in batch:
                try:
                    entry = self._convert_to_database_entry(app_id, app_data)
                    entries.append(entry)
                except (ValueError, KeyError, TypeError) as e:
                    logger.warning(t("logs.db.import_failed_app", app_id=app_id, error=str(e)))
                    failed += 1

            count = self.db.batch_insert_games(entries)
            imported += count

        dur = time.time() - t0

        stats = ImportStats(
            games_imported=imported,
            games_updated=updated,
            games_failed=failed,
            duration_seconds=dur,
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
        logger.info(t("logs.db.import_duration", duration="%.2f" % dur))

        if progress_callback:
            progress_callback(
                total, total, t("logs.db.import_complete", imported=imported, updated=updated, failed=failed)
            )

        return stats

    def incremental_update(self, changed_app_ids, progress_callback=None):
        # update only changed games
        t0 = time.time()
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

        dur = time.time() - t0

        stats = ImportStats(
            games_imported=imported,
            games_updated=updated,
            games_failed=failed,
            duration_seconds=dur,
            source="incremental_update",
        )

        self.db.record_import(stats)

        logger.info(t("logs.db.update_complete", duration="%.2f" % dur))

        if progress_callback:
            progress_callback(total, total, t("logs.db.update_complete", duration="%.2f" % dur))

        return stats

    def _convert_to_database_entry(self, app_id, app_data):
        # convert appinfo data to DatabaseEntry
        vdf = app_data.get("data", app_data)

        common = self.appinfo_manager._find_common_section(vdf)

        # basic info -- use empty string if no name in VDF
        name = common.get("name", "") or ""
        atype = common.get("type", "game")
        if isinstance(atype, str):
            atype = atype.lower()

        # developers & publishers (using associations format from appinfo)
        assoc = common.get("associations", {})
        dev = ", ".join(extract_associations(assoc, "developer"))
        pub = ", ".join(extract_associations(assoc, "publisher"))

        # fallback to direct fields
        if not dev:
            raw = common.get("developers", {})
            if isinstance(raw, dict):
                dev = ", ".join(str(v) for v in raw.values())
            elif isinstance(raw, (list, tuple)):
                dev = ", ".join(str(v) for v in raw)

        if not pub:
            raw = common.get("publishers", {})
            if isinstance(raw, dict):
                pub = ", ".join(str(v) for v in raw.values())
            elif isinstance(raw, (list, tuple)):
                pub = ", ".join(str(v) for v in raw)

        rel = self._parse_release_date(common)
        genres = self._extract_genres(common)
        platforms = self._extract_platforms(common)
        ctrl = common.get("controller_support", "none") or "none"

        return DatabaseEntry(
            app_id=app_id,
            name=name,
            app_type=atype,
            developer=dev or None,
            publisher=pub or None,
            release_date=rel,
            genres=genres,
            platforms=platforms,
            controller_support=ctrl,
            last_updated=int(time.time()),
        )

    @staticmethod
    def _parse_release_date(common):
        # parse release date from common section, returns UNIX timestamp or None
        for key in ("steam_release_date", "original_release_date", "release_date"):
            val = common.get(key)
            if isinstance(val, (int, float)) and val > 0:
                return int(val)
            if isinstance(val, str) and val.isdigit() and int(val) > 0:
                return int(val)

        return None

    @staticmethod
    def _extract_genres(common):
        # extract genre names from common section
        raw = common.get("genres", {})
        out = []

        if isinstance(raw, dict):
            for v in raw.values():
                if isinstance(v, dict):
                    desc = v.get("description")
                    if isinstance(desc, str):
                        out.append(desc)
                elif isinstance(v, str):
                    out.append(v)

        return out

    @staticmethod
    def _extract_platforms(common):
        # extract platform list from common section
        out = []
        oslist = common.get("oslist", "")
        if not isinstance(oslist, str):
            return out

        low = oslist.lower()
        if "windows" in low:
            out.append("windows")
        if "linux" in low:
            out.append("linux")
        if "mac" in low or "osx" in low:
            out.append("mac")

        return out


def create_initial_database(db_path, appinfo_manager, progress_callback=None):
    # create and populate initial database (main entry point for first-time setup)
    logger.info(t("logs.db.initializing"))

    db = Database(db_path)

    imp = DatabaseImporter(db, appinfo_manager)

    if not imp.needs_initial_import():
        n = db.get_game_count()
        logger.info(t("logs.db.already_initialized"))
        logger.info(t("logs.db.ready", count=n, duration="0.00"))
        return db

    logger.info(t("logs.db.import_one_time"))
    stats = imp.import_from_appinfo(progress_callback)

    total = stats.games_imported + stats.games_updated
    logger.info(t("logs.db.ready", count=total, duration="%.2f" % stats.duration_seconds))

    return db
