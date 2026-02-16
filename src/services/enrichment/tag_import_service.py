# src/services/enrichment/tag_import_service.py

"""Background worker for importing Steam tags from appinfo.vdf.

Parses the binary appinfo.vdf file in a background thread, extracts
store_tags (numeric TagIDs) for all games, resolves them to localized
names via TagResolver, and bulk-inserts into the game_tags table.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QThread, pyqtSignal

from src.utils.i18n import t

logger = logging.getLogger("steamlibmgr.tag_import_service")

__all__ = ["TagImportThread"]


class TagImportThread(QThread):
    """Background thread for extracting tags from appinfo.vdf.

    Signals:
        progress: Emitted for progress updates (message, current, total).
        finished_import: Emitted on completion (games_tagged, total_tags).
        error: Emitted on fatal errors (error_message).
    """

    progress = pyqtSignal(str, int, int)
    finished_import = pyqtSignal(int, int)
    error = pyqtSignal(str)

    def __init__(self, parent: Any = None) -> None:
        """Initializes the TagImportThread."""
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
        """Configure the import parameters.

        Args:
            steam_path: Path to Steam installation directory.
            db_path: Path to the metadata database.
            language: Language code for tag name resolution.
        """
        self._steam_path = steam_path
        self._db_path = db_path
        self._language = language

    def cancel(self) -> None:
        """Request cancellation of the import."""
        self._cancelled = True

    def run(self) -> None:
        """Execute the tag import in a background thread."""
        if not self._steam_path or not self._db_path:
            self.error.emit("Tag import not configured")
            return

        try:
            self._run_import()
        except Exception as exc:
            logger.exception("Tag import failed: %s", exc)
            self.error.emit(str(exc))

    def _run_import(self) -> None:
        """Parse appinfo.vdf and extract store_tags for all games."""
        from src.core.appinfo_manager import AppInfoManager
        from src.core.database import Database
        from src.utils.tag_resolver import TagResolver

        self.progress.emit(t("ui.tag_import.loading_appinfo"), 0, 0)

        # Load appinfo.vdf (the expensive operation)
        appinfo_mgr = AppInfoManager(self._steam_path)
        appinfo_mgr.load_appinfo()

        if not appinfo_mgr.appinfo or not appinfo_mgr.appinfo.apps:
            self.error.emit(t("ui.tag_import.no_appinfo"))
            return

        apps = appinfo_mgr.appinfo.apps
        total = len(apps)

        self.progress.emit(t("ui.tag_import.extracting", total=total), 0, total)

        # Open DB and ensure tag definitions are loaded
        db = Database(self._db_path)
        try:
            resolver = TagResolver(db)
            resolver.ensure_loaded()

            # Extract store_tags from each app
            batch: list[tuple[int, int, str]] = []
            games_with_tags = 0
            processed = 0

            for app_id, app_data in apps.items():
                if self._cancelled:
                    break

                processed += 1
                if processed % 500 == 0:
                    self.progress.emit(
                        t("ui.tag_import.progress", current=processed, total=total),
                        processed,
                        total,
                    )

                vdf_data = app_data.get("data", {})
                common = AppInfoManager._find_common_section(vdf_data)
                if not common:
                    continue

                store_tags = common.get("store_tags", {})
                if not store_tags or not isinstance(store_tags, dict):
                    continue

                # store_tags is {"0": "19", "1": "122", ...} or {"0": 19, "1": 122, ...}
                tag_ids = self._extract_tag_ids(store_tags)
                if not tag_ids:
                    continue

                games_with_tags += 1
                for tag_id in tag_ids:
                    name = resolver.resolve_tag_id(tag_id, self._language)
                    if name:
                        batch.append((app_id, tag_id, name))

                # Commit in batches of 5000 to avoid huge transactions
                if len(batch) >= 5000:
                    db.bulk_insert_game_tags_by_id(batch)
                    db.commit()
                    batch.clear()

            # Final batch
            if batch:
                db.bulk_insert_game_tags_by_id(batch)
                db.commit()

            total_tags = db.get_game_tag_count()
            logger.info(
                "Tag import complete: %d games tagged, %d total associations",
                games_with_tags,
                total_tags,
            )
            self.finished_import.emit(games_with_tags, total_tags)

        finally:
            db.close()

    @staticmethod
    def _extract_tag_ids(store_tags: dict) -> list[int]:
        """Extract numeric TagIDs from the store_tags dict.

        appinfo.vdf stores tags as {"0": "19", "1": "122"} or {"0": 19, "1": 122}.

        Args:
            store_tags: The store_tags dictionary from appinfo.vdf common section.

        Returns:
            List of numeric TagIDs.
        """
        tag_ids: list[int] = []
        for value in store_tags.values():
            try:
                tag_ids.append(int(value))
            except (ValueError, TypeError):
                continue
        return tag_ids
