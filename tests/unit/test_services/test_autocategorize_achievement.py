# tests/unit/test_services/test_autocategorize_achievement.py

"""Tests for AutoCategorizeService.categorize_by_achievements."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.core.game import Game
from src.services.autocategorize_service import AutoCategorizeService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_game(
    app_id: str = "1",
    name: str = "TestGame",
    achievement_total: int = 0,
    achievement_unlocked: int = 0,
    achievement_percentage: float = 0.0,
    achievement_perfect: bool = False,
) -> Game:
    """Helper to create a Game with achievement fields."""
    return Game(
        app_id=app_id,
        name=name,
        achievement_total=achievement_total,
        achievement_unlocked=achievement_unlocked,
        achievement_percentage=achievement_percentage,
        achievement_perfect=achievement_perfect,
    )


@pytest.fixture
def service() -> AutoCategorizeService:
    """Returns an AutoCategorizeService with mocked dependencies."""
    game_manager = MagicMock()
    category_service = MagicMock()
    return AutoCategorizeService(game_manager, category_service)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCategorizeByAchievements:
    """Tests for categorize_by_achievements method."""

    @patch("src.services.autocategorize_service.t", side_effect=lambda key, **kw: key)
    def test_perfect_game_categorized(self, mock_t: MagicMock, service: AutoCategorizeService) -> None:
        """Perfect game gets a 'Perfect Games' category."""
        game = _make_game(
            "1",
            "Perfector",
            achievement_total=30,
            achievement_unlocked=30,
            achievement_percentage=100.0,
            achievement_perfect=True,
        )
        result = service.categorize_by_achievements([game])
        assert result == 1
        service.category_service.add_app_to_category.assert_called_once()
        call_args = service.category_service.add_app_to_category.call_args[0]
        assert "cat_achievement_perfect" in call_args[1]

    @patch("src.services.autocategorize_service.t", side_effect=lambda key, **kw: key)
    def test_almost_done_categorized(self, mock_t: MagicMock, service: AutoCategorizeService) -> None:
        """Game with 75-99% gets 'Almost Done' category."""
        game = _make_game("1", "Almoster", achievement_total=50, achievement_unlocked=45, achievement_percentage=90.0)
        result = service.categorize_by_achievements([game])
        assert result == 1
        call_args = service.category_service.add_app_to_category.call_args[0]
        assert "cat_achievement_almost" in call_args[1]

    @patch("src.services.autocategorize_service.t", side_effect=lambda key, **kw: key)
    def test_in_progress_categorized(self, mock_t: MagicMock, service: AutoCategorizeService) -> None:
        """Game with 25-74% gets 'In Progress' category."""
        game = _make_game("1", "Worker", achievement_total=50, achievement_unlocked=25, achievement_percentage=50.0)
        result = service.categorize_by_achievements([game])
        assert result == 1
        call_args = service.category_service.add_app_to_category.call_args[0]
        assert "cat_achievement_progress" in call_args[1]

    @patch("src.services.autocategorize_service.t", side_effect=lambda key, **kw: key)
    def test_just_started_categorized(self, mock_t: MagicMock, service: AutoCategorizeService) -> None:
        """Game with <25% gets 'Just Started' category."""
        game = _make_game("1", "Beginner", achievement_total=50, achievement_unlocked=5, achievement_percentage=10.0)
        result = service.categorize_by_achievements([game])
        assert result == 1
        call_args = service.category_service.add_app_to_category.call_args[0]
        assert "cat_achievement_started" in call_args[1]

    @patch("src.services.autocategorize_service.t", side_effect=lambda key, **kw: key)
    def test_no_achievements_skipped(self, mock_t: MagicMock, service: AutoCategorizeService) -> None:
        """Games with achievement_total == 0 are skipped."""
        game = _make_game("1", "NoAch", achievement_total=0)
        result = service.categorize_by_achievements([game])
        assert result == 0
        service.category_service.add_app_to_category.assert_not_called()

    @patch("src.services.autocategorize_service.t", side_effect=lambda key, **kw: key)
    def test_empty_list_returns_zero(self, mock_t: MagicMock, service: AutoCategorizeService) -> None:
        """Empty game list returns 0."""
        result = service.categorize_by_achievements([])
        assert result == 0

    @patch("src.services.autocategorize_service.t", side_effect=lambda key, **kw: key)
    def test_progress_callback_called(self, mock_t: MagicMock, service: AutoCategorizeService) -> None:
        """Progress callback is called for each game."""
        games = [
            _make_game("1", "Game A", achievement_total=50, achievement_percentage=100.0, achievement_perfect=True),
            _make_game("2", "Game B", achievement_total=0),
            _make_game("3", "Game C", achievement_total=50, achievement_percentage=50.0),
        ]
        callback = MagicMock()
        service.categorize_by_achievements(games, progress_callback=callback)
        assert callback.call_count == 3
        callback.assert_any_call(0, "Game A")
        callback.assert_any_call(1, "Game B")
        callback.assert_any_call(2, "Game C")

    @patch("src.services.autocategorize_service.t", side_effect=lambda key, **kw: key)
    def test_mixed_list_correct_counts(self, mock_t: MagicMock, service: AutoCategorizeService) -> None:
        """Mixed list: only games with achievements get categories."""
        games = [
            _make_game("1", "Perfect", achievement_total=30, achievement_percentage=100.0, achievement_perfect=True),
            _make_game("2", "NoAch", achievement_total=0),
            _make_game("3", "Almost", achievement_total=50, achievement_percentage=80.0),
            _make_game("4", "Progress", achievement_total=50, achievement_percentage=50.0),
            _make_game("5", "Started", achievement_total=50, achievement_percentage=10.0),
        ]
        result = service.categorize_by_achievements(games)
        assert result == 4  # All except NoAch
        assert service.category_service.add_app_to_category.call_count == 4

    @patch("src.services.autocategorize_service.t", side_effect=lambda key, **kw: key)
    def test_boundary_75_is_almost(self, mock_t: MagicMock, service: AutoCategorizeService) -> None:
        """Game with exactly 75% gets 'Almost Done' category."""
        game = _make_game("1", "Boundary", achievement_total=100, achievement_percentage=75.0)
        service.categorize_by_achievements([game])
        call_args = service.category_service.add_app_to_category.call_args[0]
        assert "cat_achievement_almost" in call_args[1]

    @patch("src.services.autocategorize_service.t", side_effect=lambda key, **kw: key)
    def test_boundary_25_is_progress(self, mock_t: MagicMock, service: AutoCategorizeService) -> None:
        """Game with exactly 25% gets 'In Progress' category."""
        game = _make_game("1", "Boundary", achievement_total=100, achievement_percentage=25.0)
        service.categorize_by_achievements([game])
        call_args = service.category_service.add_app_to_category.call_args[0]
        assert "cat_achievement_progress" in call_args[1]
