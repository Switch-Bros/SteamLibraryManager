# tests/unit/test_core/test_appinfo_manager_drift.py

"""Unit tests for AppInfoManager drift detection and auto-reapply.

Steam regularly overwrites appinfo.vdf with fresh server data, wiping out
the user's metadata edits. The AppInfoManager.verify_and_reapply() method
detects that drift and re-applies modifications. These tests cover the
core logic without touching the binary VDF format.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def manager(tmp_path: Path, monkeypatch):
    # Build an AppInfoManager whose data dir lives in tmp_path
    from steam_library_manager.config import config
    from steam_library_manager.core.appinfo_manager import AppInfoManager

    monkeypatch.setattr(config, "DATA_DIR", tmp_path)

    mgr = AppInfoManager()
    return mgr


class TestHasDrifted:
    """Pure-function check on _has_drifted - no filesystem needed."""

    def test_returns_false_when_no_modifications(self):
        from steam_library_manager.core.appinfo_manager import AppInfoManager

        common = {"name": "X", "developer": "Y"}
        assert AppInfoManager._has_drifted(common, {}) is False

    def test_detects_name_drift(self):
        from steam_library_manager.core.appinfo_manager import AppInfoManager

        common = {"name": "The LEGO Movie - Videogame"}
        modified = {"name": "LEGO Movie - Videogame"}
        assert AppInfoManager._has_drifted(common, modified) is True

    def test_no_drift_when_name_matches(self):
        from steam_library_manager.core.appinfo_manager import AppInfoManager

        common = {"name": "LEGO Movie - Videogame"}
        modified = {"name": "LEGO Movie - Videogame"}
        assert AppInfoManager._has_drifted(common, modified) is False

    def test_detects_release_date_drift_via_steam_release_date(self):
        from steam_library_manager.core.appinfo_manager import AppInfoManager

        common = {"steam_release_date": "1234567890"}
        modified = {"release_date": "9876543210"}
        assert AppInfoManager._has_drifted(common, modified) is True

    def test_release_date_falls_back_to_release_date_field(self):
        from steam_library_manager.core.appinfo_manager import AppInfoManager

        # Some games carry release_date but no steam_release_date
        common = {"release_date": "1234"}
        modified = {"release_date": "1234"}
        assert AppInfoManager._has_drifted(common, modified) is False

    def test_detects_developer_drift(self):
        from steam_library_manager.core.appinfo_manager import AppInfoManager

        common = {"name": "OK", "developer": "Old Dev"}
        modified = {"developer": "New Dev"}
        assert AppInfoManager._has_drifted(common, modified) is True

    def test_unrelated_modified_keys_are_ignored(self):
        from steam_library_manager.core.appinfo_manager import AppInfoManager

        # Keys we do not push into appinfo (e.g. pegi_rating, sort_as) must
        # not trigger drift on their own.
        common = {"name": "OK"}
        modified = {"pegi_rating": "16", "sort_as": "OK"}
        assert AppInfoManager._has_drifted(common, modified) is False


class TestVerifyAndReapply:
    """End-to-end logic without parsing the real binary."""

    def test_returns_zero_when_no_appinfo_loaded(self, manager):
        manager.appinfo = None
        manager.modifications = {"640590": {"modified": {"name": "X"}}}
        assert manager.verify_and_reapply() == 0

    def test_returns_zero_when_no_modifications(self, manager):
        manager.appinfo = MagicMock()
        manager.modifications = {}
        assert manager.verify_and_reapply() == 0

    def test_reapplies_when_binary_drifted(self, manager):
        # Simulate Steam having overwritten the binary back to the original
        # name while custom_metadata.json still has the user's edit.
        fake_appinfo = MagicMock()
        fake_appinfo.apps = {
            640590: {
                "data": {
                    "appinfo": {
                        "common": {"name": "The LEGO NINJAGO Movie Video Game"},
                    }
                }
            }
        }

        manager.appinfo = fake_appinfo
        manager.appinfo_path = Path("/dev/null")  # write_to_vdf is mocked below
        manager.modifications = {
            "640590": {
                "original": {"name": "The LEGO NINJAGO Movie Video Game"},
                "modified": {"name": "LEGO NINJAGO Movie Video Game"},
            }
        }

        # Stub write_to_vdf so we don't touch real backups/disk
        manager.write_to_vdf = MagicMock(return_value=True)

        count = manager.verify_and_reapply()

        assert count == 1
        fake_appinfo.update_app_metadata.assert_called_once_with(640590, {"name": "LEGO NINJAGO Movie Video Game"})
        manager.write_to_vdf.assert_called_once_with(backup=True)
        assert manager.vdf_dirty is False or manager.write_to_vdf.called

    def test_no_reapply_when_binary_already_matches(self, manager):
        fake_appinfo = MagicMock()
        fake_appinfo.apps = {
            640590: {
                "data": {
                    "appinfo": {
                        "common": {"name": "LEGO NINJAGO Movie Video Game"},
                    }
                }
            }
        }

        manager.appinfo = fake_appinfo
        manager.modifications = {
            "640590": {
                "original": {"name": "The LEGO NINJAGO Movie Video Game"},
                "modified": {"name": "LEGO NINJAGO Movie Video Game"},
            }
        }
        manager.write_to_vdf = MagicMock(return_value=True)

        count = manager.verify_and_reapply()

        assert count == 0
        fake_appinfo.update_app_metadata.assert_not_called()
        manager.write_to_vdf.assert_not_called()

    def test_skips_apps_missing_from_appinfo(self, manager):
        fake_appinfo = MagicMock()
        fake_appinfo.apps = {}  # game has been uninstalled / never present

        manager.appinfo = fake_appinfo
        manager.modifications = {
            "640590": {
                "modified": {"name": "LEGO NINJAGO Movie Video Game"},
            }
        }
        manager.write_to_vdf = MagicMock(return_value=True)

        count = manager.verify_and_reapply()

        assert count == 0
        manager.write_to_vdf.assert_not_called()

    def test_handles_three_lego_games_partial_drift(self, manager):
        # Two are drifted, one is already in sync
        fake_appinfo = MagicMock()
        fake_appinfo.apps = {
            267530: {"data": {"common": {"name": "The LEGO Movie - Videogame"}}},  # drifted
            881320: {"data": {"common": {"name": "The LEGO Movie 2 - Videogame"}}},  # drifted
            640590: {"data": {"common": {"name": "LEGO NINJAGO Movie Video Game"}}},  # ok
        }

        manager.appinfo = fake_appinfo
        manager.modifications = {
            "267530": {"modified": {"name": "LEGO Movie - Videogame"}},
            "881320": {"modified": {"name": "LEGO Movie 2 - Videogame"}},
            "640590": {"modified": {"name": "LEGO NINJAGO Movie Video Game"}},
        }
        manager.write_to_vdf = MagicMock(return_value=True)

        count = manager.verify_and_reapply()

        assert count == 2
        # Exactly the two drifted apps were re-applied
        called_app_ids = {call.args[0] for call in fake_appinfo.update_app_metadata.call_args_list}
        assert called_app_ids == {267530, 881320}

    def test_handles_invalid_app_id_strings(self, manager):
        fake_appinfo = MagicMock()
        fake_appinfo.apps = {640590: {"data": {"common": {"name": "X"}}}}

        manager.appinfo = fake_appinfo
        manager.modifications = {
            "not_a_number": {"modified": {"name": "Y"}},
            "640590": {"modified": {"name": "X"}},
        }
        manager.write_to_vdf = MagicMock(return_value=True)

        # No crash, no spurious re-apply
        count = manager.verify_and_reapply()
        assert count == 0


class TestSaveAppinfoTriggersWrite:
    """Fix 2: save_appinfo must persist the binary VDF immediately."""

    def test_save_appinfo_writes_vdf_when_dirty(self, manager, tmp_path):
        manager.appinfo = MagicMock()
        manager.vdf_dirty = True
        manager.metadata_file = tmp_path / "custom_metadata.json"
        manager.write_to_vdf = MagicMock(return_value=True)

        manager.save_appinfo()

        manager.write_to_vdf.assert_called_once_with(backup=True)

    def test_save_appinfo_skips_vdf_write_when_clean(self, manager, tmp_path):
        manager.appinfo = MagicMock()
        manager.vdf_dirty = False
        manager.metadata_file = tmp_path / "custom_metadata.json"
        manager.write_to_vdf = MagicMock(return_value=True)

        manager.save_appinfo()

        manager.write_to_vdf.assert_not_called()
