#
# steam_library_manager/ui/handlers/data_load_handler.py
# Post-login data loading and profile-switch refresh
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
from steam_library_manager.config import config
from steam_library_manager.integrations.steam_store import SteamStoreScraper
from steam_library_manager.ui.widgets.ui_helper import UIHelper
from steam_library_manager.ui.workers import GameLoadWorker
from steam_library_manager.utils.i18n import t

logger = logging.getLogger("steamlibmgr.data_load_handler")

__all__ = ["DataLoadHandler"]


class DataLoadHandler:
    """Handles game reloading after Steam login.

    Uses inline progress (no modal). Initial startup goes
    through BootstrapService instead.
    """

    def __init__(self, mw):
        self.mw = mw
        self.load_worker = None

    def load_games_with_steam_login(self, sid, tok):
        # reload after auth
        logger.info(t("logs.auth.loading_games_after_login"))

        if isinstance(tok, str):
            logger.info(t("logs.auth.auth_mode_token"))
        else:
            logger.info(t("logs.auth.auth_mode_session"))

        # prefer bootstrap
        if hasattr(self.mw, "bootstrap_service") and self.mw.bootstrap_service:
            self.mw.bootstrap_service.start()
        else:
            self._load(sid)

    def _load(self, u):
        # inline progress
        if not self.mw.game_service:
            logger.error(t("logs.data_load.game_service_not_initialized"))
            return

        self.mw.tree.set_loading_state(True)

        self.load_worker = GameLoadWorker(self.mw.game_service, u)
        self.load_worker.progress_update.connect(self._prog)
        self.load_worker.finished.connect(self._fin)
        self.load_worker.start()

    def _prog(self, s, cur, tot):
        # update bar
        if hasattr(self.mw, "loading_label"):
            self.mw.loading_label.setText(s)
            self.mw.loading_label.setVisible(True)
        if hasattr(self.mw, "progress_bar") and tot > 0:
            pct = int((cur / tot) * 100)
            self.mw.progress_bar.setValue(pct)
            self.mw.progress_bar.setVisible(True)

    def _fin(self, win):
        # done
        if hasattr(self.mw, "loading_label"):
            self.mw.loading_label.setVisible(False)
        if hasattr(self.mw, "progress_bar"):
            self.mw.progress_bar.setVisible(False)

        self.mw.game_manager = self.mw.game_service.game_manager if self.mw.game_service else None

        if not win or not self.mw.game_manager or not self.mw.game_manager.games:
            UIHelper.show_warning(self.mw, t("ui.errors.no_games_found"))
            self.mw.reload_btn.show()
            self.mw.set_status(t("common.error"))
            return

        self.mw.steam_scraper = SteamStoreScraper(config.CACHE_DIR, config.TAGS_LANGUAGE)
        self.mw.appinfo_manager = self.mw.game_service.appinfo_manager

        # init svcs
        from steam_library_manager.services.category_service import CategoryService

        self.mw.category_service = CategoryService(
            localconfig_helper=self.mw.localconfig_helper,
            cloud_parser=self.mw.cloud_storage_parser,
            game_manager=self.mw.game_manager,
        )

        from steam_library_manager.services.metadata_service import MetadataService

        self.mw.metadata_service = MetadataService(
            appinfo_manager=self.mw.appinfo_manager,
            game_manager=self.mw.game_manager,
        )

        from steam_library_manager.services.autocategorize_service import AutoCategorizeService

        self.mw.autocategorize_service = AutoCategorizeService(
            game_mgr=self.mw.game_manager,
            cat_svc=self.mw.category_service,
            scraper=self.mw.steam_scraper,
        )

        self.mw.populate_categories()

        final_msg = self.mw.game_manager.get_load_source_message()
        self.mw.set_status(final_msg)
        self.mw.reload_btn.hide()
        self.mw.update_statistics()
