# tests/unit/test_services/test_mega_provider.py

"""Unit tests for MegaProvider with mocked mega.py."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# -- fixtures --


@pytest.fixture()
def mock_mega_cls():
    """Patch mega.Mega and return the mock class."""
    with patch("steam_library_manager.services.cloud_sync.mega_provider.Mega") as cls:
        inst = MagicMock()
        # Mega().login() returns the logged-in api object
        login_result = MagicMock()
        inst.login.return_value = login_result
        cls.return_value = inst
        yield cls


@pytest.fixture()
def mock_api(mock_mega_cls):
    """Return the mock mega api object (result of Mega().login())."""
    return mock_mega_cls.return_value.login.return_value


@pytest.fixture()
def provider(mock_mega_cls):
    """Create a MegaProvider that uses the mocked Mega."""
    from steam_library_manager.services.cloud_sync.mega_provider import (
        MegaProvider,
    )

    p = MegaProvider("user@example.com", "secret")
    return p


# -- connect / disconnect --


class TestConnect:
    def test_connect_success(self, provider, mock_api):
        assert provider.connect()
        assert provider.is_connected()

    def test_connect_login_raises(self, provider, mock_mega_cls):
        inst = mock_mega_cls.return_value
        inst.login.side_effect = RuntimeError("bad credentials")
        assert not provider.connect()
        assert not provider.is_connected()

    def test_disconnect(self, provider, mock_api):
        provider.connect()
        provider.disconnect()
        assert not provider.is_connected()


# -- upload --


class TestUpload:
    def test_upload_success(self, provider, mock_api, tmp_path: Path):
        provider.connect()

        src = tmp_path / "data.db"
        src.write_bytes(b"payload")

        # folder exists, no existing file
        folder_handle = "folder_h"
        folder_node = {"t": 1}
        mock_api.find.side_effect = [
            (folder_handle, folder_node),  # _find_or_create_folder
            None,  # check for existing file
        ]

        assert provider.upload_file(src, "data.db")
        mock_api.upload.assert_called_once_with(str(src), folder_handle)

    def test_upload_creates_folder(self, provider, mock_api, tmp_path: Path):
        provider.connect()

        src = tmp_path / "test.txt"
        src.write_text("hello")

        # folder does not exist -> create it
        mock_api.find.side_effect = [
            None,  # _find_or_create_folder: not found
            None,  # check for existing file
        ]
        mock_api.create_folder.return_value = {"SteamLibraryManager": ("new_h", {"t": 1})}

        assert provider.upload_file(src, "test.txt")
        mock_api.create_folder.assert_called_once_with("SteamLibraryManager")

    def test_upload_deletes_existing(self, provider, mock_api, tmp_path: Path):
        provider.connect()

        src = tmp_path / "update.db"
        src.write_bytes(b"new data")

        folder_handle = "folder_h"
        folder_node = {"t": 1}
        existing_handle = "old_file_h"
        existing_node = {"s": 100}

        mock_api.find.side_effect = [
            (folder_handle, folder_node),  # folder lookup
            (existing_handle, existing_node),  # existing file
        ]

        assert provider.upload_file(src, "update.db")
        mock_api.delete.assert_called_once_with(existing_handle)

    def test_upload_not_connected(self, provider, tmp_path: Path):
        src = tmp_path / "nope.txt"
        src.write_text("data")
        assert not provider.upload_file(src, "nope.txt")

    def test_upload_exception(self, provider, mock_api, tmp_path: Path):
        provider.connect()

        src = tmp_path / "fail.txt"
        src.write_text("data")

        mock_api.find.side_effect = IOError("network error")
        assert not provider.upload_file(src, "fail.txt")


# -- download --


class TestDownload:
    def test_download_success(self, provider, mock_api, tmp_path: Path):
        provider.connect()

        dst = tmp_path / "out.db"
        file_handle = "file_h"
        file_node = {"s": 2048}

        mock_api.find.return_value = (file_handle, file_node)

        # fake the download to write content
        def fake_dl(node, dest_path, dest_filename):
            Path(dest_path, dest_filename).write_bytes(b"remote content")

        mock_api.download.side_effect = fake_dl

        assert provider.download_file("backup.db", dst)
        assert dst.read_bytes() == b"remote content"

    def test_download_file_not_found(self, provider, mock_api, tmp_path: Path):
        provider.connect()
        mock_api.find.return_value = None

        dst = tmp_path / "nope.db"
        assert not provider.download_file("missing.db", dst)

    def test_download_not_connected(self, provider, tmp_path: Path):
        dst = tmp_path / "nope.db"
        assert not provider.download_file("remote.db", dst)

    def test_download_exception(self, provider, mock_api, tmp_path: Path):
        provider.connect()
        mock_api.find.return_value = ("h", {"s": 1})
        mock_api.download.side_effect = IOError("timeout")

        dst = tmp_path / "fail.db"
        assert not provider.download_file("remote.db", dst)


# -- get_file_info --


class TestGetFileInfo:
    def test_file_info_success(self, provider, mock_api, tmp_path: Path):
        provider.connect()

        file_handle = "file_h"
        file_node = {"s": 2048, "ts": 1700000000.0}
        mock_api.find.return_value = (file_handle, file_node)

        # mock download for checksum computation
        def fake_dl(node, dest_path, dest_filename):
            Path(dest_path, dest_filename).write_bytes(b"file data")

        mock_api.download.side_effect = fake_dl

        fi = provider.get_file_info("backup.db")
        assert fi is not None
        assert fi.name == "backup.db"
        assert fi.size == 2048
        assert fi.modified == 1700000000.0

        # checksum should match sha256 of "file data"
        import hashlib

        expected = hashlib.sha256(b"file data").hexdigest()
        assert fi.checksum == expected

    def test_file_info_not_found(self, provider, mock_api):
        provider.connect()
        mock_api.find.return_value = None

        fi = provider.get_file_info("nope.db")
        assert fi is None

    def test_file_info_not_connected(self, provider):
        fi = provider.get_file_info("nope.db")
        assert fi is None

    def test_file_info_large_file_no_checksum(self, provider, mock_api):
        provider.connect()

        # file larger than 50 MB -> no checksum download
        big_size = 60 * 1024 * 1024
        file_handle = "file_h"
        file_node = {"s": big_size, "ts": 1700000000.0}
        mock_api.find.return_value = (file_handle, file_node)

        fi = provider.get_file_info("huge.bin")
        assert fi is not None
        assert fi.checksum == ""
        # download should NOT have been called for checksum
        mock_api.download.assert_not_called()

    def test_file_info_exception(self, provider, mock_api):
        provider.connect()
        mock_api.find.side_effect = IOError("server down")

        fi = provider.get_file_info("fail.db")
        assert fi is None


# -- missing dependency --


class TestMissingDependency:
    def test_connect_without_mega_py(self):
        with patch(
            "steam_library_manager.services.cloud_sync.mega_provider.Mega",
            None,
        ):
            from steam_library_manager.services.cloud_sync.mega_provider import (
                MegaProvider,
            )

            p = MegaProvider("user@example.com", "secret")
            assert not p.connect()
