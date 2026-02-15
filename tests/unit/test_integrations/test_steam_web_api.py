"""Tests for the Steam Web API client."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from src.integrations.steam_web_api import SteamAppDetails, SteamWebAPI


class TestSteamAppDetails:
    """Tests for the SteamAppDetails frozen dataclass."""

    def test_dataclass_frozen(self) -> None:
        """Frozen dataclass raises AttributeError on mutation."""
        details = SteamAppDetails(app_id=440, name="TF2")
        with pytest.raises(AttributeError):
            details.name = "Changed"  # type: ignore[misc]

    def test_defaults(self) -> None:
        """Default values are correct for optional fields."""
        details = SteamAppDetails(app_id=1, name="Test")
        assert details.developers == ()
        assert details.publishers == ()
        assert details.release_date == ""
        assert details.genres == ()
        assert details.tags == ()
        assert details.platforms == ()
        assert details.languages == ()
        assert details.review_score == 0
        assert details.review_desc == ""
        assert details.is_free is False


class TestSteamWebAPIInit:
    """Tests for SteamWebAPI initialization."""

    def test_empty_api_key_raises_value_error(self) -> None:
        """Empty API key raises ValueError."""
        with pytest.raises(ValueError, match="must not be empty"):
            SteamWebAPI("")

    def test_whitespace_api_key_raises_value_error(self) -> None:
        """Whitespace-only API key raises ValueError."""
        with pytest.raises(ValueError, match="must not be empty"):
            SteamWebAPI("   ")

    def test_valid_api_key_accepted(self) -> None:
        """Valid API key is accepted and stripped."""
        api = SteamWebAPI("  my_key  ")
        assert api.api_key == "my_key"


class TestBatchChunking:
    """Tests for batch chunking logic."""

    @patch("src.integrations.steam_web_api.time.sleep")
    @patch("src.integrations.steam_web_api.requests.get")
    def test_batch_chunking_101_apps_splits_into_3(self, mock_get: MagicMock, mock_sleep: MagicMock) -> None:
        """101 app IDs are split into 3 batches (50+50+1)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": {"store_items": []}}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        api = SteamWebAPI("test_key")
        api.get_app_details_batch(list(range(101)))

        assert mock_get.call_count == 3
        # 2 sleeps between 3 batches
        assert mock_sleep.call_count == 2

    @patch("src.integrations.steam_web_api.requests.get")
    def test_empty_response_returns_empty_dict(self, mock_get: MagicMock) -> None:
        """Empty API response returns empty dict."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": {"store_items": []}}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        api = SteamWebAPI("test_key")
        result = api.get_app_details_batch([440])
        assert result == {}

    def test_empty_input_returns_empty_dict(self) -> None:
        """Empty input list returns empty dict without API calls."""
        api = SteamWebAPI("test_key")
        result = api.get_app_details_batch([])
        assert result == {}


class TestParseItem:
    """Tests for _parse_item."""

    def test_parse_item_full_data_returns_complete_dataclass(self) -> None:
        """Full API item is parsed into complete SteamAppDetails."""
        raw = {
            "id": 440,
            "name": "Team Fortress 2",
            "basic_info": {
                "developers": [{"name": "Valve"}],
                "publishers": [{"name": "Valve"}],
                "is_free": True,
                "release_date": {"date": "Oct 10, 2007"},
                "genres": [{"description": "Action"}, {"description": "Free to Play"}],
                "supported_languages": "English, German, French",
            },
            "tags": [{"name": "FPS"}, {"name": "Multiplayer"}],
            "platforms": {"windows": True, "mac": True, "linux": True},
            "reviews": {
                "summary_filtered": {
                    "review_score": 9,
                    "review_score_label": "Very Positive",
                }
            },
        }

        result = SteamWebAPI._parse_item(raw)

        assert result.app_id == 440
        assert result.name == "Team Fortress 2"
        assert result.developers == ("Valve",)
        assert result.publishers == ("Valve",)
        assert result.is_free is True
        assert result.release_date == "Oct 10, 2007"
        assert result.genres == ("Action", "Free to Play")
        assert result.tags == ("FPS", "Multiplayer")
        assert "linux" in result.platforms
        assert "windows" in result.platforms
        assert result.languages == ("English", "German", "French")
        assert result.review_score == 9
        assert result.review_desc == "Very Positive"

    def test_parse_item_missing_fields_uses_defaults(self) -> None:
        """Missing fields in API item fall back to defaults."""
        raw = {"id": 999, "name": "Minimal Game"}

        result = SteamWebAPI._parse_item(raw)

        assert result.app_id == 999
        assert result.name == "Minimal Game"
        assert result.developers == ()
        assert result.genres == ()
        assert result.tags == ()
        assert result.platforms == ()
        assert result.review_score == 0
        assert result.is_free is False


class TestRateLimitAndErrors:
    """Tests for rate limiting and error handling."""

    @patch("src.integrations.steam_web_api.time.sleep")
    @patch("src.integrations.steam_web_api.requests.get")
    def test_rate_limit_retries_with_backoff(self, mock_get: MagicMock, mock_sleep: MagicMock) -> None:
        """HTTP 429 triggers exponential backoff retries."""
        rate_limited = MagicMock()
        rate_limited.status_code = 429

        ok_response = MagicMock()
        ok_response.status_code = 200
        ok_response.json.return_value = {"response": {"store_items": []}}
        ok_response.raise_for_status = MagicMock()

        mock_get.side_effect = [rate_limited, ok_response]

        api = SteamWebAPI("test_key")
        result = api._fetch_batch([440])

        assert result == []
        assert mock_sleep.call_count >= 1

    @patch("src.integrations.steam_web_api.requests.get")
    def test_network_error_raises_connection_error(self, mock_get: MagicMock) -> None:
        """Network failure raises ConnectionError."""
        mock_get.side_effect = requests.ConnectionError("Network down")

        api = SteamWebAPI("test_key")
        with pytest.raises(requests.ConnectionError):
            api.get_app_details_batch([440])
