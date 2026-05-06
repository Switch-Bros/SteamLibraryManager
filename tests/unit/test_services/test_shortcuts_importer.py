"""Tests for ShortcutsImporter and CategoryService shortcut bidirection."""

from __future__ import annotations

from unittest.mock import MagicMock

from steam_library_manager.core.game import Game
from steam_library_manager.core.shortcuts_manager import SteamShortcut
from steam_library_manager.services.category_service import CategoryService
from steam_library_manager.services.shortcuts_importer import ShortcutsImporter


class FakeGameManager:
    def __init__(self) -> None:
        self.games: dict = {}

    def get_games_by_category(self, c: str):
        return [g for g in self.games.values() if c in g.categories]

    def get_all_categories(self):
        return {}


class TestShortcutsImporter:
    def test_imports_shortcuts_with_tags(self) -> None:
        sc = SteamShortcut(
            appid=-2093307729,
            app_name="Metroid Dread",
            exe='"/home/u/Eden.AppImage" "/roms/Metroid Dread.nsp"',
            start_dir="",
            icon="",
            launch_options="",
            tags={"0": "Nintendo Switch"},
        )
        mgr = MagicMock()
        mgr.read_shortcuts.return_value = [sc]
        importer = ShortcutsImporter(mgr)
        games = importer.read_games()
        assert len(games) == 1
        g = games[0]
        # canonical app_id is the unsigned uint32 form (2201659567 = -2093307729 & 0xFFFFFFFF)
        assert g.app_id == "2201659567"
        assert g.name == "Metroid Dread"
        assert g.is_shortcut is True
        assert g.categories == ["Nintendo Switch"]
        assert "Eden.AppImage" in g.shortcut_exe

    def test_skips_unnamed_entries(self) -> None:
        sc = SteamShortcut(appid=1, app_name="", exe="", start_dir="", icon="", launch_options="", tags={})
        mgr = MagicMock()
        mgr.read_shortcuts.return_value = [sc]
        importer = ShortcutsImporter(mgr)
        assert importer.read_games() == []

    def test_multiple_tags_preserved_in_order(self) -> None:
        sc = SteamShortcut(
            appid=-1,
            app_name="Test",
            exe="",
            start_dir="",
            icon="",
            launch_options="",
            tags={"0": "A", "1": "B", "2": "C"},
        )
        mgr = MagicMock()
        mgr.read_shortcuts.return_value = [sc]
        games = ShortcutsImporter(mgr).read_games()
        assert games[0].categories == ["A", "B", "C"]

    def test_unreadable_shortcuts_returns_empty(self) -> None:
        mgr = MagicMock()
        mgr.read_shortcuts.side_effect = OSError("boom")
        assert ShortcutsImporter(mgr).read_games() == []


