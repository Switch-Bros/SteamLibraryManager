"""Tests for language-independent system collection matching (FIX B).

Verifies that Favorites and Hidden collections are correctly detected
regardless of locale — using Steam internal IDs, hardcoded EN/DE names,
and current locale translations.
"""

from __future__ import annotations

import pytest

from src.core.game import Game
from src.services.enrichment.metadata_enrichment_service import (
    FAVORITES_IDENTIFIERS,
    HIDDEN_IDENTIFIERS,
    MetadataEnrichmentService,
)
from src.services.game_query_service import GameQueryService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_game(app_id: str, name: str = "TestGame", categories: list[str] | None = None) -> Game:
    """Creates a Game with optional categories."""
    g = Game(app_id=app_id, name=name)
    g.categories = list(categories) if categories else []
    return g


# ---------------------------------------------------------------------------
# FAVORITES_IDENTIFIERS / HIDDEN_IDENTIFIERS completeness
# ---------------------------------------------------------------------------


class TestIdentifierFrozensets:
    """Verify that the frozensets contain all expected variants."""

    def test_favorites_contains_steam_id(self) -> None:
        assert "favorite" in FAVORITES_IDENTIFIERS

    def test_favorites_contains_english(self) -> None:
        assert "Favorites" in FAVORITES_IDENTIFIERS

    def test_favorites_contains_german(self) -> None:
        assert "Favoriten" in FAVORITES_IDENTIFIERS

    def test_hidden_contains_steam_id(self) -> None:
        assert "hidden" in HIDDEN_IDENTIFIERS

    def test_hidden_contains_english(self) -> None:
        assert "Hidden" in HIDDEN_IDENTIFIERS

    def test_hidden_contains_german(self) -> None:
        assert "Versteckt" in HIDDEN_IDENTIFIERS


# ---------------------------------------------------------------------------
# MetadataEnrichmentService — merge_with_localconfig matching
# ---------------------------------------------------------------------------


class TestMergeSystemCollectionMatching:
    """Tests that merge_with_localconfig detects system collections by any name variant."""

    @pytest.fixture()
    def games(self) -> dict[str, Game]:
        return {
            "100": _make_game("100", "GameA"),
            "200": _make_game("200", "GameB"),
        }

    @pytest.fixture()
    def service(self, games: dict[str, Game], tmp_path) -> MetadataEnrichmentService:
        return MetadataEnrichmentService(games, tmp_path)

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

    def test_favorites_detected_by_steam_id(self, service, games) -> None:
        """Collection with id='favorite' should mark apps as favorites."""
        parser = self._make_parser(
            [
                {"id": "favorite", "name": "Favorites", "added": [100], "removed": []},
            ]
        )
        service.merge_with_localconfig(parser)
        assert any("avorit" in c for c in games["100"].categories)

    def test_favorites_detected_by_german_name(self, service, games) -> None:
        """Collection named 'Favoriten' should be detected even with non-standard ID."""
        parser = self._make_parser(
            [
                {"id": "custom-id", "name": "Favoriten", "added": [200], "removed": []},
            ]
        )
        service.merge_with_localconfig(parser)
        assert any("avorit" in c or "avorit" in c for c in games["200"].categories)

    def test_hidden_detected_by_steam_id(self, service, games) -> None:
        """Collection with id='hidden' should mark apps as hidden."""
        parser = self._make_parser(
            [
                {"id": "hidden", "name": "Hidden", "added": [100], "removed": []},
            ]
        )
        service.merge_with_localconfig(parser)
        assert games["100"].hidden is True

    def test_hidden_detected_by_german_name(self, service, games) -> None:
        """Collection named 'Versteckt' should be detected even with non-standard ID."""
        parser = self._make_parser(
            [
                {"id": "custom-hidden-id", "name": "Versteckt", "added": [200], "removed": []},
            ]
        )
        service.merge_with_localconfig(parser)
        assert games["200"].hidden is True


