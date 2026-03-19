#
# steam_library_manager/services/enrichment/enrich_all_coordinator.py
# Coordinates running all enrichment tracks in parallel
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging

from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger("steamlibmgr.enrich_all")

__all__ = [
    "EnrichAllCoordinator",
    "TRK_TAGS",
    "TRK_STEAM",
    "TRK_HLTB",
    "TRK_PDB",
    "TRK_DECK",
    "TRK_PEGI",
    "TRK_CURATOR",
]

# track ids
TRK_TAGS = "tags"
TRK_STEAM = "steam"
TRK_HLTB = "hltb"
TRK_PDB = "protondb"
TRK_DECK = "deck"
TRK_PEGI = "pegi"
TRK_CURATOR = "curator"


class EnrichAllCoordinator(QObject):
    """Runs all enrichment sources - tags first, then parallel."""

    track_progress = pyqtSignal(str, int, int)
    track_finished = pyqtSignal(str, int, int)
    all_finished = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._threads = {}
        self._results = {}
        self._pending = 0
        self._cancelled = False

        # config params (set via configure())
        self._db_path = None
        self._api_key = ""
        self._steam_id = ""
        self._steam_path = None
        self._games_deck = []
        self._games_db = []
        self._hltb_client = None
        self._lang = "en"
        self._cache_dir = None
        self._games_pegi = []

    def configure(
        self,
        db_path,
        api_key,
        steam_id,
        steam_path,
        games_deck,
        games_db,
        hltb_client,
        language,
        cache_dir,
        games_pegi=None,
    ):
        # setup before start()
        self._db_path = db_path
        self._api_key = api_key
        self._steam_id = steam_id
        self._steam_path = steam_path
        self._games_deck = games_deck
        self._games_db = games_db
        self._hltb_client = hltb_client
        self._lang = language
        self._cache_dir = cache_dir
        self._games_pegi = games_pegi or []

    def start(self):
        # kick off phase 0 or skip to parallel
        if self._steam_path and self._db_path:
            self._run_tag_import()
        else:
            self.track_finished.emit(TRK_TAGS, -1, 0)
            self._run_parallel()

    def cancel(self):
        self._cancelled = True
        for thr in self._threads.values():
            if hasattr(thr, "cancel"):
                thr.cancel()

    # phase 0: tag import

    def _run_tag_import(self):
        from steam_library_manager.services.enrichment.tag_import_service import TagImportThread

        thr = TagImportThread(self)
        thr.configure(self._steam_path, self._db_path, self._lang)

        thr.progress.connect(lambda _t, cur, tot: self.track_progress.emit(TRK_TAGS, cur, tot))
        thr.finished_import.connect(self._on_tags_done)
        thr.error.connect(self._on_tags_err)

        self._threads[TRK_TAGS] = thr
        thr.start()

    def _on_tags_done(self, tagged, _total):
        self._results[TRK_TAGS] = (tagged, 0)
        self.track_finished.emit(TRK_TAGS, tagged, 0)
        if not self._cancelled:
            self._run_parallel()

    def _on_tags_err(self, msg):
        logger.warning("tag import failed: %s", msg)
        self._results[TRK_TAGS] = (0, 1)
        self.track_finished.emit(TRK_TAGS, 0, 1)
        if not self._cancelled:
            self._run_parallel()

    # phase 1: parallel tracks

    def _run_parallel(self):
        self._pending = 0

        # track A: steam api (metadata + achievements)
        if self._api_key and self._games_db and self._db_path:
            self._pending += 1
            self._run_steam()
        else:
            self.track_finished.emit(TRK_STEAM, -1, 0)

        # track B: hltb
        if self._hltb_client and self._games_db and self._db_path:
            self._pending += 1
            self._run_hltb()
        else:
            self.track_finished.emit(TRK_HLTB, -1, 0)

        # track C: protondb
        if self._games_db and self._db_path:
            self._pending += 1
            self._run_protondb()
        else:
            self.track_finished.emit(TRK_PDB, -1, 0)

        # track D: deck compat
        if self._games_deck and self._cache_dir:
            self._pending += 1
            self._run_deck()
        else:
            self.track_finished.emit(TRK_DECK, -1, 0)

        # track E: pegi (chains after steam)
        if not (self._games_pegi and self._db_path):
            self._results[TRK_PEGI] = (-1, 0)
            self.track_finished.emit(TRK_PEGI, -1, 0)
        elif not (self._api_key and self._games_db and self._db_path):
            # no steam track, run pegi standalone
            self._pending += 1
            self._run_pegi()

        # track G: curators
        if self._db_path:
            curs = self._fetch_curators()
            if curs:
                self._pending += 1
                self._run_curator(curs)
            else:
                self.track_finished.emit(TRK_CURATOR, -1, 0)
        else:
            self.track_finished.emit(TRK_CURATOR, -1, 0)

        if self._pending == 0:
            self.all_finished.emit(self._results)

    # track A: steam api (metadata -> achievements -> pegi chain)

    def _run_steam(self):
        from steam_library_manager.services.enrichment.enrichment_service import EnrichmentThread

        thr = EnrichmentThread(self)
        thr.configure_steam(self._games_db, self._db_path, self._api_key, force_refresh=True)

        thr.progress.connect(lambda _t, cur, tot: self.track_progress.emit(TRK_STEAM, cur, tot))
        thr.finished_enrichment.connect(self._on_steam_meta_done)
        thr.error.connect(lambda msg: self._on_trk_err(TRK_STEAM, msg))

        self._threads[TRK_STEAM] = thr
        thr.start()

    def _on_steam_meta_done(self, ok, fail):
        # metadata done, now chain achievements
        self._results["%s_metadata" % TRK_STEAM] = (ok, fail)

        if self._cancelled or not self._steam_id or not self._db_path:
            self._results[TRK_STEAM] = (ok, fail)
            self.track_finished.emit(TRK_STEAM, ok, fail)
            self._trk_complete()
            return

        self._run_achievements(ok, fail)

    def _run_achievements(self, meta_ok, meta_fail):
        from steam_library_manager.services.enrichment.achievement_enrichment_service import (
            AchievementEnrichmentThread,
        )

        thr = AchievementEnrichmentThread(self)
        thr.configure(self._games_db, self._db_path, self._api_key, self._steam_id, force_refresh=True)

        thr.progress.connect(lambda _t, cur, tot: self.track_progress.emit(TRK_STEAM, cur, tot))
        thr.finished_enrichment.connect(lambda s, f: self._on_steam_done(meta_ok, meta_fail, s, f))
        thr.error.connect(lambda msg: self._on_trk_err(TRK_STEAM, msg))

        self._threads["%s_ach" % TRK_STEAM] = thr
        thr.start()

    def _on_steam_done(self, meta_ok, meta_fail, ach_ok, ach_fail):
        total_ok = meta_ok + ach_ok
        total_fail = meta_fail + ach_fail
        self._results[TRK_STEAM] = (total_ok, total_fail)
        self.track_finished.emit(TRK_STEAM, total_ok, total_fail)

        # chain pegi after steam
        if not self._cancelled and self._games_pegi and self._db_path:
            self._pending += 1
            self._run_pegi()
        elif self._games_pegi and self._db_path:
            self._results[TRK_PEGI] = (0, 0)
            self.track_finished.emit(TRK_PEGI, 0, 0)

        self._trk_complete()

    # track B: hltb

    def _run_hltb(self):
        from steam_library_manager.services.enrichment.enrichment_service import EnrichmentThread

        thr = EnrichmentThread(self)
        thr.configure_hltb(
            self._games_db,
            self._db_path,
            self._hltb_client,
            steam_user_id=self._steam_id,
            force_refresh=True,
        )
        self._wire_and_go(TRK_HLTB, thr)

    # track C: protondb

    def _run_protondb(self):
        from steam_library_manager.services.enrichment.protondb_enrichment_service import (
            ProtonDBEnrichmentThread,
        )

        thr = ProtonDBEnrichmentThread(self)
        thr.configure(self._games_db, self._db_path, force_refresh=True)
        self._wire_and_go(TRK_PDB, thr)

    # track D: steamdeck

    def _run_deck(self):
        from steam_library_manager.services.enrichment.deck_enrichment_service import (
            DeckEnrichmentThread,
        )

        thr = DeckEnrichmentThread(self)
        thr.configure(self._games_deck, self._cache_dir, force_refresh=True)
        self._wire_and_go(TRK_DECK, thr)

    # track E: pegi

    def _run_pegi(self):
        from steam_library_manager.services.enrichment.pegi_enrichment_service import (
            PEGIEnrichmentThread,
        )

        thr = PEGIEnrichmentThread(self)
        thr.configure(self._games_pegi, self._db_path, language=self._lang, force_refresh=False)
        self._wire_and_go(TRK_PEGI, thr)

    # track G: curators

    def _run_curator(self, curators):
        from steam_library_manager.services.enrichment.curator_enrichment_service import (
            CuratorEnrichmentThread,
        )

        thr = CuratorEnrichmentThread(self)
        thr.configure(curators, self._db_path, force_refresh=True)
        self._wire_and_go(TRK_CURATOR, thr)

    def _fetch_curators(self):
        from steam_library_manager.core.db import Database

        try:
            db = Database(self._db_path)
            try:
                return db.get_all_curators()
            finally:
                db.close()
        except Exception as exc:
            logger.warning("curator query failed: %s", exc)
            return []

    # shared wiring helpers

    def _wire_and_go(self, name, thr):
        # hook up signals and start track
        thr.progress.connect(lambda _t, cur, tot: self.track_progress.emit(name, cur, tot))
        thr.finished_enrichment.connect(lambda s, f: self._on_trk_done(name, s, f))
        thr.error.connect(lambda msg: self._on_trk_err(name, msg))
        self._threads[name] = thr
        thr.start()

    def _on_trk_done(self, trk, ok, fail):
        self._results[trk] = (ok, fail)
        self.track_finished.emit(trk, ok, fail)
        self._trk_complete()

    def _on_trk_err(self, trk, msg):
        logger.error("track %s failed: %s", trk, msg)
        self._results[trk] = (0, -1)
        self.track_finished.emit(trk, 0, -1)
        self._trk_complete()

    def _trk_complete(self):
        self._pending -= 1
        if self._pending <= 0:
            self.all_finished.emit(self._results)
