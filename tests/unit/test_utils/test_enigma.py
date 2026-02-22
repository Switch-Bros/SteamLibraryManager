# tests/unit/test_utils/test_enigma.py

"""Tests for the Easter egg loader utility."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.utils.enigma import load_easter_egg, play_easter_egg_sound


class TestLoadEasterEgg:
    """Tests for load_easter_egg()."""

    def test_load_konami_has_required_fields(self, tmp_path: Path) -> None:
        """Konami egg must have title, message, and sound."""
        enigma = tmp_path / ".enigma"
        enigma.write_text(
            json.dumps(
                {
                    "konami": {
                        "title": "T",
                        "message": "M",
                        "sound": "S.wav",
                    }
                }
            )
        )

        mock_config = MagicMock()
        mock_config.RESOURCES_DIR = tmp_path

        with patch("src.utils.enigma.config", mock_config):
            egg = load_easter_egg("konami")

        assert egg["title"] == "T"
        assert egg["message"] == "M"
        assert egg["sound"] == "S.wav"

    def test_load_missing_file_returns_empty(self, tmp_path: Path) -> None:
        """Missing .enigma file should not crash."""
        mock_config = MagicMock()
        mock_config.RESOURCES_DIR = tmp_path / "nonexistent"

        with patch("src.utils.enigma.config", mock_config):
            result = load_easter_egg("konami")

        assert result == {}

    def test_load_unknown_id_returns_empty(self, tmp_path: Path) -> None:
        """Unknown egg ID should return empty dict."""
        enigma = tmp_path / ".enigma"
        enigma.write_text(json.dumps({"konami": {"title": "T"}}))

        mock_config = MagicMock()
        mock_config.RESOURCES_DIR = tmp_path

        with patch("src.utils.enigma.config", mock_config):
            result = load_easter_egg("nonexistent")

        assert result == {}

    def test_load_corrupt_json_returns_empty(self, tmp_path: Path) -> None:
        """Corrupt JSON file should not crash."""
        enigma = tmp_path / ".enigma"
        enigma.write_text("{invalid json!!!")

        mock_config = MagicMock()
        mock_config.RESOURCES_DIR = tmp_path

        with patch("src.utils.enigma.config", mock_config):
            result = load_easter_egg("konami")

        assert result == {}

    def test_load_searchbar_egg(self, tmp_path: Path) -> None:
        """Searchbar egg should load title and message."""
        enigma = tmp_path / ".enigma"
        enigma.write_text(
            json.dumps(
                {
                    "searchbar": {
                        "title": "Hello",
                        "message": "Found!",
                    }
                }
            )
        )

        mock_config = MagicMock()
        mock_config.RESOURCES_DIR = tmp_path

        with patch("src.utils.enigma.config", mock_config):
            egg = load_easter_egg("searchbar")

        assert egg["title"] == "Hello"
        assert egg["message"] == "Found!"
        assert "sound" not in egg


class TestPlayEasterEggSound:
    """Tests for play_easter_egg_sound()."""

    def test_play_existing_sound_calls_paplay(self, tmp_path: Path) -> None:
        """Should call paplay with the correct sound path."""
        sounds_dir = tmp_path / "sounds"
        sounds_dir.mkdir()
        sound_file = sounds_dir / "test.wav"
        sound_file.write_bytes(b"RIFF")

        mock_config = MagicMock()
        mock_config.RESOURCES_DIR = tmp_path

        with (
            patch("src.utils.enigma.config", mock_config),
            patch("src.utils.enigma.subprocess.Popen") as mock_popen,
        ):
            play_easter_egg_sound("test.wav")

        mock_popen.assert_called_once()
        call_args = mock_popen.call_args[0][0]
        assert call_args[0] == "paplay"
        assert call_args[1] == str(sound_file)

    def test_play_missing_file_does_nothing(self, tmp_path: Path) -> None:
        """Missing sound file should not crash or call paplay."""
        mock_config = MagicMock()
        mock_config.RESOURCES_DIR = tmp_path

        with (
            patch("src.utils.enigma.config", mock_config),
            patch("src.utils.enigma.subprocess.Popen") as mock_popen,
        ):
            play_easter_egg_sound("nonexistent.wav")

        mock_popen.assert_not_called()

    def test_play_paplay_not_installed_fails_silently(self, tmp_path: Path) -> None:
        """If paplay is not installed, should fail silently."""
        sounds_dir = tmp_path / "sounds"
        sounds_dir.mkdir()
        sound_file = sounds_dir / "test.wav"
        sound_file.write_bytes(b"RIFF")

        mock_config = MagicMock()
        mock_config.RESOURCES_DIR = tmp_path

        with (
            patch("src.utils.enigma.config", mock_config),
            patch(
                "src.utils.enigma.subprocess.Popen",
                side_effect=FileNotFoundError("paplay not found"),
            ),
        ):
            # Should not raise
            play_easter_egg_sound("test.wav")
