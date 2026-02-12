import pytest
from unittest.mock import Mock
from src.services.search_service import SearchService


@pytest.fixture
def sample_games():
    g1 = Mock()
    g1.name = "Half-Life"
    g2 = Mock()
    g2.name = "Portal 2"
    g3 = Mock()
    g3.name = "Cyberpunk 2077"
    return [g1, g2, g3]


def test_search_simple_match(sample_games):
    service = SearchService()
    results = service.filter_games(sample_games, "Portal")

    assert len(results) == 1
    assert results[0].name == "Portal 2"


def test_search_case_insensitive(sample_games):
    service = SearchService()
    results = service.filter_games(sample_games, "half")

    assert len(results) == 1
    assert results[0].name == "Half-Life"


def test_search_no_match(sample_games):
    service = SearchService()
    results = service.filter_games(sample_games, "Fortnite")

    assert len(results) == 0


def test_search_empty_query(sample_games):
    service = SearchService()
    results = service.filter_games(sample_games, "")

    # Should return original list
    assert len(results) == 3
