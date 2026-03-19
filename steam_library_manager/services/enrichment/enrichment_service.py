#
# steam_library_manager/services/enrichment/enrichment_service.py
# Coordinator that dispatches and tracks all enrichment services
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

from steam_library_manager.services.enrichment.base_enrichment_thread import BaseEnrichmentThread
from steam_library_manager.utils.age_ratings import convert_to_pegi
from steam_library_manager.utils.i18n import t

if TYPE_CHECKING:
    from steam_library_manager.integrations.hltb_api import HLTBClient

logger = logging.getLogger("steamlibmgr.enrichment_service")

__all__ = ["EnrichmentThread"]


class EnrichmentThread(BaseEnrichmentThread):
    """Thread for enriching game metadata from external APIs."""

    def __init__(self, parent=None):
        # init thread
        super().__init__(parent)
        self._mode = ""
        self._games = []
        self._db_path = None
        self._hltb_client = None
        self._steam_user_id = ""
        self._api_key = ""
        self._db = None

    def configure_hltb(self, games, db_path: Path, hltb_client: HLTBClient, steam_user_id="", force_refresh=False):
        # setup for HLTB mode
        self._mode = "hltb"
        self._games = games
        self._db_path = db_path
        self._hltb_client = hltb_client
        self._steam_user_id = steam_user_id
        self._force_refresh = force_refresh

    def configure_steam(self, games, db_path: Path, api_key, force_refresh=False):
        # setup for Steam API mode
        self._mode = "steam"
        self._games = games
        self._db_path = db_path
        self._api_key = api_key
        self._force_refresh = force_refresh

    def run(self):
        # dispatch to correct handler
        if self._mode == "hltb":
            super().run()
        elif self._mode == "steam":
            self._run_steam()

    # --- HLTB mode hooks ---

    def _setup(self):
        # open db and load cache
        from steam_library_manager.core.database import Database

        self._db = Database(self._db_path)

        # load existing mappings
        cached = self._db.load_hltb_id_cache()

        # if empty and we have steam ID, fetch from API
        if not cached and self._steam_user_id and self._hltb_client:
            self.progress.emit(
                t("ui.enrichment.steam_import_loading"),
                0,
                len(self._games),
            )
            api_mappings = self._hltb_client.fetch_steam_import(self._steam_user_id)
            if api_mappings:
                self._db.save_hltb_id_cache(api_mappings)
                cached = api_mappings
                logger.info("HLTB Steam Import: saved %d mappings to DB", len(api_mappings))

        # populate client cache
        if cached and self._hltb_client:
            self._hltb_client.set_id_cache(cached)

    def _cleanup(self):
        # close db connection
        if self._db:
            self._db.close()
            self._db = None

    def _get_items(self):
        # return games list
        return self._games

    def _process_item(self, item):
        # enrich single game with HLTB data
        app_id, name = item
        result = self._hltb_client.search_game(name, app_id)

        if result:
            has_times = any((result.main_story, result.main_extras, result.completionist))
            self._db.conn.execute(
                """
                INSERT OR REPLACE INTO hltb_data
                (app_id, main_story, main_extras, completionist, last_updated)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    app_id,
                    result.main_story,
                    result.main_extras,
                    result.completionist,
                    int(time.time()),
                ),
            )
            self._db.conn.commit()

            if has_times:
                return True

            logger.debug("HLTB matched '%s' but 0h times, saved as checked", name)
            return False

        # mark as checked with NULL times so it won't be retried
        # dunno why HLTB returns empty results but we need to track it
        self._db.conn.execute(
            """
            INSERT OR REPLACE INTO hltb_data
            (app_id, main_story, main_extras, completionist, last_updated)
            VALUES (?, NULL, NULL, NULL, ?)
            """,
            (app_id, int(time.time())),
        )
        self._db.conn.commit()
        logger.info("HLTB miss: %d '%s' (marked as checked)", app_id, name)
        return False

    def _format_progress(self, item, current, total):
        # format progress text with game name
        _app_id, name = item
        return t("ui.enrichment.progress", name=name, current=current, total=total)

    def _rate_limit(self):
        # sleep between requests - HLTB gets angry if we go too fast
        time.sleep(0.2)

    # --- Steam API mode ---

    def _run_steam(self):
        # batch enrich from Steam Web API
        from steam_library_manager.core.database import Database
        from steam_library_manager.integrations.steam_web_api import SteamWebAPI

        self._cancelled = False
        total = len(self._games)

        if not self._api_key:
            self.error.emit(t("ui.enrichment.no_api_key"))
            return

        try:
            api = SteamWebAPI(self._api_key)
        except ValueError as exc:
            self.error.emit(str(exc))
            return

        app_ids = [aid for aid, _ in self._games]
        success = 0
        failed = 0

        db = Database(self._db_path)
        try:
            batch_size = 50
            for batch_start in range(0, len(app_ids), batch_size):
                if self._cancelled:
                    break

                batch = app_ids[batch_start : batch_start + batch_size]
                current = min(batch_start + batch_size, total)

                batch_name = "Batch %d" % (batch_start // batch_size + 1)
                self.progress.emit(
                    t("ui.enrichment.progress", name=batch_name, current=current, total=total),
                    current,
                    total,
                )

                try:
                    details_map = api.get_app_details_batch(batch)

                    for aid, details in details_map.items():
                        update_fields = {}
                        if details.name:
                            update_fields["name"] = details.name
                        if details.developers:
                            update_fields["developer"] = ", ".join(details.developers)
                        if details.publishers:
                            update_fields["publisher"] = ", ".join(details.publishers)
                        if details.review_score:
                            update_fields["review_score"] = details.review_score
                        if details.steam_release_date:
                            update_fields["steam_release_date"] = details.steam_release_date
                        if details.original_release_date:
                            update_fields["original_release_date"] = details.original_release_date

                        if update_fields:
                            db.upsert_game_metadata(aid, **update_fields)

                        if details.languages:
                            lang_dict = {
                                lang.lower().replace(" ", "_"): {
                                    "interface": True,
                                    "audio": False,
                                    "subtitles": False,
                                }
                                for lang in details.languages
                            }
                            db.upsert_languages(aid, lang_dict)

                        # extract PEGI from age ratings - ugh, so many formats
                        if details.age_ratings:
                            pegi_value = None
                            for system, value in details.age_ratings:
                                if system.upper() == "PEGI":
                                    pegi_value = str(value)
                                    break
                                mapped = convert_to_pegi(value, system)
                                if mapped:
                                    pegi_value = mapped
                                    break

                            if pegi_value:
                                db.conn.execute(
                                    "UPDATE games SET pegi_rating = ? WHERE app_id = ?",
                                    (pegi_value, aid),
                                )

                            for system, value in details.age_ratings:
                                db.conn.execute(
                                    """INSERT OR REPLACE INTO age_ratings
                                       (app_id, rating_system, rating_value, source, fetched_at)
                                       VALUES (?, ?, ?, 'api', ?)""",
                                    (aid, system, str(value), int(time.time())),
                                )

                        if details.genres:
                            db.conn.execute("DELETE FROM game_genres WHERE app_id = ?", (aid,))
                            db.conn.executemany(
                                "INSERT OR REPLACE INTO game_genres (app_id, genre) VALUES (?, ?)",
                                [(aid, g) for g in details.genres],
                            )

                        if details.tags:
                            db.conn.execute("DELETE FROM game_tags WHERE app_id = ?", (aid,))
                            db.conn.executemany(
                                "INSERT OR REPLACE INTO game_tags (app_id, tag) VALUES (?, ?)",
                                [(aid, tg) for tg in details.tags],
                            )

                        db.conn.commit()
                        success += 1

                except Exception as exc:
                    logger.warning("Steam API batch failed: %s", exc)
                    failed += len(batch)
        finally:
            db.close()

        self.finished_enrichment.emit(success, failed)
