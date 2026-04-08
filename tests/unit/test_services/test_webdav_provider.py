# tests/unit/test_services/test_webdav_provider.py

"""Unit tests for WebDAVProvider with mocked webdavclient3."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# -- fixtures --


@pytest.fixture()
def mock_client_cls():
    """Patch webdav3.client.Client and return the mock class."""
    with patch("steam_library_manager.services.cloud_sync.webdav.Client") as cls:
        inst = MagicMock()
        cls.return_value = inst
        yield cls


@pytest.fixture()
def mock_client(mock_client_cls):
    """Return the mock Client instance."""
    return mock_client_cls.return_value


@pytest.fixture()
def provider(mock_client_cls):
    """Create a WebDAVProvider that uses the mocked Client."""
    from steam_library_manager.services.cloud_sync.webdav import WebDAVProvider

    p = WebDAVProvider("https://dav.example.com", "user", "pass")
    return p


# -- connect / disconnect --


class TestConnect:
    def test_connect_success(self, provider, mock_client):
        mock_client.check.return_value = True
        assert provider.connect()
        assert provider.is_connected()

    def test_connect_check_raises(self, provider, mock_client):
        mock_client.check.side_effect = ConnectionError("nope")
        assert not provider.connect()
        assert not provider.is_connected()

    def test_disconnect(self, provider, mock_client):
        mock_client.check.return_value = True
        provider.connect()
        provider.disconnect()
        assert not provider.is_connected()


# -- upload --


class TestUpload:
    def test_upload_success(self, provider, mock_client, tmp_path: Path):
        mock_client.check.return_value = True
        provider.connect()

        src = tmp_path / "data.db"
        src.write_bytes(b"payload")

        assert provider.upload_file(src, "SteamLibraryManager/data.db")
        mock_client.upload_sync.assert_called_once_with(
            remote_path="SteamLibraryManager/data.db",
            local_path=str(src),
        )

    def test_upload_creates_parent_dir(self, provider, mock_client, tmp_path: Path):
        # check returns False for dir -> mkdir should be called
        mock_client.check.side_effect = lambda p=None: (True if p is None else False)
        provider.connect()
        # reset check side_effect for upload itself
        mock_client.check.side_effect = lambda p=None: False if p else True

        # re-connect to get the client stored
        mock_client.check.return_value = True
        provider.connect()
        mock_client.check.reset_mock()

        src = tmp_path / "test.txt"
        src.write_text("hello")

        # make check return False for dir existence checks
        mock_client.check.return_value = False
        assert provider.upload_file(src, "a/b/test.txt")
        # mkdir should have been called for parent dirs
        assert mock_client.mkdir.call_count >= 1

    def test_upload_not_connected(self, provider, tmp_path: Path):
        src = tmp_path / "nope.txt"
        src.write_text("data")
        assert not provider.upload_file(src, "nope.txt")

    def test_upload_exception(self, provider, mock_client, tmp_path: Path):
        mock_client.check.return_value = True
        provider.connect()

        src = tmp_path / "fail.txt"
        src.write_text("data")
        mock_client.upload_sync.side_effect = IOError("disk full")

        assert not provider.upload_file(src, "fail.txt")


# -- download --


class TestDownload:
    def test_download_success(self, provider, mock_client, tmp_path: Path):
        mock_client.check.return_value = True
        provider.connect()

        dst = tmp_path / "out.db"

        # fake the download_sync to write content
        def fake_dl(remote_path, local_path):
            Path(local_path).write_bytes(b"remote content")

        mock_client.download_sync.side_effect = fake_dl

        assert provider.download_file("remote.db", dst)
        assert dst.read_bytes() == b"remote content"

    def test_download_not_connected(self, provider, tmp_path: Path):
        dst = tmp_path / "nope.db"
        assert not provider.download_file("remote.db", dst)

    def test_download_exception(self, provider, mock_client, tmp_path: Path):
        mock_client.check.return_value = True
        provider.connect()

        dst = tmp_path / "fail.db"
        mock_client.download_sync.side_effect = IOError("timeout")

        assert not provider.download_file("remote.db", dst)


# -- get_file_info --


class TestGetFileInfo:
    def test_file_info_success(self, provider, mock_client, tmp_path: Path):
        mock_client.check.return_value = True
        provider.connect()

        # mock info() return
        mock_client.info.return_value = {
            "size": "2048",
            "modified": "1700000000.0",
        }

        # mock download_sync for checksum computation
        def fake_dl(remote_path, local_path):
            Path(local_path).write_bytes(b"file data")

        mock_client.download_sync.side_effect = fake_dl

        fi = provider.get_file_info("backup.db")
        assert fi is not None
        assert fi.name == "backup.db"
        assert fi.size == 2048

        # checksum should match sha256 of "file data"
        import hashlib

        expected = hashlib.sha256(b"file data").hexdigest()
        assert fi.checksum == expected

    def test_file_info_not_found(self, provider, mock_client):
        # connect first, then check returns False for the file
        mock_client.check.return_value = True
        provider.connect()
        mock_client.check.return_value = False

        fi = provider.get_file_info("nope.db")
        assert fi is None

    def test_file_info_not_connected(self, provider):
        fi = provider.get_file_info("nope.db")
        assert fi is None

    def test_file_info_large_file_no_checksum(self, provider, mock_client):
        mock_client.check.return_value = True
        provider.connect()

        # file larger than 50 MB -> no checksum download
        mock_client.info.return_value = {
            "size": str(60 * 1024 * 1024),
            "modified": "1700000000.0",
        }

        fi = provider.get_file_info("huge.bin")
        assert fi is not None
        assert fi.checksum == ""
        # download_sync should NOT have been called for checksum
        mock_client.download_sync.assert_not_called()

    def test_file_info_exception(self, provider, mock_client):
        mock_client.check.return_value = True
        provider.connect()
        mock_client.check.side_effect = IOError("server down")

        fi = provider.get_file_info("fail.db")
        assert fi is None


# -- missing dependency --


class TestMissingDependency:
    def test_connect_without_webdavclient3(self):
        with patch("steam_library_manager.services.cloud_sync.webdav.Client", None):
            from steam_library_manager.services.cloud_sync.webdav import (
                WebDAVProvider,
            )

            p = WebDAVProvider("https://example.com", "u", "p")
            assert not p.connect()
