"""Tests for the HLTB API client (direct API with endpoint discovery)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.integrations.hltb_api import (
    HLTBClient,
    HLTBResult,
    _levenshtein,
    _normalize_for_compare,
    _simplify_name,
)


def _make_hltb_entry(
    game_name: str = "Portal 2",
    profile_steam: int = 620,
    comp_main: int = 30600,
    comp_plus: int = 46800,
    comp_100: int = 79200,
    comp_all_count: int = 500,
) -> dict:
    """Creates a minimal HLTB API result entry."""
    return {
        "game_id": 1234,
        "game_name": game_name,
        "profile_steam": profile_steam,
        "comp_main": comp_main,
        "comp_plus": comp_plus,
        "comp_100": comp_100,
        "comp_all": 52200,
        "comp_all_count": comp_all_count,
    }


def _make_ready_client() -> HLTBClient:
    """Creates an HLTBClient with pre-populated endpoint cache (skips discovery)."""
    client = HLTBClient()
    client._api_path = "finder"
    client._auth_token = "test-token"
    client._cache_time = 9999999999.0  # far future
    return client


class TestHLTBResult:
    """Tests for the HLTBResult frozen dataclass."""

    def test_result_dataclass_frozen(self) -> None:
        """Frozen dataclass raises AttributeError on mutation."""
        result = HLTBResult(game_name="Test", main_story=10.0, main_extras=15.0, completionist=20.0)
        with pytest.raises(AttributeError):
            result.game_name = "Changed"  # type: ignore[misc]

    def test_result_values(self) -> None:
        """HLTBResult stores all values correctly."""
        result = HLTBResult(game_name="Portal 2", main_story=8.5, main_extras=13.0, completionist=22.0)
        assert result.game_name == "Portal 2"
        assert result.main_story == 8.5
        assert result.main_extras == 13.0
        assert result.completionist == 22.0


class TestNormalizeName:
    """Tests for the _normalize_name static method."""

    def test_normalize_name_strips_trademark(self) -> None:
        """Trademark and registered symbols are removed."""
        assert HLTBClient._normalize_name("Fallout\u2122") == "Fallout"
        assert HLTBClient._normalize_name("Skyrim\u00ae") == "Skyrim"

    def test_normalize_name_preserves_edition_suffix(self) -> None:
        """Edition suffixes are preserved (stripped later as fallback)."""
        assert HLTBClient._normalize_name("Game - Deluxe Edition") == "Game - Deluxe Edition"
        assert HLTBClient._normalize_name("Game - GOTY Edition Pack") == "Game - GOTY Edition Pack"

    def test_normalize_name_strips_copyright(self) -> None:
        """Copyright symbol is removed."""
        assert HLTBClient._normalize_name("Game\u00a9") == "Game"

    def test_normalize_name_strips_text_symbols(self) -> None:
        """Text-form symbols like (TM) and (R) are removed."""
        assert HLTBClient._normalize_name("Game(TM)") == "Game"
        assert HLTBClient._normalize_name("Game(R)") == "Game"

    def test_normalize_name_adds_space_for_symbols(self) -> None:
        """Symbols replaced with space to keep word boundaries."""
        assert HLTBClient._normalize_name("Velocity\u00aeUltra") == "Velocity Ultra"

    def test_normalize_name_strips_year_tags(self) -> None:
        """Year tags like (2003) are removed."""
        assert HLTBClient._normalize_name("Broken Sword 3 (2003)") == "Broken Sword 3"
        assert HLTBClient._normalize_name("Tomb Raider IV (1999)") == "Tomb Raider IV"

    def test_normalize_name_strips_classic_tag(self) -> None:
        """(Classic) parenthetical is removed."""
        assert HLTBClient._normalize_name("Mafia II (Classic)") == "Mafia II"

    def test_normalize_name_superscript_digits(self) -> None:
        """Superscript digits are normalized to regular digits."""
        assert HLTBClient._normalize_name("TrackMania\u00b2 Stadium") == "TrackMania2 Stadium"

    def test_normalize_name_backtick_to_apostrophe(self) -> None:
        """Backtick is normalized to apostrophe."""
        assert HLTBClient._normalize_name("The Siren`s Call") == "The Siren's Call"

    def test_normalize_name_strips_infinity_symbol(self) -> None:
        """Infinity symbols are stripped."""
        assert HLTBClient._normalize_name("Skullgirls \u221eEndless Beta\u221e") == "Skullgirls Endless Beta"

    def test_normalize_name_preserves_numbers(self) -> None:
        """Numbers in game names are preserved."""
        assert HLTBClient._normalize_name("Half-Life 2") == "Half-Life 2"
        assert HLTBClient._normalize_name("Portal 2") == "Portal 2"

    def test_normalize_name_empty_input(self) -> None:
        """Empty string returns empty string."""
        assert HLTBClient._normalize_name("") == ""


class TestNormalizeForCompare:
    """Tests for the _normalize_for_compare function."""

    def test_strips_accents(self) -> None:
        """Accented characters are stripped to base form."""
        assert _normalize_for_compare("Café") == "cafe"

    def test_lowercases(self) -> None:
        """Names are lowercased."""
        assert _normalize_for_compare("PORTAL 2") == "portal 2"

    def test_strips_special_chars(self) -> None:
        """Special characters (TM, etc.) are removed."""
        assert _normalize_for_compare("Fallout\u2122") == "fallout"


class TestLevenshtein:
    """Tests for the _levenshtein distance function."""

    def test_identical_strings(self) -> None:
        """Identical strings have distance 0."""
        assert _levenshtein("portal", "portal") == 0

    def test_empty_strings(self) -> None:
        """Empty vs non-empty string has distance equal to length."""
        assert _levenshtein("", "abc") == 3
        assert _levenshtein("abc", "") == 3

    def test_single_edit(self) -> None:
        """Strings differing by one character have distance 1."""
        assert _levenshtein("cat", "bat") == 1
        assert _levenshtein("cat", "cats") == 1

    def test_different_strings(self) -> None:
        """Completely different strings have high distance."""
        assert _levenshtein("abc", "xyz") == 3

    def test_case_sensitive(self) -> None:
        """Distance is case-sensitive."""
        assert _levenshtein("ABC", "abc") == 3


class TestSimplifyName:
    """Tests for the _simplify_name function."""

    def test_strips_deluxe_edition(self) -> None:
        """Strips '- Deluxe Edition' and similar suffixes."""
        assert _simplify_name("Game - Deluxe Edition") == "Game"

    def test_strips_goty(self) -> None:
        """Strips '- Game of the Year Edition'."""
        assert _simplify_name("Game - Game of the Year Edition") == "Game"

    def test_strips_directors_cut(self) -> None:
        """Strips '- Director's Cut'."""
        assert _simplify_name("Game - Director's Cut") == "Game"

    def test_strips_remastered(self) -> None:
        """Strips ': Remastered' with colon separator."""
        assert _simplify_name("Game: Remastered") == "Game"

    def test_preserves_name_without_edition(self) -> None:
        """Names without edition suffixes are not altered."""
        assert _simplify_name("Half-Life 2") == "Half-Life 2"

    def test_strips_with_em_dash(self) -> None:
        """Strips edition suffixes with em dash separator."""
        assert _simplify_name("Game\u2014Complete Edition") == "Game"

    def test_strips_year_tag(self) -> None:
        """Strips year tags in parentheses."""
        assert _simplify_name("Game (2013)") == "Game"

    def test_strips_anniversary_edition(self) -> None:
        """Strips numbered anniversary editions."""
        assert _simplify_name("Game 25th Anniversary Edition") == "Game"

    def test_strips_classic(self) -> None:
        """Strips 'Classic' suffix."""
        assert _simplify_name("Artifact Classic") == "Artifact"

    def test_strips_stacked_suffixes(self) -> None:
        """Handles stacked suffixes via iterative stripping."""
        assert _simplify_name("Game - Enhanced Edition - Director's Cut") == "Game"

    def test_strips_legacy_edition(self) -> None:
        """Strips '- Legacy Edition'."""
        assert _simplify_name("Company of Heroes - Legacy Edition") == "Company of Heroes"

    def test_strips_online_suffix(self) -> None:
        """Strips 'Online' suffix."""
        assert _simplify_name("Game Online") == "Game"

    def test_strips_season(self) -> None:
        """Strips 'Season N' suffix."""
        assert _simplify_name("Game - Season 2") == "Game"

    def test_strips_hd(self) -> None:
        """Strips 'HD' suffix."""
        assert _simplify_name("Game HD") == "Game"