class TestCategoryServiceShortcutPath:
    def test_add_category_to_shortcut_writes_to_vdf_and_cloud(self) -> None:
        # canonical id for Test is unsigned (4294967196 = -100 & 0xFFFFFFFF)
        unsigned = "4294967196"
        gm = FakeGameManager()
        gm.games[unsigned] = Game(app_id=unsigned, name="Test", is_shortcut=True, categories=[])

        sc = SteamShortcut(appid=-100, app_name="Test", exe="", start_dir="", icon="", launch_options="", tags={})
        mgr = MagicMock()
        mgr.read_shortcuts.return_value = [sc]
        mgr.update_shortcut.return_value = True

        cloud = MagicMock()
        cloud.modified = True

        svc = CategoryService(localconfig_helper=None, cloud_parser=cloud, game_manager=gm, shortcuts_manager=mgr)

        ok = svc.add_app_to_category(unsigned, "MyCollection")
        assert ok is True

        # shortcuts.vdf was updated with the new tag
        mgr.update_shortcut.assert_called_once()
        updated = mgr.update_shortcut.call_args[0][0]
        assert updated.tags == {"0": "MyCollection"}
        # cloud-storage was also updated and saved (so Steam shows the collection)
        cloud.add_app_category.assert_called_once_with(unsigned, "MyCollection")
        cloud.save.assert_called_once()

    def test_remove_category_from_shortcut_writes_to_vdf(self) -> None:
        unsigned = "4294967196"
        gm = FakeGameManager()
        gm.games[unsigned] = Game(app_id=unsigned, name="Test", is_shortcut=True, categories=["A", "B"])

        sc = SteamShortcut(
            appid=-100,
            app_name="Test",
            exe="",
            start_dir="",
            icon="",
            launch_options="",
            tags={"0": "A", "1": "B"},
        )
        mgr = MagicMock()
        mgr.read_shortcuts.return_value = [sc]
        mgr.update_shortcut.return_value = True

        svc = CategoryService(localconfig_helper=None, cloud_parser=MagicMock(), game_manager=gm, shortcuts_manager=mgr)

        ok = svc.remove_app_from_category(unsigned, "A")
        assert ok is True
        updated = mgr.update_shortcut.call_args[0][0]
        assert updated.tags == {"0": "B"}

    def test_add_category_to_steam_app_uses_cloud_storage(self) -> None:
        # regular Steam apps must keep using the cloud parser
        gm = FakeGameManager()
        gm.games[440] = Game(app_id="440", name="Team Fortress 2", is_shortcut=False, categories=[])

        cloud = MagicMock()
        mgr = MagicMock()

        svc = CategoryService(localconfig_helper=None, cloud_parser=cloud, game_manager=gm, shortcuts_manager=mgr)
        svc.add_app_to_category(440, "FPS")
        cloud.add_app_category.assert_called_once_with(440, "FPS")
        mgr.update_shortcut.assert_not_called()

    def test_rename_category_persists_for_shortcut(self) -> None:
        unsigned = "4294967196"
        gm = FakeGameManager()
        gm.games[unsigned] = Game(app_id=unsigned, name="Test", is_shortcut=True, categories=["OldName"])
        sc = SteamShortcut(
            appid=-100,
            app_name="Test",
            exe="",
            start_dir="",
            icon="",
            launch_options="",
            tags={"0": "OldName"},
        )
        mgr = MagicMock()
        mgr.read_shortcuts.return_value = [sc]
        mgr.update_shortcut.return_value = True

        cloud = MagicMock()
        cloud.get_all_categories.return_value = []

        svc = CategoryService(localconfig_helper=None, cloud_parser=cloud, game_manager=gm, shortcuts_manager=mgr)
        svc.rename_category("OldName", "NewName")

        # game state updated
        assert gm.games[unsigned].categories == ["NewName"]
        # shortcut.vdf rewritten
        mgr.update_shortcut.assert_called_once()
        updated = mgr.update_shortcut.call_args[0][0]
        assert updated.tags == {"0": "NewName"}

    def test_delete_category_persists_for_shortcut(self) -> None:
        unsigned = "4294967196"
        gm = FakeGameManager()
        gm.games[unsigned] = Game(app_id=unsigned, name="Test", is_shortcut=True, categories=["Doomed", "Stays"])
        sc = SteamShortcut(
            appid=-100,
            app_name="Test",
            exe="",
            start_dir="",
            icon="",
            launch_options="",
            tags={"0": "Doomed", "1": "Stays"},
        )
        mgr = MagicMock()
        mgr.read_shortcuts.return_value = [sc]
        mgr.update_shortcut.return_value = True

        svc = CategoryService(localconfig_helper=None, cloud_parser=MagicMock(), game_manager=gm, shortcuts_manager=mgr)
        svc.delete_category("Doomed")

        assert gm.games[unsigned].categories == ["Stays"]
        mgr.update_shortcut.assert_called_once()
        updated = mgr.update_shortcut.call_args[0][0]
        assert updated.tags == {"0": "Stays"}
