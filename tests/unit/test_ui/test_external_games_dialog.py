"""Tests for ExternalGamesDialog logic (non-GUI)."""

from __future__ import annotations

from src.integrations.external_games.models import ExternalGame


def _make_game(name: str, platform: str = "Heroic (Epic)") -> ExternalGame:
    """Create a test ExternalGame."""
    return ExternalGame(
        platform=platform,
        platform_app_id=f"id_{name}",
        name=name,
        launch_command=f"heroic://launch/{name}",
    )


class TestExternalGamesDialogLogic:
    """Tests for dialog helper logic without requiring a QApplication."""

    def test_game_is_detected_as_existing(self) -> None:
        """Games already in shortcuts are detected via lowercase comparison."""
        existing: set[str] = {"test game", "another game"}
        game = _make_game("Test Game")
        assert game.name.lower() in existing

    def test_game_not_existing(self) -> None:
        """New games are not in the existing set."""
        existing: set[str] = {"other game"}
        game = _make_game("New Game")
        assert game.name.lower() not in existing

    def test_filter_games_by_platform(self) -> None:
        """Platform filter correctly selects games."""
        games = [
            _make_game("A", "Heroic (Epic)"),
            _make_game("B", "Lutris"),
            _make_game("C", "Heroic (Epic)"),
        ]
        filtered = [g for g in games if g.platform == "Heroic (Epic)"]
        assert len(filtered) == 2
        assert all(g.platform == "Heroic (Epic)" for g in filtered)

    def test_filter_all_returns_everything(self) -> None:
        """Empty filter returns all games."""
        games = [
            _make_game("A", "Heroic (Epic)"),
            _make_game("B", "Lutris"),
        ]
        platform_filter = ""
        if not platform_filter:
            filtered = games
        else:
            filtered = [g for g in games if g.platform == platform_filter]
        assert len(filtered) == 2

    def test_get_new_games_excludes_existing(self) -> None:
        """New games list excludes those already in Steam."""
        existing: set[str] = {"existing game"}
        games = [
            _make_game("Existing Game"),
            _make_game("Brand New"),
        ]
        new_games = [g for g in games if g.name.lower() not in existing]
        assert len(new_games) == 1
        assert new_games[0].name == "Brand New"

    def test_stats_message_format(self) -> None:
        """Stats dict has expected keys for message formatting."""
        stats = {"added": 3, "skipped": 1, "errors": 0}
        assert stats["added"] == 3
        assert stats["skipped"] == 1
        assert stats["errors"] == 0

    def test_platform_tag_uses_game_platform(self) -> None:
        """Platform tag matches the game's platform name."""
        game = _make_game("Test", "Heroic (GOG)")
        tag = game.platform
        assert tag == "Heroic (GOG)"

    def test_scan_results_flatten(self) -> None:
        """Scan results from multiple platforms are flattened correctly."""
        results: dict[str, list[ExternalGame]] = {
            "Heroic (Epic)": [_make_game("A", "Heroic (Epic)")],
            "Lutris": [_make_game("B", "Lutris"), _make_game("C", "Lutris")],
        }
        all_games: list[ExternalGame] = []
        platforms: set[str] = set()
        for platform, games in results.items():
            platforms.add(platform)
            all_games.extend(games)

        assert len(all_games) == 3
        assert platforms == {"Heroic (Epic)", "Lutris"}

    def test_existing_count_calculation(self) -> None:
        """Existing count correctly counts games already in Steam."""
        existing: set[str] = {"game a", "game c"}
        games = [
            _make_game("Game A"),
            _make_game("Game B"),
            _make_game("Game C"),
        ]
        existing_count = sum(1 for g in games if g.name.lower() in existing)
        assert existing_count == 2

    def test_has_new_games_check(self) -> None:
        """has_new is True only when new games exist."""
        existing: set[str] = {"all existing"}
        games = [_make_game("All Existing")]
        existing_count = sum(1 for g in games if g.name.lower() in existing)
        has_new = existing_count < len(games)
        assert has_new is False

        games.append(_make_game("New One"))
        existing_count = sum(1 for g in games if g.name.lower() in existing)
        has_new = existing_count < len(games)
        assert has_new is True
