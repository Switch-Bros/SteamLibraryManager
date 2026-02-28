"""Tests for AppImage desktop integration (install/uninstall)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from src.utils.desktop_integration import (
    DESKTOP_ID,
    get_appimage_path,
    install_desktop_entry,
    is_appimage,
    is_desktop_entry_installed,
    uninstall_desktop_entry,
)


class TestIsAppimage:
    """Tests for is_appimage() detection."""

    def test_is_appimage_true(self):
        """Returns True when APPIMAGE env var is set."""
        with patch.dict("os.environ", {"APPIMAGE": "/home/user/App.AppImage"}):
            assert is_appimage() is True

    def test_is_appimage_false(self):
        """Returns False when APPIMAGE env var is not set."""
        with patch.dict("os.environ", {}, clear=True):
            assert is_appimage() is False

    def test_is_appimage_empty_string(self):
        """Returns False when APPIMAGE is empty string."""
        with patch.dict("os.environ", {"APPIMAGE": ""}):
            assert is_appimage() is False


class TestGetAppimagePath:
    """Tests for get_appimage_path()."""

    def test_returns_path_when_set(self):
        """Returns Path object when APPIMAGE is set."""
        with patch.dict("os.environ", {"APPIMAGE": "/opt/App.AppImage"}):
            result = get_appimage_path()
            assert result == Path("/opt/App.AppImage")

    def test_returns_none_when_not_set(self):
        """Returns None when APPIMAGE is not set."""
        with patch.dict("os.environ", {}, clear=True):
            assert get_appimage_path() is None


class TestInstallDesktopEntry:
    """Tests for install_desktop_entry()."""

    def test_install_creates_desktop_file(self, tmp_path):
        """Desktop file is created with correct content."""
        apps_dir = tmp_path / "applications"
        icons_dir = tmp_path / "icons" / "hicolor" / "scalable" / "apps"
        appimage_path = "/home/user/SteamLibraryManager-x86_64.AppImage"

        # Create a fake icon source
        resources_dir = tmp_path / "resources"
        resources_dir.mkdir()
        icon_src = resources_dir / "icon.svg"
        icon_src.write_text("<svg>test</svg>")

        with (
            patch.dict("os.environ", {"APPIMAGE": appimage_path}),
            patch("src.utils.desktop_integration._apps_dir", return_value=apps_dir),
            patch("src.utils.desktop_integration._icons_dir", return_value=icons_dir),
            patch("src.utils.desktop_integration.config") as mock_config,
            patch("src.utils.desktop_integration._update_desktop_database"),
        ):
            mock_config.RESOURCES_DIR = resources_dir

            result = install_desktop_entry()

        assert result is True
        desktop_file = apps_dir / f"{DESKTOP_ID}.desktop"
        assert desktop_file.exists()

    def test_install_exec_contains_appimage_path(self, tmp_path):
        """Exec= line in .desktop file points to actual AppImage path."""
        apps_dir = tmp_path / "applications"
        icons_dir = tmp_path / "icons"
        appimage_path = "/home/user/MyApp.AppImage"

        resources_dir = tmp_path / "resources"
        resources_dir.mkdir()
        (resources_dir / "icon.svg").write_text("<svg/>")

        with (
            patch.dict("os.environ", {"APPIMAGE": appimage_path}),
            patch("src.utils.desktop_integration._apps_dir", return_value=apps_dir),
            patch("src.utils.desktop_integration._icons_dir", return_value=icons_dir),
            patch("src.utils.desktop_integration.config") as mock_config,
            patch("src.utils.desktop_integration._update_desktop_database"),
        ):
            mock_config.RESOURCES_DIR = resources_dir
            install_desktop_entry()

        content = (apps_dir / f"{DESKTOP_ID}.desktop").read_text()
        assert f"Exec={appimage_path}" in content

    def test_install_copies_icon(self, tmp_path):
        """Icon SVG is copied to the icons directory."""
        apps_dir = tmp_path / "applications"
        icons_dir = tmp_path / "icons" / "hicolor" / "scalable" / "apps"

        resources_dir = tmp_path / "resources"
        resources_dir.mkdir()
        (resources_dir / "icon.svg").write_text("<svg>icon-content</svg>")

        with (
            patch.dict("os.environ", {"APPIMAGE": "/app.AppImage"}),
            patch("src.utils.desktop_integration._apps_dir", return_value=apps_dir),
            patch("src.utils.desktop_integration._icons_dir", return_value=icons_dir),
            patch("src.utils.desktop_integration.config") as mock_config,
            patch("src.utils.desktop_integration._update_desktop_database"),
        ):
            mock_config.RESOURCES_DIR = resources_dir
            install_desktop_entry()

        icon_file = icons_dir / f"{DESKTOP_ID}.svg"
        assert icon_file.exists()
        assert icon_file.read_text() == "<svg>icon-content</svg>"

    def test_install_fails_without_appimage(self):
        """Returns False when not running as AppImage."""
        with patch.dict("os.environ", {}, clear=True):
            assert install_desktop_entry() is False

    def test_install_desktop_has_correct_fields(self, tmp_path):
        """Generated .desktop file contains required fields."""
        apps_dir = tmp_path / "applications"
        icons_dir = tmp_path / "icons"

        resources_dir = tmp_path / "resources"
        resources_dir.mkdir()
        (resources_dir / "icon.svg").write_text("<svg/>")

        with (
            patch.dict("os.environ", {"APPIMAGE": "/app.AppImage"}),
            patch("src.utils.desktop_integration._apps_dir", return_value=apps_dir),
            patch("src.utils.desktop_integration._icons_dir", return_value=icons_dir),
            patch("src.utils.desktop_integration.config") as mock_config,
            patch("src.utils.desktop_integration._update_desktop_database"),
        ):
            mock_config.RESOURCES_DIR = resources_dir
            install_desktop_entry()

        content = (apps_dir / f"{DESKTOP_ID}.desktop").read_text()
        assert "Type=Application" in content
        assert "Name=Steam Library Manager" in content
        assert f"Icon={DESKTOP_ID}" in content
        assert "Terminal=false" in content
        assert "Categories=Game;Utility;" in content
        assert "StartupWMClass=SteamLibraryManager" in content


class TestUninstallDesktopEntry:
    """Tests for uninstall_desktop_entry()."""

    def test_uninstall_removes_files(self, tmp_path):
        """Both .desktop and icon files are removed."""
        apps_dir = tmp_path / "applications"
        icons_dir = tmp_path / "icons"
        apps_dir.mkdir(parents=True)
        icons_dir.mkdir(parents=True)

        desktop_file = apps_dir / f"{DESKTOP_ID}.desktop"
        icon_file = icons_dir / f"{DESKTOP_ID}.svg"
        desktop_file.write_text("[Desktop Entry]")
        icon_file.write_text("<svg/>")

        with (
            patch("src.utils.desktop_integration._apps_dir", return_value=apps_dir),
            patch("src.utils.desktop_integration._icons_dir", return_value=icons_dir),
            patch("src.utils.desktop_integration._update_desktop_database"),
        ):
            result = uninstall_desktop_entry()

        assert result is True
        assert not desktop_file.exists()
        assert not icon_file.exists()

    def test_uninstall_missing_files_no_error(self, tmp_path):
        """Uninstall succeeds even if files don't exist."""
        apps_dir = tmp_path / "applications"
        icons_dir = tmp_path / "icons"
        apps_dir.mkdir(parents=True)
        icons_dir.mkdir(parents=True)

        with (
            patch("src.utils.desktop_integration._apps_dir", return_value=apps_dir),
            patch("src.utils.desktop_integration._icons_dir", return_value=icons_dir),
            patch("src.utils.desktop_integration._update_desktop_database"),
        ):
            result = uninstall_desktop_entry()

        assert result is True


class TestIsDesktopEntryInstalled:
    """Tests for is_desktop_entry_installed()."""

    def test_returns_true_when_exists(self, tmp_path):
        """Returns True when .desktop file exists."""
        apps_dir = tmp_path / "applications"
        apps_dir.mkdir(parents=True)
        (apps_dir / f"{DESKTOP_ID}.desktop").write_text("[Desktop Entry]")

        with patch("src.utils.desktop_integration._apps_dir", return_value=apps_dir):
            assert is_desktop_entry_installed() is True

    def test_returns_false_when_missing(self, tmp_path):
        """Returns False when .desktop file does not exist."""
        apps_dir = tmp_path / "nonexistent"

        with patch("src.utils.desktop_integration._apps_dir", return_value=apps_dir):
            assert is_desktop_entry_installed() is False
