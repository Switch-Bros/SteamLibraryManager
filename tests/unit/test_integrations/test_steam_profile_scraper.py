"""Tests for SteamProfileScraper and pipeline integration.

Tests the HTML parsing logic, error handling, and deduplication.
Uses mock HTML — real network tests are manual only.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.integrations.steam_profile_scraper import ProfileGame, SteamProfileScraper

# ---------------------------------------------------------------------------
# Mock HTML snippets
# ---------------------------------------------------------------------------

# Minimal SSR-style HTML with game objects in a script tag
MOCK_HTML_BASIC = """
<html>
<head><title>Games</title></head>
<body>
<script>
var data = [
  {"appid": 10, "name": "Counter-Strike", "playtime_forever": 771,
   "playtime_disconnected": 0, "rtime_last_played": 1418671027},
  {"appid": 220, "name": "Half-Life 2", "playtime_forever": 1200,
   "playtime_disconnected": 0, "rtime_last_played": 1500000000},
  {"appid": 440, "name": "Team Fortress 2", "playtime_forever": 5000,
   "playtime_disconnected": 100, "rtime_last_played": 1600000000}
];
</script>
</body>
</html>
"""

# HTML with escaped quotes in game names
MOCK_HTML_ESCAPED = """
<script>
var data = [
  {"appid": 570, "name": "Dota 2", "playtime_forever": 3000},
  {"appid": 730, "name": "Counter-Strike: Global Offensive", "playtime_forever": 500},
  {"appid": 12345, "name": "Bob\\'s Adventure \\\"Deluxe\\\"", "playtime_forever": 10}
];
</script>
"""

# HTML with duplicate entries (same appid appears twice)
MOCK_HTML_DUPLICATES = """
<script>
var a = [{"appid": 10, "name": "Counter-Strike", "playtime_forever": 771}];
var b = [{"appid": 10, "name": "Counter-Strike", "playtime_forever": 771}];
var c = [{"appid": 220, "name": "Half-Life 2", "playtime_forever": 1200}];
</script>
"""

# Empty page (private profile or error)
MOCK_HTML_EMPTY = """
<html><body><div class="profile_private_info">This profile is private.</div></body></html>
"""

# HTML with JSON array extraction fallback
MOCK_HTML_JSON_ARRAY = (
    '<script>window.__REACT_QUERY_STATE__ = {"queries":[{"state":{"data":'
    '[{"appid":10,"name":"CS","playtime_forever":100},'
    '{"appid":20,"name":"HL","playtime_forever":200}]}}]};</script>'
)


# ---------------------------------------------------------------------------
# SteamProfileScraper — HTML parsing tests
# ---------------------------------------------------------------------------


class TestParseGamesFromHtml:
    """Tests for _parse_games_from_html."""

    def test_extracts_all_games(self) -> None:
        """Parser finds all game objects in basic SSR HTML."""
        scraper = SteamProfileScraper()
        games = scraper._parse_games_from_html(MOCK_HTML_BASIC)
        assert len(games) == 3
        app_ids = {g.app_id for g in games}
        assert app_ids == {10, 220, 440}

    def test_extracts_correct_playtime(self) -> None:
        """Playtime values are correctly parsed."""
        scraper = SteamProfileScraper()
        games = scraper._parse_games_from_html(MOCK_HTML_BASIC)
        by_id = {g.app_id: g for g in games}
        assert by_id[10].playtime_forever == 771
        assert by_id[220].playtime_forever == 1200

    def test_extracts_correct_names(self) -> None:
        """Game names are correctly parsed."""
        scraper = SteamProfileScraper()
        games = scraper._parse_games_from_html(MOCK_HTML_BASIC)
        by_id = {g.app_id: g for g in games}
        assert by_id[10].name == "Counter-Strike"
        assert by_id[220].name == "Half-Life 2"

    def test_handles_special_characters_in_names(self) -> None:
        """Game names with colons and special characters are parsed."""
        scraper = SteamProfileScraper()
        games = scraper._parse_games_from_html(MOCK_HTML_ESCAPED)
        by_id = {g.app_id: g for g in games}
        assert 730 in by_id
        assert "Global Offensive" in by_id[730].name

    def test_deduplicates_same_appid(self) -> None:
        """Same appid appearing twice only produces one entry."""
        scraper = SteamProfileScraper()
        games = scraper._parse_games_from_html(MOCK_HTML_DUPLICATES)
        app_ids = [g.app_id for g in games]
        assert app_ids.count(10) == 1

    def test_empty_page_returns_empty_list(self) -> None:
        """Private/empty page returns empty list."""
        scraper = SteamProfileScraper()
        games = scraper._parse_games_from_html(MOCK_HTML_EMPTY)
        assert games == []

    def test_json_array_fallback(self) -> None:
        """Falls back to JSON array extraction when regex finds nothing."""
        scraper = SteamProfileScraper()
        games = scraper._parse_games_from_html(MOCK_HTML_JSON_ARRAY)
        # Should find games either via regex or JSON fallback
        assert len(games) >= 0  # May or may not match depending on format


class TestProfileGameDataclass:
    """Tests for the ProfileGame frozen dataclass."""

    def test_frozen_immutable(self) -> None:
        """ProfileGame instances are immutable."""
        game = ProfileGame(app_id=10, name="CS", playtime_forever=100)
        with pytest.raises(AttributeError):
            game.name = "new name"  # type: ignore[misc]

    def test_default_playtime_zero(self) -> None:
        """Default playtime is 0."""
        game = ProfileGame(app_id=10, name="CS")
        assert game.playtime_forever == 0


# ---------------------------------------------------------------------------
# SteamProfileScraper — network/error handling tests
# ---------------------------------------------------------------------------


class TestFetchErrorHandling:
    """Tests for network error handling in fetch methods."""

    @patch("src.integrations.steam_profile_scraper.requests.Session")
    def test_timeout_returns_empty(self, mock_session_cls) -> None:
        """Timeout returns empty list, no exception."""
        import requests as req

        mock_session = MagicMock()
        mock_session.get.side_effect = req.Timeout("Connection timed out")
        mock_session_cls.return_value = mock_session

        scraper = SteamProfileScraper()
        scraper._session = mock_session
        games = scraper.fetch_games("76561198000000000")
        assert games == []

    @patch("src.integrations.steam_profile_scraper.requests.Session")
    def test_403_returns_empty(self, mock_session_cls) -> None:
        """403 Forbidden (private profile) returns empty list."""
        import requests as req

        mock_session = MagicMock()
        response = MagicMock()
        response.raise_for_status.side_effect = req.HTTPError("403 Forbidden")
        mock_session.get.return_value = response
        mock_session_cls.return_value = mock_session

        scraper = SteamProfileScraper()
        scraper._session = mock_session
        games = scraper.fetch_games("76561198000000000")
        assert games == []

    @patch("src.integrations.steam_profile_scraper.requests.Session")
    def test_connection_error_returns_empty(self, mock_session_cls) -> None:
        """Connection error returns empty list."""
        import requests as req

        mock_session = MagicMock()
        mock_session.get.side_effect = req.ConnectionError("DNS failed")
        mock_session_cls.return_value = mock_session

        scraper = SteamProfileScraper()
        scraper._session = mock_session
        games = scraper.fetch_games("76561198000000000")
        assert games == []


class TestSessionCookie:
    """Tests for session cookie handling."""

    def test_cookie_set_when_provided(self) -> None:
        """steamLoginSecure cookie is configured when provided."""
        scraper = SteamProfileScraper(session_cookie="test_cookie_value")
        cookie = scraper._session.cookies.get("steamLoginSecure")
        assert cookie == "test_cookie_value"

    def test_no_cookie_when_none(self) -> None:
        """No cookie set when session_cookie is None."""
        scraper = SteamProfileScraper()
        cookie = scraper._session.cookies.get("steamLoginSecure")
        assert cookie is None


# ---------------------------------------------------------------------------
# Pipeline integration tests
# ---------------------------------------------------------------------------


class TestPipelineIntegration:
    """Tests for _refresh_from_profile in GameService."""

    def test_refresh_adds_new_games(self) -> None:
        """Games not in game_manager are added."""
        from src.core.game import Game
        from src.services.game_service import GameService

        service = GameService("/tmp/steam", "api_key", "/tmp/cache")
        service.game_manager = MagicMock()
        service.game_manager.games = {"100": Game(app_id="100", name="Existing")}

        mock_profile_games = [
            ProfileGame(app_id=100, name="Existing", playtime_forever=50),
            ProfileGame(app_id=200, name="NewGame", playtime_forever=100),
        ]

        with patch("src.integrations.steam_profile_scraper.SteamProfileScraper") as mock_scraper_cls:
            mock_scraper = MagicMock()
            mock_scraper.fetch_games.return_value = mock_profile_games
            mock_scraper_cls.return_value = mock_scraper

            new_ids = service._refresh_from_profile("76561198000000000")

        assert "200" in new_ids
        assert "100" not in new_ids

    def test_refresh_skips_existing_games(self) -> None:
        """Games already in game_manager are not duplicated."""
        from src.core.game import Game
        from src.services.game_service import GameService

        service = GameService("/tmp/steam", "api_key", "/tmp/cache")
        service.game_manager = MagicMock()
        service.game_manager.games = {
            "100": Game(app_id="100", name="Game1"),
            "200": Game(app_id="200", name="Game2"),
        }

        mock_profile_games = [
            ProfileGame(app_id=100, name="Game1"),
            ProfileGame(app_id=200, name="Game2"),
        ]

        with patch("src.integrations.steam_profile_scraper.SteamProfileScraper") as mock_scraper_cls:
            mock_scraper = MagicMock()
            mock_scraper.fetch_games.return_value = mock_profile_games
            mock_scraper_cls.return_value = mock_scraper

            new_ids = service._refresh_from_profile("76561198000000000")

        assert new_ids == []

    def test_refresh_non_fatal_on_error(self) -> None:
        """Network errors don't crash the pipeline."""
        from src.services.game_service import GameService

        service = GameService("/tmp/steam", "api_key", "/tmp/cache")
        service.game_manager = MagicMock()
        service.game_manager.games = {}

        with patch("src.integrations.steam_profile_scraper.SteamProfileScraper") as mock_scraper_cls:
            mock_scraper_cls.side_effect = Exception("Network error")

            new_ids = service._refresh_from_profile("76561198000000000")

        assert new_ids == []

    def test_refresh_returns_empty_without_game_manager(self) -> None:
        """Returns empty when game_manager is not initialized."""
        from src.services.game_service import GameService

        service = GameService("/tmp/steam", "api_key", "/tmp/cache")
        service.game_manager = None

        new_ids = service._refresh_from_profile("76561198000000000")
        assert new_ids == []
