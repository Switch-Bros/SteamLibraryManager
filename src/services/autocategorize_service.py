"""
Auto-Categorize Service for Steam Library Manager.

This service handles all auto-categorization operations including:
- Categorizing games by Steam Store tags
- Categorizing games by publisher
- Categorizing games by detected franchise
- Categorizing games by genre
- Categorizing games by developer
- Categorizing games by platform
- Categorizing games by user score
- Categorizing games by playtime (hours played)
- Categorizing games by feature flags
- Categorizing games by VR support
- Cache coverage checking for tags
- Time estimation for tag fetching

The service acts as a bridge between the UI and various managers,
providing a clean API for auto-categorization operations.
"""

from __future__ import annotations

from typing import Callable, Any

from src.core.game_manager import Game, GameManager
from src.integrations.steam_store import SteamStoreScraper
from src.services.category_service import CategoryService
from src.utils.i18n import t

__all__ = ["AutoCategorizeService"]


class AutoCategorizeService:
    """Service for managing auto-categorization operations."""

    def __init__(
        self,
        game_manager: GameManager,
        category_service: CategoryService,
        steam_scraper: SteamStoreScraper | None = None,
    ):
        """
        Initialize the AutoCategorizeService.

        Args:
            game_manager: Manager for accessing game data.
            category_service: Service for category operations.
            steam_scraper: Optional scraper for Steam Store data (required for tags).
        """
        self.game_manager = game_manager
        self.category_service = category_service
        self.steam_scraper = steam_scraper

    # === TAGS CATEGORIZATION ===

    def categorize_by_tags(
        self, games: list[Game], tags_count: int, progress_callback: Callable[[int, str], None] | None = None
    ) -> int:
        """
        Categorize games by Steam Store tags.

        Fetches top N tags for each game from Steam Store and adds them as categories.

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

            # Fetch tags from Steam Store
            all_tags = self.steam_scraper.fetch_tags(game.app_id)
            tags = all_tags[:tags_count]

            # Add each tag as a category
            for tag in tags:
                try:
                    self.category_service.add_app_to_category(game.app_id, tag)
                    if tag not in game.categories:
                        game.categories.append(tag)
                    categories_added += 1
                except (ValueError, RuntimeError):
                    # Category already exists or parser not available
                    pass

        return categories_added

    # === PUBLISHER CATEGORIZATION ===

    def categorize_by_publisher(
        self, games: list[Game], progress_callback: Callable[[int, str], None] | None = None
    ) -> int:
        """
        Categorize games by publisher.

        Creates categories in format "Publisher: <name>" for each game with a publisher.

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

            if not game.publisher:
                continue

            # Create publisher category
            category = t("auto_categorize.cat_publisher", name=game.publisher)

            try:
                self.category_service.add_app_to_category(game.app_id, category)
                if category not in game.categories:
                    game.categories.append(category)
                categories_added += 1
            except (ValueError, RuntimeError):
                # Category already exists or parser not available
                pass

        return categories_added

    # === FRANCHISE CATEGORIZATION ===

    def categorize_by_franchise(
        self, games: list[Game], progress_callback: Callable[[int, str], None] | None = None
    ) -> int:
        """
        Categorize games by detected franchise.

        Uses SteamStoreScraper.detect_franchise() to detect franchise from game name.
        Creates categories in format "Franchise: <name>".

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

            # Detect franchise from game name
            franchise = SteamStoreScraper.detect_franchise(game.name)

            if not franchise:
                continue

            # Create franchise category
            category = t("auto_categorize.cat_franchise", name=franchise)

            try:
                self.category_service.add_app_to_category(game.app_id, category)
                if category not in game.categories:
                    game.categories.append(category)
                categories_added += 1
            except (ValueError, RuntimeError):
                # Category already exists or parser not available
                pass

        return categories_added

    # === GENRE CATEGORIZATION ===

    def categorize_by_genre(
        self, games: list[Game], progress_callback: Callable[[int, str], None] | None = None
    ) -> int:
        """
        Categorize games by genre.

        Adds all genres from game.genres as categories.

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

            if not game.genres:
                continue

            # Add each genre as a category
            for genre in game.genres:
                try:
                    self.category_service.add_app_to_category(game.app_id, genre)
                    if genre not in game.categories:
                        game.categories.append(genre)
                    categories_added += 1
                except (ValueError, RuntimeError):
                    # Category already exists or parser not available
                    pass

        return categories_added

    # === DEVELOPER CATEGORIZATION ===

    def categorize_by_developer(
        self, games: list[Game], progress_callback: Callable[[int, str], None] | None = None
    ) -> int:
        """
        Categorize games by developer.

        Creates categories in format "Developer: <name>" for each game with a developer.

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

            if not game.developer:
                continue

            category = t("auto_categorize.cat_developer", name=game.developer)

            try:
                self.category_service.add_app_to_category(game.app_id, category)
                if category not in game.categories:
                    game.categories.append(category)
                categories_added += 1
            except (ValueError, RuntimeError):
                pass

        return categories_added

    # === PLATFORM CATEGORIZATION ===

    def categorize_by_platform(
        self, games: list[Game], progress_callback: Callable[[int, str], None] | None = None
    ) -> int:
        """
        Categorize games by supported platform.

        Creates categories like "Platform: Linux", "Platform: Windows" for each platform.

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

            if not game.platforms:
                continue

            for platform in game.platforms:
                category = t("auto_categorize.cat_platform", name=platform.capitalize())

                try:
                    self.category_service.add_app_to_category(game.app_id, category)
                    if category not in game.categories:
                        game.categories.append(category)
                    categories_added += 1
                except (ValueError, RuntimeError):
                    pass

        return categories_added

    # === USER SCORE CATEGORIZATION ===

    _SCORE_THRESHOLDS: list[tuple[int, str]] = [
        (95, "ui.reviews.overwhelmingly_positive"),
        (80, "ui.reviews.very_positive"),
        (70, "ui.reviews.positive"),
        (40, "ui.reviews.mixed"),
        (0, "ui.reviews.negative"),
    ]

    def categorize_by_user_score(
        self, games: list[Game], progress_callback: Callable[[int, str], None] | None = None
    ) -> int:
        """
        Categorize games by Steam user review score.

        Buckets review_percentage into score tiers (Overwhelmingly Positive, etc.).
        Games without a review score are skipped.

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

            if not game.review_percentage:
                continue

            label = self._get_score_label(game.review_percentage)
            category = t("auto_categorize.cat_user_score", name=label)

            try:
                self.category_service.add_app_to_category(game.app_id, category)
                if category not in game.categories:
                    game.categories.append(category)
                categories_added += 1
            except (ValueError, RuntimeError):
                pass

        return categories_added

    def _get_score_label(self, score: int) -> str:
        """
        Map a review percentage to a human-readable score label.

        Args:
            score: Review percentage (0-100).

        Returns:
            Translated score label string.
        """
        for threshold, key in self._SCORE_THRESHOLDS:
            if score >= threshold:
                return t(key)
        return t("ui.reviews.negative")

    # === HOURS PLAYED CATEGORIZATION ===

    _PLAYTIME_RANGES: list[tuple[int, int, str]] = [
        (0, 0, "auto_categorize.hours_never"),
        (1, 120, "auto_categorize.hours_0_2"),
        (121, 600, "auto_categorize.hours_2_10"),
        (601, 3000, "auto_categorize.hours_10_50"),
        (3001, 6000, "auto_categorize.hours_50_100"),
        (6001, 999999, "auto_categorize.hours_100_plus"),
    ]

    def categorize_by_hours_played(
        self, games: list[Game], progress_callback: Callable[[int, str], None] | None = None
    ) -> int:
        """
        Categorize games by playtime ranges.

        Buckets playtime_minutes into ranges like "0-2h", "10-50h", "100h+".

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

            range_label = self._get_playtime_label(game.playtime_minutes)
            category = t("auto_categorize.cat_hours_played", range=range_label)

            try:
                self.category_service.add_app_to_category(game.app_id, category)
                if category not in game.categories:
                    game.categories.append(category)
                categories_added += 1
            except (ValueError, RuntimeError):
                pass

        return categories_added

    def _get_playtime_label(self, minutes: int) -> str:
        """
        Map playtime minutes to a range label.

        Args:
            minutes: Total playtime in minutes.

        Returns:
            Translated playtime range label.
        """
        for low, high, key in self._PLAYTIME_RANGES:
            if low <= minutes <= high:
                return t(key)
        return t("auto_categorize.hours_100_plus")

    # === FLAGS CATEGORIZATION ===

    def categorize_by_flags(
        self, games: list[Game], progress_callback: Callable[[int, str], None] | None = None
    ) -> int:
        """
        Categorize games by feature flags (e.g. Free to Play).

        Currently checks for the is_free field. Will be extended with DB fields
        (workshop, trading_cards, controller_support) in later phases.

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

            flags = self._detect_flags(game)

            for flag_name in flags:
                category = t("auto_categorize.cat_flags", name=flag_name)

                try:
                    self.category_service.add_app_to_category(game.app_id, category)
                    if category not in game.categories:
                        game.categories.append(category)
                    categories_added += 1
                except (ValueError, RuntimeError):
                    pass

        return categories_added

    @staticmethod
    def _detect_flags(game: Game) -> list[str]:
        """
        Detect feature flags from Game fields.

        Args:
            game: The game to check.

        Returns:
            List of flag display names.
        """
        flags: list[str] = []
        if getattr(game, "is_free", False):
            flags.append("Free to Play")
        return flags

    # === VR CATEGORIZATION ===

    def categorize_by_vr(self, games: list[Game], progress_callback: Callable[[int, str], None] | None = None) -> int:
        """
        Categorize games by VR support level.

        Checks the vr_support field for values like "required" or "supported".
        Games without VR data are skipped.

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

            vr_support: str = getattr(game, "vr_support", "")
            if not vr_support:
                continue

            category = t("auto_categorize.cat_vr", name=vr_support.capitalize())

            try:
                self.category_service.add_app_to_category(game.app_id, category)
                if category not in game.categories:
                    game.categories.append(category)
                categories_added += 1
            except (ValueError, RuntimeError):
                pass

        return categories_added

    # === YEAR CATEGORIZATION ===

    def categorize_by_year(self, games: list[Game], progress_callback: Callable[[int, str], None] | None = None) -> int:
        """
        Categorize games by release year.

        Creates categories in format "Year: <year>" for each game with a release_year.
        Games without a release_year are skipped.

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

            if not game.release_year:
                continue

            category = t("auto_categorize.cat_year", year=game.release_year)

            try:
                self.category_service.add_app_to_category(game.app_id, category)
                if category not in game.categories:
                    game.categories.append(category)
                categories_added += 1
            except (ValueError, RuntimeError):
                pass

        return categories_added

    # === HLTB CATEGORIZATION ===

    _HLTB_RANGES: list[tuple[float, float, str]] = [
        (0.1, 5, "auto_categorize.hltb_under_5"),
        (5, 15, "auto_categorize.hltb_5_15"),
        (15, 30, "auto_categorize.hltb_15_30"),
        (30, 50, "auto_categorize.hltb_30_50"),
        (50, 999999, "auto_categorize.hltb_50_plus"),
    ]

    def categorize_by_hltb(self, games: list[Game], progress_callback: Callable[[int, str], None] | None = None) -> int:
        """
        Categorize games by HowLongToBeat main story duration.

        Buckets hltb_main_story hours into ranges like "Under 5h", "5-15h", etc.
        Games without HLTB data (hltb_main_story <= 0) are skipped.

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

            hours = getattr(game, "hltb_main_story", 0.0)
            if not hours or hours <= 0:
                continue

            range_label = self._get_hltb_label(hours)
            category = t("auto_categorize.cat_hltb", range=range_label)

            try:
                self.category_service.add_app_to_category(game.app_id, category)
                if category not in game.categories:
                    game.categories.append(category)
                categories_added += 1
            except (ValueError, RuntimeError):
                pass

        return categories_added

    def _get_hltb_label(self, hours: float) -> str:
        """
        Map HLTB hours to a range label.

        Args:
            hours: Main story duration in hours.

        Returns:
            Translated HLTB range label.
        """
        for low, high, key in self._HLTB_RANGES:
            if low <= hours < high:
                return t(key)
        return t("auto_categorize.hltb_50_plus")

    # === LANGUAGE CATEGORIZATION ===

    def categorize_by_language(
        self, games: list[Game], progress_callback: Callable[[int, str], None] | None = None
    ) -> int:
        """
        Categorize games by supported interface languages.

        Creates categories in format "Language: <name>" for each interface language.
        Games without language data are skipped.

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

            languages: list[str] = getattr(game, "languages", None) or []
            if not languages:
                continue

            for language in languages:
                category = t("auto_categorize.cat_language", name=language)

                try:
                    self.category_service.add_app_to_category(game.app_id, category)
                    if category not in game.categories:
                        game.categories.append(category)
                    categories_added += 1
                except (ValueError, RuntimeError):
                    pass

        return categories_added

    # === CACHE COVERAGE ===

    def get_cache_coverage(self, games: list[Game]) -> dict[str, Any]:
        """
        Get cache coverage for games (for tags method).

        Checks how many games have cached Steam Store data.

        Args:
            games: List of games to check.

        Returns:
            Dictionary with 'total', 'cached', 'missing', 'percentage'.
            Returns zeros if steam_scraper is not available.
        """
        if not self.steam_scraper:
            return {"total": len(games), "cached": 0, "missing": len(games), "percentage": 0.0}

        app_ids = [game.app_id for game in games]
        return self.steam_scraper.get_cache_coverage(app_ids)

    # === TIME ESTIMATION ===

    @staticmethod
    def estimate_time(missing_count: int) -> str:
        """
        Estimate time for fetching missing tags.

        Assumes ~1.5 seconds per game.

        Args:
            missing_count: Number of games with missing cache.

        Returns:
            Formatted time string (e.g., "5 Minuten", "1 Stunde 30 Minuten").
        """
        estimated_seconds = int(missing_count * 1.5)
        estimated_minutes = estimated_seconds // 60

        # Format time string
        if estimated_minutes > 60:
            hours = estimated_minutes // 60
            mins = estimated_minutes % 60
            return t("time.time_hours", hours=hours, minutes=mins)
        elif estimated_minutes > 0:
            return t("time.time_minutes", minutes=estimated_minutes)
        else:
            return t("time.time_seconds", seconds=estimated_seconds)
