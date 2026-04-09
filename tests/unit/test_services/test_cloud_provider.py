# tests/unit/test_services/test_cloud_provider.py

"""Unit tests for CloudProvider interface and FileInfo dataclass."""

import hashlib
import time
from pathlib import Path

import pytest

from steam_library_manager.services.cloud_sync import CloudProvider, FileInfo

# -- fixtures and helpers --


class MockProvider(CloudProvider):
    """In-memory cloud provider for contract testing."""

    def __init__(self):
        self._connected = False
        self._files: dict[str, bytes] = {}

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def upload_file(self, local: Path, remote_name: str) -> bool:
        if not self._connected:
            return False
        self._files[remote_name] = local.read_bytes()
        return True

    def download_file(self, remote_name: str, local: Path) -> bool:
        if not self._connected:
            return False
        if remote_name not in self._files:
            return False
        local.write_bytes(self._files[remote_name])
        return True

    def get_file_info(self, remote_name: str) -> FileInfo | None:
        if remote_name not in self._files:
            return None
        data = self._files[remote_name]
        cs = hashlib.sha256(data).hexdigest()
        return FileInfo(
            name=remote_name,
            size=len(data),
            modified=time.time(),
            checksum=cs,
        )


class TestFileInfo:
    """Tests for FileInfo dataclass."""

    def test_creation(self):
        fi = FileInfo(name="backup.db", size=1024, modified=1700000000.0, checksum="abc123")
        assert fi.name == "backup.db"
        assert fi.size == 1024
        assert fi.modified == 1700000000.0
        assert fi.checksum == "abc123"

    def test_frozen(self):
        fi = FileInfo(name="backup.db", size=1024, modified=1700000000.0, checksum="abc123")
        with pytest.raises(AttributeError):
            fi.name = "other.db"  # type: ignore[misc]


class TestCloudProviderContract:
    """Contract tests using MockProvider."""

    @pytest.fixture()
    def provider(self):
        return MockProvider()

    def test_connect_disconnect(self, provider: MockProvider):
        assert not provider.is_connected()
        assert provider.connect()
        assert provider.is_connected()
        provider.disconnect()
        assert not provider.is_connected()

    def test_upload_requires_connection(self, provider: MockProvider, tmp_path: Path):
        # upload without connecting -> fails
        fp = tmp_path / "test.txt"
        fp.write_text("hello")
        assert not provider.upload_file(fp, "test.txt")

    def test_upload_download_roundtrip(self, provider: MockProvider, tmp_path: Path):
        provider.connect()
        src = tmp_path / "src.txt"
        src.write_text("roundtrip data")
        assert provider.upload_file(src, "remote.txt")

        dst = tmp_path / "dst.txt"
        assert provider.download_file("remote.txt", dst)
        assert dst.read_text() == "roundtrip data"

    def test_get_file_info(self, provider: MockProvider, tmp_path: Path):
        provider.connect()
        src = tmp_path / "info.bin"
        payload = b"\x00" * 512
        src.write_bytes(payload)
        provider.upload_file(src, "info.bin")

        fi = provider.get_file_info("info.bin")
        assert fi is not None
        assert fi.name == "info.bin"
        assert fi.size == 512
        expected_cs = hashlib.sha256(payload).hexdigest()
        assert fi.checksum == expected_cs

    def test_get_file_info_missing(self, provider: MockProvider):
        provider.connect()
        assert provider.get_file_info("nope.txt") is None

    def test_download_missing_file(self, provider: MockProvider, tmp_path: Path):
        provider.connect()
        dst = tmp_path / "missing.txt"
        assert not provider.download_file("nope.txt", dst)
        assert not dst.exists()

    def test_base_class_raises_not_implemented(self):
        # bare CloudProvider should raise on every method
        base = CloudProvider()
        with pytest.raises(NotImplementedError):
            base.connect()
        with pytest.raises(NotImplementedError):
            base.disconnect()
        with pytest.raises(NotImplementedError):
            base.is_connected()
        with pytest.raises(NotImplementedError):
            base.upload_file(Path("/tmp/x"), "x")
        with pytest.raises(NotImplementedError):
            base.download_file("x", Path("/tmp/x"))
        with pytest.raises(NotImplementedError):
            base.get_file_info("x")
