# tests/unit/test_services/test_cloud_sync_config.py

"""Tests for cloud sync config fields: defaults, save, load."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(tmp_path: Path):
    # build a Config with DATA_DIR in tmp so no real FS side effects
    with patch("steam_library_manager.config.Config._find_steam_path", return_value=None):
        from steam_library_manager.config import Config

        cfg = Config.__new__(Config)
        cfg.DATA_DIR = tmp_path
        cfg.CACHE_DIR = tmp_path / "cache"
        cfg.SETTINGS_FILE = tmp_path / "settings.json"
        cfg.RESOURCES_DIR = Path(__file__).parent  # dummy
        cfg.ICONS_DIR = cfg.RESOURCES_DIR / "icons"
        cfg.APP_DIR = Path(__file__).parent

        # set all defaults manually so __post_init__ side effects are skipped
        cfg.UI_LANGUAGE = "en"
        cfg.TAGS_LANGUAGE = "en"
        cfg.DEFAULT_LOCALE = "en"
        cfg.THEME = "dark"
        cfg.STEAM_API_KEY = None
        cfg.STEAMGRIDDB_API_KEY = None
        cfg.STEAM_PATH = None
        cfg.STEAM_USER_ID = None
        cfg.STEAM_ACCESS_TOKEN = None
        cfg.STEAM_LIBRARIES = []
        cfg.EXPANDED_CATEGORIES = []
        cfg.MAX_BACKUPS = 5
        cfg.TAGS_PER_GAME = 13
        cfg.IGNORE_COMMON_TAGS = True
        cfg.UPDATE_CHECK_ON_STARTUP = True
        cfg.UPDATE_CHECK_INTERVAL = "weekly"
        cfg.UPDATE_LAST_CHECK = ""
        cfg.UPDATE_SKIPPED_VERSION = ""
        cfg.CLOUD_PROVIDER = ""
        cfg.CLOUD_SYNC_MODE = "manual"
        cfg.CLOUD_LAST_SYNC = ""
        cfg.CLOUD_LAST_CHECKSUM = ""
        cfg.CLOUD_WEBDAV_URL = ""

        cfg.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cfg.CACHE_DIR.mkdir(parents=True, exist_ok=True)

        return cfg


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCloudSyncConfigDefaults:
    # verify default values on a fresh Config

    def test_cloud_provider_default(self, tmp_path: Path):
        cfg = _make_config(tmp_path)
        assert cfg.CLOUD_PROVIDER == ""

    def test_cloud_sync_mode_default(self, tmp_path: Path):
        cfg = _make_config(tmp_path)
        assert cfg.CLOUD_SYNC_MODE == "manual"

    def test_cloud_last_sync_default(self, tmp_path: Path):
        cfg = _make_config(tmp_path)
        assert cfg.CLOUD_LAST_SYNC == ""

    def test_cloud_last_checksum_default(self, tmp_path: Path):
        cfg = _make_config(tmp_path)
        assert cfg.CLOUD_LAST_CHECKSUM == ""

    def test_cloud_webdav_url_default(self, tmp_path: Path):
        cfg = _make_config(tmp_path)
        assert cfg.CLOUD_WEBDAV_URL == ""


class TestCloudSyncConfigSave:
    # verify cloud fields are written to JSON on save()

    def test_save_includes_cloud_fields(self, tmp_path: Path):
        cfg = _make_config(tmp_path)
        cfg.CLOUD_PROVIDER = "webdav"
        cfg.CLOUD_SYNC_MODE = "auto_upload"
        cfg.CLOUD_LAST_SYNC = "2026-04-08T12:00:00Z"
        cfg.CLOUD_LAST_CHECKSUM = "abc123"
        cfg.CLOUD_WEBDAV_URL = "https://dav.example.com/slm/"

        cfg.save()

        raw = json.loads(cfg.SETTINGS_FILE.read_text("utf-8"))
        assert raw["cloud_provider"] == "webdav"
        assert raw["cloud_sync_mode"] == "auto_upload"
        assert raw["cloud_last_sync"] == "2026-04-08T12:00:00Z"
        assert raw["cloud_last_checksum"] == "abc123"
        assert raw["cloud_webdav_url"] == "https://dav.example.com/slm/"

    def test_save_empty_cloud_fields(self, tmp_path: Path):
        cfg = _make_config(tmp_path)
        cfg.save()

        raw = json.loads(cfg.SETTINGS_FILE.read_text("utf-8"))
        assert raw["cloud_provider"] == ""
        assert raw["cloud_sync_mode"] == "manual"


class TestCloudSyncConfigLoad:
    # verify cloud fields are loaded from JSON

    def test_load_cloud_fields(self, tmp_path: Path):
        cfg = _make_config(tmp_path)

        # write settings with cloud values
        settings = {
            "cloud_provider": "mega",
            "cloud_sync_mode": "full_auto",
            "cloud_last_sync": "2026-01-01T00:00:00Z",
            "cloud_last_checksum": "deadbeef",
            "cloud_webdav_url": "",
        }
        cfg.SETTINGS_FILE.write_text(json.dumps(settings), encoding="utf-8")

        cfg._load_settings()

        assert cfg.CLOUD_PROVIDER == "mega"
        assert cfg.CLOUD_SYNC_MODE == "full_auto"
        assert cfg.CLOUD_LAST_SYNC == "2026-01-01T00:00:00Z"
        assert cfg.CLOUD_LAST_CHECKSUM == "deadbeef"
        assert cfg.CLOUD_WEBDAV_URL == ""

    def test_load_missing_cloud_fields_keeps_defaults(self, tmp_path: Path):
        cfg = _make_config(tmp_path)

        # write settings WITHOUT any cloud keys
        cfg.SETTINGS_FILE.write_text(json.dumps({"ui_language": "de"}), encoding="utf-8")

        cfg._load_settings()

        assert cfg.CLOUD_PROVIDER == ""
        assert cfg.CLOUD_SYNC_MODE == "manual"
        assert cfg.CLOUD_LAST_SYNC == ""
        assert cfg.CLOUD_LAST_CHECKSUM == ""
        assert cfg.CLOUD_WEBDAV_URL == ""

    def test_roundtrip(self, tmp_path: Path):
        # save then load preserves values
        cfg = _make_config(tmp_path)
        cfg.CLOUD_PROVIDER = "webdav"
        cfg.CLOUD_SYNC_MODE = "full_auto"
        cfg.CLOUD_WEBDAV_URL = "https://my.server/dav/"
        cfg.save()

        cfg2 = _make_config(tmp_path)
        cfg2._load_settings()

        assert cfg2.CLOUD_PROVIDER == "webdav"
        assert cfg2.CLOUD_SYNC_MODE == "full_auto"
        assert cfg2.CLOUD_WEBDAV_URL == "https://my.server/dav/"
