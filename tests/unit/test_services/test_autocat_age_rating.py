"""Tests for AutoCat age rating (PEGI) categorization.

Tests the categorize_by_pegi() method on AutoCategorizeService.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from src.core.game import Game


def _make_game(app_id: str = "1", name: str = "Test", pegi: str = "") -> Game:
    """Helper to create a Game with PEGI rating."""
    g = Game(app_id=app_id, name=name)
    g.pegi_rating = pegi
    g.categories = []
    return g


def _make_service():
    """Creates a real AutoCategorizeService with mocked dependencies."""
    from src.services.autocategorize_service import AutoCategorizeService

    service = AutoCategorizeService.__new__(AutoCategorizeService)
    service.category_service = MagicMock()
    service.category_service.add_app_to_category = MagicMock()
    return service


class TestCategorizeByPEGI:
    """Tests for AutoCategorizeService.categorize_by_pegi()."""

    def test_pegi_18_creates_category(self) -> None:
        """Game with PEGI 18 should be categorized."""
        service = _make_service()
        games = [_make_game("1", "Doom Eternal", pegi="18")]
        result = service.categorize_by_pegi(games)
        assert result == 1
        service.category_service.add_app_to_category.assert_called_once()

    def test_pegi_3_creates_category(self) -> None:
        """Game with PEGI 3 should be categorized."""
        service = _make_service()
        games = [_make_game("1", "Stardew Valley", pegi="3")]
        result = service.categorize_by_pegi(games)
        assert result == 1

    def test_no_rating_creates_unknown_category(self) -> None:
        """Game WITHOUT rating MUST get 'Unknown' category, NOT be skipped."""
        service = _make_service()
        games = [_make_game("1", "Mystery Game", pegi="")]
        result = service.categorize_by_pegi(games)
        assert result == 1
        service.category_service.add_app_to_category.assert_called_once()

    def test_none_rating_creates_unknown_category(self) -> None:
        """Game with None rating should also get 'Unknown' category."""
        service = _make_service()
        game = _make_game("1", "Old Game")
        game.pegi_rating = None
        result = service.categorize_by_pegi([game])
        assert result == 1

    def test_all_five_pegi_levels_accepted(self) -> None:
        """All 5 PEGI values (3, 7, 12, 16, 18) should be categorized."""
        service = _make_service()
        games = [
            _make_game("1", "A", pegi="3"),
            _make_game("2", "B", pegi="7"),
            _make_game("3", "C", pegi="12"),
            _make_game("4", "D", pegi="16"),
            _make_game("5", "E", pegi="18"),
        ]
        result = service.categorize_by_pegi(games)
        assert result == 5
        assert service.category_service.add_app_to_category.call_count == 5

    def test_mixed_library_all_categorized(self) -> None:
        """Mix of rated + unrated games should produce categories for all."""
        service = _make_service()
        games = [
            _make_game("1", "A", pegi="3"),
            _make_game("2", "B", pegi="18"),
            _make_game("3", "C", pegi=""),
        ]
        result = service.categorize_by_pegi(games)
        assert result == 3

    def test_progress_callback_invoked_per_game(self) -> None:
        """Progress callback should be called once per game."""
        service = _make_service()
        callback = MagicMock()
        games = [
            _make_game("1", "Alpha", pegi="3"),
            _make_game("2", "Beta", pegi="18"),
            _make_game("3", "Gamma", pegi=""),
        ]
        service.categorize_by_pegi(games, progress_callback=callback)
        assert callback.call_count == 3
        callback.assert_any_call(0, "Alpha")
        callback.assert_any_call(1, "Beta")
        callback.assert_any_call(2, "Gamma")

    def test_empty_game_list_returns_zero(self) -> None:
        """Empty game list should return 0."""
        service = _make_service()
        result = service.categorize_by_pegi([])
        assert result == 0

    def test_category_service_error_handled(self) -> None:
        """ValueError from category_service should not crash."""
        service = _make_service()
        service.category_service.add_app_to_category.side_effect = ValueError("test")
        games = [_make_game("1", "Crasher", pegi="18")]
        result = service.categorize_by_pegi(games)
        assert result == 0

    def test_invalid_pegi_value_gets_unknown(self) -> None:
        """Unexpected PEGI value (e.g. '99') should fall to Unknown."""
        service = _make_service()
        games = [_make_game("1", "Weird Game", pegi="99")]
        result = service.categorize_by_pegi(games)
        assert result == 1