class TestSearchGame:
    """Tests for HLTBClient.search_game with direct API."""

    @patch.object(HLTBClient, "_ensure_api_ready", return_value=True)
    def test_search_game_exact_match(self, _mock_ready: MagicMock) -> None:
        """Exact name match returns result immediately."""
        client = _make_ready_client()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [
                _make_hltb_entry("Portal 2 Wrong", profile_steam=999),
                _make_hltb_entry("Portal 2", profile_steam=620),
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        client._session.post = MagicMock(return_value=mock_resp)

        result = client.search_game("Portal 2", app_id=620)

        assert result is not None
        assert result.game_name == "Portal 2"
        assert result.main_story == pytest.approx(30600 / 3600, rel=1e-2)

    @patch.object(HLTBClient, "_ensure_api_ready", return_value=True)
    def test_search_game_falls_back_to_name(self, _mock_ready: MagicMock) -> None:
        """Falls back to exact name match when AppID not found."""
        client = _make_ready_client()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": [_make_hltb_entry("Portal 2", profile_steam=0)]}
        mock_resp.raise_for_status = MagicMock()
        client._session.post = MagicMock(return_value=mock_resp)

        result = client.search_game("Portal 2", app_id=620)

        assert result is not None
        assert result.game_name == "Portal 2"

    @patch.object(HLTBClient, "_ensure_api_ready", return_value=True)
    def test_search_game_fuzzy_match(self, _mock_ready: MagicMock) -> None:
        """Levenshtein matching finds close name matches."""
        client = _make_ready_client()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": [_make_hltb_entry("The Witcher 3: Wild Hunt", profile_steam=0)]}
        mock_resp.raise_for_status = MagicMock()
        client._session.post = MagicMock(return_value=mock_resp)

        result = client.search_game("The Witcher 3 Wild Hunt", app_id=0)

        assert result is not None
        assert "Witcher" in result.game_name

    @patch.object(HLTBClient, "_ensure_api_ready", return_value=True)
    def test_search_game_not_found_returns_none(self, _mock_ready: MagicMock) -> None:
        """Empty results from HLTB returns None."""
        client = _make_ready_client()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": []}
        mock_resp.raise_for_status = MagicMock()
        client._session.post = MagicMock(return_value=mock_resp)

        result = client.search_game("NonexistentGame12345")

        assert result is None

    @patch.object(HLTBClient, "_ensure_api_ready", return_value=True)
    def test_search_game_api_error_returns_none(self, _mock_ready: MagicMock) -> None:
        """Network errors are caught and return None."""
        client = _make_ready_client()
        client._session.post = MagicMock(side_effect=ConnectionError("timeout"))

        result = client.search_game("Portal 2")

        assert result is None

    @patch.object(HLTBClient, "_ensure_api_ready", return_value=True)
    def test_conversion_seconds_to_hours(self, _mock_ready: MagicMock) -> None:
        """HLTB API returns seconds, client converts to hours."""
        client = _make_ready_client()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": [_make_hltb_entry(comp_main=36000, comp_plus=54000, comp_100=90000)]}
        mock_resp.raise_for_status = MagicMock()
        client._session.post = MagicMock(return_value=mock_resp)

        result = client.search_game("Portal 2", app_id=620)

        assert result is not None
        assert result.main_story == pytest.approx(10.0)
        assert result.main_extras == pytest.approx(15.0)
        assert result.completionist == pytest.approx(25.0)

    def test_is_available_always_true(self) -> None:
        """is_available returns True (no library dependency)."""
        assert HLTBClient.is_available() is True

    def test_search_game_empty_name_returns_none(self) -> None:
        """Empty name returns None without making API call."""
        client = HLTBClient()
        result = client.search_game("")
        assert result is None

    @patch.object(HLTBClient, "_ensure_api_ready", return_value=False)
    def test_search_game_api_not_ready_returns_none(self, _mock_ready: MagicMock) -> None:
        """Returns None when API endpoint cannot be discovered."""
        client = HLTBClient()
        result = client.search_game("Portal 2")
        assert result is None

    @patch.object(HLTBClient, "_ensure_api_ready", return_value=True)
    def test_retry_on_404(self, mock_ready: MagicMock) -> None:
        """Retries with fresh endpoint on 404 response."""
        client = _make_ready_client()

        first_resp = MagicMock()
        first_resp.status_code = 404

        second_resp = MagicMock()
        second_resp.status_code = 200
        second_resp.json.return_value = {"data": [_make_hltb_entry("Portal 2", profile_steam=620)]}
        second_resp.raise_for_status = MagicMock()

        client._session.post = MagicMock(side_effect=[first_resp, second_resp])

        result = client.search_game("Portal 2", app_id=620)

        assert result is not None
        assert result.game_name == "Portal 2"
        # _ensure_api_ready called twice (initial + retry)
        assert mock_ready.call_count == 2

    @patch.object(HLTBClient, "_ensure_api_ready", return_value=True)
    def test_popularity_tiebreaker(self, _mock_ready: MagicMock) -> None:
        """When distance is equal, more popular game wins."""
        client = _make_ready_client()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [
                _make_hltb_entry("Game X", comp_all_count=10),
                _make_hltb_entry("Game Y", comp_all_count=1000),
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        client._session.post = MagicMock(return_value=mock_resp)

        # Both names have same distance to "Game Z"
        result = client.search_game("Game Z")

        assert result is not None
        assert result.game_name == "Game Y"


class TestFindBestMatch:
    """Tests for the _find_best_match static method."""

    def test_exact_name_match_preferred(self) -> None:
        """Exact name match is preferred over fuzzy match."""
        results = [
            _make_hltb_entry("Team Fortress Classic"),
            _make_hltb_entry("Team Fortress 2"),
        ]
        match, distance = HLTBClient._find_best_match(results, "Team Fortress 2")
        assert match is not None
        assert match["game_name"] == "Team Fortress 2"
        assert distance == 0

    def test_returns_closest_levenshtein_match(self) -> None:
        """Returns result with smallest Levenshtein distance."""
        results = [
            _make_hltb_entry("ZZZZZZZZZZ"),
            _make_hltb_entry("Portal 3"),
        ]
        match, distance = HLTBClient._find_best_match(results, "Portal 2")
        assert match is not None
        assert match["game_name"] == "Portal 3"
        assert distance == 1


class TestEndpointDiscovery:
    """Tests for the _discover_endpoint method."""

    def test_discover_finds_endpoint_in_app_bundle(self) -> None:
        """Discovers API path from _app-*.js bundle."""
        client = HLTBClient()

        homepage_html = """
        <html><head>
        <script src="/_next/static/chunks/abc123.js"></script>
        </head><body></body></html>
        """

        js_content = """
        fetch(`/api/finder/init?t=${Date.now()}`).then(r=>r.json())
        function searchGames(e){return fetch("/api/finder",{method:"POST",body:JSON.stringify(e)})}
        """

        mock_js = MagicMock()
        mock_js.text = js_content
        mock_js.raise_for_status = MagicMock()

        client._session.get = MagicMock(return_value=mock_js)

        path = client._discover_endpoint(homepage_html)
        assert path == "finder"

    def test_discover_returns_empty_on_no_match(self) -> None:
        """Returns empty string when no init pattern found in JS."""
        client = HLTBClient()

        homepage_html = """
        <html><head>
        <script src="/_next/static/chunks/abc123.js"></script>
        </head><body></body></html>
        """

        mock_js = MagicMock()
        mock_js.text = "var x = 42;"
        mock_js.raise_for_status = MagicMock()

        client._session.get = MagicMock(return_value=mock_js)

        path = client._discover_endpoint(homepage_html)
        assert path == ""

    def test_discover_returns_empty_on_empty_html(self) -> None:
        """Returns empty string for empty HTML."""
        client = HLTBClient()
        path = client._discover_endpoint("")
        assert path == ""


class TestAuthToken:
    """Tests for the _get_auth_token method."""

    def test_get_auth_token_success(self) -> None:
        """Successfully obtains auth token from init endpoint."""
        client = HLTBClient()

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"token": "abc123xyz"}
        mock_resp.raise_for_status = MagicMock()
        client._session.get = MagicMock(return_value=mock_resp)

        token = client._get_auth_token("finder")
        assert token == "abc123xyz"

    def test_get_auth_token_failure(self) -> None:
        """Returns empty string on init endpoint failure."""
        client = HLTBClient()
        client._session.get = MagicMock(side_effect=ConnectionError("offline"))

        token = client._get_auth_token("finder")
        assert token == ""


class TestFallbackSearch:
    """Tests for the two-pass search strategy in search_game."""

    @patch.object(HLTBClient, "_ensure_api_ready", return_value=True)
    def test_fallback_strips_edition_on_miss(self, _mock_ready: MagicMock) -> None:
        """Falls back to stripped name when full name returns no match."""
        client = _make_ready_client()

        # First search (full name) returns empty, second (stripped) finds match
        empty_resp = MagicMock()
        empty_resp.status_code = 200
        empty_resp.json.return_value = {"data": []}
        empty_resp.raise_for_status = MagicMock()

        match_resp = MagicMock()
        match_resp.status_code = 200
        match_resp.json.return_value = {"data": [_make_hltb_entry("Skyrim", comp_main=72000)]}
        match_resp.raise_for_status = MagicMock()

        client._session.post = MagicMock(side_effect=[empty_resp, match_resp])

        result = client.search_game("Skyrim - Special Edition")

        assert result is not None
        assert result.game_name == "Skyrim"
        assert client._session.post.call_count == 2

    @patch.object(HLTBClient, "_ensure_api_ready", return_value=True)
    def test_no_fallback_when_exact_match(self, _mock_ready: MagicMock) -> None:
        """No fallback search when exact match is found on first pass."""
        client = _make_ready_client()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": [_make_hltb_entry("Portal 2")]}
        mock_resp.raise_for_status = MagicMock()
        client._session.post = MagicMock(return_value=mock_resp)

        result = client.search_game("Portal 2")

        assert result is not None
        # Only one POST call — no fallback needed
        assert client._session.post.call_count == 1


class TestIdCache:
    """Tests for the steam_app_id → hltb_game_id cache."""

    def test_set_and_get_id_cache(self) -> None:
        """set_id_cache populates and get_id_cache returns mappings."""
        client = HLTBClient()
        mappings = {620: 1234, 730: 5678}
        client.set_id_cache(mappings)

        result = client.get_id_cache()
        assert result == {620: 1234, 730: 5678}
        # Returned copy, not same object
        assert result is not client._id_cache

    def test_empty_id_cache(self) -> None:
        """Empty cache returns empty dict."""
        client = HLTBClient()
        assert client.get_id_cache() == {}

    @patch.object(HLTBClient, "_ensure_api_ready", return_value=True)
    @patch.object(HLTBClient, "fetch_game_by_id")
    def test_search_game_uses_cache(self, mock_fetch: MagicMock, _mock_ready: MagicMock) -> None:
        """search_game uses ID cache when app_id is cached."""
        client = _make_ready_client()
        client.set_id_cache({620: 1234})

        expected_result = HLTBResult(game_name="Portal 2", main_story=8.5, main_extras=13.0, completionist=22.0)
        mock_fetch.return_value = expected_result

        result = client.search_game("Portal 2", app_id=620)

        assert result is expected_result
        mock_fetch.assert_called_once_with(1234)

    @patch.object(HLTBClient, "_ensure_api_ready", return_value=True)
    @patch.object(HLTBClient, "fetch_game_by_id", return_value=None)
    def test_search_game_falls_back_on_cache_miss(self, _mock_fetch: MagicMock, _mock_ready: MagicMock) -> None:
        """search_game falls back to name search if fetch_game_by_id returns None."""
        client = _make_ready_client()
        client.set_id_cache({620: 9999})

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": [_make_hltb_entry("Portal 2")]}
        mock_resp.raise_for_status = MagicMock()
        client._session.post = MagicMock(return_value=mock_resp)

        result = client.search_game("Portal 2", app_id=620)

        assert result is not None
        assert result.game_name == "Portal 2"

    @patch.object(HLTBClient, "_ensure_api_ready", return_value=True)
    def test_search_game_skips_cache_without_app_id(self, _mock_ready: MagicMock) -> None:
        """search_game skips cache lookup when app_id is 0."""
        client = _make_ready_client()
        client.set_id_cache({620: 1234})

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": [_make_hltb_entry("Portal 2")]}
        mock_resp.raise_for_status = MagicMock()
        client._session.post = MagicMock(return_value=mock_resp)

        result = client.search_game("Portal 2", app_id=0)

        assert result is not None
        # Should have used POST (name search), not fetch_game_by_id
        assert client._session.post.call_count == 1


class TestFetchSteamImport:
    """Tests for the fetch_steam_import method."""

    @patch.object(HLTBClient, "_ensure_api_ready", return_value=True)
    def test_fetch_steam_import_success(self, _mock_ready: MagicMock) -> None:
        """Successfully parses Steam Import API response."""
        client = _make_ready_client()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "games": [
                {"steam_id": 620, "hltb_id": 1234, "name": "Portal 2"},
                {"steam_id": 730, "hltb_id": 5678, "name": "Counter-Strike 2"},
                {"steam_id": 0, "hltb_id": 0, "name": "Invalid"},  # filtered out
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        client._session.post = MagicMock(return_value=mock_resp)

        mappings = client.fetch_steam_import("76561198012345678")

        assert mappings == {620: 1234, 730: 5678}

    @patch.object(HLTBClient, "_ensure_api_ready", return_value=True)
    def test_fetch_steam_import_empty_response(self, _mock_ready: MagicMock) -> None:
        """Empty response returns empty dict."""
        client = _make_ready_client()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"games": []}
        mock_resp.raise_for_status = MagicMock()
        client._session.post = MagicMock(return_value=mock_resp)

        mappings = client.fetch_steam_import("76561198012345678")

        assert mappings == {}

    @patch.object(HLTBClient, "_ensure_api_ready", return_value=True)
    def test_fetch_steam_import_network_error(self, _mock_ready: MagicMock) -> None:
        """Network error returns empty dict."""
        client = _make_ready_client()
        client._session.post = MagicMock(side_effect=ConnectionError("timeout"))

        mappings = client.fetch_steam_import("76561198012345678")

        assert mappings == {}

    @patch.object(HLTBClient, "_ensure_api_ready", return_value=False)
    def test_fetch_steam_import_api_not_ready(self, _mock_ready: MagicMock) -> None:
        """Returns empty dict when API is not ready."""
        client = HLTBClient()

        mappings = client.fetch_steam_import("76561198012345678")

        assert mappings == {}


class TestFetchGameById:
    """Tests for the fetch_game_by_id method."""

    @patch.object(HLTBClient, "_ensure_api_ready", return_value=True)
    def test_fetch_game_by_id_success(self, _mock_ready: MagicMock) -> None:
        """Successfully fetches game data by HLTB ID."""
        client = _make_ready_client()
        client._build_id = "abc123"

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "pageProps": {"game": {"data": {"game": [_make_hltb_entry("Portal 2", comp_main=30600)]}}}
        }
        mock_resp.raise_for_status = MagicMock()
        client._session.get = MagicMock(return_value=mock_resp)

        result = client.fetch_game_by_id(1234)

        assert result is not None
        assert result.game_name == "Portal 2"
        assert result.main_story == pytest.approx(30600 / 3600, rel=1e-2)

    @patch.object(HLTBClient, "_ensure_api_ready", return_value=True)
    def test_fetch_game_by_id_no_build_id(self, _mock_ready: MagicMock) -> None:
        """Returns None when buildId is not available."""
        client = _make_ready_client()
        client._build_id = ""

        result = client.fetch_game_by_id(1234)

        assert result is None

    @patch.object(HLTBClient, "_ensure_api_ready", return_value=True)
    def test_fetch_game_by_id_empty_game_list(self, _mock_ready: MagicMock) -> None:
        """Returns None when game list is empty."""
        client = _make_ready_client()
        client._build_id = "abc123"

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"pageProps": {"game": {"data": {"game": []}}}}
        mock_resp.raise_for_status = MagicMock()
        client._session.get = MagicMock(return_value=mock_resp)

        result = client.fetch_game_by_id(1234)

        assert result is None

    @patch.object(HLTBClient, "_ensure_api_ready", return_value=True)
    def test_fetch_game_by_id_malformed_response(self, _mock_ready: MagicMock) -> None:
        """Returns None on malformed response."""
        client = _make_ready_client()
        client._build_id = "abc123"

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"pageProps": {}}
        mock_resp.raise_for_status = MagicMock()
        client._session.get = MagicMock(return_value=mock_resp)

        result = client.fetch_game_by_id(1234)

        assert result is None

    @patch.object(HLTBClient, "_ensure_api_ready", return_value=True)
    def test_fetch_game_by_id_network_error(self, _mock_ready: MagicMock) -> None:
        """Network error returns None."""
        client = _make_ready_client()
        client._build_id = "abc123"
        client._session.get = MagicMock(side_effect=ConnectionError("timeout"))

        result = client.fetch_game_by_id(1234)

        assert result is None


class TestDiscoverBuildId:
    """Tests for the _discover_build_id static method."""

    def test_discover_build_id_from_manifest(self) -> None:
        """Extracts buildId from _buildManifest.js script tag."""
        html = """
        <html><head>
        <script src="/_next/static/abc123def/_buildManifest.js"></script>
        </head><body></body></html>
        """
        build_id = HLTBClient._discover_build_id(html)
        assert build_id == "abc123def"

    def test_discover_build_id_not_found(self) -> None:
        """Returns empty string when no _buildManifest.js found."""
        html = """
        <html><head>
        <script src="/_next/static/chunks/main.js"></script>
        </head><body></body></html>
        """
        build_id = HLTBClient._discover_build_id(html)
        assert build_id == ""

    def test_discover_build_id_empty_html(self) -> None:
        """Returns empty string for empty HTML."""
        build_id = HLTBClient._discover_build_id("")
        assert build_id == ""
