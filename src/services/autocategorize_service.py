"""
Auto-Categorize Service for Steam Library Manager.

This service handles all auto-categorization operations including:
- Categorizing games by Steam Store tags
- Categorizing games by publisher
- Categorizing games by detected franchise
- Categorizing games by genre
- Cache coverage checking for tags
- Time estimation for tag fetching

The service acts as a bridge between the UI and various managers,
providing a clean API for auto-categorization operations.
"""

from __future__ import annotations

from typing import Callable, Any

from src.core.game_manager import Game, GameManager
from src.services.category_service import CategoryService
from src.integrations.steam_store import SteamStoreScraper
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
            category = t("ui.auto_categorize.cat_publisher", name=game.publisher)

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
            category = t("ui.auto_categorize.cat_franchise", name=franchise)

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
