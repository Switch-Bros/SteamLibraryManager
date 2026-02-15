"""Central startup orchestrator for non-blocking application bootstrap.

This service manages the entire startup sequence so the UI appears
immediately while data loads progressively in the background.

Architecture:
    Phase 1: Show loading state (instant, main thread)
    Phase 2: Quick init — validate paths, create GameService, init parsers
    Phase 3: Launch concurrent background workers (session + game loading)
    Phase 4: Completion — initialize services, populate tree, update UI
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSignal

from src.config import config
from src.utils.i18n import t

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow

logger = logging.getLogger("steamlibmgr.bootstrap_service")

__all__ = ["BootstrapService"]


class BootstrapService(QObject):
    """Orchestrates the non-blocking startup sequence.

    Emits signals at each phase so the UI can update progressively
    without blocking the main thread.

    Attributes:
        mw: Reference to the MainWindow instance.

    Signals:
        loading_started: Emitted when bootstrap begins (tree shows placeholder).
        load_progress: Emitted with (step, current, total) during game loading.
        persona_resolved: Emitted with the persona display name.
        session_restored: Emitted with success status after session restore.
        bootstrap_complete: Emitted when all loading is finished.
    """

    loading_started = pyqtSignal()
    load_progress = pyqtSignal(str, int, int)
    persona_resolved = pyqtSignal(str)
    session_restored = pyqtSignal(bool)
    bootstrap_complete = pyqtSignal()

    def __init__(self, main_window: MainWindow) -> None:
        """Initialize the bootstrap service.

        Args:
            main_window: The MainWindow instance to orchestrate.
        """
        super().__init__(parent=main_window)
        self.mw: MainWindow = main_window
        self._session_done: bool = False
        self._games_done: bool = False
        self._session_worker = None
        self._game_worker = None

    def start(self) -> None:
        """Begin the bootstrap sequence.

        Can be called multiple times (e.g. for reload via Ctrl+R).
        Resets internal state and launches all phases.
        """
        self._session_done = False
        self._games_done = False

        # Phase 1: Show loading state
        self.loading_started.emit()

        # Phase 2: Quick init (no HTTP, main thread)
        quick_init_ok = self._quick_init()
        if not quick_init_ok:
            self.bootstrap_complete.emit()
            return

        # Phase 3: Launch background workers concurrently
        self._start_session_worker()
        self._start_game_worker()

    def _quick_init(self) -> bool:
        """Validate Steam paths, create GameService, and initialize parsers.

        This runs on the main thread but is fast (no HTTP, no heavy I/O).
        Loads stored token synchronously from keyring (fast read) and sets
        it in config so game loading can use it immediately.

        Returns:
            True if initialization succeeded and workers can be started.
        """
        from src.ui.widgets.ui_helper import UIHelper

        if not config.STEAM_PATH:
            UIHelper.show_warning(self.mw, t("logs.main.steam_not_found"))
            self.mw.reload_btn.show()
            return False

        short_id, long_id = config.get_detected_user()
        target_id = config.STEAM_USER_ID if config.STEAM_USER_ID else long_id

        if not short_id and not target_id:
            UIHelper.show_warning(self.mw, t("ui.errors.no_users_found"))
            self.mw.reload_btn.show()
            return False

        # Store IDs for later use by workers
        self._short_id = short_id
        self._target_id = target_id

        # Show user ID immediately (persona name replaces it later via signal)
        display_id = self.mw.steam_username or target_id or short_id
        if display_id:
            self.mw.user_label.setText(t("ui.main_window.user_label", user_id=display_id))

        # Quick token load (keyring/file, no HTTP) so game loading can use it
        self._quick_token_load()

        # Initialize GameService
        from src.services.game_service import GameService

        self.mw.game_service = GameService(str(config.STEAM_PATH), config.STEAM_API_KEY, str(config.CACHE_DIR))

        # Initialize parsers through GameService
        config_path = config.get_localconfig_path(short_id)
        if not config_path:
            UIHelper.show_error(self.mw, t("ui.errors.localconfig_load_error"))
            self.mw.reload_btn.show()
            return False

        vdf_success, cloud_success = self.mw.game_service.initialize_parsers(str(config_path), short_id)

        if not vdf_success and not cloud_success:
            UIHelper.show_error(self.mw, t("ui.errors.localconfig_load_error"))
            self.mw.reload_btn.show()
            return False

        # Set references for backward compatibility
        self.mw.localconfig_helper = self.mw.game_service.localconfig_helper
        self.mw.cloud_storage_parser = self.mw.game_service.cloud_storage_parser

        return True

    def _quick_token_load(self) -> None:
        """Load stored tokens from keyring/file without HTTP.

        Sets config.STEAM_ACCESS_TOKEN so game loading can use the
        token immediately. The SessionRestoreWorker will refresh it
        in the background; if a new token is obtained, it replaces
        the stored one for next startup.
        """
        from src.core.token_store import TokenStore

        token_store = TokenStore()
        stored = token_store.load_tokens()

        if stored is None:
            return

        # Set token in config so GameService can access it during loading
        config.STEAM_ACCESS_TOKEN = stored.access_token
        self.mw.access_token = stored.access_token
        self.mw.refresh_token = stored.refresh_token

        if stored.steam_id:
            config.STEAM_USER_ID = stored.steam_id

    def _start_session_worker(self) -> None:
        """Launch the session restore worker in a background thread."""
        from src.ui.workers.session_restore_worker import SessionRestoreWorker

        self._session_worker = SessionRestoreWorker()
        self._session_worker.session_restored.connect(self._on_session_restored)
        self._session_worker.start()

    def _start_game_worker(self) -> None:
        """Launch the game load worker in a background thread."""
        from src.ui.workers.game_load_worker import GameLoadWorker

        self._game_worker = GameLoadWorker(self.mw.game_service, self._target_id or "local")
        self._game_worker.progress_update.connect(self._on_load_progress)
        self._game_worker.finished.connect(self._on_games_loaded)
        self._game_worker.start()

    def _on_session_restored(self, result) -> None:
        """Handle completion of the session restore worker.

        Updates MainWindow state with the restored session and emits
        signals to update toolbar and user label.

        Args:
            result: SessionRestoreResult from the worker.
        """
        self._session_done = True

        if result.success:
            # Update authenticated state
            self.mw.access_token = result.access_token
            self.mw.refresh_token = result.refresh_token
            self.mw.session = None
            config.STEAM_ACCESS_TOKEN = result.access_token

            if result.steam_id:
                config.STEAM_USER_ID = result.steam_id

            # Update persona name
            if result.persona_name:
                self.mw.steam_username = result.persona_name
                self.persona_resolved.emit(result.persona_name)
            elif result.steam_id:
                self.persona_resolved.emit(result.steam_id)

            self.mw.set_status(t("steam.login.session_restored"))
            self.session_restored.emit(True)
        else:
            self.mw.set_status(t("steam.login.token_expired"))
            self.session_restored.emit(False)

        self._check_complete()

    def _on_load_progress(self, step: str, current: int, total: int) -> None:
        """Forward game loading progress to the UI.

        Args:
            step: Description of the current loading step.
            current: Current progress count.
            total: Total items to process.
        """
        self.load_progress.emit(step, current, total)

    def _on_games_loaded(self, success: bool) -> None:
        """Handle completion of the game load worker.

        Initializes services and populates the tree — same logic as
        DataLoadHandler.on_load_finished() but without modal dialogs.

        Args:
            success: Whether game loading completed successfully.
        """
        from src.ui.widgets.ui_helper import UIHelper
        from src.integrations.steam_store import SteamStoreScraper

        self._games_done = True

        # Get game_manager reference from game_service
        self.mw.game_manager = self.mw.game_service.game_manager if self.mw.game_service else None

        if not success or not self.mw.game_manager or not self.mw.game_manager.games:
            UIHelper.show_warning(self.mw, t("ui.errors.no_games_found"))
            self.mw.reload_btn.show()
            self.mw.set_status(t("common.error"))
            self._check_complete()
            return

        # Initialize SteamStoreScraper (lightweight, no I/O)
        self.mw.steam_scraper = SteamStoreScraper(config.CACHE_DIR, config.TAGS_LANGUAGE)

        # Set appinfo_manager reference (already loaded by worker)
        self.mw.appinfo_manager = self.mw.game_service.appinfo_manager

        # Initialize CategoryService
        from src.services.category_service import CategoryService

        self.mw.category_service = CategoryService(
            localconfig_helper=self.mw.localconfig_helper,
            cloud_parser=self.mw.cloud_storage_parser,
            game_manager=self.mw.game_manager,
        )

        # Initialize MetadataService
        from src.services.metadata_service import MetadataService

        self.mw.metadata_service = MetadataService(
            appinfo_manager=self.mw.appinfo_manager,
            game_manager=self.mw.game_manager,
        )

        # Initialize AutoCategorizeService
        from src.services.autocategorize_service import AutoCategorizeService

        self.mw.autocategorize_service = AutoCategorizeService(
            game_manager=self.mw.game_manager,
            category_service=self.mw.category_service,
            steam_scraper=self.mw.steam_scraper,
        )

        # Populate tree and update status
        self.mw.populate_categories()

        status_msg = self.mw.game_manager.get_load_source_message()
        self.mw.set_status(status_msg)
        self.mw.reload_btn.hide()
        self.mw.update_statistics()

        # If session worker hasn't resolved persona yet, show target_id
        if not self.mw.steam_username:
            display_id = self._target_id or self._short_id
            if display_id:
                self.mw.user_label.setText(t("ui.main_window.user_label", user_id=display_id))

        self._check_complete()

    def _check_complete(self) -> None:
        """Emit bootstrap_complete when both workers have finished."""
        if self._session_done and self._games_done:
            self.bootstrap_complete.emit()