# ---------------------------------------------------------------------------
# GameQueryService — get_uncategorized_games excludes system categories
# ---------------------------------------------------------------------------


class TestUncategorizedExcludesSystemCategories:
    """Tests that get_uncategorized_games ignores ALL system category name variants."""

    def test_game_only_in_favorites_en_is_uncategorized(self) -> None:
        """A game only in 'Favorites' (EN) is still uncategorized."""
        games = {"1": _make_game("1", "Game1", categories=["Favorites"])}
        svc = GameQueryService(games, filter_non_games=False)
        uncategorized = svc.get_uncategorized_games()
        assert any(g.app_id == "1" for g in uncategorized)

    def test_game_only_in_favoriten_de_is_uncategorized(self) -> None:
        """A game only in 'Favoriten' (DE) is still uncategorized."""
        games = {"1": _make_game("1", "Game1", categories=["Favoriten"])}
        svc = GameQueryService(games, filter_non_games=False)
        uncategorized = svc.get_uncategorized_games()
        assert any(g.app_id == "1" for g in uncategorized)

    def test_game_only_in_hidden_en_is_uncategorized(self) -> None:
        """A game only in 'Hidden' (EN) is still uncategorized."""
        games = {"1": _make_game("1", "Game1", categories=["Hidden"])}
        svc = GameQueryService(games, filter_non_games=False)
        uncategorized = svc.get_uncategorized_games()
        assert any(g.app_id == "1" for g in uncategorized)

    def test_game_only_in_versteckt_de_is_uncategorized(self) -> None:
        """A game only in 'Versteckt' (DE) is still uncategorized."""
        games = {"1": _make_game("1", "Game1", categories=["Versteckt"])}
        svc = GameQueryService(games, filter_non_games=False)
        uncategorized = svc.get_uncategorized_games()
        assert any(g.app_id == "1" for g in uncategorized)

    def test_game_only_in_steam_favorite_id_is_uncategorized(self) -> None:
        """A game only in 'favorite' (Steam internal ID) is still uncategorized."""
        games = {"1": _make_game("1", "Game1", categories=["favorite"])}
        svc = GameQueryService(games, filter_non_games=False)
        uncategorized = svc.get_uncategorized_games()
        assert any(g.app_id == "1" for g in uncategorized)

    def test_game_in_real_collection_is_not_uncategorized(self) -> None:
        """A game in a real user collection should NOT be uncategorized."""
        games = {"1": _make_game("1", "Game1", categories=["Action"])}
        svc = GameQueryService(games, filter_non_games=False)
        uncategorized = svc.get_uncategorized_games()
        assert not any(g.app_id == "1" for g in uncategorized)

    def test_game_in_system_and_real_collection_not_uncategorized(self) -> None:
        """A game in both system + real collection is NOT uncategorized."""
        games = {"1": _make_game("1", "Game1", categories=["Favorites", "RPG"])}
        svc = GameQueryService(games, filter_non_games=False)
        uncategorized = svc.get_uncategorized_games()
        assert not any(g.app_id == "1" for g in uncategorized)

    def test_smart_collection_excluded_from_categorization(self) -> None:
        """A game only in a Smart Collection is still uncategorized."""
        games = {"1": _make_game("1", "Game1", categories=["My Smart Collection"])}
        svc = GameQueryService(games, filter_non_games=False)
        uncategorized = svc.get_uncategorized_games(
            smart_collection_names={"My Smart Collection"},
        )
        assert any(g.app_id == "1" for g in uncategorized)

    def test_smart_plus_real_collection_not_uncategorized(self) -> None:
        """A game in Smart Collection + real collection is NOT uncategorized."""
        games = {"1": _make_game("1", "Game1", categories=["My SC", "Action"])}
        svc = GameQueryService(games, filter_non_games=False)
        uncategorized = svc.get_uncategorized_games(
            smart_collection_names={"My SC"},
        )
        assert not any(g.app_id == "1" for g in uncategorized)
