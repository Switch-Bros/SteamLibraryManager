"""Action handler for metadata enrichment operations.

Provides start methods for HLTB and Steam API enrichment that check
preconditions, create the EnrichmentThread, and launch the progress dialog.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.ui.widgets.ui_helper import UIHelper
from src.utils.i18n import t

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.services.enrichment.base_enrichment_thread import BaseEnrichmentThread
    from src.ui.main_window import MainWindow

logger = logging.getLogger("steamlibmgr.enrichment_actions")

__all__ = ["EnrichmentActions"]


class EnrichmentActions:
    """Handles enrichment-related menu actions.

    Checks preconditions (API keys, library availability, games to enrich)
    and launches the enrichment dialog with a background thread.

    Attributes:
        mw: Back-reference to the owning MainWindow instance.
    """

    def __init__(self, main_window: MainWindow) -> None:
        """Initializes the EnrichmentActions handler.

        Args:
            main_window: The MainWindow instance that owns these actions.
        """
        self.mw: MainWindow = main_window

    def start_deck_enrichment(self, force_refresh: bool = False) -> None:
        """Starts deck status enrichment for games missing deck data.

        Filters games with no or 'unknown' deck status, then launches
        the DeckEnrichmentThread with a progress dialog.

        Args:
            force_refresh: If True, re-fetch all games.
        """
        from src.services.enrichment.deck_enrichment_service import DeckEnrichmentThread

        if not self.mw.game_manager:
            return

        # Filter games
        all_games = self.mw.game_manager.get_real_games()
        if force_refresh:
            games_to_enrich = all_games
        else:
            games_to_enrich = [g for g in all_games if not g.steam_deck_status or g.steam_deck_status == "unknown"]

        if not games_to_enrich:
            if UIHelper.show_batch_result(
                self.mw,
                t("ui.enrichment.no_games_deck"),
                t("ui.enrichment.complete_title"),
            ) and UIHelper.confirm(
                self.mw,
                t("ui.enrichment.force_refresh_confirm"),
                title=t("ui.enrichment.force_refresh_title"),
            ):
                self.start_deck_enrichment(force_refresh=True)
            return

        # Determine cache directory
        from src.config import config

        cache_dir = config.DATA_DIR / "cache"

        # Create and launch thread
        thread = DeckEnrichmentThread(self.mw)
        thread.configure(games_to_enrich, cache_dir, force_refresh=force_refresh)
        callback = None if force_refresh else lambda: self.start_deck_enrichment(force_refresh=True)
        self._run_enrichment(
            thread,
            title_key="ui.enrichment.deck_title",
            starting_key="ui.enrichment.deck_starting",
            total=len(games_to_enrich),
            force_refresh_callback=callback,
        )

    def start_hltb_enrichment(self, force_refresh: bool = False) -> None:
        """Starts HLTB enrichment for games missing HLTB data.

        Checks that howlongtobeatpy is installed and that there are
        games without HLTB data. Launches the enrichment dialog.

        Args:
            force_refresh: If True, re-fetch all games.
        """
        from src.integrations.hltb_api import HLTBClient
        from src.services.enrichment.enrichment_service import EnrichmentThread
        from src.ui.dialogs.enrichment_dialog import EnrichmentDialog

        # Check library availability
        if not HLTBClient.is_available():
            UIHelper.show_warning(self.mw, t("ui.enrichment.hltb_not_available"))
            return

        # Check database
        db = self._open_database()
        if db is None:
            return

        if force_refresh:
            games = db.get_all_game_ids()
        else:
            games = db.get_apps_without_hltb()
        db.close()
        if not games:
            if UIHelper.show_batch_result(
                self.mw,
                t("ui.enrichment.no_games_hltb"),
                t("ui.enrichment.complete_title"),
            ) and UIHelper.confirm(
                self.mw,
                t("ui.enrichment.force_refresh_confirm"),
                title=t("ui.enrichment.force_refresh_title"),
            ):
                self.start_hltb_enrichment(force_refresh=True)
            return

        # Create thread with HLTB configuration
        from src.config import config

        db_path = self._get_db_path()
        hltb_client = HLTBClient()

        # Get 64-bit Steam ID for Steam Import prefetch
        steam_user_id_64 = ""
        if config.STEAM_USER_ID:
            steam_user_id_64 = config.STEAM_USER_ID
        else:
            _, detected_id_64 = config.get_detected_user()
            if detected_id_64:
                steam_user_id_64 = detected_id_64

        thread = EnrichmentThread(self.mw)
        thread.configure_hltb(
            games,
            db_path,
            hltb_client,
            steam_user_id=steam_user_id_64,
            force_refresh=force_refresh,
        )

        # Create dialog — thread starts in showEvent
        dialog = EnrichmentDialog(t("ui.enrichment.hltb_title"), self.mw)
        dialog.start_thread(thread)
        dialog.exec()

        # Check if user wants force refresh from batch result
        if not force_refresh and dialog.wants_force_refresh:
            if UIHelper.confirm(
                self.mw,
                t("ui.enrichment.force_refresh_confirm"),
                title=t("ui.enrichment.force_refresh_title"),
            ):
                self.start_hltb_enrichment(force_refresh=True)
                return

        self.mw.populate_categories()

    def start_steam_api_enrichment(self, force_refresh: bool = False) -> None:
        """Starts Steam API enrichment for games missing metadata.

        Checks that an API key is configured and that there are
        games with missing metadata. Launches the enrichment dialog.

        Args:
            force_refresh: If True, re-fetch all games.
        """
        from src.config import config
        from src.services.enrichment.enrichment_service import EnrichmentThread
        from src.ui.dialogs.enrichment_dialog import EnrichmentDialog

        # Check API key
        api_key = config.STEAM_API_KEY
        if not api_key:
            UIHelper.show_warning(self.mw, t("ui.enrichment.no_api_key"))
            self._open_settings_api_tab()
            return

        # Check database
        db = self._open_database()
        if db is None:
            return

        if force_refresh:
            games = db.get_all_game_ids()
        else:
            games = db.get_apps_missing_metadata()
        db.close()
        if not games:
            if UIHelper.show_batch_result(
                self.mw,
                t("ui.enrichment.no_games_steam"),
                t("ui.enrichment.complete_title"),
            ) and UIHelper.confirm(
                self.mw,
                t("ui.enrichment.force_refresh_confirm"),
                title=t("ui.enrichment.force_refresh_title"),
            ):
                self.start_steam_api_enrichment(force_refresh=True)
            return

        # Create thread with Steam API configuration
        db_path = self._get_db_path()

        thread = EnrichmentThread(self.mw)
        thread.configure_steam(games, db_path, api_key, force_refresh=force_refresh)

        # Create dialog — thread starts in showEvent
        dialog = EnrichmentDialog(t("ui.enrichment.steam_title"), self.mw)
        dialog.start_thread(thread)
        dialog.exec()

        # Check if user wants force refresh from batch result
        if not force_refresh and dialog.wants_force_refresh:
            if UIHelper.confirm(
                self.mw,
                t("ui.enrichment.force_refresh_confirm"),
                title=t("ui.enrichment.force_refresh_title"),
            ):
                self.start_steam_api_enrichment(force_refresh=True)
                return

        self.mw.populate_categories()

    def start_achievement_enrichment(self, force_refresh: bool = False) -> None:
        """Starts achievement enrichment for games missing achievement data.

        Checks that an API key and Steam ID are configured, then launches
        the AchievementEnrichmentThread with a progress dialog.

        Args:
            force_refresh: If True, re-fetch all games.
        """
        from src.config import config
        from src.services.enrichment.achievement_enrichment_service import AchievementEnrichmentThread

        # Check API key
        api_key = config.STEAM_API_KEY
        if not api_key:
            UIHelper.show_warning(self.mw, t("ui.enrichment.no_api_key"))
            self._open_settings_api_tab()
            return

        # Check Steam user ID
        steam_id = config.STEAM_USER_ID
        if not steam_id:
            UIHelper.show_warning(self.mw, t("ui.enrichment.no_steam_id"))
            return

        # Check database
        db = self._open_database()
        if db is None:
            return

        if force_refresh:
            games = db.get_all_game_ids()
        else:
            games = db.get_apps_without_achievements()
        db.close()
        if not games:
            if UIHelper.show_batch_result(
                self.mw,
                t("ui.enrichment.no_games_achievements"),
                t("ui.enrichment.complete_title"),
            ) and UIHelper.confirm(
                self.mw,
                t("ui.enrichment.force_refresh_confirm"),
                title=t("ui.enrichment.force_refresh_title"),
            ):
                self.start_achievement_enrichment(force_refresh=True)
            return

        # Create and launch thread
        db_path = self._get_db_path()
        thread = AchievementEnrichmentThread(self.mw)
        thread.configure(games, db_path, api_key, steam_id, force_refresh=force_refresh)
        callback = None if force_refresh else lambda: self.start_achievement_enrichment(force_refresh=True)
        self._run_enrichment(
            thread,
            title_key="ui.enrichment.achievement_title",
            starting_key="ui.enrichment.achievement_starting",
            total=len(games),
            force_refresh_callback=callback,
        )

    def _run_enrichment(
        self,
        thread: BaseEnrichmentThread,
        title_key: str,
        starting_key: str,
        total: int,
        force_refresh_callback: Callable[[], None] | None = None,
    ) -> None:
        """Launches an enrichment thread with a modal progress dialog.

        Generic helper that de-duplicates the QProgressDialog setup shared
        by deck, achievement, and similar enrichment launchers.

        Args:
            thread: Configured enrichment thread ready to start.
            title_key: i18n key for the progress dialog title.
            starting_key: i18n key for the initial progress label.
            total: Total number of items to process.
            force_refresh_callback: If provided, completion dialog offers
                a force-refresh button that triggers this callback.
        """
        progress = UIHelper.create_progress_dialog(
            self.mw,
            t(starting_key),
            maximum=total,
            title=t(title_key),
        )

        # Keep references alive to prevent garbage collection
        self._active_thread = thread
        self._active_progress = progress

        def on_progress(text: str, current: int, _total: int) -> None:
            if progress.wasCanceled():
                thread.cancel()
                return
            progress.setValue(current)
            progress.setLabelText(text)

        def on_finished(success: int, failed: int) -> None:
            progress.close()
            if force_refresh_callback:
                wants_refresh = UIHelper.show_batch_result(
                    self.mw,
                    t("ui.enrichment.complete", success=success, failed=failed),
                    t("ui.enrichment.complete_title"),
                )
                if wants_refresh and UIHelper.confirm(
                    self.mw,
                    t("ui.enrichment.force_refresh_confirm"),
                    title=t("ui.enrichment.force_refresh_title"),
                ):
                    force_refresh_callback()
                    return
            else:
                UIHelper.show_success(
                    self.mw,
                    t("ui.enrichment.complete", success=success, failed=failed),
                )
            self.mw.populate_categories()

        thread.progress.connect(on_progress)
        thread.finished_enrichment.connect(on_finished)
        progress.canceled.connect(thread.cancel)
        thread.start()

    def start_protondb_enrichment(self, force_refresh: bool = False) -> None:
        """Starts ProtonDB enrichment for games missing ProtonDB data.

        Checks that there are games without ProtonDB ratings, then
        launches the ProtonDBEnrichmentThread with a progress dialog.

        Args:
            force_refresh: If True, re-fetch all games.
        """
        from src.services.enrichment.protondb_enrichment_service import ProtonDBEnrichmentThread

        # Check database
        db = self._open_database()
        if db is None:
            return

        if force_refresh:
            games = db.get_all_game_ids()
        else:
            games = db.get_apps_without_protondb()
        db.close()
        if not games:
            if UIHelper.show_batch_result(
                self.mw,
                t("ui.enrichment.no_games_protondb"),
                t("ui.enrichment.complete_title"),
            ) and UIHelper.confirm(
                self.mw,
                t("ui.enrichment.force_refresh_confirm"),
                title=t("ui.enrichment.force_refresh_title"),
            ):
                self.start_protondb_enrichment(force_refresh=True)
            return

        # Create and launch thread
        db_path = self._get_db_path()
        thread = ProtonDBEnrichmentThread(self.mw)
        thread.configure(games, db_path, force_refresh=force_refresh)
        callback = None if force_refresh else lambda: self.start_protondb_enrichment(force_refresh=True)
        self._run_enrichment(
            thread,
            title_key="ui.enrichment.protondb_title",
            starting_key="ui.enrichment.protondb_starting",
            total=len(games),
            force_refresh_callback=callback,
        )

    def start_tag_import(self) -> None:
        """Starts background import of tags from appinfo.vdf.

        Parses the binary appinfo.vdf, extracts store_tags (TagIDs),
        resolves them to localized names, and stores in the database.
        """
        from src.config import config
        from src.services.enrichment.tag_import_service import TagImportThread

        # Check Steam path
        steam_path = config.STEAM_PATH
        if not steam_path:
            UIHelper.show_warning(self.mw, t("ui.tag_import.no_steam_path"))
            return

        # Check database
        db_path = self._get_db_path()
        if db_path is None:
            return

        # Check if tags already exist
        db = self._open_database()
        if db:
            tag_count = db.get_game_tag_count()
            db.close()
            if tag_count > 0:
                if not UIHelper.confirm(
                    self.mw,
                    t("ui.tag_import.already_populated", count=tag_count),
                    title=t("ui.tag_import.dialog_title"),
                ):
                    return

        # Determine language
        language = "en"
        if hasattr(self.mw, "tag_resolver") and self.mw.tag_resolver:
            i18n = getattr(self.mw, "_i18n", None)
            if i18n:
                language = i18n.locale

        # Create thread
        thread = TagImportThread(self.mw)
        thread.configure(steam_path, db_path, language)

        # Create progress dialog
        progress = UIHelper.create_progress_dialog(
            self.mw,
            t("ui.tag_import.starting"),
            maximum=0,
            title=t("ui.tag_import.dialog_title"),
        )

        # Keep references alive
        self._tag_import_thread = thread
        self._tag_import_progress = progress

        def on_progress(text: str, current: int, total: int) -> None:
            if progress.wasCanceled():
                thread.cancel()
                return
            if total > 0:
                progress.setMaximum(total)
            progress.setValue(current)
            progress.setLabelText(text)

        def on_finished(games_tagged: int, total_tags: int) -> None:
            progress.close()
            UIHelper.show_success(
                self.mw,
                t("ui.tag_import.complete", games=games_tagged, tags=total_tags),
            )
            self.mw.populate_categories()

        def on_error(msg: str) -> None:
            progress.close()
            UIHelper.show_warning(self.mw, msg)

        thread.progress.connect(on_progress)
        thread.finished_import.connect(on_finished)
        thread.error.connect(on_error)
        progress.canceled.connect(thread.cancel)
        thread.start()

    def start_enrich_all(self) -> None:
        """Starts a full refresh of all enrichment data.

        Runs tag import followed by four parallel tracks:
        Steam API (metadata + achievements), HLTB, ProtonDB, and Deck.
        """
        from src.config import config
        from src.services.enrichment.enrich_all_coordinator import EnrichAllCoordinator
        from src.ui.dialogs.enrich_all_progress_dialog import EnrichAllProgressDialog

        # Check prerequisites
        if not self.mw.game_manager:
            return

        api_key = config.STEAM_API_KEY
        if not api_key:
            UIHelper.show_warning(self.mw, t("ui.enrichment.no_api_key"))
            self._open_settings_api_tab()
            return

        # Resolve Steam user ID
        steam_id = config.STEAM_USER_ID or ""
        if not steam_id:
            _, detected_id = config.get_detected_user()
            if detected_id:
                steam_id = detected_id

        # Get game lists
        all_deck_games = self.mw.game_manager.get_real_games()
        db = self._open_database()
        if db is None:
            return
        all_db_games = db.get_all_game_ids()
        db.close()

        if not all_db_games:
            UIHelper.show_info(self.mw, t("ui.enrichment.no_games_steam"))
            return

        # Confirm with user
        if not UIHelper.confirm(
            self.mw,
            t("ui.enrichment.enrich_all_confirm", count=len(all_db_games)),
            title=t("ui.enrichment.enrich_all_title"),
        ):
            return

        # Check HLTB availability
        hltb_client = None
        try:
            from src.integrations.hltb_api import HLTBClient

            if HLTBClient.is_available():
                hltb_client = HLTBClient()
        except ImportError:
            pass

        # Gather paths and config
        db_path = self._get_db_path()
        if db_path is None:
            return

        steam_path = config.STEAM_PATH
        cache_dir = config.DATA_DIR / "cache"

        language = "en"
        if hasattr(self.mw, "tag_resolver") and self.mw.tag_resolver:
            i18n = getattr(self.mw, "_i18n", None)
            if i18n:
                language = i18n.locale

        # Create dialog and coordinator (coordinator parented to dialog)
        dialog = EnrichAllProgressDialog(self.mw)
        coordinator = EnrichAllCoordinator(dialog)
        coordinator.configure(
            db_path=db_path,
            api_key=api_key,
            steam_id=steam_id,
            steam_path=steam_path,
            games_deck=all_deck_games,
            games_db=all_db_games,
            hltb_client=hltb_client,
            language=language,
            cache_dir=cache_dir,
        )

        dialog.set_coordinator(coordinator)
        dialog.exec()

        self.mw.populate_categories()

    def _open_settings_api_tab(self) -> None:
        """Opens the Settings dialog on the API keys tab."""
        from src.ui.dialogs.settings_dialog import SettingsDialog

        dialog = SettingsDialog(self.mw)
        dialog.tabs.setCurrentIndex(1)  # "Other" tab with API keys
        dialog.settings_saved.connect(self.mw.settings_actions.apply_settings)
        dialog.exec()

    def _get_db_path(self):
        """Returns the database file path from the active game service.

        Returns:
            Path to the SQLite database, or None if not available.
        """
        if hasattr(self.mw, "game_service") and self.mw.game_service:
            db = getattr(self.mw.game_service, "database", None)
            if db and hasattr(db, "db_path"):
                return db.db_path

        logger.warning("No database available for enrichment")
        return None

    def _open_database(self):
        """Opens a fresh database connection for enrichment operations.

        Creates a new Database instance to avoid SQLite threading issues,
        since the main database may have been created in a different thread.

        Returns:
            New Database instance, or None if path not available.
        """
        from src.core.database import Database

        db_path = self._get_db_path()
        if db_path is None:
            return None
        return Database(db_path)
