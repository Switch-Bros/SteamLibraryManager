"""Background enrichment worker for metadata updates.

Provides EnrichmentThread (BaseEnrichmentThread subclass) that runs HLTB
and Steam API enrichment in a background thread, emitting progress signals
for the UI.

HLTB mode uses the base class template pattern.
Steam API mode uses custom batch processing (overrides run dispatch).
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.services.enrichment.base_enrichment_thread import BaseEnrichmentThread
from src.utils.i18n import t

if TYPE_CHECKING:
    from src.integrations.hltb_api import HLTBClient

logger = logging.getLogger("steamlibmgr.enrichment_service")

__all__ = ["EnrichmentThread"]


class EnrichmentThread(BaseEnrichmentThread):
    """Background thread for metadata enrichment operations.

    Supports two modes:
    - HLTB: Per-game enrichment using the base class template pattern.
    - Steam API: Batch enrichment with custom run logic.

    Configure with configure_hltb() or configure_steam() before starting.
    """

    def __init__(self, parent: Any = None) -> None:
        """Initializes the EnrichmentThread."""
        super().__init__(parent)
        self._mode: str = ""
        self._games: list[tuple[int, str]] = []
        self._db_path: Path | None = None
        self._hltb_client: HLTBClient | None = None
        self._api_key: str = ""
        self._db: Any = None

    def configure_hltb(
        self,
        games: list[tuple[int, str]],
        db_path: Path,
        hltb_client: HLTBClient,
    ) -> None:
        """Configures the thread for HLTB enrichment.

        Args:
            games: List of (app_id, name) tuples to enrich.
            db_path: Path to the SQLite database file.
            hltb_client: HLTB client for searching.
        """
        self._mode = "hltb"
        self._games = games
        self._db_path = db_path
        self._hltb_client = hltb_client

    def configure_steam(
        self,
        games: list[tuple[int, str]],
        db_path: Path,
        api_key: str,
    ) -> None:
        """Configures the thread for Steam API enrichment.

        Args:
            games: List of (app_id, name) tuples to enrich.
            db_path: Path to the SQLite database file.
            api_key: Steam Web API key.
        """
        self._mode = "steam"
        self._games = games
        self._db_path = db_path
        self._api_key = api_key

    def run(self) -> None:
        """Dispatches to HLTB template or Steam custom implementation."""
        if self._mode == "hltb":
            super().run()
        elif self._mode == "steam":
            self._run_steam()

    # ── BaseEnrichmentThread hooks (HLTB mode) ─────────

    def _setup(self) -> None:
        """Opens the database connection for HLTB enrichment."""
        from src.core.database import Database

        self._db = Database(self._db_path)

    def _cleanup(self) -> None:
        """Closes the database connection."""
        if self._db:
            self._db.close()
            self._db = None

    def _get_items(self) -> list:
        """Returns the list of games to enrich."""
        return self._games

    def _process_item(self, item: Any) -> bool:
        """Enriches a single game with HLTB data.

        Args:
            item: Tuple of (app_id, name).

        Returns:
            True if meaningful HLTB times were found and stored.
        """
        app_id, name = item
        result = self._hltb_client.search_game(name, app_id)

        if result:
            has_times = any((result.main_story, result.main_extras, result.completionist))
            self._db.conn.execute(
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
            self._db.conn.commit()

            if has_times:
                return True

            logger.debug("HLTB matched '%s' but 0h times, saved as checked", name)
            return False

        logger.info("HLTB miss: %d '%s'", app_id, name)
        return False

    def _format_progress(self, item: Any, current: int, total: int) -> str:
        """Formats progress text with the game name.

        Args:
            item: Tuple of (app_id, name).
            current: 1-based current index.
            total: Total games count.

        Returns:
            Formatted progress string.
        """
        _app_id, name = item
        return t("ui.enrichment.progress", name=name, current=current, total=total)

    def _rate_limit(self) -> None:
        """Sleeps 200ms between HLTB requests."""
        time.sleep(0.2)

    # ── Steam API mode (custom batch processing) ───────

    def _run_steam(self) -> None:
        """Enriches games with metadata from the Steam Web API."""
        from src.core.database import Database
        from src.integrations.steam_web_api import SteamWebAPI

        self._cancelled = False
        total = len(self._games)

        if not self._api_key:
            self.error.emit(t("ui.enrichment.no_api_key"))
            return

        try:
            api = SteamWebAPI(self._api_key)
        except ValueError as exc:
            self.error.emit(str(exc))
            return

        app_ids = [aid for aid, _ in self._games]
        success = 0
        failed = 0

        db = Database(self._db_path)
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

        self.finished_enrichment.emit(success, failed)
