#
# steam_library_manager/ui/handlers/category_populator.py
# Populates sidebar category tree from game manager state
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from collections import OrderedDict

from steam_library_manager.integrations.external_games.models import get_collection_emoji
from steam_library_manager.utils.i18n import t

__all__ = ["CategoryPopulator"]

# app_type -> i18n key
_TYPE_MAP = {
    "music": "categories.soundtracks",
    "tool": "categories.tools",
    "application": "categories.software",
    "video": "categories.videos",
}


class CategoryPopulator:
    """Builds the sidebar category tree.

    Cheap to rebuild (~50ms for 2500 games), no cache needed.
    Handles German umlauts, smart collections, duplicates.
    """

    def __init__(self, mw):
        self._mw = mw

    @staticmethod
    def german_sort_key(txt):
        # sort with umlaut support
        repl = {
            "\u00e4": "a~",
            "\u00c4": "a~",
            "\u00f6": "o~",
            "\u00d6": "o~",
            "\u00fc": "u~",
            "\u00dc": "u~",
            "\u00df": "ss",
        }
        r = txt.lower()
        for old, new in repl.items():
            r = r.replace(old, new)
        return r

    @staticmethod
    def _get_type_cats(apps):
        # group non-games by type
        bkts = {}
        for a in apps:
            if a.hidden:
                continue
            tl = a.app_type.lower() if a.app_type else ""
            ck = _TYPE_MAP.get(tl)
            if ck:
                cn = t(ck)
                bkts.setdefault(cn, []).append(a)

        out = {}
        for cn in sorted(bkts.keys()):
            out[cn] = sorted(bkts[cn], key=lambda g: g.sort_name.lower())
        return out

    def populate(self):
        # refresh sidebar
        mw = self._mw
        if not mw.game_manager:
            return

        # apply filters
        raw = mw.game_manager.get_library_entries()
        filt = mw.filter_service.apply(raw)
        fids = {g.app_id for g in filt}

        sort_fn = mw.filter_service.sort_games

        vis = sort_fn([g for g in filt if not g.hidden])
        hid = sort_fn([g for g in filt if g.hidden])

        favs = sort_fn(
            [g for g in mw.game_manager.get_favorites() if not g.hidden and g.app_id in fids],
        )

        # smart collections
        sc = set()
        if hasattr(mw, "smart_collection_manager") and mw.smart_collection_manager:
            for c in mw.smart_collection_manager.get_all():
                sc.add(c.name)

        uncat = sort_fn(
            [g for g in mw.game_manager.get_uncategorized_games(sc) if not g.hidden and g.app_id in fids],
        )

        cats_data = OrderedDict()

        # 1. All Games
        cats_data[t("categories.all_games")] = vis

        # 2. Favorites
        if favs:
            cats_data[t("categories.favorites")] = favs

        # 3. User categories
        cats = mw.game_manager.get_all_categories()

        active = mw.cloud_storage_parser or mw.localconfig_helper
        if active:
            for pc in active.get_all_categories():
                if pc not in cats:
                    cats[pc] = 0

        # duplicates
        dups = {}
        if mw.cloud_storage_parser:
            dups = mw.cloud_storage_parser.get_duplicate_groups()

        # protected names
        from steam_library_manager.ui.constants import get_protected_collection_names

        spec = get_protected_collection_names() | {
            t("categories.soundtracks"),
            t("categories.tools"),
            t("categories.software"),
            t("categories.videos"),
        }

        dup_info = {}

        for cn in sorted(cats.keys(), key=self.german_sort_key):
            if cn in spec:
                continue

            if cn in dups:
                colls = dups[cn]
                tot = len(colls)
                for idx, coll in enumerate(colls):
                    apps = coll.get("added", coll.get("apps", []))
                    if not isinstance(apps, list):
                        apps = []
                    aids = set(apps)
                    cg = sort_fn(
                        [
                            g
                            for g in mw.game_manager.games.values()
                            if not g.hidden and int(g.app_id) in aids and g.app_id in fids
                        ],
                    )
                    dk = "__dup__%s__%d" % (cn, idx)
                    cats_data[dk] = cg
                    dup_info[dk] = (cn, idx + 1, tot)
            else:
                cg = sort_fn(
                    [g for g in mw.game_manager.get_games_by_category(cn) if not g.hidden and g.app_id in fids],
                )
                cats_data[cn] = cg

        # 4. Type categories
        _tf = {
            "music": "soundtracks",
            "tool": "tools",
            "application": "software",
            "video": "videos",
        }
        type_cats = self._get_type_cats(list(mw.game_manager.games.values()))
        for cn, gl in type_cats.items():
            fk = None
            for atv, fv in _tf.items():
                if t(_TYPE_MAP[atv]) == cn:
                    fk = fv
                    break
            if fk and not mw.filter_service.is_type_category_visible(fk):
                continue
            fg = [g for g in gl if g.app_id in fids]
            if fg:
                cats_data[cn] = fg

        # 5. Uncategorized
        if uncat:
            cats_data[t("categories.uncategorized")] = uncat

        # 6. Hidden
        if hid:
            cats_data[t("categories.hidden")] = hid

        # dynamic collections
        dyn = set()
        if mw.cloud_storage_parser:
            for c in mw.cloud_storage_parser.collections:
                if "filterSpec" in c:
                    dyn.add(c["name"])

        # external platforms
        ext = set()
        for cn in cats_data:
            if get_collection_emoji(cn):
                ext.add(cn)

        mw.tree.populate_categories(cats_data, dyn, dup_info, sc, ext)
