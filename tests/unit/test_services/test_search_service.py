# tests/unit/test_services/test_search_service.py

"""Tests for SearchService including regex support."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from src.services.search_service import SearchService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_games() -> list[Mock]:
    """Returns mock games for search testing."""
    g1 = Mock()
    g1.name = "Half-Life"
    g2 = Mock()
    g2.name = "Portal 2"
    g3 = Mock()
    g3.name = "Cyberpunk 2077"
    g4 = Mock()
    g4.name = "Half-Life 2"
    return [g1, g2, g3, g4]


# ---------------------------------------------------------------------------
# Plain text search
# ---------------------------------------------------------------------------


class TestPlainTextSearch:
    """Tests for case-insensitive substring search."""

    def test_search_simple_match(self, sample_games: list[Mock]) -> None:
        results = SearchService.filter_games(sample_games, "Portal")
        assert len(results) == 1
        assert results[0].name == "Portal 2"

    def test_search_case_insensitive(self, sample_games: list[Mock]) -> None:
        results = SearchService.filter_games(sample_games, "half")
        assert len(results) == 2

    def test_search_no_match(self, sample_games: list[Mock]) -> None:
        results = SearchService.filter_games(sample_games, "Fortnite")
        assert len(results) == 0

    def test_search_empty_query_returns_all(self, sample_games: list[Mock]) -> None:
        results = SearchService.filter_games(sample_games, "")
        assert len(results) == 4


# ---------------------------------------------------------------------------
# Regex search
# ---------------------------------------------------------------------------


class TestRegexSearch:
    """Tests for regex search (query prefixed with /)."""

    def test_regex_match(self, sample_games: list[Mock]) -> None:
        results = SearchService.filter_games(sample_games, "/^Half")
        assert len(results) == 2
        names = {g.name for g in results}
        assert "Half-Life" in names
        assert "Half-Life 2" in names

    def test_regex_exact_name(self, sample_games: list[Mock]) -> None:
        results = SearchService.filter_games(sample_games, "/^Portal 2$")
        assert len(results) == 1
        assert results[0].name == "Portal 2"

    def test_regex_digit_pattern(self, sample_games: list[Mock]) -> None:
        results = SearchService.filter_games(sample_games, "/\\d{4}")
        assert len(results) == 1
        assert results[0].name == "Cyberpunk 2077"

    def test_regex_invalid_pattern_returns_empty(self, sample_games: list[Mock]) -> None:
        results = SearchService.filter_games(sample_games, "/[invalid")
        assert len(results) == 0

    def test_regex_case_insensitive(self, sample_games: list[Mock]) -> None:
        results = SearchService.filter_games(sample_games, "/portal")
        assert len(results) == 1

    def test_slash_only_not_regex(self, sample_games: list[Mock]) -> None:
        """A lone / should be treated as plain text search."""
        results = SearchService.filter_games(sample_games, "/")
        assert len(results) == 0  # no game name contains "/"


# ---------------------------------------------------------------------------
# validate_regex
# ---------------------------------------------------------------------------


class TestValidateRegex:
    """Tests for SearchService.validate_regex()."""

    def test_valid_pattern(self) -> None:
        assert SearchService.validate_regex(r"^Half.*\d+$") is True

    def test_invalid_pattern(self) -> None:
        assert SearchService.validate_regex("[invalid") is False

    def test_empty_pattern(self) -> None:
        assert SearchService.validate_regex("") is True
