"""Background enrichment worker for metadata updates.

Provides EnrichmentWorker (QObject) that runs HLTB and Steam API
enrichment in a QThread, emitting progress signals for the UI.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSignal

from src.utils.i18n import t

if TYPE_CHECKING:
    from src.integrations.hltb_api import HLTBClient

logger = logging.getLogger("steamlibmgr.enrichment_service")

__all__ = ["EnrichmentWorker"]


class EnrichmentWorker(QObject):
    """Background worker for metadata enrichment operations.

    Designed to run in a QThread. Emits progress and completion signals
    for UI updates. Supports cancellation via the cancel() method.

    Signals:
        progress: Emitted for each processed game (step_text, current, total).
        finished: Emitted when enrichment completes (success_count, failed_count).
        error: Emitted on fatal errors (error_message).
    """

    progress = pyqtSignal(str, int, int)
    finished = pyqtSignal(int, int)
    error = pyqtSignal(str)

    def __init__(self) -> None:
        """Initializes the EnrichmentWorker."""
        super().__init__()
        self._cancelled: bool = False

    def cancel(self) -> None:
        """Requests cancellation of the current enrichment operation."""
        self._cancelled = True

    def run_hltb_enrichment(
        self,
        games: list[tuple[int, str]],
        db_path: Path,
        hltb_client: HLTBClient,
    ) -> None:
        """Enriches games with HowLongToBeat completion time data.

        Opens its own database connection to avoid SQLite threading issues.

        Args:
            games: List of (app_id, name) tuples to enrich.
            db_path: Path to the SQLite database file.
            hltb_client: HLTB client for searching.
        """
        from src.core.database import Database

        self._cancelled = False
        total = len(games)
        success = 0
        failed = 0

        db = Database(db_path)
        try:
            for idx, (app_id, name) in enumerate(games):
                if self._cancelled:
                    break

                self.progress.emit(
                    t("ui.enrichment.progress", name=name, current=idx + 1, total=total),
                    idx + 1,
                    total,
                )

                try:
                    result = hltb_client.search_game(name)
                    if result and result.main_story > 0:
                        db.conn.execute(
                            """
                            INSERT OR REPLACE INTO hltb_data
                            (app_id, main_story, main_extras, completionist, last_updated)
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (
                                app_id,
                                result.main_story,
                                result.main_extras,
                                result.completionist,
                                int(time.time()),
                            ),
                        )
                        db.conn.commit()
                        success += 1
                    else:
                        failed += 1
                except Exception as exc:
                    logger.warning("HLTB enrichment failed for %d (%s): %s", app_id, name, exc)
                    failed += 1

                time.sleep(0.5)
        finally:
            db.close()

        self.finished.emit(success, failed)

    def run_steam_api_enrichment(
        self,
        games: list[tuple[int, str]],
        db_path: Path,
        api_key: str,
    ) -> None:
        """Enriches games with metadata from the Steam Web API.

        Opens its own database connection to avoid SQLite threading issues.

        Args:
            games: List of (app_id, name) tuples to enrich.
            db_path: Path to the SQLite database file.
            api_key: Steam Web API key.
        """
        from src.core.database import Database
        from src.integrations.steam_web_api import SteamWebAPI

        self._cancelled = False
        total = len(games)

        if not api_key:
            self.error.emit(t("ui.enrichment.no_api_key"))
            return

        try:
            api = SteamWebAPI(api_key)
        except ValueError as exc:
            self.error.emit(str(exc))
            return

        app_ids = [aid for aid, _ in games]
        success = 0
        failed = 0

        db = Database(db_path)
        try:
            batch_size = 50
            for batch_start in range(0, len(app_ids), batch_size):
                if self._cancelled:
                    break

                batch = app_ids[batch_start : batch_start + batch_size]
                current = min(batch_start + batch_size, total)

                batch_name = f"Batch {batch_start // batch_size + 1}"
                self.progress.emit(
                    t("ui.enrichment.progress", name=batch_name, current=current, total=total),
                    current,
                    total,
                )

                try:
                    details_map = api.get_app_details_batch(batch)

                    for aid, details in details_map.items():
                        update_fields: dict = {}
                        if details.name:
                            update_fields["name"] = details.name
                        if details.developers:
                            update_fields["developer"] = ", ".join(details.developers)
                        if details.publishers:
                            update_fields["publisher"] = ", ".join(details.publishers)
                        if details.review_score:
                            update_fields["review_score"] = details.review_score
                        if details.steam_release_date:
                            update_fields["steam_release_date"] = details.steam_release_date
                        if details.original_release_date:
                            update_fields["original_release_date"] = details.original_release_date

                        if update_fields:
                            db.upsert_game_metadata(aid, **update_fields)

                        if details.languages:
                            lang_dict = {
                                lang.lower().replace(" ", "_"): {
                                    "interface": True,
                                    "audio": False,
                                    "subtitles": False,
                                }
                                for lang in details.languages
                            }
                            db.upsert_languages(aid, lang_dict)

                        if details.genres:
                            db.conn.execute("DELETE FROM game_genres WHERE app_id = ?", (aid,))
                            db.conn.executemany(
                                "INSERT OR REPLACE INTO game_genres (app_id, genre) VALUES (?, ?)",
                                [(aid, g) for g in details.genres],
                            )

                        if details.tags:
                            db.conn.execute("DELETE FROM game_tags WHERE app_id = ?", (aid,))
                            db.conn.executemany(
                                "INSERT OR REPLACE INTO game_tags (app_id, tag) VALUES (?, ?)",
                                [(aid, tg) for tg in details.tags],
                            )

                        success += 1

                    db.conn.commit()

                except Exception as exc:
                    logger.warning("Steam API batch failed: %s", exc)
                    failed += len(batch)
        finally:
            db.close()

        self.finished.emit(success, failed)
