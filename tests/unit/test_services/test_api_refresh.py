"""Tests for GameService API refresh — new game discovery at startup."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from src.core.game import Game
from src.services.game_service import GameService


class TestApiRefresh:
    """Tests for GameService._refresh_from_api()."""

    def _make_service(self, tmp_path: Path) -> GameService:
        """Creates a GameService with a mock GameManager."""
        svc = GameService(
            steam_path=str(tmp_path / "steam"),
            api_key="test-key",
            cache_dir=str(tmp_path / "cache"),
        )
        svc.game_manager = MagicMock()
        svc.game_manager.games = {}
        return svc

    @patch("src.services.game_service.requests.get")
    def test_discovers_new_games(self, mock_get: MagicMock, tmp_path: Path) -> None:
        """API refresh adds games not already in game_manager.games."""
        svc = self._make_service(tmp_path)
        # Pre-populate with one existing game
        svc.game_manager.games["440"] = Game(app_id="440", name="TF2")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": {
                "games": [
                    {"appid": 440, "name": "TF2", "playtime_forever": 100},
                    {"appid": 730, "name": "CS2", "playtime_forever": 50},
                ],
            },
        }
        mock_get.return_value = mock_response

        new_ids = svc._refresh_from_api("76561198000000000")

        assert new_ids == ["730"]
        assert "730" in svc.game_manager.games
        assert svc.game_manager.games["730"].name == "CS2"
        assert svc.game_manager.games["730"].playtime_minutes == 50

    @patch("src.services.game_service.requests.get")
    def test_no_duplicates(self, mock_get: MagicMock, tmp_path: Path) -> None:
        """API refresh does not duplicate existing games."""
        svc = self._make_service(tmp_path)
        svc.game_manager.games["440"] = Game(app_id="440", name="TF2")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": {
                "games": [
                    {"appid": 440, "name": "TF2", "playtime_forever": 100},
                ],
            },
        }
        mock_get.return_value = mock_response

        new_ids = svc._refresh_from_api("76561198000000000")

        assert new_ids == []
        assert len(svc.game_manager.games) == 1

    @patch("src.services.game_service.requests.get")
    def test_failure_is_nonfatal(self, mock_get: MagicMock, tmp_path: Path) -> None:
        """API failure returns empty list, does not crash."""
        import requests

        svc = self._make_service(tmp_path)
        mock_get.side_effect = requests.ConnectionError("No internet")

        new_ids = svc._refresh_from_api("76561198000000000")

        assert new_ids == []
        assert len(svc.game_manager.games) == 0
