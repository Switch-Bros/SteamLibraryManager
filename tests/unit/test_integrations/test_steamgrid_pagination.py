"""Tests for SteamGridDB pagination support."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.integrations.steamgrid_api import SteamGridDB


class TestGetImagesByTypePaged:
    """Tests for SteamGridDB.get_images_by_type_paged()."""

    @patch.object(SteamGridDB, "_get_game_id", return_value=12345)
    @patch("src.integrations.steamgrid_api.requests.get")
    def test_returns_single_page(self, mock_get: MagicMock, mock_game_id: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "data": [{"id": i, "url": f"https://example.com/{i}.png"} for i in range(10)],
        }
        mock_get.return_value = mock_response

        api = SteamGridDB()
        api.api_key = "test-key"
        result = api.get_images_by_type_paged(730, "grids", page=0, limit=24)

        assert len(result) == 10
        assert result[0]["id"] == 0

    @patch.object(SteamGridDB, "_get_game_id", return_value=12345)
    @patch("src.integrations.steamgrid_api.requests.get")
    def test_empty_result(self, mock_get: MagicMock, mock_game_id: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "data": []}
        mock_get.return_value = mock_response

        api = SteamGridDB()
        api.api_key = "test-key"
        result = api.get_images_by_type_paged(730, "grids", page=5)

        assert result == []

    @patch.object(SteamGridDB, "_get_game_id", return_value=12345)
    @patch("src.integrations.steamgrid_api.requests.get")
    def test_api_error_returns_empty(self, mock_get: MagicMock, mock_game_id: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        api = SteamGridDB()
        api.api_key = "test-key"
        result = api.get_images_by_type_paged(730, "heroes")

        assert result == []

    @patch.object(SteamGridDB, "_get_game_id", return_value=None)
    def test_game_not_found_returns_empty(self, mock_game_id: MagicMock) -> None:
        api = SteamGridDB()
        api.api_key = "test-key"
        result = api.get_images_by_type_paged(99999, "grids")

        assert result == []

    def test_no_api_key_returns_empty(self) -> None:
        api = SteamGridDB()
        api.api_key = ""
        result = api.get_images_by_type_paged(730, "grids")

        assert result == []

    @patch.object(SteamGridDB, "_get_game_id", return_value=12345)
    @patch("src.integrations.steamgrid_api.requests.get")
    def test_page_parameter_passed(self, mock_get: MagicMock, mock_game_id: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "data": []}
        mock_get.return_value = mock_response

        api = SteamGridDB()
        api.api_key = "test-key"
        api.get_images_by_type_paged(730, "grids", page=3, limit=24)

        call_kwargs = mock_get.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
        assert params["page"] == 3
        assert params["limit"] == 24

    @patch.object(SteamGridDB, "_get_game_id", return_value=12345)
    @patch("src.integrations.steamgrid_api.requests.get")
    def test_grids_include_dimensions(self, mock_get: MagicMock, mock_game_id: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "data": []}
        mock_get.return_value = mock_response

        api = SteamGridDB()
        api.api_key = "test-key"
        api.get_images_by_type_paged(730, "grids", page=0)

        call_kwargs = mock_get.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
        assert "dimensions" in params

    @patch.object(SteamGridDB, "_get_game_id", return_value=12345)
    @patch("src.integrations.steamgrid_api.requests.get")
    def test_detect_last_page(self, mock_get: MagicMock, mock_game_id: MagicMock) -> None:
        """If results < limit, this is the last page."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "data": [{"id": i} for i in range(15)],
        }
        mock_get.return_value = mock_response

        api = SteamGridDB()
        api.api_key = "test-key"
        result = api.get_images_by_type_paged(730, "grids", page=0, limit=24)

        # 15 < 24, so caller should know this is the last page
        assert len(result) < 24
