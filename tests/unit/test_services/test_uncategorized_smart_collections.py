"""Tests for uncategorized games excluding Smart Collections."""

from __future__ import annotations

from src.core.game import Game
from src.services.game_query_service import GameQueryService


def _make_game(app_id: str, name: str, categories: list[str] | None = None) -> Game:
    """Creates a Game with given categories."""
    return Game(app_id=app_id, name=name, app_type="game", categories=categories or [])


class TestUncategorizedSmartCollections:
    """Tests that Smart Collections are excluded from uncategorized check."""

    def test_excludes_smart_collections(self) -> None:
        """Game only in a Smart Collection is still uncategorized."""
        games = {
            "1": _make_game("1", "Game A", ["My Smart Collection"]),
            "2": _make_game("2", "Game B", []),
        }
        svc = GameQueryService(games, filter_non_games=False)

        result = svc.get_uncategorized_games(
            smart_collection_names={"My Smart Collection"},
        )

        app_ids = {g.app_id for g in result}
        assert "1" in app_ids  # Only in SC → still uncategorized
        assert "2" in app_ids  # No categories at all

    def test_real_collection_counts(self) -> None:
        """Game in a real Steam collection is NOT uncategorized."""
        games = {
            "1": _make_game("1", "Game A", ["Action"]),
            "2": _make_game("2", "Game B", []),
        }
        svc = GameQueryService(games, filter_non_games=False)

        result = svc.get_uncategorized_games(
            smart_collection_names={"My Smart Collection"},
        )

        app_ids = {g.app_id for g in result}
        assert "1" not in app_ids  # In real collection → categorized
        assert "2" in app_ids  # No categories → uncategorized

    def test_mixed_collections(self) -> None:
        """Game in both Smart + real collection is categorized."""
        games = {
            "1": _make_game("1", "Game A", ["Action", "My Smart Collection"]),
            "2": _make_game("2", "Game B", ["My Smart Collection"]),
        }
        svc = GameQueryService(games, filter_non_games=False)

        result = svc.get_uncategorized_games(
            smart_collection_names={"My Smart Collection"},
        )

        app_ids = {g.app_id for g in result}
        assert "1" not in app_ids  # Has "Action" → categorized
        assert "2" in app_ids  # Only SC → still uncategorized
