# tests/unit/test_services/test_game_detail_service.py

"""Tests for GameDetailService."""

from unittest.mock import patch

from src.core.game import Game
from src.services.game_detail_service import GameDetailService


class TestGameDetailServiceInit:
    """Tests for GameDetailService initialization."""

    def test_init_stores_references(self, tmp_path):
        """Test that init stores games dict and cache dir."""
        games = {"440": Game(app_id="440", name="TF2")}
        service = GameDetailService(games, tmp_path)
        assert service._games is games
        assert service._cache_dir == tmp_path

    def test_shared_games_reference(self, tmp_path):
        """Test that service shares the same games dict (not a copy)."""
        games: dict[str, Game] = {}
        service = GameDetailService(games, tmp_path)
        games["440"] = Game(app_id="440", name="TF2")
        assert "440" in service._games


class TestFetchGameDetails:
    """Tests for fetch_game_details orchestrator."""

    def test_returns_false_for_missing_game(self, tmp_path):
        """Test that fetching details for unknown app_id returns False."""
        games: dict[str, Game] = {}
        service = GameDetailService(games, tmp_path)
        assert service.fetch_game_details("999") is False

    @patch("src.services.game_detail_service.requests.get")
    def test_returns_true_for_existing_game(self, mock_get, tmp_path):
        """Test that fetching details for known app_id returns True."""
        import requests as req_mod

        mock_get.side_effect = req_mod.RequestException("No network in tests")
        games = {"440": Game(app_id="440", name="TF2")}
        service = GameDetailService(games, tmp_path)
        # Returns True because the game exists; individual fetches swallow exceptions
        assert service.fetch_game_details("440") is True


class TestApplyStoreData:
    """Tests for _apply_store_data."""

    def test_applies_developer_and_publisher(self, tmp_path):
        """Test that store data is correctly applied to a game."""
        game = Game(app_id="440", name="TF2")
        games = {"440": game}
        service = GameDetailService(games, tmp_path)

        store_data = {
            "developers": ["Valve"],
            "publishers": ["Valve"],
            "release_date": {"date": "Oct 10, 2007"},
            "genres": [{"description": "Action"}, {"description": "Free to Play"}],
            "categories": [{"description": "Multi-player"}],
        }
        service._apply_store_data("440", store_data)

        assert game.developer == "Valve"
        assert game.publisher == "Valve"
        assert game.release_year == "Oct 10, 2007"
        assert "Action" in game.genres
        assert "Multi-player" in game.tags

    def test_skips_developer_when_name_overridden(self, tmp_path):
        """Test that developer is not overwritten when name is overridden."""
        game = Game(app_id="440", name="TF2", developer="Custom Dev")
        game.name_overridden = True
        games = {"440": game}
        service = GameDetailService(games, tmp_path)

        store_data = {"developers": ["Valve"], "publishers": ["Valve"]}
        service._apply_store_data("440", store_data)

        assert game.developer == "Custom Dev"

    def test_applies_pegi_rating(self, tmp_path):
        """Test PEGI rating extraction from store data."""
        game = Game(app_id="440", name="TF2")
        games = {"440": game}
        service = GameDetailService(games, tmp_path)

        store_data = {"ratings": {"pegi": {"rating": "16"}}}
        service._apply_store_data("440", store_data)

        assert game.pegi_rating == "16"


class TestApplyReviewData:
    """Tests for _apply_review_data."""

    def test_applies_review_count(self, tmp_path):
        """Test that review data is correctly applied."""
        game = Game(app_id="440", name="TF2")
        games = {"440": game}
        service = GameDetailService(games, tmp_path)

        review_data = {
            "query_summary": {
                "review_score_desc": "Very Positive",
                "total_reviews": 500000,
            }
        }
        service._apply_review_data("440", review_data)

        assert game.review_count == 500000

    def test_skips_missing_game(self, tmp_path):
        """Test that review data for missing game is silently skipped."""
        games: dict[str, Game] = {}
        service = GameDetailService(games, tmp_path)
        # Should not raise
        service._apply_review_data("999", {"query_summary": {}})
