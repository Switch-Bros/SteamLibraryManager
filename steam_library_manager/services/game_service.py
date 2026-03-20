#
# steam_library_manager/services/game_service.py
# Game loading and init pipeline
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
import requests
from pathlib import Path

from steam_library_manager.utils.i18n import t
from steam_library_manager.core.game import Game
from steam_library_manager.core.game_manager import GameManager
from steam_library_manager.core.localconfig_helper import LocalConfigHelper
from steam_library_manager.core.cloud_storage_parser import CloudStorageParser
from steam_library_manager.core.appinfo_manager import AppInfoManager
from steam_library_manager.core.database import Database
from steam_library_manager.core.db.models import DatabaseEntry
from steam_library_manager.core.database_importer import DatabaseImporter
from steam_library_manager.core.packageinfo_parser import PackageInfoParser
from steam_library_manager.utils.license_cache_parser import LicenseCacheParser
from steam_library_manager.utils.timeouts import HTTP_TIMEOUT_LONG

logger = logging.getLogger("steamlibmgr.game_service")

__all__ = ["GameService"]


class GameService:
    """Orchestrates game loading from multiple sources.

    Pipeline: API fetch -> local VDF parse -> cloud storage merge
    -> DB enrichment -> metadata overrides -> done.
    """

    def __init__(self, steam_path, api_key, cache_dir):
        self.steam_path = steam_path
        self.api_key = api_key
        self.cache_dir = cache_dir

        self.localconfig_helper = None
        self.cloud_storage_parser = None
        self.game_manager = None
        self.appinfo_manager = None
        self.database = None

    def initialize_parsers(self, localconfig_path, user_id):
        # setup VDF + cloud storage parsers
        vdf_ok = False
        cloud_ok = False

        try:
            self.localconfig_helper = LocalConfigHelper(localconfig_path)
            if self.localconfig_helper.load():
                vdf_ok = True
            else:
                self.localconfig_helper = None
        except (OSError, FileNotFoundError, ValueError) as e:
            logger.error(t("logs.service.localconfig_init_error", error=e))
            self.localconfig_helper = None

        try:
            self.cloud_storage_parser = CloudStorageParser(self.steam_path, user_id)
            if self.cloud_storage_parser.load():
                cloud_ok = True
            else:
                self.cloud_storage_parser = None
        except Exception as e:
            logger.error(t("logs.service.cloud_parser_init_error", error=e))
            self.cloud_storage_parser = None

        return vdf_ok, cloud_ok

    def _init_db(self):
        # open metadata.db
        db_dir = Path(self.cache_dir).parent
        db_path = db_dir / "metadata.db"
        try:
            d = Database(db_path)
            logger.info(t("logs.db.initializing"))
            return d
        except Exception as e:
            logger.error(t("logs.db.schema_error", error=str(e)))
            return None

    def _initial_import(self, db, cb=None):
        # one-time import from appinfo.vdf
        if db.get_game_count() > 0:
            logger.info(t("logs.db.already_initialized"))
            return

        if not self.appinfo_manager:
            self.appinfo_manager = AppInfoManager(Path(self.steam_path))
            self.appinfo_manager.load_appinfo()

        imp = DatabaseImporter(db, self.appinfo_manager)

        def bridge(cur, total, msg):
            if cb:
                cb(msg, cur, total)

        logger.info(t("logs.db.import_one_time"))
        imp.import_from_appinfo(bridge)

    def load_games(self, user_id, progress_callback=None):
        # load all games from API/local, enrich with DB
        if not self.cloud_storage_parser:
            raise RuntimeError("Parsers not initialized. Call initialize_parsers() first.")

        self.game_manager = GameManager(self.api_key, Path(self.cache_dir), Path(self.steam_path))
        self.database = self._init_db()

        if self.database:
            self._initial_import(self.database, progress_callback)
            self.database.repair_placeholder_names()

        ok = self.game_manager.load_games(user_id, progress_callback)

        if self.database and self.game_manager.games:
            self.game_manager.enrich_from_database(self.database)

        return ok and bool(self.game_manager.games)

    def load_and_prepare(self, user_id, progress_callback=None):
        # full pipeline
        ok = self.load_games(user_id, progress_callback)
        if not ok or not self.game_manager or not self.game_manager.games:
            return False

        cb = progress_callback
        self._merge_cloud(cb)
        mods = self._load_mods(cb)
        pkg_ids = self._resolve_pkgs(cb)
        types = self._discover_missing(pkg_ids, cb)
        self._api_refresh_merge(user_id, cb)
        self._finalize(mods, types, cb)
        return True

    # pipeline steps

    def _merge_cloud(self, cb):
        if cb:
            cb(t("logs.manager.merging"), 0, 0)
        if self.cloud_storage_parser:
            self.game_manager.merge_with_localconfig(self.cloud_storage_parser)

    def _load_mods(self, cb):
        if cb:
            cb(t("logs.service.applying_metadata"), 0, 0)
        if not self.appinfo_manager:
            self.appinfo_manager = AppInfoManager(Path(self.steam_path))
        return self.appinfo_manager.load_modifications_only()

    def _resolve_pkgs(self, cb):
        if cb:
            cb(t("logs.service.parsing_packages"), 0, 0)

        pkg = PackageInfoParser(Path(self.steam_path))

        from steam_library_manager.config import config as _cfg

        sid, _ = _cfg.get_detected_user()
        s32 = int(sid) if sid else None

        if not s32:
            return pkg.get_all_app_ids()

        lic = LicenseCacheParser(Path(self.steam_path), s32)
        owned = lic.get_owned_package_ids()

        if not owned:
            return pkg.get_all_app_ids()

        ids = pkg.get_app_ids_for_packages(owned)
        logger.info(t("logs.license_cache.cross_reference", packages=len(owned), apps=len(ids)))
        return ids

    def _discover_missing(self, pkg_ids, cb):
        if cb:
            cb(t("logs.service.discovering_games"), 0, 0)

        types = None
        if self.database and self.database.get_game_count() > 0:
            types = self.database.get_app_type_lookup()

        # FIXME: types can be empty dict which is valid
        if types is not None:
            found = self.game_manager.discover_missing_games(
                self.localconfig_helper,
                self.appinfo_manager,
                pkg_ids,
                db_type_lookup=types,
            )
        else:
            self.appinfo_manager.load_appinfo()
            found = self.game_manager.discover_missing_games(
                self.localconfig_helper,
                self.appinfo_manager,
                pkg_ids,
            )

        if found > 0 and self.cloud_storage_parser:
            self.game_manager.merge_with_localconfig(self.cloud_storage_parser)

        return types

    def _api_refresh_merge(self, uid, cb):
        if cb:
            cb(t("ui.status.api_refresh"), 0, 0)
        new = self._api_refresh(uid)
        if new:
            if self.cloud_storage_parser:
                self.game_manager.merge_with_localconfig(self.cloud_storage_parser)
            if self.database:
                self._save_new(new)
                self._enrich_new_games(new, cb)

    def _finalize(self, mods, types, cb):
        if self.database:
            self.game_manager.enrich_from_database(self.database)

        self._repair_placeholders()

        if cb:
            cb(t("logs.service.applying_overrides"), 0, 0)
        if types is not None:
            self.game_manager.apply_custom_overrides(mods)
        else:
            self.game_manager.apply_metadata_overrides(self.appinfo_manager)

    def _api_refresh(self, uid):
        # fetch from steam API (oauth first, api key fallback)
        if not self.game_manager:
            return []

        from steam_library_manager.config import config

        tok = getattr(config, "STEAM_ACCESS_TOKEN", None)

        if not tok and not self.api_key:
            logger.debug("no API creds - skip")
            return []

        url = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
        base_params = {
            "steamid": uid,
            "include_appinfo": 1,
            "include_played_free_games": 1,
            "include_free_sub": 1,
            "skip_unvetted_apps": 0,
            "format": "json",
        }

        attempts = []
        if tok:
            attempts.append(("oauth", {"access_token": tok}))
        if self.api_key:
            attempts.append(("api_key", {"key": self.api_key}))

        for method, auth_params in attempts:
            try:
                params = {**base_params, **auth_params}
                resp = requests.get(url, params=params, timeout=HTTP_TIMEOUT_LONG)
                resp.raise_for_status()
                data = resp.json()

                glist = data.get("response", {}).get("games", [])
                if not glist:
                    if method == "oauth" and self.api_key:
                        logger.info("OAuth returned empty, trying API key")
                        continue
                    return []

                new_ids = []
                for gd in glist:
                    aid = str(gd["appid"])
                    if aid not in self.game_manager.games:
                        nm = gd.get("name") or t("ui.game_details.game_fallback", id=aid)
                        pt = gd.get("playtime_forever", 0)
                        game = Game(
                            app_id=aid,
                            name=nm,
                            playtime_minutes=pt,
                            app_type="",
                        )
                        self.game_manager.games[aid] = game
                        new_ids.append(aid)
                        logger.debug("found %s (%s)" % (aid, nm))

                if new_ids:
                    logger.info("refresh: %d new games" % len(new_ids))
                return new_ids

            except Exception as e:
                if isinstance(e, requests.HTTPError) and e.response is not None:
                    msg = "HTTP %d" % e.response.status_code
                else:
                    msg = type(e).__name__

                # oauth failed? try api key next
                if method == "oauth" and self.api_key:
                    logger.info("OAuth refresh failed (%s), trying API key" % msg)
                    continue

                logger.warning("API refresh failed: %s" % msg)
                return []

        return []

    def _save_new(self, new_ids):
        # persist to db
        if not self.database or not self.game_manager:
            return

        for aid in new_ids:
            g = self.game_manager.games.get(aid)
            if not g:
                continue
            entry = DatabaseEntry(
                app_id=int(aid),
                name=g.name,
                app_type=g.app_type or "game",
            )
            try:
                self.database.insert_game(entry)
            except Exception as e:
                logger.debug("insert %s failed: %s" % (aid, e))

        self.database.commit()

    def _enrich_new_games(self, new_ids, cb=None):
        # fetch tags + metadata for newly discovered games via batch API
        if not self.api_key or not self.database:
            return

        if cb:
            cb("Enriching %d new games..." % len(new_ids), 0, 0)

        try:
            from steam_library_manager.integrations.steam_web_api import SteamWebAPI

            api = SteamWebAPI(self.api_key)
            int_ids = [int(aid) for aid in new_ids]
            details = api.get_app_details_batch(int_ids)

            tag_batch = []

            for aid, det in details.items():
                str_id = str(aid)
                game = self.game_manager.games.get(str_id)
                if not game:
                    continue

                # apply to in-memory Game object
                if det.tags:
                    game.tags = list(det.tags)
                if det.genres:
                    game.genres = list(det.genres)
                if det.developers:
                    game.developer = ", ".join(det.developers)
                if det.publishers:
                    game.publisher = ", ".join(det.publishers)
                if det.platforms:
                    game.platforms = list(det.platforms)

                # collect tags for bulk DB insert
                for tag_id, tag_name in det.tag_ids:
                    tag_batch.append((aid, tag_id, tag_name))

            # persist tags
            if tag_batch:
                self.database.bulk_insert_game_tags_by_id(tag_batch)

            # persist basic metadata
            for aid, det in details.items():
                game = self.game_manager.games.get(str(aid))
                if not game:
                    continue
                entry = DatabaseEntry(
                    app_id=aid,
                    name=det.name or game.name,
                    app_type=game.app_type or "",
                    developer=", ".join(det.developers) if det.developers else "",
                    publisher=", ".join(det.publishers) if det.publishers else "",
                )
                try:
                    self.database.update_game(entry)
                except Exception:
                    pass  # non-fatal

            if details:
                self.database.commit()
                logger.info("enriched %d/%d new games" % (len(details), len(new_ids)))

        except Exception as e:
            logger.warning("auto-enrich failed: %s" % type(e).__name__)

    def _repair_placeholders(self):
        # fix "App XXXXX" names
        if not self.game_manager or not self.appinfo_manager:
            return

        from steam_library_manager.core.database import is_placeholder_name

        bad = [g for g in self.game_manager.games.values() if is_placeholder_name(g.name)]

        if not bad:
            return

        # lazy load
        if not getattr(self.appinfo_manager, "appinfo", None):
            self.appinfo_manager.load_appinfo()

        fixed = 0
        for g in bad:
            meta = self.appinfo_manager.get_app_metadata(g.app_id)
            real = meta.get("name", "")

            if real and not is_placeholder_name(real):
                g.name = real
                if not g.name_overridden:
                    g.sort_name = real

                if self.database:
                    self.database.update_game_name(int(g.app_id), real)

                fixed += 1

        if fixed > 0:
            if self.database:
                self.database.commit()
            logger.info(t("logs.service.placeholder_names_repaired", count=fixed))

    def merge_with_localconfig(self):
        if not self.game_manager:
            raise RuntimeError("GameManager not initialized. Call load_games() first.")

        parser = self.cloud_storage_parser
        if not parser:
            raise RuntimeError("No parser available for merging.")

        self.game_manager.merge_with_localconfig(parser)

    def apply_metadata(self):
        if not self.game_manager:
            raise RuntimeError("GameManager not initialized. Call load_games() first.")

        if not self.appinfo_manager:
            self.appinfo_manager = AppInfoManager(Path(self.steam_path))
            self.appinfo_manager.load_appinfo()

        pkg = PackageInfoParser(Path(self.steam_path))
        ids = pkg.get_all_app_ids()

        if self.appinfo_manager:
            found = self.game_manager.discover_missing_games(self.localconfig_helper, self.appinfo_manager, ids)
            if found > 0 and self.cloud_storage_parser:
                self.game_manager.merge_with_localconfig(self.cloud_storage_parser)

        self.game_manager.apply_metadata_overrides(self.appinfo_manager)

    def get_active_parser(self):
        return self.cloud_storage_parser

    def _refresh_from_profile(self, uid):
        # scrape profile as fallback
        if not self.game_manager:
            return []

        try:
            from steam_library_manager.integrations.steam_profile_scraper import SteamProfileScraper

            scraper = SteamProfileScraper()
            pgs = scraper.fetch_games(uid)

            if not pgs:
                return []

            new = []
            for pg in pgs:
                aid = str(pg.app_id)
                if aid not in self.game_manager.games:
                    game = Game(
                        app_id=aid,
                        name=pg.name,
                        playtime_minutes=pg.playtime_forever,
                        app_type="",
                    )
                    self.game_manager.games[aid] = game
                    new.append(aid)

            if new:
                logger.info(t("logs.service.profile_discovered", count=len(new)))

            return new

        except Exception as e:
            logger.warning(t("logs.service.profile_scrape_failed", error=str(e)))
            return []

    def get_load_source_message(self):
        if not self.game_manager:
            return "No games loaded"
        return self.game_manager.get_load_source_message()
