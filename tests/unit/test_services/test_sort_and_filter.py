# tests/unit/test_services/test_sort_and_filter.py

"""Tests for SortKey enum and FilterService sort functionality."""

from __future__ import annotations

from datetime import datetime

import pytest

from src.core.game import Game
from src.services.filter_service import FilterService, FilterState, SortKey

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_game(
    app_id: str = "1",
    name: str = "TestGame",
    sort_name: str = "",
    playtime_minutes: int = 0,
    last_played: datetime | None = None,
    release_year: str = "",
) -> Game:
    """Helper to create a Game with sensible defaults."""
    return Game(
        app_id=app_id,
        name=name,
        sort_name=sort_name or name,
        playtime_minutes=playtime_minutes,
        last_played=last_played,
        release_year=release_year,
    )


@pytest.fixture
def service() -> FilterService:
    """Returns a fresh FilterService instance."""
    return FilterService()


@pytest.fixture
def sample_games() -> list[Game]:
    """Returns a set of games with varied attributes for sort testing."""
    return [
        _make_game("1", "Zelda", playtime_minutes=500, release_year="2023", last_played=datetime(2025, 6, 1)),
        _make_game("2", "Alpha", playtime_minutes=100, release_year="2020", last_played=datetime(2025, 1, 1)),
        _make_game("3", "Mario", playtime_minutes=1000, release_year="2024", last_played=datetime(2026, 1, 1)),
        _make_game("4", "Beta", playtime_minutes=0, release_year=""),
    ]


# ---------------------------------------------------------------------------
# SortKey Enum
# ---------------------------------------------------------------------------


class TestSortKeyEnum:
    """Tests for SortKey enum values."""

    def test_sort_key_values(self) -> None:
        assert SortKey.NAME.value == "name"
        assert SortKey.PLAYTIME.value == "playtime"
        assert SortKey.LAST_PLAYED.value == "last_played"
        assert SortKey.RELEASE_DATE.value == "release_date"

    def test_sort_key_from_string(self) -> None:
        assert SortKey("name") == SortKey.NAME
        assert SortKey("playtime") == SortKey.PLAYTIME

    def test_sort_key_invalid_string_raises(self) -> None:
        with pytest.raises(ValueError):
            SortKey("bogus")


# ---------------------------------------------------------------------------
# FilterService.set_sort_key
# ---------------------------------------------------------------------------


class TestSetSortKey:
    """Tests for FilterService.set_sort_key()."""

    def test_set_sort_key_valid(self, service: FilterService) -> None:
        service.set_sort_key("playtime")
        assert service.sort_key == SortKey.PLAYTIME

    def test_set_sort_key_invalid_falls_back_to_name(self, service: FilterService) -> None:
        service.set_sort_key("bogus")
        assert service.sort_key == SortKey.NAME

    def test_sort_key_in_state(self, service: FilterService) -> None:
        service.set_sort_key("release_date")
        state = service.state
        assert state.sort_key == SortKey.RELEASE_DATE

    def test_sort_key_restore(self, service: FilterService) -> None:
        state = FilterState(sort_key=SortKey.LAST_PLAYED)
        service.restore_state(state)
        assert service.sort_key == SortKey.LAST_PLAYED


# ---------------------------------------------------------------------------
# FilterService.sort_games
# ---------------------------------------------------------------------------


class TestSortGames:
    """Tests for FilterService.sort_games()."""

    def test_sort_by_name_alphabetical(self, service: FilterService, sample_games: list[Game]) -> None:
        result = service.sort_games(sample_games)
        names = [g.name for g in result]
        assert names == ["Alpha", "Beta", "Mario", "Zelda"]

    def test_sort_by_playtime_descending(self, service: FilterService, sample_games: list[Game]) -> None:
        service.set_sort_key("playtime")
        result = service.sort_games(sample_games)
        playtimes = [g.playtime_minutes for g in result]
        assert playtimes == [1000, 500, 100, 0]

    def test_sort_by_last_played_descending(self, service: FilterService, sample_games: list[Game]) -> None:
        service.set_sort_key("last_played")
        result = service.sort_games(sample_games)
        # Mario (2026-01-01) > Zelda (2025-06-01) > Alpha (2025-01-01) > Beta (None)
        names = [g.name for g in result]
        assert names[0] == "Mario"
        assert names[-1] == "Beta"  # None goes last

    def test_sort_by_release_date_descending(self, service: FilterService, sample_games: list[Game]) -> None:
        service.set_sort_key("release_date")
        result = service.sort_games(sample_games)
        # 2024 > 2023 > 2020 > "" (empty goes last)
        years = [g.release_year for g in result]
        assert years[0] == "2024"
        assert years[-1] == ""

    def test_sort_empty_list(self, service: FilterService) -> None:
        result = service.sort_games([])
        assert result == []

    def test_sort_single_game(self, service: FilterService) -> None:
        game = _make_game("1", "OnlyGame")
        result = service.sort_games([game])
        assert len(result) == 1
        assert result[0].name == "OnlyGame"
