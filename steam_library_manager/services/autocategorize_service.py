#
# steam_library_manager/services/autocategorize_service.py
# Auto-categorization engine - sorts games into collections by various criteria
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from steam_library_manager.services.autocat_configs import (
    BUCKET_METHOD_CONFIGS,
    GHOST_PREFIXES,
    KNOWN_FRANCHISES,
    SIMPLE_METHOD_CONFIGS,
)
from steam_library_manager.utils.i18n import t

__all__ = ["AutoCategorizeService"]


class AutoCategorizeService:
    """Sorts all selected games or all games from selected Collection
    into Steam collections based on all used metadata:

    Tags, Year, Genre, Publisher, Developer, Language, VR, User Score, blabla.
    """

    def __init__(self, game_mgr, cat_svc, scraper=None):
        self.game_mgr = game_mgr
        self.cat_svc = cat_svc
        self.scraper = scraper

    def _add_cat(self, game, category):
        # add game to category
        try:
            self.cat_svc.add_app_to_category(game.app_id, category)
            if category not in game.categories:
                game.categories.append(category)
            return True
        except (ValueError, RuntimeError):
            return False

    # generic engines

    def _categorize_simple(self, method_key, games, progress_cb=None):
        # reads one attribute per game, creates category from it
        cfg = SIMPLE_METHOD_CONFIGS[method_key]
        added = 0
        for i, game in enumerate(games):
            if progress_cb:
                progress_cb(i, game.name)
            val = getattr(game, cfg.attr, None)
            if not val:
                continue
            # dates are unix timestamps behind the scenes, converted for Users eyes
            if cfg.attr == "release_year" and isinstance(val, int) and val > 9999:
                from steam_library_manager.utils.date_utils import year_from_timestamp

                val = year_from_timestamp(val)
                if not val:
                    continue
            for v in (val if cfg.is_list else [val]):
                if not v:
                    continue
                disp = str(v).capitalize() if cfg.capitalize else str(v)
                cat = disp if cfg.use_raw else t(cfg.i18n_key, **{cfg.i18n_kwarg: disp})
                added += self._add_cat(game, cat)
        return added

    def _categorize_buckets(self, method_key, games, progress_cb=None):
        # maps numeric attribute to threshold ranges
        cfg = BUCKET_METHOD_CONFIGS[method_key]
        added = 0
        for i, game in enumerate(games):
            if progress_cb:
                progress_cb(i, game.name)
            raw = getattr(game, cfg.attr, None)
            if raw is None:
                if not cfg.fallback_key:
                    continue
                lbl = t(cfg.fallback_key)
            else:
                num = float(raw) if isinstance(raw, (int, float)) else 0.0
                if cfg.skip_falsy and num <= 0:
                    continue
                lbl = None
                for thresh, key in cfg.buckets:
                    if num >= thresh:
                        lbl = t(key)
                        break
                if lbl is None:
                    if cfg.fallback_key:
                        lbl = t(cfg.fallback_key)
                    else:
                        continue
            cat = t(cfg.i18n_wrapper_key, **{cfg.i18n_wrapper_kwarg: lbl})
            added += self._add_cat(game, cat)
        return added

    # simple method wrappers

    def categorize_by_publisher(self, games, progress_callback=None):
        return self._categorize_simple("publisher", games, progress_callback)

    def categorize_by_developer(self, games, progress_callback=None):
        return self._categorize_simple("developer", games, progress_callback)

    def categorize_by_genre(self, games, progress_callback=None):
        return self._categorize_simple("genre", games, progress_callback)

    def categorize_by_platform(self, games, progress_callback=None):
        return self._categorize_simple("platform", games, progress_callback)

    def categorize_by_year(self, games, progress_callback=None):
        return self._categorize_simple("year", games, progress_callback)

    def categorize_by_language(self, games, progress_callback=None):
        return self._categorize_simple("language", games, progress_callback)

    def categorize_by_vr(self, games, progress_callback=None):
        return self._categorize_simple("vr", games, progress_callback)

    # bucket method wrappers

    def categorize_by_user_score(self, games, progress_callback=None):
        return self._categorize_buckets("user_score", games, progress_callback)

    def categorize_by_hours_played(self, games, progress_callback=None):
        return self._categorize_buckets("hours_played", games, progress_callback)

    def categorize_by_hltb(self, games, progress_callback=None):
        return self._categorize_buckets("hltb", games, progress_callback)

    # special methods

    def categorize_by_tags(self, games, tags_count, progress_callback=None):
        # uses steam store scraper to fetch tags per game
        if not self.scraper:
            return 0
        added = 0
        for i, game in enumerate(games):
            if progress_callback:
                progress_callback(i, game.name)
            for tag in self.scraper.fetch_tags(game.app_id)[:tags_count]:
                added += self._add_cat(game, tag)
        return added

    @staticmethod
    def _detect_franchise(name):
        # tries to figure out franchise from game name
        if not name:
            return None
        for pfx in GHOST_PREFIXES:
            if name.startswith(pfx):
                return None
        name_lower = name.lower()
        for franchise in KNOWN_FRANCHISES:
            fl = franchise.lower()
            if name_lower.startswith(fl):
                rest = name[len(franchise) :]
                if not rest or rest[0] in (" ", ":", "-", "\u2122", "\u00ae"):
                    return franchise
        clean = name.replace("\u2122", "").replace("\u00ae", "").strip()
        for delim in (":", " - ", " \u2013 "):
            if delim in clean:
                potential = clean.split(delim)[0].strip()
                if len(potential) > 3 and not potential.isdigit():
                    return potential
        return None

    def categorize_by_franchise(self, games, progress_callback=None):
        # two-pass: detect franchises, then create categories for known ones
        fmap = {}
        for i, game in enumerate(games):
            if progress_callback:
                progress_callback(i, game.name)
            fr = self._detect_franchise(game.name)
            if fr:
                fmap.setdefault(fr, []).append(game)

        added = 0
        known_lc = {f.lower() for f in KNOWN_FRANCHISES}
        for franchise, matched in fmap.items():
            if franchise.lower() not in known_lc and len(matched) < 3:
                continue
            cat = t("auto_categorize.cat_franchise", name=franchise)
            for game in matched:
                added += self._add_cat(game, cat)
        return added

    def categorize_by_flags(self, games, progress_callback=None):
        added = 0
        for i, game in enumerate(games):
            if progress_callback:
                progress_callback(i, game.name)
            flags = []
            if getattr(game, "is_free", False):
                flags.append("Free to Play")
            for flag in flags:
                cat = t("auto_categorize.cat_flags", name=flag)
                added += self._add_cat(game, cat)
        return added

    _DECK_KEYS = frozenset({"verified", "playable", "unsupported"})

    def categorize_by_deck_status(self, games, progress_callback=None):
        added = 0
        for i, game in enumerate(games):
            if progress_callback:
                progress_callback(i, game.name)
            status = game.steam_deck_status.lower() if game.steam_deck_status else ""
            if not status or status not in self._DECK_KEYS:
                continue
            cat = "%s %s" % (t("auto_categorize.cat_deck_" + status), t("emoji.vr"))
            added += self._add_cat(game, cat)
        return added

    _PEGI_BUCKETS = (
        ("3", "auto_categorize.pegi_3"),
        ("7", "auto_categorize.pegi_7"),
        ("12", "auto_categorize.pegi_12"),
        ("16", "auto_categorize.pegi_16"),
        ("18", "auto_categorize.pegi_18"),
    )

    def _migrate_pegi_categories(self, games):
        # renames old pegi labels to zero-padded format (PEGI 3 -> PEGI 03)
        # can be removed once all users have re-categorized
        import re

        pegi_re = re.compile(r"^(.+?)(PEGI\s*)(\d+)(.*)$")
        renames = {}
        for game in games:
            for cat in list(game.categories):
                m = pegi_re.match(cat)
                if not m:
                    continue
                pfx, pw, num, sfx = m.groups()
                clean_sfx = re.sub(r"\s*\(.*?\)", "", sfx).strip()
                padded = "%s%s%02d%s" % (pfx, pw, int(num), clean_sfx)
                if padded != cat:
                    renames[cat] = padded

        for old, new in renames.items():
            for game in games:
                if old in game.categories:
                    game.categories.remove(old)
                    if new not in game.categories:
                        game.categories.append(new)
                    self.cat_svc.add_app_to_category(game.app_id, new)
            try:
                self.cat_svc.delete_category(old)
            except (ValueError, RuntimeError):
                pass

    def categorize_by_pegi(self, games, progress_callback=None):
        self._migrate_pegi_categories(games)
        added = 0
        for i, game in enumerate(games):
            if progress_callback:
                progress_callback(i, game.name)
            pegi = game.pegi_rating or ""
            if pegi:
                for rating, key in self._PEGI_BUCKETS:
                    if str(pegi) == rating:
                        lbl = t(key)
                        break
                else:
                    lbl = t("auto_categorize.pegi_unknown")
            else:
                lbl = t("auto_categorize.pegi_unknown")
            cat = t("auto_categorize.cat_pegi", rating=lbl)
            added += self._add_cat(game, cat)
        return added

    def categorize_by_achievements(self, games, progress_callback=None):
        added = 0
        for i, game in enumerate(games):
            if progress_callback:
                progress_callback(i, game.name)
            if game.achievement_total == 0:
                continue
            pct = game.achievement_percentage
            trophy = t("emoji.trophy")
            if game.achievement_perfect:
                name = "%s %s" % (t("auto_categorize.cat_achievement_perfect"), trophy)
            elif pct >= 75:
                name = "%s %s" % (t("auto_categorize.cat_achievement_almost"), trophy)
            elif pct >= 25:
                name = "%s %s" % (t("auto_categorize.cat_achievement_progress"), trophy)
            else:
                name = "%s %s" % (t("auto_categorize.cat_achievement_started"), trophy)
            added += self._add_cat(game, name)
        return added

    def categorize_by_curator(self, games, db_path=None, progress_callback=None):
        # uses stored curator recommendations from DB
        if db_path is None:
            return 0

        from steam_library_manager.core.database import Database

        db = Database(db_path)
        try:
            curators = db.get_active_curators()
            if not curators:
                return 0

            added = 0
            for cur in curators:
                cid = cur["curator_id"]
                cname = "%s %s" % (cur["name"], t("emoji.curator"))
                rec_ids = db.get_recommendations_for_curator(cid)
                if not rec_ids:
                    continue

                for i, game in enumerate(games):
                    if progress_callback:
                        progress_callback(i, game.name)
                    try:
                        num_id = int(game.app_id)
                    except (ValueError, TypeError):
                        continue
                    if num_id in rec_ids:
                        added += self._add_cat(game, cname)

            return added
        finally:
            db.close()

    # cache coverage + time estimates

    def get_cache_coverage(self, games):
        if not self.scraper:
            return {"total": len(games), "cached": 0, "missing": len(games), "percentage": 0.0}
        ids = [g.app_id for g in games]
        return self.scraper.get_cache_coverage(ids)

    def get_tag_coverage_from_db(self, total, database=None):
        # check tag coverage from DB instead of file cache
        if not database:
            return {"total": total, "cached": 0, "missing": total, "percentage": 0.0}
        cached = database.get_games_with_tags_count()
        miss = max(0, total - cached)
        pct = (cached / total * 100) if total > 0 else 0.0
        return {"total": total, "cached": cached, "missing": miss, "percentage": pct}

    @staticmethod
    def estimate_time(missing_count):
        secs = int(missing_count * 1.5)
        mins = secs // 60
        if mins > 60:
            h = mins // 60
            m = mins % 60
            return t("time.time_hours", hours=h, minutes=m)
        elif mins > 0:
            return t("time.time_minutes", minutes=mins)
        else:
            return t("time.time_seconds", seconds=secs)
