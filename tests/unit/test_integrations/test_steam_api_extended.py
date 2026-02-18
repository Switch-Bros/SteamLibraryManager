"""Tests for SteamWebAPI extended endpoints (Phase 6.2).

Covers: GetItems extended fields, fetch_tag_list, fetch_localized_tag_names,
fetch_achievements_progress, fetch_dlc_for_apps, fetch_popular_tags,
fetch_private_app_list, toggle_app_privacy, fetch_client_app_list,
fetch_client_info, fetch_wishlist, and SteamAppDetails parsing.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.integrations.steam_web_api import SteamAppDetails, SteamWebAPI

# ---------------------------------------------------------------------------
# SteamAppDetails: frozen dataclass tests
# ---------------------------------------------------------------------------


class TestSteamAppDetailsExtended:
    """Tests for extended SteamAppDetails fields."""

    def test_description_fields(self) -> None:
        details = SteamAppDetails(
            app_id=730,
            name="CS2",
            description="A tactical shooter",
            short_description="FPS game",
        )
        assert details.description == "A tactical shooter"
        assert details.short_description == "FPS game"

    def test_age_ratings_tuple(self) -> None:
        details = SteamAppDetails(
            app_id=730,
            name="CS2",
            age_ratings=(("PEGI", "16"), ("ESRB", "M")),
        )
        assert len(details.age_ratings) == 2
        assert details.age_ratings[0] == ("PEGI", "16")
        assert details.age_ratings[1] == ("ESRB", "M")

    def test_dlc_ids_tuple(self) -> None:
        details = SteamAppDetails(
            app_id=570,
            name="Dota 2",
            dlc_ids=(100, 200, 300),
        )
        assert len(details.dlc_ids) == 3
        assert 200 in details.dlc_ids

    def test_asset_urls_tuple(self) -> None:
        details = SteamAppDetails(
            app_id=730,
            name="CS2",
            asset_urls=(("library_capsule", "https://example.com/capsule.jpg"),),
        )
        assert details.asset_urls[0][0] == "library_capsule"

    def test_defaults_are_empty(self) -> None:
        details = SteamAppDetails(app_id=1, name="Test")
        assert details.description == ""
        assert details.short_description == ""
        assert details.age_ratings == ()
        assert details.dlc_ids == ()
        assert details.asset_urls == ()

    def test_frozen(self) -> None:
        details = SteamAppDetails(app_id=1, name="Test")
        with pytest.raises(AttributeError):
            details.description = "modified"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# _parse_item: extended fields
# ---------------------------------------------------------------------------


class TestParseItemExtended:
    """Tests for _parse_item with new fields."""

    def test_parse_description(self) -> None:
        raw = {
            "id": 730,
            "name": "CS2",
            "full_description": "Full desc here",
            "short_description": "Short desc",
        }
        result = SteamWebAPI._parse_item(raw)
        assert result.description == "Full desc here"
        assert result.short_description == "Short desc"

    def test_parse_ratings_list_format(self) -> None:
        raw = {
            "id": 730,
            "name": "CS2",
            "ratings": [
                {"rating_system": "PEGI", "rating": 16},
                {"rating_system": "ESRB", "rating": "M"},
            ],
        }
        result = SteamWebAPI._parse_item(raw)
        assert ("PEGI", "16") in result.age_ratings
        assert ("ESRB", "M") in result.age_ratings

    def test_parse_ratings_dict_format(self) -> None:
        raw = {
            "id": 730,
            "name": "CS2",
            "ratings": {
                "pegi": {"rating": "16"},
                "esrb": {"rating": "M"},
            },
        }
        result = SteamWebAPI._parse_item(raw)
        assert ("PEGI", "16") in result.age_ratings
        assert ("ESRB", "M") in result.age_ratings

    def test_parse_included_items(self) -> None:
        raw = {
            "id": 570,
            "name": "Dota 2",
            "included_items": [
                {"appid": 100},
                {"appid": 200},
            ],
        }
        result = SteamWebAPI._parse_item(raw)
        assert result.dlc_ids == (100, 200)

    def test_parse_assets(self) -> None:
        raw = {
            "id": 730,
            "name": "CS2",
            "assets": {
                "library_capsule": "https://cdn.steam/capsule.jpg",
                "hero": "https://cdn.steam/hero.jpg",
            },
        }
        result = SteamWebAPI._parse_item(raw)
        assert len(result.asset_urls) == 2
        urls_dict = dict(result.asset_urls)
        assert "library_capsule" in urls_dict
        assert urls_dict["hero"] == "https://cdn.steam/hero.jpg"

    def test_parse_languages(self) -> None:
        raw = {
            "id": 730,
            "name": "CS2",
            "basic_info": {
                "supported_languages": "English<strong>*</strong>, German, French",
            },
        }
        result = SteamWebAPI._parse_item(raw)
        assert "English" in result.languages
        assert "German" in result.languages
        assert "French" in result.languages

    def test_parse_empty_ratings(self) -> None:
        raw = {"id": 1, "name": "Test", "ratings": []}
        result = SteamWebAPI._parse_item(raw)
        assert result.age_ratings == ()

    def test_parse_empty_included_items(self) -> None:
        raw = {"id": 1, "name": "Test", "included_items": []}
        result = SteamWebAPI._parse_item(raw)
        assert result.dlc_ids == ()

    def test_parse_empty_assets(self) -> None:
        raw = {"id": 1, "name": "Test", "assets": {}}
        result = SteamWebAPI._parse_item(raw)
        assert result.asset_urls == ()


# ---------------------------------------------------------------------------
# fetch_tag_list
# ---------------------------------------------------------------------------


class TestFetchTagList:
    """Tests for SteamWebAPI.fetch_tag_list()."""

    @patch("src.integrations.steam_web_api.requests.get")
    def test_success(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "response": {
                "tags": [
                    {"tagid": 19, "name": "Action"},
                    {"tagid": 21, "name": "Adventure"},
                ]
            }
        }
        mock_get.return_value = mock_resp

        api = SteamWebAPI("test-key")
        result = api.fetch_tag_list("english")

        assert result == {19: "Action", 21: "Adventure"}

    @patch("src.integrations.steam_web_api.requests.get")
    def test_empty(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"response": {"tags": []}}
        mock_get.return_value = mock_resp

        api = SteamWebAPI("test-key")
        result = api.fetch_tag_list()

        assert result == {}

    @patch("src.integrations.steam_web_api.requests.get")
    def test_network_error(self, mock_get: MagicMock) -> None:
        import requests

        mock_get.side_effect = requests.ConnectionError("timeout")

        api = SteamWebAPI("test-key")
        result = api.fetch_tag_list()

        assert result == {}


# ---------------------------------------------------------------------------
# fetch_localized_tag_names
# ---------------------------------------------------------------------------


class TestFetchLocalizedTagNames:
    """Tests for SteamWebAPI.fetch_localized_tag_names()."""

    @patch("src.integrations.steam_web_api.requests.get")
    def test_success(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "response": {
                "tags": [
                    {"tagid": 19, "name": "Aktion"},
                    {"tagid": 21, "name": "Abenteuer"},
                ]
            }
        }
        mock_get.return_value = mock_resp

        api = SteamWebAPI("test-key")
        result = api.fetch_localized_tag_names([19, 21], "german")

        assert result == {19: "Aktion", 21: "Abenteuer"}
        # Verify array params were passed
        call_kwargs = mock_get.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
        assert params["tagids[0]"] == 19
        assert params["tagids[1]"] == 21


# ---------------------------------------------------------------------------
# fetch_achievements_progress
# ---------------------------------------------------------------------------


class TestFetchAchievementsProgress:
    """Tests for SteamWebAPI.fetch_achievements_progress()."""

    @patch("src.integrations.steam_web_api.requests.get")
    def test_batch_success(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "response": {
                "achievement_progress": [
                    {"appid": 730, "unlocked": 10, "total": 50, "percentage": 20.0},
                    {"appid": 570, "unlocked": 5, "total": 20, "percentage": 25.0},
                ]
            }
        }
        mock_get.return_value = mock_resp

        api = SteamWebAPI("test-key")
        result = api.fetch_achievements_progress(76561198000000000, [730, 570])

        assert 730 in result
        assert result[730]["unlocked"] == 10
        assert result[730]["total"] == 50
        assert 570 in result

    @patch("src.integrations.steam_web_api.requests.get")
    def test_404_returns_empty(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        api = SteamWebAPI("test-key")
        result = api.fetch_achievements_progress(76561198000000000, [730])

        assert result == {}


# ---------------------------------------------------------------------------
# fetch_dlc_for_apps
# ---------------------------------------------------------------------------


class TestFetchDlcForApps:
    """Tests for SteamWebAPI.fetch_dlc_for_apps()."""

    @patch("src.integrations.steam_web_api.requests.get")
    def test_success(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "response": {
                "dlc_data": [
                    {
                        "appid": 730,
                        "dlc": [{"appid": 1001}, {"appid": 1002}],
                    }
                ]
            }
        }
        mock_get.return_value = mock_resp

        api = SteamWebAPI("test-key")
        result = api.fetch_dlc_for_apps([730])

        assert 730 in result
        assert result[730] == [1001, 1002]

    @patch("src.integrations.steam_web_api.requests.get")
    def test_empty_dlc(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"response": {"dlc_data": []}}
        mock_get.return_value = mock_resp

        api = SteamWebAPI("test-key")
        result = api.fetch_dlc_for_apps([730])

        assert result == {}


# ---------------------------------------------------------------------------
# fetch_private_app_list
# ---------------------------------------------------------------------------


class TestFetchPrivateAppList:
    """Tests for SteamWebAPI.fetch_private_app_list()."""

    @patch("src.integrations.steam_web_api.requests.get")
    def test_success(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"response": {"apps": [{"appid": 100}, {"appid": 200}]}}
        mock_get.return_value = mock_resp

        api = SteamWebAPI("test-key")
        result = api.fetch_private_app_list()

        assert result == [100, 200]

    @patch("src.integrations.steam_web_api.requests.get")
    def test_empty(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"response": {"apps": []}}
        mock_get.return_value = mock_resp

        api = SteamWebAPI("test-key")
        result = api.fetch_private_app_list()

        assert result == []

    @patch("src.integrations.steam_web_api.requests.get")
    def test_auth_error(self, mock_get: MagicMock) -> None:
        import requests as req

        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.raise_for_status.side_effect = req.HTTPError("Forbidden")
        mock_get.return_value = mock_resp

        api = SteamWebAPI("test-key")
        result = api.fetch_private_app_list()

        assert result == []


# ---------------------------------------------------------------------------
# toggle_app_privacy
# ---------------------------------------------------------------------------


class TestToggleAppPrivacy:
    """Tests for SteamWebAPI.toggle_app_privacy()."""

    @patch("src.integrations.steam_web_api.requests.post")
    def test_success(self, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        api = SteamWebAPI("test-key")
        result = api.toggle_app_privacy([730, 570], private=True)

        assert result is True

    @patch("src.integrations.steam_web_api.requests.post")
    def test_failure(self, mock_post: MagicMock) -> None:
        import requests as req

        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.raise_for_status.side_effect = req.HTTPError("Server Error")
        mock_post.return_value = mock_resp

        api = SteamWebAPI("test-key")
        result = api.toggle_app_privacy([730], private=False)

        assert result is False


# ---------------------------------------------------------------------------
# fetch_client_app_list
# ---------------------------------------------------------------------------


class TestFetchClientAppList:
    """Tests for SteamWebAPI.fetch_client_app_list()."""

    @patch("src.integrations.steam_web_api.requests.get")
    def test_success(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "response": {
                "apps": [
                    {"appid": 730, "name": "CS2"},
                    {"appid": 570, "name": "Dota 2"},
                ]
            }
        }
        mock_get.return_value = mock_resp

        api = SteamWebAPI("test-key")
        result = api.fetch_client_app_list()

        assert len(result) == 2
        assert result[0]["appid"] == 730

    @patch("src.integrations.steam_web_api.requests.get")
    def test_steam_not_running(self, mock_get: MagicMock) -> None:
        import requests as req

        mock_resp = MagicMock()
        mock_resp.status_code = 503
        mock_resp.raise_for_status.side_effect = req.HTTPError("Service Unavailable")
        mock_get.return_value = mock_resp

        api = SteamWebAPI("test-key")
        result = api.fetch_client_app_list()

        assert result == []


# ---------------------------------------------------------------------------
# fetch_wishlist
# ---------------------------------------------------------------------------


class TestFetchWishlist:
    """Tests for SteamWebAPI.fetch_wishlist()."""

    @patch("src.integrations.steam_web_api.requests.get")
    def test_success(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "response": {
                "items": [
                    {"appid": 100, "priority": 1},
                    {"appid": 200, "priority": 2},
                ]
            }
        }
        mock_get.return_value = mock_resp

        api = SteamWebAPI("test-key")
        result = api.fetch_wishlist(76561198000000000)

        assert len(result) == 2
        assert result[0]["appid"] == 100

    @patch("src.integrations.steam_web_api.requests.get")
    def test_empty_wishlist(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"response": {"items": []}}
        mock_get.return_value = mock_resp

        api = SteamWebAPI("test-key")
        result = api.fetch_wishlist(76561198000000000)

        assert result == []


# ---------------------------------------------------------------------------
# fetch_popular_tags
# ---------------------------------------------------------------------------


class TestFetchPopularTags:
    """Tests for SteamWebAPI.fetch_popular_tags()."""

    @patch("src.integrations.steam_web_api.requests.get")
    def test_success(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "response": {
                "tags": [
                    {"tagid": 19, "name": "Action"},
                    {"tagid": 21, "name": "Adventure"},
                ]
            }
        }
        mock_get.return_value = mock_resp

        api = SteamWebAPI("test-key")
        result = api.fetch_popular_tags("english")

        assert len(result) == 2
        assert result[0]["name"] == "Action"


# ---------------------------------------------------------------------------
# Constructor validation
# ---------------------------------------------------------------------------


class TestSteamWebAPIInit:
    """Tests for SteamWebAPI constructor."""

    def test_empty_key_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            SteamWebAPI("")

    def test_whitespace_key_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            SteamWebAPI("   ")

    def test_valid_key(self) -> None:
        api = SteamWebAPI("abc123")
        assert api.api_key == "abc123"
