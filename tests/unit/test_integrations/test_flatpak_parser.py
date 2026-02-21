"""Tests for Flatpak parser."""

from __future__ import annotations

from unittest.mock import patch

from src.integrations.external_games.flatpak_parser import FlatpakParser


class TestFlatpakParser:
    """Tests for Flatpak CLI parsing."""

    def test_parse_flatpak_output(self) -> None:
        """Parse tab-separated flatpak list output."""
        output = (
            "com.valvesoftware.Steam\tSteam\t1.0\n"
            "com.example.game\tCool Game\t2.0\n"
            "org.gnome.Calculator\tCalculator\t3.0\n"
        )

        parser = FlatpakParser()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = output
            with patch.object(parser, "is_available", return_value=True):
                games = parser.read_games()

        # Only "Cool Game" passes the non-game filter
        assert len(games) == 1
        assert games[0].name == "Cool Game"
        assert games[0].launch_command == "flatpak run com.example.game"

    def test_filter_non_games(self) -> None:
        """Known non-game prefixes are filtered."""
        output = (
            "com.heroicgameslauncher.hgl\tHeroic\t2.0\n"
            "net.lutris.Lutris\tLutris\t0.5\n"
            "io.github.somedev.SomeTool\tSomeTool\t1.0\n"
            "com.real.GameStudio\tActual Game\t1.0\n"
        )

        parser = FlatpakParser()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = output
            with patch.object(parser, "is_available", return_value=True):
                games = parser.read_games()

        assert len(games) == 1
        assert games[0].name == "Actual Game"

    def test_flatpak_not_installed(self) -> None:
        """Returns empty list when flatpak is not available."""
        parser = FlatpakParser()
        with patch("shutil.which", return_value=None):
            assert parser.is_available() is False
            assert parser.read_games() == []

    def test_empty_output(self) -> None:
        """Empty flatpak output returns empty list."""
        parser = FlatpakParser()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = ""
            with patch.object(parser, "is_available", return_value=True):
                assert parser.read_games() == []

    def test_flatpak_error(self) -> None:
        """Non-zero return code returns empty list."""
        parser = FlatpakParser()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stdout = ""
            with patch.object(parser, "is_available", return_value=True):
                assert parser.read_games() == []
