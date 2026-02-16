"""Unit tests for CuratorClient."""

from unittest.mock import patch, MagicMock

import pytest

from src.services.curator_client import CuratorClient, CuratorRecommendation


class TestCuratorClientURLParsing:
    """Tests for curator URL parsing."""

    def test_parse_curator_id_full_url(self) -> None:
        """Test parsing curator ID from a full Steam URL."""
        url = "https://store.steampowered.com/curator/6856218-BoilingSteam/"
        assert CuratorClient.parse_curator_id(url) == 6856218

    def test_parse_curator_id_without_trailing_slash(self) -> None:
        """Test parsing curator ID from URL without trailing slash."""
        url = "https://store.steampowered.com/curator/6856218-BoilingSteam"
        assert CuratorClient.parse_curator_id(url) == 6856218

    def test_parse_curator_id_numeric_only(self) -> None:
        """Test parsing curator ID from plain numeric string."""
        assert CuratorClient.parse_curator_id("6856218") == 6856218

    def test_parse_curator_id_with_listsort(self) -> None:
        """Test parsing curator ID from URL with additional path segments."""
        url = "https://store.steampowered.com/curator/6856218-BoilingSteam/list/12345"
        assert CuratorClient.parse_curator_id(url) == 6856218

    def test_parse_curator_id_invalid_url_returns_none(self) -> None:
        """Test that invalid URL returns None."""
        assert CuratorClient.parse_curator_id("https://store.steampowered.com/app/440/") is None

    def test_parse_curator_id_empty_string_returns_none(self) -> None:
        """Test that empty string returns None."""
        assert CuratorClient.parse_curator_id("") is None

    def test_parse_curator_id_random_text_returns_none(self) -> None:
        """Test that random text returns None."""
        assert CuratorClient.parse_curator_id("not a url at all") is None


class TestCuratorClientNameParsing:
    """Tests for curator name extraction from URL slugs."""

    def test_parse_curator_name_full_url(self) -> None:
        """Test extracting name from a standard curator URL."""
        url = "https://store.steampowered.com/curator/6856218-BoilingSteam/"
        assert CuratorClient.parse_curator_name(url) == "BoilingSteam"

    def test_parse_curator_name_with_hyphens(self) -> None:
        """Test extracting name from URL slug with hyphens (spaces)."""
        url = "https://store.steampowered.com/curator/33030023-Waifu-Hunter/"
        assert CuratorClient.parse_curator_name(url) == "Waifu Hunter"

    def test_parse_curator_name_without_trailing_slash(self) -> None:
        """Test extracting name from URL without trailing slash."""
        url = "https://store.steampowered.com/curator/4771848-PCGamer"
        assert CuratorClient.parse_curator_name(url) == "PCGamer"

    def test_parse_curator_name_with_extra_path(self) -> None:
        """Test extracting name from URL with additional path segments."""
        url = "https://store.steampowered.com/curator/6856218-BoilingSteam/list/12345"
        assert CuratorClient.parse_curator_name(url) == "BoilingSteam"

    def test_parse_curator_name_numeric_only_returns_none(self) -> None:
        """Test that a plain numeric ID returns None (no name available)."""
        assert CuratorClient.parse_curator_name("6856218") is None

    def test_parse_curator_name_invalid_url_returns_none(self) -> None:
        """Test that an invalid URL returns None."""
        assert CuratorClient.parse_curator_name("not a url") is None

    def test_parse_curator_name_empty_returns_none(self) -> None:
        """Test that empty string returns None."""
        assert CuratorClient.parse_curator_name("") is None


