"""Coordinator for running all enrichment tracks in parallel.

Orchestrates tag import (Phase 0) followed by four parallel enrichment
tracks (Phase 1): Steam API, HLTB, ProtonDB, and Deck status.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSignal

if TYPE_CHECKING:
    from pathlib import Path

    from src.core.game import Game
    from src.integrations.hltb_api import HLTBClient

logger = logging.getLogger("steamlibmgr.enrich_all")

__all__ = ["EnrichAllCoordinator"]

TRACK_TAGS = "tags"
TRACK_STEAM = "steam"
TRACK_HLTB = "hltb"
TRACK_PROTONDB = "protondb"
TRACK_DECK = "deck"
TRACK_PEGI = "pegi"


class EnrichAllCoordinator(QObject):
    """Coordinates parallel execution of all enrichment tracks.

    Phase 0: Tag import (runs first, then triggers Phase 1).
    Phase 1: Four parallel tracks run simultaneously:
        - Steam API (metadata then achievements, sequential within track)
        - HLTB
        - ProtonDB
        - Deck status

    Attributes:
        track_progress: Per-track progress (track_name, current, total).
        track_finished: Track completion (track_name, success, failed).
            A success value of -1 indicates a skipped track.
        all_finished: All tracks done, carries summary dict.
    """

    track_progress = pyqtSignal(str, int, int)
    track_finished = pyqtSignal(str, int, int)
    all_finished = pyqtSignal(dict)

    def __init__(self, parent: QObject | None = None) -> None:
        """Initializes the coordinator.

        Args:
            parent: Parent QObject for lifecycle management.
        """
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
        """Configures all enrichment tracks.

        Args:
            db_path: Path to the SQLite database.
            api_key: Steam Web API key.
            steam_id: 64-bit Steam user ID.
            steam_path: Steam installation root (for tag import).
            games_deck: Game objects for deck status enrichment.
            games_db: (app_id, name) tuples for DB-based enrichments.
            hltb_client: HLTBClient instance, or None if unavailable.
            language: Language code for tag resolution.
            cache_dir: Cache directory for deck status.
        """
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
        """Starts the enrichment pipeline.

        Runs tag import (Phase 0) first if steam_path is available,
        then starts four parallel tracks (Phase 1).
        """
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

    # ------------------------------------------------------------------
    # Phase 0: Tag import
    # ------------------------------------------------------------------

    def _start_tag_import(self) -> None:
        """Phase 0: Starts tag import from appinfo.vdf."""
        from src.services.enrichment.tag_import_service import TagImportThread

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
        """Handles tag import completion, then starts parallel tracks.

        Args:
            games_tagged: Number of games that received tags.
            _total_tags: Total number of unique tags found.
        """
        self._results[TRACK_TAGS] = (games_tagged, 0)
        self.track_finished.emit(TRACK_TAGS, games_tagged, 0)
        if not self._cancelled:
            self._start_parallel_tracks()

    def _on_tags_error(self, message: str) -> None:
        """Handles tag import errors and continues with parallel tracks.

        Args:
            message: Error description.
        """
        logger.warning("Tag import failed: %s", message)
        self._results[TRACK_TAGS] = (0, 1)
        self.track_finished.emit(TRACK_TAGS, 0, 1)
        if not self._cancelled:
            self._start_parallel_tracks()

    # ------------------------------------------------------------------
    # Phase 1: Parallel tracks
    # ------------------------------------------------------------------

    def _start_parallel_tracks(self) -> None:
        """Phase 1: Starts all applicable parallel enrichment tracks."""
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

        # Track E: PEGI age ratings
        if self._games_pegi and self._db_path:
            self._pending_tracks += 1
            self._start_pegi_track()
        else:
            self._results[TRACK_PEGI] = (-1, 0)
            self.track_finished.emit(TRACK_PEGI, -1, 0)

        if self._pending_tracks == 0:
            self.all_finished.emit(self._results)

    # -- Track A: Steam API (metadata → achievements) -----------------

    def _start_steam_track(self) -> None:
        """Starts Steam API metadata enrichment.

        On completion, chains to achievement enrichment when steam_id
        is available.
        """
        from src.services.enrichment.enrichment_service import EnrichmentThread

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
        """Chains from Steam metadata to achievement enrichment.

        Args:
            success: Number of successfully enriched games.
            failed: Number of failed games.
        """
        self._results[f"{TRACK_STEAM}_metadata"] = (success, failed)

        if self._cancelled or not self._steam_id or not self._db_path:
            self._results[TRACK_STEAM] = (success, failed)
            self.track_finished.emit(TRACK_STEAM, success, failed)
            self._on_track_complete()
            return

        self._start_achievement_phase(success, failed)

    def _start_achievement_phase(self, meta_success: int, meta_failed: int) -> None:
        """Starts achievement enrichment as second phase of Steam track.

        Args:
            meta_success: Success count from metadata phase.
            meta_failed: Fail count from metadata phase.
        """
        from src.services.enrichment.achievement_enrichment_service import (
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
        """Handles completion of the full Steam track.

        Args:
            meta_success: Metadata phase success count.
            meta_failed: Metadata phase fail count.
            ach_success: Achievement phase success count.
            ach_failed: Achievement phase fail count.
        """
        total_success = meta_success + ach_success
        total_failed = meta_failed + ach_failed
        self._results[TRACK_STEAM] = (total_success, total_failed)
        self.track_finished.emit(TRACK_STEAM, total_success, total_failed)
        self._on_track_complete()

    # -- Track B: HLTB ------------------------------------------------

    def _start_hltb_track(self) -> None:
        """Starts HLTB enrichment track."""
        from src.services.enrichment.enrichment_service import EnrichmentThread

        thread = EnrichmentThread(self)
        thread.configure_hltb(
            self._games_db,
            self._db_path,  # type: ignore[arg-type]
            self._hltb_client,  # type: ignore[arg-type]
            steam_user_id=self._steam_id,
            force_refresh=True,
        )
        self._wire_and_start_track(TRACK_HLTB, thread)

    # -- Track C: ProtonDB --------------------------------------------

    def _start_protondb_track(self) -> None:
        """Starts ProtonDB enrichment track."""
        from src.services.enrichment.protondb_enrichment_service import (
            ProtonDBEnrichmentThread,
        )

        thread = ProtonDBEnrichmentThread(self)
        thread.configure(
            self._games_db,
            self._db_path,  # type: ignore[arg-type]
            force_refresh=True,
        )
        self._wire_and_start_track(TRACK_PROTONDB, thread)

    # -- Track D: Deck status -----------------------------------------

    def _start_deck_track(self) -> None:
        """Starts Deck status enrichment track."""
        from src.services.enrichment.deck_enrichment_service import (
            DeckEnrichmentThread,
        )

        thread = DeckEnrichmentThread(self)
        thread.configure(
            self._games_deck,
            self._cache_dir,  # type: ignore[arg-type]
            force_refresh=True,
        )
        self._wire_and_start_track(TRACK_DECK, thread)

    # -- Track E: PEGI age ratings --------------------------------------

    def _start_pegi_track(self) -> None:
        """Starts PEGI age rating enrichment track."""
        from src.services.enrichment.pegi_enrichment_service import (
            PEGIEnrichmentThread,
        )

        thread = PEGIEnrichmentThread(self)
        thread.configure(
            self._games_pegi,
            self._db_path,  # type: ignore[arg-type]
            language=self._language,
            force_refresh=True,
        )
        self._wire_and_start_track(TRACK_PEGI, thread)

    # ------------------------------------------------------------------
    # Shared track wiring
    # ------------------------------------------------------------------

    def _wire_and_start_track(self, track_name: str, thread: object) -> None:
        """Connects standard signals and starts a simple enrichment track.

        Wires progress, finished_enrichment, and error signals to the
        shared handlers. Only suitable for non-chained tracks (B–E).

        Args:
            track_name: Track identifier constant.
            thread: The enrichment thread to wire and start.
        """
        thread.progress.connect(  # type: ignore[union-attr]
            lambda _t, cur, tot: self.track_progress.emit(track_name, cur, tot)
        )
        thread.finished_enrichment.connect(  # type: ignore[union-attr]
            lambda s, f: self._on_simple_track_done(track_name, s, f)
        )
        thread.error.connect(lambda msg: self._on_track_error(track_name, msg))  # type: ignore[union-attr]
        self._threads[track_name] = thread
        thread.start()  # type: ignore[union-attr]

    # ------------------------------------------------------------------
    # Shared completion handlers
    # ------------------------------------------------------------------

    def _on_simple_track_done(self, track: str, success: int, failed: int) -> None:
        """Handles completion of a simple (non-chained) track.

        Args:
            track: Track identifier.
            success: Number of successfully processed items.
            failed: Number of failed items.
        """
        self._results[track] = (success, failed)
        self.track_finished.emit(track, success, failed)
        self._on_track_complete()

    def _on_track_error(self, track: str, message: str) -> None:
        """Handles a track-level error.

        Args:
            track: Track identifier.
            message: Error description.
        """
        logger.error("Track %s failed: %s", track, message)
        self._results[track] = (0, -1)
        self.track_finished.emit(track, 0, -1)
        self._on_track_complete()

    def _on_track_complete(self) -> None:
        """Decrements pending counter and emits all_finished when done."""
        self._pending_tracks -= 1
        if self._pending_tracks <= 0:
            self.all_finished.emit(self._results)
