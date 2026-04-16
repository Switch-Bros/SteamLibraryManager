from __future__ import annotations

import logging
from collections import Counter
from typing import TYPE_CHECKING

from steam_library_manager.services.chart_data import ChartSlice
from steam_library_manager.core.game import is_real_game

if TYPE_CHECKING:
    from steam_library_manager.core.game import Game
    from steam_library_manager.core.database import Database

__all__ = ["StatisticsService"]

logger = logging.getLogger("steamlibmgr.statistics")


class StatisticsService:
    """Aggregiert Game-Daten fuer Charts."""

    def __init__(self, games: list[Game], database: Database | None = None):
        self._games = games
        self._real = [g for g in games if is_real_game(g)]
        self._db = database

    def overview(self) -> dict[str, int | float]:
        total = len(self._real)
        inst = sum(1 for g in self._real if g.installed)
        pt = sum(g.playtime_minutes for g in self._real)
        never = sum(1 for g in self._real if g.playtime_minutes == 0)
        perfect = sum(1 for g in self._real if g.achievement_perfect)
        return {
            "total": total,
            "installed": inst,
            "not_installed": total - inst,
            "playtime_hours": round(pt / 60, 1),
            "never_played": never,
            "never_played_pct": round(never / total * 100, 1) if total else 0,
            "perfect_games": perfect,
            "avg_playtime_hours": round(pt / 60 / total, 1) if total else 0,
        }

    def genres_by_count(self, top_n: int = 15) -> list[ChartSlice]:
        return self._counter_to_slices(self._count_list_field("genres"), top_n)

    def genres_by_playtime(self, top_n: int = 15) -> list[ChartSlice]:
        cnt: Counter = Counter()
        for g in self._real:
            for genre in g.genres:
                cnt[genre] += g.playtime_minutes
        for k in cnt:
            cnt[k] = round(cnt[k] / 60, 1)
        return self._counter_to_slices(cnt, top_n)

    def platforms(self) -> list[ChartSlice]:
        return self._counter_to_slices(self._count_list_field("platforms"))

    def deck_status(self) -> list[ChartSlice]:
        cnt = Counter(g.steam_deck_status or "unknown" for g in self._real)
        return self._counter_to_slices(cnt)

    def protondb_tiers(self) -> list[ChartSlice]:
        cnt = Counter(g.proton_db_rating or "unknown" for g in self._real)
        return self._counter_to_slices(cnt)

    def achievement_buckets(self) -> list[ChartSlice]:
        buckets = {"perfect": 0, "almost": 0, "progress": 0, "started": 0, "zero": 0, "none": 0}
        for g in self._real:
            if g.achievement_total == 0:
                buckets["none"] += 1
            elif g.achievement_perfect:
                buckets["perfect"] += 1
            elif g.achievement_percentage >= 75:
                buckets["almost"] += 1
            elif g.achievement_percentage >= 25:
                buckets["progress"] += 1
            elif g.achievement_percentage > 0:
                buckets["started"] += 1
            else:
                buckets["zero"] += 1
        return [ChartSlice(label=k, value=v) for k, v in buckets.items() if v > 0]

    def perfect_games(self) -> list[Game]:
        return sorted(
            [g for g in self._real if g.achievement_perfect],
            key=lambda g: g.name.lower(),
        )

    def almost_done(self, threshold: float = 80.0) -> list[Game]:
        return sorted(
            [
                g
                for g in self._real
                if g.achievement_total > 0 and g.achievement_percentage >= threshold and not g.achievement_perfect
            ],
            key=lambda g: g.achievement_percentage,
            reverse=True,
        )

    def rare_achievements(self, threshold: float = 10.0) -> dict[str, int]:
        if not self._db:
            return {"rare_count": 0, "ultra_rare_count": 0, "total_unlocked": 0}
        try:
            cursor = self._db.conn.execute(
                "SELECT COUNT(*) FROM achievements WHERE is_unlocked = 1 AND rarity_percentage < ?",
                (threshold,),
            )
            rare = cursor.fetchone()[0] or 0
            cursor = self._db.conn.execute(
                "SELECT COUNT(*) FROM achievements WHERE is_unlocked = 1 AND rarity_percentage < 1.0"
            )
            ultra = cursor.fetchone()[0] or 0
            cursor = self._db.conn.execute("SELECT COUNT(*) FROM achievements WHERE is_unlocked = 1")
            total = cursor.fetchone()[0] or 0
            return {"rare_count": rare, "ultra_rare_count": ultra, "total_unlocked": total}
        except Exception:
            return {"rare_count": 0, "ultra_rare_count": 0, "total_unlocked": 0}

    def achievement_rarity_buckets(self) -> list[ChartSlice]:
        if not self._db:
            return []
        try:
            buckets = {"ultra_rare": 0, "rare": 0, "uncommon": 0, "common": 0}
            cursor = self._db.conn.execute("SELECT rarity_percentage FROM achievements WHERE is_unlocked = 1")
            for row in cursor:
                pct = row[0] or 100.0
                if pct < 1.0:
                    buckets["ultra_rare"] += 1
                elif pct < 10.0:
                    buckets["rare"] += 1
                elif pct < 50.0:
                    buckets["uncommon"] += 1
                else:
                    buckets["common"] += 1
            return [ChartSlice(label=k, value=v) for k, v in buckets.items() if v > 0]
        except Exception:
            return []

    def top_played(self, n: int = 10) -> list[ChartSlice]:
        top = sorted(self._real, key=lambda g: g.playtime_minutes, reverse=True)[:n]
        return [ChartSlice(label=g.name, value=round(g.playtime_minutes / 60, 1)) for g in top]

    def shame_pile(self) -> dict[str, int]:
        never = [g for g in self._real if g.playtime_minutes == 0]
        return {
            "total": len(never),
            "installed": sum(1 for g in never if g.installed),
            "not_installed": sum(1 for g in never if not g.installed),
        }

    def shame_pile_games(self, n: int = 5) -> list[ChartSlice]:
        """Top installed-but-never-played games sorted by HLTB main story hours."""
        never_installed = [g for g in self._real if g.playtime_minutes == 0 and g.installed]
        by_hltb = sorted(never_installed, key=lambda g: g.hltb_main_story, reverse=True)
        return [ChartSlice(label=g.name, value=g.hltb_main_story) for g in by_hltb[:n] if g.hltb_main_story > 0]

    def platform_playtime(self) -> list[ChartSlice]:
        """Playtime distribution across platforms (hours)."""
        totals = {
            "Windows": 0,
            "Linux": 0,
            "Mac": 0,
            "Steam Deck": 0,
        }
        for g in self._real:
            totals["Windows"] += g.playtime_windows
            totals["Linux"] += g.playtime_linux
            totals["Mac"] += g.playtime_mac
            totals["Steam Deck"] += g.playtime_deck
        tracked = sum(totals.values())
        total_all = sum(g.playtime_minutes for g in self._real)
        untracked = total_all - tracked
        if untracked > 0:
            totals["Untracked"] = untracked
        return [ChartSlice(label=lbl, value=round(mins / 60, 1)) for lbl, mins in totals.items() if mins > 0]

    def playtime_buckets(self) -> list[ChartSlice]:
        buckets = {"0h": 0, "lt_1h": 0, "1_5h": 0, "5_20h": 0, "20_100h": 0, "100h_plus": 0}
        for g in self._real:
            hrs = g.playtime_minutes / 60
            if hrs == 0:
                buckets["0h"] += 1
            elif hrs < 1:
                buckets["lt_1h"] += 1
            elif hrs < 5:
                buckets["1_5h"] += 1
            elif hrs < 20:
                buckets["5_20h"] += 1
            elif hrs < 100:
                buckets["20_100h"] += 1
            else:
                buckets["100h_plus"] += 1
        return [ChartSlice(label=k, value=v) for k, v in buckets.items() if v > 0]

    def pegi_distribution(self) -> list[ChartSlice]:
        cnt = Counter(g.pegi_rating or "none" for g in self._real)
        return self._counter_to_slices(cnt)

    def review_buckets(self) -> list[ChartSlice]:
        buckets = {"op_95": 0, "vp_80": 0, "pos_70": 0, "mixed_40": 0, "neg_0": 0, "no_reviews": 0}
        for g in self._real:
            pct = g.review_percentage
            if g.review_count == 0:
                buckets["no_reviews"] += 1
            elif pct >= 95:
                buckets["op_95"] += 1
            elif pct >= 80:
                buckets["vp_80"] += 1
            elif pct >= 70:
                buckets["pos_70"] += 1
            elif pct >= 40:
                buckets["mixed_40"] += 1
            else:
                buckets["neg_0"] += 1
        return [ChartSlice(label=k, value=v) for k, v in buckets.items() if v > 0]

    def top_developers(self, n: int = 10) -> list[ChartSlice]:
        cnt: Counter = Counter()
        for g in self._real:
            if g.developer:
                for dev in g.developer.split(", "):
                    dev = dev.strip()
                    if dev:
                        cnt[dev] += 1
        return self._counter_to_slices(cnt, n)

    def hltb_buckets(self) -> list[ChartSlice]:
        buckets = {
            "lt_5h": 0,
            "5_10h": 0,
            "10_20h": 0,
            "20_40h": 0,
            "40_100h": 0,
            "100h_plus": 0,
            "no_data": 0,
        }
        for g in self._real:
            hrs = g.hltb_main_story
            if hrs <= 0:
                buckets["no_data"] += 1
            elif hrs < 5:
                buckets["lt_5h"] += 1
            elif hrs < 10:
                buckets["5_10h"] += 1
            elif hrs < 20:
                buckets["10_20h"] += 1
            elif hrs < 40:
                buckets["20_40h"] += 1
            elif hrs < 100:
                buckets["40_100h"] += 1
            else:
                buckets["100h_plus"] += 1
        return [ChartSlice(label=k, value=v) for k, v in buckets.items() if v > 0]

    def _count_list_field(self, field: str) -> Counter:
        cnt: Counter = Counter()
        for g in self._real:
            vals = getattr(g, field, [])
            if isinstance(vals, list):
                for v in vals:
                    cnt[str(v).capitalize()] += 1
        return cnt

    @staticmethod
    def _counter_to_slices(cnt: Counter, top_n: int = 0) -> list[ChartSlice]:
        items = cnt.most_common(top_n) if top_n > 0 else cnt.most_common()
        return [ChartSlice(label=lbl, value=val) for lbl, val in items]
