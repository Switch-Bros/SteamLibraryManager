#
# steam_library_manager/ui/actions/enrichment_starters.py
# Individual enrichment launchers for each data source
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from steam_library_manager.ui.widgets.ui_helper import UIHelper
from steam_library_manager.utils.i18n import t

if TYPE_CHECKING:
    from collections.abc import Callable

    from steam_library_manager.services.enrichment.base_enrichment_thread import BaseEnrichmentThread
    from steam_library_manager.ui.main_window import MainWindow

logger = logging.getLogger("steamlibmgr.enrichment_starters")

__all__ = ["EnrichmentStarters"]


@dataclass(frozen=True)
class _EnrichmentConfig:
    """Configuration for a generic DB-filter enrichment method."""

    filter_method: str
    title_key: str
    starting_key: str
    no_games_key: str


_ENRICHMENT_CONFIGS: dict[str, _EnrichmentConfig] = {
    "protondb": _EnrichmentConfig(
        filter_method="get_apps_without_protondb",
        title_key="ui.enrichment.protondb_title",
        starting_key="ui.enrichment.protondb_starting",
        no_games_key="ui.enrichment.no_games_protondb",
    ),
    "pegi": _EnrichmentConfig(
        filter_method="get_apps_without_pegi",
        title_key="ui.enrichment.pegi_title",
        starting_key="ui.enrichment.pegi_starting",
        no_games_key="ui.enrichment.no_games_pegi",
    ),
    "achievements": _EnrichmentConfig(
        filter_method="get_apps_without_achievements",
        title_key="ui.enrichment.achievement_title",
        starting_key="ui.enrichment.achievement_starting",
        no_games_key="ui.enrichment.no_games_achievements",
    ),
}


