"""Tests for the HLTB API client."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.integrations.hltb_api import HLTBClient, HLTBResult


class TestHLTBResult:
    """Tests for the HLTBResult frozen dataclass."""

    def test_result_dataclass_frozen(self) -> None:
        """Frozen dataclass raises AttributeError on mutation."""
        result = HLTBResult(game_name="Test", main_story=10.0, main_extras=15.0, completionist=20.0)
        with pytest.raises(AttributeError):
            result.game_name = "Changed"  # type: ignore[misc]

    def test_result_values(self) -> None:
        """HLTBResult stores all values correctly."""
        result = HLTBResult(game_name="Portal 2", main_story=8.5, main_extras=13.0, completionist=22.0)
        assert result.game_name == "Portal 2"
        assert result.main_story == 8.5
        assert result.main_extras == 13.0
        assert result.completionist == 22.0


class TestNormalizeName:
    """Tests for the _normalize_name static method."""

    def test_normalize_name_strips_trademark(self) -> None:
        """Trademark and registered symbols are removed."""
        assert HLTBClient._normalize_name("Fallout\u2122") == "Fallout"
        assert HLTBClient._normalize_name("Skyrim\u00ae") == "Skyrim"

    def test_normalize_name_strips_edition_suffix(self) -> None:
        """Edition suffixes are stripped from names."""
        assert HLTBClient._normalize_name("Game - Deluxe Edition") == "Game"
        assert HLTBClient._normalize_name("Game - GOTY Edition Pack") == "Game"
        assert HLTBClient._normalize_name("Game - Remastered Edition") == "Game"

    def test_normalize_name_preserves_numbers(self) -> None:
        """Numbers in game names are preserved."""
        assert HLTBClient._normalize_name("Half-Life 2") == "Half-Life 2"
        assert HLTBClient._normalize_name("Portal 2") == "Portal 2"

    def test_normalize_name_empty_input(self) -> None:
        """Empty string returns empty string."""
        assert HLTBClient._normalize_name("") == ""


class TestSearchGame:
    """Tests for HLTBClient.search_game."""

    def test_search_game_found_returns_result(self) -> None:
        """Found game returns HLTBResult with completion times."""
        mock_result = MagicMock()
        mock_result.game_name = "Portal 2"
        mock_result.main_story = 8.5
        mock_result.main_extra = 13.0
        mock_result.completionist = 22.0
        mock_result.similarity = 0.95

        mock_hltb_class = MagicMock()
        mock_hltb_class.return_value.search.return_value = [mock_result]

        with patch.dict("sys.modules", {"howlongtobeatpy": MagicMock(HowLongToBeat=mock_hltb_class)}):
            client = HLTBClient()
            result = client.search_game("Portal 2")

        assert result is not None
        assert result.game_name == "Portal 2"
        assert result.main_story == 8.5

    def test_search_game_not_found_returns_none(self) -> None:
        """No results from HLTB returns None."""
        mock_hltb_class = MagicMock()
        mock_hltb_class.return_value.search.return_value = []

        with patch.dict("sys.modules", {"howlongtobeatpy": MagicMock(HowLongToBeat=mock_hltb_class)}):
            client = HLTBClient()
            result = client.search_game("NonexistentGame12345")

        assert result is None
