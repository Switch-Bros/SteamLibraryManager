#
# tests/unit/test_ui/test_cloud_sync_settings.py
# Tests for CloudSyncSettingsTab widget
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from unittest.mock import MagicMock

from steam_library_manager.ui.dialogs.cloud_sync_settings import CloudSyncSettingsTab


class TestCloudSyncSettingsTab:
    def test_create_tab(self, qapp):
        tab = CloudSyncSettingsTab()
        assert tab is not None

    def test_has_provider_selection(self, qapp):
        tab = CloudSyncSettingsTab()
        assert hasattr(tab, "provider_group")

    def test_has_sync_mode(self, qapp):
        tab = CloudSyncSettingsTab()
        assert hasattr(tab, "mode_manual")
        assert hasattr(tab, "mode_auto_upload")
        assert hasattr(tab, "mode_full_auto")

    def test_get_settings_defaults(self, qapp):
        tab = CloudSyncSettingsTab()
        settings = tab.get_settings()
        assert settings["provider"] == "none"
        assert settings["sync_mode"] == "manual"

    def test_get_settings_has_all_keys(self, qapp):
        tab = CloudSyncSettingsTab()
        settings = tab.get_settings()
        assert "provider" in settings
        assert "sync_mode" in settings
        assert "webdav_url" in settings
        assert "webdav_user" in settings
        assert "webdav_pass" in settings
        assert "mega_email" in settings
        assert "mega_pass" in settings

    def test_select_webdav_provider(self, qapp):
        tab = CloudSyncSettingsTab()
        tab.radio_webdav.setChecked(True)
        settings = tab.get_settings()
        assert settings["provider"] == "webdav"

    def test_select_mega_provider(self, qapp):
        tab = CloudSyncSettingsTab()
        tab.radio_mega.setChecked(True)
        settings = tab.get_settings()
        assert settings["provider"] == "mega"

    def test_sync_mode_auto_upload(self, qapp):
        tab = CloudSyncSettingsTab()
        tab.mode_auto_upload.setChecked(True)
        settings = tab.get_settings()
        assert settings["sync_mode"] == "auto_upload"

    def test_sync_mode_full_auto(self, qapp):
        tab = CloudSyncSettingsTab()
        tab.mode_full_auto.setChecked(True)
        settings = tab.get_settings()
        assert settings["sync_mode"] == "full_auto"

    def test_load_settings(self, qapp):
        tab = CloudSyncSettingsTab()
        cfg = MagicMock()
        cfg.CLOUD_PROVIDER = "webdav"
        cfg.CLOUD_SYNC_MODE = "auto_upload"
        cfg.WEBDAV_URL = "https://example.com/dav"
        cfg.WEBDAV_USER = "testuser"
        cfg.WEBDAV_PASS = "secret"
        cfg.MEGA_EMAIL = ""
        cfg.MEGA_PASS = ""
        cfg.CLOUD_LAST_SYNC = None

        tab.load_settings(cfg)
        settings = tab.get_settings()
        assert settings["provider"] == "webdav"
        assert settings["sync_mode"] == "auto_upload"
        assert settings["webdav_url"] == "https://example.com/dav"
        assert settings["webdav_user"] == "testuser"

    def test_credential_stack_switches(self, qapp):
        tab = CloudSyncSettingsTab()
        # default: none -> page 0
        assert tab.cred_stack.currentIndex() == 0
        tab.radio_webdav.setChecked(True)
        assert tab.cred_stack.currentIndex() == 1
        tab.radio_mega.setChecked(True)
        assert tab.cred_stack.currentIndex() == 2
        tab.radio_none.setChecked(True)
        assert tab.cred_stack.currentIndex() == 0
