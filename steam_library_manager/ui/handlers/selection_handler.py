#
# steam_library_manager/ui/handlers/selection_handler.py
# Game selection state and multi-select logic
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal, Qt

from steam_library_manager.utils.i18n import t

__all__ = ["SelectionHandler"]


class SelectionHandler:
    """Handles game selection and background detail fetching.

    Only one fetch thread at a time - new click kills old thread.
    """

    def __init__(self, mw):
        self.mw = mw
        self._fetch = None  # current thread
        self._old_fetches = []  # keep old threads alive until they finish

    def on_games_selected(self, gs):
        # multi-selection changed
        self.mw.selected_games = gs
        cats = list(self.mw.game_manager.get_all_categories().keys())

        if len(gs) > 1:
            self.mw.set_status(t("ui.main_window.games_selected", count=len(gs)))
            self.mw.details_widget.set_games(gs, cats)
        elif len(gs) == 1:
            self.mw.set_status("%s" % gs[0].name)
            self.on_game_selected(gs[0])
        else:
            pass  # nothing selected

    def on_game_selected(self, g):
        # single game clicked
        if len(self.mw.selected_games) > 1:
            return

        self.mw.selected_game = g
        cats = list(self.mw.game_manager.get_all_categories().keys())

        self._update_overlap(g)

        # show UI immediately, fetch in background
        self.mw.details_widget.set_game(g, cats)

        if self.mw.game_manager.detail_svc.needs_enrichment(g.app_id):
            self.fetch_game_details_async(g.app_id, cats)

    def fetch_game_details_async(self, aid, cats):
        # background fetch

        class _Fetcher(QThread):
            done = pyqtSignal(bool)

            def __init__(self, mgr, app_id):
                super().__init__()
                self.mgr = mgr
                self.aid = app_id
                self.dead = False  # stale flag

            def run(self):
                ok = self.mgr.fetch_game_details(self.aid)
                if not self.dead:
                    self.done.emit(ok)

        # mark old fetch as stale so its result is ignored
        if self._fetch and self._fetch.isRunning():
            self._fetch.dead = True  # type: ignore[attr-defined]
            # prevent GC crash: park the old thread until it finishes
            self._old_fetches.append(self._fetch)
            self._fetch.finished.connect(lambda t=self._fetch: self._cleanup_fetch(t))

        thr = _Fetcher(self.mw.game_manager, aid)

        def _on_done(ok):
            if ok and self.mw.selected_game and self.mw.selected_game.app_id == aid:
                g = self.mw.game_manager.get_game(aid)
                if g:
                    self.mw.details_widget.set_game(g, cats)

        thr.done.connect(_on_done)
        self._fetch = thr
        thr.start()

    def _cleanup_fetch(self, thr):
        # remove finished thread from parking list
        if thr in self._old_fetches:
            self._old_fetches.remove(thr)

    def restore_game_selection(self, ids):
        # re-select after tree refresh
        if not ids:
            return

        self.mw.tree.blockSignals(True)

        for i in range(self.mw.tree.topLevelItemCount()):
            ci = self.mw.tree.topLevelItem(i)
            for j in range(ci.childCount()):
                gi = ci.child(j)
                aid = gi.data(0, Qt.ItemDataRole.UserRole)
                if aid and aid in ids:
                    gi.setSelected(True)

        self.mw.tree.blockSignals(False)

        self.mw.selected_games = [self.mw.game_manager.get_game(aid) for aid in ids]
        self.mw.selected_games = [g for g in self.mw.selected_games if g is not None]

    def _update_overlap(self, g):
        # compute curator overlap from cache
        try:
            fs = self.mw.filter_service
            c = fs.curator_cache
            if not c:
                g.curator_overlap = ""
                return
            nid = int(g.app_id)
            recs = sum(1 for r in c.values() if nid in r)
            tot = len(c)
            g.curator_overlap = "%d/%d" % (recs, tot)
        except (ValueError, TypeError, AttributeError):
            g.curator_overlap = ""
