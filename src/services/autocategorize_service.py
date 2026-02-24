"""Auto-Categorize Service for Steam Library Manager.

Uses two generic engines (simple attribute-based and threshold-based bucket)
plus special methods for tags, franchise, flags, deck, achievements, curator, PEGI.
"""

from __future__ import annotations

from typing import Any, Callable

from src.core.game_manager import Game, GameManager
from src.integrations.steam_store import SteamStoreScraper
from src.services.autocat_configs import (
    BUCKET_METHOD_CONFIGS,
    GHOST_PREFIXES,
    KNOWN_FRANCHISES,
    SIMPLE_METHOD_CONFIGS,
)
from src.services.category_service import CategoryService
from src.services.curator_client import CuratorClient, CuratorRecommendation
from src.utils.i18n import t

__all__ = ["AutoCategorizeService"]


class AutoCategorizeService:
    """Service for managing auto-categorization operations."""

    def __init__(
        self,
        game_manager: GameManager,
        category_service: CategoryService,
        steam_scraper: SteamStoreScraper | None = None,
    ) -> None:
        """Initialize the AutoCategorizeService.

        Args:
            game_manager: Manager for accessing game data.
            category_service: Service for category operations.
            steam_scraper: Optional scraper for Steam Store data.
        """
        self.game_manager = game_manager
        self.category_service = category_service
        self.steam_scraper = steam_scraper

    # -- Shared helper -----------------------------------------------------

    def _add_category(self, game: Game, category: str) -> bool:
        """Adds a game to a category, updating both DB and in-memory state.

        Args:
            game: The game to categorize.
            category: Category name to add.

        Returns:
            True if category was added, False on error.
        """
        try:
            self.category_service.add_app_to_category(game.app_id, category)
            if category not in game.categories:
                game.categories.append(category)
            return True
        except (ValueError, RuntimeError):
            return False

    # -- Generic engines ---------------------------------------------------

    def _categorize_simple(
        self,
        method_key: str,
        games: list[Game],
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> int:
        """Categorize games by reading a single attribute and creating categories.

        Args:
            method_key: Key into SIMPLE_METHOD_CONFIGS.
            games: List of games to categorize.
            progress_callback: Optional callback(current_index, game_name).

        Returns:
            Number of categories added.
        """
        cfg = SIMPLE_METHOD_CONFIGS[method_key]
        categories_added = 0
        for i, game in enumerate(games):
            if progress_callback:
                progress_callback(i, game.name)
            value = getattr(game, cfg.attr, None)
            if not value:
                continue
            for v in (value if cfg.is_list else [value]):
                if not v:
                    continue
                display = str(v).capitalize() if cfg.capitalize else str(v)
                category = display if cfg.use_raw else t(cfg.i18n_key, **{cfg.i18n_kwarg: display})
                categories_added += self._add_category(game, category)
        return categories_added

    def _categorize_by_buckets(
        self,
        method_key: str,
        games: list[Game],
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> int:
        """Categorize games by mapping a numeric attribute to threshold buckets.

        Args:
            method_key: Key into BUCKET_METHOD_CONFIGS.
            games: List of games to categorize.
            progress_callback: Optional callback(current_index, game_name).

        Returns:
            Number of categories added.
        """
        cfg = BUCKET_METHOD_CONFIGS[method_key]
        categories_added = 0
        for i, game in enumerate(games):
            if progress_callback:
                progress_callback(i, game.name)
            raw_value = getattr(game, cfg.attr, None)
            if raw_value is None:
                if not cfg.fallback_key:
                    continue
                label = t(cfg.fallback_key)
            else:
                numeric = float(raw_value) if isinstance(raw_value, (int, float)) else 0.0
                if cfg.skip_falsy and numeric <= 0:
                    continue
                label = None
                for threshold, key in cfg.buckets:
                    if numeric >= threshold:
                        label = t(key)
                        break
                if label is None:
                    if cfg.fallback_key:
                        label = t(cfg.fallback_key)
                    else:
                        continue
            category = t(cfg.i18n_wrapper_key, **{cfg.i18n_wrapper_kwarg: label})
            categories_added += self._add_category(game, category)
        return categories_added

    # -- Simple method wrappers --------------------------------------------

    def categorize_by_publisher(
        self, games: list[Game], progress_callback: Callable[[int, str], None] | None = None
    ) -> int:
        """Categorize games by publisher."""
        return self._categorize_simple("publisher", games, progress_callback)

    def categorize_by_developer(
        self, games: list[Game], progress_callback: Callable[[int, str], None] | None = None
    ) -> int:
        """Categorize games by developer."""
        return self._categorize_simple("developer", games, progress_callback)

    def categorize_by_genre(
        self, games: list[Game], progress_callback: Callable[[int, str], None] | None = None
    ) -> int:
        """Categorize games by genre."""
        return self._categorize_simple("genre", games, progress_callback)

    def categorize_by_platform(
        self, games: list[Game], progress_callback: Callable[[int, str], None] | None = None
    ) -> int:
        """Categorize games by supported platform."""
        return self._categorize_simple("platform", games, progress_callback)

    def categorize_by_year(self, games: list[Game], progress_callback: Callable[[int, str], None] | None = None) -> int:
        """Categorize games by release year."""
        return self._categorize_simple("year", games, progress_callback)

    def categorize_by_language(
        self, games: list[Game], progress_callback: Callable[[int, str], None] | None = None
    ) -> int:
        """Categorize games by supported interface languages."""
        return self._categorize_simple("language", games, progress_callback)

    def categorize_by_vr(self, games: list[Game], progress_callback: Callable[[int, str], None] | None = None) -> int:
        """Categorize games by VR support level."""
        return self._categorize_simple("vr", games, progress_callback)

    # -- Bucket method wrappers --------------------------------------------

    def categorize_by_user_score(
        self, games: list[Game], progress_callback: Callable[[int, str], None] | None = None
    ) -> int:
        """Categorize games by Steam user review score."""
        return self._categorize_by_buckets("user_score", games, progress_callback)

    def categorize_by_hours_played(
        self, games: list[Game], progress_callback: Callable[[int, str], None] | None = None
    ) -> int:
        """Categorize games by playtime ranges."""
        return self._categorize_by_buckets("hours_played", games, progress_callback)

    def categorize_by_hltb(self, games: list[Game], progress_callback: Callable[[int, str], None] | None = None) -> int:
        """Categorize games by HowLongToBeat main story duration."""
        return self._categorize_by_buckets("hltb", games, progress_callback)

    # -- Special methods (unique logic) ------------------------------------

    def categorize_by_tags(
        self,
        games: list[Game],
        tags_count: int,
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> int:
        """Categorize games by Steam Store tags.

        Args:
            games: List of games to categorize.
            tags_count: Number of top tags to use per game.
            progress_callback: Optional callback(current_index, game_name).

        Returns:
            Number of categories added.
        """
        if not self.steam_scraper:
            return 0
        categories_added = 0
        for i, game in enumerate(games):
            if progress_callback:
                progress_callback(i, game.name)
            for tag in self.steam_scraper.fetch_tags(game.app_id)[:tags_count]:
                categories_added += self._add_category(game, tag)
        return categories_added

    @staticmethod
    def _detect_franchise(game_name: str) -> str | None:
        """Detects franchise from a game name using the curated list + pattern fallback.

        Args:
            game_name: The full game name.

        Returns:
            The detected franchise name, or None.
        """
        if not game_name:
            return None
        for prefix in GHOST_PREFIXES:
            if game_name.startswith(prefix):
                return None
        name_lower = game_name.lower()
        for franchise in KNOWN_FRANCHISES:
            fl = franchise.lower()
            if name_lower.startswith(fl):
                rest = game_name[len(franchise) :]
                if not rest or rest[0] in (" ", ":", "-", "\u2122", "\u00ae"):
                    return franchise
        clean = game_name.replace("\u2122", "").replace("\u00ae", "").strip()
        for delim in (":", " - ", " \u2013 "):
            if delim in clean:
                potential = clean.split(delim)[0].strip()
                if len(potential) > 3 and not potential.isdigit():
                    return potential
        return None

    def categorize_by_franchise(
        self, games: list[Game], progress_callback: Callable[[int, str], None] | None = None
    ) -> int:
        """Categorize games by detected franchise (two-pass approach).

        Args:
            games: List of games to categorize.
            progress_callback: Optional callback(current_index, game_name).

        Returns:
            Number of categories added.
        """
        game_franchise_map: dict[str, list[Game]] = {}
        for i, game in enumerate(games):
            if progress_callback:
                progress_callback(i, game.name)
            franchise = self._detect_franchise(game.name)
            if franchise:
                game_franchise_map.setdefault(franchise, []).append(game)

        categories_added = 0
        known_lower = {f.lower() for f in KNOWN_FRANCHISES}
        for franchise, matched_games in game_franchise_map.items():
            if franchise.lower() not in known_lower and len(matched_games) < 3:
                continue
            category = t("auto_categorize.cat_franchise", name=franchise)
            for game in matched_games:
                categories_added += self._add_category(game, category)
        return categories_added

    def categorize_by_flags(
        self, games: list[Game], progress_callback: Callable[[int, str], None] | None = None
    ) -> int:
        """Categorize games by feature flags (e.g. Free to Play).

        Args:
            games: List of games to categorize.
            progress_callback: Optional callback(current_index, game_name).

        Returns:
            Number of categories added.
        """
        categories_added = 0
        for i, game in enumerate(games):
            if progress_callback:
                progress_callback(i, game.name)
            flags: list[str] = []
            if getattr(game, "is_free", False):
                flags.append("Free to Play")
            for flag_name in flags:
                category = t("auto_categorize.cat_flags", name=flag_name)
                categories_added += self._add_category(game, category)
        return categories_added

    _DECK_STATUS_KEYS: frozenset[str] = frozenset({"verified", "playable", "unsupported"})

    def categorize_by_deck_status(
        self, games: list[Game], progress_callback: Callable[[int, str], None] | None = None
    ) -> int:
        """Categorize games by Steam Deck compatibility status.

        Args:
            games: List of games to categorize.
            progress_callback: Optional callback(current_index, game_name).

        Returns:
            Number of categories added.
        """
        categories_added = 0
        for i, game in enumerate(games):
            if progress_callback:
                progress_callback(i, game.name)
            status = game.steam_deck_status.lower() if game.steam_deck_status else ""
            if not status or status not in self._DECK_STATUS_KEYS:
                continue
            category = f"{t('auto_categorize.cat_deck_' + status)} {t('emoji.vr')}"
            categories_added += self._add_category(game, category)
        return categories_added

    _PEGI_BUCKETS: tuple[tuple[str, str], ...] = (
        ("3", "auto_categorize.pegi_3"),
        ("7", "auto_categorize.pegi_7"),
        ("12", "auto_categorize.pegi_12"),
        ("16", "auto_categorize.pegi_16"),
        ("18", "auto_categorize.pegi_18"),
    )

    def categorize_by_pegi(self, games: list[Game], progress_callback: Callable[[int, str], None] | None = None) -> int:
        """Categorize games by PEGI age rating.

        Args:
            games: List of games to categorize.
            progress_callback: Optional callback(current_index, game_name).

        Returns:
            Number of categories added.
        """
        categories_added = 0
        for i, game in enumerate(games):
            if progress_callback:
                progress_callback(i, game.name)
            pegi = game.pegi_rating or ""
            if pegi:
                for rating, key in self._PEGI_BUCKETS:
                    if str(pegi) == rating:
                        label = t(key)
                        break
                else:
                    label = t("auto_categorize.pegi_unknown")
            else:
                label = t("auto_categorize.pegi_unknown")
            category = t("auto_categorize.cat_pegi", rating=label)
            categories_added += self._add_category(game, category)
        return categories_added

    def categorize_by_achievements(
        self, games: list[Game], progress_callback: Callable[[int, str], None] | None = None
    ) -> int:
        """Categorize games by achievement completion percentage.

        Args:
            games: List of games to categorize.
            progress_callback: Optional callback(current_index, game_name).

        Returns:
            Number of categories added.
        """
        categories_added = 0
        for i, game in enumerate(games):
            if progress_callback:
                progress_callback(i, game.name)
            if game.achievement_total == 0:
                continue
            pct = game.achievement_percentage
            trophy = t("emoji.trophy")
            if game.achievement_perfect:
                cat_name = f"{t('auto_categorize.cat_achievement_perfect')} {trophy}"
            elif pct >= 75:
                cat_name = f"{t('auto_categorize.cat_achievement_almost')} {trophy}"
            elif pct >= 25:
                cat_name = f"{t('auto_categorize.cat_achievement_progress')} {trophy}"
            else:
                cat_name = f"{t('auto_categorize.cat_achievement_started')} {trophy}"
            categories_added += self._add_category(game, cat_name)
        return categories_added

    def categorize_by_curator(
        self,
        games: list[Game],
        curator_url: str,
        included_types: set[CuratorRecommendation] | None = None,
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> int:
        """Categorize games based on a Steam Curator's recommendations.

        Args:
            games: List of games to categorize.
            curator_url: Steam Curator URL or numeric ID.
            included_types: Set of recommendation types to include.
            progress_callback: Optional callback(current_index, game_name).

        Returns:
            Number of categories added.

        Raises:
            ValueError: If the curator URL is invalid.
            ConnectionError: If the Steam Store API is unreachable.
        """
        if included_types is None:
            included_types = set(CuratorRecommendation)
        client = CuratorClient()
        recommendations = client.fetch_recommendations(curator_url)
        raw_name = CuratorClient.parse_curator_name(curator_url)
        if not raw_name:
            curator_id = CuratorClient.parse_curator_id(curator_url)
            raw_name = f"Curator {curator_id}" if curator_id else "Curator"
        curator_name = f"{raw_name} {t('emoji.curator')}"
        categories_added = 0
        for i, game in enumerate(games):
            if progress_callback:
                progress_callback(i, game.name)
            try:
                numeric_id = int(game.app_id)
            except (ValueError, TypeError):
                continue
            rec_type = recommendations.get(numeric_id)
            if rec_type is None or rec_type not in included_types:
                continue
            categories_added += self._add_category(game, curator_name)
        return categories_added

    # -- Cache coverage & time estimation ----------------------------------

    def get_cache_coverage(self, games: list[Game]) -> dict[str, Any]:
        """Get cache coverage for games (for tags method).

        Args:
            games: List of games to check.

        Returns:
            Dictionary with 'total', 'cached', 'missing', 'percentage'.
        """
        if not self.steam_scraper:
            return {"total": len(games), "cached": 0, "missing": len(games), "percentage": 0.0}
        app_ids = [game.app_id for game in games]
        return self.steam_scraper.get_cache_coverage(app_ids)

    @staticmethod
    def estimate_time(missing_count: int) -> str:
        """Estimate time for fetching missing tags.

        Args:
            missing_count: Number of games with missing cache.

        Returns:
            Formatted time string.
        """
        estimated_seconds = int(missing_count * 1.5)
        estimated_minutes = estimated_seconds // 60
        if estimated_minutes > 60:
            hours = estimated_minutes // 60
            mins = estimated_minutes % 60
            return t("time.time_hours", hours=hours, minutes=mins)
        elif estimated_minutes > 0:
            return t("time.time_minutes", minutes=estimated_minutes)
        else:
            return t("time.time_seconds", seconds=estimated_seconds)
