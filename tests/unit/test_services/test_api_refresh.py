"""Tests for GameService API refresh and GameManager API loading with OAuth/API key fallback."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import requests as req_lib

from steam_library_manager.core.game import Game
from steam_library_manager.core.game_manager import GameManager
from steam_library_manager.services.game_service import GameService


class TestApiRefresh:
    """Tests for GameService._api_refresh()."""

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

    @patch("steam_library_manager.services.game_service.requests.get")
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

        new_ids = svc._api_refresh("76561198000000000")

        assert new_ids == ["730"]
        assert "730" in svc.game_manager.games
        assert svc.game_manager.games["730"].name == "CS2"
        assert svc.game_manager.games["730"].playtime_minutes == 50

    @patch("steam_library_manager.services.game_service.requests.get")
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

        new_ids = svc._api_refresh("76561198000000000")

        assert new_ids == []
        assert len(svc.game_manager.games) == 1

    @patch("steam_library_manager.services.game_service.requests.get")
    def test_failure_is_nonfatal(self, mock_get: MagicMock, tmp_path: Path) -> None:
        """API failure returns empty list, does not crash."""
        svc = self._make_service(tmp_path)
        mock_get.side_effect = req_lib.ConnectionError("No internet")

        new_ids = svc._api_refresh("76561198000000000")

        assert new_ids == []
        assert len(svc.game_manager.games) == 0

    @patch("steam_library_manager.services.game_service.requests.get")
    def test_oauth_401_falls_back_to_api_key(self, mock_get: MagicMock, tmp_path: Path) -> None:
        """OAuth 401 should fall back to API key and discover games."""
        svc = self._make_service(tmp_path)

        # first call: oauth 401, second call: api key success
        resp_401 = MagicMock()
        resp_401.status_code = 401
        resp_401.raise_for_status.side_effect = req_lib.HTTPError(response=resp_401)

        resp_ok = MagicMock()
        resp_ok.status_code = 200
        resp_ok.json.return_value = {
            "response": {"games": [{"appid": 730, "name": "CS2", "playtime_forever": 50}]},
        }
        mock_get.side_effect = [resp_401, resp_ok]

        with patch("steam_library_manager.config.config") as mock_cfg:
            mock_cfg.STEAM_ACCESS_TOKEN = "expired_token"
            new_ids = svc._api_refresh("76561198000000000")

        assert new_ids == ["730"]
        assert mock_get.call_count == 2

    @patch("steam_library_manager.services.game_service.requests.get")
    def test_both_fail_returns_empty(self, mock_get: MagicMock, tmp_path: Path) -> None:
        """OAuth 401 + API key 401 should return empty list."""
        svc = self._make_service(tmp_path)

        resp_401 = MagicMock()
        resp_401.status_code = 401
        resp_401.raise_for_status.side_effect = req_lib.HTTPError(response=resp_401)
        mock_get.return_value = resp_401

        with patch("steam_library_manager.config.config") as mock_cfg:
            mock_cfg.STEAM_ACCESS_TOKEN = "expired_token"
            new_ids = svc._api_refresh("76561198000000000")

        assert new_ids == []
        assert mock_get.call_count == 2

    @patch("steam_library_manager.services.game_service.requests.get")
    def test_oauth_empty_falls_back_to_api_key(self, mock_get: MagicMock, tmp_path: Path) -> None:
        """OAuth 200 with empty games should fall back to API key."""
        svc = self._make_service(tmp_path)

        resp_empty = MagicMock()
        resp_empty.status_code = 200
        resp_empty.json.return_value = {"response": {"games": []}}

        resp_ok = MagicMock()
        resp_ok.status_code = 200
        resp_ok.json.return_value = {
            "response": {"games": [{"appid": 440, "name": "TF2", "playtime_forever": 100}]},
        }
        mock_get.side_effect = [resp_empty, resp_ok]

        with patch("steam_library_manager.config.config") as mock_cfg:
            mock_cfg.STEAM_ACCESS_TOKEN = "some_token"
            new_ids = svc._api_refresh("76561198000000000")

        assert new_ids == ["440"]
        assert mock_get.call_count == 2


class TestLoadApiKeyFallback:
    """Tests for GameManager._load_api() OAuth/API key fallback."""

    def _make_manager(self) -> GameManager:
        mgr = GameManager.__new__(GameManager)
        mgr.games = {}
        mgr.api_key = "test-api-key"
        mgr._load_source = None
        return mgr

    @patch("steam_library_manager.core.game_manager.requests.get")
    def test_oauth_401_falls_back_to_api_key(self, mock_get: MagicMock) -> None:
        """OAuth 401 should try API key and load games."""
        mgr = self._make_manager()

        resp_401 = MagicMock()
        resp_401.status_code = 401
        resp_401.raise_for_status.side_effect = req_lib.HTTPError(response=resp_401)

        resp_ok = MagicMock()
        resp_ok.status_code = 200
        resp_ok.json.return_value = {
            "response": {"games": [{"appid": 730, "name": "CS2", "playtime_forever": 50}]},
        }
        mock_get.side_effect = [resp_401, resp_ok]

        with patch("steam_library_manager.config.config") as mock_cfg:
            mock_cfg.STEAM_ACCESS_TOKEN = "expired_token"
            result = mgr._load_api("76561198000000000")

        assert result is True
        assert "730" in mgr.games
        assert mock_get.call_count == 2

    @patch("steam_library_manager.core.game_manager.requests.get")
    def test_oauth_success_no_api_key_attempt(self, mock_get: MagicMock) -> None:
        """Successful OAuth should not try API key."""
        mgr = self._make_manager()

        resp_ok = MagicMock()
        resp_ok.status_code = 200
        resp_ok.json.return_value = {
            "response": {"games": [{"appid": 440, "name": "TF2", "playtime_forever": 100}]},
        }
        mock_get.return_value = resp_ok

        with patch("steam_library_manager.config.config") as mock_cfg:
            mock_cfg.STEAM_ACCESS_TOKEN = "valid_token"
            result = mgr._load_api("76561198000000000")

        assert result is True
        assert mock_get.call_count == 1

    @patch("steam_library_manager.core.game_manager.requests.get")
    def test_both_fail(self, mock_get: MagicMock) -> None:
        """Both OAuth and API key fail should return False."""
        mgr = self._make_manager()

        resp_401 = MagicMock()
        resp_401.status_code = 401
        resp_401.raise_for_status.side_effect = req_lib.HTTPError(response=resp_401)
        mock_get.return_value = resp_401

        with patch("steam_library_manager.config.config") as mock_cfg:
            mock_cfg.STEAM_ACCESS_TOKEN = "expired"
            result = mgr._load_api("76561198000000000")

        assert result is False
        assert mock_get.call_count == 2

    @patch("steam_library_manager.core.game_manager.requests.get")
    def test_no_token_uses_api_key_directly(self, mock_get: MagicMock) -> None:
        """No OAuth token should use API key directly (only 1 request)."""
        mgr = self._make_manager()

        resp_ok = MagicMock()
        resp_ok.status_code = 200
        resp_ok.json.return_value = {
            "response": {"games": [{"appid": 440, "name": "TF2", "playtime_forever": 100}]},
        }
        mock_get.return_value = resp_ok

        with patch("steam_library_manager.config.config") as mock_cfg:
            mock_cfg.STEAM_ACCESS_TOKEN = None
            result = mgr._load_api("76561198000000000")

        assert result is True
        assert mock_get.call_count == 1
        # verify it used the API key, not OAuth
        call_params = mock_get.call_args[1].get("params", mock_get.call_args[0][0] if mock_get.call_args[0] else {})
        if not isinstance(call_params, dict):
            call_params = mock_get.call_args[1].get("params", {})
        assert "key" in call_params

    @patch("steam_library_manager.core.game_manager.requests.get")
    def test_oauth_empty_falls_back_to_api_key(self, mock_get: MagicMock) -> None:
        """OAuth 200 with empty response should fall back to API key."""
        mgr = self._make_manager()

        resp_empty = MagicMock()
        resp_empty.status_code = 200
        resp_empty.json.return_value = {"response": {}}

        resp_ok = MagicMock()
        resp_ok.status_code = 200
        resp_ok.json.return_value = {
            "response": {"games": [{"appid": 730, "name": "CS2", "playtime_forever": 50}]},
        }
        mock_get.side_effect = [resp_empty, resp_ok]

        with patch("steam_library_manager.config.config") as mock_cfg:
            mock_cfg.STEAM_ACCESS_TOKEN = "some_token"
            result = mgr._load_api("76561198000000000")

        assert result is True
        assert "730" in mgr.games
        assert mock_get.call_count == 2


class TestSteamAppDetailsTagIds:
    """Tests for tag_ids field on SteamAppDetails."""

    def test_default_tag_ids_empty(self) -> None:
        from steam_library_manager.integrations.steam_web_api import SteamAppDetails

        det = SteamAppDetails(app_id=1, name="X")
        assert det.tag_ids == ()

    def test_tag_ids_preserved(self) -> None:
        from steam_library_manager.integrations.steam_web_api import SteamAppDetails

        det = SteamAppDetails(app_id=1, name="X", tag_ids=((42, "LEGO"),))
        assert det.tag_ids == ((42, "LEGO"),)
        assert det.tags == ()


class TestEnrichNewGames:
    """Tests for GameService._enrich_new_games()."""

    def _make_service(self, tmp_path: Path) -> GameService:
        svc = GameService(
            steam_path=str(tmp_path / "steam"),
            api_key="test-key",
            cache_dir=str(tmp_path / "cache"),
        )
        svc.game_manager = MagicMock()
        svc.game_manager.games = {}
        svc.database = MagicMock()
        return svc

    def test_enrich_sets_tags_on_game(self, tmp_path: Path) -> None:
        svc = self._make_service(tmp_path)
        game = Game(app_id="730", name="CS2")
        svc.game_manager.games["730"] = game

        mock_det = MagicMock()
        mock_det.tags = ("FPS", "Action")
        mock_det.tag_ids = ((1, "FPS"), (2, "Action"))
        mock_det.genres = ("Action",)
        mock_det.developers = ("Valve",)
        mock_det.publishers = ("Valve",)
        mock_det.platforms = ("windows", "linux")
        mock_det.name = "CS2"

        mock_api = MagicMock()
        mock_api.get_app_details_batch.return_value = {730: mock_det}

        with patch("steam_library_manager.integrations.steam_web_api.SteamWebAPI", return_value=mock_api):
            svc._enrich_new_games(["730"])

        assert game.tags == ["FPS", "Action"]
        assert game.developer == "Valve"

    def test_enrich_persists_tags_to_db(self, tmp_path: Path) -> None:
        svc = self._make_service(tmp_path)
        svc.game_manager.games["730"] = Game(app_id="730", name="CS2")

        mock_det = MagicMock()
        mock_det.tags = ("LEGO",)
        mock_det.tag_ids = ((42, "LEGO"),)
        mock_det.genres = ()
        mock_det.developers = ()
        mock_det.publishers = ()
        mock_det.platforms = ()
        mock_det.name = "CS2"

        mock_api = MagicMock()
        mock_api.get_app_details_batch.return_value = {730: mock_det}

        with patch("steam_library_manager.integrations.steam_web_api.SteamWebAPI", return_value=mock_api):
            svc._enrich_new_games(["730"])

        svc.database.bulk_insert_game_tags_by_id.assert_called_once()
        args = svc.database.bulk_insert_game_tags_by_id.call_args[0][0]
        assert (730, 42, "LEGO") in args

    def test_enrich_failure_nonfatal(self, tmp_path: Path) -> None:
        svc = self._make_service(tmp_path)
        svc.game_manager.games["1"] = Game(app_id="1", name="X")

        with patch(
            "steam_library_manager.integrations.steam_web_api.SteamWebAPI",
            side_effect=Exception("boom"),
        ):
            svc._enrich_new_games(["1"])  # should not raise

    def test_api_refresh_merge_calls_enrich(self, tmp_path: Path) -> None:
        svc = self._make_service(tmp_path)
        svc.cloud_storage_parser = None

        with (
            patch.object(svc, "_api_refresh", return_value=["730"]),
            patch.object(svc, "_save_new"),
            patch.object(svc, "_enrich_new_games") as mock_enrich,
        ):
            svc._api_refresh_merge("uid", None)

        mock_enrich.assert_called_once_with(["730"], None)

    def test_api_refresh_merge_no_new_skips_enrich(self, tmp_path: Path) -> None:
        svc = self._make_service(tmp_path)

        with (
            patch.object(svc, "_api_refresh", return_value=[]),
            patch.object(svc, "_enrich_new_games") as mock_enrich,
        ):
            svc._api_refresh_merge("uid", None)

        mock_enrich.assert_not_called()
