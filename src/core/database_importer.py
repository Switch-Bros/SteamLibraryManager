"""Steam Library Manager - Database Importer.

Imports game metadata from appinfo.vdf into SQLite database.
Initial import is a ONE-TIME operation on first run, then incremental updates only.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from src.core.database import Database, DatabaseEntry, ImportStats
from src.utils.i18n import t

if TYPE_CHECKING:
    from src.core.appinfo_manager import AppInfoManager

logger = logging.getLogger("steamlibmgr.database_importer")

__all__ = ["DatabaseImporter", "create_initial_database"]


class DatabaseImporter:
    """Imports game metadata from appinfo.vdf into SQLite database.

    Workflow:
        1. Read apps from AppInfoManager.steam_apps
        2. Convert to DatabaseEntry objects
        3. Batch insert into SQLite
        4. Record import statistics
    """

    def __init__(self, database: Database, appinfo_manager: AppInfoManager):
        """Initialize importer.

        Args:
            database: Database instance.
            appinfo_manager: AppInfoManager instance for reading VDF data.
        """
        self.db = database
        self.appinfo_manager = appinfo_manager

    def needs_initial_import(self) -> bool:
        """Check if initial import is needed.

        Returns:
            True if database is empty.
        """
        return self.db.get_game_count() == 0

    def import_from_appinfo(
        self,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> ImportStats:
        """Import all games from appinfo.vdf.

        This is a ONE-TIME operation on first run.

        Args:
            progress_callback: Optional callback(current, total, message).

        Returns:
            Import statistics.
        """
        start_time = time.time()

        logger.info(t("logs.db.import_started"))
        logger.info(t("logs.db.import_one_time"))

        # Parse appinfo.vdf
        logger.info(t("logs.db.parsing"))
        if progress_callback:
            progress_callback(0, 100, t("logs.db.parsing"))

        # Get all apps from appinfo (dict[int, dict])
        all_apps = self.appinfo_manager.steam_apps
        total_apps = len(all_apps)

        logger.info(t("logs.db.found_apps", count=total_apps))

        # Pre-convert to list once for efficient batching
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

            # Batch insert without per-entry commit
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
        """Update only changed games.

        Args:
            changed_app_ids: Set of app IDs that changed.
            progress_callback: Optional callback(current, total, message).

        Returns:
            Import statistics.
        """
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
        """Convert appinfo data to DatabaseEntry.

        Args:
            app_id: Steam app ID.
            app_data: Raw data from appinfo.vdf (may contain nested 'data' key).

        Returns:
            DatabaseEntry object.
        """
        # Navigate to the actual data (appinfo.vdf structure may vary)
        vdf_data = app_data.get("data", app_data)

        # Find common section using AppInfoManager's logic
        common = self.appinfo_manager._find_common_section(vdf_data)

        # Basic info
        name = common.get("name", t("logs.db.unknown_app", app_id=app_id))
        app_type = common.get("type", "game")
        if isinstance(app_type, str):
            app_type = app_type.lower()

        # Developers & Publishers (using associations format from appinfo)
        developer = self._extract_associations(common, "developer")
        publisher = self._extract_associations(common, "publisher")

        # Fallback to direct fields
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

        # Release dates
        release_date = self._parse_release_date(common)

        # Extract genres safely
        genres = self._extract_genres(common)

        # Platform support
        platforms = self._extract_platforms(common)

        # Controller support
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
    def _extract_associations(common: dict, assoc_type: str) -> str:
        """Extract developer/publisher from associations block.

        Args:
            common: The common section from VDF data.
            assoc_type: 'developer' or 'publisher'.

        Returns:
            Comma-separated string of names, or empty string.
        """
        associations = common.get("associations", {})
        if not isinstance(associations, dict):
            return ""

        names = []
        for entry in associations.values():
            if isinstance(entry, dict):
                if entry.get("type") == assoc_type and entry.get("name"):
                    names.append(entry["name"])

        return ", ".join(names)

    @staticmethod
    def _parse_release_date(common: dict) -> int | None:
        """Parse release date from common section.

        Args:
            common: The common section from VDF data.

        Returns:
            UNIX timestamp or None.
        """
        # Try numeric timestamp first
        for key in ("steam_release_date", "original_release_date", "release_date"):
            val = common.get(key)
            if isinstance(val, (int, float)) and val > 0:
                return int(val)
            if isinstance(val, str) and val.isdigit() and int(val) > 0:
                return int(val)

        return None

    @staticmethod
    def _extract_genres(common: dict) -> list[str]:
        """Extract genre names from common section.

        Args:
            common: The common section from VDF data.

        Returns:
            List of genre name strings.
        """
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
        """Extract platform list from common section.

        Args:
            common: The common section from VDF data.

        Returns:
            List of platform strings.
        """
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
    """Create and populate initial database.

    Main entry point for first-time setup.

    Args:
        db_path: Path to database file.
        appinfo_manager: AppInfoManager instance.
        progress_callback: Optional progress callback.

    Returns:
        Initialized database.
    """
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
