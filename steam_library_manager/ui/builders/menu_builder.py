#
# steam_library_manager/ui/builders/menu_builder.py
# Builds the main application menu bar
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QActionGroup, QKeySequence
from PyQt6.QtWidgets import QLabel

from steam_library_manager.ui.widgets.ui_helper import UIHelper
from steam_library_manager.utils.i18n import get_language, t
from steam_library_manager.utils.open_url import open_url

__all__ = ["MenuBuilder"]

_GH = "https://github.com/Switch-Bros/SteamLibraryManager"


class MenuBuilder:
    """Builds the entire menu bar with all submenus and shortcuts.

    Each top-level menu (File, Edit, View, Tools, Help) is built in
    its own method. Filter submenus are generated from key tuples.
    Curator filter is populated dynamically on menu open.
    """

    def __init__(self, mw):
        self.mw = mw
        self.user_label = QLabel(t("common.unknown"))

    def build(self, menubar):
        self._file(menubar)
        self._edit(menubar)
        self._view(menubar)
        self._tools(menubar)
        self._help(menubar)
        self._corner(menubar)

    # helpers

    def _not_implemented(self, fkey):
        feat = t(fkey)
        msg = "%s %s" % (t("common.placeholder_message", feature=feat), t("emoji.rocket"))
        UIHelper.show_info(self.mw, msg, t("common.placeholder_title"))

    def _url(self, url):
        open_url(url)

    def _edit_single(self):
        w = self.mw
        if w.selected_game is None:
            w.set_status(t("ui.errors.no_selection"))
            return
        w.metadata_actions.edit_game_metadata(w.selected_game)

    def _rename_coll(self):
        w = self.mw
        sel = w.tree.get_selected_categories()
        if not sel:
            w.set_status(t("ui.errors.no_selection"))
            return
        self._not_implemented("menu.edit.collections.rename")

    def _merge_colls(self):
        w = self.mw
        sel = w.tree.get_selected_categories()
        if len(sel) < 2:
            w.set_status(t("ui.errors.no_selection"))
            return
        self._not_implemented("menu.edit.collections.merge")

    def _add_filters(self, parent, pfx, keys, fname=None, checked=False):
        # add checkable filter submenu
        if fname is None:
            fname = pfx.rsplit(".", 1)[-1]
        sub = parent.addMenu(t("%s.root" % pfx))
        w = self.mw
        for k in keys:
            act = QAction(t("%s.%s" % (pfx, k)), w)
            act.setCheckable(True)
            if checked:
                act.setChecked(True)
            act.triggered.connect(lambda c, key=k, fn=fname: w.view_actions.on_filter_toggled(fn, key, c))
            sub.addAction(act)

    # -- file menu --

    def _file(self, mb):
        w = self.mw
        m = mb.addMenu(t("menu.file.root"))

        a = QAction(t("menu.file.refresh"), w)
        a.setShortcut(QKeySequence("Ctrl+R"))
        a.triggered.connect(w.file_actions.refresh_data)
        m.addAction(a)

        a = QAction(t("common.save"), w)
        a.setShortcut(QKeySequence("Ctrl+S"))
        a.triggered.connect(w.file_actions.force_save)
        m.addAction(a)

        m.addSeparator()

        # export submenu
        exp = m.addMenu(t("menu.file.export.root"))

        for key, fn in (
            ("collections_vdf", w.file_actions.export_collections_text),
            ("collections_text", w.file_actions.export_collections_text),
            ("games_csv_simple", w.file_actions.export_csv_simple),
            ("games_csv_full", w.file_actions.export_csv_full),
            ("games_json", w.file_actions.export_json),
            ("smart_collections", w.file_actions.export_smart_collections),
        ):
            a = QAction(t("menu.file.export.%s" % key), w)
            a.triggered.connect(fn)
            exp.addAction(a)

        a = QAction(t("menu.file.export.artwork_package"), w)
        a.triggered.connect(lambda: self._not_implemented("menu.file.export.artwork_package"))
        exp.addAction(a)

        a = QAction(t("menu.file.export.db_backup"), w)
        a.triggered.connect(w.file_actions.export_db_backup)
        exp.addAction(a)

        # import submenu
        imp = m.addMenu(t("menu.file.import.root"))

        for key, fn in (
            ("collections", w.file_actions.import_collections_vdf),
            ("smart_collections", w.file_actions.import_smart_collections),
            ("db_backup", w.file_actions.import_db_backup),
        ):
            a = QAction(t("menu.file.import.%s" % key), w)
            a.triggered.connect(fn)
            imp.addAction(a)

        a = QAction(t("menu.file.import.artwork_package"), w)
        a.triggered.connect(lambda: self._not_implemented("menu.file.import.artwork_package"))
        imp.addAction(a)

        # profiles
        prof = m.addMenu(t("menu.file.profiles.root"))

        a = QAction(t("menu.file.profiles.save_current"), w)
        a.triggered.connect(w.profile_actions.save_current_as_profile)
        prof.addAction(a)

        a = QAction(t("menu.file.profiles.manage"), w)
        a.triggered.connect(w.profile_actions.show_profile_manager)
        prof.addAction(a)

        m.addSeparator()

        a = QAction(t("menu.file.exit"), w)
        a.setShortcut(QKeySequence("Ctrl+Q"))
        a.triggered.connect(w.file_actions.exit_application)
        m.addAction(a)

    # -- edit menu --

    def _edit(self, mb):
        w = self.mw
        m = mb.addMenu(t("menu.edit.root"))

        # metadata
        meta = m.addMenu(t("menu.edit.metadata.root"))

        a = QAction(t("menu.edit.metadata.single"), w)
        a.triggered.connect(self._edit_single)
        meta.addAction(a)

        a = QAction(t("menu.edit.metadata.bulk"), w)
        a.triggered.connect(w.metadata_actions.bulk_edit_metadata)
        meta.addAction(a)

        a = QAction(t("menu.edit.auto_categorize"), w)
        a.setShortcut(QKeySequence("Ctrl+Shift+A"))
        a.triggered.connect(w.edit_actions.auto_categorize)
        m.addAction(a)

        m.addSeparator()

        # collections
        coll = m.addMenu(t("menu.edit.collections.root"))

        a = QAction(t("menu.edit.collections.rename"), w)
        a.triggered.connect(self._rename_coll)
        coll.addAction(a)

        a = QAction(t("menu.edit.collections.merge"), w)
        a.triggered.connect(self._merge_colls)
        coll.addAction(a)

        a = QAction(t("menu.edit.collections.delete_empty"), w)
        a.triggered.connect(lambda: self._not_implemented("menu.edit.collections.delete_empty"))
        coll.addAction(a)

        coll.addSeparator()

        # smart collections
        a = QAction(t("menu.edit.collections.create_smart"), w)
        a.setShortcut(QKeySequence("Ctrl+Shift+N"))
        a.triggered.connect(w.edit_actions.create_smart_collection)
        coll.addAction(a)

        a = QAction(t("menu.edit.collections.edit_smart"), w)
        a.triggered.connect(w.edit_actions.edit_smart_collection)
        coll.addAction(a)

        a = QAction(t("menu.edit.collections.delete_smart"), w)
        a.triggered.connect(w.edit_actions.delete_smart_collection)
        coll.addAction(a)

        a = QAction(t("menu.edit.collections.refresh_smart"), w)
        a.triggered.connect(w.edit_actions.refresh_smart_collections)
        coll.addAction(a)

        coll.addSeparator()

        a = QAction(t("menu.edit.collections.expand_all"), w)
        a.triggered.connect(w.view_actions.expand_all)
        coll.addAction(a)

        a = QAction(t("menu.edit.collections.collapse_all"), w)
        a.triggered.connect(w.view_actions.collapse_all)
        coll.addAction(a)

        m.addSeparator()

        a = QAction(t("menu.edit.find_missing_metadata"), w)
        a.triggered.connect(w.tools_actions.find_missing_metadata)
        m.addAction(a)

        a = QAction(t("menu.edit.reset_metadata"), w)
        a.triggered.connect(w.metadata_actions.restore_metadata_changes)
        m.addAction(a)

        a = QAction(t("menu.edit.remove_duplicates"), w)
        a.triggered.connect(w.file_actions.remove_duplicate_collections)
        m.addAction(a)

    # -- view menu --

    def _view(self, mb):
        w = self.mw
        m = mb.addMenu(t("menu.view.root"))

        # sort (exclusive radio group)
        sort_m = m.addMenu(t("menu.view.sort.root"))
        grp = QActionGroup(w)
        grp.setExclusive(True)

        for k in ("name", "playtime", "last_played", "release_date"):
            a = QAction(t("menu.view.sort.%s" % k), w)
            a.setCheckable(True)
            if k == "name":
                a.setChecked(True)
            a.triggered.connect(lambda checked, key=k: w.view_actions.on_sort_changed(key))
            grp.addAction(a)
            sort_m.addAction(a)

        m.addSeparator()

        # filter submenus
        self._add_filters(m, "menu.view.type", ("games", "soundtracks", "software", "videos", "tools"), checked=True)
        self._add_filters(m, "menu.view.platform", ("linux", "windows", "steamos"), checked=True)
        self._add_filters(m, "menu.view.status", ("installed", "not_installed", "hidden", "with_playtime", "favorites"))
        self._add_filters(
            m,
            "menu.view.language",
            (
                "english",
                "german",
                "french",
                "spanish",
                "italian",
                "portuguese",
                "russian",
                "polish",
                "japanese",
                "chinese_simplified",
                "chinese_traditional",
                "korean",
                "dutch",
                "swedish",
                "turkish",
            ),
        )
        self._add_filters(m, "menu.view.deck", ("verified", "playable", "unsupported", "unknown"), fname="deck_status")
        self._add_filters(m, "menu.view.achievement", ("perfect", "almost", "progress", "started", "none"))
        self._add_filters(m, "menu.view.pegi", ("pegi_3", "pegi_7", "pegi_12", "pegi_16", "pegi_18", "pegi_none"))

        # curator filter (dynamic)
        self._cur_menu = m.addMenu(t("menu.view.curator.root"))
        self._cur_menu.aboutToShow.connect(self._pop_cur_menu)

        m.addSeparator()

        a = QAction(t("menu.view.statistics.root"), w)
        a.triggered.connect(w.view_actions.show_statistics)
        m.addAction(a)

    # -- tools menu --

    def _tools(self, mb):
        w = self.mw
        m = mb.addMenu(t("menu.tools.root"))

        # artwork (stubs)
        art = m.addMenu(t("menu.tools.artwork.root"))
        for k in ("download_missing", "edit"):
            a = QAction(t("menu.tools.artwork.%s" % k), w)
            a.triggered.connect(lambda checked, key="menu.tools.artwork.%s" % k: self._not_implemented(key))
            art.addAction(a)

        # search (stubs)
        srch = m.addMenu(t("menu.tools.search.root"))
        for k in ("by_publisher", "by_developer", "by_genre", "by_tags", "by_year"):
            a = QAction(t("menu.tools.search.%s" % k), w)
            a.triggered.connect(lambda checked, key="menu.tools.search.%s" % k: self._not_implemented(key))
            srch.addAction(a)

        # batch ops
        batch = m.addMenu(t("menu.tools.batch.root"))

        for key, fn in (
            ("update_metadata", w.enrichment_starters.start_steam_api_enrichment),
            ("update_hltb", w.enrichment_starters.start_hltb_enrichment),
            ("update_deck", w.enrichment_starters.start_deck_enrichment),
            ("update_achievements", w.enrichment_starters.start_achievement_enrichment),
            ("import_tags", w.enrichment_starters.start_tag_import),
            ("update_protondb", w.enrichment_starters.start_protondb_enrichment),
            ("update_pegi", w.enrichment_starters.start_pegi_enrichment),
        ):
            a = QAction(t("menu.tools.batch.%s" % key), w)
            a.triggered.connect(fn)
            batch.addAction(a)

        a = QAction(t("menu.tools.batch.update_pegi_force"), w)
        a.triggered.connect(lambda: w.enrichment_starters.start_pegi_enrichment(force_refresh=True))
        batch.addAction(a)

        a = QAction(t("menu.tools.batch.update_curator"), w)
        a.triggered.connect(w.enrichment_starters.start_curator_enrichment)
        batch.addAction(a)

        batch.addSeparator()

        a = QAction(t("menu.tools.batch.enrich_all"), w)
        a.triggered.connect(w.enrichment_actions.start_enrich_all)
        batch.addAction(a)

        batch.addSeparator()

        a = QAction(t("menu.tools.batch.check_store"), w)
        a.triggered.connect(w.tools_actions.start_library_health_check)
        batch.addAction(a)

        # db (stubs)
        db = m.addMenu(t("menu.tools.database.root"))
        for k in ("optimize", "recreate", "import_appinfo", "backup"):
            a = QAction(t("menu.tools.database.%s" % k), w)
            a.triggered.connect(lambda checked, key="menu.tools.database.%s" % k: self._not_implemented(key))
            db.addAction(a)

        m.addSeparator()

        a = QAction(t("menu.tools.external_games"), w)
        a.setShortcut(QKeySequence("Ctrl+Shift+E"))
        a.triggered.connect(w.tools_actions.show_external_games)
        m.addAction(a)

        a = QAction(t("menu.tools.manage_curators"), w)
        a.triggered.connect(w.tools_actions.show_curator_manager)
        m.addAction(a)

        m.addSeparator()

        a = QAction(t("menu.tools.settings"), w)
        a.setShortcut(QKeySequence("Ctrl+P"))
        a.triggered.connect(w.settings_actions.show_settings)
        m.addAction(a)

    # -- help menu --

    def _help(self, mb):
        w = self.mw
        m = mb.addMenu(t("menu.help.root"))

        # docs
        docs = m.addMenu(t("menu.help.docs.root"))
        dmap = {
            "manual": "USER_MANUAL.md",
            "tips": "TIPS_AND_TRICKS.md",
            "shortcuts": "KEYBOARD_SHORTCUTS.md",
            "faq": "FAQ.md",
        }
        base = "%s/blob/master/docs" % _GH
        for k in ("manual", "tips", "shortcuts", "faq"):
            a = QAction(t("menu.help.docs.%s" % k), w)
            if k == "manual":
                a.setShortcut(QKeySequence("F1"))
            a.triggered.connect(lambda checked, key=k: self._url("%s/%s/%s" % (base, get_language(), dmap[key])))
            docs.addAction(a)

        # online
        online = m.addMenu(t("menu.help.online.root"))
        for k, u in (("github", _GH), ("issues", "%s/issues" % _GH), ("wiki", "%s/wiki" % _GH)):
            a = QAction(t("menu.help.online.%s" % k), w)
            a.triggered.connect(lambda checked, url=u: self._url(url))
            online.addAction(a)

        # updates
        upd = m.addMenu(t("menu.help.updates.root"))
        a = QAction(t("menu.help.updates.check"), w)
        a.triggered.connect(lambda checked: w.steam_actions.check_for_updates())
        upd.addAction(a)
        a = QAction(t("menu.help.updates.changelog"), w)
        a.triggered.connect(lambda checked: self._url("%s/blob/master/CHANGELOG.md" % _GH))
        upd.addAction(a)

        # support
        sup = m.addMenu(t("menu.help.support.root"))
        for k, u in (
            ("kofi", "https://ko-fi.com/S6S51T9G3Y"),
            ("paypal", "https://www.paypal.com/donate/?hosted_button_id=HWPG6YAGXAWJJ"),
            ("github", "https://github.com/sponsors/Switch-Bros"),
        ):
            a = QAction(t("menu.help.support.%s" % k), w)
            a.triggered.connect(lambda checked, url=u: self._url(url))
            sup.addAction(a)

        m.addSeparator()

        a = QAction(t("menu.help.about"), w)
        a.setShortcut(QKeySequence("F12"))
        a.triggered.connect(w.steam_actions.show_about)
        m.addAction(a)

    # -- curator filter (dynamic) --

    def _pop_cur_menu(self):
        menu = self._cur_menu
        menu.clear()
        w = self.mw

        cache = w.filter_service.curator_cache
        if not cache:
            nd = QAction(t("menu.view.curator.no_data"), w)
            nd.setEnabled(False)
            menu.addAction(nd)
            return

        # get curator names from db
        names = {}
        try:
            dbp = None
            if hasattr(w, "game_service") and w.game_service:
                db = getattr(w.game_service, "database", None)
                if db and hasattr(db, "db_path"):
                    dbp = db.db_path
            if dbp:
                from steam_library_manager.core.database import Database

                tmp = Database(dbp)
                try:
                    for c in tmp.get_all_curators():
                        names[c["curator_id"]] = c["name"]
                finally:
                    tmp.close()
        except Exception:
            pass

        active = w.filter_service._cur_ids
        for cid in sorted(cache.keys()):
            nm = names.get(cid, "Curator %d" % cid)
            cnt = len(cache[cid])
            a = QAction("%s (%d)" % (nm, cnt), w)
            a.setCheckable(True)
            a.setChecked(cid in active)
            a.triggered.connect(lambda checked, id=cid: w.view_actions.on_filter_toggled("curator", str(id), checked))
            menu.addAction(a)

    def _corner(self, mb):
        self.user_label.setStyleSheet("padding: 5px 10px;")
        self.user_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.user_label.setMinimumWidth(250)
        mb.setCornerWidget(self.user_label, Qt.Corner.TopRightCorner)
