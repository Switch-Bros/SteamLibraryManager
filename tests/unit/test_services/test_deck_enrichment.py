# tests/unit/test_services/test_deck_enrichment.py

"""Tests for DeckEnrichmentThread."""

from __future__ import annotations

from unittest.mock import patch, MagicMock

from src.core.game import Game
from src.services.enrichment.deck_enrichment_service import (
    DeckEnrichmentThread,
    _DECK_STATUS_MAP,
)

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


# ---------------------------------------------------------------------------
# Configuration Tests
# ---------------------------------------------------------------------------


class TestDeckEnrichmentConfig:
    """Tests for DeckEnrichmentThread configuration."""

    def test_configure_stores_games(self, tmp_path: object) -> None:
        """Configure should store the games list."""
        thread = DeckEnrichmentThread()
        games = [_make_game("1", "Game A"), _make_game("2", "Game B")]
        thread.configure(games, tmp_path)
        assert thread._games is games

    def test_configure_stores_cache_dir(self, tmp_path: object) -> None:
        """Configure should store the cache directory."""
        thread = DeckEnrichmentThread()
        thread.configure([], tmp_path)
        assert thread._cache_dir == tmp_path

    def test_cancel_sets_flag(self) -> None:
        """Cancel should set the internal cancelled flag."""
        thread = DeckEnrichmentThread()
        assert not thread._cancelled
        thread.cancel()
        assert thread._cancelled


# ---------------------------------------------------------------------------
# Static fetch method tests
# ---------------------------------------------------------------------------


class TestFetchDeckStatus:
    """Tests for the static _fetch_deck_status method."""

    @patch("src.services.enrichment.deck_enrichment_service.requests.get")
    def test_fetch_verified_status(self, mock_get: MagicMock, tmp_path: object) -> None:
        """API returning resolved_category=3 should map to 'verified'."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": {"resolved_category": 3}}
        mock_get.return_value = mock_response

        store_dir = tmp_path / "store_data"
        store_dir.mkdir()

        result = DeckEnrichmentThread._fetch_deck_status("440", store_dir)
        assert result == "verified"

    @patch("src.services.enrichment.deck_enrichment_service.requests.get")
    def test_fetch_playable_status(self, mock_get: MagicMock, tmp_path: object) -> None:
        """API returning resolved_category=2 should map to 'playable'."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": {"resolved_category": 2}}
        mock_get.return_value = mock_response

        store_dir = tmp_path / "store_data"
        store_dir.mkdir()

        result = DeckEnrichmentThread._fetch_deck_status("440", store_dir)
        assert result == "playable"

    @patch("src.services.enrichment.deck_enrichment_service.requests.get")
    def test_fetch_unsupported_status(self, mock_get: MagicMock, tmp_path: object) -> None:
        """API returning resolved_category=1 should map to 'unsupported'."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": {"resolved_category": 1}}
        mock_get.return_value = mock_response

        store_dir = tmp_path / "store_data"
        store_dir.mkdir()

        result = DeckEnrichmentThread._fetch_deck_status("440", store_dir)
        assert result == "unsupported"

    @patch("src.services.enrichment.deck_enrichment_service.requests.get")
    def test_fetch_unknown_status(self, mock_get: MagicMock, tmp_path: object) -> None:
        """API returning resolved_category=0 should map to 'unknown'."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": {"resolved_category": 0}}
        mock_get.return_value = mock_response

        store_dir = tmp_path / "store_data"
        store_dir.mkdir()

        result = DeckEnrichmentThread._fetch_deck_status("440", store_dir)
        assert result == "unknown"

    @patch("src.services.enrichment.deck_enrichment_service.requests.get")
    def test_fetch_api_error_returns_none(self, mock_get: MagicMock, tmp_path: object) -> None:
        """Network errors should return None."""
        import requests as req_mod

        mock_get.side_effect = req_mod.RequestException("timeout")

        store_dir = tmp_path / "store_data"
        store_dir.mkdir()

        result = DeckEnrichmentThread._fetch_deck_status("440", store_dir)
        assert result is None

    @patch("src.services.enrichment.deck_enrichment_service.requests.get")
    def test_fetch_non_200_returns_none(self, mock_get: MagicMock, tmp_path: object) -> None:
        """Non-200 HTTP status should return None."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        store_dir = tmp_path / "store_data"
        store_dir.mkdir()

        result = DeckEnrichmentThread._fetch_deck_status("440", store_dir)
        assert result is None

    @patch("src.services.enrichment.deck_enrichment_service.requests.get")
    def test_fetch_creates_cache_file(self, mock_get: MagicMock, tmp_path: object) -> None:
        """Successful fetch should create a cache file."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": {"resolved_category": 3}}
        mock_get.return_value = mock_response

        store_dir = tmp_path / "store_data"
        store_dir.mkdir()

        DeckEnrichmentThread._fetch_deck_status("440", store_dir)

        cache_file = store_dir / "440_deck.json"
        assert cache_file.exists()

    @patch("src.services.enrichment.deck_enrichment_service.requests.get")
    def test_fetch_handles_list_results(self, mock_get: MagicMock, tmp_path: object) -> None:
        """API sometimes returns results as a list — handle gracefully."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [{"resolved_category": 2}]}
        mock_get.return_value = mock_response

        store_dir = tmp_path / "store_data"
        store_dir.mkdir()

        result = DeckEnrichmentThread._fetch_deck_status("440", store_dir)
        assert result == "playable"


# ---------------------------------------------------------------------------
# Status map coverage
# ---------------------------------------------------------------------------


class TestDeckStatusMap:
    """Tests for the deck status mapping constants."""

    def test_all_categories_mapped(self) -> None:
        """All expected Valve categories (0-3) should be in the map."""
        assert 0 in _DECK_STATUS_MAP
        assert 1 in _DECK_STATUS_MAP
        assert 2 in _DECK_STATUS_MAP
        assert 3 in _DECK_STATUS_MAP

    def test_map_values(self) -> None:
        """Map values should match expected status strings."""
        assert _DECK_STATUS_MAP[0] == "unknown"
        assert _DECK_STATUS_MAP[1] == "unsupported"
        assert _DECK_STATUS_MAP[2] == "playable"
        assert _DECK_STATUS_MAP[3] == "verified"
