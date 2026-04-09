# tests/unit/test_services/test_sync_service.py

"""Unit tests for CloudSyncService."""

import hashlib
import sqlite3
import time
from pathlib import Path

import pytest

from steam_library_manager.services.cloud_sync import CloudProvider, FileInfo
from steam_library_manager.services.cloud_sync.sync_service import (
    CloudSyncService,
    ConflictAction,
    SyncResult,
)

# -- mock provider (same pattern as test_cloud_provider.py) --


class MockProvider(CloudProvider):
    """In-memory cloud provider for sync testing."""

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
        local.parent.mkdir(parents=True, exist_ok=True)
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


# -- helpers --


def _make_test_db(path: Path) -> None:
    """Create a minimal SQLite database for testing."""
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, val TEXT)")
    conn.execute("INSERT INTO test (val) VALUES ('hello')")
    conn.commit()
    conn.close()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


# -- fixtures --


@pytest.fixture()
def provider():
    prov = MockProvider()
    prov.connect()
    return prov


@pytest.fixture()
def setup(tmp_path: Path, provider: MockProvider):
    """Set up db, settings, tmp_dir, and sync service."""
    db = tmp_path / "metadata.db"
    _make_test_db(db)

    settings = tmp_path / "settings.json"
    settings.write_text('{"theme": "dark"}')

    tmp_dir = tmp_path / "sync_tmp"
    svc = CloudSyncService(provider, db, settings, tmp_dir)
    return svc, provider, db, settings, tmp_dir


# -- SyncResult tests --


class TestSyncResult:
    def test_success(self):
        r = SyncResult(True, "abc123")
        assert r.success is True
        assert r.message == "abc123"

    def test_failure(self):
        r = SyncResult(False, "something broke")
        assert r.success is False
        assert r.message == "something broke"


# -- upload tests --


class TestUpload:
    def test_upload_creates_remote_files(self, setup):
        svc, prov, db, settings, _ = setup
        result = svc.upload()

        assert result.success
        # db should exist in remote
        assert "SteamLibraryManager/metadata.db" in prov._files
        # settings should exist in remote
        assert "SteamLibraryManager/settings.json" in prov._files

    def test_upload_returns_checksum(self, setup):
        svc, prov, db, _, _ = setup
        result = svc.upload()

        assert result.success
        # result message should be a valid sha256 hex string
        assert len(result.message) == 64
        assert all(c in "0123456789abcdef" for c in result.message)

    def test_upload_db_is_valid_sqlite(self, setup):
        svc, prov, _, _, _ = setup
        result = svc.upload()
        assert result.success

        # the uploaded bytes should be a valid sqlite database
        raw = prov._files["SteamLibraryManager/metadata.db"]
        assert raw[:16] == b"SQLite format 3\x00"

        # verify we can query it
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            f.write(raw)
            tmp = Path(f.name)
        try:
            conn = sqlite3.connect(str(tmp))
            rows = conn.execute("SELECT val FROM test").fetchall()
            conn.close()
            assert rows == [("hello",)]
        finally:
            tmp.unlink()

    def test_upload_fails_when_not_connected(self, setup):
        svc, prov, _, _, _ = setup
        prov.disconnect()
        result = svc.upload()

        assert not result.success
        assert result.message == "not connected"

    def test_upload_cleans_up_temp(self, setup):
        svc, _, _, _, tmp_dir = setup
        svc.upload()

        # temp snapshot should be removed
        snap = tmp_dir / "metadata.db"
        assert not snap.exists()

    def test_upload_without_settings(self, tmp_path: Path, provider: MockProvider):
        # settings file does not exist
        db = tmp_path / "metadata.db"
        _make_test_db(db)
        missing = tmp_path / "nonexistent_settings.json"
        tmp_dir = tmp_path / "sync_tmp"

        svc = CloudSyncService(provider, db, missing, tmp_dir)
        result = svc.upload()

        assert result.success
        assert "SteamLibraryManager/metadata.db" in provider._files
        assert "SteamLibraryManager/settings.json" not in provider._files


# -- download tests --


class TestDownload:
    def test_download_replaces_local_db(self, setup):
        svc, prov, db, _, _ = setup

        # upload first to populate remote
        up = svc.upload()
        assert up.success
        remote_cs = up.message  # checksum of the backup snapshot

        # modify local db
        conn = sqlite3.connect(str(db))
        conn.execute("INSERT INTO test (val) VALUES ('modified')")
        conn.commit()
        conn.close()

        # download should restore to uploaded snapshot
        result = svc.download()
        assert result.success
        assert _sha256(db) == remote_cs

    def test_download_fails_when_not_connected(self, setup):
        svc, prov, _, _, _ = setup
        prov.disconnect()
        result = svc.download()

        assert not result.success
        assert result.message == "not connected"

    def test_download_fails_when_no_remote(self, setup):
        svc, _, _, _, _ = setup
        # nothing uploaded yet
        result = svc.download()

        assert not result.success
        assert result.message == "no remote db found"

    def test_download_cleans_up_temp(self, setup):
        svc, _, _, _, tmp_dir = setup
        svc.upload()
        svc.download()

        # temp files should be cleaned up
        tmp_db = tmp_dir / "metadata.db"
        tmp_settings = tmp_dir / "settings.json"
        assert not tmp_db.exists()
        assert not tmp_settings.exists()

    def test_download_also_gets_settings(self, setup):
        svc, prov, _, settings, _ = setup
        svc.upload()

        # modify local settings
        settings.write_text('{"theme": "light"}')

        result = svc.download()
        assert result.success
        assert settings.read_text() == '{"theme": "dark"}'


# -- conflict detection tests --


class TestConflictDetection:
    def test_no_conflict_when_identical(self, setup):
        svc, prov, db, _, _ = setup
        up = svc.upload()
        last_cs = up.message  # use snapshot checksum from upload

        action = svc.detect_conflict(last_cs)
        assert action == ConflictAction.NONE

    def test_upload_when_only_local_changed(self, setup):
        svc, prov, db, _, _ = setup
        up = svc.upload()
        last_cs = up.message

        # modify local
        conn = sqlite3.connect(str(db))
        conn.execute("INSERT INTO test (val) VALUES ('local change')")
        conn.commit()
        conn.close()

        action = svc.detect_conflict(last_cs)
        assert action == ConflictAction.UPLOAD

    def test_download_when_only_remote_changed(self, setup):
        svc, prov, db, _, _ = setup
        up = svc.upload()
        last_cs = up.message

        # tamper remote directly
        prov._files["SteamLibraryManager/metadata.db"] = b"remote change"

        action = svc.detect_conflict(last_cs)
        assert action == ConflictAction.DOWNLOAD

    def test_conflict_when_both_changed(self, setup):
        svc, prov, db, _, _ = setup
        up = svc.upload()
        last_cs = up.message

        # modify local
        conn = sqlite3.connect(str(db))
        conn.execute("INSERT INTO test (val) VALUES ('local')")
        conn.commit()
        conn.close()

        # tamper remote
        prov._files["SteamLibraryManager/metadata.db"] = b"remote"

        action = svc.detect_conflict(last_cs)
        assert action == ConflictAction.CONFLICT

    def test_upload_when_no_remote(self, setup):
        svc, _, _, _, _ = setup
        # no upload yet -> should suggest upload
        action = svc.detect_conflict("doesntmatter")
        assert action == ConflictAction.UPLOAD
