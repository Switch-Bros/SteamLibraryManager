#
# tests/unit/test_ui/test_cloud_sync_dialog.py
# Tests for CloudSyncDialog toolbar widget
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from steam_library_manager.ui.dialogs.cloud_sync_dialog import CloudSyncDialog


class TestCloudSyncDialog:
    def test_create_dialog(self, qapp):
        dlg = CloudSyncDialog()
        assert dlg is not None

    def test_has_upload_download_buttons(self, qapp):
        dlg = CloudSyncDialog()
        assert hasattr(dlg, "btn_upload")
        assert hasattr(dlg, "btn_download")

    def test_has_status_label(self, qapp):
        dlg = CloudSyncDialog()
        assert hasattr(dlg, "status_label")

    def test_return_codes(self, qapp):
        assert CloudSyncDialog.UPLOAD == 1
        assert CloudSyncDialog.DOWNLOAD == 2

    def test_buttons_exist_no_provider(self, qapp):
        # default config has no provider -> dialog still shows buttons
        dlg = CloudSyncDialog()
        assert dlg.btn_upload is not None
        assert dlg.btn_download is not None
