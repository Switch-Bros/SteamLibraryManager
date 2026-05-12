"""Tests for ExternalGamesService orchestrator."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from steam_library_manager.core.shortcuts_manager import ShortcutsManager
from steam_library_manager.integrations.external_games.models import ExternalGame
from steam_library_manager.services.external_games_service import ExternalGamesService


def _make_game(name: str, platform: str = "Heroic (Epic)") -> ExternalGame:
    """Create a test ExternalGame."""
    return ExternalGame(
        platform=platform,
        platform_app_id=f"id_{name}",
        name=name,
        launch_command=f"heroic://launch/{name}",
    )


class TestExternalGamesService:
    """Tests for the external games orchestrator."""

    def _make_service(self, tmp_path: Path) -> ExternalGamesService:
        """Create a service with a temp ShortcutsManager."""
        userdata = tmp_path / "userdata"
        (userdata / "99" / "config").mkdir(parents=True)
        mgr = ShortcutsManager(userdata, "99")
        return ExternalGamesService(mgr)

    def test_scan_all_platforms(self, tmp_path: Path) -> None:
        """Scan all platforms orchestrates all parsers."""
        service = self._make_service(tmp_path)

        # Mock all parsers to return known data
        mock_parser = MagicMock()
        mock_parser.is_available.return_value = True
        mock_parser.read_games.return_value = [_make_game("TestGame")]
        mock_parser.platform_name.return_value = "Mock"

        service._parsers = {"Mock": mock_parser}
        results = service.scan_all_platforms()

        assert "Mock" in results
        assert len(results["Mock"]) == 1

    def test_scan_unavailable_platforms_skipped(self, tmp_path: Path) -> None:
        """Unavailable platforms are skipped."""
        service = self._make_service(tmp_path)

        mock_parser = MagicMock()
        mock_parser.is_available.return_value = False
        service._parsers = {"Mock": mock_parser}

        results = service.scan_all_platforms()
        assert results == {}
        mock_parser.read_games.assert_not_called()

    def test_duplicate_detection(self, tmp_path: Path) -> None:
        """Games already in shortcuts.vdf are detected."""
        service = self._make_service(tmp_path)

        # Add a game first
        game = _make_game("Existing")
        service.add_to_steam(game)

        existing = service.get_existing_shortcuts()
        assert "existing" in existing  # lowercase

    def test_add_creates_shortcut(self, tmp_path: Path) -> None:
        """Adding a game creates a shortcuts.vdf entry."""
        service = self._make_service(tmp_path)
        game = _make_game("New Game")

        result = service.add_to_steam(game)
        assert result is True

        shortcuts = service._shortcuts_mgr.read_shortcuts()
        assert len(shortcuts) == 1
        assert shortcuts[0].app_name == "New Game"

    def test_add_duplicate_returns_false(self, tmp_path: Path) -> None:
        """Adding a duplicate game returns False."""
        service = self._make_service(tmp_path)
        game = _make_game("Dupe")

        assert service.add_to_steam(game) is True
        assert service.add_to_steam(game) is False

    def test_batch_add_progress(self, tmp_path: Path) -> None:
        """Batch add reports progress through callback."""
        service = self._make_service(tmp_path)
        games = [_make_game("A"), _make_game("B"), _make_game("C")]

        progress_calls: list[tuple[int, int, str]] = []
        service.batch_add_to_steam(
            games,
            progress_callback=lambda c, t, n: progress_calls.append((c, t, n)),
        )

        assert len(progress_calls) == 3
        assert progress_calls[0] == (1, 3, "A")
        assert progress_calls[2] == (3, 3, "C")

    def test_batch_add_stats(self, tmp_path: Path) -> None:
        """Batch add returns correct statistics."""
        service = self._make_service(tmp_path)
        # Pre-add "Existing" to trigger skip
        service.add_to_steam(_make_game("Existing"))

        games = [_make_game("New"), _make_game("Existing")]
        stats = service.batch_add_to_steam(games)

        assert stats["added"] == 1
        assert stats["skipped"] == 1
        assert stats["errors"] == 0

    def test_add_with_category_tag(self, tmp_path: Path) -> None:
        """Category tag is stored in shortcut tags."""
        service = self._make_service(tmp_path)
        game = _make_game("Tagged", platform="Heroic (GOG)")

        service.add_to_steam(game, category_tag="GOG Games")

        shortcuts = service._shortcuts_mgr.read_shortcuts()
        assert shortcuts[0].tags == {"0": "GOG Games"}

    def test_remove_from_steam(self, tmp_path: Path) -> None:
        """Remove deletes a shortcut."""
        service = self._make_service(tmp_path)
        service.add_to_steam(_make_game("ToRemove"))

        assert service.remove_from_steam("ToRemove") is True
        assert len(service._shortcuts_mgr.read_shortcuts()) == 0

    def test_get_available_platforms(self, tmp_path: Path) -> None:
        """Available platforms are correctly detected."""
        service = self._make_service(tmp_path)

        available = MagicMock()
        available.is_available.return_value = True
        unavailable = MagicMock()
        unavailable.is_available.return_value = False

        service._parsers = {"Yes": available, "No": unavailable}
        assert service.get_available_platforms() == ["Yes"]

    def test_heroic_sideload_parser_registered(self, tmp_path: Path) -> None:
        """Heroic (Sideload) parser is registered in ExternalGamesService."""
        service = self._make_service(tmp_path)
        assert "Heroic (Sideload)" in service._parsers


class TestCoverFallback:
    """Tests for SteamGridDB -> cover_url_hint fallback chain."""

    def _make_service(self, tmp_path: Path) -> ExternalGamesService:
        userdata = tmp_path / "userdata"
        (userdata / "99" / "config").mkdir(parents=True)
        mgr = ShortcutsManager(userdata, "99")
        return ExternalGamesService(mgr)

    def _make_game(self, name: str = "X", cover_hint: str | None = None) -> ExternalGame:
        return ExternalGame(
            platform="Heroic (Sideload)",
            platform_app_id="abc",
            name=name,
            executable="/p/x.exe",
            launch_command="heroic://launch/abc?runner=sideload",
            cover_url_hint=cover_hint,
        )

    def test_uses_steamgriddb_when_search_succeeds(self, tmp_path: Path) -> None:
        """When SteamGridDB returns a result, that cover URL is used."""
        from unittest.mock import patch

        svc = self._make_service(tmp_path)
        game = self._make_game(name="WarCraft 2", cover_hint="https://heroic.example/c.png")

        fake_results = [{"id": 99, "name": "WarCraft 2"}]
        fake_grid = [{"url": "https://gridurl/x.png"}]

        with patch("steam_library_manager.services.external_games_service.SteamGridDB") as MockGrid:
            grid_inst = MockGrid.return_value
            grid_inst.api_key = "fake-key"
            grid_inst.search_games_by_name.return_value = fake_results
            grid_inst.get_images_by_type_paged.return_value = fake_grid

            with patch(
                "steam_library_manager.services.external_games_service.SteamAssets.save_custom_image"
            ) as save_img:
                save_img.return_value = True
                svc._try_fetch_cover(appid=12345, game=game)

            save_img.assert_called_once()
            args, _ = save_img.call_args
            assert args[2] == "https://gridurl/x.png"

    def test_falls_back_to_hint_when_steamgriddb_empty(self, tmp_path: Path) -> None:
        """When SteamGridDB returns no results, cover_url_hint is used."""
        from unittest.mock import patch

        svc = self._make_service(tmp_path)
        game = self._make_game(name="Obscure App", cover_hint="https://heroic.example/c.png")

        with patch("steam_library_manager.services.external_games_service.SteamGridDB") as MockGrid:
            grid_inst = MockGrid.return_value
            grid_inst.api_key = "fake-key"
            grid_inst.search_games_by_name.return_value = []

            with patch(
                "steam_library_manager.services.external_games_service.SteamAssets.save_custom_image"
            ) as save_img:
                save_img.return_value = True
                svc._try_fetch_cover(appid=12345, game=game)

            save_img.assert_called_once()
            args, _ = save_img.call_args
            assert args[2] == "https://heroic.example/c.png"

    def test_no_cover_when_both_fail(self, tmp_path: Path) -> None:
        """SteamGridDB empty + no cover_url_hint -> save_custom_image NOT called."""
        from unittest.mock import patch

        svc = self._make_service(tmp_path)
        game = self._make_game(name="X", cover_hint=None)

        with patch("steam_library_manager.services.external_games_service.SteamGridDB") as MockGrid:
            grid_inst = MockGrid.return_value
            grid_inst.api_key = "fake-key"
            grid_inst.search_games_by_name.return_value = []

            with patch(
                "steam_library_manager.services.external_games_service.SteamAssets.save_custom_image"
            ) as save_img:
                svc._try_fetch_cover(appid=12345, game=game)

            save_img.assert_not_called()
