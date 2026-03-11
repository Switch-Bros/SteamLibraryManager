# tests/test_config_library_sync.py

"""Tests for Config._sync_library_folders()."""

from unittest.mock import patch

import pytest


@pytest.fixture
def config_with_sync(tmp_path):
    """Create a minimal Config-like object for testing _sync_library_folders.

    Uses a real Config instance with mocked paths to avoid side effects.
    """
    from steam_library_manager.config import Config

    steam_path = tmp_path / "steam"
    steam_path.mkdir()
    steamapps = steam_path / "steamapps"
    steamapps.mkdir()

    # Create a valid libraryfolders.vdf
    vdf_content = """"libraryfolders"
{
    "0"
    {
        "path"  "%s"
    }
}""" % str(steam_path)
    (steamapps / "libraryfolders.vdf").write_text(vdf_content)

    # Build a Config without triggering full __post_init__
    with patch.object(Config, "__post_init__", lambda self: None):
        cfg = Config()

    cfg.STEAM_PATH = steam_path
    cfg.STEAM_LIBRARIES = []
    cfg.DATA_DIR = tmp_path / "data"
    cfg.DATA_DIR.mkdir()

    return cfg, steam_path


def test_sync_removes_dead_paths(config_with_sync):
    """Dead paths are removed, existing paths are kept."""
    cfg, steam_path = config_with_sync

    existing_lib = str(steam_path)
    dead_lib = "/mnt/old_hdd/SteamLibrary"

    cfg.STEAM_LIBRARIES = [existing_lib, dead_lib]

    with patch.object(cfg, "save"):
        cfg._sync_library_folders()

    assert existing_lib in cfg.STEAM_LIBRARIES
    assert dead_lib not in cfg.STEAM_LIBRARIES


def test_sync_adds_new_steam_paths(config_with_sync, tmp_path):
    """Paths from libraryfolders.vdf not in settings are added."""
    cfg, steam_path = config_with_sync

    # Add a second library to the vdf
    new_lib = tmp_path / "new_library"
    new_lib.mkdir()

    vdf_content = """"libraryfolders"
{
    "0"
    {
        "path"  "%s"
    }
    "1"
    {
        "path"  "%s"
    }
}""" % (str(steam_path), str(new_lib))
    (steam_path / "steamapps" / "libraryfolders.vdf").write_text(vdf_content)

    cfg.STEAM_LIBRARIES = [str(steam_path)]

    with patch.object(cfg, "save"):
        cfg._sync_library_folders()

    assert str(new_lib) in cfg.STEAM_LIBRARIES
    assert str(steam_path) in cfg.STEAM_LIBRARIES


def test_sync_no_changes_when_in_sync(config_with_sync):
    """No save() call when saved and detected paths match."""
    cfg, steam_path = config_with_sync

    cfg.STEAM_LIBRARIES = [str(steam_path)]

    with patch.object(cfg, "save") as mock_save:
        cfg._sync_library_folders()

    mock_save.assert_not_called()


def test_sync_handles_both_dead_and_new(config_with_sync, tmp_path):
    """Dead paths removed AND new paths added in one pass."""
    cfg, steam_path = config_with_sync

    new_lib = tmp_path / "new_ssd"
    new_lib.mkdir()

    vdf_content = """"libraryfolders"
{
    "0"
    {
        "path"  "%s"
    }
    "1"
    {
        "path"  "%s"
    }
}""" % (str(steam_path), str(new_lib))
    (steam_path / "steamapps" / "libraryfolders.vdf").write_text(vdf_content)

    dead_path = "/mnt/dead_volume/SteamLibrary"
    cfg.STEAM_LIBRARIES = [str(steam_path), dead_path]

    with patch.object(cfg, "save"):
        cfg._sync_library_folders()

    assert str(steam_path) in cfg.STEAM_LIBRARIES
    assert str(new_lib) in cfg.STEAM_LIBRARIES
    assert dead_path not in cfg.STEAM_LIBRARIES


def test_sync_skipped_when_no_steam_path(config_with_sync):
    """No sync attempted when STEAM_PATH is None."""
    cfg, _ = config_with_sync

    cfg.STEAM_PATH = None
    cfg.STEAM_LIBRARIES = ["/mnt/fake/path"]

    with patch.object(cfg, "save") as mock_save:
        cfg._sync_library_folders()

    # _detect_library_folders returns [] when STEAM_PATH is None, so no changes
    mock_save.assert_not_called()
    assert cfg.STEAM_LIBRARIES == ["/mnt/fake/path"]


def test_sync_skipped_when_vdf_missing(config_with_sync):
    """Graceful no-op when libraryfolders.vdf doesn't exist."""
    cfg, steam_path = config_with_sync

    # Remove the vdf file
    vdf_path = steam_path / "steamapps" / "libraryfolders.vdf"
    vdf_path.unlink()

    cfg.STEAM_LIBRARIES = ["/mnt/old/path"]

    with patch.object(cfg, "save") as mock_save:
        cfg._sync_library_folders()

    mock_save.assert_not_called()
    assert cfg.STEAM_LIBRARIES == ["/mnt/old/path"]


def test_sync_ignores_dead_vdf_paths(config_with_sync):
    """Paths in libraryfolders.vdf that don't exist on disk are NOT added.

    Steam keeps dead paths in libraryfolders.vdf until manually removed.
    SLM must not re-add them.
    """
    cfg, steam_path = config_with_sync

    # VDF lists a path that doesn't exist on disk (dead drive)
    vdf_content = """"libraryfolders"
{
    "0"
    {
        "path"  "%s"
    }
    "1"
    {
        "path"  "/mnt/dead_drive/SteamLibrary"
    }
}""" % str(steam_path)
    (steam_path / "steamapps" / "libraryfolders.vdf").write_text(vdf_content)

    cfg.STEAM_LIBRARIES = [str(steam_path)]

    with patch.object(cfg, "save") as mock_save:
        cfg._sync_library_folders()

    assert str(steam_path) in cfg.STEAM_LIBRARIES
    assert "/mnt/dead_drive/SteamLibrary" not in cfg.STEAM_LIBRARIES
    mock_save.assert_not_called()
