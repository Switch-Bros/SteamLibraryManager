# tests/unit/test_services/test_filter_deck.py

"""Tests for the Steam Deck compatibility filter in FilterService."""

from __future__ import annotations

import pytest

from src.core.game import Game
from src.services.filter_service import (
    ALL_DECK_KEYS,
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
    steam_deck_status: str = "",
) -> Game:
    """Helper to create a Game with sensible defaults."""
    return Game(
        app_id=app_id,
        name=name,
        app_type=app_type,
        steam_deck_status=steam_deck_status,
    )


@pytest.fixture
def service() -> FilterService:
    """Returns a fresh FilterService instance."""
    return FilterService()


@pytest.fixture
def deck_games() -> list[Game]:
    """Returns a set of games with various deck statuses."""
    return [
        _make_game("1", "Verified Game", steam_deck_status="verified"),
        _make_game("2", "Playable Game", steam_deck_status="playable"),
        _make_game("3", "Unsupported Game", steam_deck_status="unsupported"),
        _make_game("4", "Unknown Game", steam_deck_status="unknown"),
        _make_game("5", "No Status Game", steam_deck_status=""),
    ]


# ---------------------------------------------------------------------------
# Toggle method
# ---------------------------------------------------------------------------


class TestToggleDeckStatus:
    """Tests for toggle_deck_status method."""

    def test_toggle_deck_status_adds_key(self, service: FilterService) -> None:
        """Toggling a deck status on adds it to active set."""
        service.toggle_deck_status("verified", True)
        assert "verified" in service.state.active_deck_statuses

    def test_toggle_deck_status_removes_key(self, service: FilterService) -> None:
        """Toggling a deck status off removes it from active set."""
        service.toggle_deck_status("verified", True)
        service.toggle_deck_status("verified", False)
        assert "verified" not in service.state.active_deck_statuses

    def test_toggle_unknown_deck_key_ignored(self, service: FilterService) -> None:
        """Unknown deck status keys are silently ignored."""
        service.toggle_deck_status("bogus", True)
        assert service.state.active_deck_statuses == frozenset()


# ---------------------------------------------------------------------------
# Filter logic
# ---------------------------------------------------------------------------


class TestPassesDeckFilter:
    """Tests for _passes_deck_filter via apply()."""

    def test_no_active_returns_all(self, service: FilterService, deck_games: list[Game]) -> None:
        """When no deck filter is active, all games pass."""
        result = service.apply(deck_games)
        assert len(result) == len(deck_games)

    def test_verified_only(self, service: FilterService, deck_games: list[Game]) -> None:
        """Only verified games pass when 'verified' filter is active."""
        service.toggle_deck_status("verified", True)
        result = service.apply(deck_games)
        assert len(result) == 1
        assert result[0].steam_deck_status == "verified"

    def test_or_logic_verified_and_playable(self, service: FilterService, deck_games: list[Game]) -> None:
        """OR logic: verified OR playable games pass."""
        service.toggle_deck_status("verified", True)
        service.toggle_deck_status("playable", True)
        result = service.apply(deck_games)
        assert len(result) == 2
        statuses = {g.steam_deck_status for g in result}
        assert statuses == {"verified", "playable"}

    def test_unknown_filter_includes_empty_status(self, service: FilterService, deck_games: list[Game]) -> None:
        """Games with empty deck status are treated as 'unknown'."""
        service.toggle_deck_status("unknown", True)
        result = service.apply(deck_games)
        # Should include both "unknown" and "" (empty → treated as unknown)
        assert len(result) == 2
        ids = {g.app_id for g in result}
        assert "4" in ids  # steam_deck_status="unknown"
        assert "5" in ids  # steam_deck_status=""

    def test_all_statuses_active_returns_all(self, service: FilterService, deck_games: list[Game]) -> None:
        """All deck statuses active returns all games."""
        for key in ALL_DECK_KEYS:
            service.toggle_deck_status(key, True)
        result = service.apply(deck_games)
        assert len(result) == len(deck_games)


# ---------------------------------------------------------------------------
# Integration with apply() and has_active_filters()
# ---------------------------------------------------------------------------


class TestDeckFilterIntegration:
    """Tests for deck filter in has_active_filters and state restore."""

    def test_has_active_filters_deck(self, service: FilterService) -> None:
        """Active deck filter makes has_active_filters() return True."""
        assert not service.has_active_filters()
        service.toggle_deck_status("verified", True)
        assert service.has_active_filters()

    def test_deck_filter_state_restore(self, service: FilterService) -> None:
        """Deck filter state is preserved through save/restore cycle."""
        service.toggle_deck_status("verified", True)
        service.toggle_deck_status("playable", True)
        state = service.state

        new_service = FilterService()
        new_service.restore_state(state)
        assert new_service.state.active_deck_statuses == frozenset({"verified", "playable"})

    def test_filter_state_default_deck_empty(self) -> None:
        """Default FilterState has empty active_deck_statuses."""
        state = FilterState()
        assert state.active_deck_statuses == frozenset()
