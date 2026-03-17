#
# steam_library_manager/core/game_manager.py
# Central manager coordinating game loading, saving, and categorization
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
import platform

import requests

from steam_library_manager.core.database import is_placeholder_name
from steam_library_manager.core.game import Game, NON_GAME_APP_IDS, NON_GAME_NAME_PATTERNS
from steam_library_manager.services.game_detail_service import GameDetailService
from steam_library_manager.services.game_query_service import GameQueryService
from steam_library_manager.services.enrichment.metadata_enrichment_service import MetadataEnrichmentService
from steam_library_manager.utils.i18n import t
from steam_library_manager.utils.timeouts import HTTP_TIMEOUT

logger = logging.getLogger("steamlibmgr.game_manager")

__all__ = ["Game", "GameManager"]


class GameManager:
    """Manages and loads games, handles metadata and all that cool stuff.

    Loads different GameInfos from local manifests and localinfo.vdf

    Gets Steam_API and fills up the DB with Data :)
    """

    NON_GAME_APP_IDS = NON_GAME_APP_IDS
    NON_GAME_NAME_PATTERNS = NON_GAME_NAME_PATTERNS

    def __init__(self, steam_api_key, cache_dir, steam_path):
        self.api_key = steam_api_key
        self.cache_dir = cache_dir
        self.steam_path = steam_path
        self.cache_dir.mkdir(exist_ok=True)

        self.games = {}
        self.steam_user_id = None
        self.load_source = "unknown"
        self.appinfo_manager = None

        # filter proton crap on linux
        self.filter_non_games = platform.system() == "Linux"

        self.detail_svc = GameDetailService(self.games, cache_dir)
        self.enrich_svc = MetadataEnrichmentService(self.games, cache_dir)
        self.query_svc = GameQueryService(self.games, self.filter_non_games)

    def load_games(self, steam_user_id, progress_callback=None):
        """Load games from API and/or local files.

        Tries API first if credentials exist, fallback to local.
        Shows progress via callback if provided.

        Args:
            steam_user_id: Steam ID to load for
            progress_callback: Optional func(message, current, total)

        Returns:
            bool: True if loaded, False if complete fail
        """
        self.steam_user_id = steam_user_id
        api_ok = False

        from steam_library_manager.config import config as _cfg

        has_creds = self.api_key or getattr(_cfg, "STEAM_ACCESS_TOKEN", None)
        if has_creds:
            if progress_callback:
                progress_callback(t("logs.manager.api_trying"), 0, 3)

            logger.info(t("logs.manager.api_trying"))
            api_ok = self._load_api(steam_user_id)

        if progress_callback:
            progress_callback(t("logs.manager.local_loading"), 1, 3)

        logger.info(t("logs.manager.local_loading"))
        local_ok = self._load_local(progress_callback)

        if progress_callback:
            progress_callback(t("common.loading"), 2, 3)

        # figure out where the data is coming from
        if api_ok and local_ok:
            self.load_source = "mixed"
        elif api_ok:
            self.load_source = "api"
        elif local_ok:
            self.load_source = "local"
        else:
            self.load_source = "failed"
            return False

        if progress_callback:
            progress_callback(t("ui.main_window.status_ready"), 3, 3)

        return True

    def _load_local(self, progress_cb=None):
        # grab installed games from local steam manifests
        from steam_library_manager.core.local_games_loader import LocalGamesLoader

        try:
            loader = LocalGamesLoader(self.steam_path)
            games_data = loader.get_all_games()

            if not games_data:
                logger.warning(t("logs.manager.error_local", error="No local games found"))
                return False

            # get playtime from localconfig
            from steam_library_manager.config import config

            short_id, _ = config.get_detected_user()
            if short_id:
                lc_path = config.get_localconfig_path(short_id)
                playtimes = loader.get_playtime_from_localconfig(lc_path)
            else:
                playtimes = {}

            total = len(games_data)
            for i, gd in enumerate(games_data):
                if progress_cb and i % 50 == 0:
                    progress_cb(t("common.loading"), i, total)

                aid = str(gd["appid"])
                if aid in self.games:
                    continue

                pt = playtimes.get(aid, 0)
                game = Game(app_id=aid, name=gd["name"], playtime_minutes=pt, installed=True)
                self.games[aid] = game

            logger.info(t("logs.manager.loaded_local", count=len(games_data)))
            return True

        except (OSError, ValueError, KeyError, RecursionError) as e:
            logger.error(t("logs.manager.error_local", error=e))
            return False

    def _load_api(self, steam_uid):
        # fetch from steam web api
        from steam_library_manager.config import config

        token = getattr(config, "STEAM_ACCESS_TOKEN", None)

        if not self.api_key and not token:
            logger.info(t("logs.manager.no_api_key"))
            return False

        try:
            url = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"

            if token:
                logger.info(t("logs.manager.using_oauth"))
                params = {
                    "access_token": token,
                    "steamid": steam_uid,
                    "include_appinfo": 1,
                    "include_played_free_games": 1,
                    "include_free_sub": 1,
                    "skip_unvetted_apps": 0,
                    "format": "json",
                }
                resp = requests.get(url, params=params, timeout=HTTP_TIMEOUT)
            else:
                logger.info(t("logs.manager.using_api_key"))
                params = {
                    "key": self.api_key,
                    "steamid": steam_uid,
                    "include_appinfo": 1,
                    "include_played_free_games": 1,
                    "include_free_sub": 1,
                    "skip_unvetted_apps": 0,
                    "format": "json",
                }
                resp = requests.get(url, params=params, timeout=HTTP_TIMEOUT)

            resp.raise_for_status()
            data = resp.json()

            if "response" not in data or "games" not in data["response"]:
                logger.warning(t("logs.manager.error_api", error="No games in response"))
                return False

            games_list = data["response"]["games"]
            logger.info(t("logs.manager.loaded_api", count=len(games_list)))

            for gd in games_list:
                aid = str(gd["appid"])
                name = gd.get("name") or t("ui.game_details.game_fallback", id=aid)

                game = Game(app_id=aid, name=name, playtime_minutes=gd.get("playtime_forever", 0))
                self.games[aid] = game

            return True

        except (requests.RequestException, ValueError, KeyError) as e:
            # NEVER leak api key, nowehere
            if isinstance(e, requests.HTTPError) and e.response is not None:
                safe_msg = "HTTP %d" % e.response.status_code
            else:
                safe_msg = type(e).__name__
            logger.error(t("logs.manager.error_api", error=safe_msg))
            return False

    # wrapper for enrich service
    def merge_with_localconfig(self, parser):
        self.enrich_svc.merge_with_localconfig(parser)

    def apply_appinfo_data(self, appinfo_data):
        self.enrich_svc.apply_appinfo_data(appinfo_data)

    def apply_metadata_overrides(self, appinfo_mgr):
        self.appinfo_manager = appinfo_mgr
        self.enrich_svc.apply_metadata_overrides(appinfo_mgr)

    def discover_missing_games(self, localconfig_helper, appinfo_manager, packageinfo_ids=None, *, db_type_lookup=None):
        return self.enrich_svc.discover_missing_games(
            localconfig_helper,
            appinfo_manager,
            packageinfo_ids,
            db_type_lookup=db_type_lookup,
        )

    def apply_custom_overrides(self, mods):
        self.enrich_svc.apply_custom_overrides(mods)

    def enrich_from_database(self, db):
        """Fill in cached metadata from DB.

        It's a bit messy because we have to map DB columns
        to Game object attributes. v8 schema added lot of fields.

        Args:
            db: Database instance with game entries

        Returns:
            int: Number of games enriched
        """
        entries = db.get_all_games()
        if not entries:
            return 0

        lookup = {str(e.app_id): e for e in entries}
        enriched = 0

        # TODO: This loop is slow as hell with 3k+ games -> need to batch this properly in one of the next Versions
        for aid, game in self.games.items():
            entry = lookup.get(aid)
            if not entry:
                continue

            # fix placeholder names
            if not is_placeholder_name(entry.name) and is_placeholder_name(game.name):
                game.name = entry.name
                if not game.name_overridden:
                    game.sort_name = entry.name

            # only fill empty fields
            if not game.developer and entry.developer:
                game.developer = entry.developer
            if not game.publisher and entry.publisher:
                game.publisher = entry.publisher
            if not game.release_year:
                ts = entry.release_date or entry.steam_release_date or entry.original_release_date
                if ts and isinstance(ts, int) and ts > 0:
                    game.release_year = ts
            if not game.genres and entry.genres:
                game.genres = list(entry.genres)
            if not game.tags and entry.tags:
                game.tags = list(entry.tags)
            if not game.tag_ids and entry.tag_ids:
                game.tag_ids = list(entry.tag_ids)
            if not game.app_type and entry.app_type:
                game.app_type = entry.app_type
            if not game.platforms and entry.platforms:
                game.platforms = list(entry.platforms)
            if not game.review_score and entry.review_score is not None:
                game.review_score = str(entry.review_score)
            if not game.review_percentage and entry.review_percentage:
                game.review_percentage = entry.review_percentage
            if not game.review_count and entry.review_count:
                game.review_count = entry.review_count

            # languages
            if not game.languages and entry.languages:
                game.languages = [lang for lang, sup in entry.languages.items() if sup.get("interface")]

            # v8 enrichment cache
            if not game.pegi_rating and entry.pegi_rating:
                game.pegi_rating = entry.pegi_rating
            if not game.esrb_rating and entry.esrb_rating:
                game.esrb_rating = entry.esrb_rating
            if not game.metacritic_score and entry.metacritic_score:
                game.metacritic_score = entry.metacritic_score
            if not game.steam_deck_status and entry.steam_deck_status:
                game.steam_deck_status = entry.steam_deck_status
            if not game.description and entry.short_description:
                game.description = entry.short_description

            # achievements
            if not game.achievement_percentage and entry.achievement_percentage:
                game.achievement_percentage = entry.achievement_percentage
            if not game.achievement_total and entry.achievements_total:
                game.achievement_total = entry.achievements_total
            if not game.achievement_unlocked and entry.achievement_unlocked:
                game.achievement_unlocked = entry.achievement_unlocked
            if not game.achievement_perfect and entry.achievement_perfect:
                game.achievement_perfect = entry.achievement_perfect

            enriched += 1

        # hltb times
        hltb_data = db._batch_get_hltb([int(x) for x in self.games.keys() if x.isdigit()])
        for aid_int, (main, extras, comp) in hltb_data.items():
            g = self.games.get(str(aid_int))
            if g and g.hltb_main_story <= 0:
                g.hltb_main_story = main
                g.hltb_main_extras = extras
                g.hltb_completionist = comp

        # protondb ratings
        num_ids = [int(x) for x in self.games.keys() if x.isdigit()]
        pdb_data = db.batch_get_protondb(num_ids)
        for aid_int, tier in pdb_data.items():
            g = self.games.get(str(aid_int))
            if g and not g.proton_db_rating:
                g.proton_db_rating = tier

        logger.info(t("logs.db.loaded_from_cache", count=enriched, duration="<1"))
        return enriched

    # query wrappers -> forward to query service
    def get_game(self, app_id):
        return self.games.get(app_id)

    def get_games_by_category(self, cat):
        return self.query_svc.get_games_by_category(cat)

    def get_uncategorized_games(self, smart_names=None):
        return self.query_svc.get_uncategorized_games(smart_names)

    def get_favorites(self):
        return self.query_svc.get_favorites()

    def get_all_categories(self):
        return self.query_svc.get_all_categories()

    def fetch_game_details(self, app_id):
        return self.detail_svc.fetch_game_details(app_id)

    def get_load_source_message(self):
        # msg of game source
        if self.load_source == "api":
            return t("logs.manager.loaded_api", count=len(self.games))
        elif self.load_source == "local":
            return t("logs.manager.loaded_local", count=len(self.games))
        elif self.load_source == "mixed":
            return t("logs.manager.loaded_mixed", count=len(self.games))
        else:
            return t("ui.main_window.status_ready")

    def get_real_games(self):
        return self.query_svc.get_real_games()

    def get_all_games(self):
        return self.query_svc.get_all_games()

    def get_game_statistics(self):
        return self.query_svc.get_game_statistics()
