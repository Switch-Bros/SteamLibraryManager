#
# steam_library_manager/services/enrichment/enrich_all_coordinator.py
# Coordinator for running all enrichment tracks in parallel
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSignal

if TYPE_CHECKING:
    from pathlib import Path

    from steam_library_manager.core.game import Game
    from steam_library_manager.integrations.hltb_api import HLTBClient

logger = logging.getLogger("steamlibmgr.enrich_all")

__all__ = ["EnrichAllCoordinator"]

TRACK_TAGS = "tags"
TRACK_STEAM = "steam"
TRACK_HLTB = "hltb"
TRACK_PROTONDB = "protondb"
TRACK_DECK = "deck"
TRACK_PEGI = "pegi"
TRACK_CURATOR = "curator"


class EnrichAllCoordinator(QObject):
    """Coordinates parallel execution of all enrichment tracks."""

    track_progress = pyqtSignal(str, int, int)
    track_finished = pyqtSignal(str, int, int)
    all_finished = pyqtSignal(dict)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._threads: dict[str, object] = {}
        self._results: dict[str, tuple[int, int]] = {}
        self._pending_tracks: int = 0
        self._cancelled: bool = False

        self._db_path: Path | None = None
        self._api_key: str = ""
        self._steam_id: str = ""
        self._steam_path: Path | None = None
        self._games_deck: list[Game] = []
        self._games_db: list[tuple[int, str]] = []
        self._hltb_client: HLTBClient | None = None
        self._language: str = "en"
        self._cache_dir: Path | None = None
        self._games_pegi: list[tuple[int, str]] = []

    def configure(
        self,
        db_path: Path,
        api_key: str,
        steam_id: str,
        steam_path: Path | None,
        games_deck: list[Game],
        games_db: list[tuple[int, str]],
        hltb_client: HLTBClient | None,
        language: str,
        cache_dir: Path,
        games_pegi: list[tuple[int, str]] | None = None,
    ) -> None:
        """Configure all enrichment tracks before calling start()."""
        self._db_path = db_path
        self._api_key = api_key
        self._steam_id = steam_id
        self._steam_path = steam_path
        self._games_deck = games_deck
        self._games_db = games_db
        self._hltb_client = hltb_client
        self._language = language
        self._cache_dir = cache_dir
        self._games_pegi = games_pegi or []

    def start(self) -> None:
        """Start the enrichment pipeline (Phase 0 then Phase 1)."""
        if self._steam_path and self._db_path:
            self._start_tag_import()
        else:
            self.track_finished.emit(TRACK_TAGS, -1, 0)
            self._start_parallel_tracks()

    def cancel(self) -> None:
        """Requests cancellation of all running threads."""
        self._cancelled = True
        for thread in self._threads.values():
            if hasattr(thread, "cancel"):
                thread.cancel()  # type: ignore[union-attr]

    # Phase 0: Tag import

    def _start_tag_import(self) -> None:
        """Phase 0: Starts tag import from appinfo.vdf."""
        from steam_library_manager.services.enrichment.tag_import_service import TagImportThread

        thread = TagImportThread(self)
        thread.configure(
            self._steam_path,  # type: ignore[arg-type]
            self._db_path,  # type: ignore[arg-type]
            self._language,
        )

        thread.progress.connect(lambda _text, cur, tot: self.track_progress.emit(TRACK_TAGS, cur, tot))
        thread.finished_import.connect(self._on_tags_finished)
        thread.error.connect(self._on_tags_error)

        self._threads[TRACK_TAGS] = thread
        thread.start()

    def _on_tags_finished(self, games_tagged: int, _total_tags: int) -> None:
        """Handle tag import completion, then start parallel tracks."""
        self._results[TRACK_TAGS] = (games_tagged, 0)
        self.track_finished.emit(TRACK_TAGS, games_tagged, 0)
        if not self._cancelled:
            self._start_parallel_tracks()

    def _on_tags_error(self, message: str) -> None:
        """Handle tag import error and continue with parallel tracks."""
        logger.warning("Tag import failed: %s", message)
        self._results[TRACK_TAGS] = (0, 1)
        self.track_finished.emit(TRACK_TAGS, 0, 1)
        if not self._cancelled:
            self._start_parallel_tracks()

    # Phase 1: Parallel tracks

    def _start_parallel_tracks(self) -> None:
        """Start all applicable parallel enrichment tracks."""
        self._pending_tracks = 0

        # Track A: Steam API (metadata + achievements)
        if self._api_key and self._games_db and self._db_path:
            self._pending_tracks += 1
            self._start_steam_track()
        else:
            self.track_finished.emit(TRACK_STEAM, -1, 0)

        # Track B: HLTB
        if self._hltb_client and self._games_db and self._db_path:
            self._pending_tracks += 1
            self._start_hltb_track()
        else:
            self.track_finished.emit(TRACK_HLTB, -1, 0)

        # Track C: ProtonDB
        if self._games_db and self._db_path:
            self._pending_tracks += 1
            self._start_protondb_track()
        else:
            self.track_finished.emit(TRACK_PROTONDB, -1, 0)

        # Track D: Deck status
        if self._games_deck and self._cache_dir:
            self._pending_tracks += 1
            self._start_deck_track()
        else:
            self.track_finished.emit(TRACK_DECK, -1, 0)

        # Track E: PEGI age ratings — chained after Steam API track
        # (batch API fills most PEGI values, gap filler handles the rest)
        # Only emit skip if PEGI has no data OR Steam track won't chain it
        if not (self._games_pegi and self._db_path):
            self._results[TRACK_PEGI] = (-1, 0)
            self.track_finished.emit(TRACK_PEGI, -1, 0)
        elif not (self._api_key and self._games_db and self._db_path):
            # Steam track won't run, so PEGI won't be chained — run it directly
            self._pending_tracks += 1
            self._start_pegi_track()

        # Track G: Curator recommendations
        if self._db_path:
            curators = self._get_curators_for_refresh()
            if curators:
                self._pending_tracks += 1
                self._start_curator_track(curators)
            else:
                self.track_finished.emit(TRACK_CURATOR, -1, 0)
        else:
            self.track_finished.emit(TRACK_CURATOR, -1, 0)

        if self._pending_tracks == 0:
            self.all_finished.emit(self._results)

    # Track A: Steam API (metadata -> achievements)

    def _start_steam_track(self) -> None:
        """Start Steam API metadata enrichment, chains to achievements."""
        from steam_library_manager.services.enrichment.enrichment_service import EnrichmentThread

        thread = EnrichmentThread(self)
        thread.configure_steam(
            self._games_db,
            self._db_path,  # type: ignore[arg-type]
            self._api_key,
            force_refresh=True,
        )

        thread.progress.connect(lambda _t, cur, tot: self.track_progress.emit(TRACK_STEAM, cur, tot))
        thread.finished_enrichment.connect(self._on_steam_metadata_finished)
        thread.error.connect(lambda msg: self._on_track_error(TRACK_STEAM, msg))

        self._threads[TRACK_STEAM] = thread
        thread.start()

    def _on_steam_metadata_finished(self, success: int, failed: int) -> None:
        """Chain from Steam metadata to achievement enrichment."""
        self._results[f"{TRACK_STEAM}_metadata"] = (success, failed)

        if self._cancelled or not self._steam_id or not self._db_path:
            self._results[TRACK_STEAM] = (success, failed)
            self.track_finished.emit(TRACK_STEAM, success, failed)
            self._on_track_complete()
            return

        self._start_achievement_phase(success, failed)

    def _start_achievement_phase(self, meta_success: int, meta_failed: int) -> None:
        """Start achievement enrichment as second phase of Steam track."""
        from steam_library_manager.services.enrichment.achievement_enrichment_service import (
            AchievementEnrichmentThread,
        )

        thread = AchievementEnrichmentThread(self)
        thread.configure(
            self._games_db,
            self._db_path,  # type: ignore[arg-type]
            self._api_key,
            self._steam_id,
            force_refresh=True,
        )

        thread.progress.connect(lambda _t, cur, tot: self.track_progress.emit(TRACK_STEAM, cur, tot))
        thread.finished_enrichment.connect(lambda s, f: self._on_steam_track_done(meta_success, meta_failed, s, f))
        thread.error.connect(lambda msg: self._on_track_error(TRACK_STEAM, msg))

        self._threads[f"{TRACK_STEAM}_ach"] = thread
        thread.start()

    def _on_steam_track_done(
        self,
        meta_success: int,
        meta_failed: int,
        ach_success: int,
        ach_failed: int,
    ) -> None:
        """Handle completion of the full Steam track, then chain PEGI."""
        total_success = meta_success + ach_success
        total_failed = meta_failed + ach_failed
        self._results[TRACK_STEAM] = (total_success, total_failed)
        self.track_finished.emit(TRACK_STEAM, total_success, total_failed)

        # Chain PEGI gap filler after Steam API (batch already filled most)
        if not self._cancelled and self._games_pegi and self._db_path:
            self._pending_tracks += 1
            self._start_pegi_track()
        elif self._games_pegi and self._db_path:
            # Cancelled — report PEGI as skipped and count it as complete
            self._results[TRACK_PEGI] = (0, 0)
            self.track_finished.emit(TRACK_PEGI, 0, 0)

        self._on_track_complete()

    # Track B: HLTB

    def _start_hltb_track(self) -> None:
        """Starts HLTB enrichment track."""
        from steam_library_manager.services.enrichment.enrichment_service import EnrichmentThread

        thread = EnrichmentThread(self)
        thread.configure_hltb(
            self._games_db,
            self._db_path,  # type: ignore[arg-type]
            self._hltb_client,  # type: ignore[arg-type]
            steam_user_id=self._steam_id,
            force_refresh=True,
        )
        self._wire_and_start_track(TRACK_HLTB, thread)

    # Track C: ProtonDB

    def _start_protondb_track(self) -> None:
        """Starts ProtonDB enrichment track."""
        from steam_library_manager.services.enrichment.protondb_enrichment_service import (
            ProtonDBEnrichmentThread,
        )

        thread = ProtonDBEnrichmentThread(self)
        thread.configure(
            self._games_db,
            self._db_path,  # type: ignore[arg-type]
            force_refresh=True,
        )
        self._wire_and_start_track(TRACK_PROTONDB, thread)

    # Track D: Deck status

    def _start_deck_track(self) -> None:
        """Starts Deck status enrichment track."""
        from steam_library_manager.services.enrichment.deck_enrichment_service import (
            DeckEnrichmentThread,
        )

        thread = DeckEnrichmentThread(self)
        thread.configure(
            self._games_deck,
            self._cache_dir,  # type: ignore[arg-type]
            force_refresh=True,
        )
        self._wire_and_start_track(TRACK_DECK, thread)

    # Track E: PEGI age ratings

    def _start_pegi_track(self) -> None:
        """Start PEGI age rating gap filler after Steam API track."""
        from steam_library_manager.services.enrichment.pegi_enrichment_service import (
            PEGIEnrichmentThread,
        )

        thread = PEGIEnrichmentThread(self)
        thread.configure(
            self._games_pegi,
            self._db_path,  # type: ignore[arg-type]
            language=self._language,
            force_refresh=False,
        )
        self._wire_and_start_track(TRACK_PEGI, thread)

    # Track G: Curator recommendations

    def _start_curator_track(self, curators: list) -> None:
        """Start curator recommendation enrichment track."""
        from steam_library_manager.services.enrichment.curator_enrichment_service import (
            CuratorEnrichmentThread,
        )

        thread = CuratorEnrichmentThread(self)
        thread.configure(
            curators,
            self._db_path,  # type: ignore[arg-type]
            force_refresh=True,
        )
        self._wire_and_start_track(TRACK_CURATOR, thread)

    def _get_curators_for_refresh(self) -> list:
        """Fetch curators needing refresh from the DB."""
        from steam_library_manager.core.db import Database

        try:
            db = Database(self._db_path)  # type: ignore[arg-type]
            try:
                curators = db.get_all_curators()
                return curators
            finally:
                db.close()
        except Exception as exc:
            logger.warning("Failed to query curators: %s", exc)
            return []

    # Shared track wiring

    def _wire_and_start_track(self, track_name: str, thread: object) -> None:
        """Wire standard signals and start a non-chained enrichment track."""
        thread.progress.connect(  # type: ignore[union-attr]
            lambda _t, cur, tot: self.track_progress.emit(track_name, cur, tot)
        )
        thread.finished_enrichment.connect(  # type: ignore[union-attr]
            lambda s, f: self._on_simple_track_done(track_name, s, f)
        )
        thread.error.connect(lambda msg: self._on_track_error(track_name, msg))  # type: ignore[union-attr]
        self._threads[track_name] = thread
        thread.start()  # type: ignore[union-attr]

    # Shared completion handlers

    def _on_simple_track_done(self, track: str, success: int, failed: int) -> None:
        """Handle completion of a non-chained track."""
        self._results[track] = (success, failed)
        self.track_finished.emit(track, success, failed)
        self._on_track_complete()

    def _on_track_error(self, track: str, message: str) -> None:
        """Handle a track-level error."""
        logger.error("Track %s failed: %s", track, message)
        self._results[track] = (0, -1)
        self.track_finished.emit(track, 0, -1)
        self._on_track_complete()

    def _on_track_complete(self) -> None:
        """Decrements pending counter and emits all_finished when done."""
        self._pending_tracks -= 1
        if self._pending_tracks <= 0:
            self.all_finished.emit(self._results)
