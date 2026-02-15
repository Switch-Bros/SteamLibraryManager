# tests/unit/test_services/test_filter_service.py

"""Tests for the FilterService and FilterState."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.core.game import Game
from src.services.filter_service import (
    ALL_PLATFORM_KEYS,
    ALL_TYPE_KEYS,
    FilterService,
    FilterState,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_game(
    app_id: str = "1",
    name: str = "TestGame",
    app_type: str = "game",
    platforms: list[str] | None = None,
    installed: bool = False,
    hidden: bool = False,
    playtime_minutes: int = 0,
    categories: list[str] | None = None,
    languages: list[str] | None = None,
) -> Game:
    """Helper to create a Game with sensible defaults."""
    return Game(
        app_id=app_id,
        name=name,
        app_type=app_type,
        platforms=platforms,
        installed=installed,
        hidden=hidden,
        playtime_minutes=playtime_minutes,
        categories=categories,
        languages=languages,
    )


@pytest.fixture
def service() -> FilterService:
    """Returns a fresh FilterService instance."""
    return FilterService()


@pytest.fixture
def mixed_games() -> list[Game]:
    """Returns a diverse set of games for filter testing."""
    return [
        _make_game("1", "Game A", "game", ["windows", "linux"], installed=True, playtime_minutes=120),
        _make_game("2", "Game B", "game", ["windows"], installed=False, playtime_minutes=0),
        _make_game("3", "Soundtrack", "music", ["windows"]),
        _make_game("4", "Tool App", "tool", ["linux"]),
        _make_game("5", "Software", "application", ["windows", "linux"]),
        _make_game("6", "Video", "video"),
        _make_game("7", "DLC Pack", "dlc"),
        _make_game("8", "Unknown Type", "", ["linux"], installed=True),
        _make_game("9", "Hidden Game", "game", hidden=True),
        _make_game("10", "No Platform", "game"),
    ]


# ---------------------------------------------------------------------------
# FilterState defaults
# ---------------------------------------------------------------------------


class TestFilterStateDefaults:
    """Tests for FilterState immutable defaults."""

    def test_default_types_all_enabled(self) -> None:
        state = FilterState()
        assert state.enabled_types == ALL_TYPE_KEYS

    def test_default_platforms_all_enabled(self) -> None:
        state = FilterState()
        assert state.enabled_platforms == ALL_PLATFORM_KEYS

    def test_default_statuses_empty(self) -> None:
        state = FilterState()
        assert state.active_statuses == frozenset()

    def test_frozen(self) -> None:
        state = FilterState()
        with pytest.raises(AttributeError):
            state.enabled_types = frozenset()  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Toggle methods
# ---------------------------------------------------------------------------


class TestToggleMethods:
    """Tests for FilterService toggle methods."""

    def test_toggle_type_off(self, service: FilterService) -> None:
        service.toggle_type("soundtracks", False)
        assert "soundtracks" not in service.state.enabled_types

    def test_toggle_type_on(self, service: FilterService) -> None:
        service.toggle_type("soundtracks", False)
        service.toggle_type("soundtracks", True)
        assert "soundtracks" in service.state.enabled_types

    def test_toggle_platform_off(self, service: FilterService) -> None:
        service.toggle_platform("windows", False)
        assert "windows" not in service.state.enabled_platforms

    def test_toggle_platform_on(self, service: FilterService) -> None:
        service.toggle_platform("linux", False)
        service.toggle_platform("linux", True)
        assert "linux" in service.state.enabled_platforms

    def test_toggle_status_on(self, service: FilterService) -> None:
        service.toggle_status("installed", True)
        assert "installed" in service.state.active_statuses

    def test_toggle_status_off(self, service: FilterService) -> None:
        service.toggle_status("favorites", True)
        service.toggle_status("favorites", False)
        assert "favorites" not in service.state.active_statuses

    def test_toggle_unknown_type_ignored(self, service: FilterService) -> None:
        service.toggle_type("bogus", False)
        assert service.state.enabled_types == ALL_TYPE_KEYS

    def test_toggle_unknown_platform_ignored(self, service: FilterService) -> None:
        service.toggle_platform("bogus", False)
        assert service.state.enabled_platforms == ALL_PLATFORM_KEYS

    def test_toggle_unknown_status_ignored(self, service: FilterService) -> None:
        service.toggle_status("bogus", True)
        assert service.state.active_statuses == frozenset()


# ---------------------------------------------------------------------------
# has_active_filters / is_type_category_visible
# ---------------------------------------------------------------------------


class TestFilterQueries:
    """Tests for has_active_filters and is_type_category_visible."""

    def test_no_active_filters_by_default(self, service: FilterService) -> None:
        assert service.has_active_filters() is False

    def test_has_active_filters_type(self, service: FilterService) -> None:
        service.toggle_type("tools", False)
        assert service.has_active_filters() is True

    def test_has_active_filters_platform(self, service: FilterService) -> None:
        service.toggle_platform("windows", False)
        assert service.has_active_filters() is True

    def test_has_active_filters_status(self, service: FilterService) -> None:
        service.toggle_status("installed", True)
        assert service.has_active_filters() is True

    def test_type_category_visible_default(self, service: FilterService) -> None:
        assert service.is_type_category_visible("soundtracks") is True

    def test_type_category_not_visible(self, service: FilterService) -> None:
        service.toggle_type("soundtracks", False)
        assert service.is_type_category_visible("soundtracks") is False


# ---------------------------------------------------------------------------
# apply() – Type filter
# ---------------------------------------------------------------------------


class TestRestoreState:
    """Tests for FilterService.restore_state()."""

    def test_restore_state_replaces_current_state(self, service: FilterService) -> None:
        """restore_state should replace all internal sets with the snapshot values."""
        custom = FilterState(
            enabled_types=frozenset({"games"}),
            enabled_platforms=frozenset({"linux"}),
            active_statuses=frozenset({"installed"}),
        )
        service.restore_state(custom)
        result = service.state

        assert result.enabled_types == frozenset({"games"})
        assert result.enabled_platforms == frozenset({"linux"})
        assert result.active_statuses == frozenset({"installed"})

    def test_restore_state_partial_types_only_those_enabled(self, service: FilterService) -> None:
        """After restoring a state with only 2 types, only those should be enabled."""
        partial = FilterState(
            enabled_types=frozenset({"games", "dlcs"}),
        )
        service.restore_state(partial)
        assert service.state.enabled_types == frozenset({"games", "dlcs"})
        # Platforms and statuses should use the values from the given FilterState
        assert service.state.enabled_platforms == ALL_PLATFORM_KEYS
        assert service.state.active_statuses == frozenset()


class TestApplyTypeFilter:
    """Tests for apply() with type filters."""

    def test_no_filter_returns_all(self, service: FilterService, mixed_games: list[Game]) -> None:
        result = service.apply(mixed_games)
        assert len(result) == len(mixed_games)

    def test_disable_soundtracks(self, service: FilterService, mixed_games: list[Game]) -> None:
        service.toggle_type("soundtracks", False)
        result = service.apply(mixed_games)
        assert not any(g.app_type == "music" for g in result)

    def test_disable_games_hides_game_type(self, service: FilterService, mixed_games: list[Game]) -> None:
        service.toggle_type("games", False)
        result = service.apply(mixed_games)
        # Should hide app_type "game" and "" (unknown)
        app_types = {g.app_type.lower() for g in result}
        assert "game" not in app_types

    def test_disable_all_types_returns_empty(self, service: FilterService, mixed_games: list[Game]) -> None:
        for key in ALL_TYPE_KEYS:
            service.toggle_type(key, False)
        result = service.apply(mixed_games)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# apply() – Platform filter
# ---------------------------------------------------------------------------


class TestApplyPlatformFilter:
    """Tests for apply() with platform filters."""

    def test_disable_windows(self, service: FilterService, mixed_games: list[Game]) -> None:
        service.toggle_platform("windows", False)
        service.toggle_platform("steamos", False)
        result = service.apply(mixed_games)
        # Games with only ["windows"] should be gone
        game_b = [g for g in result if g.app_id == "2"]
        assert len(game_b) == 0

    def test_games_without_platforms_always_pass(self, service: FilterService) -> None:
        """Games with no platform data should pass the platform filter."""
        service.toggle_platform("windows", False)
        service.toggle_platform("linux", False)
        service.toggle_platform("steamos", False)
        game = _make_game("1", "No Platforms", "game", platforms=[])
        result = service.apply([game])
        assert len(result) == 1


# ---------------------------------------------------------------------------
# apply() – Status filter
# ---------------------------------------------------------------------------


class TestApplyStatusFilter:
    """Tests for apply() with status filters (OR logic)."""

    def test_installed_only(self, service: FilterService, mixed_games: list[Game]) -> None:
        service.toggle_status("installed", True)
        result = service.apply(mixed_games)
        assert all(g.installed for g in result)

    def test_not_installed_only(self, service: FilterService, mixed_games: list[Game]) -> None:
        service.toggle_status("not_installed", True)
        result = service.apply(mixed_games)
        assert all(not g.installed for g in result)

    def test_with_playtime(self, service: FilterService, mixed_games: list[Game]) -> None:
        service.toggle_status("with_playtime", True)
        result = service.apply(mixed_games)
        assert all(g.playtime_minutes > 0 for g in result)

    def test_hidden_status(self, service: FilterService, mixed_games: list[Game]) -> None:
        service.toggle_status("hidden", True)
        result = service.apply(mixed_games)
        assert all(g.hidden for g in result)

    @patch("src.core.game.t", return_value="Favorites")
    def test_favorites_status(self, mock_t: object, service: FilterService) -> None:
        fav_game = _make_game("1", "Fav", categories=["Favorites"])
        nonfav_game = _make_game("2", "NonFav", categories=["Action"])
        service.toggle_status("favorites", True)
        result = service.apply([fav_game, nonfav_game])
        assert len(result) == 1
        assert result[0].app_id == "1"

    def test_or_logic_installed_or_playtime(self, service: FilterService) -> None:
        """Multiple status filters use OR logic."""
        games = [
            _make_game("1", "Installed", installed=True, playtime_minutes=0),
            _make_game("2", "Played", installed=False, playtime_minutes=100),
            _make_game("3", "Neither", installed=False, playtime_minutes=0),
        ]
        service.toggle_status("installed", True)
        service.toggle_status("with_playtime", True)
        result = service.apply(games)
        assert len(result) == 2
        ids = {g.app_id for g in result}
        assert ids == {"1", "2"}


# ---------------------------------------------------------------------------
# apply() – Combined filters
# ---------------------------------------------------------------------------


class TestApplyCombinedFilters:
    """Tests for apply() with multiple filter types active simultaneously."""

    def test_type_and_platform_combined(self, service: FilterService) -> None:
        """Only games that are type=game AND platform=linux should pass."""
        games = [
            _make_game("1", "Linux Game", "game", ["linux"]),
            _make_game("2", "Windows Game", "game", ["windows"]),
            _make_game("3", "Linux Tool", "tool", ["linux"]),
        ]
        # Disable all types except games
        for key in ("soundtracks", "software", "videos", "dlcs", "tools"):
            service.toggle_type(key, False)
        # Disable all platforms except linux
        service.toggle_platform("windows", False)
        service.toggle_platform("steamos", False)

        result = service.apply(games)
        assert len(result) == 1
        assert result[0].app_id == "1"

    def test_type_platform_and_status_combined(self, service: FilterService) -> None:
        """Triple filter: type=game, platform=linux, status=installed."""
        games = [
            _make_game("1", "Perfect Match", "game", ["linux"], installed=True),
            _make_game("2", "Not Installed", "game", ["linux"], installed=False),
            _make_game("3", "Wrong Platform", "game", ["windows"], installed=True),
        ]
        for key in ("soundtracks", "software", "videos", "dlcs", "tools"):
            service.toggle_type(key, False)
        service.toggle_platform("windows", False)
        service.toggle_platform("steamos", False)
        service.toggle_status("installed", True)

        result = service.apply(games)
        assert len(result) == 1
        assert result[0].app_id == "1"

    def test_empty_input(self, service: FilterService) -> None:
        """Applying filters to an empty list returns an empty list."""
        service.toggle_type("games", False)
        result = service.apply([])
        assert result == []


# ===========================================================================
# Language Filter Tests
# ===========================================================================


class TestLanguageFilter:
    """Tests for the language filter extension."""

    def test_toggle_language_adds_to_active(self, service: FilterService) -> None:
        """Toggling a language on adds it to active set."""
        service.toggle_language("english", True)
        state = service.state
        assert "english" in state.active_languages

    def test_toggle_language_removes_from_active(self, service: FilterService) -> None:
        """Toggling a language off removes it from active set."""
        service.toggle_language("english", True)
        service.toggle_language("english", False)
        state = service.state
        assert "english" not in state.active_languages

    def test_language_filter_single_language_filters(self, service: FilterService) -> None:
        """Single active language filters out games without that language."""
        game_en = _make_game("1", "English Game", languages=["english"])
        game_de = _make_game("2", "German Game", languages=["german"])
        game_both = _make_game("3", "Both Game", languages=["english", "german"])

        service.toggle_language("english", True)
        result = service.apply([game_en, game_de, game_both])

        assert len(result) == 2
        result_ids = {g.app_id for g in result}
        assert "1" in result_ids
        assert "3" in result_ids
        assert "2" not in result_ids

    def test_language_filter_multi_or_logic(self, service: FilterService) -> None:
        """Multiple active languages use OR logic (any match passes)."""
        game_en = _make_game("1", "English Game", languages=["english"])
        game_de = _make_game("2", "German Game", languages=["german"])
        game_fr = _make_game("3", "French Game", languages=["french"])

        service.toggle_language("english", True)
        service.toggle_language("german", True)
        result = service.apply([game_en, game_de, game_fr])

        assert len(result) == 2
        result_ids = {g.app_id for g in result}
        assert "1" in result_ids
        assert "2" in result_ids
        assert "3" not in result_ids

    def test_game_without_languages_passes_filter(self, service: FilterService) -> None:
        """Games without language data pass the filter (safe default)."""
        game_no_lang = _make_game("1", "No Language Data")
        service.toggle_language("english", True)

        result = service.apply([game_no_lang])
        assert len(result) == 1

    def test_no_active_languages_all_pass(self, service: FilterService) -> None:
        """When no language filter is active, all games pass."""
        game_en = _make_game("1", "English Game", languages=["english"])
        game_de = _make_game("2", "German Game", languages=["german"])

        result = service.apply([game_en, game_de])
        assert len(result) == 2

    def test_language_filter_in_has_active_filters(self, service: FilterService) -> None:
        """Active language filter makes has_active_filters() return True."""
        assert not service.has_active_filters()
        service.toggle_language("english", True)
        assert service.has_active_filters()

    def test_language_filter_state_restore(self, service: FilterService) -> None:
        """Language filter state is preserved through save/restore cycle."""
        service.toggle_language("german", True)
        service.toggle_language("japanese", True)
        state = service.state

        new_service = FilterService()
        new_service.restore_state(state)
        assert new_service.state.active_languages == frozenset({"german", "japanese"})
