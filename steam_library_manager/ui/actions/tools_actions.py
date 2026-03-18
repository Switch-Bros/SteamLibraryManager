#
# steam_library_manager/ui/actions/tools_actions.py
# Tools menu action handlers
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal
import requests

from steam_library_manager.utils.i18n import t
from steam_library_manager.utils.timeouts import HTTP_TIMEOUT
from steam_library_manager.ui.widgets.ui_helper import UIHelper
from steam_library_manager.ui.dialogs.missing_metadata_dialog import MissingMetadataDialog

__all__ = ["StoreCheckThread", "ToolsActions"]


class StoreCheckThread(QThread):
    # checks if game is on store
    finished = pyqtSignal(str, str)

    def __init__(self, aid):
        super().__init__()
        self.aid = aid

    _GEO_KW = (
        "not available in your country",
        "not available in your region",
        "unavailable in your region",
        "nicht in ihrem land",
        "dieses produkt steht in ihrem land",
        "currently unavailable",
        "error processing your request",
    )

    def run(self):
        try:
            u = "https://store.steampowered.com/app/%s/" % self.aid
            r = requests.get(
                u,
                timeout=HTTP_TIMEOUT,
                allow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
                    " (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                },
            )

            if r.status_code in (404, 403):
                self.finished.emit("removed", "%s %s" % (t("emoji.error"), t("ui.store_check.removed")))
                return

            if r.status_code != 200:
                self.finished.emit(
                    "unknown", "%s %s" % (t("emoji.unknown"), t("ui.store_check.unknown", code=r.status_code))
                )
                return

            fu = r.url
            txt = r.text.lower()

            if "agecheck" in fu or ("agecheck" in txt and "/app/%s" % self.aid in fu):
                self.finished.emit("age_gate", "%s %s" % (t("emoji.success"), t("ui.store_check.age_gate")))
                return

            if any(kw in txt for kw in self._GEO_KW):
                self.finished.emit("geo_locked", "%s %s" % (t("emoji.blocked"), t("ui.store_check.geo_locked")))
                return

            if "game_area_purchase" in txt or "app_header" in txt:
                self.finished.emit("available", "%s %s" % (t("emoji.success"), t("ui.store_check.available")))
                return

            if "/app/%s" % self.aid not in fu:
                self.finished.emit("delisted", "%s %s" % (t("emoji.error"), t("ui.store_check.delisted")))
                return

            self.finished.emit(
                "unknown", "%s %s" % (t("emoji.unknown"), t("ui.store_check.unknown", code=r.status_code))
            )

        except Exception as ex:
            self.finished.emit("unknown", str(ex))


class ToolsActions:
    """Tools menu handlers - external games, curators, health check.

    Also does the store availability check per game (background thread)
    and the full library health scan with progress dialog.
    """

    def __init__(self, win):
        self.mw = win
        self._st = None
        self._ht = None

    def show_external_games(self):
        from steam_library_manager.ui.dialogs.external_games_dialog import ExternalGamesDialog

        ExternalGamesDialog(self.mw).exec()

    def show_curator_manager(self):
        from steam_library_manager.ui.dialogs.curator_management_dialog import CuratorManagementDialog

        dbp = self._get_db_path()
        if dbp is None:
            UIHelper.show_warning(self.mw, t("ui.enrichment.no_curators"))
            return

        # collect existing names
        ns = set()
        if self.mw.game_manager:
            ns = set(self.mw.game_manager.get_all_categories().keys())
        if self.mw.cloud_storage_parser:
            ns.update(self.mw.cloud_storage_parser.get_all_categories())

        dlg = CuratorManagementDialog(self.mw, dbp, ns)
        dlg.exec()
        self._refresh_curator_cache()

    def _get_db_path(self):
        if hasattr(self.mw, "game_service") and self.mw.game_service:
            db = getattr(self.mw.game_service, "database", None)
            if db and hasattr(db, "db_path"):
                return db.db_path
        return None

    def _refresh_curator_cache(self):
        dbp = self._get_db_path()
        if not dbp:
            return
        from steam_library_manager.core.database import Database

        tmp = Database(dbp)
        try:
            cache = {}
            for c in tmp.get_active_curators():
                cid = c["curator_id"]
                cache[cid] = tmp.get_recommendations_for_curator(cid)
            self.mw.filter_service.set_curator_cache(cache)
        finally:
            tmp.close()

    def find_missing_metadata(self):
        if not self.mw.metadata_service:
            return
        affected = self.mw.metadata_service.find_missing_metadata()
        if affected:
            MissingMetadataDialog(self.mw, affected).exec()
        else:
            UIHelper.show_success(self.mw, t("ui.tools.missing_metadata.all_complete"))

    def check_store_availability(self, g):
        prog = UIHelper.create_progress_dialog(
            self.mw,
            t("ui.store_check.checking"),
            maximum=0,
            cancelable=False,
            title=t("ui.store_check.title"),
        )
        prog.show()

        def _done(st, det):
            prog.close()
            msg = "%s: %s" % (g.name, det)
            if st == "available":
                UIHelper.show_success(self.mw, msg, t("ui.store_check.title"))
            elif st == "age_gate":
                UIHelper.show_info(self.mw, msg, t("ui.store_check.title"))
            else:
                UIHelper.show_warning(self.mw, msg, t("ui.store_check.title"))

        self._st = StoreCheckThread(g.app_id)
        self._st.finished.connect(_done)
        self._st.start()

    def start_library_health_check(self):
        from steam_library_manager.config import config
        from steam_library_manager.services.library_health_thread import LibraryHealthThread
        from steam_library_manager.ui.dialogs.health_check_dialog import HealthCheckResultDialog

        if not self.mw.game_manager:
            return

        all_g = self.mw.game_manager.get_real_games()
        n = len(all_g)

        if not UIHelper.confirm(self.mw, t("health_check.confirm", count=n), t("health_check.title")):
            return

        games = []
        for x in all_g:
            try:
                games.append((int(x.app_id), x.name))
            except (ValueError, TypeError):
                continue

        key = config.STEAM_API_KEY or ""
        dbp = self._get_db_path()
        if not dbp:
            UIHelper.show_warning(self.mw, t("health_check.progress.starting"))
            return

        prog = UIHelper.create_progress_dialog(
            self.mw,
            t("health_check.progress.starting"),
            maximum=100,
            title=t("health_check.title"),
        )
        prog.show()

        self._ht = LibraryHealthThread(games, key, dbp, self.mw)

        def _prog(cur, tot, k):
            if prog.wasCanceled():
                self._ht.cancel()
                return
            pct = int((cur / max(tot, 1)) * 100)
            prog.setValue(pct)
            prog.setLabelText(t(k, current=cur, total=tot))

        def _phase(pk):
            prog.setLabelText(t(pk))

        def _fin(rep):
            prog.close()
            HealthCheckResultDialog(self.mw, rep).exec()

        self._ht.progress.connect(_prog)
        self._ht.phase_changed.connect(_phase)
        self._ht.finished_report.connect(_fin)
        prog.canceled.connect(self._ht.cancel)
        self._ht.start()