class TestCuratorClientHTMLParsing:
    """Tests for HTML recommendation parsing."""

    def test_parse_recommended(self) -> None:
        """Test parsing a recommended game from HTML."""
        html = """
        <div class="recommendation color_recommended" data-ds-appid="440">
            <span>Recommended</span>
        </div>
        """
        result = CuratorClient.parse_recommendations_html(html)
        assert result == {440: CuratorRecommendation.RECOMMENDED}

    def test_parse_not_recommended(self) -> None:
        """Test parsing a not-recommended game from HTML."""
        html = """
        <div data-ds-appid="730" class="recommendation">
            <div class="color_not_recommended">Not Recommended</div>
        </div>
        """
        result = CuratorClient.parse_recommendations_html(html)
        assert result == {730: CuratorRecommendation.NOT_RECOMMENDED}

    def test_parse_informational(self) -> None:
        """Test parsing an informational game from HTML."""
        html = """
        <div data-ds-appid="570" class="something">
            <span class="color_informational">Info</span>
        </div>
        """
        result = CuratorClient.parse_recommendations_html(html)
        assert result == {570: CuratorRecommendation.INFORMATIONAL}

    def test_parse_multiple_recommendations(self) -> None:
        """Test parsing multiple games from HTML."""
        html = """
        <div data-ds-appid="440" class="rec">
            <span class="color_recommended">Yes</span>
        </div>
        <div data-ds-appid="730" class="rec">
            <span class="color_not_recommended">No</span>
        </div>
        <div data-ds-appid="570" class="rec">
            <span class="color_informational">Info</span>
        </div>
        """
        result = CuratorClient.parse_recommendations_html(html)
        assert len(result) == 3
        assert result[440] == CuratorRecommendation.RECOMMENDED
        assert result[730] == CuratorRecommendation.NOT_RECOMMENDED
        assert result[570] == CuratorRecommendation.INFORMATIONAL

    def test_parse_empty_html_returns_empty(self) -> None:
        """Test that empty HTML returns empty dict."""
        assert CuratorClient.parse_recommendations_html("") == {}

    def test_parse_html_without_appid_returns_empty(self) -> None:
        """Test that HTML without app IDs returns empty dict."""
        html = '<div class="recommendation color_recommended">No app id here</div>'
        assert CuratorClient.parse_recommendations_html(html) == {}

    def test_parse_appid_only_defaults_to_recommended(self) -> None:
        """Test that app ID without color class defaults to RECOMMENDED."""
        html = '<div data-ds-appid="440">Some text without color class</div>'
        result = CuratorClient.parse_recommendations_html(html)
        assert result == {440: CuratorRecommendation.RECOMMENDED}

    def test_parse_duplicate_appid_keeps_first(self) -> None:
        """Test that duplicate app IDs keep the first occurrence."""
        html = """
        <div data-ds-appid="440" class="x">
            <span class="color_recommended">First</span>
        </div>
        <div data-ds-appid="440" class="x">
            <span class="color_not_recommended">Second</span>
        </div>
        """
        result = CuratorClient.parse_recommendations_html(html)
        assert len(result) == 1
        assert result[440] == CuratorRecommendation.RECOMMENDED


class TestCuratorClientFetch:
    """Tests for the fetch_recommendations method."""

    def test_fetch_invalid_url_raises_value_error(self) -> None:
        """Test that invalid URL raises ValueError."""
        client = CuratorClient()
        with pytest.raises(ValueError, match="Invalid curator URL"):
            client.fetch_recommendations("not-a-url")

    @patch("src.services.curator_client.urlopen")
    def test_fetch_single_page(self, mock_urlopen: MagicMock) -> None:
        """Test fetching recommendations with a single page of results."""
        import json

        response_data = {
            "success": 1,
            "total_count": 2,
            "results_html": '<div data-ds-appid="440"><span class="color_recommended">R</span></div>'
            '<div data-ds-appid="730"><span class="color_not_recommended">NR</span></div>',
        }

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(response_data).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        client = CuratorClient()
        result = client.fetch_recommendations("https://store.steampowered.com/curator/6856218-Test/")

        assert len(result) == 2
        assert result[440] == CuratorRecommendation.RECOMMENDED
        assert result[730] == CuratorRecommendation.NOT_RECOMMENDED

    @patch("src.services.curator_client.urlopen")
    def test_fetch_with_progress_callback(self, mock_urlopen: MagicMock) -> None:
        """Test that progress callback is called during fetch."""
        import json

        response_data = {
            "success": 1,
            "total_count": 1,
            "results_html": '<div data-ds-appid="440"><span class="color_recommended">R</span></div>',
        }

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(response_data).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        callback = MagicMock()
        client = CuratorClient()
        client.fetch_recommendations("6856218", progress_callback=callback)

        callback.assert_called_with(1)

    @patch("src.services.curator_client.urlopen")
    def test_fetch_empty_results_stops_pagination(self, mock_urlopen: MagicMock) -> None:
        """Test that empty results stop pagination."""
        import json

        response_data = {
            "success": 1,
            "total_count": 100,
            "results_html": "",
        }

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(response_data).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        client = CuratorClient()
        result = client.fetch_recommendations("6856218")

        assert result == {}

    @patch("src.services.curator_client.urlopen")
    def test_fetch_connection_error_raises(self, mock_urlopen: MagicMock) -> None:
        """Test that connection errors are properly raised."""
        from urllib.error import URLError

        mock_urlopen.side_effect = URLError("Connection refused")

        client = CuratorClient()
        with pytest.raises(ConnectionError, match="Failed to fetch curator data"):
            client.fetch_recommendations("6856218")
