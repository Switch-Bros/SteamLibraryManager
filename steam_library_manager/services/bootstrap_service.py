#
# steam_library_manager/services/bootstrap_service.py
# Startup sequence: detect steam, load tokens, kick off workers
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from steam_library_manager.config import config
from steam_library_manager.utils.i18n import t

logger = logging.getLogger("steamlibmgr.bootstrap")

__all__ = ["BootstrapService"]


class BootstrapService(QObject):
    """Handles app startup - detect steam, validate paths, fire workers.

    Runs two background workers after quick init:
        - session restore (token refresh + persona name lookup)
        - game loading (api, local files, db enrichment)

    Emits bootstrap_complete when both are done.
    """

    loading_started = pyqtSignal()
    load_progress = pyqtSignal(str, int, int)
    persona_resolved = pyqtSignal(str)
    session_restored = pyqtSignal(bool)
    bootstrap_complete = pyqtSignal()

    def __init__(self, main_window):
        super().__init__(parent=main_window)
        self.mw = main_window
        self._sess_done = False
        self._games_done = False
        self._sess_w = None
        self._game_w = None

    def start(self):
        self._sess_done = False
        self._games_done = False
        self.loading_started.emit()

        if not self._init():
            self.bootstrap_complete.emit()
            return

        # session restore first, games load after token is ready
        self._launch_sess()

    def _init(self):
        # validate steam paths, create game service, init parsers
        from steam_library_manager.ui.widgets.ui_helper import UIHelper

        if not config.STEAM_PATH:
            UIHelper.show_warning(self.mw, t("logs.main.steam_not_found"))
            self.mw.reload_btn.show()
            return False

        sid, lid = config.get_detected_user()
        tgt = config.STEAM_USER_ID if config.STEAM_USER_ID else lid

        if not sid and not tgt:
            UIHelper.show_warning(self.mw, t("ui.errors.no_users_found"))
            self.mw.reload_btn.show()
            return False

        self._sid = sid
        self._tid = tgt

        # show user id, persona comes later
        d = self.mw.steam_username or tgt or sid
        if d:
            self.mw.user_label.setText(t("ui.main_window.user_label", user_id=d))

        self._load_tokens()

        # setup game service
        from steam_library_manager.services.game_service import GameService

        self.mw.game_service = GameService(str(config.STEAM_PATH), config.STEAM_API_KEY, str(config.CACHE_DIR))

        cfg = config.get_localconfig_path(sid)
        if not cfg:
            UIHelper.show_error(self.mw, t("ui.errors.localconfig_load_error"))
            self.mw.reload_btn.show()
            return False

        v_ok, c_ok = self.mw.game_service.initialize_parsers(str(cfg), sid)

        if not v_ok and not c_ok:
            UIHelper.show_error(self.mw, t("ui.errors.localconfig_load_error"))
            self.mw.reload_btn.show()
            return False

        # compat refs
        self.mw.localconfig_helper = self.mw.game_service.localconfig_helper
        self.mw.cloud_storage_parser = self.mw.game_service.cloud_storage_parser

        return True

    def _load_tokens(self):
        # grab from keyring, no network
        from steam_library_manager.core.token_store import TokenStore

        store = TokenStore()
        tok = store.load_tokens()

        if not tok:
            return

        config.STEAM_ACCESS_TOKEN = tok.access_token
        self.mw.access_token = tok.access_token
        self.mw.refresh_token = tok.refresh_token

        if tok.steam_id:
            config.STEAM_USER_ID = tok.steam_id

    def _launch_sess(self):
        from steam_library_manager.ui.workers.session_restore_worker import SessionRestoreWorker

        self._sess_w = SessionRestoreWorker()
        self._sess_w.session_restored.connect(self._on_sess)
        self._sess_w.start()

        # safety net: if session restore hangs, load games anyway after 15s
        self._sess_timer = QTimer(self)
        self._sess_timer.setSingleShot(True)
        self._sess_timer.timeout.connect(self._on_sess_timeout)
        self._sess_timer.start(15000)

    def _launch_games(self):
        from steam_library_manager.ui.workers.game_load_worker import GameLoadWorker

        self._game_w = GameLoadWorker(self.mw.game_service, self._tid or "local")
        self._game_w.progress_update.connect(self._on_prog)
        self._game_w.finished.connect(self._on_games)
        self._game_w.start()

    def _on_sess_timeout(self):
        if not self._sess_done:
            logger.warning("session restore timed out after 15s - loading games without API")
            self._sess_done = True
            self.session_restored.emit(False)
            self._launch_games()

    def _on_sess(self, res):
        # stop safety timer
        if hasattr(self, "_sess_timer"):
            self._sess_timer.stop()

        self._sess_done = True

        if res.success:
            # update token BEFORE game loading starts
            self.mw.access_token = res.access_token
            self.mw.refresh_token = res.refresh_token
            self.mw.session = None
            config.STEAM_ACCESS_TOKEN = res.access_token

            if res.steam_id:
                config.STEAM_USER_ID = res.steam_id

            if res.persona_name:
                self.mw.steam_username = res.persona_name
                self.persona_resolved.emit(res.persona_name)
            elif res.steam_id:
                self.persona_resolved.emit(res.steam_id)

            logger.info("session restored, token valid - starting game load")
            self.mw.set_status(t("steam.login.session_restored"))
            self.session_restored.emit(True)
        else:
            logger.info("session restore failed - loading games without API")
            self.mw.set_status(t("steam.login.token_expired"))
            self.session_restored.emit(False)

        # NOW load games - with fresh (or no) token
        self._launch_games()

    def _on_prog(self, step, cur, tot):
        self.load_progress.emit(step, cur, tot)

    def _on_games(self, ok):
        from steam_library_manager.ui.widgets.ui_helper import UIHelper
        from steam_library_manager.integrations.steam_store import SteamStoreScraper

        self._games_done = True
        self.mw.game_manager = self.mw.game_service.game_manager if self.mw.game_service else None

        if not ok or not self.mw.game_manager or not self.mw.game_manager.games:
            UIHelper.show_warning(self.mw, t("ui.errors.no_games_found"))
            self.mw.reload_btn.show()
            self.mw.set_status(t("common.error"))
            self._check_done()
            return

        # scraper for tags
        self.mw.steam_scraper = SteamStoreScraper(config.CACHE_DIR, config.TAGS_LANGUAGE)
        self.mw.appinfo_manager = self.mw.game_service.appinfo_manager

        # wire up services
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

        # smart collections (always init, db auto-created)
        if self.mw.game_manager:
            from steam_library_manager.core.database import Database
            from steam_library_manager.services.smart_collections.smart_collection_manager import SmartCollectionManager

            dbp = config.DATA_DIR / "metadata.db"
            sdb = Database(dbp)
            self.mw.smart_collection_manager = SmartCollectionManager(
                database=sdb,
                game_manager=self.mw.game_manager,
                category_service=self.mw.category_service,
            )

            self.mw.smart_collection_manager.recover_from_sidecar()

            from steam_library_manager.utils.tag_resolver import TagResolver

            tr = TagResolver(sdb)
            tr.ensure_loaded()
            self.mw.tag_resolver = tr

        # refresh smart collections with fresh tag data before populating
        if self.mw.smart_collection_manager:
            self.mw.smart_collection_manager.refresh()
        self.mw.populate_categories()
        self.mw.set_status(self.mw.game_manager.get_load_source_message())
        self.mw.reload_btn.hide()
        self.mw.update_statistics()

        if not self.mw.steam_username:
            d = self._tid or self._sid
            if d:
                self.mw.user_label.setText(t("ui.main_window.user_label", user_id=d))

        self._check_done()

    def _check_done(self):
        if self._sess_done and self._games_done:
            self.bootstrap_complete.emit()
