"""Verification tests for B2 (Favorites pinning) and B4 (Uncategorized count).

B2: Favorites must be recognized regardless of locale so they appear at
    position 2 in the sidebar (after "All Games").
B4: Uncategorized count must exclude all system categories (all known
    locale variants) AND Smart Collections.
"""

from __future__ import annotations

import pytest

from src.core.game import Game
from src.services.enrichment.metadata_enrichment_service import MetadataEnrichmentService
from src.services.game_query_service import GameQueryService


def _make_game(
    app_id: str,
    name: str = "TestGame",
    categories: list[str] | None = None,
    app_type: str = "",
) -> Game:
    """Creates a Game with optional categories and type."""
    g = Game(app_id=app_id, name=name, app_type=app_type)
    g.categories = list(categories) if categories else []
    return g


class TestVerifyB2FavoritesPinning:
    """B2: Favorites must be detected in any locale variant via enrichment.

    The enrichment service writes the *current locale* favorites key into
    game.categories.  get_favorites() then finds those games.  This test
    verifies the full enrichment → query chain for all known variants.
    """

    def _make_parser(self, collections: list[dict]) -> object:
        """Creates a mock parser with collections."""

        class FakeParser:
            def __init__(self, colls):
                self.collections = colls

            def get_app_categories(self, app_id):
                return []

            def get_all_app_ids(self):
                return []

        return FakeParser(collections)

    @pytest.mark.parametrize(
        "col_id,col_name",
        [
            ("favorite", "Favorites"),
            ("favorite", "Favoriten"),
            ("custom-id", "Favoriten"),
            ("custom-id", "Favorites"),
        ],
        ids=["steam_id+en", "steam_id+de", "custom+de", "custom+en"],
    )
    def test_enrichment_marks_favorites_for_any_variant(self, col_id: str, col_name: str, tmp_path) -> None:
        """Enrichment detects favorites regardless of collection ID/name combo."""
        games = {"100": _make_game("100", "GameA")}
        service = MetadataEnrichmentService(games, tmp_path)
        parser = self._make_parser([{"id": col_id, "name": col_name, "added": [100], "removed": []}])
        service.merge_with_localconfig(parser)

        # After enrichment, game should be detectable as favorite
        svc = GameQueryService(games, filter_non_games=False)
        favorites = svc.get_favorites()
        assert any(g.app_id == "100" for g in favorites), (
            f"Game should be favorite after enrichment with id='{col_id}', " f"name='{col_name}'"
        )

    def test_favorites_list_non_empty_triggers_sidebar_pinning(self) -> None:
        """When get_favorites() returns games, sidebar will pin them at position 2.

        category_populator.py:164-166 shows favorites at position 2 only if
        the list is non-empty.  This test proves the list is non-empty after
        enrichment.
        """
        games = {"1": _make_game("1", "GameA")}
        service = MetadataEnrichmentService(games, "/tmp")
        parser = self._make_parser([{"id": "favorite", "name": "Favorites", "added": [1], "removed": []}])
        service.merge_with_localconfig(parser)

        svc = GameQueryService(games, filter_non_games=False)
        favorites = svc.get_favorites()
        # Non-empty → category_populator will pin at position 2
        assert len(favorites) > 0


class TestVerifyB4UncategorizedCount:
    """B4: Uncategorized count must match expected behavior."""

    def test_empty_game_is_uncategorized(self) -> None:
        """Game with no categories is uncategorized."""
        games = {"1": _make_game("1")}
        svc = GameQueryService(games, filter_non_games=False)
        assert len(svc.get_uncategorized_games()) == 1

    def test_game_in_user_collection_not_uncategorized(self) -> None:
        """Game in a real user collection is NOT uncategorized."""
        games = {"1": _make_game("1", categories=["Action"])}
        svc = GameQueryService(games, filter_non_games=False)
        assert len(svc.get_uncategorized_games()) == 0

    def test_game_only_in_system_category_is_uncategorized(self) -> None:
        """Game ONLY in a system category counts as uncategorized."""
        games = {"1": _make_game("1", categories=["Favorites"])}
        svc = GameQueryService(games, filter_non_games=False)
        assert len(svc.get_uncategorized_games()) == 1

    def test_non_game_types_excluded_from_uncategorized(self) -> None:
        """Non-game types (music, tool, etc.) are never in uncategorized."""
        games = {
            "1": _make_game("1", app_type="music"),
            "2": _make_game("2", app_type="tool"),
        }
        svc = GameQueryService(games, filter_non_games=False)
        assert len(svc.get_uncategorized_games()) == 0

    def test_smart_collections_dont_count_as_categorized(self) -> None:
        """Smart Collections are SLM-only — don't prevent uncategorized status."""
        games = {"1": _make_game("1", categories=["Top Rated"])}
        svc = GameQueryService(games, filter_non_games=False)
        uncategorized = svc.get_uncategorized_games(
            smart_collection_names={"Top Rated"},
        )
        assert len(uncategorized) == 1

    def test_mixed_scenario_counts_correctly(self) -> None:
        """Verify correct count with mix of categorized/uncategorized/system."""
        games = {
            "1": _make_game("1", categories=["Action"]),  # categorized
            "2": _make_game("2", categories=["Favorites"]),  # system → uncategorized
            "3": _make_game("3"),  # no cats → uncategorized
            "4": _make_game("4", categories=["hidden"]),  # system → uncategorized
            "5": _make_game("5", categories=["RPG", "Favoriten"]),  # real → NOT
            "6": _make_game("6", app_type="music"),  # non-game → excluded
        }
        svc = GameQueryService(games, filter_non_games=False)
        uncategorized = svc.get_uncategorized_games()
        uncategorized_ids = {g.app_id for g in uncategorized}
        assert "1" not in uncategorized_ids  # in Action
        assert "2" in uncategorized_ids  # only Favorites (system)
        assert "3" in uncategorized_ids  # no categories
        assert "4" in uncategorized_ids  # only hidden (system)
        assert "5" not in uncategorized_ids  # has RPG (real)
        assert "6" not in uncategorized_ids  # non-game type excluded
