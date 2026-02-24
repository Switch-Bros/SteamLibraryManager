"""Tests for CuratorClient auto-discovery methods (Phase C)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.services.curator_client import CuratorClient


class TestFetchTopCurators:
    """Tests for CuratorClient.fetch_top_curators()."""

    @patch("src.services.curator_client.urlopen")
    def test_parses_html_with_curators(self, mock_urlopen: MagicMock) -> None:
        """Should extract curator_id and name from response HTML."""
        import json

        html = (
            '<div data-clanid="12345" class="curator">'
            '<span class="curator_name">TestCurator</span></div>'
            '<div data-clanid="67890" class="curator">'
            '<span class="curator_name">AnotherCurator</span></div>'
        )
        response_data = json.dumps({"results_html": html}).encode()
        mock_response = MagicMock()
        mock_response.read.return_value = response_data
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = CuratorClient.fetch_top_curators(count=10)
        assert len(result) == 2
        assert result[0]["curator_id"] == 12345
        assert result[0]["name"] == "TestCurator"
        assert result[1]["curator_id"] == 67890

    @patch("src.services.curator_client.urlopen")
    def test_empty_html_returns_empty(self, mock_urlopen: MagicMock) -> None:
        """Should return empty list when no HTML in response."""
        import json

        response_data = json.dumps({"results_html": ""}).encode()
        mock_response = MagicMock()
        mock_response.read.return_value = response_data
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = CuratorClient.fetch_top_curators(count=10)
        assert result == []


class TestDiscoverSubscribedCurators:
    """Tests for CuratorClient.discover_subscribed_curators()."""

    @patch("src.services.curator_client.urlopen")
    def test_parses_followed_ids(self, mock_urlopen: MagicMock) -> None:
        """Should extract curator IDs from gFollowedCuratorIDs."""
        html = (
            "<script>var gFollowedCuratorIDs = [111, 222, 333];</script>"
            '<div data-clanid="111"><span class="curator_name">Curator A</span></div>'
            '<div data-clanid="222"><span class="curator_name">Curator B</span></div>'
        )
        mock_response = MagicMock()
        mock_response.read.return_value = html.encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = CuratorClient.discover_subscribed_curators("steamLoginSecure=xyz")
        assert len(result) == 3
        ids = {r["curator_id"] for r in result}
        assert ids == {111, 222, 333}
        # Names should be populated for those with matching HTML
        name_map = {r["curator_id"]: r["name"] for r in result}
        assert name_map[111] == "Curator A"
        assert name_map[222] == "Curator B"
        assert name_map[333] == ""  # No HTML block for this one

    @patch("src.services.curator_client.urlopen")
    def test_no_followed_ids_returns_empty(self, mock_urlopen: MagicMock) -> None:
        """Should return empty list when gFollowedCuratorIDs is not found."""
        html = "<html><body>No curator data here</body></html>"
        mock_response = MagicMock()
        mock_response.read.return_value = html.encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = CuratorClient.discover_subscribed_curators("steamLoginSecure=xyz")
        assert result == []

    @patch("src.services.curator_client.urlopen")
    def test_empty_followed_ids_returns_empty(self, mock_urlopen: MagicMock) -> None:
        """Should return empty list when gFollowedCuratorIDs is empty array."""
        html = "<script>var gFollowedCuratorIDs = [];</script>"
        mock_response = MagicMock()
        mock_response.read.return_value = html.encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = CuratorClient.discover_subscribed_curators("steamLoginSecure=xyz")
        assert result == []
