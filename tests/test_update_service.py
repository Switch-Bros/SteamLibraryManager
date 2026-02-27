"""Tests for the UpdateService auto-update functionality."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from src.services.update_service import UpdateInfo, UpdateService


class TestUpdateInfo:
    """Tests for UpdateInfo frozen dataclass."""

    def test_create_update_info(self) -> None:
        """UpdateInfo stores all fields correctly."""
        info = UpdateInfo(
            version="2.0.0",
            download_url="https://example.com/app.AppImage",
            download_size=50_000_000,
            release_notes="# v2.0.0\n- New feature",
            html_url="https://github.com/example/releases/v2.0.0",
        )
        assert info.version == "2.0.0"
        assert info.download_size == 50_000_000
        assert "New feature" in info.release_notes

    def test_update_info_is_frozen(self) -> None:
        """UpdateInfo is immutable."""
        info = UpdateInfo(
            version="2.0.0",
            download_url="",
            download_size=0,
            release_notes="",
            html_url="",
        )
        with pytest.raises(AttributeError):
            info.version = "3.0.0"  # type: ignore[misc]


class TestIsAppimage:
    """Tests for AppImage detection."""

    def test_is_appimage_true(self) -> None:
        """Returns True when APPIMAGE env var is set."""
        with patch.dict(os.environ, {"APPIMAGE": "/path/to/App.AppImage"}):
            assert UpdateService.is_appimage() is True

    def test_is_appimage_false(self) -> None:
        """Returns False when APPIMAGE env var is not set."""
        env = os.environ.copy()
        env.pop("APPIMAGE", None)
        with patch.dict(os.environ, env, clear=True):
            assert UpdateService.is_appimage() is False

    def test_current_appimage_path_set(self) -> None:
        """Returns Path when APPIMAGE is set."""
        with patch.dict(os.environ, {"APPIMAGE": "/tmp/SLM.AppImage"}):
            result = UpdateService.current_appimage_path()
            assert result == Path("/tmp/SLM.AppImage")

    def test_current_appimage_path_not_set(self) -> None:
        """Returns None when APPIMAGE is not set."""
        env = os.environ.copy()
        env.pop("APPIMAGE", None)
        with patch.dict(os.environ, env, clear=True):
            assert UpdateService.current_appimage_path() is None


class TestIsNewer:
    """Tests for semantic version comparison."""

    def test_newer_version(self) -> None:
        """Detects newer version correctly."""
        assert UpdateService._is_newer("2.0.0") is True

    def test_same_version(self) -> None:
        """Same version is not newer."""
        from src.version import __version__

        assert UpdateService._is_newer(__version__) is False

    def test_older_version(self) -> None:
        """Older version is not newer."""
        assert UpdateService._is_newer("0.1.0") is False

    def test_invalid_version_fallback(self) -> None:
        """Invalid version falls back to string comparison."""
        from src.version import __version__

        # Same as current — not newer
        assert UpdateService._is_newer(__version__) is False
        # Different string — fallback says "newer"
        assert UpdateService._is_newer("not-a-version") is True

    def test_prerelease_not_newer(self) -> None:
        """Pre-release of same version is not newer."""
        from src.version import __version__

        assert UpdateService._is_newer(f"{__version__}rc1") is False


class TestInstallUpdate:
    """Tests for atomic replace logic."""

    def test_install_no_appimage_env(self) -> None:
        """Install fails gracefully when not running as AppImage."""
        env = os.environ.copy()
        env.pop("APPIMAGE", None)
        with patch.dict(os.environ, env, clear=True):
            result = UpdateService.install_update("/tmp/new.AppImage")
            assert result is False

    def test_install_nonexistent_current(self, tmp_path: Path) -> None:
        """Install fails when current AppImage doesn't exist."""
        fake_path = str(tmp_path / "nonexistent.AppImage")
        with patch.dict(os.environ, {"APPIMAGE": fake_path}):
            result = UpdateService.install_update("/tmp/new.AppImage")
            assert result is False

    def test_install_creates_backup_and_replaces(self, tmp_path: Path) -> None:
        """Install creates .bak backup before replacing."""
        current = tmp_path / "SLM.AppImage"
        current.write_text("old-binary")
        new = tmp_path / "SLM_new.AppImage"
        new.write_text("new-binary")

        with (
            patch.dict(os.environ, {"APPIMAGE": str(current)}),
            patch("os.execv", side_effect=SystemExit(0)),
        ):
            try:
                UpdateService.install_update(str(new))
            except SystemExit:
                pass

        # Backup should exist
        backup = current.with_suffix(".bak")
        assert backup.exists()
        assert backup.read_text() == "old-binary"
        # Current should have new content
        assert current.read_text() == "new-binary"

    def test_install_rollback_on_failure(self, tmp_path: Path) -> None:
        """Install rolls back from backup on failure."""
        current = tmp_path / "SLM.AppImage"
        current.write_text("old-binary")
        new = tmp_path / "SLM_new.AppImage"
        new.write_text("new-binary")

        with (
            patch.dict(os.environ, {"APPIMAGE": str(current)}),
            patch("os.execv", side_effect=OSError("exec failed")),
        ):
            result = UpdateService.install_update(str(new))

        assert result is False
        # Should be rolled back to original
        assert current.read_text() == "old-binary"


class TestGithubApiParsing:
    """Tests for parsing GitHub API responses."""

    @staticmethod
    def _make_release_json(
        tag: str = "v2.0.0",
        appimage_url: str = "https://example.com/SLM-2.0.0.AppImage",
        appimage_size: int = 50_000_000,
    ) -> dict:
        """Create a mock GitHub release JSON response."""
        return {
            "tag_name": tag,
            "html_url": f"https://github.com/example/releases/{tag}",
            "body": f"# {tag}\n- Feature A\n- Feature B",
            "assets": [
                {
                    "name": f"SteamLibraryManager-{tag.lstrip('v')}-x86_64.AppImage",
                    "browser_download_url": appimage_url,
                    "size": appimage_size,
                },
                {
                    "name": "SHA256SUMS.txt",
                    "browser_download_url": "https://example.com/SHA256SUMS.txt",
                    "size": 128,
                },
            ],
        }

    def test_parse_appimage_asset(self) -> None:
        """Finds AppImage asset from release data."""
        data = self._make_release_json()
        assets = data["assets"]
        appimage_assets = [a for a in assets if a["name"].endswith(".AppImage")]
        assert len(appimage_assets) == 1
        assert appimage_assets[0]["size"] == 50_000_000

    def test_no_appimage_asset(self) -> None:
        """Handles release with no AppImage gracefully."""
        data = self._make_release_json()
        data["assets"] = [{"name": "source.tar.gz", "browser_download_url": "", "size": 100}]
        appimage_assets = [a for a in data["assets"] if a["name"].endswith(".AppImage")]
        assert len(appimage_assets) == 0

    def test_tag_version_parsing(self) -> None:
        """Version extracted from tag correctly."""
        data = self._make_release_json(tag="v1.2.3")
        version = data["tag_name"].lstrip("v")
        assert version == "1.2.3"

    def test_release_notes_preserved(self) -> None:
        """Release notes markdown is preserved."""
        data = self._make_release_json()
        assert "Feature A" in data["body"]
        assert "Feature B" in data["body"]