class EnrichmentStarters:
    """Individual enrichment starters for each data source."""

    def __init__(self, main_window: MainWindow) -> None:
        self.mw: MainWindow = main_window

    # Individual Starters

    def start_deck_enrichment(self, force_refresh: bool = False) -> None:
        """Starts deck status enrichment for games missing deck data."""
        from steam_library_manager.services.enrichment.deck_enrichment_service import DeckEnrichmentThread

        if not self.mw.game_manager:
            return

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

        from steam_library_manager.config import config

        cache_dir = config.DATA_DIR / "cache"

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
        """Starts HLTB enrichment for games missing HLTB data."""
        from steam_library_manager.integrations.hltb_api import HLTBClient
        from steam_library_manager.services.enrichment.enrichment_service import EnrichmentThread
        from steam_library_manager.ui.dialogs.enrichment_dialog import EnrichmentDialog

        if not HLTBClient.is_available():
            UIHelper.show_warning(self.mw, t("ui.enrichment.hltb_not_available"))
            return

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

        from steam_library_manager.config import config

        db_path = self._get_db_path()
        hltb_client = HLTBClient()

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

        dialog = EnrichmentDialog(t("ui.enrichment.hltb_title"), self.mw)
        dialog.start_thread(thread)
        dialog.exec()

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
        """Starts Steam API enrichment for games missing metadata."""
        from steam_library_manager.config import config
        from steam_library_manager.services.enrichment.enrichment_service import EnrichmentThread
        from steam_library_manager.ui.dialogs.enrichment_dialog import EnrichmentDialog

        api_key = config.STEAM_API_KEY
        if not api_key:
            UIHelper.show_warning(self.mw, t("ui.enrichment.no_api_key"))
            self._open_settings_api_tab()
            return

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

        db_path = self._get_db_path()

        thread = EnrichmentThread(self.mw)
        thread.configure_steam(games, db_path, api_key, force_refresh=force_refresh)

        dialog = EnrichmentDialog(t("ui.enrichment.steam_title"), self.mw)
        dialog.start_thread(thread)
        dialog.exec()

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
        """Starts achievement enrichment for games missing achievement data."""
        from steam_library_manager.config import config
        from steam_library_manager.services.enrichment.achievement_enrichment_service import AchievementEnrichmentThread

        api_key = config.STEAM_API_KEY
        if not api_key:
            UIHelper.show_warning(self.mw, t("ui.enrichment.no_api_key"))
            self._open_settings_api_tab()
            return
        steam_id = config.STEAM_USER_ID
        if not steam_id:
            UIHelper.show_warning(self.mw, t("ui.enrichment.no_steam_id"))
            return
        self._start_enrichment_generic(
            "achievements",
            AchievementEnrichmentThread,
            force_refresh,
            configure_kwargs={"api_key": api_key, "steam_id": steam_id},
        )

    def start_protondb_enrichment(self, force_refresh: bool = False) -> None:
        """Starts ProtonDB enrichment for games missing ProtonDB data."""
        from steam_library_manager.services.enrichment.protondb_enrichment_service import ProtonDBEnrichmentThread

        self._start_enrichment_generic("protondb", ProtonDBEnrichmentThread, force_refresh)

    def start_pegi_enrichment(self, force_refresh: bool = False) -> None:
        """Starts PEGI age rating enrichment for games missing ratings."""
        from steam_library_manager.services.enrichment.pegi_enrichment_service import PEGIEnrichmentThread

        language = "en"
        if hasattr(self.mw, "_i18n") and self.mw._i18n:
            language = self.mw._i18n.locale
        self._start_enrichment_generic(
            "pegi",
            PEGIEnrichmentThread,
            force_refresh,
            configure_kwargs={"language": language},
        )

    def start_curator_enrichment(self, force_refresh: bool = False) -> None:
        """Starts curator recommendation enrichment."""
        db = self._open_database()
        if db is None:
            return

        curators = db.get_all_curators() if force_refresh else db.get_curators_needing_refresh()
        db.close()

        if not curators:
            UIHelper.show_batch_result(
                self.mw,
                t("ui.enrichment.no_curators"),
                t("ui.enrichment.complete_title"),
            )
            return

        from steam_library_manager.services.enrichment.curator_enrichment_service import (
            CuratorEnrichmentThread,
        )

        db_path = self._get_db_path()
        if db_path is None:
            return

        thread = CuratorEnrichmentThread(self.mw)
        thread.configure(curators, db_path, force_refresh=force_refresh)
        callback = None if force_refresh else lambda: self.start_curator_enrichment(force_refresh=True)
        self._run_enrichment(
            thread,
            title_key="ui.enrichment.curator_title",
            starting_key="ui.enrichment.curator_starting",
            total=len(curators),
            force_refresh_callback=callback,
        )

    def start_tag_import(self) -> None:
        """Starts background import of tags from appinfo.vdf."""
        from steam_library_manager.config import config
        from steam_library_manager.services.enrichment.tag_import_service import TagImportThread

        steam_path = config.STEAM_PATH
        if not steam_path:
            UIHelper.show_warning(self.mw, t("ui.tag_import.no_steam_path"))
            return

        db_path = self._get_db_path()
        if db_path is None:
            return

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

        language = config.TAGS_LANGUAGE

        thread = TagImportThread(self.mw)
        thread.configure(steam_path, db_path, language)

        progress = UIHelper.create_progress_dialog(
            self.mw,
            t("ui.tag_import.starting"),
            maximum=0,
            title=t("ui.tag_import.dialog_title"),
        )

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
            self._refresh_games_from_db()
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

    # Generic Enrichment Infrastructure

    def _start_enrichment_generic(
        self,
        config_key: str,
        thread_cls: type[BaseEnrichmentThread],
        force_refresh: bool = False,
        configure_kwargs: dict[str, str] | None = None,
    ) -> None:
        """Generic enrichment launcher for DB-filter-based enrichments."""
        cfg = _ENRICHMENT_CONFIGS[config_key]
        db = self._open_database()
        if db is None:
            return
        games = db.get_all_game_ids() if force_refresh else getattr(db, cfg.filter_method)()
        db.close()
        if not games:
            if UIHelper.show_batch_result(
                self.mw,
                t(cfg.no_games_key),
                t("ui.enrichment.complete_title"),
            ) and UIHelper.confirm(
                self.mw,
                t("ui.enrichment.force_refresh_confirm"),
                title=t("ui.enrichment.force_refresh_title"),
            ):
                self._start_enrichment_generic(
                    config_key,
                    thread_cls,
                    True,
                    configure_kwargs,
                )
            return

        thread = thread_cls(self.mw)
        extra = configure_kwargs or {}
        thread.configure(games, self._get_db_path(), force_refresh=force_refresh, **extra)
        callback = (
            None
            if force_refresh
            else lambda: self._start_enrichment_generic(
                config_key,
                thread_cls,
                True,
                configure_kwargs,
            )
        )
        self._run_enrichment(
            thread,
            cfg.title_key,
            cfg.starting_key,
            len(games),
            callback,
        )

    def _run_enrichment(
        self,
        thread: BaseEnrichmentThread,
        title_key: str,
        starting_key: str,
        total: int,
        force_refresh_callback: Callable[[], None] | None = None,
    ) -> None:
        """Launches an enrichment thread with a modal progress dialog."""
        progress = UIHelper.create_progress_dialog(
            self.mw,
            t(starting_key),
            maximum=total,
            title=t(title_key),
        )

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
            self._refresh_games_from_db()
            self.mw.populate_categories()

        thread.progress.connect(on_progress)
        thread.finished_enrichment.connect(on_finished)
        progress.canceled.connect(thread.cancel)
        thread.start()

    # Helpers

    def _open_settings_api_tab(self) -> None:
        """Opens the Settings dialog on the API keys tab."""
        from steam_library_manager.ui.dialogs.settings_dialog import SettingsDialog

        dialog = SettingsDialog(self.mw)
        dialog.tabs.setCurrentIndex(1)
        dialog.settings_saved.connect(self.mw.settings_actions.apply_settings)
        dialog.exec()

    def _get_db_path(self):
        """Returns the database file path, or None if unavailable."""
        if hasattr(self.mw, "game_service") and self.mw.game_service:
            db = getattr(self.mw.game_service, "database", None)
            if db and hasattr(db, "db_path"):
                return db.db_path

        logger.warning("No database available for enrichment")
        return None

    def _refresh_games_from_db(self) -> None:
        """Sync in-memory Game objects with DB after enrichment writes."""
        db = self._open_database()
        if not db:
            return
        try:
            app_ids = [int(aid) for aid in self.mw.game_manager.games]

            all_tags = db._batch_get_related("game_tags", "tag", app_ids)
            all_tag_ids = db._batch_get_tag_ids(app_ids)
            all_genres = db._batch_get_related("game_genres", "genre", app_ids)

            # Refresh list fields
            for app_id_str, game in self.mw.game_manager.games.items():
                aid = int(app_id_str)
                game.tags = all_tags.get(aid, [])
                game.tag_ids = all_tag_ids.get(aid, [])
                game.genres = all_genres.get(aid, [])
        finally:
            db.close()

    def _open_database(self):
        """Opens a fresh database connection, or None if path unavailable."""
        from steam_library_manager.core.database import Database

        db_path = self._get_db_path()
        if db_path is None:
            return None
        return Database(db_path)
