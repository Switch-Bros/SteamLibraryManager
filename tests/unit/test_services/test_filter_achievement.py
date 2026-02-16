# tests/unit/test_services/test_filter_achievement.py

"""Tests for the Achievement filter in FilterService."""

from __future__ import annotations

import pytest

from src.core.game import Game
from src.services.filter_service import (
    ALL_ACHIEVEMENT_KEYS,
    FilterService,
    FilterState,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_game(
    app_id: str = "1",
    name: str = "TestGame",
    app_type: str = "game",
    achievement_total: int = 0,
    achievement_unlocked: int = 0,
    achievement_percentage: float = 0.0,
    achievement_perfect: bool = False,
) -> Game:
    """Helper to create a Game with achievement fields."""
    return Game(
        app_id=app_id,
        name=name,
        app_type=app_type,
        achievement_total=achievement_total,
        achievement_unlocked=achievement_unlocked,
        achievement_percentage=achievement_percentage,
        achievement_perfect=achievement_perfect,
    )


@pytest.fixture
def service() -> FilterService:
    """Returns a fresh FilterService instance."""
    return FilterService()


@pytest.fixture
def achievement_games() -> list[Game]:
    """Returns a set of games covering all achievement buckets."""
    return [
        _make_game(
            "1",
            "Perfect Game",
            achievement_total=50,
            achievement_unlocked=50,
            achievement_percentage=100.0,
            achievement_perfect=True,
        ),
        _make_game("2", "Almost Game", achievement_total=50, achievement_unlocked=45, achievement_percentage=90.0),
        _make_game("3", "Progress Game", achievement_total=50, achievement_unlocked=25, achievement_percentage=50.0),
        _make_game("4", "Started Game", achievement_total=50, achievement_unlocked=5, achievement_percentage=10.0),
        _make_game("5", "No Achievements", achievement_total=0),
    ]


# ---------------------------------------------------------------------------
# Toggle method
# ---------------------------------------------------------------------------


class TestToggleAchievementFilter:
    """Tests for toggle_achievement_filter method."""

    def test_toggle_adds_key(self, service: FilterService) -> None:
        """Toggling an achievement filter on adds it to the active set."""
        service.toggle_achievement_filter("perfect", True)
        assert "perfect" in service.state.active_achievement_filters

    def test_toggle_removes_key(self, service: FilterService) -> None:
        """Toggling an achievement filter off removes it from the active set."""
        service.toggle_achievement_filter("perfect", True)
        service.toggle_achievement_filter("perfect", False)
        assert "perfect" not in service.state.active_achievement_filters

    def test_toggle_unknown_key_ignored(self, service: FilterService) -> None:
        """Unknown achievement filter keys are silently ignored."""
        service.toggle_achievement_filter("bogus", True)
        assert service.state.active_achievement_filters == frozenset()

    def test_toggle_all_valid_keys(self, service: FilterService) -> None:
        """All keys in ALL_ACHIEVEMENT_KEYS can be toggled."""
        for key in ALL_ACHIEVEMENT_KEYS:
            service.toggle_achievement_filter(key, True)
        assert service.state.active_achievement_filters == ALL_ACHIEVEMENT_KEYS


# ---------------------------------------------------------------------------
# Filter logic (_passes_achievement_filter via apply)
# ---------------------------------------------------------------------------


class TestPassesAchievementFilter:
    """Tests for _passes_achievement_filter via apply()."""

    def test_no_active_returns_all(self, service: FilterService, achievement_games: list[Game]) -> None:
        """When no achievement filter is active, all games pass."""
        result = service.apply(achievement_games)
        assert len(result) == len(achievement_games)

    def test_perfect_only(self, service: FilterService, achievement_games: list[Game]) -> None:
        """Only perfect games pass when 'perfect' filter is active."""
        service.toggle_achievement_filter("perfect", True)
        result = service.apply(achievement_games)
        assert len(result) == 1
        assert result[0].achievement_perfect is True

    def test_almost_only(self, service: FilterService, achievement_games: list[Game]) -> None:
        """Only 75-99% games pass when 'almost' filter is active."""
        service.toggle_achievement_filter("almost", True)
        result = service.apply(achievement_games)
        assert len(result) == 1
        assert result[0].name == "Almost Game"

    def test_progress_only(self, service: FilterService, achievement_games: list[Game]) -> None:
        """Only 25-74% games pass when 'progress' filter is active."""
        service.toggle_achievement_filter("progress", True)
        result = service.apply(achievement_games)
        assert len(result) == 1
        assert result[0].name == "Progress Game"

    def test_started_only(self, service: FilterService, achievement_games: list[Game]) -> None:
        """Only <25% games pass when 'started' filter is active."""
        service.toggle_achievement_filter("started", True)
        result = service.apply(achievement_games)
        assert len(result) == 1
        assert result[0].name == "Started Game"

    def test_none_only(self, service: FilterService, achievement_games: list[Game]) -> None:
        """Only games without achievements pass when 'none' filter is active."""
        service.toggle_achievement_filter("none", True)
        result = service.apply(achievement_games)
        assert len(result) == 1
        assert result[0].achievement_total == 0

    def test_or_logic_perfect_and_almost(self, service: FilterService, achievement_games: list[Game]) -> None:
        """OR logic: perfect OR almost games pass."""
        service.toggle_achievement_filter("perfect", True)
        service.toggle_achievement_filter("almost", True)
        result = service.apply(achievement_games)
        assert len(result) == 2
        names = {g.name for g in result}
        assert names == {"Perfect Game", "Almost Game"}

    def test_all_filters_active_returns_all(self, service: FilterService, achievement_games: list[Game]) -> None:
        """All achievement filters active returns all games."""
        for key in ALL_ACHIEVEMENT_KEYS:
            service.toggle_achievement_filter(key, True)
        result = service.apply(achievement_games)
        assert len(result) == len(achievement_games)


# ---------------------------------------------------------------------------
# Boundary values
# ---------------------------------------------------------------------------


class TestAchievementBoundaries:
    """Tests for boundary values in achievement filter buckets."""

    def test_exactly_75_is_almost(self, service: FilterService) -> None:
        """Game with exactly 75% falls into 'almost' bucket."""
        game = _make_game("1", "Boundary", achievement_total=100, achievement_percentage=75.0)
        service.toggle_achievement_filter("almost", True)
        result = service.apply([game])
        assert len(result) == 1

    def test_exactly_25_is_progress(self, service: FilterService) -> None:
        """Game with exactly 25% falls into 'progress' bucket."""
        game = _make_game("1", "Boundary", achievement_total=100, achievement_percentage=25.0)
        service.toggle_achievement_filter("progress", True)
        result = service.apply([game])
        assert len(result) == 1

    def test_just_under_75_is_progress(self, service: FilterService) -> None:
        """Game with 74.9% falls into 'progress' bucket."""
        game = _make_game("1", "Boundary", achievement_total=100, achievement_percentage=74.9)
        service.toggle_achievement_filter("progress", True)
        result = service.apply([game])
        assert len(result) == 1

    def test_just_under_25_is_started(self, service: FilterService) -> None:
        """Game with 24.9% falls into 'started' bucket."""
        game = _make_game("1", "Boundary", achievement_total=100, achievement_percentage=24.9)
        service.toggle_achievement_filter("started", True)
        result = service.apply([game])
        assert len(result) == 1

    def test_zero_percent_with_achievements_is_not_started(self, service: FilterService) -> None:
        """Game with 0% and total > 0 does NOT match 'started' (0 < pct < 25)."""
        game = _make_game("1", "Zero", achievement_total=50, achievement_percentage=0.0)
        service.toggle_achievement_filter("started", True)
        result = service.apply([game])
        assert len(result) == 0


# ---------------------------------------------------------------------------
# Integration with has_active_filters and state
# ---------------------------------------------------------------------------


class TestAchievementFilterIntegration:
    """Tests for achievement filter in has_active_filters and state restore."""

    def test_has_active_filters_achievement(self, service: FilterService) -> None:
        """Active achievement filter makes has_active_filters() return True."""
        assert not service.has_active_filters()
        service.toggle_achievement_filter("perfect", True)
        assert service.has_active_filters()

    def test_achievement_filter_state_restore(self, service: FilterService) -> None:
        """Achievement filter state is preserved through save/restore cycle."""
        service.toggle_achievement_filter("perfect", True)
        service.toggle_achievement_filter("almost", True)
        state = service.state

        new_service = FilterService()
        new_service.restore_state(state)
        assert new_service.state.active_achievement_filters == frozenset({"perfect", "almost"})

    def test_filter_state_default_achievement_empty(self) -> None:
        """Default FilterState has empty active_achievement_filters."""
        state = FilterState()
        assert state.active_achievement_filters == frozenset()
