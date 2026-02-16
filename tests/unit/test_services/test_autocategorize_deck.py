# tests/unit/test_services/test_autocategorize_deck.py

"""Tests for AutoCategorizeService.categorize_by_deck_status."""

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
    steam_deck_status: str = "",
) -> Game:
    """Helper to create a Game with sensible defaults."""
    return Game(
        app_id=app_id,
        name=name,
        steam_deck_status=steam_deck_status,
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


class TestCategorizeDeckStatus:
    """Tests for categorize_by_deck_status method."""

    @patch("src.services.autocategorize_service.t", side_effect=lambda key, **kw: key)
    def test_categorize_deck_verified_game(self, mock_t: MagicMock, service: AutoCategorizeService) -> None:
        """Verified games get a deck category."""
        game = _make_game("1", "Verified Game", steam_deck_status="verified")
        result = service.categorize_by_deck_status([game])
        assert result == 1
        service.category_service.add_app_to_category.assert_called_once()

    @patch("src.services.autocategorize_service.t", side_effect=lambda key, **kw: key)
    def test_categorize_deck_playable_game(self, mock_t: MagicMock, service: AutoCategorizeService) -> None:
        """Playable games get a deck category."""
        game = _make_game("1", "Playable Game", steam_deck_status="playable")
        result = service.categorize_by_deck_status([game])
        assert result == 1

    @patch("src.services.autocategorize_service.t", side_effect=lambda key, **kw: key)
    def test_categorize_deck_unsupported_game(self, mock_t: MagicMock, service: AutoCategorizeService) -> None:
        """Unsupported games get a deck category."""
        game = _make_game("1", "Unsupported Game", steam_deck_status="unsupported")
        result = service.categorize_by_deck_status([game])
        assert result == 1

    @patch("src.services.autocategorize_service.t", side_effect=lambda key, **kw: key)
    def test_categorize_deck_unknown_skipped(self, mock_t: MagicMock, service: AutoCategorizeService) -> None:
        """Games with 'unknown' deck status are skipped."""
        game = _make_game("1", "Unknown Game", steam_deck_status="unknown")
        result = service.categorize_by_deck_status([game])
        assert result == 0
        service.category_service.add_app_to_category.assert_not_called()

    @patch("src.services.autocategorize_service.t", side_effect=lambda key, **kw: key)
    def test_categorize_deck_empty_status_skipped(self, mock_t: MagicMock, service: AutoCategorizeService) -> None:
        """Games with empty deck status are skipped."""
        game = _make_game("1", "No Status", steam_deck_status="")
        result = service.categorize_by_deck_status([game])
        assert result == 0
        service.category_service.add_app_to_category.assert_not_called()

    @patch("src.services.autocategorize_service.t", side_effect=lambda key, **kw: key)
    def test_categorize_deck_progress_callback(self, mock_t: MagicMock, service: AutoCategorizeService) -> None:
        """Progress callback is called for each game."""
        games = [
            _make_game("1", "Game A", steam_deck_status="verified"),
            _make_game("2", "Game B", steam_deck_status="playable"),
        ]
        callback = MagicMock()
        service.categorize_by_deck_status(games, progress_callback=callback)
        assert callback.call_count == 2
        callback.assert_any_call(0, "Game A")
        callback.assert_any_call(1, "Game B")

    @patch("src.services.autocategorize_service.t", side_effect=lambda key, **kw: key)
    def test_categorize_deck_empty_list(self, mock_t: MagicMock, service: AutoCategorizeService) -> None:
        """Empty game list returns 0."""
        result = service.categorize_by_deck_status([])
        assert result == 0

    @patch("src.services.autocategorize_service.t", side_effect=lambda key, **kw: key)
    def test_categorize_deck_mixed_statuses(self, mock_t: MagicMock, service: AutoCategorizeService) -> None:
        """Mixed list: only verified/playable/unsupported get categories."""
        games = [
            _make_game("1", "Verified", steam_deck_status="verified"),
            _make_game("2", "Unknown", steam_deck_status="unknown"),
            _make_game("3", "Playable", steam_deck_status="playable"),
            _make_game("4", "Empty", steam_deck_status=""),
            _make_game("5", "Unsupported", steam_deck_status="unsupported"),
        ]
        result = service.categorize_by_deck_status(games)
        assert result == 3
        assert service.category_service.add_app_to_category.call_count == 3
