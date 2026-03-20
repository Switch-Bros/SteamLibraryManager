#
# steam_library_manager/ui/actions/view_actions.py
# View menu action handlers
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from steam_library_manager.utils.i18n import t

__all__ = ["ViewActions"]


class ViewActions:
    """View menu stuff - sorting, filtering, search, tree expand/collapse.

    Dispatches filter toggles to FilterService, handles search with
    easter eggs (switchbros, teamslm), and manages tree state.
    """

    def __init__(self, mw):
        self.mw = mw

    def on_sort_changed(self, k):
        self.mw.filter_service.set_sort_key(k)
        if self.mw.current_search_query:
            self.on_search(self.mw.current_search_query)
        else:
            self.mw.populate_categories()

    def on_filter_toggled(self, grp, k, chk):
        fs = self.mw.filter_service
        if grp == "type":
            fs.toggle_type(k, chk)
        elif grp == "platform":
            fs.toggle_platform(k, chk)
        elif grp == "status":
            fs.toggle_status(k, chk)
        elif grp == "language":
            fs.toggle_language(k, chk)
        elif grp == "deck_status":
            fs.toggle_deck_status(k, chk)
        elif grp == "achievement":
            fs.toggle_achievement_filter(k, chk)
        elif grp == "pegi":
            fs.toggle_pegi_rating(k, chk)
        elif grp == "curator":
            try:
                fs.toggle_curator_filter(int(k), chk)
            except (ValueError, TypeError):
                pass

        if self.mw.current_search_query:
            self.on_search(self.mw.current_search_query)
        else:
            self.mw.populate_categories()

    def expand_all(self):
        if self.mw.tree:
            self.mw.tree.expandAll()

    def collapse_all(self):
        if self.mw.tree:
            self.mw.tree.collapseAll()

    def on_search(self, q):
        self.mw.current_search_query = q

        if not q:
            self.mw.populate_categories()
            return

        # easter eggs
        ql = q.strip().lower()
        if ql in ("switchbros", "teamslm"):
            from steam_library_manager.utils.enigma import load_easter_egg

            egg = load_easter_egg("searchbar" if ql == "switchbros" else "teamslm")
            if egg:
                from steam_library_manager.ui.widgets.ui_helper import UIHelper

                UIHelper.show_info(self.mw, egg.get("message", ""), title=egg.get("title", ""))
            return

        if not self.mw.game_manager or not self.mw.search_service:
            return

        # filter then search
        gs = self.mw.game_manager.get_library_entries()
        filt = self.mw.filter_service.apply(gs)
        res = self.mw.search_service.filter_games(filt, q)

        if res:
            cat = t("ui.search.results_category", count=len(res))
            sorted_r = self.mw.filter_service.sort_games(res)
            self.mw.tree.populate_categories({cat: sorted_r})
            self.mw.tree.expandAll()
            self.mw.set_status(t("ui.search.status_found", count=len(res)))
        else:
            self.mw.tree.clear()
            self.mw.set_status(t("ui.search.status_none"))

    def show_statistics(self):
        from steam_library_manager.ui.dialogs.statistics_dialog import StatisticsDialog

        StatisticsDialog(self.mw).exec()

    def clear_search(self):
        self.mw.current_search_query = ""
        if self.mw.search_entry:
            self.mw.search_entry.clear()
        self.mw.populate_categories()
